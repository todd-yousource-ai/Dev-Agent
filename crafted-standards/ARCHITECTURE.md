# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS build orchestration subsystem for Crafted Dev Agent. It converts a plain-language build intent into an ordered sequence of pull requests and drives each PR through generation, correction, validation, CI, and operator gating.

At a high level, the subsystem:

- Decomposes build intent into staged PR work
- Performs scope analysis and enforces a confidence gate before implementation
- Generates implementation and tests using two LLM providers in parallel
- Uses Claude arbitration through the consensus path
- Runs a self-correction pass, lint gate, and up to a 20-pass local fix loop
- Executes CI for the PR
- Emits streamed status and gate cards to the UI layer
- Waits indefinitely for operator input at gates
- Persists per-PR checkpoints so completed work is not rerun after crashes
- Persists cross-run learning in build memory and build rules

Primary implementation surfaces identified in the architecture context:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR type routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM` + `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — checkpointing and build progress persistence implied by per-PR stage checkpoints

## Component Boundaries

CraftedAgent is responsible for orchestration, enforcement, and safe coordination. Its boundaries are defined by the following responsibilities and exclusions.

### In scope

- Build intent decomposition into ordered PRs
- PR-stage orchestration via `BuildPipeline`
- Scope confidence evaluation and gating
- Consensus-based generation using two LLM providers in parallel
- Use of document context for generation
- Build memory and build rules persistence
- Streaming UI protocol messages:
  - `build_card`
  - `gate_card`
  - `doc_status`
  - `ready`
- GitHub operations through `GitHubTool`
- Crash-safe stage checkpointing per PR
- Local failure handling and bounded retry/fix behavior
- Validation of write paths before any file mutation

### Out of scope / prohibited

- Direct GitHub API use outside `GitHubTool`
- Execution of generated code by the agent
- Silent fallback on auth, crypto, or identity failures
- Auto-approval of gates
- Placement of external document context into the SYSTEM prompt
- Clearing persistent build memory or build rules during normal clean runs
- Raising exceptions for unknown XPC message types

### Trust boundary

All external inputs are untrusted and must be validated, including:

- Documents
- PR comments
- CI output

The subsystem treats protocol payloads, document store content, and external service responses as data that must be constrained before use.

## Data Flow

### 1. Session/bootstrap

CraftedAgent participates in an XPC protocol with:

- Line-delimited JSON wire format
- Nonce authentication
- Maximum 16MB per message

The subsystem emits or consumes protocol messages including:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `build_card`
  - `{ card_type, stage, content, progress }`
- `gate_card`
  - `{ gate_type, options[], description }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged.

### 2. Scope and planning

The build intent enters the core loop and is evaluated by the scope confidence path.

Documented scope behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold, the subsystem:

- Shows coverage gaps
- Offers operator choices:
  - proceed
  - answer
  - cancel
- Allows a one-shot re-scope if the operator provides gap answers
- Does not loop indefinitely on re-scope

This establishes whether implementation should proceed and what missing information must be surfaced to the operator.

### 3. Context assembly for generation

Generation context is assembled from:

- Repository state
- Requested build intent
- Document store material
- Persistent build memory
- Persistent build rules

Document usage rules:

- Document store is used for generation context
- A specific document can be loaded, for example `PRODUCT_CONTEXT.md`
- Context from external documents goes into the USER prompt, never the SYSTEM prompt

Persistent learning inputs:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - never deleted on clean runs
- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3+ recurring failure patterns are found
  - never deleted on clean runs unless switching to a completely new codebase

### 4. Generation and arbitration

For each PR, CraftedAgent generates implementation and tests using two LLM providers in parallel. Claude arbitrates via the consensus path implemented in `src/consensus.py`.

The subsystem applies generation system prompts from the consensus module, including:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM`
- `UI_ADDENDUM`

The consensus path is therefore a controlled generation mechanism rather than arbitrary model invocation.

### 5. Local correction and validation loop

After generation, CraftedAgent performs:

- A self-correction pass
- A lint gate
- A bounded fix loop with a maximum of 20 local attempts

Failure handling rules are explicitly defined:

- In `failure_handler.py`: `_choose_strategy(failure_type, attempt, records)`
- Failure type is the primary signal
- Attempt count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely — max 20 local attempts, then move on

Automatic context/log controls inside this flow:

- `ContextManager` auto-trims at 30k tokens
- Preserves spec-anchor first turn + last 6 messages
- CI log output truncated at 8k chars using 70% head / 30% tail

### 6. File and repository mutation

