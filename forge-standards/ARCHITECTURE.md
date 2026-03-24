# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated, pull-request-based implementation workflow.

Within the Forge architecture, this subsystem:

- decomposes build intent into an ordered sequence of pull requests
- performs scope analysis and confidence gating before execution
- generates implementation and tests using two LLM providers in parallel, with Claude arbitrating
- runs self-correction, lint gating, and a bounded 20-pass fix loop
- executes CI and presents results
- blocks on operator approval before merge
- persists cross-run learning through build memory and build rules
- streams build and gate state over the XPC protocol to the macOS frontend

It is an orchestration subsystem, not an execution sandbox for generated code. Generated code is produced, written to validated paths, and then evaluated through repository tooling and CI, but is never executed directly by the agent via `eval`, `exec`, or subprocess invocation of generated content.

## Component Boundaries

ForgeAgent spans orchestration, generation coordination, GitHub mediation, state persistence, and operator gating. Its boundaries are defined by the following components and exclusions.

### In-scope components

#### Build orchestration
- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - handles confidence gate behavior
  - routes work by `pr_type`

This is the control plane for the core loop and stage progression.

#### Consensus and generation
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines `GENERATION_SYSTEM`
  - defines `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

This component manages multi-provider generation behavior and arbitration.

#### GitHub mediation
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`

All GitHub operations are mediated here. Direct GitHub API usage outside `GitHubTool` is explicitly out of bounds.

#### Persistent learning
- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread state wipes
  - must not be deleted on clean runs

- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3+ recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

These are persistent learning systems and are part of subsystem state.

#### Document-backed context handling
ForgeAgent uses the document store for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`. External document content is treated as untrusted and must be inserted into the USER prompt, never the SYSTEM prompt.

#### Failure handling and repair strategy
The subsystem includes bounded local recovery behavior driven by failure classification:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- maximum 20 local attempts, then move on

### Explicitly out of scope

#### Direct execution of generated code
ForgeAgent does not execute generated content directly:
- no `eval`
- no `exec`
- no subprocess execution of generated content

#### Direct GitHub API access
All GitHub operations must go through `GitHubTool`. Any direct GitHub API usage is outside subsystem boundaries.

#### Automatic operator bypass
ForgeAgent does not auto-approve gates and does not proceed past blocking approval states without operator input.

#### Prompt privilege escalation from external context
External documents, PR comments, and CI output are not trusted as system instructions and cannot be promoted into the SYSTEM prompt.

## Data Flow

### 1. Session establishment
ForgeAgent communicates over XPC using:
- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

On readiness, it emits:
- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Input ingestion
The subsystem accepts:
- plain-language build intent
- external documents
- PR comments
- CI output
- operator responses
- credentials
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

All such external inputs are untrusted and validated before use.

### 3. Scope analysis and confidence gate
Before implementation, ForgeAgent evaluates scope under the scope confidence gate:

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range `0–100`
  - `coverage_gaps`

- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold:
- the subsystem shows the identified gaps
- offers operator actions:
  - proceed
  - answer
  - cancel

If the operator provides gap answers:
- one-shot re-scope is performed
- no iterative re-scope loop is allowed

### 4. Context assembly
Generation context is assembled from:
- repository context
- document store content
- persistent learning artifacts:
  - `build_memory.json`
  - `build_rules.md`

`ContextManager` automatically trims context at 30k tokens while preserving:
- the spec-anchor first turn
- the last 6 messages

External document context is placed in the USER prompt only.

### 5. Multi-provider generation and arbitration
ForgeAgent generates implementation and tests using two LLM providers in parallel. Claude arbitrates consensus outcomes via the `ConsensusEngine`.

Generation is governed by the consensus and generation system prompts defined in `src/consensus.py`.

### 6. File mutation
When generated changes are ready to be materialized, every write path is validated before execution via:

- `path_security.validate_write_path()`

No file write is permitted outside validated paths.

### 7. Validation and repair loop
After generation, the subsystem performs:
- self-correction pass
- lint gate
- fix loop up to 20 local attempts

Failure strategy selection uses failure type as the primary signal and attempt count as secondary escalation. Retry behavior is bounded and non-infinite.

### 8. CI processing
ForgeAgent executes CI and ingests CI output as untrusted input.

CI log output is truncated automatically to 8k characters using:
- 70% head
- 30% tail

Polling behavior includes:
- ETag caching on all polling endpoints

Backoff behavior includes:
- `403 primary`: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary`: respect `Retry-After` header

