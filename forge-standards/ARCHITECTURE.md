# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that drives the end-to-end build workflow from plain-language build intent to gated merge-ready pull requests.

At a subsystem level, ForgeAgent:

- decomposes a build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbiter in consensus generation flow
- runs a self-correction pass
- runs a lint gate
- runs a bounded 20-pass fix loop
- executes CI
- blocks on operator approval before merge
- persists per-PR stage checkpoints to prevent re-running completed work after a crash
- persists cross-run learning via build memory and build rules

The subsystem also performs scope qualification before implementation:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- when confidence is below threshold, the operator is shown gaps and offered:
  - proceed
  - answer
  - cancel
- if the operator answers gap questions, ForgeAgent performs a one-shot re-scope only; there is no re-scope loop

ForgeAgent streams build status over XPC using structured cards:

- `build_card` messages for progress and stage reporting
- `gate_card` messages when operator input is required

It also integrates document context and persistent learning into generation:

- external document context is used for generation as user-supplied context
- `build_memory.json` records successful PR outcomes and survives fresh installs and thread state wipes
- `build_rules.md` accumulates self-improving coding rules derived from recurring failure patterns

## Component Boundaries

ForgeAgent is bounded by the following responsibilities and interfaces derived from the documented architecture.

### In Scope

#### Build orchestration
Primary orchestration is owned by:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing

This includes:

- PR sequencing
- stage progression
- confidence gating
- operator gates
- crash-safe checkpoint progression

#### Consensus generation
LLM consensus behavior is owned by:

- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

This includes:

- parallel generation across two LLM providers
- arbitration by Claude
- generation prompt system definitions

#### GitHub operations
All GitHub interactions are isolated behind:

- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`

ForgeAgent must not call the GitHub API directly. All GitHub operations go through `GitHubTool`.

#### Persistent build learning
ForgeAgent owns persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are intentionally durable across runs and are not automatically cleared.

### Out of Scope

ForgeAgent does not:

- execute generated code
- `eval`, `exec`, or spawn subprocesses from generated content
- auto-approve gates
- bypass `SECURITY_REFUSAL` by prompt rephrasing
- write files without path validation
- trust external inputs without validation
- raise exceptions for unknown XPC message types

### Trust Boundary

ForgeAgent treats the following as untrusted external input:

- documents
- PR comments
- CI output

All such inputs are validated before use.

Prompt boundary rules are strict:

- context from external documents goes in the `USER` prompt
- external document context never goes in the `SYSTEM` prompt

## Data Flow

### 1. Session initialization over XPC

ForgeAgent communicates over an XPC wire protocol with these constraints:

- line-delimited JSON
- nonce-authenticated
- maximum `16MB` per message

Startup readiness is communicated with:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Credential intake

ForgeAgent receives credentials in structured form:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

Secrets from credentials are operational inputs only and must never appear in logs, error messages, or generated code.

### 3. Build intent to scoped plan

ForgeAgent accepts a plain-language build intent and performs scoping.

Scoping behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence`
  - `coverage_gaps`
- `_stage_scope` compares confidence to `_CONFIDENCE_THRESHOLD = 85`

Outcomes:

- `confidence >= 85`: proceed into implementation stages
- `confidence < 85`: emit a gate describing gaps and wait indefinitely for operator input

The gate is represented as a `gate_card`:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

If the operator supplies answers, ForgeAgent performs one re-scope pass only.

### 4. Document context loading

ForgeAgent uses document store content for generation context, including targeted document loads such as `PRODUCT_CONTEXT.md`.

Document ingestion and embedding progress is reported via:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

Document context is used as generation context in the `USER` prompt only.

### 5. PR generation and consensus

For each PR in the ordered sequence, ForgeAgent:

- routes by `pr_type`
- invokes the `ConsensusEngine`
- generates implementation and tests using two LLM providers in parallel
- uses Claude to arbitrate between candidate outputs

Generated outputs remain inert artifacts; they are not executed by the agent.

### 6. File write path validation

Before any filesystem write, ForgeAgent validates the target path via:

- `path_security.validate_write_path()`

This requirement applies to all file writes before execution of the write.

