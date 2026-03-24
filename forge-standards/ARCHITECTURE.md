# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that drives an operator-gated build pipeline from plain-language build intent to pull-requested implementation work.

At a subsystem level, ForgeAgent:

- accepts a build intent and decomposes it into an ordered sequence of pull requests
- performs scoped planning with a confidence gate before implementation proceeds
- generates implementation and tests using two LLM providers in parallel, with Claude arbitration in the consensus layer
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI and presents results to the operator
- blocks on explicit operator approval before merge
- persists per-PR progress and cross-run learning state

The subsystem is responsible for enforcing the build-loop safety and orchestration rules described in the Forge context, including strict handling of untrusted input, checkpointed execution, and persistent build learning.

Named implementation anchors in the repository:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR-type routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing and recovery state
- `failure_handler.py` — failure strategy selection via `_choose_strategy(failure_type, attempt, records)`

Related persistent state:

- `workspace/{engineer_id}/build_memory.json` — persistent build memory written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md` — persistent self-improving coding rules derived from build history and loaded automatically by `DocumentStore`

## Component Boundaries

ForgeAgent owns orchestration, gating, generation coordination, recovery control, and persistence of build learning. Its boundaries are defined by what it may invoke, what it must validate, and what it must never do.

### Inside the subsystem

ForgeAgent is responsible for:

- build orchestration across PR stages
- scope-confidence evaluation and operator gating
- LLM consensus and generation prompt routing
- document-context loading for generation
- CI-driven correction and bounded retry behavior
- operator gate presentation and indefinite waiting for responses
- per-PR stage checkpointing to avoid re-running completed work after crashes
- persistence of build memory and build rules across runs

### Outside the subsystem

ForgeAgent does not directly own:

- direct GitHub API calls; all GitHub operations must go through `GitHubTool`
- arbitrary filesystem mutation; writes are permitted only after path validation through `path_security.validate_write_path()`
- execution of generated code; generated output is produced as artifacts, but never executed by the agent through eval, exec, or subprocess of generated content
- trust of external content; documents, PR comments, and CI output are external inputs and remain untrusted data even when consumed for context
- auto-approval decisions; merge and other gate transitions require operator input and never auto-approve

### Prompt-placement boundary

External document context belongs in the `USER` prompt only and must never be placed into the `SYSTEM` prompt. This is a hard subsystem boundary because prompt-channel separation is part of the safety model.

### XPC boundary

ForgeAgent communicates across an XPC boundary using nonce-authenticated, line-delimited JSON messages with a maximum size of 16 MB per message. Unknown XPC message types are discarded and logged, never raised as exceptions.

## Data Flow

### 1. Session initialization

ForgeAgent establishes an XPC session using the defined wire format:

- line-delimited JSON
- nonce-authenticated
- max 16 MB per message

A `ready` message advertises runtime status:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Credentials are passed as structured input:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

Auth, crypto, or identity failures fail closed and do not degrade silently.

### 2. Build intent intake and scoping

ForgeAgent accepts a plain-language build intent and enters the scope stage.

The documented scope gate behavior is:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the subsystem shows gaps and offers `proceed / answer / cancel`
- if the operator provides gap answers, ForgeAgent performs a one-shot re-scope only; there is no looping re-scope cycle

This stage establishes whether implementation can proceed and whether additional operator clarification is required.

### 3. Context assembly

ForgeAgent assembles generation context from:

- repository context
- document-store content
- build memory
- build rules

DocumentStore usage is explicitly called out as a primary mechanism for generation context. A specific document such as `PRODUCT_CONTEXT.md` may be loaded when needed.

Context handling rules:

- all external documents are untrusted input and must be validated
- external document context is inserted into the `USER` prompt, never the `SYSTEM` prompt
- `ContextManager` auto-trims at 30k tokens
- trimming preserves the spec-anchor first turn and the last 6 messages

Document ingestion/reporting may surface `doc_status` messages of the form:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

### 4. Parallel generation and arbitration

ForgeAgent invokes two LLM providers in parallel for implementation/test generation and uses the consensus layer for arbitration.

The consensus component is anchored in `src/consensus.py` and includes:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

The platform overview states that Claude arbitrates the parallel provider outputs.

Generated code remains inert output within the subsystem. It is never executed by eval, exec, or subprocess of generated content.

### 5. Build execution and correction loop

After generation, ForgeAgent runs:

- a self-correction pass
- a lint gate
- a bounded fix loop of up to 20 passes
- CI execution

Failure handling is governed by `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is the primary signal; attempt count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — max 20 local attempts, then move on

Operational controls:

- `403 primary` → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints
- CI log output truncated at 8k chars using 70% head / 30% tail

### 6. Operator-facing stream and gates

ForgeAgent emits structured UI messages over XPC.

