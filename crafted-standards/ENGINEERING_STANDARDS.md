# Crafted Engineering Standards

## Core Principles
- All code must be engineered for maximum security.
- All code must be engineered for maximum performance.
- All code must be engineered for simplicity, clarity, maintainability, and traceability.
- Security, correctness, documentation, and operational integrity take priority over development speed.
- Do not introduce complexity unless it is required and justified.

## Security Requirements
- Default to secure-by-design and deny-by-default behavior.
- All trust boundaries must be explicitly identified and enforced.
- All sensitive operations must be authenticated, authorized, and fully auditable.
- All secrets, keys, tokens, and credentials must be protected in memory, at rest, and in transit.
- Never hardcode secrets, tokens, credentials, or cryptographic material.
- All external input must be treated as untrusted and validated strictly.
- All parsing must be bounds-checked and fail safely.
- All failures involving trust, identity, policy, or cryptography must fail closed.
- All administrative or policy-changing actions must generate audit logs.
- Minimize attack surface, dependencies, privileges, and exposed interfaces.
- Avoid libraries with weak maintenance history, unclear provenance, or unnecessary bloat.

## Performance Requirements
- Performance must be considered a design requirement, not a post-build optimization.
- Favor low-latency, low-overhead architectures.
- Avoid unnecessary allocations, copies, blocking calls, and serialization overhead.
- Measure hot paths, do not guess.
- Design for efficient concurrency and safe parallelism where appropriate.
- Startup time, steady-state latency, and resource usage must be explicitly evaluated.
- Dependencies that materially degrade performance must be rejected.

## Code Quality Requirements
- Code must be production-grade, not demo-grade.
- Code must be readable, deterministic, and easy to review.
- Prefer explicit behavior over magic abstractions.
- Prefer small, composable modules over large multipurpose components.
- Every major component must have clear ownership, interfaces, and failure behavior.
- Remove dead code, unused dependencies, and experimental leftovers.
- No silent failure paths.
- Cyclomatic complexity ≤ 15 per function. Refactor before you write.
- No TODOs in security-critical or runtime-critical code without tracked follow-up.

## Dependency Requirements
- Every dependency must be justified.
- Prefer mature, actively maintained, minimal dependencies.
- Prefer first-party implementation over third-party packages when the function is
  security-critical and feasible to own.
- All dependencies must be reviewed for licensing, maintenance health, CVE history,
  and transitive risk.
- Do not add a dependency for convenience if the functionality is small and can be
  safely implemented internally.
- pyyaml must remain in requirements.txt — required for CI workflow YAML validation (FM-6).

## Observability and Auditability
- All critical actions must be observable through structured logs, metrics, and telemetry.
- Logs must support forensic reconstruction without exposing secrets.
- Security-relevant events must be timestamped, attributable, and tamper-evident.
- Build with operational diagnostics from the start, not as an afterthought.

## Testing Requirements
- All security-critical logic must have unit, integration, and negative-path tests.
- Test coverage ≥ 85% on all new modules.
- Test for failure behavior, not just success behavior.
- Add regression tests for every material bug.
- Tests must not mock the logic under test — they may mock external calls.
- Exit code 5 (no tests collected) is treated as success in CI — do not add empty test files.

## Platform and Runtime Requirements
- Design for least privilege on every platform.
- Python 3.12. Type annotations on every function. Dataclasses for all structured data.
- Swift 5.9+. macOS 13.0 minimum. SwiftUI throughout — no AppKit unless TRD-1 requires it.
- async/await throughout both processes. No blocking calls on the event loop.
- Never execute generated code. No eval(), no exec(), no subprocess of generated content.

## Code Traceability and Documentation Requirements
- Every major module and security-critical function must have a documented purpose.
- Every material code path must be traceable to a TRD, design decision, or bug fix.
- Comments must explain why, assumptions, constraints, and failure behavior.
- Public interfaces and critical data flows must be documented.
- AI-generated code must meet the same review, traceability, and documentation
  standards as human-written code.

---

## Crafted Architecture Rules

These rules apply to every component in this codebase. They are hard requirements,
not guidelines. Code review must confirm compliance before any PR merges.

