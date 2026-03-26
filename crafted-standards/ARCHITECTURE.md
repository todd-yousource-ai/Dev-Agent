# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the native macOS AI coding agent subsystem responsible for converting a plain-language build intent into an operator-gated sequence of pull requests and driving each PR through generation, correction, validation, CI, and merge readiness.

At a subsystem level, it:

- decomposes build intent into an ordered PR plan
- performs scope analysis and confidence gating before implementation
- generates implementation and tests using two LLM providers in parallel
- arbitrates generation via the consensus engine
- incorporates repository and document context through the document store
- applies self-correction, lint, and a bounded local fix loop
- executes CI and surfaces results
- blocks on explicit operator gate decisions before merge-related progression
- persists per-PR checkpoints to avoid replaying completed stages after crashes
- persists cross-run learning in build memory and build rules

The subsystem is orchestrated primarily by the build pipeline and related backend components named in the architecture context:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing and build progress persistence implied by stage-checkpoint invariants

It is explicitly human-in-the-loop. Gates wait indefinitely for operator input, and there is no auto-approve path.

## Component Boundaries

### Inside the CraftedDevAgent subsystem

The subsystem includes the logic and state handling for:

- build-intent intake and PR decomposition
- scope confidence evaluation and `_stage_scope` gating
- LLM-based generation and arbitration through `ConsensusEngine`
- document context loading for generation
- persistent build learning:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- staged PR execution with checkpointing
- fix-loop orchestration and failure strategy selection
- CI result intake and presentation
- operator gate presentation through protocol cards
- GitHub operations exclusively through `GitHubTool`

### Outside this subsystem

The subsystem does not own or bypass:

- direct GitHub API access
  - all GitHub operations must go through `GitHubTool`
- execution of generated code as agent instructions
  - generated code is never executed by the agent via `eval`, `exec`, or subprocess of generated content
- automatic operator decision-making
  - merge or equivalent gated progression cannot proceed without operator input
- trust in external artifacts
  - documents, PR comments, and CI output are external input and treated as untrusted
- path authorization outside centralized validation
  - all writes must be validated via `path_security.validate_write_path()` before execution

### Protocol boundary

The subsystem communicates across XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16MB per message

Known message shapes include:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

Unknown XPC message types are not raised as exceptions; they are discarded and logged.

## Data Flow

### 1. Session initialization

On startup, the subsystem emits or consumes protocol state needed to establish capability and environment status, including the `ready` message:

```json
{ "agent_version", "min_swift_version", "capabilities[]", "doc_store_status" }
```

Credentials are provided as structured input:

```json
{ "anthropic_api_key", "openai_api_key", "github_token", "engineer_id" }
```

Auth, crypto, or identity failures fail closed and do not silently degrade.

### 2. Build intent to scoped work

The agent receives a plain-language build intent and enters the core loop. Scope evaluation occurs before implementation.

The documented scope gate behavior is:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- if below threshold:
  - present the gaps
  - offer `proceed`, `answer`, or `cancel`
- if the operator answers the gaps:
  - perform a one-shot re-scope
  - no repeated rescoping loop

This means scope insufficiency is surfaced explicitly and never hidden.

### 3. Context assembly

Generation context is assembled from repository and document sources.

Document store usage is a primary path for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

A critical prompt-boundary invariant applies:

- context from external documents goes in the `USER` prompt
- never in the `SYSTEM` prompt

The subsystem also loads persistent learning context from:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These artifacts are durable across runs and are not automatically cleared.

### 4. Parallel generation and arbitration

Implementation and tests are generated using two LLM providers in parallel. `ConsensusEngine` in `src/consensus.py` performs arbitration. System prompt variants are defined there, including:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

Generated outputs are treated as content to write and validate, not instructions to execute.

### 5. File write path validation

Before any write operation, the destination path must be validated through:

- `path_security.validate_write_path()`

This applies to all generated code and any other file modifications. No write is allowed to bypass this validation.

### 6. Validation, correction, and bounded repair

After generation, the subsystem applies:

- a self-correction pass
- a lint gate
- a local fix loop capped at 20 attempts

Failure handling is governed by documented strategy selection in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary

Documented mappings:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

Related automatic context controls:

- `ContextManager` auto-trims at 30k tokens
- preserves the spec-anchor first turn and last 6 messages
- CI log output is truncated at 8k chars using 70% head / 30% tail

### 7. CI and external polling

CI is executed and its output is consumed as untrusted external input.

For polling and rate-limited interactions:

