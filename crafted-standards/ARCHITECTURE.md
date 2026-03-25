# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an operator-gated sequence of implementation pull requests.

At a subsystem level, it is responsible for:

- decomposing build intent into an ordered PR plan
- generating implementation and tests for each PR using two LLM providers in parallel
- arbitrating generation via Claude through the consensus path
- performing self-correction, lint gating, and a bounded local fix loop
- executing CI
- presenting build and gate state to the operator
- stopping for operator approval before merge
- preserving per-PR progress so completed work is not re-run after crashes
- persisting build learning across runs via build memory and build rules

The subsystem operates as the orchestration and generation layer of the build pipeline. It manages untrusted external context, enforces write and execution constraints, coordinates provider output, and ensures that all merge progression remains human-gated.

Relevant implementation anchors named in the TRD:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py`

## Component Boundaries

### Inside this subsystem

The subsystem includes the following responsibilities described in the source material:

- build orchestration through `BuildPipeline`
- scope evaluation and confidence gating
- document-backed generation context assembly
- dual-provider generation and arbitration through `ConsensusEngine`
- self-correction, lint gate, and bounded fix-loop execution
- CI invocation and CI-result handling
- operator gating through streamed cards and blocking gate cards
- checkpointing per PR stage
- persistence of build memory and build rules
- GitHub operations mediated through `GitHubTool`
- failure strategy selection and retry escalation patterns
- context trimming and CI-log truncation for prompt safety and size control

### Outside this subsystem

The following are explicitly outside its authority or prohibited:

- direct GitHub API usage outside `GitHubTool`
- execution of generated code by the agent via `eval`, `exec`, or subprocess of generated content
- auto-approval of gates
- automatic clearing of build memory or build rules
- promotion of external document content into the SYSTEM prompt
- raising exceptions on unknown XPC message types

### Trust boundary

All external input is untrusted and must be validated, including:

- documents
- PR comments
- CI output

Credentials are transported separately via the `credentials` protocol message and include:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Secrets must not appear in:

- logs
- error messages
- generated code

## Data Flow

### 1. Session initialization

The subsystem communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16MB per message

It advertises readiness with:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent intake and scope evaluation

A plain-language build intent enters the build pipeline. The subsystem evaluates scope using the scope-confidence path:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

Behavior at the scope gate:

- if confidence is at or above threshold, the pipeline proceeds
- if below threshold, the subsystem shows gaps and offers:
  - proceed
  - answer
  - cancel
- if the operator answers coverage gaps, the subsystem performs one one-shot re-scope
- no looping re-scope cycle is allowed

### 3. Context assembly

Generation context is assembled from repository context, document store content, and persistent learning artifacts.

Document-store usage is the primary context-loading path. External document context is placed in the USER prompt only, never the SYSTEM prompt.

Persistent learning inputs:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread-state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - intentionally retained across runs
- `Mac-Docs/build_rules.md`
  - loaded by `DocumentStore` automatically
  - written after each build run when 3 or more recurring failure patterns are found
  - intentionally retained unless switching to a completely new codebase

Prompt/context controls:

- `ContextManager` auto-trims at 30k tokens
- preserves:
  - spec-anchor first turn
  - last 6 messages

### 4. Generation and arbitration

For each planned PR, the subsystem generates implementation and tests using two LLM providers in parallel. Claude arbitrates through the consensus path.

Generation behavior is anchored in `src/consensus.py`, including:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM`
- `UI_ADDENDUM`

The subsystem uses this stage to produce candidate code changes and tests, but generated code is not executed by the agent as code content.

### 5. Validation, correction, and local repair loop

After generation, the subsystem applies:

- a self-correction pass
- a lint gate
- a bounded fix loop

Retry and repair behavior is governed by failure handling rules:

- primary signal: `failure_type`
- secondary signal: `attempt`

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 6. CI and output handling

The subsystem executes CI and consumes CI output as untrusted input.

Automatic output controls:

- CI log output truncated at 8k chars
- truncation split:
  - 70% head
  - 30% tail

Polling and rate-limit controls:

