# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an ordered sequence of pull requests and drives each PR through generation, validation, correction, CI, and operator-gated merge.

At a subsystem level, it is responsible for:

- Decomposing a build intent into staged PR work
- Running code generation through two LLM providers in parallel
- Using Claude as the arbitration layer for generation outcomes
- Applying a self-correction pass, lint gate, and up to a 20-pass local fix loop
- Executing CI for produced changes
- Stopping on explicit operator gates before merge
- Streaming build state and gating state over XPC to the macOS UI
- Persisting cross-run learning through build memory and build rules
- Incorporating external document context through the document store
- Performing GitHub operations exclusively through `GitHubTool`

The subsystem is explicitly human-in-the-loop. Gates block indefinitely for operator input; there is no auto-approve path.

Relevant implementation anchors named in the TRDs:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM` + `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py`

## Component Boundaries

### Inside the subsystem

The subsystem includes the orchestration and policy-bearing logic for:

- Build pipeline coordination
- Scope confidence gating
- Consensus-based generation
- Document-backed generation context loading
- Build memory persistence
- Build rules persistence and reuse
- GitHub interaction through the approved tool surface
- Failure handling and retry strategy selection
- XPC protocol emission and handling for UI coordination
- Per-PR checkpointing for crash recovery

### Outside the subsystem

The subsystem does not own:

- Direct execution of generated code as agent instructions
- Any policy that would allow auto-approval at gates
- Direct GitHub API calls outside `GitHubTool`
- Trust in external inputs without validation
- Resetting persistent learning artifacts on normal cleanup
- Rewriting external document context into the SYSTEM prompt

### Explicit non-capabilities / forbidden behavior

The subsystem must not:

- Degrade silently on auth, crypto, or identity errors
- Swallow errors without surfacing contextual details
- Log or emit secrets in logs, errors, or generated code
- Trust PR comments, documents, or CI output without validation
- Execute generated code via `eval`, `exec`, or subprocess execution of generated content
- Bypass a `SECURITY_REFUSAL` by rephrasing or retrying around it
- Raise exceptions on unknown XPC message types; they must be discarded and logged
- Re-run completed PR stages after a crash if checkpoints indicate completion
- Clear `build_memory.json` or `build_rules.md` automatically

## Data Flow

### 1. Build intent intake

The subsystem starts from a plain-language build intent. It evaluates scope and routes work through staged PR execution.

The documented scope gate behavior is:

- `SCOPE_SYSTEM` returns:
  - `confidence` (0–100)
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- Below threshold, the operator is shown gaps and offered:
  - proceed
  - answer
  - cancel
- If the operator answers gaps, a one-shot re-scope is performed
- There is no re-scope loop

### 2. Context assembly

Generation context is assembled from trusted internal state plus validated external documents.

Document store usage is a primary context source for generation. External document context must be placed in the USER prompt, never the SYSTEM prompt.

Additional persistent context sources:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - intentionally preserved across runs
- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - intentionally preserved unless switching to a completely new codebase

### 3. Parallel generation and arbitration

For each PR, the subsystem generates implementation and tests using two LLM providers in parallel. `ConsensusEngine` performs the consensus/arbitration role, with Claude designated as the arbiter in the platform overview.

Relevant generation system definitions are housed in `src/consensus.py`:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM`
- `UI_ADDENDUM`

### 4. Validation and correction loop

After generation, the subsystem applies:

- a self-correction pass
- a lint gate
- a local fix loop with a maximum of 20 attempts

Failure strategy selection follows the documented policy in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- Primary decision signal: `failure_type`
- Secondary escalation signal: `attempt`

Defined strategy mapping:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely — max 20 local attempts, then move on

### 5. CI and external feedback handling

The subsystem executes CI and consumes CI output as untrusted external input. CI log handling is automatically constrained:

- output truncated at 8k chars
- 70% head / 30% tail

Polling and rate-limit behavior:

- ETag caching on all polling endpoints
- `403` primary: exponential backoff
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary: respect `Retry-After` header

### 6. UI/XPC reporting and gating

