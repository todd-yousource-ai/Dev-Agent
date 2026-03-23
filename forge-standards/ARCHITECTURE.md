# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS AI coding agent. It owns the full build lifecycle from operator intent through scoped planning, pull-request decomposition, code generation, validation, CI execution, operator gating, and merge progression.

At a high level, this subsystem:

- Accepts a plain-language build intent from the operator.
- Establishes repository-aware context from documents and persistent build learning.
- Performs scope analysis and enforces a confidence gate before implementation begins.
- Decomposes work into an ordered sequence of PRs with per-PR stage checkpoints.
- Runs dual-provider code generation and arbitration through the consensus engine.
- Applies self-correction, linting, and bounded fix-loop remediation.
- Executes CI and surfaces results with truncation and context preservation rules.
- Blocks for explicit operator approval at required gates; it never auto-approves.
- Persists build memory and build rules across runs as a deliberate learning system.

This subsystem is the primary coordinator for build execution, but it is not a free-form executor. It enforces strict trust, path, auth, and gating constraints defined by Forge-wide invariants.

## Component Boundaries

FullPlatform is a coordination subsystem. It composes other capabilities, but does not bypass their interfaces.

### In Scope

- Build lifecycle orchestration.
- PR sequencing and stage progression.
- Scope-confidence evaluation and operator gating.
- LLM generation coordination via consensus.
- DocumentStore-backed context retrieval for generation.
- Persistent build learning integration:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- CI result handling and bounded remediation loops.
- Build/gate card emission to the UI transport.
- GitHub operations through the approved abstraction.

### Out of Scope

- Direct execution of generated code content.
- Direct GitHub API usage outside `GitHubTool`.
- Arbitrary filesystem writes without path validation.
- Silent recovery from identity, auth, or crypto failures.
- Automatic operator approval or timeout-based advancement.
- Mutation or deletion of persistent learning artifacts during normal clean runs.

### Primary Internal Modules

Based on the repository mapping provided:

- `src/build_director.py`
  - Primary orchestration entrypoint.
  - Owns `BuildPipeline`, confidence gating, PR-type routing, and stage coordination.
- `src/consensus.py`
  - `ConsensusEngine`.
  - Holds generation system prompts and provider arbitration behavior.
- `src/github_tools.py`
  - `GitHubTool`, `WebhookReceiver`.
  - Sole authorized path for GitHub operations.
- `src/build_ledger.py`
  - Per-PR progress/checkpoint persistence and crash-safe resumability.

### External Interfaces

- XPC wire protocol:
  - Line-delimited JSON.
  - Nonce-authenticated.
  - Maximum 16 MB per message.
- UI streaming messages:
  - `build_card: { card_type, stage, content, progress }`
  - `gate_card: { gate_type, options[], description }`
- Session/bootstrap messages:
  - `ready: { agent_version, min_swift_version, capabilities[], doc_store_status }`
  - `credentials: { anthropic_api_key, openai_api_key, github_token, engineer_id }`
  - `doc_status: { doc_id, doc_name, status, chunk_count, embedded_count }`

## Data Flow

### 1. Session Initialization

FullPlatform starts after transport/session establishment over XPC. It consumes authenticated session metadata and credentials, including:

- LLM provider keys
- GitHub token
- `engineer_id`

Unknown XPC message types are discarded and logged. They are never raised as exceptions.

### 2. Context Assembly

Before implementation planning, the subsystem gathers repository and build context from:

- Operator-supplied build intent
- External documents retrieved through DocumentStore
- Persistent `build_memory.json`
- Persistent `build_rules.md`

Document-derived context is inserted into the **USER** prompt only, never the SYSTEM prompt. All external text sources are treated as untrusted input and validated/handled accordingly.

ContextManager behavior is part of effective prompt shaping:

- Auto-trims at 30k tokens
- Preserves:
  - spec-anchor first turn
  - last 6 messages

### 3. Scope Analysis and Confidence Gate

The scope stage invokes the scope system to produce:

- `confidence` in the range `0–100`
- `coverage_gaps`

