# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding subsystem responsible for turning a plain-language build intent into a controlled, staged software delivery workflow.

Within Forge, it:

- decomposes the requested build into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbiter in the consensus flow
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI
- pauses on operator gates before merge decisions
- persists cross-run learning through build memory and build rules

The subsystem operates as a gated build pipeline, not an autonomous executor of generated code. Its role is orchestration, generation, validation, retry handling, and operator-mediated progression.

Relevant implementation anchors from the repository structure:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing and run progress persistence

## Component Boundaries

CraftedAgent includes the build orchestration and generation path, but it is constrained by explicit boundaries.

### Inside the subsystem

- Build intent handling and staged PR decomposition
- Scope confidence evaluation and gating
- Multi-provider generation via the consensus engine
- Document/context loading for generation
- Build memory and build rules persistence/use
- GitHub operations through the approved tool abstraction
- Failure classification and bounded retry strategy
- CI execution handling and result processing
- Operator gate presentation through protocol cards
- Per-PR checkpointing to avoid replay after crashes

### Outside the subsystem

- Direct execution of generated code as agent instructions
- Direct GitHub API usage outside `GitHubTool`
- Silent auto-approval or automatic gate advancement
- Trusting external content without validation
- Clearing persistent learning artifacts on normal clean runs
- Raising XPC exceptions for unknown message types

### Hard boundaries it enforces

- **Generated code is never executed by the agent**: no `eval`, no `exec`, no subprocess invocation of generated content
- **All file writes are path-validated** via `path_security.validate_write_path()` before execution
- **All GitHub operations go through `GitHubTool`**; direct API access is disallowed
- **External document context belongs in the USER prompt only**, never the SYSTEM prompt
- **Operator gates block indefinitely** until human input; no auto-approve path exists
- **Security refusal handling is terminal for that path**: `SECURITY_REFUSAL` cannot be bypassed by rephrasing

## Data Flow

### 1. Session and protocol initialization

CraftedAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum message size of 16 MB

The ready handshake uses:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Build intent intake and scope gating

A plain-language build intent enters the core loop. Before implementation begins, the subsystem performs a scope-confidence pass.

Documented gate behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold, CraftedAgent:

- shows the identified gaps
- offers operator choices:
  - proceed
  - answer
  - cancel
- allows one-shot re-scope if the operator answers the gaps
- does not loop indefinitely on re-scope

This makes scope sufficiency an explicit operator-visible gate rather than an implicit model assumption.

### 3. Context assembly

Generation context is assembled from trusted internal state and validated external inputs.

Sources include:

- repository context
- specific loaded documents from the document store, including examples like `PRODUCT_CONTEXT.md`
- persistent build memory
- persistent build rules

Document store usage is a primary path for generation context. External documents are treated as untrusted input and validated before use.

Prompt-placement rule:

- context from external documents goes in the **USER** prompt
- never in the **SYSTEM** prompt

### 4. Persistent learning inputs

CraftedAgent maintains two persistent learning artifacts.

#### Build memory

- file: `build_memory.json`
- location: `workspace/{engineer_id}/build_memory.json`
- written after every successful PR via `build_memory.record_pr()`
- survives fresh installs and thread-state wipes
- is not deleted on clean runs

This is a cross-run learning system, not ephemeral session state.

#### Build rules

- file: `build_rules.md`
- location: `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- written after each build run when 3 or more recurring failure patterns are found
- is not deleted on clean runs unless switching to a completely new codebase

### 5. Parallel generation and arbitration

For each PR stage, CraftedAgent invokes two LLM providers in parallel and routes their outputs through the consensus engine.

Key implementation anchor:

- `src/consensus.py` — `ConsensusEngine`

The consensus layer is responsible for applying the generation system prompts and arbitration flow, with Claude serving as arbiter per the Forge platform overview.

### 6. PR-oriented execution pipeline

The subsystem processes work in ordered PR stages. For each PR, it performs:

- implementation generation
- test generation
- self-correction pass
- lint gate
- bounded local fix loop
- CI execution
- operator gate before merge progression

The local repair loop is bounded at 20 attempts maximum. It does not retry indefinitely.

### 7. Failure handling and retry strategy

Failure handling is driven primarily by failure type, secondarily by attempt count.

In `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- max 20 local attempts, then move on

Related transport/polling behavior:

