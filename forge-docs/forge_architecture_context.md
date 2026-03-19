# Consensus Dev Agent — Architecture Context
# ─────────────────────────────────────────────────────────────────────────────
# This file is injected into EVERY code generation prompt.
# Derived from TRD-1 through TRD-12 in forge-docs/.
# The more precise this file, the better the generated code.
# Update it when TRDs change.
# ─────────────────────────────────────────────────────────────────────────────

## Platform Overview
Consensus Dev Agent is a native macOS AI coding agent. It takes a plain-language
build intent, decomposes it into an ordered sequence of pull requests, generates
implementation and tests for each PR using two LLM providers in parallel (Claude
arbitrates), runs a 3-pass review cycle, executes CI, and gates on operator
approval before merging. The human is in the loop at every gate. The agent is
autonomous between gates.

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
HolisticReview, TRDWorkflow, CommandRouter.

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
`min_swift_version`. Swift validates before delivering credentials. Incompatible
versions show an error card — credentials never delivered to incompatible backend.

## Backend Startup Sequence
Order is mandatory. Do not reorder. TRD-12.

1. Initialize logger
2. Start XPC server, listen on socket
3. Print FORGE_AGENT_LISTENING:{socket_path} to stdout  ← Swift reads this
4. Wait for credentials via XPC (timeout 30s — exit 1 on timeout)
5. Initialize GitHubTool with token (non-fatal on bad token — emit auth_error card)
6. Initialize ConsensusEngine with API keys (non-fatal — emit auth_error card)
7. Start DocumentStore loading in background (async — app is responsive immediately)
8. Send ready message via XPC (agent_version, min_swift_version, capabilities)
9. Enter CommandRouter event loop

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
- language="swift" selects SWIFT_GENERATION_SYSTEM (14 Swift-specific rules)
- language="python" selects GENERATION_SYSTEM (security-focused Python rules)
- On 529/overload: retry after 10s, then fall back to the other provider
- SECURITY_REFUSAL in output: STOP. Gate. Log. Never retry by rephrasing.
- Token budget enforced via OI13Gate. Hard stop — no silent overruns.

## Build Pipeline Stages
8 stages. Each is a separate class. Max cyclomatic complexity 15 per function. TRD-3.

- Stage 1: ScopeStage        — confirms subsystem, relevant docs, branch prefix
- Stage 2: PRDPlanStage      — decomposes intent into ordered PRD list
- Stage 3: PRDGenStage       — generates each PRD document (consensus)
- Stage 4: PRPlanStage       — decomposes each PRD into ordered PR specs
- Stage 5: CodeGenStage      — generates implementation + tests (consensus)
- Stage 6: ThreePassReview   — correctness → performance → security (per PR)
- Stage 7: CIGateStage       — local tests, ruff/mypy/swiftc, CI webhook wait
- Stage 8: OperatorGateStage — blocks until operator approves, corrects, or stops

State checkpointed in ThreadStateStore after every stage. Resume from checkpoint
on restart. Gates never auto-timeout — they wait indefinitely. No undo on gate decisions.

## GitHub Integration
All GitHub ops go through GitHubTool. Never call the API directly. TRD-5.

Branch naming (mandatory):
  forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}

File writes: always SHA-based updates via commit_file(). Never blind-write.
All paths: path_security.validate_write_path() before EVERY write operation.

PR lifecycle: open draft → commit files → CI gate → mark ready → operator gate → merge.

Rate limiting:
- 403 primary limit: exponential backoff starting at 60s
- 429 secondary limit: respect Retry-After header exactly
- ETag caching on all polling endpoints

## Multi-Agent Coordination
Multiple engineers, same repo, no collision. TRD-4.

- BuildLedger stored at: forge-docs/BUILD_LEDGER.json on default branch
- Claim protocol: optimistic locking via SHA-based commits
- Heartbeat: 30s interval. Dead agents detected after 90s silence.
- Conflict detection: file overlap warnings before and after PR execution

## Document Store
FAISS vector index. sentence-transformers all-mpnet-base-v2 (local, default). TRD-10.

```python
# Context for generation — primary use case
ctx = doc_store.auto_context(
    query="implement XPC handshake",
    project_id=project_id,
    doc_filter=["TRD-1-v1.1", "TRD-12"],  # restrict to relevant TRDs (optional)
    max_chars=24_000,
)
# Returns text wrapped in injection-defense delimiters.
# Append to USER prompt — NEVER system prompt.
```

Chunking: semantic at heading boundaries first, fixed-size with overlap as fallback.
Cache: SHA-256 per document. Changed content triggers re-embedding.
All chunks scanned for injection patterns before storage. Context wrapped in
CONTEXT_OPEN / CONTEXT_CLOSE delimiters in every prompt.

## Endpoint Memory Budget (OI-13)
No fixed memory budget constraint for this product.
OI13Gate is used for per-session token spend limits only — not memory allocation.
ENDPOINT_MEMORY_BUDGET_MB = None

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

## Protocol References
- XPC wire format: line-delimited JSON, nonce-authenticated, max 16MB per message
- ready message: { agent_version, min_swift_version, capabilities[], doc_store_status }
- build_card: { card_type, stage, content, progress } — streamed to BuildStreamView
- gate_card: { gate_type, options[], description } — blocks until operator responds
- credentials: { anthropic_api_key, openai_api_key, github_token, engineer_id }
- doc_status: { doc_id, doc_name, status, chunk_count, embedded_count } — embedding progress
- ThreadStateStore checkpoint: atomic write (tmp → rename), JSON, per-BuildThread
- BuildLedger: { schema_version, engineers{}, prd_results[], pr_executions[], knowledge_notes[] }

## File Naming Conventions
Python backend:
  src/consensus.py            — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM
  src/build_director.py       — BuildPipeline orchestration, stage dispatch
  src/github_tools.py         — GitHubTool (24 methods), WebhookReceiver
  src/build_ledger.py         — BuildLedger, claim/release, heartbeat
  src/document_store.py       — DocumentStore, chunk(), embed(), retrieve()
  src/ci_workflow.py          — forge-ci.yml and forge-ci-macos.yml generation
  src/path_security.py        — validate_write_path() — called before every write
  src/config.py               — AgentConfig — all configuration
  src/api_errors.py           — classify_api_error(), is_transient_error()
  src/providers.py            — ClaudeProvider, OpenAIProvider, GitHubProvider
  src/forge_context.py        — architecture context injection (this file's loader)
  tests/                      — mirrors src/ structure, pytest

Swift shell:
  ForgeAgent/AuthManager.swift              — Touch ID, SessionState machine
  ForgeAgent/KeychainKit/KeychainManager.swift — Keychain read/write/delete
  ForgeAgent/XPCBridge/XPCChannel.swift    — Unix socket, wire protocol, nonce auth
  ForgeAgent/ProcessManager.swift          — Python backend launch/monitor/restart
  ForgeAgent/Views/NavigatorView.swift     — left panel, project + doc navigator
  ForgeAgent/Views/BuildStreamView.swift   — center panel, card stream, auto-scroll
  ForgeAgent/Views/ContextPanelView.swift  — right panel, 5 tabs
  ForgeAgent/Views/GateCardView.swift      — blocking operator gate UI
  ForgeAgentTests/                         — XCTest suites (Auth, Keychain, XPC, Process)

GitHub Actions:
  .github/workflows/forge-ci.yml          — Ubuntu CI (Python, Go, TypeScript, Rust)
  .github/workflows/forge-ci-macos.yml   — Mac CI (Swift, xcodebuild, self-hosted runner)