The subsystem communicates with the macOS UI over XPC using line-delimited JSON with nonce authentication and a maximum message size of 16 MB.

Documented message shapes:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator responds
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 7. Merge gating and completion

Before merge, the subsystem requires operator approval. Gates wait indefinitely; there is no auto-approve behavior.

After successful PR completion:

- build memory is updated via `build_memory.record_pr()`
- build rules may be updated if recurring failure patterns meet the threshold
- per-PR checkpoints prevent replaying completed stages after crashes

## Key Invariants

The following invariants are explicitly defined by the Forge architecture context and apply to this subsystem:

- Fail closed on auth, crypto, and identity errors — never degrade silently
- No silent failure paths — every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input (documents, PR comments, CI output) is untrusted and validated
- Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content
- Gates wait indefinitely for operator input — no auto-approve ever
- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Context from external documents goes in the USER prompt — never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log
- XPC unknown message types are discarded and logged — never raised as exceptions
- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory and build rules are never cleared automatically — they are persistent learning systems

Additional operational invariants from the TRDs:

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly
- Validate paths before any write
- `ContextManager` auto-trims at 30k tokens
- It preserves the spec-anchor first turn plus the last 6 messages
- Scope confidence below threshold must gate with operator-visible coverage gaps
- Re-scope after operator clarification is one-shot only
- Local repair attempts are bounded to 20 attempts

## Failure Modes

### Scope uncertainty

If `_stage_scope` receives confidence below `_CONFIDENCE_THRESHOLD = 85`, the subsystem must not proceed silently. It surfaces `coverage_gaps` and gates on operator choice:

- proceed
- answer
- cancel

A single re-scope is allowed after operator answers; repeated looping is not.

### Auth, crypto, or identity failures

These fail closed. The subsystem must stop rather than degrade behavior. Errors must surface with context.

### Security refusal from model output

If `SECURITY_REFUSAL` is produced, the subsystem must:

- stop
- gate
- log

It must not attempt bypass through rephrasing.

### Invalid or unsafe file writes

Any write not validated by `path_security.validate_write_path()` must not execute.

### Unknown XPC message types

These are not exceptional control-flow events. They are discarded and logged.

### GitHub and polling failures

Documented response handling includes:

- `403` primary rate/permission-related behavior: exponential backoff up to 64 seconds
- `429` secondary: obey `Retry-After`
- polling endpoints use ETag caching

All GitHub operations must remain within `GitHubTool`.

### Repeated local correction failures

Failure handling escalates by failure type and attempt count. Repair is bounded:

- strategy chosen by `_choose_strategy(failure_type, attempt, records)`
- max 20 local attempts
- no indefinite retry

After exhaustion, the subsystem moves on rather than looping forever.

### Crash recovery and replay prevention

Per-PR stage checkpoints prevent re-running already completed work after a crash. Failure to respect checkpoints would violate subsystem invariants.

### Context overflow

`ContextManager` trims automatically at 30k tokens while preserving:

- the spec-anchor first turn
- the last 6 messages

This constrains context growth without dropping the anchoring structure.

### Secret leakage risk

Secrets in logs, error text, or generated code are prohibited. Any code path that would surface credentials or tokens is a subsystem violation.

## Dependencies

### Internal components named in the TRDs

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- `GitHubTool` in `src/github_tools.py`
- `WebhookReceiver` in `src/github_tools.py`
- `build_memory.record_pr()`
- `DocumentStore`
- `ContextManager`
- `failure_handler.py` with `_choose_strategy(...)`
- `path_security.validate_write_path()`

### Persistent stores and files

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External services / protocols

- Two LLM providers used in parallel
- GitHub, mediated exclusively via `GitHubTool`
- XPC transport using:
  - line-delimited JSON
  - nonce authentication
  - 16 MB max per message

### UI protocol dependencies

- `BuildStreamView` consumes streamed `build_card` messages
- operator gating depends on `gate_card` request/response flow
- startup capability negotiation depends on `ready`
- credentials provisioning depends on `credentials`
- document ingestion/progress status depends on `doc_status`