### Two-Process Contract
- Swift shell owns: SwiftUI interface, Touch ID, Keychain, XPC channel, process lifecycle.
- Python backend owns: ConsensusEngine, BuildPipeline, GitHubTool, DocumentStore,
  BuildLedger, BuildMemory, BuildRulesEngine, ContextManager, LintGate,
  SelfCorrectionLoop, RepoContextFetcher, AuditLogger, MemoryStore, DreamConsolidator.
- Swift MUST NEVER: call LLM APIs, read Keychain for the backend, execute generated code.
- Python MUST NEVER: read Keychain directly, access the UI, persist credentials to disk.
- All cross-process communication goes through the XPC channel. No other IPC mechanism.
- Credential flow: Touch ID → Swift reads Keychain → XPC `credentials` message →
  Python stores in memory only. Never in env vars. Never in logs.

### Consensus Engine Contract
- Both models generate concurrently via asyncio.gather — never sequential.
- Claude arbitrates. Never let the generation model also be the sole arbitrator.
- Always pass language= to ConsensusEngine.run(). Never omit it.
- Never call providers directly from pipeline code. Always go through ConsensusEngine.run().
- SECURITY_REFUSAL in output: STOP immediately. Gate. Log full prompt context.
  Never retry by rephrasing. Never route to the other provider to bypass.
- Token budget enforced via OI13Gate. Hard stop — no silent overruns.
- On 529/overload: retry once after 10s, then fall back to the other provider.

### Build Pipeline Contract
- Stage sequence in TRD-3 is mandatory. Never reorder stages.
- Per-PR pipeline: RepoContextFetch → BuildMemoryInjection → SelfCorrection →
  LintGate → FixLoop → CIGate → OperatorGate.
- State must be checkpointed in ThreadStateStore after every stage.
- Gates wait indefinitely for operator input — no auto-approve, no timeout.
- PR type routing is controlled by PRSpec.pr_type ("implementation" | "documentation" | "test").
  Documentation PRs skip test loop and CI gate. Test-only PRs defer CI to after
  dependency PRs merge. Never bypass pr_type routing.
- Fix loop maximum: 20 local attempts. Strategy dispatch via _choose_strategy(), not static lookup.
- Fix arbitration via _score_fix() based on assertion token overlap — not response length.

### Context Assembly Contract
- Context layers must be assembled in priority order so _trim_context() preserves
  highest-value content when truncation is required:
    1. MEMORY.md session rulebook (protected — never trimmed)
    2. PR spec (title, description, impl_plan, acceptance criteria)
    3. Build memory (PR patterns from this run)
    4. Crafted/platform context + OI13 constraints
    5. TRD/PRD document context (trimmable)
    6. Repo context / existing file contents (largest, trimmed first)
    7. Operational instructions (multi-file delimiters etc.)
- External document context goes in the USER prompt — NEVER the system prompt.
- All document chunks must pass injection scanning before inclusion in any prompt.

### Memory and Learning Contract
- BuildMemory (build_memory.json) records completed PR patterns per run.
  Never clear automatically. Only via explicit mem.clear() call.
- MemoryStore (logs/<engineer>/memory/) holds the dream-consolidated session rulebook
  (MEMORY.md). Updated by DreamConsolidator on signal-driven triggers.
- DreamConsolidator fires on: arbitration score delta ≥ 3, fix loop ≥ 4 attempts,
  every 5 PRs, and unconditionally at session teardown.
- MEMORY.md is a RULEBOOK, not a history log. It contains only: Architectural Invariants,
  Consensus Constraints, TRD Decisions, Active Anti-patterns.
  Never write PR completion records to MEMORY.md — that is BuildMemory's job.
- BuildRulesEngine (build_rules.md) derives self-improving coding rules from build history.
  Triggers when ≥ 3 recurring failure patterns found across ≥ 3 PRs.

### GitHub Integration Contract
- ALL GitHub operations go through GitHubTool. Never call the GitHub API directly.
- All file paths must pass path_security.validate_write_path() before any write.
  validate_write_path() returns a safe default on rejection — it does not raise.
- All file writes use SHA-based commit_file(). Never blind-write to a branch.
- Branch naming: crafted-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
- PR lifecycle: open draft → commit files → CI gate → mark ready → operator gate → merge.
- Rate limiting: 403 → exponential backoff (2s base, doubles to 64s).
  429 → respect Retry-After header exactly.