- ETag caching is used on all polling endpoints
- `403 primary` uses exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429 secondary` respects the `Retry-After` header

### 8. Operator gates

The subsystem streams progress and requests decisions through cards:

- `build_card`:
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`:
  - `{ gate_type, options[], description }`
  - blocks until operator responds

Operator gating is a hard stop. Gates wait indefinitely; there is no auto-approve path.

### 9. Checkpointing and persistence

Per-PR stage checkpoints are maintained so a crash does not re-run completed work.

Cross-run learning persistence is explicit:

- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread state wipes
  - must not be deleted on clean runs
- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded by `DocumentStore` automatically
  - written after each build run when 3+ recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The subsystem enforces the following architectural invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Prompt and context isolation

- External document context is placed only in the `USER` prompt.
- External document context is never inserted into the `SYSTEM` prompt.

### Write safety

- All file writes are validated via `path_security.validate_write_path()` before execution.
- Path validation applies before any write, not only generated-code writes.

### Human control

- Gates wait indefinitely for operator input.
- There is no auto-approve behavior.

### Protocol robustness

- XPC uses line-delimited JSON with nonce authentication.
- Message size is capped at 16MB.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Progress durability

- Per-PR stage checkpoints prevent replay of completed work after crashes.
- Build memory and build rules persist across runs and are never automatically cleared.

### Repair-loop boundedness

- Local repair is capped at 20 attempts.
- Retry behavior is strategy-driven and finite; there is no infinite retry path.

## Failure Modes

### Scope ambiguity or insufficient context

Condition:
- `SCOPE_SYSTEM` returns confidence below 85

Behavior:
- surface `coverage_gaps`
- gate with `proceed`, `answer`, or `cancel`
- allow one-shot re-scope only if the operator answers gaps

Constraint:
- no repeated scope loop

### Authentication, crypto, or identity failure

Condition:
- failure in credentials, identity, or cryptographic validation

Behavior:
- fail closed
- do not degrade to partial or anonymous operation

### Unsafe or invalid external input

Condition:
- malformed or untrusted document, PR comment, CI output, or protocol payload

Behavior:
- validate input
- reject or constrain processing as needed
- surface the error with context

### Unknown XPC message type

Condition:
- message type not recognized by the protocol handler

Behavior:
- discard and log
- do not raise as an exception

### Path validation failure

Condition:
- `path_security.validate_write_path()` rejects a write target

Behavior:
- the write does not execute
- failure surfaces explicitly

### Security refusal from model output

Condition:
- model emits `SECURITY_REFUSAL`

Behavior:
- stop processing for that path
- gate
- log
- do not attempt bypass by rephrasing

### Generation or validation failure

Condition:
- test, import, runtime, lint, or related local validation failure

Behavior:
- choose recovery strategy via `_choose_strategy(failure_type, attempt, records)`
- apply documented escalation:
  - `assertion_error` → `test_driven`
  - `import_error` / `runtime_error` → `converse`, then `test_driven`
  - `attempt >= 8` → `nuclear` every 3rd attempt
- stop local repair after 20 attempts

### Polling or rate-limit failure

Condition:
- polling endpoints or remote services return limiting responses

Behavior:
- use ETag caching on polling endpoints
- back off on `403 primary` using exponential intervals up to 64s
- respect `Retry-After` on `429 secondary`

### Crash or process interruption

Condition:
- subsystem exits mid-PR or mid-stage

Behavior:
- resume using per-PR stage checkpoints
- do not re-run completed stages

### Context overflow

Condition:
- conversation state exceeds context budget

Behavior:
- `ContextManager` auto-trims at 30k tokens
- preserve the spec-anchor first turn and last 6 messages automatically

## Dependencies

### Internal components

- `BuildPipeline` in `src/build_director.py`
- scope confidence gate and `pr_type` routing in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- generation system prompt definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- build ledger / checkpoint persistence in `src/build_ledger.py`
- `failure_handler.py` strategy selection via `_choose_strategy(...)`
- `ContextManager` auto-trimming behavior
- `DocumentStore` for repository and auxiliary document loading
- `path_security.validate_write_path()`

### External services and interfaces

- two LLM providers used in parallel:
  - Anthropic
  - OpenAI
- GitHub, accessed only through `GitHubTool`
- CI system output consumed as untrusted input
- XPC transport using nonce-authenticated line-delimited JSON

### Persistent data artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These artifacts are architectural dependencies because they carry forward learned behavior and repository-specific operational context across runs.