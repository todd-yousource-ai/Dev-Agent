# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that executes the build workflow from a plain-language build intent through staged implementation, validation, CI execution, operator gating, and merge preparation.

At a subsystem level, ForgeAgent:

- decomposes a build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitration layer for consensus
- performs a self-correction pass
- runs a lint gate
- runs a 20-pass local fix loop
- executes CI
- blocks on operator approval before merge

ForgeAgent is explicitly human-gated. It does not auto-approve progression at gates, and it waits indefinitely for operator input when a gate is presented.

The subsystem also maintains persistent learning artifacts:

- `build_memory.json` — cross-run PR history and learning state
- `build_rules.md` — self-improving coding rules derived from recurring build failures

These artifacts are intentionally persistent and are not automatically cleared on clean runs.

## Component Boundaries

ForgeAgent is bounded by the components and responsibilities identified in the TRD.

### In scope

#### Build orchestration
`src/build_director.py` contains BuildPipeline orchestration, including:

- staged build progression
- confidence gate behavior
- PR type routing

Relevant scope gating behavior:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- if below threshold, ForgeAgent shows gaps and offers:
  - proceed
  - answer
  - cancel
- if the operator provides gap answers, ForgeAgent performs one one-shot re-scope only; it does not loop indefinitely on re-scoping

#### Consensus and generation
`src/consensus.py` contains:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

ForgeAgent uses two LLM providers in parallel for generation and uses consensus/arbitration to select or refine output.

#### GitHub operations
`src/github_tools.py` contains:

- `GitHubTool`
- `WebhookReceiver`

All GitHub operations are routed through `GitHubTool`. Direct GitHub API usage is out of bounds for other subsystem code.

#### Build state persistence
`src/build_ledger.py` is referenced as part of the backend file naming set and participates in subsystem state tracking.

The subsystem also relies on per-PR stage checkpoints to prevent replaying completed work after a crash.

#### Document and memory context
ForgeAgent uses a document store for generation context and loads persistent build learning from:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

`build_memory.json`:

- survives fresh installs
- survives thread state wipes
- is written after every successful PR via `build_memory.record_pr()`
- must not be deleted on clean runs

`build_rules.md`:

- is loaded automatically by `DocumentStore`
- is written after each build run when 3 or more recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

### Out of scope / explicitly not permitted

ForgeAgent does **not**:

- execute generated code
- use `eval`
- use `exec`
- run subprocesses from generated content
- place external document context into the SYSTEM prompt
- bypass a `SECURITY_REFUSAL` by rephrasing
- degrade silently on authentication, cryptography, or identity failures
- raise exceptions for unknown XPC message types

Unknown XPC message types are discarded and logged.

## Data Flow

### 1. Session establishment over XPC
ForgeAgent communicates over an XPC wire protocol with these constraints:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

A `ready` message is emitted with:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

### 2. Credential intake
ForgeAgent receives credentials in a `credentials` payload containing:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Credentials are security-sensitive inputs and must never appear in logs, error messages, or generated code.

### 3. Intent intake and scoping
ForgeAgent receives a plain-language build intent and enters the scope phase.

Scoping uses `SCOPE_SYSTEM`, which returns:

- `confidence`
- `coverage_gaps`