Any file write is guarded before execution:

- All writes must be validated via `path_security.validate_write_path()`
- “Validate paths before ANY write”

Repository operations are mediated through:

- `GitHubTool`
- `WebhookReceiver`

All GitHub operations must go through `GitHubTool`. Direct GitHub API access is prohibited.

### 7. CI, polling, and operator gate

The subsystem executes CI and handles remote service interaction with bounded, explicit retry behavior:

- 403 primary: exponential backoff
  - `2s → 4s → 8s → 16s → 32s → 64s`
- 429 secondary: respect `Retry-After` header
- ETag caching on all polling endpoints

After CI and validation, CraftedAgent emits a `gate_card` and blocks for operator response. Gates wait indefinitely and are never auto-approved.

### 8. Checkpointing and persistence

Per-PR stage checkpoints prevent re-running completed work after a crash. This persistence boundary ensures idempotent stage progression across restarts without erasing successful prior stages.

Cross-run learning remains persistent independently of checkpoints:

- Build memory persists successful PR learnings
- Build rules persist recurring failure-derived coding rules

## Key Invariants

The subsystem enforces the following invariants from Forge architecture context and subsystem-specific TRD content:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent
  - no `eval`
  - no `exec`
  - no subprocess of generated content
- Gates wait indefinitely for operator input; no auto-approve ever
- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, log
- Unknown XPC message types are discarded and logged, never raised as exceptions
- Per-PR stage checkpoints prevent rerunning completed work after crashes
- Build memory and build rules are persistent learning systems and are never cleared automatically
- Scope execution is gated at confidence threshold 85
- Re-scope is one-shot when operator supplies coverage-gap answers
- Local remediation is bounded to 20 attempts maximum
- All GitHub operations go through `GitHubTool`

## Failure Modes

### Scope uncertainty

Condition:
- `SCOPE_SYSTEM` returns confidence below 85

Behavior:
- Surface `coverage_gaps`
- Present proceed/answer/cancel gate
- Permit one-shot re-scope if operator answers gaps
- Do not enter an unbounded clarification loop

### Auth / crypto / identity failures

Condition:
- Any authentication, cryptographic, or identity error

Behavior:
- Fail closed
- Do not silently continue with degraded guarantees
- Surface the error with context
- Do not leak secrets in logs or messages

### Security refusal

Condition:
- `SECURITY_REFUSAL` is returned

Behavior:
- Stop current path
- Gate
- Log
- Do not attempt bypass via prompt rephrasing

### Invalid or unsafe file write target

Condition:
- Write path fails `path_security.validate_write_path()`

Behavior:
- Write must not execute
- Failure must surface explicitly

### Unknown XPC message type

Condition:
- XPC message type not recognized

Behavior:
- Discard
- Log
- Do not raise as exception

### GitHub / polling throttling and authorization responses

Condition:
- 403 primary or 429 secondary responses

Behavior:
- 403: exponential backoff through 64s maximum listed delay
- 429: honor `Retry-After`
- Use ETag caching on all polling endpoints

### Local build/test correction exhaustion

Condition:
- Repeated local failures during fix loop

Behavior:
- Strategy selected by `_choose_strategy(failure_type, attempt, records)`
- Escalate by failure type first, attempt count second
- Stop local retries after 20 attempts and move on

### Crash during PR execution

Condition:
- Agent crashes mid-stage or between stages

Behavior:
- Resume using per-PR stage checkpoints
- Do not rerun completed work

### Oversized context or logs

Condition:
- Prompt context or CI output exceeds configured bounds

Behavior:
- Auto-trim context at 30k tokens while preserving spec-anchor first turn and last 6 messages
- Truncate CI logs to 8k chars with 70/30 head-tail split

## Dependencies

### Internal modules

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - PR type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - per-PR stage checkpoint persistence

### Supporting subsystem concepts referenced by TRD content

- `DocumentStore`
  - used for generation context
  - auto-loads `Mac-Docs/build_rules.md`
- `ContextManager`
  - auto-trims prompt context
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
  - mandatory precondition for all writes
- `build_memory.record_pr()`
  - persistence hook after every successful PR

### External services/protocols

- XPC transport using line-delimited JSON with nonce authentication
- Two LLM providers in parallel
  - credentials include `anthropic_api_key` and `openai_api_key`
- GitHub through `GitHubTool`
  - credentials include `github_token`
- Operator-facing UI consuming streamed `build_card` and `gate_card`
- Document embedding/status pipeline via `doc_status`

### Persistent data locations

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`