### 9. UI streaming and gates
Progress is streamed via:
- `build_card`
  - `{ card_type, stage, content, progress }`

Blocking operator decisions are presented via:
- `gate_card`
  - `{ gate_type, options[], description }`

Gates block indefinitely until operator response. There is no auto-approve path.

### 10. Checkpointing and persistence
ForgeAgent maintains per-PR stage checkpoints so completed work is not re-run after a crash.

Persistent learning updates occur as follows:
- after every successful PR:
  - `build_memory.record_pr()` writes `workspace/{engineer_id}/build_memory.json`
- after each build run with 3+ recurring failure patterns:
  - `Mac-Docs/build_rules.md` is updated

These artifacts persist across clean runs by design.

## Key Invariants

The subsystem is constrained by the following hard invariants.

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional operational constraints derived from the core loop and failure handling:

- Scope execution is gated at confidence threshold 85.
- Re-scope after operator clarification is one-shot only.
- Failure type drives recovery strategy before attempt count does.
- Local repair is bounded to 20 attempts maximum.
- Context is automatically trimmed at 30k tokens while preserving required anchor/history structure.
- CI log presentation is bounded to 8k characters.

## Failure Modes

### Scope confidence below threshold
Condition:
- `SCOPE_SYSTEM` returns `confidence < 85`

Behavior:
- gaps are shown to the operator
- operator may proceed, answer, or cancel
- if answers are provided, exactly one re-scope pass occurs

This is a gate, not a silent downgrade.

### Auth, crypto, or identity error
Condition:
- authentication, cryptographic validation, or identity handling failure

Behavior:
- fail closed
- do not continue in degraded mode
- surface the error with context

### Security refusal
Condition:
- model or subsystem emits `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log

Rephrasing is not allowed to bypass refusal handling.

### Invalid or unsafe write path
Condition:
- target path fails `path_security.validate_write_path()`

Behavior:
- write is blocked
- error is surfaced

No unsafe file write fallback exists.

### Unknown XPC message type
Condition:
- inbound XPC message type is not recognized

Behavior:
- discard message
- log event

The subsystem does not raise exceptions for this case.

### Generation or validation failure
Condition:
- generation result fails tests, lint, imports, runtime checks, or assertions

Behavior:
- apply failure-strategy selection
- escalate by failure type first, attempt count second
- stop local retries after 20 attempts and move on

Specific strategy rules:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt

### GitHub or polling throttling
Condition:
- GitHub operation encounters rate or permission throttling

Behavior:
- `403 primary`: exponential backoff from 2s to 64s
- `429 secondary`: respect `Retry-After`
- polling uses ETag caching on all polling endpoints

### Crash or restart during staged work
Condition:
- process crash or restart mid-pipeline

Behavior:
- per-PR stage checkpoints prevent completed stages from re-running

### Oversized or noisy context
Condition:
- assembled context exceeds operational size budget

Behavior:
- `ContextManager` trims automatically at 30k tokens
- preserves spec-anchor first turn and last 6 messages

### Excessive CI log volume
Condition:
- CI output exceeds presentation budget

Behavior:
- truncate to 8k chars
- retain 70% head and 30% tail

## Dependencies

### Internal code dependencies
- `src/build_director.py`
  - `BuildPipeline`
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

- failure handling implementation in `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

### State and storage dependencies
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- `DocumentStore`

### Protocol dependencies
- XPC line-delimited JSON transport
- nonce-authenticated messaging
- message size limit: 16 MB
- message shapes:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External service dependencies
- two LLM providers in parallel
- GitHub, only through `GitHubTool`
- CI systems as external signal sources

### Security and validation dependencies
- `path_security.validate_write_path()`
- validation of all untrusted external inputs
- secret redaction discipline across logs, errors, and generated code