`_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.

If confidence is below threshold:

- ForgeAgent presents the gaps
- it offers `proceed`, `answer`, or `cancel`
- if the operator answers, a single re-scope pass is performed
- no iterative re-scope loop is allowed

### 4. Context assembly
ForgeAgent assembles context from:

- repository state
- document store content
- build memory
- build rules
- external documents as needed

External context is treated as untrusted input and validated.

Prompt placement rule:

- context from external documents goes in the USER prompt
- never in the SYSTEM prompt

Document-related status can be surfaced as `doc_status` records:

- `doc_id`
- `doc_name`
- `status`
- `chunk_count`
- `embedded_count`

### 5. PR decomposition and generation
ForgeAgent decomposes the build into an ordered PR sequence.

For each PR, it:

- generates implementation and tests using two LLM providers in parallel
- uses `ConsensusEngine` for arbitration
- performs self-correction
- applies lint gating
- enters the local fix loop

### 6. Local correction loop
ForgeAgent performs at most 20 local attempts.

Failure handling is driven by `failure_handler.py` strategy selection:

- `_choose_strategy(failure_type, attempt, records)`

Policy:

- failure type is the primary signal
- attempt count is the secondary escalation signal
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- after 20 local attempts, move on

### 7. CI and polling behavior
ForgeAgent executes CI and handles remote interaction with the following controls:

- `403` primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary: respect `Retry-After`
- ETag caching on all polling endpoints

CI log output is truncated automatically to 8k characters:

- 70% head
- 30% tail

No operator action is required for that truncation behavior.

### 8. Operator gating and UI stream
ForgeAgent streams progress via `build_card`:

- `card_type`
- `stage`
- `content`
- `progress`

These are streamed to `BuildStreamView`.

When operator intervention is required, ForgeAgent emits `gate_card`:

- `gate_type`
- `options[]`
- `description`

A gate blocks indefinitely until the operator responds. There is no auto-approve path.

### 9. Persistence and crash recovery
ForgeAgent records per-PR stage checkpoints so that, after a crash, completed work is not re-run.

Persistent learning state updates include:

- `build_memory.record_pr()` after every successful PR
- `build_rules.md` updates after build runs with 3+ recurring failure patterns

## Key Invariants

The subsystem enforces the following invariants.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the flow must stop, gate, and log.

### File and path safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Validate paths before any write.

### Prompt and model context discipline

- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.

### Protocol robustness

- XPC unknown message types are discarded and logged, never raised as exceptions.
- XPC messages are line-delimited JSON, nonce-authenticated, and limited to 16 MB per message.

### Recovery and persistence

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### Context management

- `ContextManager` auto-trims at 30k tokens.
- It preserves the spec-anchor first turn plus the last 6 messages.

## Failure Modes

### Scope confidence failure
If scope confidence is below `_CONFIDENCE_THRESHOLD = 85`, ForgeAgent does not silently proceed as if fully scoped.

Behavior:

- presents `coverage_gaps`
- gates on operator choice
- allows one re-scope after operator answers
- otherwise proceeds or cancels based on explicit operator action

### Authentication, cryptography, or identity failure
These are fail-closed failures.

Behavior:

- do not continue in degraded mode
- surface the error with context
- do not silently substitute fallback identity/auth behavior

### Security refusal
If model output produces `SECURITY_REFUSAL`, ForgeAgent must not attempt prompt rephrasing to bypass it.

Behavior:

- stop
- gate
- log

### Unknown XPC message type
An unrecognized XPC message type is treated as a protocol-level discard case, not an exceptional crash path.

Behavior:

- discard
- log
- do not raise as exception

### Path validation failure
If `path_security.validate_write_path()` fails, the write must not execute.

### Generation or correction failure
Within the local correction loop:

- strategy selection depends on `failure_type`
- escalation depends on `attempt`
- retries are capped at 20 attempts

Specific routing:

- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- at `attempt >= 8`, every 3rd attempt may escalate to `nuclear`

### Rate limiting and remote access failure
Polling and API interaction failures are handled with bounded retry control:

- `403` primary → exponential backoff up to 64 seconds
- `429` secondary → obey `Retry-After`
- polling endpoints use ETag caching

### Context overrun
If context grows too large, `ContextManager` trims automatically at 30k tokens while preserving:

- the spec-anchor first turn
- the last 6 messages

### CI log overload
CI log output is truncated to 8k characters using a 70/30 head/tail split.

This is automatic and prevents oversized context insertion.

## Dependencies

ForgeAgent depends on the following subsystem-local and external interfaces named in the TRD.

### Internal code modules

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate behavior
  - PR type routing
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
- `ContextManager`
- `DocumentStore`
- `build_memory.record_pr()`

### Persistent data and documents

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External providers and services

- Anthropic provider access via `anthropic_api_key`
- OpenAI provider access via `openai_api_key`
- GitHub access via `github_token`

### Protocol and UI contracts

- XPC wire format
- `ready` message
- `build_card` streamed to `BuildStreamView`
- `gate_card`
- `credentials`
- `doc_status`

### Boundary rule on GitHub integration

All GitHub operations must go through `GitHubTool`. Never use the GitHub API directly.