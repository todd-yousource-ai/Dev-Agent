# AGENTS.md — Crafted Dev Agent

Instructions for AI agents working in this repository. Read this before making any change.

---

## Repository Identity

**Product:** Crafted Dev Agent — a native macOS AI coding agent.
**Architecture:** Two-process. Swift shell (UI, auth, Keychain, XPC) + Python backend (consensus, pipeline, GitHub).
**Specification:** 16 TRDs in `forge-docs/`. They are the source of truth. Code must match them.
**Security model:** TRD-11 governs all components. Read it before touching security-relevant code.
**Current version:** 38.153.0

---

## Before You Write Any Code

1. **Find the TRD that owns the component you are modifying.** Check the TRD Index in `README.md`.
2. **Read the relevant TRD sections** — especially: interfaces, error contracts, security, testing requirements.
3. **Check TRD-11** if your change touches credentials, external content, generated code, or CI.
4. **Run the existing tests** before making changes: `cd src && pytest ../tests/ -v --tb=short`

---

## Repository Structure

```
forge-docs/                      ← ALL TRDs and PRDs live here. Read before building.
  TRD-1-macOS-Application-Shell.docx
  TRD-2-Consensus-Engine.docx
  TRD-3-Build-Pipeline.docx
  TRD-4-Multi-Agent-Coordination.docx
  TRD-5-GitHub-Integration.docx
  TRD-6-Holistic-Code-Review.docx
  TRD-7-TRD-Development-Workflow.docx
  TRD-8-UIUX-Design-System.docx
  TRD-9-Mac-CI-Runner.docx
  TRD-10-Document-Store.docx
  TRD-11-Security-Threat-Model.docx
  TRD-12-Backend-Runtime-Startup.docx
  TRD-13-Recovery-State-Management.docx
  TRD-14-Code-Quality-CI-Pipeline.docx
  TRD-15-Agent-Operational-Runbook.docx
  TRD-16-Agent-Testing-and-Validation.docx

forge-standards/                 ← Coding standards, interface contracts, decisions
  ARCHITECTURE.md
  INTERFACES.md
  DECISIONS.md
  CONVENTIONS.md
  build_rules.md                 ← Auto-generated per-run coding rules (from build_rules.py)

src/                             ← Python backend
  agent.py                       ← Entry point, REPL, version
  build_director.py              ← Pipeline orchestration — confidence gate, pr_type routing
  consensus.py                   ← ConsensusEngine — parallel generation + arbitration
  providers.py                   ← ClaudeProvider, OpenAIProvider
  build_ledger.py                ← BuildLedger — multi-engineer coordination
  github_tools.py                ← GitHubTool — all GitHub API calls
  document_store.py              ← DocumentStore — embeddings, FAISS, retrieval
  ci_workflow.py                 ← crafted-ci.yml and crafted-ci-macos.yml generation
  config.py                      ← AgentConfig — all configuration
  api_errors.py                  ← classify_api_error(), is_transient_error()
  path_security.py               ← validate_write_path() — must be called before every write
  build_memory.py                ← BuildMemory — cross-run PR note persistence (workspace/)
  build_rules.py                 ← BuildRulesEngine — derives coding rules from build history
  context_manager.py             ← ContextManager — fix loop history trimming at 30k tokens
  failure_handler.py             ← FailureHandler — fix loop, _choose_strategy(), _score_fix()
  lint_gate.py                   ← LintGate — ast → ruff → import pre-test pipeline
  self_correction.py             ← SelfCorrectionLoop — LLM self-review before tests
  repo_context.py                ← RepoContextFetcher — existing file content before generation
  pr_planner.py                  ← PRPlanner, PRSpec (pr_type field), PR_LIST_SYSTEM
  prd_planner.py                 ← PRDPlanner — PRD decomposition
  thread_state.py                ← ThreadStateStore — per-PR stage checkpoints
  ci_checker.py                  ← CIChecker — GitHub Actions polling
  pr_review_ingester.py          ← PR review comment ingestion
  repo_bootstrap.py              ← Repository first-use setup
  audit.py                       ← AuditLogger — build event recording
  branch_scaffold.py             ← Branch setup (standards, build map)
  build_map.py                   ← Build interface map — signatures across PRs
  notifier.py                    ← EmailNotifier — batch complete, CI failure alerts
  recover.py                     ← Recovery tool
  FAILURE_TAXONOMY.md            ← 7 FM root cause buckets — v39 no-regression contract

Crafted/                         ← Swift/SwiftUI application shell (TRD-1)
CraftedTests/                    ← XCTest suites (TRD-9)
tests/                           ← Python test suite (17 files)
  test_regression_taxonomy.py    ← 35 regression tests — FM-1 through FM-7 contract
.github/workflows/
  crafted-ci.yml                 ← Ubuntu CI (Python, Go, TypeScript, Rust)
  crafted-ci-macos.yml           ← Mac CI (Swift, xcodebuild) — requires self-hosted runner
conftest.py                      ← src/ import resolution for pytest (auto-committed by ci_workflow)
```

