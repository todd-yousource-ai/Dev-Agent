# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated sequence of pull requests.

At a high level, it:

- accepts build intent and repository context
- decomposes work into an ordered PR plan
- performs scope assessment and confidence gating
- generates implementation and tests using two LLM providers in parallel
- uses Claude as the arbitration layer in consensus
- applies a self-correction pass
- runs lint and a bounded local fix loop
- executes CI
- blocks on operator approval before merge
- persists cross-run learning in build memory and build rules
- reports status and gating state over XPC to the macOS UI

This subsystem is explicitly human-gated. Gates wait indefinitely for operator input; there is no auto-approve behavior.

## Component Boundaries

The subsystem boundary is defined by the files and responsibilities called out in the Forge architecture context.

### In-scope components

#### `src/build_director.py`
Owns build pipeline orchestration, including:

- ordered execution of build stages
- confidence gate handling
- PR type routing
- stage progression and operator-facing gate behavior

It contains the scope stage behavior documented as:

- `SCOPE_SYSTEM` returns `confidence` (0–100) and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the operator is shown gaps and offered:
  - proceed
  - answer
  - cancel
- if the operator answers gaps, exactly one re-scope pass is allowed; there is no iterative loop

#### `src/consensus.py`
Owns multi-model generation and arbitration, including:

- `ConsensusEngine`
- generation system prompts:
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`

This component is responsible for parallel provider usage and arbitration behavior referenced in the platform overview.

#### `src/github_tools.py`
Owns all GitHub interactions via:

- `GitHubTool`
- `WebhookReceiver`

Boundary rule: all GitHub operations must go through `GitHubTool`. Direct GitHub API use is out of bounds.

#### `src/build_ledger.py`
Owns per-PR stage checkpointing and progress durability.

This boundary exists to enforce the invariant that completed work is not re-run after a crash.

#### Build memory and rules persistence
Persistent learning artifacts are in scope:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are durable system memory, not temporary caches.

#### Document store integration
The subsystem uses document-store-backed repository and product context, including automatic loading of `build_rules.md` and specific document retrieval such as `PRODUCT_CONTEXT.md`.

#### XPC protocol integration
The subsystem emits and consumes the documented XPC message types used by the native macOS application shell and UI.

### Out-of-scope behavior

The subsystem does **not**:

- execute generated code through `eval`, `exec`, or subprocess of generated content
- bypass operator gates
- write files without path validation
- place external document context into the system prompt
- clear build memory or build rules automatically
- call GitHub APIs outside `GitHubTool`
- treat unknown XPC message types as exceptions

## Data Flow

The subsystem’s data flow follows the documented pipeline and protocol boundaries.

### 1. Session initialization over XPC

The agent communicates over nonce-authenticated, line-delimited JSON XPC messages with a maximum size of 16MB per message.

Initialization includes a `ready` message:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Credentials are supplied as:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

These credentials are sensitive and must never appear in logs, error messages, or generated code.

### 2. Build intent and context ingestion

Inputs include:

- plain-language build intent
- repository context
- external documents
- PR comments
- CI output

All such external input is untrusted and must be validated.

Document-store context is used primarily for generation. A specific rule applies:

- context from external documents goes in the **USER** prompt
- never in the **SYSTEM** prompt

### 3. Scope analysis and confidence gate

The build director performs scope assessment using `SCOPE_SYSTEM`, which returns:

- `confidence` from 0 to 100
- `coverage_gaps`

`_stage_scope` compares confidence to `_CONFIDENCE_THRESHOLD = 85`.

- if confidence is at or above threshold, the build proceeds
- if below threshold, a gate is emitted to the operator with identified gaps and options to:
  - proceed
  - answer
  - cancel

If the operator supplies answers, the subsystem performs one re-scope pass only.

### 4. PR decomposition and generation

The build intent is decomposed into an ordered PR sequence.

For each PR, the subsystem:

- assembles generation context from repository state, documents, build memory, and build rules
- invokes two LLM providers in parallel
- arbitrates results through Claude via the consensus engine
- generates implementation and tests

The context manager trims context automatically at 30k tokens while preserving:

- the spec-anchor first turn
- the last 6 messages

### 5. Correction, lint, and local fix loop

After initial generation, the subsystem runs:

- a self-correction pass
- a lint gate
- a bounded local fix loop

Failure handling is strategy-driven:

- primary signal: failure type
- secondary signal: attempt count

Documented strategies:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- maximum 20 local attempts, then move on

There is no indefinite local retry behavior.

### 6. CI execution and result handling

The subsystem executes CI and consumes CI output as untrusted external input.

CI polling behavior includes:

- ETag caching on all polling endpoints
- `403 primary` exponential backoff:
  - 2s
  - 4s
  - 8s
  - 16s
  - 32s
  - 64s
- `429 secondary` respects `Retry-After`

CI log output is automatically truncated to 8k characters using:

- 70% head
- 30% tail

### 7. Operator gating and merge control

The subsystem emits `gate_card` messages:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

A gate blocks indefinitely until the operator responds. There is no auto-approval path.

### 8. Status streaming

Progress is streamed via `build_card`:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

These messages feed `BuildStreamView`.

Document embedding/indexing progress may be surfaced as `doc_status`:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

### 9. Persistence and crash recovery

After every successful PR:

- `build_memory.record_pr()` writes to `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is updated

