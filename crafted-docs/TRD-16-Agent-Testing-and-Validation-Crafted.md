# TRD-16-Agent-Testing-and-Validation-Crafted

_Source: `TRD-16-Agent-Testing-and-Validation-Crafted.docx` — extracted 2026-03-26 21:48 UTC_

---

TRD-16: Agent Testing and Validation

Technical Requirements Document — v3.1

Field | Value
Product | Crafted
Document | TRD-16: Agent Testing and Validation
Version | 3.1
Status | Updated — Confidence Gate Contract + Schema Completeness Lesson (March 2026)
Author | Todd Gould / YouSource.ai
Previous Version | v3.0 (2026-03-22)
Depends on | TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality), TRD-15 (Runbook)

# 1. Purpose and Scope

This document specifies the complete testing and validation strategy for the Crafted Dev Agent. It covers the unit test suite, integration tests, regression tests, live smoke tests, and the methodologies for validating agent behavior without running full builds.

The testing philosophy: all tests except test_smoke.py run at zero network cost and zero LLM cost. The agent must be testable without API keys. This enables CI validation on every commit and fast local iteration during development.

# 2. Testing Philosophy

## 2.1 Cost Model

Test type | Network | LLM calls | Approximate cost
Unit tests | None | $0
Integration tests (mocked) | None | None (mocked) | $0
Recovery smoke tests | None (partial mock) | None | $0
Live smoke tests | Anthropic + OpenAI + GitHub | Yes | ~$0.01 per run

## 2.2 Test Independence

Unit tests must not depend on the filesystem, network, or LLM APIs. Any test that requires these must use mocks. The conftest.py at the repo root inserts src/ into sys.path so all tests can import from src/ without PYTHONPATH being set.

## 2.3 No Side Effects

Tests must not modify real GitHub repositories, make real API calls, or write to production directories. Tests that need file system operations use tmp_path (pytest fixture) or tmp_workspace fixtures.

# 3. Unit Test Suite

## 3.1 Coverage Areas

File | Coverage area
test_audit.py | AuditLogger: JSONL write, permissions, sequence numbers, session tracking, replay
test_build_director.py | Path sanitization, slugs, parse_nums, chat print sentinels, thread state store, PRD planner decompose, path injection prevention
test_build_map.py | Module interface extraction, build map rendering, OI13 prompt constraint, multi-turn fix loop, generation context
test_consensus.py | Consensus engine run, clear winner, improvement pass, eval JSON failure, telemetry, token budget
test_document_store.py | Markdown loading, search ranking, auto-context, empty store behavior, reload
test_failure_handler.py | Failure classification, error line extraction, sanitization, missing package extraction, fix loop control
test_github_tools.py | Path/branch validation, commit_file, create_pr, list_files_recursive, download_file
test_path_security.py | validate_write_path, validate_branch_name, validate_commit_path — all boundary cases
test_prd_planner.py | PRDItem, PRDResult, PRSpec, DecompositionResult, safe_json, doc_filter
test_pre_pr_review.py | Pre-PR review: approved/needs_changes/malformed, security critical variant
test_sandbox.py | Docker detection, fallback behavior, command construction, safe env
test_test_runner.py | File write paths, workspace boundary, sensitive env filtering, language detection

# 4. Integration Tests

## 4.1 test_integration.py

Tests that exercise multiple modules together with mocked network and LLM calls:

TestDocumentGrounding — document store auto_context injection, forge context subsystem section, token budget

TestConsensusIntegration — full consensus run with document context

TestFileWriteAndValidation — write paths, workspace boundary, env var stripping, pyproject.toml scaffolding

TestGitHubPRCreation — draft PR creation, impl commit sequencing

TestFailureEscalation — failure classification, fix loop strategy selection

TestAuditTelemetry — session ID consistency, replay coverage

## 4.2 test_e2e.py

End-to-end tests that verify the system configures correctly and imports cleanly:

TestVersionConsistency — VERSION file, pyproject.toml version match, agent/ledger reads version

TestConfigLoading — .env loading, missing key exit, batch size defaults

TestBridgeDependencyCheck — bridge imports, no runtime pip install, fail-fast message

TestBridgeSecurityModel — localhost bind, DNS rebinding, httponly cookie, compare_digest, WebSocket origin

TestProviderAdapters — providers module importable, lazy import, complete call, error message

TestAgentImportChain — all src modules importable, version readable

