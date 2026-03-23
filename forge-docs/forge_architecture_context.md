# Crafted Dev Agent — Architecture Context
# ─────────────────────────────────────────────────────────────────────────────
# This file is injected into EVERY code generation prompt.
# Derived from TRD-1 through TRD-16 in forge-docs/.
# The more precise this file, the better the generated code.
# Update it when TRDs change.
# ─────────────────────────────────────────────────────────────────────────────

## Platform Overview
Crafted Dev Agent is a native macOS AI coding agent. It takes a plain-language
build intent, decomposes it into an ordered sequence of pull requests, generates
implementation and tests for each PR using two LLM providers in parallel (Claude
arbitrates), runs a self-correction pass, a lint gate, and a 20-pass fix loop,
executes CI, and gates on operator approval before merging. The human is in the
loop at every gate. The agent is autonomous between gates.

Two-process architecture. Always. No exceptions:
- Swift shell (macOS app): owns UI, Touch ID, Keychain, XPC channel, process management
- Python backend: owns consensus generation, pipeline, GitHub, ledger, doc store

## Two-Process Architecture

### Swift Shell
Owns: SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric
gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.

Swift NEVER: calls LLM APIs, reads Keychain for the backend, executes generated code.

### Python Backend
Owns: ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore,
HolisticReview, TRDWorkflow, CommandRouter, BuildMemory, BuildRulesEngine,
ContextManager, LintGate, SelfCorrectionLoop, RepoContextFetcher.

Python NEVER: reads Keychain directly, accesses the UI, persists credentials to disk.

### Credential Flow
Touch ID → Swift reads Keychain → delivers via XPC `credentials` message →
Python stores in memory only. Never in env vars. Never in logs.

## XPC Wire Protocol
All messages: line-delimited JSON on a Unix socket. TRD-1 Section 6.

Message envelope (every message):
```
{ "type": "...", "id": "<UUID>", "session_id": "<UUID>", "timestamp": <ms epoch> }
```

Swift → Python: credentials, start_build, gate_response, stop, ping, write_file
Python → Swift: ready, build_card, gate_card, error_card, shutdown_ack, pong, doc_status

Max message size: 16MB. Rate limit: 100 msg/sec.
Unknown message types: DISCARD and log. Never raise. Never crash on unknown type.

Version handshake: Python sends `ready` with `agent_version` (semver) and
`min_swift_version`. Swift validates before delivering credentials.

## Backend Startup Sequence
Order is mandatory. Do not reorder. TRD-12.

1. Initialize logger
2. Start XPC server, listen on socket
3. Print FORGE_AGENT_LISTENING:{socket_path} to stdout  ← Swift reads this
4. Wait for credentials via XPC (timeout 30s — exit 1 on timeout)
5. Initialize GitHubTool with token (non-fatal on bad token — emit auth_error card)
6. Initialize ConsensusEngine with API keys (non-fatal — emit auth_error card)
7. Start DocumentStore loading in background (async — app is responsive immediately)
   — Loads all .docx TRDs from Mac-Docs including build_rules.md if present
8. Send ready message via XPC (agent_version, min_swift_version, capabilities)
9. Display build_memory startup summary if prior runs exist (💾 count, CI clean rate)
10. Display build_rules startup summary if Mac-Docs/build_rules.md exists (📋 count)
11. Enter CommandRouter event loop

## Consensus Engine
Parallel generation. Claude arbitrates. TRD-2.

