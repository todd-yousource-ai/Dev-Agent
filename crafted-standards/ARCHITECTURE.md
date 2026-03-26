# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into staged implementation work under operator control.

At a high level, it:

- decomposes build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitration layer in consensus generation
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI
- blocks on explicit operator approval before merge
- persists build learning across runs via build memory and build rules
- streams build and gate state over the XPC interface to the macOS UI

This subsystem is part of the Forge architecture context and operates as an orchestrated build pipeline rather than a free-form code execution environment.

Relevant implementation anchors named in the TRDs:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py`
- `failure_handler.py` — `_choose_strategy(failure_type, attempt, records)`

## Component Boundaries

### Inside CraftedAgent

CraftedAgent owns:

- build orchestration through the per-PR pipeline
- scope confidence evaluation and operator gating
- consensus-based code generation usage
- document context loading for generation
- persistent learning artifacts:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- CI-driven correction flow and bounded retry behavior
- XPC message production for readiness, progress, gates, credentials, and document status
- GitHub operations exclusively via `GitHubTool`

### Outside CraftedAgent

CraftedAgent does not own:

- direct GitHub API access outside `GitHubTool`
- arbitrary execution of generated code content
- automatic merge approval or auto-approval logic
- trust in external inputs such as:
  - documents
  - PR comments
  - CI output
- system-prompt injection of external document context
- unchecked filesystem mutation

### Explicit subsystem boundaries enforced by the TRDs

- All GitHub operations must go through `GitHubTool`; the subsystem must never use the GitHub API directly.
- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- Generated code is never executed by the agent; no `eval`, `exec`, or subprocess execution of generated content is permitted.
- Context from external documents belongs only in the USER prompt, never the SYSTEM prompt.
- Gates are operator-blocking and wait indefinitely; there is no auto-approve path.
- Unknown XPC message types are discarded and logged, not raised.

## Data Flow

### 1. Initialization and transport

CraftedAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum message size of 16MB

The readiness handshake emits:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged.

### 2. Build intent to scoped work

A plain-language build intent enters the build pipeline. The subsystem evaluates scope confidence using the scope gate logic documented under:

- `SCOPE_SYSTEM returns confidence (0–100) and coverage_gaps`
- `_stage_scope gates at _CONFIDENCE_THRESHOLD = 85`

Behavior:

- if confidence is at least `85`, the pipeline proceeds
- if below threshold, the subsystem surfaces coverage gaps and offers:
  - proceed
  - answer
  - cancel
- if the operator answers gap questions, one re-scope pass is allowed
- there is no unbounded re-scope loop

### 3. Context assembly for generation

Generation context is assembled from:

- repository state
- build intent
- document store content
- persisted build memory
- persisted build rules

Document usage is explicitly for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

Context management constraints:

- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn and the last 6 messages

External document context is injected only into the USER prompt.

### 4. Parallel generation and arbitration

For each PR-stage unit of work:

- implementation and tests are generated using two LLM providers in parallel
- Claude arbitrates through the consensus layer

The consensus implementation anchor is `ConsensusEngine` in `src/consensus.py`.

### 5. Validation, correction, and bounded local repair

After generation, the subsystem runs:

- a self-correction pass
- a lint gate
- a fix loop capped at 20 local attempts

Failure handling is strategy-driven in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — max 20 local attempts, then move on

### 6. CI processing

CraftedAgent executes CI and consumes CI output as untrusted input.

CI-specific handling includes:

- CI log output truncated at 8k chars
- truncation policy is 70% head / 30% tail
- no operator action required for truncation; it is automatic

Polling and rate-limit behavior:

- ETag caching on all polling endpoints
- `403 primary` → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header

### 7. Operator gate and merge boundary

Before merge, CraftedAgent emits a gate card and blocks until operator response:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

This is a hard human-in-the-loop boundary:

- gates wait indefinitely
- no auto-approve ever

### 8. Progress and status streaming

Build progress is streamed to the UI as build cards:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

Document embedding or availability state is communicated as document status messages:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

### 9. Persistence across runs

CraftedAgent persists cross-run learning in two stores:

#### Build memory

- file: `workspace/{engineer_id}/build_memory.json`
- survives fresh installs and thread state wipes
- written after every successful PR via `build_memory.record_pr()`
- must not be deleted on clean runs

#### Build rules

- file: `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- written after each build run when 3 or more recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