### Error Handling Contract
- All trust, identity, and security failures MUST fail closed.
- Fail closed means: reject the action, log the event, surface to caller — never silently continue.
- No swallowed exceptions in enforcement or pipeline paths. try/except/pass is forbidden
  in any non-trivial code path.
- All errors must include: component, operation, failure_reason.
- Error messages must NOT include: keys, tokens, secrets, or credentials.
- Transient API errors (529, 500): retry once after 10s, then surface — never infinite retry.

### Audit Contract
- Every material build action must generate an audit record via AuditLogger.
- Audit records are append-only JSONL. No modification or deletion.
- Audit records must NOT contain: secrets, keys, tokens, or credentials.
- Audit failures are non-fatal to agent operation but must be logged immediately.

### XPC Contract
- All messages: line-delimited JSON on Unix socket. Max 16MB per message.
- Unknown message types: DISCARD and log. Never raise. Never crash on unknown type.
- Rate limit: 100 messages/sec.
- Version handshake: Python sends `ready` with agent_version and min_swift_version.
  Swift validates before delivering credentials.
- Nonce authentication on all messages.

---

## Crafted Component Interface Contracts

Every component MUST implement these contracts. These are hard requirements
enforced at code review — not guidelines.

### ConsensusEngine Contract
Every call to ConsensusEngine.run() MUST:
- Pass task, context, and language explicitly — no defaults relied upon.
- Receive a ConsensusResult with: final_code, winner, claude_score, openai_score,
  rationale, duration_sec. All fields must be present.
- Log the result via _log_llm() for every generate, evaluate, and improve stage call.
  No LLM call is permitted to be dark (unlogged).
- Record the arbitration outcome to DreamConsolidator via record_pr_completion()
  after the PR completes.

### DocumentStore Contract
- auto_context() MUST be called with query and optional doc_filter.
- Returned context is injection-safe and wrapped in delimiters.
- Append to USER prompt only — never system prompt.
- Keyword and semantic scoring both active when OpenAI client is available.
- Cache invalidation on document content change (SHA-256 based).

### LintGate Contract
- Pipeline: ast.parse → ruff (E999, F821, F811 only) → import check.
- Ruff checks errors only — never fail on style.
- ast.parse failure is a hard stop — never commit code that fails to parse.
- Max 3 lint fix attempts before surfacing to fix loop.

### SelfCorrectionLoop Contract
- Maximum 10 passes (configurable via SELF_CORRECTION_PASSES).
- Each pass: LLM reviews its own output against spec and prior failures.
- Oscillation detection: A→B→A→B pattern triggers immediate escalation.
- Never correct the same issue more than twice without escalating strategy.

### PathSecurity Contract
- validate_write_path() MUST be called before every file write operation.
- It returns a safe default path on path traversal detection — it does not raise.
- No file write may bypass this check for any reason.
- Generated code paths are untrusted input — always validate.

### ContextManager Contract
- Trim trigger: estimated tokens > 30,000 in fix loop history.
- Preserved: history[0] (spec-anchor) + history[-6:] (last 3 exchange pairs).
- CI log output truncated at 8,000 chars (70% head / 30% tail).
- Minimum savings threshold: 5,000 tokens — skip trim if savings below this.

---

## Test Requirements Contract

- Every pipeline stage MUST have a negative test (what happens on rejection/failure).
- Every LLM call site MUST have a test verifying it writes to llm_trace.log.
- Every context assembly path MUST have a test verifying layer ordering.
- Every memory write (BuildMemory, MemoryStore) MUST have an atomicity test
  (no .tmp files left after write).
- Fix loop strategy dispatch (_choose_strategy) MUST be tested per failure type.
- Dream trigger state MUST be tested for all four trigger conditions.
- Test coverage for pipeline and enforcement paths MUST be ≥ 85%.

---

## Crafted Code Review Checklist