`_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.

Behavior at the gate:

- If confidence is at or above threshold:
  - build proceeds.
- If below threshold:
  - gaps are shown to the operator.
  - operator options include proceed / answer / cancel.
- If the operator answers gaps:
  - one-shot re-scope occurs.
  - no iterative loop is allowed.

This gate is blocking and waits indefinitely for operator input. There is no auto-approve path.

### 4. PR Decomposition and Stage Planning

Once scope is accepted, FullPlatform decomposes the build into an ordered sequence of PRs. Each PR advances through defined stages with persisted checkpoints. Checkpoints prevent re-running already completed work after crashes or restarts.

This checkpointing is per-PR and stage-granular, making orchestration resumable and idempotent at the stage level.

### 5. Generation and Arbitration

For each PR, FullPlatform invokes the consensus workflow:

- two LLM providers generate in parallel
- Claude arbitrates between candidates
- self-correction pass is applied
- lint gate is executed
- bounded fix loop runs up to 20 local attempts

Consensus and generation prompts are sourced through the consensus module and repository-aware context.

Generated code is treated strictly as output artifacts; it is never executed by the agent through `eval`, `exec`, or subprocess execution of generated content.

### 6. Failure Handling During Remediation

Failure remediation follows typed escalation rules in `failure_handler.py`, where `_choose_strategy(failure_type, attempt, records)` uses failure type as the primary signal and attempt count as the secondary signal.

Required strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- maximum 20 local attempts, then stop and move on

This subsystem must never retry indefinitely.

### 7. GitHub and CI Operations

All GitHub operations are routed through `GitHubTool`. Direct GitHub API access is prohibited.

Polling/network handling constraints include:

- 403 on primary: exponential backoff
  - `2s → 4s → 8s → 16s → 32s → 64s`
- 429 on secondary: respect `Retry-After`
- ETag caching on all polling endpoints

CI log output is truncated to 8k characters using a `70% head / 30% tail` policy before surfacing to downstream consumers.

### 8. Operator Gate and Merge Progression

At required decision points, FullPlatform emits `gate_card` messages and blocks until the operator responds. Gates never auto-resolve.

This includes approval boundaries before merge progression. The human remains in the loop for final advancement decisions.

### 9. Persistent Learning Update

After every successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is written/updated

These files are persistent learning systems and must not be cleared automatically.

## Key Invariants

The following invariants are enforced by FullPlatform and are architectural, not optional:

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are validated via `path_security.validate_write_path()` before execution.
- External document context goes only into the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the attempted path:
  - do not bypass by rephrasing
  - stop
  - gate
  - log
- Unknown XPC message types are discarded and logged, never raised.
- Per-PR stage checkpoints prevent duplicate work after crashes.
- Build memory and build rules persist across runs and are never automatically cleared.

Additional subsystem-specific enforcement:

- Scope confidence threshold is hard-gated at 85 unless the operator explicitly chooses to proceed.
- Re-scope after operator gap answers is one-shot only.
- GitHub access is exclusively through `GitHubTool`.
- Local remediation is bounded to 20 attempts.
- CI output surfaced to prompts/UI is truncated deterministically.

## Failure Modes

### Scope Confidence Failure

Condition:
- scope confidence `< 85`

Behavior:
- surface `coverage_gaps`
- block on operator decision
- optionally perform one-shot re-scope if answers are provided
- do not silently proceed

### Auth / Crypto / Identity Failure

Condition:
- invalid or missing credentials
- nonce/authentication problems on transport
- identity mismatch

Behavior:
- fail closed
- stop affected operation
- surface contextual error
- never degrade to partial or anonymous behavior

### Document / External Input Risk

Condition:
- malformed, adversarial, or untrusted content from docs, PR comments, CI logs, or external systems

Behavior:
- validate and treat as untrusted
- never promote raw external content into the SYSTEM prompt
- if safety policy produces `SECURITY_REFUSAL`, terminate the path, gate, and log

### Path Validation Failure

Condition:
- attempted file write fails `path_security.validate_write_path()`

Behavior:
- abort write
- surface explicit error
- do not attempt alternate unvalidated path writes

### XPC Protocol Violation

Condition:
- unknown message type
- malformed line-delimited JSON
- oversized message beyond 16 MB

Behavior:
- unknown types: discard and log
- malformed/oversized messages: treat as protocol errors and surface appropriately
- never escalate unknown types as exceptions

### LLM Generation / Consensus Failure

Condition:
- provider failure
- arbitration failure
- unusable outputs
- safety refusal

Behavior:
- surface context-rich failure
- enter bounded remediation when applicable
- never execute generated output
- never suppress refusal paths

### Fix Loop Exhaustion

Condition:
- 20 local remediation attempts consumed without success

Behavior:
- stop retrying
- move to next handling path / operator-visible failure
- do not loop indefinitely

### GitHub / Network Rate Limiting

Condition:
- 403 on primary
- 429 on secondary

Behavior:
- 403 primary: exponential backoff through 64s max sequence
- 429 secondary: honor `Retry-After`
- polling endpoints use ETag caching

### Crash / Restart Mid-Build

Condition:
- process termination or subsystem crash during PR execution

Behavior:
- resume using per-PR stage checkpoints
- completed stages are not re-run
- persistent learning artifacts remain intact

## Dependencies

### Required Internal Dependencies

- `BuildPipeline` / `build_director.py`
  - orchestration and stage control
- `ConsensusEngine` / `consensus.py`
  - parallel generation and arbitration
- `GitHubTool` / `github_tools.py`
  - all GitHub interactions
- `build_ledger.py`
  - checkpoint persistence and crash recovery
- `failure_handler.py`
  - typed remediation strategy selection
- `path_security.validate_write_path()`
  - mandatory write-path validation
- ContextManager
  - prompt window trimming and preservation rules
- DocumentStore
  - repository and product context retrieval
- Build memory/rules persistence layer
  - cross-run learning state

### Required External Dependencies

- XPC transport with nonce-authenticated line-delimited JSON
- LLM providers:
  - Anthropic
  - OpenAI
- GitHub platform APIs, only via `GitHubTool`
- CI system outputs/logs as untrusted inputs
- UI consumer for streamed `build_card` and `gate_card` messages

### Dependency Constraints

- FullPlatform depends on GitHub only through `GitHubTool`.
- FullPlatform depends on external documents only through validated ingestion and USER-prompt placement.
- FullPlatform must not depend on runtime execution of generated artifacts.
- Persistent learning files are operational dependencies and must survive fresh installs, thread-state wipes, and clean runs unless intentionally switching to a completely new codebase.