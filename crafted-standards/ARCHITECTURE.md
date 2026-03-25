# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an ordered sequence of pull requests and drives each PR through generation, validation, repair, CI, operator gating, and merge orchestration.

At a subsystem level, it is responsible for:

- decomposing build intent into staged PR work
- routing generation through two LLM providers in parallel
- arbitrating generation output through Claude
- running self-correction, lint gating, and a bounded local fix loop
- executing CI for generated changes
- presenting progress and gate state to the UI over XPC
- pausing indefinitely for operator input at required gates
- persisting per-PR stage checkpoints to avoid re-running completed work after crashes
- persisting build learning via `build_memory.json` and `build_rules.md`

The subsystem also performs scope validation before execution. The scope gate uses `SCOPE_SYSTEM` to return:

- `confidence` in the range `0–100`
- `coverage_gaps`

`_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`. If confidence is below threshold, the subsystem surfaces the gaps and offers operator choices to proceed, answer, or cancel. If the operator supplies gap answers, the subsystem performs a one-shot re-scope only; it does not loop indefinitely.

Generated code is produced, edited, linted, tested, and sent through CI, but is never executed by the agent via `eval`, `exec`, or subprocess execution of generated content.

## Component Boundaries

### Inside the CraftedDevAgent subsystem

The subsystem includes orchestration, generation coordination, operator gating, persistence of build learning, and protocol-level communication required to drive a build.

Known implementation surfaces from the architecture context:

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate
  - `pr_type` routing
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
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

The subsystem also owns use of:

- DocumentStore for generation context
- build memory persistence at `workspace/{engineer_id}/build_memory.json`
- build rules persistence at `Mac-Docs/build_rules.md`

### Outside the CraftedDevAgent subsystem

The following are external inputs, services, or interfaces consumed by the subsystem rather than defined by it:

- operator decisions and approval input
- external documents loaded as generation context
- PR comments
- CI output
- GitHub platform state
- LLM providers
- XPC clients consuming streamed cards and status messages

These inputs are explicitly untrusted and must be validated before use.

### Explicit non-responsibilities

The subsystem does not:

- auto-approve gates
- silently downgrade auth, crypto, or identity failures
- write files without path validation
- place external document context into the system prompt
- call the GitHub API directly outside `GitHubTool`
- clear build memory or build rules automatically
- raise exceptions for unknown XPC message types
- execute generated code content

## Data Flow

### 1. Session initialization and protocol handshake

The subsystem communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum `16MB` per message

The `ready` message shape is:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

This establishes compatibility and document-store availability.

### 2. Credential intake

Credentials are supplied in the protocol message:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

These credentials are security-sensitive. They must not appear in logs, error messages, or generated code.

### 3. Build intent and context assembly

A plain-language build intent enters the pipeline. The subsystem assembles context from:

- repository state
- DocumentStore content
- build memory
- build rules

DocumentStore is used for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

A critical boundary rule applies here:

- context from external documents goes in the `USER` prompt
- never in the `SYSTEM` prompt

The `ContextManager` auto-trims at `30k` tokens and preserves:

- the spec-anchor first turn
- the last 6 messages

### 4. Scope confidence gate

Before implementation proceeds, `_stage_scope` runs the scope analysis. `SCOPE_SYSTEM` returns:

- `confidence`
- `coverage_gaps`

If `confidence >= 85`, the build may proceed.

If `confidence < 85`, the subsystem presents the gaps and offers:

- proceed
- answer
- cancel

If the operator answers the gaps, the subsystem performs a single re-scope pass. There is no repeated re-scope loop.

### 5. PR planning and execution

The build intent is decomposed into an ordered sequence of PRs. For each PR, the subsystem:

- restores or creates the per-PR checkpoint state
- routes work by `pr_type`
- invokes parallel generation through two LLM providers
- arbitrates via the consensus engine
- applies self-correction
- runs lint gate
- enters the bounded local fix loop

### 6. Failure-driven repair loop