# 5. Recovery Smoke Tests

## 5.1 test_smoke_recovery.py

Recovery tests that verify state machine behavior without network access:

TestPerPRStateSave — state saved after each PR (not just batch), completed PR nums tracked individually

TestResumeSkipsCorrectPRs — resume skips completed PRs, round-trip serialization

TestStateMachineResume — state forced to pr_pipeline when plans exist, PRD completed ids prevent regeneration

TestMidBatchCrashRecovery — crash after PR3 resumes from PR4, crash before save restores to batch start

TestGitHubJSONRecovery — resume fetches from GitHub when local empty, recovery preserves impl_files

TestAutosaveDaemon — forces pr_pipeline when plans exist, patch sentinel triggers immediate save

TestMidPRCheckpoints — checkpoint stages wired in source, in_progress_pr persists, cost of no checkpoints

# §6. Self-Correction Loop

## Purpose

The self-correction loop runs between code generation and the lint gate. It gives the LLM an opportunity to review and fix its own output before tests run — catching errors that only appear when the LLM deliberately looks for them.

## Architecture

Implemented in self_correction.py as SelfCorrectionLoop. Takes claude_fn and openai_fn callables and a max_passes cap (default 10).

Step | Description
1. Review (both models) | Claude and OpenAI each review the code: syntax → imports → logic → edge cases → spec alignment. JSON response: {verdict, issues[], summary}.
2. Merge issues | Critical/major from either model included. Minor only from Claude. Deduplicated by first 40 chars. Sorted by severity.
3. Fix (both models) | If issues found, both models generate a fix with fresh context focused on specific issues. Longer response wins.
4. Update review history | Review conversation gets 'Fixed. Here is the updated code.' message — next pass has full context of what changed.
5. Repeat | Until verdict='clean' or max_passes reached. Cap logged as warning; build proceeds with best code.

## Key Design Decisions

Review history and fix history are separate conversations. Review accumulates context across all passes. Fix calls start fresh — focused on specific issues.

10-pass cap vs 3-pass: production AI coding tools take 5–10 turns on complex code. 3 is too few. 10 balances quality with cost (~$0.30 per 10-pass session).

Does not run for Docs or Test-only PRs.

## Validation

Test | Validates
test_self_correction_clean_first_pass | Returns immediately on clean verdict, no fix calls made
test_self_correction_fixes_syntax_error | Detects and fixes unterminated string before tests run
test_self_correction_cap_respected | Stops at max_passes even if still dirty
test_self_correction_skips_docs_pr | Returns original code unmodified for docs PRs

# §7. Repo Context Fetcher

## Purpose

Fetches existing file content from GitHub before code generation. Writing with context produces far better output than writing blind.

## Fetch Strategy

Try current PR branch first — file may already exist from a prior run

Try main branch — file may exist from a completed earlier PR

For dependency PRs: scan dep branch file tree, fetch .py files (capped at 10)

Files not found: recorded as exists=False (new file — LLM writes from scratch)

## Validation

Test | Validates
test_repo_context_fetches_branch_first | Branch content preferred over main when both exist
test_repo_context_marks_new_files | Files not found on any branch get exists=False
test_repo_context_edit_instruction | has_existing_files() True triggers targeted edit instruction

# §8. Fix Loop Improvements

## §8.1 Failure Classification

classify_failure() categorizes SyntaxError and pytest collection errors as 'syntax_error'. Patterns added: 'ERROR collecting' → syntax_error; 'SyntaxError' in output → syntax_error.

## §8.2 Early Bail-Out

After 5 consecutive failures of the same type (unknown or syntax_error), the fix loop exits with passed=False rather than burning all 20 attempts. Targets the failure mode of test-only PRs checking for files from unmerged dependency PRs.

## §8.3 Test Growth Gating

Test growth (adding assertions per failed attempt) is now gated on failure type. Skipped when: failure is structural (FileNotFoundError, ModuleNotFoundError) — growing tests won't help; same failure type has appeared 3+ consecutive times at attempt 6+.

## §8 Update — Fix Loop Strategy Dispatch (Updated in v3.0)

### SP-2: _choose_strategy() — Replaces Static Lookup Table

v2.0 used a 20-element static list indexed by attempt number. A SyntaxError on attempt 6 got test_driven; an assertion error on attempt 2 got converse — both wrong. v3.0 replaces this with _choose_strategy(failure_type, attempt, records) where failure type is the primary signal:

