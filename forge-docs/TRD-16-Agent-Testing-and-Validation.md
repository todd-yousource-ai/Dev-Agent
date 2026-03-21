# TRD-16-Agent-Testing-and-Validation

_Source: `TRD-16-Agent-Testing-and-Validation.docx` — extracted 2026-03-21 21:32 UTC_

---

# TRD-16: Agent Testing and Validation

Technical Requirements Document — v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-16: Agent Testing and Validation
Version | 1.0
Status | Production Reference (March 2026)
Author | Todd Gould / YouSource.ai
Date | 2026-03-20
Depends on | TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality), TRD-15 (Runbook)

## 1. Purpose and Scope

This TRD defines the complete testing and validation strategy for the Forge Dev Agent. It covers three distinct layers of testing that together provide confidence the agent will function correctly before spending a single token on a real build.

The testing strategy owns: - Unit tests — logic validation without API calls or network - Recovery smoke tests — state persistence and restart validation - Live smoke tests — real API connectivity and end-to-end pipeline validation - Install integration — when and how tests run automatically - Cost rationale — why each test layer exists and what it protects

What this TRD does not cover: The test suite the agent generates for the code it builds (that is covered by TRD-3 §12 and TRD-14).

## 2. Testing Philosophy

### 2.1 Three Layers, Three Purposes

Layer 1: Unit Tests
  Purpose:  Validate logic in isolation
  Requires: No network, no API keys, no GitHub
  Speed:    ~30 seconds for full suite
  When:     Always — runs automatically at install, on every patch

Layer 2: Recovery Smoke Tests
  Purpose:  Validate state persistence and restart behavior
  Requires: No network (mocks GitHub for JSON recovery tests)
  Speed:    ~15 seconds
  When:     Included in unit test suite — runs with Layer 1

Layer 3: Live Smoke Tests
  Purpose:  Validate real API connectivity and full pipeline
  Requires: Anthropic API key, OpenAI API key, GitHub token
  Speed:    ~60 seconds, costs ~$0.01
  When:     Recommended at first install, on demand thereafter

### 2.2 The Financial Rationale

The agent runs unattended for 3–8 hours and makes hundreds of API calls. A misconfigured API key discovered at PR #5 means restarting the entire build. A failing GitHub token means 30 minutes of PRD generation work is committed to no branches.

The test layers exist to front-load failure discovery:

Failure discovered at | Cost
Unit test (Layer 1) | $0
Recovery test (Layer 2) | $0
Live smoke test (Layer 3) | ~$0.01
PR #1 during real build | ~$0.63
PR #5 during real build | ~$3.15
PR #23 after 8 hours | ~$75+

Spending $0.01 on a smoke test to avoid discovering a problem at PR #23 is the correct tradeoff.

### 2.3 What We Test vs. What We Mock

Unit tests mock all external dependencies. The rule: if it makes a network call, mock it. If it’s pure logic, test it directly.

Live smoke tests mock nothing. They exist specifically because the mocked unit tests cannot tell you whether your API keys are valid, your GitHub token has write access, or the Anthropic API is reachable from your network.

## 3. Unit Test Suite

### 3.1 Coverage Summary

The unit test suite covers 53 source files across 17 test files, 333 test functions.

Test file | What it covers
test_audit.py | Audit log events, JSONL format, replay
test_build_director.py | Pipeline logic, state machine, path sanitization, slug generation
test_build_map.py | AST extraction, interface map rendering, OI13 gate, multi-turn loop, impl_files population
test_consensus.py | Consensus engine, context window, arbitration JSON parsing
test_document_store.py | Document loading, auto-context, doc filtering
test_e2e.py | Bridge startup, WebSocket auth, agent lifecycle
test_failure_handler.py | Failure classification, error extraction, fix loop control
test_github_tools.py | GitHub tool operations (mocked)
test_integration.py | Full pipeline with all external calls mocked
test_path_security.py | Path traversal prevention, allowed roots, placeholder rejection
test_prd_planner.py | PRD generation, decomposition, correction protocol
test_pre_pr_review.py | Pre-PR consensus review, issue detection
test_sandbox.py | Sandboxed execution, file write safety
test_smoke_recovery.py | State persistence, restart, checkpoints (see §4)
test_smoke.py | Live API tests (see §5)
test_test_runner.py | pytest/ruff execution, result parsing

### 3.2 Coverage Gaps (Documented)