```python
result = await engine.run(
    task="Implement: PaymentProcessor.process()",
    context=doc_store.auto_context(task, project_id),
    language="python",  # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

- Both models generate concurrently via asyncio.gather — never sequential
- Claude scores both implementations. Winner goes through improvement pass if score delta < 2
- language="swift" selects SWIFT_GENERATION_SYSTEM + SWIFT_UI_ADDENDUM (if UI keywords detected)
- language="python" selects GENERATION_SYSTEM (security-focused Python rules)
- On 529/overload: retry after 10s, then fall back to the other provider
- SECURITY_REFUSAL in output: STOP. Gate. Log. Never retry by rephrasing.
- Token budget enforced via OI13Gate. Hard stop — no silent overruns.

## Build Pipeline
Interleaved PRD-then-PR execution. TRD-3.

**Scope Phase (Confidence-Gated):**
- SCOPE_SYSTEM returns confidence (0–100) and coverage_gaps
- _stage_scope gates at _CONFIDENCE_THRESHOLD = 85
- Below threshold: displays gaps, offers proceed/answer/cancel
- One-shot re-scope on operator answer — no loop
- Confidence label shown in scope summary (✓ ≥90%, ⚠ 60–89%, ✗ <60%)

**PR Type Routing (PRSpec.pr_type):**
- "implementation" — full pipeline: repo context → self-correction → lint → tests → CI
- "documentation" — skip test loop and CI gate (paths-ignore handles CI at GitHub level)
- "test" — skip local loop, defer CI until dependency PRs merge

**Per-PR Code Generation Pipeline:**
1. Repo Context Fetch — existing file content from GitHub before generation
2. Build Memory Injection — prior run PR patterns injected into context
3. Self-Correction Loop — LLM reviews its own output (up to 10 passes)
4. Lint Gate — ast.parse → ruff (E999,F821,F811 only) → import check
5. Fix Loop — pytest up to 20 attempts; _choose_strategy() selects strategy by failure type
6. CI Gate — wait for crafted-ci.yml on ubuntu-latest

**Per-PR Stage Checkpoints** (crash recovery, TRD-13 §8):
branch_opened → code_generated → tests_passed → committed → ci_passed

State checkpointed in ThreadStateStore after every stage. Resume from checkpoint
on restart. Gates never auto-timeout — they wait indefinitely. No undo on gate decisions.

## Fix Loop Strategy Dispatch
_choose_strategy(failure_type, attempt, records) — TRD-16 §8.

| Failure Type | Early (1–4) | Mid (5–7) | Late (8+) |
|---|---|---|---|
| compile_error / syntax_error | test_driven immediately | test_driven | nuclear every 3rd |
| assertion_error | test_driven | test_driven until 6, then nuclear | nuclear majority |
| import_error / type_error / runtime_error | converse (diagnostic) | test_driven | nuclear every 3rd |
| timeout / unknown | converse | test_driven | nuclear every 3rd |

_score_fix(code, failure_output): +2 per assertion identifier, +1 per FAILED test name.
Falls back to length tiebreaker only when scores are equal. Claude wins ties.

## Context Manager
ContextManager prevents context rot in long fix loops. TRD-13 §9.

```python
_ctx_mgr = ContextManager(
    trigger_tokens=30_000,   # trim when estimated tokens exceed this
    keep_tail=6,             # retain last 6 messages (3 exchange pairs)
    min_savings_tokens=5_000,# skip trim if savings < this threshold
    max_failure_chars=8_000, # truncate CI log/test output to this length
)
# maybe_trim() preserves history[0] (spec-anchor) and history[-6:] (recent working context)
# truncate_failure_output() retains 70% head (root cause) / 30% tail (summary)
```

## Build Memory and Build Rules
Two cross-run learning systems. TRD-13 §10, §11.

```python
# build_memory.json — workspace/{engineer_id}/build_memory.json
# Survives: fresh installs, thread state wipes, version upgrades
# Cleared by: explicit mem.clear() call only — never automatic
# Injected at startup (summary) and into each PR's generation context