### 7. Correction, lint, and bounded fix loop

After initial generation, ForgeAgent runs:

- self-correction
- lint gate
- local fix iteration

Failure handling is guided by `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`

Selection rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum `20` local attempts, then move on

### 8. CI execution and log handling

ForgeAgent executes CI and consumes CI output as untrusted input.

Automatic context management rules apply:

- `ContextManager` auto-trims at `30k` tokens
- preserves spec-anchor first turn plus last `6` messages
- CI log output is truncated at `8k` chars
  - `70%` head
  - `30%` tail

### 9. Operator gating and merge progression

When a gate is reached, ForgeAgent emits a `gate_card` and waits indefinitely.

Invariant behavior:

- no auto-approve ever
- operator input is required to continue through gates

### 10. Checkpointing and persistent learning

Per-PR stage checkpoints prevent re-running completed work after a crash.

Persistent learning writes include:

- `build_memory.record_pr()` after every successful PR, updating:
  - `workspace/{engineer_id}/build_memory.json`
- `build_rules.md` after each build run when `3+` recurring failure patterns are found, writing:
  - `Mac-Docs/build_rules.md`

These stores are intentionally persistent and are not automatically deleted on clean runs.

## Key Invariants

ForgeAgent enforces the following subsystem invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.

### Filesystem safety

- All file writes are validated via `path_security.validate_write_path()` before execution.
- Path validation applies before any write operation.

### Protocol robustness

- XPC messages use line-delimited JSON with nonce authentication.
- Maximum XPC message size is `16MB`.
- Unknown XPC message types are discarded and logged, not raised as exceptions.

### Execution continuity

- Per-PR stage checkpoints prevent duplicate completed work after crashes.
- Build memory is persistent across fresh installs and thread state wipes.
- Build rules are persistent and never automatically cleared unless switching to a completely new codebase.

### Bounded recovery

- Retry behavior is finite.
- Local remediation attempts are capped at `20`.

## Failure Modes

### Scope uncertainty

Condition:

- `SCOPE_SYSTEM` returns `confidence < 85`

Behavior:

- ForgeAgent does not silently proceed
- shows `coverage_gaps`
- gates operator with proceed/answer/cancel
- allows at most one operator-assisted re-scope

### Auth, crypto, or identity failure

Condition:

- any authentication, cryptographic, or identity error

Behavior:

- fail closed
- no degraded mode
- no silent continuation

### Security refusal

Condition:

- model or pipeline emits `SECURITY_REFUSAL`

Behavior:

- stop
- gate
- log
- do not retry by rephrasing around the refusal

### Invalid or unsafe file write target

Condition:

- target path fails `path_security.validate_write_path()`

Behavior:

- write must not execute
- failure surfaces with context

### Unknown XPC message type

Condition:

- inbound XPC message type is not recognized

Behavior:

- discard message
- log occurrence
- do not raise as an exception

### GitHub API and polling failures

GitHub access must go through `GitHubTool`.

Documented handling patterns include:

- `403 primary` → exponential backoff:
  - `2s`
  - `4s`
  - `8s`
  - `16s`
  - `32s`
  - `64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints

### Local build/test failure during fix loop

Condition:

- assertion, import, runtime, or other local failure during correction loop

Behavior:

- strategy selected by `_choose_strategy(failure_type, attempt, records)`
- strategy escalates by failure type first, then attempt count
- after `20` attempts, ForgeAgent stops local retries and moves on

### Oversized or noisy context

Condition:

- accumulated context exceeds limits, or CI output is too large

Behavior:

- `ContextManager` trims automatically at `30k` tokens
- preserves spec-anchor first turn and last `6` messages
- truncates CI logs to `8k` chars with `70/30` head-tail split

## Dependencies

### Internal modules

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
- `path_security`
  - `validate_write_path()`
- `ContextManager`
- `build_memory`
  - `build_memory.record_pr()`
- `DocumentStore`

### External service dependencies

- Anthropic provider via `anthropic_api_key`
- OpenAI provider via `openai_api_key`
- GitHub via `github_token`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol dependencies

- XPC line-delimited JSON transport
- nonce-authenticated messaging
- structured messages:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`