The following source modules have no dedicated test file. They are covered partially by integration tests but are acknowledged gaps:

agent.py, branch_scaffold.py, build_ledger.py, ci_checker.py, ci_workflow.py, forge_context.py, markdown_strategy.py, mcp_generator.py, oi13_gate.py, pr_planner.py, thread_state.py

Priority for v2.0 test suite: thread_state.py (critical to recovery) and ci_checker.py (critical to CI fix loop).

### 3.3 Running Unit Tests

# At install — automatic, no action required
python install.py

# Anytime after install
python install.py --test

# Direct pytest
PYTHONPATH=src python3 -m pytest tests/ -v --ignore=tests/test_smoke.py

# Specific module
PYTHONPATH=src python3 -m pytest tests/test_build_map.py -v

### 3.4 Critical Unit Tests

The following tests directly validate fixes that were root causes of build failures:

test_build_map.py::TestImplFilesPopulation::test_impl_files_read_from_spec_data Verifies that PRPlanner reads impl_files and test_files from the LLM spec response. This was the root cause of every untitled.py CI failure — the PR planner was generating correct filenames but never storing them.

test_build_map.py::TestImplFilesPopulation::test_untitled_py_rejected_by_sanitize Verifies that _sanitize_file_path() rejects untitled.py and derives a proper filename. The fallback must never be untitled.py.

test_build_map.py::TestOI13PromptConstraint::test_returns_empty_when_gate_disabled Verifies the OI13 gate returns empty string when disabled. If this fails, every PR prompt contains an irrelevant endpoint memory budget warning.

test_build_map.py::TestMultiTurnFixLoop::test_builds_grounding_system_prompt Verifies the system prompt contains impl_files, acceptance_criteria, and PR title. If this fails, the LLM on fix loop turn 15 has no memory of which file it is writing.

test_build_map.py::TestGenerationContext::test_context_window_not_absurdly_small Verifies MAX_CONTEXT_TOKENS >= 30000. The previous value was 1,500 — so small that description_md was being truncated to a few sentences.

## 4. Recovery Smoke Tests

### 4.1 Purpose

Recovery tests validate the state persistence and restart system without making any real API calls. They answer the question: “If the agent crashes at this exact point, will it resume correctly?”

These are not unit tests — they test the interaction between BuildThread, ThreadStateStore, StateAutosave, and the resume logic in BuildDirector. A failure here means money lost on the next crash.

### 4.2 Test Suite Location

tests/test_smoke_recovery.py   # 29 tests, no network required

### 4.3 Test Classes and What They Prove

TestPerPRStateSave

Proves that thread_store.save() is called after each individual PR, not just after the full batch. Inspects the source code directly to verify the save call appears in the right location relative to prd_done.append(exc.spec.pr_num).

If this test fails: a 5-PR batch crash at PR 4 loses PRs 1-3.
Cost: up to $2.52 per crash.

TestResumeSkipsCorrectPRs

Proves the resume logic correctly identifies which PRs to skip. Tests the exact scenario of 5 PRs completed on a 23-PR plan — the remaining list must start at PR 6.

If this test fails: resume re-runs completed PRs, wasting tokens and
creating duplicate GitHub branches and PRs.

TestStateMachineResume

Proves thread.state is forced to pr_pipeline when pr_plans_by_prd is non-empty, regardless of what was saved. A crash during PRD approval could save state="prd_gen" — without this fix, the agent would re-generate all PRD plans on restart.

If this test fails: a crash during PRD approval triggers full PRD
regeneration on restart. Cost: $12-15 in tokens.

TestMidBatchCrashRecovery

The core scenario test. Simulates a 23-PR build where PRs 1–3 complete with per-PR saves, then crash during PR 4. Verifies: - completed_pr_nums_by_prd contains exactly {1, 2, 3} after reload - remaining list starts at PR 4, not PR 1 - Maximum loss from a pre-save crash is one full batch (not all prior batches)

TestGitHubJSONRecovery

Proves the GitHub JSON recovery path works and preserves impl_files. When local state is wiped, the agent fetches prd-XXX-pr-plan.json from the GitHub prds branch. Critically, impl_files must survive the round-trip — if it doesn’t, code generation falls back to untitled.py.

TestAutosaveDaemon

Proves three behaviors: - Autosave forces state="pr_pipeline" when PR plans exist - A None thread does not raise an exception - The patch sentinel triggers an immediate state flush

