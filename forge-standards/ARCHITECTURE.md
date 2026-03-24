# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that executes the build workflow from plain-language build intent through staged pull-request delivery.

At a high level, the subsystem:

- accepts a build intent
- decomposes work into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude for arbitration in consensus
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI
- blocks on explicit operator approval before merge
- persists learning artifacts across runs

Within this workflow, ForgeAgent also:

- performs a scope confidence gate before proceeding with implementation work
- incorporates repository and external document context through the document store
- maintains persistent build memory in `workspace/{engineer_id}/build_memory.json`
- maintains persistent build rules in `Mac-Docs/build_rules.md`
- checkpoints per-PR stages so completed work is not re-run after a crash
- streams build progress and gate state over XPC to the UI

The subsystem is designed as a fail-closed orchestration layer around generation, validation, CI, operator gating, and repository operations.

## Component Boundaries

ForgeAgent includes the orchestration and policy-bearing components identified in the TRD context.

### In scope

#### Build orchestration
- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - handles confidence gating
  - handles `pr_type` routing

#### Consensus and generation policy
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines generation system prompts:
    - `GENERATION_SYSTEM`
    - `SWIFT_GENERATION_SYSTEM`
    - `UI_ADDENDUM`

#### GitHub operations façade
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
- All GitHub operations must go through `GitHubTool`.

#### Persistent build learning
- build memory
  - file: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - persists across fresh installs and thread state wipes