Per-PR stage checkpoints are persisted so completed work is not re-run after a crash.

## Key Invariants

The subsystem must preserve the following invariants.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the system must stop, gate, and log.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists anywhere in the pipeline.
- Scope uncertainty below threshold is surfaced explicitly through a gate with operator options.

### Protocol correctness

- XPC wire format is line-delimited JSON.
- XPC messages are nonce-authenticated.
- XPC message size is capped at 16MB.
- Unknown XPC message types are discarded and logged; they are never raised as exceptions.

### Execution and recovery guarantees

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory is persistent and is not automatically cleared.
- Build rules are persistent and are not automatically cleared except when intentionally switching to a completely new codebase.
- ContextManager auto-trims at 30k tokens while preserving the spec-anchor first turn and the last 6 messages.
- Local repair attempts are bounded to 20.

### GitHub and repository operations

- All GitHub operations go through `GitHubTool`.
- Paths are validated before any write.

## Failure Modes

### Scope confidence below threshold

Condition:

- `SCOPE_SYSTEM` returns `confidence < 85`

Behavior:

- surface `coverage_gaps`
- emit a gate offering proceed, answer, or cancel
- if operator answers, perform one re-scope pass only
- do not enter an unbounded clarification loop

### Auth, crypto, or identity failure

Condition:

- any authentication, cryptographic, or identity validation error

Behavior:

- fail closed
- do not degrade functionality silently
- surface the error with context
- do not continue in a partially authenticated state

### Security refusal

Condition:

- model or policy layer returns `SECURITY_REFUSAL`

Behavior:

- stop processing
- gate
- log
- do not retry by paraphrasing or prompt rewording

### Invalid or unsafe file write

Condition:

- write path is not validated by `path_security.validate_write_path()`

Behavior:

- do not perform the write
- surface the failure with context

### Unknown XPC message type

Condition:

- inbound XPC message type is not recognized

Behavior:

- discard message
- log occurrence
- do not raise an exception

### Local build/test failure during correction loop

Condition:

- assertion, import, runtime, lint, or similar local failure during repair

Behavior:

- choose strategy via `failure_handler.py:_choose_strategy(failure_type, attempt, records)`
- use failure type as the primary routing signal
- use attempt count for escalation
- stop after 20 attempts maximum

Specific strategy mapping:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- every 3rd attempt once `attempt >= 8` → `nuclear`

### CI API throttling or access failure

Condition:

- polling endpoints return `403 primary` or `429 secondary`

Behavior:

- `403 primary` uses exponential backoff from 2s to 64s
- `429 secondary` respects `Retry-After`
- polling uses ETag caching

### Oversized or long-running context

Condition:

- context grows beyond model budget

Behavior:

- ContextManager auto-trims at 30k tokens
- preserve spec-anchor first turn
- preserve last 6 messages

### Crash or restart mid-PR

Condition:

- process terminates during PR processing

Behavior:

- recover from per-PR stage checkpoints
- do not re-run already completed work

## Dependencies

### Internal code dependencies

- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `src/build_ledger.py`
- `failure_handler.py`
- `path_security.validate_write_path()`
- `build_memory.record_pr()`
- `ContextManager`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol dependencies

- XPC line-delimited JSON transport
- nonce authentication
- XPC message schemas:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External service dependencies

- Anthropic provider access
- OpenAI provider access
- GitHub access exclusively through `GitHubTool`
- document store services for repository/product context and automatic `build_rules.md` loading

### UI integration dependencies

- `BuildStreamView` for streamed `build_card` updates
- operator response path for `gate_card` blocking gates