### 10. Crash recovery and stage continuity

Per-PR stage checkpoints prevent re-running completed work after a crash. This gives the subsystem resumability at stage granularity and avoids duplicate execution of already-completed stages.

## Key Invariants

The following are explicit architectural invariants for CraftedAgent:

- Fail closed on auth, crypto, and identity errors — never degrade silently.
- No silent failure paths — every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including documents, PR comments, and CI output.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input — no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the subsystem must stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional enforced behaviors from the TRDs:

- All GitHub operations go through `GitHubTool`.
- Scope gating uses a confidence threshold of `85`.
- Re-scoping after operator clarification is one-shot, not iterative.
- Local repair is bounded to 20 attempts.
- Context trimming is automatic at 30k tokens while preserving anchor turns.

## Failure Modes

### Scope uncertainty

If scope confidence is below `85`:

- CraftedAgent does not silently continue as if confidence were sufficient
- it surfaces `coverage_gaps`
- it gates the operator with `proceed`, `answer`, or `cancel`
- if answers are provided, only one re-scope attempt is performed

### Auth, crypto, or identity failures

These fail closed. The subsystem must not continue in degraded mode.

### Security refusal

If a `SECURITY_REFUSAL` result is produced:

- the subsystem must stop
- gate
- log

It must not attempt bypass by rephrasing.

### Invalid or unsafe write path

Any write failing `path_security.validate_write_path()` must not execute.

### Unknown XPC message type

The subsystem discards and logs the message. It does not raise an exception for this class of protocol error.

### Generation or repair failure

Repair behavior is bounded and strategy-specific:

- assertion-oriented failures move immediately to test-driven handling
- import/runtime failures begin with converse handling, then escalate to test-driven
- after attempt 8, nuclear handling is used every third attempt
- after 20 local attempts, the subsystem stops retrying and moves on

### GitHub polling and rate limits

- `403 primary` triggers exponential backoff up to 64 seconds
- `429 secondary` obeys `Retry-After`
- polling endpoints use ETag caching to reduce redundant calls

### CI log volume

Oversized CI output is truncated automatically to 8k characters using a 70/30 head-tail split. This is a bounded-context measure, not a silent drop of all context.

### Crash during staged execution

Per-PR stage checkpoints prevent completed stages from being re-run after restart.

## Dependencies

Named dependencies and interfaces documented in the TRDs:

### Internal code modules

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - owns confidence gating
  - owns `pr_type` routing
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines `GENERATION_SYSTEM`
  - defines `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
- `src/build_ledger.py`
- `failure_handler.py`
  - owns `_choose_strategy(failure_type, attempt, records)`

### Platform services and stores

- XPC transport using line-delimited JSON and nonce authentication
- `DocumentStore`
- `ContextManager`
- persistent build memory at `workspace/{engineer_id}/build_memory.json`
- persistent build rules at `Mac-Docs/build_rules.md`

### External credentials and tokens

The subsystem accepts credentials in the documented wire shape:

```json
{
  "anthropic_api_key": "...",
  "openai_api_key": "...",
  "github_token": "...",
  "engineer_id": "..."
}
```

These credentials are subject to the invariant that secrets must never appear in logs, error messages, or generated code.

### External systems

- GitHub, accessed only through `GitHubTool`
- two LLM providers used in parallel generation
- CI systems whose output is treated as untrusted input

### Non-dependencies by policy

CraftedAgent must not depend on:

- direct GitHub API calls outside `GitHubTool`
- execution of generated code
- automatic approval logic
- unvalidated external input
- unvalidated file write paths