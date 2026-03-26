# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into a gated, multi-PR implementation workflow.

At a high level, it:

- accepts a build intent from the operator
- decomposes the work into an ordered sequence of pull requests
- performs scope analysis and confidence gating before implementation
- generates implementation and tests using two LLM providers in parallel
- uses Claude as the arbitration layer in consensus
- runs self-correction, lint, and an iterative local fix loop
- executes CI
- blocks on explicit operator approval before merge
- persists cross-run learning in build memory and build rules
- resumes safely after crashes using per-PR stage checkpoints

The subsystem is explicitly human-gated. It does not auto-approve and does not degrade silently when security-, identity-, or auth-related failures occur.

## Component Boundaries

CraftedDevAgent is bounded by the following responsibilities and non-responsibilities.

### Inside the subsystem

Core orchestration and policy enforcement include:

- **BuildPipeline orchestration**
  - Implemented in `src/build_director.py`
  - Handles pipeline sequencing, confidence gating, and `pr_type` routing

- **Consensus generation**
  - Implemented in `src/consensus.py`
  - Provides `ConsensusEngine`
  - Owns generation system prompts including:
    - `GENERATION_SYSTEM`
    - `SWIFT_GENERATION_SYSTEM`
    - `UI_ADDENDUM`

- **GitHub operation mediation**
  - All GitHub operations must flow through `GitHubTool`
  - Implemented in `src/github_tools.py`
  - `WebhookReceiver` is part of this boundary

- **Persistent build learning**
  - `build_memory.json`
    - Location: `workspace/{engineer_id}/build_memory.json`
    - Written after every successful PR via `build_memory.record_pr()`
    - Must survive fresh installs and thread state wipes
    - Must not be deleted on clean runs
  - `build_rules.md`
    - Location: `Mac-Docs/build_rules.md`
    - Loaded automatically by `DocumentStore`
    - Written after each build run when 3 or more recurring failure patterns are found
    - Must not be deleted on clean runs unless switching to a completely new codebase

- **Document-backed context loading**
  - Uses `DocumentStore`
  - Supports primary generation context loading and specific document loads such as `PRODUCT_CONTEXT.md`

- **Failure handling strategy selection**
  - Governed by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`

### Outside the subsystem

The subsystem does not own or bypass:

- direct GitHub API access
  - prohibited; only `GitHubTool` may perform GitHub operations
- execution of generated code
  - prohibited; no `eval`, `exec`, or subprocess execution of generated content
- automatic approval decisions
  - prohibited; gates wait indefinitely for operator input
- unvalidated filesystem writes
  - prohibited; all writes require `path_security.validate_write_path()` before execution
- promotion of external document context into the system prompt
  - prohibited; external document context belongs only in the USER prompt
- automatic clearing of persistent learning state
  - prohibited for build memory and build rules under normal clean runs

## Data Flow

The subsystem data flow is stage-oriented and checkpointed per PR.

### 1. Session initialization and transport

The subsystem communicates over XPC with:

- line-delimited JSON wire format
- nonce authentication
- maximum 16 MB per message

The agent emits or consumes protocol messages including:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator response
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged; they are never raised as exceptions.

### 2. Build intent intake and scope analysis

The operator supplies a plain-language build intent.

The subsystem performs scope analysis using the documented confidence gate:

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

Behavior at this gate:

- if confidence is at or above threshold, the pipeline proceeds
- if below threshold, the subsystem shows coverage gaps and offers:
  - proceed
  - answer
  - cancel
- if the operator answers gap questions, one-shot re-scope is performed
- there is no unbounded clarification loop

### 3. Context assembly

Generation context is assembled from trusted internal state plus validated external inputs.

Inputs may include:

- repository state
- loaded documents from `DocumentStore`
- specific documents such as `PRODUCT_CONTEXT.md`
- build memory from `workspace/{engineer_id}/build_memory.json`
- build rules from `Mac-Docs/build_rules.md`
- PR/thread state and checkpoints

Constraint:

- context from external documents must be placed in the USER prompt, never in the SYSTEM prompt

All external input is treated as untrusted and validated, including:

- documents
- PR comments
- CI output

### 4. PR planning and generation

The build intent is decomposed into an ordered sequence of PRs.

For each PR, the subsystem:

- routes by `pr_type` through `BuildPipeline`
- invokes parallel generation using two LLM providers
- uses Claude to arbitrate via the consensus layer
- generates implementation and tests
- applies self-correction
- runs lint gating
- enters the local fix loop, bounded to 20 attempts

### 5. Local failure handling and iteration

Failure recovery is governed by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`.

Selection rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Related runtime controls:

- `ContextManager` auto-trims at 30k tokens
- preserves the spec-anchor first turn plus last 6 messages
- CI log output is truncated at 8k characters
  - 70% head
  - 30% tail
- no action required for these controls; they are automatic