TestMidPRCheckpoints

Proves all four stage checkpoints are wired in _execute_pr_inner: branch_opened, tests_passed, committed, ci_passed. Verifies in_progress_pr survives a save/load cycle. Includes the cost analysis test that prints the financial comparison at runtime.

### 4.4 The Cost Analysis Test Output

When run, test_cost_of_no_checkpoints prints:

Cost analysis — batch of 5 PRs, crash at PR 5:
  Batch-only save (v2.0):          $2.52 lost (4 PRs)
  Per-PR save (v3.0):              $0.63 lost (1 PR max)
  Per-stage checkpoint (v3.0):     $0.18 lost (1 generation max)
  Savings vs batch-only:           $2.34 per crash

Over 150-PR build, 10 crashes: saves $23.40 in tokens

This test always passes — it is documentation that runs.

## 5. Live Smoke Tests

### 5.1 Purpose

Live smoke tests make real API calls to verify the complete pipeline before starting a build. They use real API keys, create real GitHub branches, and clean up after themselves.

Cost: approximately $0.01 per run (one Anthropic call + one OpenAI call + 3 GitHub API calls).

### 5.2 Running Live Smoke Tests

# At install — prompted after unit tests pass
python install.py
# "Run live smoke tests? [y/N]" → type Y

# Anytime after install
python install.py --smoke

# Direct pytest
PYTHONPATH=src python3 -m pytest tests/test_smoke.py -v -s

All live tests are automatically skipped if the .env file is missing or has missing API keys. Each test prints a specific diagnostic message on failure.

### 5.3 Test Coverage

TestAnthropicAPI

Test | What it validates
test_api_key_format | Key starts with sk-ant- — catches copy-paste errors
test_live_generation_call | Real API call returns SMOKE_TEST_OK
test_multi_turn_conversation | Multi-turn: rename a function across two turns — validates the fix loop’s core mechanism

The multi-turn test is the most important in this class. It verifies that a second conversation turn correctly builds on the first. If this fails, the fix loop will not work — the LLM will not remember prior context across attempts.

TestOpenAIAPI

Test | What it validates
test_api_key_format | Key starts with sk-
test_live_generation_call | Real API call returns SMOKE_TEST_OK
test_consensus_arbitration | Claude evaluates two implementations and returns valid JSON with winner field

The arbitration test verifies the consensus engine’s evaluation path. If this returns non-JSON or a missing winner field, every PR generation step will fail silently.

TestGitHubAPI

Test | What it validates
test_token_has_repo_access | Token can read the target repository
test_can_create_and_delete_branch | Token has write access
test_can_commit_file | Full write cycle: create branch → commit file → read back → delete

TestFullPipeline

The most important live test. Exercises the complete code generation → GitHub pipeline:

Make a real Anthropic + OpenAI consensus call for a smoke_check() function

Create a real branch on GitHub

Commit the generated code to the branch

Open a real draft PR

Verify the PR is in draft state

Close and delete the PR (cleanup)

If all 5 steps complete, the pipeline will work on a real build.

TestBuildMapLive

Verifies fetch_build_map() returns None gracefully when no map exists yet. This is the state for the first 5 PRs of any build — the function must not raise an exception.

### 5.4 Failure Diagnostics

Each test failure includes a specific message identifying the cause and fix:

FAILED tests/test_smoke.py::TestAnthropicAPI::test_live_generation_call
  Anthropic API timed out after 30s.
  Possible causes:
    - Network issue or firewall blocking api.anthropic.com
    - API key quota exhausted
  Check: console.anthropic.com/usage

On overall failure, a summary section prints:

SMOKE TEST FAILURES — DIAGNOSIS
================================
  Anthropic failures: check ANTHROPIC_API_KEY, CLAUDE_MODEL, console.anthropic.com/usage
  OpenAI failures:    check OPENAI_API_KEY, OPENAI_MODEL, platform.openai.com/usage
  GitHub failures:    check GITHUB_TOKEN (needs 'repo' scope), GITHUB_OWNER, GITHUB_REPO
  Paste the full failure output to your engineer for diagnosis.

## 6. Install Integration

### 6.1 Unit Tests at Install — Mandatory

Unit tests run automatically as part of python install.py. They are not optional and cannot be skipped. The install runs:

PYTHONPATH=src python3 -m pytest tests/ -v --tb=short -x