# build_rules.md — Mac-Docs/build_rules.md
# Derived: analyze_and_update() called at build completion
# Trigger: ≥3 PRs completed AND ≥1 pattern with MIN_OCCURRENCES=3
# Loaded: by DocumentStore at startup alongside TRDs (no special injection)
# Pruned: MAX_RULES_AGE=10 oldest sections pruned on each write
```

## GitHub Integration
All GitHub ops go through GitHubTool. Never call the API directly. TRD-5.

Branch naming (mandatory):
  forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}

File writes: always SHA-based updates via commit_file(). Never blind-write.
All paths: path_security.validate_write_path() before EVERY write operation.
validate_write_path() is a sanitizer — returns _DEFAULT_SAFE_PATH on rejection, does not raise.

CI workflow files: crafted-ci.yml (Ubuntu) and crafted-ci-macos.yml (macOS Swift).
conftest.py auto-committed at repo root by ci_workflow.ensure() for src/ import resolution.

PR lifecycle: open draft → commit files → CI gate → mark ready → operator gate → merge.

Rate limiting:
- 403 primary limit: exponential backoff (2s base, doubles: 2→4→8→16→32→64s)
- 429 secondary limit: respect Retry-After header exactly
- ETag caching on all polling endpoints

## Document Store
FAISS vector index. sentence-transformers all-mpnet-base-v2 (local, default). TRD-10.

```python
# Context for generation — primary use case
ctx = doc_store.auto_context(
    query="implement XPC handshake",
    project_id=project_id,
    doc_filter=["TRD-1", "TRD-12"],  # restrict to relevant TRDs (optional)
    max_chars=24_000,
)
# Returns text wrapped in injection-defense delimiters.
# Append to USER prompt — NEVER system prompt.
# build_rules.md in Mac-Docs is loaded as a standard document alongside TRDs.
```

Chunking: semantic at heading boundaries first, fixed-size with overlap as fallback.
Cache: SHA-256 per document. Changed content triggers re-embedding.
All chunks scanned for injection patterns before storage. Context wrapped in
CONTEXT_OPEN / CONTEXT_CLOSE delimiters in every prompt.

## CI Pipeline (TRD-14)
crafted-ci.yml on ubuntu-latest. Key properties:
- PYTHONPATH set at job level (every step inherits)
- Exit code 5 (no tests collected) treated as success
- ruff errors-only: E999, F821, F811 (never fail on style)
- Concurrency: cancel-in-progress=true
- permissions: {} at workflow level, contents: read at job level
- pip caching keyed on requirements.txt
- conftest.py at repo root (committed by ci_workflow.ensure()) provides src/ imports

pyyaml is a required dependency (requirements.txt) — used for CI workflow validation
before committing crafted-ci.yml to GitHub (FM-6 regression contract).

## Key Invariants (enforce in all generated code)
- Fail closed on auth, crypto, and identity errors — never degrade silently
- No silent failure paths — every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input (documents, PR comments, CI output) is untrusted and validated
- Generated code is never executed by the agent — no eval, no exec, no subprocess of generated content
- Gates wait indefinitely for operator input — no auto-approve ever
- All file writes are path-validated via path_security.validate_write_path() before execution
- Context from external documents goes in the USER prompt — never the SYSTEM prompt
- SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log
- XPC unknown message types are discarded and logged — never raised as exceptions
- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory and build rules are never cleared automatically — they are persistent learning systems

## Protocol References
- XPC wire format: line-delimited JSON, nonce-authenticated, max 16MB per message
- ready message: { agent_version, min_swift_version, capabilities[], doc_store_status }
- build_card: { card_type, stage, content, progress } — streamed to BuildStreamView
- gate_card: { gate_type, options[], description } — blocks until operator responds
- credentials: { anthropic_api_key, openai_api_key, github_token, engineer_id }
- doc_status: { doc_id, doc_name, status, chunk_count, embedded_count } — embedding progress
- ThreadStateStore checkpoint: atomic write (tmp → rename), JSON, per-BuildThread
  — in_progress_pr field carries per-PR stage checkpoint for crash recovery
- BuildLedger: { schema_version, engineers{}, prd_results[], pr_executions[], knowledge_notes[] }

## File Naming Conventions
Python backend:
  src/consensus.py            — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM+UI_ADDENDUM
  src/build_director.py       — BuildPipeline orchestration, confidence gate, pr_type routing
  src/github_tools.py         — GitHubTool, WebhookReceiver
  src/build_ledger.py         — BuildLedger, claim/release, heartbeat
  src/document_store.py       — DocumentStore, chunk(), embed(), retrieve()
  src/ci_workflow.py          — crafted-ci.yml and crafted-ci-macos.yml generation + conftest.py
  src/path_security.py        — validate_write_path() — sanitizer, returns safe default on rejection
  src/config.py               — AgentConfig — all configuration
  src/api_errors.py           — classify_api_error(), is_transient_error()
  src/providers.py            — ClaudeProvider, OpenAIProvider
  src/forge_context.py        — architecture context injection (this file's loader)
  src/failure_handler.py      — FailureHandler, _choose_strategy(), _score_fix()
  src/context_manager.py      — ContextManager — fix loop history trimming at 30k tokens
  src/build_memory.py         — BuildMemory — cross-run PR note persistence
  src/build_rules.py          — BuildRulesEngine — derives coding rules from failure history
  src/lint_gate.py            — LintGate — ast.parse → ruff → import check pipeline
  src/self_correction.py      — SelfCorrectionLoop — LLM self-review (up to 10 passes)
  src/repo_context.py         — RepoContextFetcher — existing file content before generation
  src/pr_planner.py           — PRPlanner, PRSpec (pr_type field), PR_LIST_SYSTEM
  src/prd_planner.py          — PRDPlanner — PRD decomposition
  src/thread_state.py         — ThreadStateStore — per-PR stage checkpoints
  src/ci_checker.py           — CIChecker — GitHub Actions polling with exponential backoff
  src/pr_review_ingester.py   — PR review comment ingestion into fix loop
  src/repo_bootstrap.py       — Repository first-use setup (upload TRDs, generate AGENTS.md)
  src/audit.py                — AuditLogger — build event recording (JSONL)
  src/branch_scaffold.py      — Branch setup (standards, build map, conftest.py)
  src/build_map.py            — Build interface map — class/function signatures across PRs
  src/notifier.py             — EmailNotifier — batch complete, CI failure alerts
  FAILURE_TAXONOMY.md         — 7 FM root cause buckets (FM-1 through FM-7)
  tests/test_regression_taxonomy.py — 35 tests, v39 no-regression contract
  conftest.py                 — repo root, auto-committed, provides src/ imports for pytest

Swift shell:
  Crafted/AuthManager.swift              — Touch ID, SessionState machine
  Crafted/KeychainKit/KeychainManager.swift — Keychain read/write/delete
  Crafted/XPCBridge/XPCChannel.swift    — Unix socket, wire protocol, nonce auth
  Crafted/ProcessManager.swift          — Python backend launch/monitor/restart
  Crafted/Views/NavigatorView.swift     — left panel, project + doc navigator
  Crafted/Views/BuildStreamView.swift   — center panel, card stream, auto-scroll
  Crafted/Views/ContextPanelView.swift  — right panel, 5 tabs
  Crafted/Views/GateCardView.swift      — blocking operator gate UI
  CraftedTests/                         — XCTest suites (Auth, Keychain, XPC, Process)

GitHub Actions:
  .github/workflows/crafted-ci.yml          — Ubuntu CI (Python, Go, TypeScript, Rust)
  .github/workflows/crafted-ci-macos.yml   — Mac CI (Swift, xcodebuild, self-hosted runner)