- `403` on primary path: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` on secondary path: respect `Retry-After`
- ETag caching on all polling endpoints

### 8. Context and output shaping

The subsystem automatically constrains context growth and CI verbosity.

- `ContextManager` auto-trims at 30k tokens
- preserves:
  - spec-anchor first turn
  - last 6 messages
- CI log output truncated at 8k chars
  - 70% head
  - 30% tail

These are automatic safeguards to preserve useful context while keeping prompt sizes bounded.

### 9. Progress and gate emission

Operator-visible progress is streamed through protocol cards.

#### Build progress

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": ... }
```

These `build_card` messages stream to `BuildStreamView`.

#### Human gates

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

These `gate_card` messages block until the operator responds.

### 10. Checkpointing and crash recovery

Per-PR stage checkpoints prevent re-running completed work after a crash.

This checkpointing boundary is part of the build ledger/pipeline state and ensures resumed runs continue from the last durable completed stage rather than re-executing prior PR work.

## Key Invariants

The subsystem is defined by the following invariants from the Forge context and subsystem requirements.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error must surface with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- `SECURITY_REFUSAL` is never bypassed by rephrasing; stop, gate, and log

### Execution safety

- Generated code is never executed by the agent
- No `eval`
- No `exec`
- No subprocess execution of generated content

### File and repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Validate paths before any write
- All GitHub operations go through `GitHubTool`

### Human control

- Gates wait indefinitely for operator input
- No auto-approve path exists
- Below-threshold scope confidence always surfaces coverage gaps and explicit options

### Protocol correctness

- XPC wire format is line-delimited JSON
- XPC messages are nonce-authenticated
- Maximum message size is 16 MB
- Unknown XPC message types are discarded and logged, never raised

### Durability and learning

- Per-PR stage checkpoints prevent replay after crashes
- Build memory is persistent and never cleared automatically
- Build rules are persistent and never cleared automatically except when switching to a completely new codebase

## Failure Modes

### Scope uncertainty

If scope confidence is below the threshold of 85:

- the subsystem does not proceed silently
- it emits the identified `coverage_gaps`
- it blocks on operator choice
- it permits a one-shot re-scope only if the operator answers the gaps

This prevents low-confidence implementation from being treated as normal flow.

### Auth, crypto, or identity failures

These fail closed. CraftedAgent must not degrade to a weaker mode or continue with reduced guarantees.

### Security refusal

If a generation or validation path yields `SECURITY_REFUSAL`:

- processing stops for that path
- a gate is raised
- the event is logged
- rephrasing cannot be used to bypass the refusal

### Invalid external input

Because all external input is untrusted, malformed or unsafe documents, PR comments, or CI output must be validated and rejected or constrained. They are not promoted to trusted instructions.

### Write-path violations

Any attempted file write that fails `path_security.validate_write_path()` must not execute.

### GitHub transport and rate limiting

Documented handling includes:

- `403` primary path: bounded exponential backoff
- `429` secondary path: honor `Retry-After`
- polling endpoints use ETag caching

These conditions are handled explicitly rather than treated as opaque transient failures.

### XPC protocol anomalies

Unknown XPC message types are:

- discarded
- logged

They do not crash the subsystem through raised exceptions.

### Repeated repair failure

The local repair loop is bounded:

- strategy escalates by failure type and attempt count
- max 20 attempts
- never retries indefinitely
- after the maximum, the subsystem moves on rather than spinning forever

### Crash/restart during multi-PR execution

Per-PR stage checkpoints bound recovery. Completed work is not re-run after restart.

### Context overflow or oversized logs

Automatic mitigation applies:

- prompt context is trimmed at 30k tokens while preserving anchor and recency
- CI logs are truncated to 8k chars with head/tail retention

## Dependencies

### Internal repository components

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - `pr_type` routing
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - per-PR stage checkpointing and durable progress state
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
  - mandatory precondition for all writes
- `DocumentStore`
  - document loading
  - automatic loading of `Mac-Docs/build_rules.md`
- `ContextManager`
  - token trimming and preservation policy
- `build_memory.record_pr()`
  - persistent learning write path after successful PRs

### External/service dependencies implied by protocol and platform

- two LLM providers used in parallel for generation
- Claude as arbiter in consensus
- GitHub, only through `GitHubTool`
- CI execution environment
- XPC transport on macOS
- `BuildStreamView` as the consumer of streamed `build_card` updates

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These persistent artifacts are architectural dependencies, not temporary caches.