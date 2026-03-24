# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an ordered sequence of pull requests and driving each PR through generation, validation, CI, and operator-gated merge flow.

At a subsystem level, ForgeAgent:

- Decomposes build intent into ordered PR work.
- Uses two LLM providers in parallel for implementation and test generation, with Claude arbitrating through the consensus layer.
- Performs self-correction, lint gating, and a bounded local fix loop of up to 20 passes.
- Executes CI for generated changes.
- Presents streamed build status and blocking gates to the operator.
- Waits indefinitely for operator input at gates; it never auto-approves.
- Persists per-PR stage checkpoints to prevent re-running completed work after crashes.
- Persists cross-run learning in build memory and build rules.

ForgeAgent is also the enforcement point for several system-wide safety properties:

- authentication, crypto, and identity failures fail closed
- external inputs are treated as untrusted
- generated code is never executed by the agent
- all file writes are path-validated before execution
- security refusals are terminal within the flow and cannot be bypassed by prompt rephrasing

## Component Boundaries

ForgeAgent includes orchestration and coordination logic across the following documented components and responsibilities.

### Included Components

#### Build orchestration
Defined in:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing

This layer owns:

- the core staged build loop
- scope confidence evaluation and threshold gating
- routing work by PR type
- operator-facing proceed/answer/cancel behavior for scope gaps
- stage checkpoint handling per PR

#### Consensus and generation coordination
Defined in:

- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

This layer owns:

- parallel use of two LLM providers
- arbitration behavior
- generation system prompt assets
- generation context assembly rules

It must preserve the invariant that context from external documents is placed in the `USER` prompt and never in the `SYSTEM` prompt.

#### GitHub integration
Defined in:

- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`

This boundary is strict:

- all GitHub operations go through `GitHubTool`
- the GitHub API is never used directly outside this tool boundary

#### Persistent build learning
Documented artifacts:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

This layer owns:

- cross-run build memory via `build_memory.record_pr()`
- self-improving coding rules derived from build history

These stores are explicitly persistent learning systems and are not automatically cleared.

### Excluded / External Boundaries

ForgeAgent does not own:

- direct execution of generated code via `eval`, `exec`, or subprocess execution of generated content; this is explicitly prohibited
- bypassing operator approval at any gate
- direct GitHub API access outside `GitHubTool`
- unvalidated file writes
- exception propagation for unknown XPC message types; they must be discarded and logged

ForgeAgent interacts with, but is bounded by, the following external protocol surfaces:

- XPC line-delimited JSON wire protocol, nonce-authenticated, maximum 16 MB per message
- UI consumers of `build_card` and `gate_card`
- credentials delivery
- document embedding/status reporting via `doc_status`

## Data Flow

### 1. Initialization and session readiness

ForgeAgent participates in the XPC protocol using line-delimited JSON messages with:

- nonce authentication
- maximum message size of 16 MB

The ready handshake shape is:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent intake and scope gating

A plain-language build intent enters the build pipeline. Before implementation proceeds, ForgeAgent performs a scope confidence evaluation.

Documented behavior:

- `SCOPE_SYSTEM` returns `confidence` from 0–100 and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- gaps are shown to the operator
- options are `proceed`, `answer`, or `cancel`
- if the operator provides gap answers, ForgeAgent performs a one-shot re-scope only
- there is no repeated looping on scope refinement

This stage is a hard gate in the pipeline.

### 3. Context assembly

Generation context may include:

- repository context
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- document store content
- persistent build rules
- persistent build memory

All external input is untrusted and validated, including:

- documents
- PR comments
- CI output

External document context is placed in the `USER` prompt only, never in the `SYSTEM` prompt.

### 4. Multi-model generation and arbitration

ForgeAgent invokes two LLM providers in parallel for implementation and test generation. The consensus layer arbitrates between outputs.

Relevant implementation anchor:

- `ConsensusEngine` in `src/consensus.py`

The subsystem uses generation system prompt assets including:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

Generated code is treated as output artifacts only. ForgeAgent never executes generated content directly.

### 5. Local correction and validation loop

After initial generation, ForgeAgent runs:

- a self-correction pass
- a lint gate
- a bounded fix loop

Failure handling is governed by `failure_handler.py` behavior:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is the primary signal
- attempt count is secondary escalation

Required strategy mappings:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 6. CI execution and output handling

ForgeAgent executes CI and consumes CI output as untrusted input.

Automatic handling constraints:

- CI log output is truncated to 8k characters
- truncation policy is 70% head / 30% tail
- no operator action is required for truncation behavior

Rate-limit and polling behavior includes:

- `403` on primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` on secondary: respect `Retry-After`
- ETag caching on all polling endpoints

### 7. Operator gates and UI streaming