Repair behavior is selected by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`.

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum `20` local attempts, then move on

This is a bounded, policy-driven correction loop rather than unbounded retry.

### 7. CI and polling behavior

After local validation, the subsystem executes CI and consumes CI output as untrusted input.

Operational constraints:

- CI log output truncated at `8k` chars
- truncation split is `70%` head / `30%` tail
- ETag caching on all polling endpoints
- `403` primary rate limits use exponential backoff:
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate limits respect the `Retry-After` header

### 8. Operator gating and UI stream

The subsystem emits progress and blocking gates through protocol cards.

Progress cards:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

These are streamed to `BuildStreamView`.

Gate cards:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

Gate cards block until the operator responds. Gates wait indefinitely; there is no auto-approve path.

### 9. GitHub operations and merge path

All GitHub operations must go through `GitHubTool`. The subsystem must never use the GitHub API directly.

Any file write associated with repository changes must be validated through:

- `path_security.validate_write_path()`

before execution.

### 10. Persistence and learning

Per-PR stage checkpoints are stored so that completed work is not re-run after a crash.

Persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - must not be deleted on clean runs
- `Mac-Docs/build_rules.md`
  - loaded by DocumentStore automatically
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

Document embedding status may be surfaced via:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

## Key Invariants

The subsystem is constrained by the following invariants from the Forge architecture context:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, no subprocess of generated content.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are never cleared automatically; they are persistent learning systems.

Additional enforced behaviors documented in the TRD material:

- `_stage_scope` gates below `_CONFIDENCE_THRESHOLD = 85`
- below-threshold scope handling allows only one re-scope after operator answers
- all GitHub operations go through `GitHubTool`
- path validation is required before any write
- context trimming is automatic at `30k` tokens while preserving anchor and recent turns
- local repair attempts are capped at `20`

## Failure Modes

### Authentication, crypto, or identity failure

Behavior:

- fail closed
- do not continue in degraded mode
- surface the error with context
- do not expose secrets

### Scope confidence below threshold

Behavior:

- block progression at `_stage_scope`
- show `coverage_gaps`
- offer `proceed`, `answer`, or `cancel`
- if answered, perform one-shot re-scope only

### LLM generation disagreement or low-confidence output

Behavior:

- resolve through `ConsensusEngine`
- continue through self-correction and downstream validation gates
- do not execute generated code directly

### Local validation failures

Behavior is selected by `_choose_strategy(failure_type, attempt, records)`:

- `assertion_error` triggers immediate test-driven repair
- `import_error` and `runtime_error` begin with converse repair, then test-driven
- after attempt 8, every third attempt may escalate to nuclear
- hard stop after 20 local attempts

### GitHub API or polling rate limits

Behavior:

- `403` primary limit uses exponential backoff up to `64s`
- `429` secondary limit respects `Retry-After`
- polling uses ETag caching

### Oversized or noisy CI output

Behavior:

- CI logs are truncated to `8k` characters
- preserve signal using `70%` head and `30%` tail split

### Unknown XPC message type

Behavior:

- discard message
- log occurrence
- do not raise an exception

### Crash or restart during PR processing

Behavior:

- resume from per-PR stage checkpoints
- do not re-run already completed work for that PR

### Security refusal from model output

Behavior:

- do not bypass by rephrasing
- stop
- gate
- log

### Invalid file write target

Behavior:

- reject the write unless `path_security.validate_write_path()` passes
- do not perform unvalidated writes

## Dependencies

### Internal code modules

- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `src/build_ledger.py`
- `failure_handler.py`

### Persistent state and local artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Platform and protocol dependencies

- XPC transport using line-delimited JSON
- nonce authentication
- `BuildStreamView` for streamed `build_card` updates

### Service dependencies

- two LLM providers in parallel
- GitHub, exclusively via `GitHubTool`
- CI system output and status endpoints
- DocumentStore, including automatic loading of `build_rules.md`

### Utility and policy dependencies

- `path_security.validate_write_path()`
- `SCOPE_SYSTEM`
- `ContextManager`
- `build_memory.record_pr()`

The subsystem depends on these components to enforce its safety, gating, persistence, and orchestration responsibilities, but it remains bounded by the invariants above: fail closed, validate all untrusted input, never execute generated code, and never advance past operator gates automatically.