- build rules
  - file: `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - persists unless switching to a completely new codebase

#### Document context ingestion
- `DocumentStore` usage for generation context
- explicit document loading such as `PRODUCT_CONTEXT.md`

#### Failure handling policy
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

#### XPC messaging surface
- line-delimited JSON protocol
- ready/build/gate/document-status messaging to the macOS UI

### Explicitly out of scope or prohibited

#### Direct GitHub API usage
- ForgeAgent must not call the GitHub API directly.
- All GitHub operations must be mediated by `GitHubTool`.

#### Execution of generated code
- Generated code is never executed by the agent.
- No `eval`
- No `exec`
- No subprocess execution of generated content

#### Automatic approval or unattended gate bypass
- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.

#### Unvalidated file writes
- Any file write outside `path_security.validate_write_path()` is out of bounds.

#### Trust elevation of external content
- Documents, PR comments, and CI output are untrusted inputs.
- External document context must not be placed into the system prompt.

## Data Flow

### 1. Session establishment over XPC
ForgeAgent communicates with the macOS host over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

The subsystem emits a `ready` message with:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

### 2. Build intent enters orchestration
The build request is handled by the build orchestration path in `BuildPipeline` within `src/build_director.py`.

The pipeline determines work decomposition into ordered PRs and applies stage routing.

### 3. Scope confidence gate
Before implementation proceeds, ForgeAgent performs scope analysis.

The documented gate behavior is:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold:

- gaps are shown to the operator
- options are:
  - proceed
  - answer
  - cancel
- if the operator answers gap questions, one one-shot re-scope is performed
- there is no indefinite clarification loop in scope analysis

### 4. Context assembly
Generation context is assembled from repository and document inputs.

DocumentStore is used for the primary generation context use case, including loading specific documents such as `PRODUCT_CONTEXT.md`.

Context handling constraints:

- external document context goes in the USER prompt
- never in the SYSTEM prompt
- all external input is treated as untrusted and validated

Context management behavior includes:

- automatic trimming at 30k tokens
- preservation of:
  - the spec-anchor first turn
  - the last 6 messages

### 5. Parallel generation and arbitration
ForgeAgent generates implementation and tests using two LLM providers in parallel.

Consensus is managed by `ConsensusEngine` in `src/consensus.py`, with Claude serving as arbitrator.

### 6. Correction and local quality passes
After generation, the pipeline performs:

- a self-correction pass
- a lint gate
- a bounded fix loop of up to 20 local attempts

Failure strategy selection is determined by `_choose_strategy(failure_type, attempt, records)` with the following rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 7. CI execution and log handling
ForgeAgent executes CI and consumes CI output as untrusted input.

CI log handling behavior:

- output is truncated at 8k characters
- truncation policy is 70% head / 30% tail
- no operator action required for truncation

### 8. Operator gating
When a blocking decision is required, ForgeAgent emits a `gate_card` with:

- `gate_type`
- `options[]`
- `description`

The gate blocks indefinitely until the operator responds.

There is no auto-approval path.

### 9. Merge and persistence
After successful PR completion:

- build memory is written via `build_memory.record_pr()`
- per-PR stage checkpoints preserve completion state across crashes
- build rules may be updated after a build run when 3 or more recurring failure patterns are found

### 10. Progress streaming
ForgeAgent streams build progress to the UI via `build_card` messages containing:

- `card_type`
- `stage`
- `content`
- `progress`

Document embedding progress may be reported via `doc_status`:

- `doc_id`
- `doc_name`
- `status`
- `chunk_count`
- `embedded_count`

## Key Invariants

The subsystem enforces the following invariants from the architecture context.

### Security and trust
- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged; they are never raised as exceptions.

### Execution safety
- Generated code is never executed by the agent.
- No `eval`, `exec`, or subprocess execution of generated content.

### Human control
- Gates wait indefinitely for operator input.
- No auto-approve behavior is allowed.

### Filesystem safety
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Validate paths before any write.

### Recovery and persistence
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory is persistent and is never cleared automatically.
- Build rules are persistent and are never cleared automatically.

### Operational limits
- Scope gate threshold is fixed at confidence 85 for `_stage_scope`.
- Scope clarification permits one re-scope after operator gap answers; no loop.
- Local remediation is bounded to 20 attempts maximum.
- Context is auto-trimmed at 30k tokens while preserving the spec-anchor first turn and last 6 messages.
- XPC messages are capped at 16 MB each.
- CI logs are truncated to 8k characters using a 70/30 head-tail split.

## Failure Modes

### Authentication, cryptography, or identity failure
Behavior:
- fail closed
- do not continue in degraded mode
- surface the error with context

Reason:
- auth, crypto, and identity errors are explicitly non-recoverable silent-degradation cases

### Unknown or malformed XPC message type
Behavior:
- discard
- log the event
- do not raise as an exception

Reason:
- unknown XPC message types must not destabilize the process

### Scope confidence below threshold
Trigger:
- `SCOPE_SYSTEM.confidence < 85`

Behavior:
- show `coverage_gaps`
- offer `proceed`, `answer`, or `cancel`
- if the operator answers, perform one one-shot re-scope
- otherwise remain gated or terminate per operator choice

### Generation or correction loop failures
Behavior depends on `failure_type` and `attempt`:

- `assertion_error`
  - choose `test_driven` immediately
- `import_error` or `runtime_error`
  - choose `converse` first
  - then escalate to `test_driven`
- `attempt >= 8`
  - use `nuclear` every third attempt
- after 20 local attempts
  - stop local retries
  - move on

This prevents unbounded retry loops.

### GitHub rate limiting or service throttling
For `403 primary`:
- exponential backoff:
  - 2s
  - 4s
  - 8s
  - 16s
  - 32s
  - 64s

For `429 secondary`:
- respect the `Retry-After` header

Polling behavior:
- use ETag caching on all polling endpoints

### Crash during multi-stage PR processing
Behavior:
- resume using per-PR stage checkpoints
- do not re-run stages already marked complete

### Unsafe write target
Behavior:
- reject the write unless validated by `path_security.validate_write_path()`

### Security refusal from model output
Behavior:
- do not attempt prompt rewording to bypass refusal
- stop
- gate
- log

### Oversized or excessive context
Behavior:
- automatically trim to 30k tokens
- preserve the spec-anchor first turn and last 6 messages

### Large CI logs
Behavior:
- truncate automatically to 8k characters
- keep 70% head and 30% tail

## Dependencies

### Internal components
- `src/build_director.py`
  - `BuildPipeline`
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

### Storage and knowledge components
- `DocumentStore`
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Security and validation components
- `path_security.validate_write_path()`

### External service classes implied by protocol and platform behavior
- two LLM providers for parallel generation
- GitHub via `GitHubTool`
- CI system producing logs and status input
- XPC transport using nonce-authenticated line-delimited JSON

### Protocol contracts
- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

These protocol shapes define ForgeAgent’s integration boundary with the host UI and credential/bootstrap flow.