Failure Type | Early (1–4) | Mid (5–7) | Late (8+)
compile_error / syntax_error | test_driven immediately | test_driven | nuclear every 3rd
assertion_error | test_driven | test_driven until 6, then nuclear | nuclear majority
import_error / type_error / runtime_error | converse (diagnostic reasoning) | test_driven | nuclear every 3rd
timeout / unknown | converse | test_driven | nuclear every 3rd

Hard escalation overrides type-based logic: attempt >= 8 triggers nuclear every 3rd attempt; attempt >= 15 alternates nuclear/test_driven regardless of failure type.

### SP-3: _score_fix() — Replaces Length Arbitration

v2.0 arbitrated between Claude and OpenAI fixes by preferring the longer response. Longer ≠ better. v3.0 replaces with _score_fix(code, failure_output): scores by assertion token overlap (+2 each failing assertion identifier found) and FAILED test name (+1 each). Falls back to length tiebreaker only when scores are equal. Claude wins ties.

## §8 Addendum — Confidence Gate Test Contract (New in v3.1)

The confidence-gated scope phase (TRD-3 §1c) introduces testable invariants:

Test | Validates
test_scope_gates_below_threshold | _stage_scope refuses to advance when confidence < 85 without operator override
test_scope_proceeds_on_override | Operator 'yes' at confidence gate allows build to continue with low-confidence scope
test_scope_one_shot_rescope | Gap answer triggers exactly one re-scope call — no loop
test_scope_confidence_display | Scope summary includes conf_label with correct tier (✓/⚠/✗)
test_scope_coverage_gaps_shown | coverage_gaps displayed when confidence < threshold

The one-shot re-scope path must never loop. A re-scope that returns confidence < 85 does not trigger another gate. The test must verify this invariant explicitly:

def test_scope_one_shot_rescope_no_loop(mock_claude):

# First call: confidence=70, second call: confidence=65

mock_claude.side_effect = [low_conf_response, still_low_response]

with simulate_input('my gap answer'):

result = await director._stage_scope('build everything')

# claude_json called exactly twice (initial + one re-scope)

assert mock_claude.call_count == 2

# §9. LLM Observability

## 9.1 llm_trace.log

Every LLM call written to logs/llm_trace.log in structured format showing: call number, provider, stage, PR title, system prompt, user prompt, response, token count, and duration. Always written regardless of terminal verbosity.

## 9.2 Terminal Verbosity Levels

Level | Set Via | Terminal Output | Use Case
0 — Silent | CRAFTED_LLM_VERBOSE=0 or /verbose | Nothing (prior behavior) | Background runs, CI
1 — Preview (default) | CRAFTED_LLM_VERBOSE=1 (default) | Model + stage + response first 300 chars | Normal supervised builds
2 — Full | CRAFTED_LLM_VERBOSE=2 or /verbose /verbose | Full prompt summary + full response | Debugging, diagnosing failures

## 9.3 /verbose REPL Command

/verbose (or /v) cycles through levels 0→1→2→0. /verbose N sets explicit level. Allows operators to increase verbosity when something looks wrong and reduce it when the build is flowing normally.

# §10. v38 Failure Mode Taxonomy (New in v3.0)

## Purpose

Open coding applied to the full v38.0–v38.136 patch history. Every patch was catalogued with an open code (raw observation), then grouped into axial categories (root cause buckets). Stored in FAILURE_TAXONOMY.md at the repository root.

## Seven Root Cause Buckets

ID | Bucket | Root Mechanism | Detection Signature
FM-1 | State Persistence | Write timing — saves at batch boundaries, not PR boundaries | Agent re-runs completed work after restart
FM-2 | Code Generation Quality | No pre-commit validation; CI is first to catch syntax errors | CI first to catch syntax error, not local lint gate
FM-3 | Template Placeholder Leakage | Template not evaluated before write | Literal {identifier} in committed file
FM-4 | CI Environment Mismatch | Mac assumptions in code and config, Ubuntu in CI | Passes local, fails CI — not a logic error
FM-5 | Context Window Degradation | No history trimming; unresolvable loop runs to attempt 20 | Code quality decreases over fix attempts
FM-6 | GitHub API Operation Failures | Silent non-fatal handling on critical write paths | Agent reports success, repo disagrees
FM-7 | Dependency Resolution Failure | No pre-execution dependency check | 20 identical ImportErrors on same missing module