Progress is streamed via `build_card`:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": ... }
```

These are consumed by `BuildStreamView`.

Blocking decisions are emitted via `gate_card`:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

Gate semantics are strict:

- gates wait indefinitely for operator input
- there is no auto-approve path
- if a `SECURITY_REFUSAL` output occurs, it is never bypassed by rephrasing; the subsystem must stop, gate, and log

### 7. GitHub operations and merge path

All GitHub interactions must be routed through `GitHubTool`. Direct GitHub API access is forbidden by architecture.

Any write associated with repo mutation must be path-validated through `path_security.validate_write_path()` before execution.

The subsystem proceeds through PR-based stages and gates on operator approval before merge.

### 8. Checkpointing and persistence

ForgeAgent persists execution progress and learning state in two distinct forms.

#### Per-PR stage checkpoints

Per-PR stage checkpoints prevent re-running completed work after a crash. This recovery state is part of the build ledger and is used to resume safely rather than replay completed stages.

#### Persistent build learning

Build learning is intentionally persistent and is never cleared automatically.

- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - must not be deleted on clean runs

- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The ForgeAgent subsystem enforces the following invariants.

### Security and trust invariants

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no eval, no exec, no subprocess of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Operator-control invariants

- Gates wait indefinitely for operator input.
- There is never any auto-approve behavior.
- Scope progression below the confidence threshold must surface coverage gaps and require an operator choice.

### Filesystem and mutation invariants

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Prompting and context invariants

- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- Context is token-bounded by automatic trimming at 30k tokens while preserving the spec-anchor first turn and last 6 messages.

### Transport and protocol invariants

- XPC wire format is line-delimited JSON with nonce authentication and a 16 MB max message size.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Execution and recovery invariants

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Retry behavior is bounded to a maximum of 20 local attempts.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

## Failure Modes

### Scope confidence failure

If scope confidence is below `_CONFIDENCE_THRESHOLD = 85`, ForgeAgent does not silently continue as if confidence were sufficient.

Expected behavior:

- surface `coverage_gaps`
- offer `proceed / answer / cancel`
- if the operator answers gaps, perform one re-scope pass only

This is a controlled gate, not an unbounded clarification loop.

### Auth, crypto, or identity failure

These failures fail closed. ForgeAgent must stop rather than continue in a degraded state. No silent fallback is permitted.

### Security refusal from model output

If model output yields `SECURITY_REFUSAL`, the subsystem:

- stops
- gates on operator input
- logs the event

Rephrasing to try to bypass the refusal is explicitly disallowed.

### Invalid or untrusted external input

Documents, PR comments, and CI output are treated as untrusted. Validation failure prevents unsafe use of that input. The subsystem must surface the failure with context rather than silently dropping into a weaker mode.

### Unknown XPC message type

Unknown message types on the XPC boundary are discarded and logged. They do not raise exceptions. This prevents protocol noise from crashing the subsystem while still preserving observability.

### Path validation failure

If `path_security.validate_write_path()` fails for an intended write, the write must not execute. This failure blocks the mutation path.

### GitHub operation failure

GitHub failures are mediated through `GitHubTool`.

Documented behaviors include:

- `403 primary` uses exponential backoff from 2s through 64s
- `429 secondary` respects `Retry-After`
- polling uses ETag caching

ForgeAgent does not bypass `GitHubTool` to work around these failures.

### Generation/correction failure

The local correction loop is bounded.

Failure-strategy selection:

- `assertion_error` → `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- from attempt 8 onward, every third attempt may escalate to `nuclear`

If local correction reaches 20 attempts, ForgeAgent stops local retry and moves on rather than retrying indefinitely.

### Crash/restart during PR processing

Per-PR stage checkpoints prevent already completed work from being re-run after a crash. Recovery resumes from checkpointed state.

### Context overrun

If assembled prompt context becomes too large, `ContextManager` auto-trims at 30k tokens, preserving the spec-anchor first turn and last 6 messages. This is automatic and prevents uncontrolled context growth.

### Oversized CI output

CI log output is truncated at 8k characters using a 70% head / 30% tail split. This constrains downstream context usage and transport size without altering the fact that CI output is still untrusted input.

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - performs confidence gating
  - routes by PR type

- `src/consensus.py`
  - provides `ConsensusEngine`
  - defines generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

- `src/github_tools.py`
  - provides `GitHubTool`
  - includes `WebhookReceiver`

- `src/build_ledger.py`
  - supports per-PR stage checkpoint persistence and crash recovery

- `failure_handler.py`
  - defines `_choose_strategy(failure_type, attempt, records)` for correction escalation

### Data/store dependencies

- `DocumentStore`
  - used for generation context
  - automatically loads `Mac-Docs/build_rules.md`

- build memory
  - file: `workspace/{engineer_id}/build_memory.json`
  - updated via `build_memory.record_pr()` after every successful PR

- build rules
  - file: `Mac-Docs/build_rules.md`
  - written after build runs when 3+ recurring failure patterns are identified

### External service dependencies

- two LLM providers used in parallel for generation
- GitHub, accessed only through `GitHubTool`
- CI systems, whose output is consumed as untrusted input
- XPC peer using the documented JSON wire protocol

### Protocol dependencies

ForgeAgent depends on the following message shapes being honored on the XPC boundary:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

These protocol contracts define how ForgeAgent exposes status, receives credentials, reports document-store progress, and blocks for operator decisions.