ForgeAgent streams progress to the UI using:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": ... }
```

for `build_card`, and blocks for operator input using:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

for `gate_card`.

Gate behavior is strict:

- gates wait indefinitely for operator input
- there is no auto-approve behavior ever

### 8. GitHub operations and merge flow

All GitHub operations are mediated through `GitHubTool`.

Hard rule:

- never use the GitHub API directly

This applies to PR creation, updates, webhook-driven interactions, and other repository operations.

### 9. Persistence and crash recovery

ForgeAgent persists:

- per-PR stage checkpoints, preventing re-running completed work after a crash
- `build_memory.json`, written after every successful PR via `build_memory.record_pr()`
- `build_rules.md`, written after each build run when 3 or more recurring failure patterns are found

Persistence locations:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are not cleanup artifacts:

- `build_memory.json` survives fresh installs and thread state wipes
- `build_memory.json` must not be deleted on clean runs
- `build_rules.md` must not be deleted on clean runs unless switching to a completely new codebase

### 10. Context window management

ForgeAgent applies automatic context trimming through `ContextManager`:

- auto-trims at 30k tokens
- preserves the spec-anchor first turn
- preserves the last 6 messages

This is automatic and requires no operator action.

## Key Invariants

The following invariants are architectural requirements of ForgeAgent.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, and no subprocess execution of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Operator control

- Gates wait indefinitely for operator input.
- No auto-approve ever.

### File and repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Validate paths before any write.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Prompt and context discipline

- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### Protocol handling

- XPC unknown message types are discarded and logged, never raised as exceptions.
- XPC messages use line-delimited JSON, are nonce-authenticated, and must fit within the 16 MB maximum per message.

### Recovery and bounded execution

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Scope re-evaluation after operator gap answers is one-shot only.
- Local remediation is bounded to a maximum of 20 attempts.

## Failure Modes

### Scope uncertainty

Condition:

- `SCOPE_SYSTEM` confidence below 85

Behavior:

- present coverage gaps
- gate on operator choice: `proceed`, `answer`, or `cancel`
- if answers are provided, perform one re-scope pass only

This prevents unbounded clarification loops.

### Auth, crypto, or identity failure

Condition:

- authentication, cryptographic, or identity validation error

Behavior:

- fail closed
- do not silently degrade
- surface error context without exposing secrets

### Security refusal from model output

Condition:

- generation returns `SECURITY_REFUSAL`

Behavior:

- do not retry by rephrasing around the refusal
- stop
- gate
- log

### Invalid or unsafe write path

Condition:

- file write target fails `path_security.validate_write_path()`

Behavior:

- write is not executed

This is a hard enforcement point before any write.

### Unknown XPC message type

Condition:

- inbound XPC message type is not recognized

Behavior:

- discard
- log
- do not raise as an exception

### Generation or validation failures

Condition:

- assertion, import, runtime, lint, or test failures during local correction

Behavior:

- choose recovery strategy via `_choose_strategy(failure_type, attempt, records)`
- `assertion_error` uses `test_driven` immediately
- `import_error` and `runtime_error` use `converse` first, then `test_driven`
- after attempt 8, escalate to `nuclear` every third attempt
- stop after 20 attempts and move on rather than retry indefinitely

### Polling and API throttling

Condition:

- `403` on primary endpoints
- `429` on secondary endpoints

Behavior:

- exponential backoff for `403`: `2s → 4s → 8s → 16s → 32s → 64s`
- respect `Retry-After` for `429`
- use ETag caching on all polling endpoints

### Oversized or noisy CI output

Condition:

- CI logs exceed retained context budget

Behavior:

- truncate to 8k characters
- retain 70% head and 30% tail

### Context overflow risk

Condition:

- conversation context approaches token limits

Behavior:

- `ContextManager` auto-trims at 30k tokens
- preserve spec-anchor first turn and last 6 messages

### Crash during PR processing

Condition:

- ForgeAgent crashes after partial PR completion

Behavior:

- resume using per-PR stage checkpoints
- do not re-run completed stages

## Dependencies

### Internal code artifacts

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - `pr_type` routing
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
- `ContextManager`
- `build_memory.record_pr()`

### Persistent data and documents

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- document store content, including specifically loaded documents such as `PRODUCT_CONTEXT.md`

### Protocol and external interfaces

- XPC line-delimited JSON transport
- ready message schema
- `build_card` schema
- `gate_card` schema
- credentials schema:
  ```json
  { "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
  ```
- `doc_status` schema for embedding/document status reporting

### External service classes of dependency

ForgeAgent depends on:

- two LLM providers used in parallel
- GitHub through `GitHubTool`
- CI execution/results
- operator input at gate points

These dependencies are always mediated by the subsystem’s safety and validation invariants; ForgeAgent does not permit those external surfaces to bypass its trust, path, prompt, or approval controls.