---

## The Core Loop

When `/prd start <intent>` is called:

```
ConfidenceGatedScope → PRDPlanStage → PRDGenStage → PRPlanStage
    → for each PR:
        RepoContextFetch → SelfCorrection → LintGate → CodeGenStage
        → FixLoop (_choose_strategy) → CIGateStage → OperatorGateStage
```

Each stage is a separate class. Max cyclomatic complexity 15 per function. State checkpointed after every stage via `ThreadStateStore`. Never modify the stage sequence — it is in TRD-3.

**PR type routing:** PRSpec.pr_type ("implementation" | "documentation" | "test") controls which stages run. Documentation PRs skip the test loop entirely. Test-only PRs skip the local loop and defer to CI after dependency PRs merge.

---

## Scope Confidence Gate

The scope phase now gates on document coverage quality before expensive PRD generation begins:

```python
# SCOPE_SYSTEM returns confidence (0–100) and coverage_gaps
# _stage_scope gates at _CONFIDENCE_THRESHOLD = 85
# Below threshold: shows gaps, offers proceed/answer/cancel
# One-shot re-scope if operator provides gap answers — no loop
```

---

## Consensus Engine Usage

Always pass language:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

`language="swift"` selects `SWIFT_GENERATION_SYSTEM` + optional `SWIFT_UI_ADDENDUM` (injected when UI keywords detected).
`language="python"` selects `GENERATION_SYSTEM` — security-focused Python rules.

Fix loop strategy is now failure-type-aware via `_choose_strategy(failure_type, attempt, records)` — not a static lookup table. Fix arbitration uses `_score_fix()` based on assertion token overlap — not response length.

Never call providers directly from pipeline code. Always go through `ConsensusEngine.run()`.

---

## Document Store Usage

```python
# Context for generation (primary use case)
ctx = self._doc_store.auto_context(
    query=f"{thread.subsystem} {spec.title}",
    project_id=project_id,
    doc_filter=thread.relevant_docs or None,   # restrict to relevant TRDs
    max_chars=24_000,
)

# Load a specific document (e.g. PRODUCT_CONTEXT.md)
content = self._doc_store.get_document_content("PRODUCT_CONTEXT.md", project_id)
```

`auto_context()` returns text already wrapped in injection-defense delimiters. Append it to the user prompt — never the system prompt. Build rules (build_rules.md in Mac-Docs) are loaded automatically alongside TRDs.

---

## Build Memory and Build Rules

```python
# build_memory.json — survives fresh installs, thread state wipes
# Location: workspace/{engineer_id}/build_memory.json
# Written: after every successful PR via build_memory.record_pr()
# DO NOT delete on clean runs — cross-run learning is intentional

# build_rules.md — self-improving coding rules derived from build history
# Location: Mac-Docs/build_rules.md (loaded by DocumentStore automatically)
# Written: after each build run when 3+ recurring failure patterns found
# DO NOT delete on clean runs unless switching to a completely new codebase
```

---

## GitHub Operations

```python
# ALL GitHub ops go through GitHubTool. Never use the GitHub API directly.
self._github.commit_file(branch, path, content, message)
self._github.create_pr(branch, title, body)
self._github.get_file(path)

# Validate paths before ANY write
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
```

Branch naming convention (mandatory — kept intentionally as forge-agent for compatibility):
`forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

CI workflow files: `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift).
conftest.py is auto-committed by `ci_workflow.ensure()` for src/ import resolution.

---

## Error Handling Patterns

**Transient API errors (529, 500):**
```python
# In failure_handler.py: _choose_strategy(failure_type, attempt, records)
# Failure type is the primary signal; attempt count is secondary escalation
# assertion_error → test_driven immediately
# import_error / runtime_error → converse first, then test_driven
# attempt >= 8 → nuclear every 3rd attempt
# Never retry indefinitely — max 20 local attempts, then move on
```

**GitHub rate limits:**
```python
# 403 primary: exponential backoff (2s → 4s → 8s → 16s → 32s → 64s)
# 429 secondary: respect Retry-After header
# ETag caching on all polling endpoints
```

**Context rot in long fix loops:**
```python
# ContextManager auto-trims at 30k tokens
# Preserves spec-anchor first turn + last 6 messages
# CI log output truncated at 8k chars (70% head / 30% tail)
# No action required — automatic
```

**SECURITY_REFUSAL in LLM output:**
```python
# STOP. Do not retry. Do not rephrase.
# Emit error card. Gate. Log full prompt context.
# Operator must explicitly override.
```

---

## CI Routing

| Language | Runner | Workflow file |
|----------|--------|--------------|
| Python, Go, TypeScript, Rust | `ubuntu-latest` | `crafted-ci.yml` |
| Swift | `[self-hosted, macos, xcode, x64]` | `crafted-ci-macos.yml` |