### 6. GitHub and CI interaction

All GitHub operations must pass through `GitHubTool`.

Operational constraints include:

- path validation before any write
- no direct GitHub API usage outside `GitHubTool`
- ETag caching on all polling endpoints
- rate-limit handling:
  - `403` primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
  - `429` secondary: respect `Retry-After` header

### 7. Human gate and merge progression

The subsystem surfaces progress through `build_card` updates and blocks at decision points using `gate_card`.

Critical gate behavior:

- gates wait indefinitely for operator input
- there is no auto-approve path
- operator approval is required before merge

### 8. Persistence and recovery

The subsystem maintains:

- per-PR stage checkpoints to prevent re-running completed work after a crash
- persistent build memory via `build_memory.record_pr()` after every successful PR
- persistent build rules updated after runs with 3+ recurring failure patterns

These persistence mechanisms are intentional learning and recovery systems and are not automatically cleared.

## Key Invariants

The subsystem enforces the following invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the subsystem must stop, gate, and log.

### Human control and gating

- Gates wait indefinitely for operator input.
- There is no auto-approve behavior.
- Below-threshold scope confidence requires explicit operator decision through the confidence gate.

### File and path safety

- All file writes are validated by `path_security.validate_write_path()` before execution.
- Path validation is required before any write, including GitHub-mediated operations.

### Prompt and context isolation

- External document context goes in the USER prompt only.
- External document context must never be inserted into the SYSTEM prompt.

### Transport robustness

- XPC unknown message types are discarded and logged.
- Unknown message types are never raised as exceptions.
- XPC messages are line-delimited JSON, nonce-authenticated, and capped at 16 MB.

### Iteration and recovery bounds

- Per-PR stage checkpoints prevent replay of completed stages after crash recovery.
- Local fix attempts are capped at 20.
- Scope clarification allows one re-scope after operator gap answers; no open-ended loop.

### Persistent learning

- Build memory is persistent across fresh installs and thread state wipes.
- Build rules are persistent and self-improving.
- Neither build memory nor build rules is cleared automatically during normal clean runs.

## Failure Modes

### Scope confidence below threshold

Condition:

- `_stage_scope` receives `confidence < 85`

Behavior:

- surface `coverage_gaps`
- present operator options: proceed / answer / cancel
- allow one-shot re-scope if the operator answers
- do not enter an infinite clarification cycle

### Auth, crypto, or identity failure

Condition:

- any authentication, cryptographic, or identity validation error

Behavior:

- fail closed
- do not silently degrade
- surface the error with context
- do not continue on reduced trust assumptions

### Security refusal from model output

Condition:

- model returns `SECURITY_REFUSAL`

Behavior:

- stop processing
- gate on operator input
- log the event
- do not retry by rephrasing to bypass refusal

### Unknown XPC message type

Condition:

- inbound XPC message type is not recognized

Behavior:

- discard message
- log occurrence
- do not throw exception for the unknown type

### Path validation failure

Condition:

- `path_security.validate_write_path()` rejects a target path

Behavior:

- abort the write
- surface the error with context
- do not attempt alternate unvalidated write paths

### GitHub rate limiting or polling pressure

Condition:

- GitHub returns `403` primary rate limit or `429` secondary rate limit

Behavior:

- `403`: exponential backoff from 2s through 64s
- `429`: honor `Retry-After`
- use ETag caching on polling endpoints to reduce repeated load

### Repeated local build/test failure

Condition:

- local generation/fix loop encounters repeated failures

Behavior:

- choose recovery strategy primarily by `failure_type`, secondarily by `attempt`
- escalate according to `_choose_strategy(...)`
- hard-stop local retries at 20 attempts
- move on rather than retry indefinitely

### Crash or restart mid-PR

Condition:

- subsystem terminates during a PR stage

Behavior:

- recover from per-PR stage checkpoints
- do not rerun completed work for that PR

### Excessive context or oversized CI logs

Condition:

- prompt context grows too large or CI logs are too long

Behavior:

- `ContextManager` trims at 30k tokens
- preserve spec-anchor first turn and last 6 messages
- truncate CI logs to 8k chars with 70/30 head-tail split

## Dependencies

The subsystem depends on the following named components and interfaces from the source material.

### Internal components

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate logic
  - `pr_type` routing

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

- `path_security.validate_write_path()`

- `ContextManager`

- `DocumentStore`

- build memory subsystem
  - `workspace/{engineer_id}/build_memory.json`
  - `build_memory.record_pr()`

### External/provider-facing dependencies

- two LLM providers in parallel
- Claude as arbitration layer
- GitHub via `GitHubTool`
- XPC transport using the documented JSON protocol

### Persistent artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### UI/protocol surfaces

- `BuildStreamView`
- `ready` messages
- `build_card` messages
- `gate_card` messages
- `credentials` messages
- `doc_status` messages