Before any PR is merged, a reviewer MUST confirm:
[ ] No hardcoded credentials, API keys, tokens, or secrets in any string literal
[ ] No shell=True in any subprocess call
[ ] No eval() or exec() on any external or generated content
[ ] All new file write paths pass through path_security.validate_write_path()
[ ] All new document chunks pass through injection scanning before prompt inclusion
[ ] External document context is in the USER prompt, never the SYSTEM prompt
[ ] SECURITY_REFUSAL output: stopped, gated, logged — never retried or rerouted
[ ] All new LLM call sites write to llm_trace.log (no dark calls)
[ ] New XPC message types: unknown types discarded and logged, never raised
[ ] pyyaml present in requirements.txt (FM-6 contract)
[ ] Version bumped in both VERSION file and pyproject.toml
[ ] New modules have ≥ 85% test coverage
[ ] Cyclomatic complexity ≤ 15 per function
[ ] Context assembly follows the 7-layer priority order
[ ] DreamConsolidator.record_pr_completion() called after PR completion with arbitration scores

---

## Crafted File Naming Conventions

Python backend (src/):
  consensus.py            — ConsensusEngine, generation system prompts
  build_director.py       — BuildPipeline orchestration, confidence gate, pr_type routing
  github_tools.py         — GitHubTool — all GitHub API calls
  build_ledger.py         — BuildLedger — multi-engineer coordination
  document_store.py       — DocumentStore — keyword + semantic retrieval
  ci_workflow.py          — crafted-ci.yml and crafted-ci-macos.yml generation
  config.py               — AgentConfig — all configuration
  api_errors.py           — classify_api_error(), is_transient_error()
  path_security.py        — validate_write_path() — sanitizer, returns safe default
  build_memory.py         — BuildMemory — cross-run PR note persistence
  build_rules.py          — BuildRulesEngine — derives rules from failure history
  memory_store.py         — MemoryStore — dream-consolidated session rulebook
  dream.py                — DreamConsolidator — signal-driven memory consolidation
  context_manager.py      — ContextManager — fix loop history trimming at 30k tokens
  failure_handler.py      — FailureHandler — _choose_strategy(), _score_fix()
  lint_gate.py            — LintGate — ast → ruff → import check pipeline
  self_correction.py      — SelfCorrectionLoop — LLM self-review (up to 10 passes)
  repo_context.py         — RepoContextFetcher — existing file content before generation
  pr_planner.py           — PRPlanner, PRSpec (pr_type), PR_LIST_SYSTEM
  prd_planner.py          — PRDPlanner — PRD decomposition
  thread_state.py         — ThreadStateStore — per-PR stage checkpoints
  ci_checker.py           — CIChecker — GitHub Actions polling
  pr_review_ingester.py   — PR review comment ingestion into fix loop
  audit.py                — AuditLogger — build event recording (JSONL)
  branch_scaffold.py      — Branch setup (standards, build map, conftest.py)
  build_map.py            — Build interface map — class/function signatures across PRs
  llm_trace.py            — LLM prompt/response tracing — all calls logged here
  crafted_context.py      — Architecture context loader and injection
  notifier.py             — EmailNotifier — batch complete, CI failure alerts

Swift shell (Crafted/):
  AuthManager.swift                       — Touch ID, SessionState machine
  KeychainKit/KeychainManager.swift       — Keychain read/write/delete
  XPCBridge/XPCChannel.swift             — Unix socket, wire protocol, nonce auth
  ProcessManager.swift                    — Python backend launch/monitor/restart
  Views/NavigatorView.swift              — left panel, project + doc navigator
  Views/BuildStreamView.swift            — center panel, card stream
  Views/ContextPanelView.swift           — right panel, 5 tabs
  Views/GateCardView.swift               — blocking operator gate UI
  CraftedTests/                          — XCTest suites (Auth, Keychain, XPC, Process)

GitHub Actions:
  .github/workflows/crafted-ci.yml          — Ubuntu CI (Python, Go, TypeScript, Rust)
  .github/workflows/crafted-ci-macos.yml   — Mac CI (Swift, xcodebuild, self-hosted)

Tests (tests/):
  test_consensus.py           — ConsensusEngine pipeline, arbitration, token budget
  test_build_director.py      — BuildPipeline orchestration, pr_type routing
  test_memory_dream.py        — MemoryStore, DreamConsolidator, context assembly order
  test_llm_trace_coverage.py  — LLM call site tracing coverage (no dark calls)
  test_regression_taxonomy.py — 35 regression tests, FM-1 through FM-7 contract
  FAILURE_TAXONOMY.md         — 7 FM root cause buckets — v39 no-regression contract