Key CI hardening (v38.145+): PYTHONPATH at job level, exit code 5 treated as success (no tests collected), ruff errors-only (E999,F821,F811), concurrency cancel-in-progress, least-privilege permissions, pip caching.

---

## Version Management

VERSION file and `pyproject.toml` must always match. The test `TestVersionConsistency.test_version_matches_pyproject` enforces this.

When bumping version: update BOTH files.
```bash
echo "38.XX.0" > VERSION
sed -i 's/version = "38.YY.0"/version = "38.XX.0"/' pyproject.toml
```

---

## v39 No-Regression Contract

Before any v39 modular refactor ships, all 35 regression tests must pass:
```bash
pytest tests/test_regression_taxonomy.py -v
# All 35 must be green. FM-1 through FM-7 buckets covered.
```

---

## Security Checklist (Run Before Every PR)

- [ ] No hardcoded credentials, keys, or tokens in any string literal
- [ ] No `shell=True` in any subprocess call
- [ ] No `eval()` or `exec()` on any external content
- [ ] No HTTP response bodies in log statements
- [ ] All new file write paths pass through `path_security.validate_write_path()`
- [ ] All new document chunks pass through `_scan_for_injection()` before storage
- [ ] External content only in user prompt — never system prompt
- [ ] New LLM generation calls use `self._gen_system` (language-aware), not hardcoded string
- [ ] New XPC message types: unknown message types are discarded, not raised
- [ ] pyyaml present in requirements.txt (needed for CI workflow validation)

---

## What Generates What

| You want | Call this |
|----------|-----------|
| Implementation code for a PR | `ConsensusEngine.run(task, context, language)` |
| Tests for a PR | `PRPlanner.generate_tests(spec, impl_code)` |
| PRD document | `PRDPlanner.generate_prd(item, context)` |
| PR plan for a PRD | `PRPlanner.plan_prs(prd_result, thread)` |
| TRD document | `TRDWorkflow.generate_trd(session)` |
| Holistic review | `ReviewDirector.run(branch, scope, lenses)` |
| Context string for any of the above | `DocumentStore.auto_context(query, project_id)` |
| Build memory for generation context | `BuildMemory.pr_generation_injection(pr_title, impl_files, subsystem)` |
| Self-improving rules for next run | `BuildRulesEngine.analyze_and_update()` — called automatically at build completion |

---

## Critical Files — Read Before Modifying

| File | Why It Matters |
|------|---------------|
| `src/consensus.py` | Core generation loop — changes here affect every PR the agent builds |
| `src/build_director.py` | Pipeline orchestration — complexity 15 limit strictly enforced |
| `src/github_tools.py` | All GitHub I/O — path validation, rate limiting, SHA protocol |
| `src/path_security.py` | Security boundary — every write path must pass through here |
| `src/ci_workflow.py` | Generates the YAML that runs in CI — template bugs break every build |
| `src/failure_handler.py` | Fix loop strategy dispatch — _choose_strategy() is the core escalation logic |
| `src/pr_planner.py` | PRSpec + PR_LIST_SYSTEM — pr_type field drives all routing decisions |
| `src/build_memory.py` | Cross-run learning — do not clear without understanding the impact |
| `src/build_rules.py` | Self-improving rules — output goes to Mac-Docs, loaded by DocumentStore |
| `src/context_manager.py` | Fix loop history trimming — prevents context rot at 30k tokens |
| `Crafted/XPCBridge.swift` | The bridge between Swift and Python — wire protocol is TRD-1 §6 |
| `Crafted/AuthManager.swift` | Touch ID + Keychain — biometric failures must lock session, not degrade |
| `.github/workflows/crafted-ci-macos.yml` | Mac runner workflow — YAML errors break all Swift CI |

---

## Forbidden Patterns

These will fail code review. Do not write them.

```python
# FORBIDDEN: shell injection
subprocess.run(cmd, shell=True)

# FORBIDDEN: credential in log
logger.info(f"Using key: {api_key}")

# FORBIDDEN: credential in prompt
system = f"Use this key: {self._config.anthropic_api_key}"

# FORBIDDEN: direct execution of generated code
exec(result.final_code)
eval(result.final_code)

# FORBIDDEN: path traversal
open(f"../{user_input}")  # must use path_security.validate_write_path()

# FORBIDDEN: blind GitHub write (no SHA)
github.create_file(path, content)  # use commit_file() which handles SHA

# FORBIDDEN: context in system prompt
system = f"Context: {doc_store.auto_context(query)}"  # context goes in user prompt

# FORBIDDEN: ignoring SECURITY_REFUSAL
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry

# FORBIDDEN: static strategy lookup (replaced by _choose_strategy)
strategies = ["converse", "test_driven", ...]  # WRONG — use _choose_strategy()

# FORBIDDEN: length-based fix arbitration (replaced by _score_fix)
winner = max(claude_fix, openai_fix, key=len)  # WRONG — use _score_fix()
```

```swift
// FORBIDDEN: force unwrap
let value = optional!

// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)

// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```