The -x flag stops on first failure so the output is readable. On failure:

⚠  Tests failed. The agent may not work correctly.
   Fix the failures above before running a build.
   To re-run tests: PYTHONPATH=src python3 -m pytest tests/ -v

On success:

✓  Pre-flight tests passed — ready to build

### 6.2 Live Smoke Tests at Install — Recommended

After unit tests pass, the installer prompts:

─────────────────────────────────────────────────────
OPTIONAL: Live smoke test (recommended for first install)
  Tests real Anthropic, OpenAI, and GitHub connectivity.
  Creates and deletes one test PR. Costs ~$0.01 in tokens.
─────────────────────────────────────────────────────
Run live smoke tests now? [y/N]

Defaulting to N allows fast reinstalls and patch applications. For a first install or after changing API keys, the answer should be Y.

### 6.3 Command Reference

Command | When to use
python install.py | Fresh install or after wiping agent directory
python install.py --test | Re-run unit tests only (no install steps)
python install.py --smoke | Re-run live smoke tests only
PYTHONPATH=src python3 -m pytest tests/ -v | Full test suite directly
PYTHONPATH=src python3 -m pytest tests/test_smoke_recovery.py -v -s | Recovery tests with printed output
PYTHONPATH=src python3 -m pytest tests/test_smoke.py -v -s | Live tests with printed output

### 6.4 When to Run Smoke Tests

Event | Recommended action
Fresh install | Run --smoke
After changing any API key in .env | Run --smoke
After applying a patch | Run --test
Before starting a new build | Run --test (smoke optional)
Build failing unexpectedly | Run --smoke to rule out connectivity
After GitHub token rotation | Run --smoke

## 7. Test-Driven Development for the Agent Itself

The Forge Dev Agent builds other software from TRDs. When new features are added to the agent itself, the same test philosophy applies:

Write a failing test that describes the expected behavior

Implement the feature

Verify the test passes

Add to the recovery/smoke test suite if the feature affects state or APIs

The agent’s own test coverage documents every non-obvious behavior. When a bug is fixed, the fix must include a test that would have caught the original bug. The history of this test suite is the history of the agent’s failure modes.

## 8. Non-Functional Requirements

Requirement | Target
Unit test suite runtime | < 60 seconds
Recovery smoke test runtime | < 20 seconds
Live smoke test runtime | < 120 seconds
Live smoke test cost | < $0.05 per run
Unit test suite: no network calls | Enforced — all external deps mocked
Test isolation | Each test must clean up after itself
Test determinism | No test may depend on external state or prior test order
Coverage of new features | Every new fix must include a regression test

## 9. Acceptance Criteria

☒ Unit tests run automatically at install with PYTHONPATH=src

☒ Unit test failure blocks build with clear diagnostic output

☒ Recovery tests cover per-PR save, stage checkpoints, GitHub JSON recovery

☒ Live smoke tests cover Anthropic multi-turn, OpenAI arbitration, GitHub write, full E2E pipeline

☒ All live tests skip gracefully when .env is missing or incomplete

☒ Each test failure prints a specific actionable diagnostic message

☒ python install.py --test and --smoke flags available for on-demand runs

☒ Cost analysis test documents financial rationale for checkpoints

☐ thread_state.py dedicated test file (v2.0 target)

☐ ci_checker.py dedicated test file (v2.0 target)

☐ Test coverage reporting (pytest --cov) integrated into CI workflow (v2.0 target)

## Appendix A: Test File Summary

File | Tests | Network | Cost
test_audit.py | Unit | None | $0
test_build_director.py | Unit | None | $0
test_build_map.py | Unit | None | $0
test_consensus.py | Unit | None | $0
test_document_store.py | Unit | None | $0
test_e2e.py | Integration | Localhost only | $0
test_failure_handler.py | Unit | None | $0
test_github_tools.py | Unit | None (mocked) | $0
test_integration.py | Integration | None (mocked) | $0
test_path_security.py | Unit | None | $0
test_prd_planner.py | Unit | None | $0
test_pre_pr_review.py | Unit | None | $0
test_sandbox.py | Unit | None | $0
test_smoke_recovery.py | Recovery | None (partial mock) | $0
test_smoke.py | Live | Anthropic + OpenAI + GitHub | ~$0.01
test_test_runner.py | Unit | None | $0

## Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-20 | YouSource.ai | Initial document — complete testing strategy extracted from March 2026 build sprint