Before any v39 modular refactor: run pytest tests/test_regression_taxonomy.py — all 35 tests must be green. Any failing test means a known FM-N failure mode has been reintroduced.

# §11. Regression Test Suite (New in v3.0)

## File

tests/test_regression_taxonomy.py — 35 tests across 8 classes. This is the v39 no-regression contract.

## Structure

Class | FM Bucket | Tests | Coverage
TestStatePersistence | FM-1 | 4 | Phase key round-trip, completed PR list reload, per-PRD tracking, build memory persistence
TestCodeGenerationQuality | FM-2 | 5 | Valid Python check, unterminated string detection, F541 f-string detection, impl_files required, pre-commit syntax
TestTemplatePlaceholder | FM-3 | 4 | YAML placeholder detection, clean YAML passes, Python braces boundary, CI workflow validation
TestCIEnvironmentParity | FM-4 | 4 | requirements.txt completeness, no Mac paths, pathlib usage, ruff config present
TestContextManagement | FM-5 | 5 | Trim at threshold, first turn preserved, failure output truncation, unresolvable bail-out, nuclear keeps system prompt
TestGitHubOperations | FM-6 | 5 | Path injection blocked, safe title passes, YAML valid before commit, placeholder in YAML detected, is_safe_path
TestDependencyResolution | FM-7 | 5 | ImportError classification, unresolvable heuristic, depends_on_prs is list, unmet dep detectable, met deps allow execution
TestBuildMemoryIntegration | FM-1 + FM-5 | 3 | CI clean rate tracked, pattern injection targets correct PR, deduplication on rerun

## Coverage Requirement

Every FM-N bucket must have at minimum 3 tests. No bucket may have zero tests at v39 release. Current suite: minimum 4 tests per bucket.

# §12. Testing Methodology Lesson — Schema Completeness (New in v3.1)

## What Was Found

During v38.147 testing, static analysis found that PR_LIST_SYSTEM JSON schema contained worked examples for 'implementation' and 'documentation' pr_type values but no example for 'test'. The model silently defaulted to 'implementation' for test-only PRs on every run.

## How It Was Caught

def test_pr_list_system_has_all_pr_type_examples():

assert '"pr_type": "implementation"' in PR_LIST_SYSTEM

assert '"pr_type": "documentation"' in PR_LIST_SYSTEM

assert '"pr_type": "test"' in PR_LIST_SYSTEM  # ← this was missing

## The General Principle

Every enum or restricted-value field in a system prompt schema must have a worked example for every valid value. The test suite should statically verify this for all system prompt schemas. A rule without an example is a rule that will be ignored under pressure. Add to TestCodeGenerationQuality in test_regression_taxonomy.py:

def test_all_pr_types_have_schema_examples(self):

"""

REGRESSION (v38.147): PR_LIST_SYSTEM had no 'test' pr_type example,

causing models to default to 'implementation' for test-only PRs.

All pr_type values must have at least one JSON schema example.

"""

from pr_planner import PR_LIST_SYSTEM

for val in ['implementation', 'documentation', 'test']:

assert f'"pr_type": "{val}"' in PR_LIST_SYSTEM, \

f'Missing example for pr_type={val!r} in PR_LIST_SYSTEM'

# Updated Test File Summary (v3.1)

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
test_regression_taxonomy.py | Regression | None | $0
test_sandbox.py | Unit | None | $0
test_smoke_recovery.py | Recovery | None (partial mock) | $0
test_smoke.py | Live | Anthropic + OpenAI + GitHub | ~$0.01
test_test_runner.py | Unit | None | $0

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — complete testing strategy extracted from March 2026 build sprint
2.0 | 2026-03-21 | Self-Correction Loop (§6), Repo Context Fetcher (§7), fix loop improvements — failure classification, early bail-out, test growth gating (§8), LLM Observability — trace log, verbosity levels, /verbose command (§9)
3.0 | 2026-03-22 | v38 failure taxonomy: 7 FM buckets, FAILURE_TAXONOMY.md (§10). Regression test suite: test_regression_taxonomy.py, 35 tests, v39 contract (§11). Fix loop: _choose_strategy() failure-type-aware dispatch; _score_fix() assertion-content scoring (§8 update).
3.1 | 2026-03-22 | Confidence gate test contract: 5 new testable invariants, no-loop invariant example (§8 addendum). Schema completeness lesson: pr_type test example gap found and fixed, general principle, regression test specified (§12).