- ETag caching on all polling endpoints
- `403` primary: exponential backoff
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429` secondary: respect `Retry-After` header

### 7. Operator gating and merge progression

The subsystem streams status to the UI using:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

via `build_card`, and blocks on operator decisions using:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

via `gate_card`.

Gates wait indefinitely for operator input. There is no auto-approve path.

### 8. Persistence and crash recovery

Per-PR stage checkpoints prevent re-running completed work after a crash.

Build memory and build rules persist across runs and are never cleared automatically, because they are intentional learning systems.

### 9. Write execution boundary

All file writes must be validated by:

- `path_security.validate_write_path()`

before execution of the write.

This applies to any filesystem modification performed by the subsystem.

## Key Invariants

The subsystem enforces the following architectural invariants from the Forge context and repository guidance:

- fail closed on auth, crypto, and identity errors
- never degrade silently on auth, crypto, or identity failures
- no silent failure paths; every error surfaces with context
- secrets never appear in logs, error messages, or generated code
- all external input is untrusted and validated
- generated code is never executed by the agent
- no `eval`
- no `exec`
- no subprocess execution of generated content
- gates wait indefinitely for operator input
- no auto-approve ever
- all file writes are validated through `path_security.validate_write_path()`
- context from external documents goes in the USER prompt, never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the system must stop, gate, and log
- unknown XPC message types are discarded and logged, never raised as exceptions
- per-PR stage checkpoints prevent duplicate re-execution after crashes
- build memory and build rules persist and are never automatically cleared
- all GitHub operations go through `GitHubTool`; direct GitHub API access is disallowed
- scope progression is gated by `_CONFIDENCE_THRESHOLD = 85`
- local repair is bounded to 20 attempts maximum

## Failure Modes

### Scope uncertainty

If scope confidence is below threshold:

- the subsystem does not silently continue as fully confident
- it presents `coverage_gaps`
- it gates for operator choice:
  - proceed
  - answer
  - cancel
- if answers are provided, it performs exactly one re-scope pass

### Auth, crypto, or identity errors

These fail closed. The subsystem must stop rather than continue in a degraded mode.

### Security refusal

If `SECURITY_REFUSAL` is produced:

- it is not bypassed by prompt rephrasing
- the subsystem stops
- gates
- logs the event

### Unknown XPC messages

Unknown message types are:

- discarded
- logged

They are not escalated as exceptions.

### Path validation failure

If `path_security.validate_write_path()` does not validate a target path, the write must not execute.

### GitHub/API rate limiting or access failures

For polling and remote operations:

- `403` primary responses trigger exponential backoff up to 64 seconds
- `429` secondary responses respect `Retry-After`
- ETag caching is used on polling endpoints

All GitHub operations must remain within `GitHubTool`.

### Local repair exhaustion

If correction attempts continue failing:

- strategy escalates by failure type and attempt count
- attempts are capped at 20
- the subsystem moves on rather than retrying indefinitely

### Crash recovery

If the process crashes mid-build:

- per-PR stage checkpoints prevent already completed stages from being re-run

### Oversized or noisy context

Prompt and log controls reduce failure from context overflow:

- context auto-trim at 30k tokens
- preserve the spec anchor and last 6 messages
- CI logs truncated to 8k chars with head/tail retention

## Dependencies

### Internal components named in the TRD

- `BuildPipeline` in `src/build_director.py`
- scope-confidence gating in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- generation system prompts in `src/consensus.py`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- `GitHubTool` in `src/github_tools.py`
- `WebhookReceiver` in `src/github_tools.py`
- `build_memory.record_pr()`
- `DocumentStore`
- `ContextManager`
- `path_security.validate_write_path()`
- failure strategy logic in `failure_handler.py` via `_choose_strategy(failure_type, attempt, records)`

### External/service dependencies described in the TRD

- two LLM providers operating in parallel
- Claude as arbitration path
- GitHub through `GitHubTool`
- XPC transport using nonce-authenticated line-delimited JSON
- operator UI consumers of:
  - `build_card`
  - `gate_card`
  - `doc_status`
  - `ready`
  - `credentials`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are architectural dependencies because they carry cross-run learning and generation constraints, and they must not be automatically removed during normal operation.