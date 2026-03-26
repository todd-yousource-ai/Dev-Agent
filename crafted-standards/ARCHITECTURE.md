# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding agent subsystem within Forge. It converts a plain-language build intent into an operator-gated sequence of pull requests and coordinates generation, correction, validation, CI, and merge preparation across that sequence.

From the provided architecture context, the subsystem is responsible for:

- decomposing build intent into an ordered sequence of PRs
- generating implementation and tests for each PR using two LLM providers in parallel
- using Claude as the arbiter in consensus
- running a self-correction pass
- running a lint gate
- running a bounded local fix loop of up to 20 passes
- executing CI
- blocking on operator approval before merge
- maintaining per-PR stage checkpoints so completed work is not re-run after a crash
- incorporating persistent learning via build memory and build rules
- loading and supplying external document context for generation through the proper prompt channel
- streaming build status and gate requests over the XPC protocol to the macOS UI

The subsystem also performs scope qualification before implementation work begins. The scope stage uses a confidence gate:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the agent shows gaps and offers `proceed`, `answer`, or `cancel`
- if the operator answers the gaps, the system performs a one-shot re-scope only; it does not loop indefinitely

## Component Boundaries

CraftedAgent is an orchestration and enforcement subsystem. Its boundaries are defined by the files and platform rules explicitly referenced in the source material.

### Inside the subsystem

The following components are part of the CraftedAgent execution path:

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate
  - `pr_type` routing

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

- `src/build_ledger.py`
  - implied persistence for per-PR stage checkpoints

- document-backed context loading and persistent learning systems:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

- failure strategy machinery described under `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

- XPC message production and consumption for:
  - `ready`
  - `build_card`
  - `gate_card`
  - `doc_status`
  - `credentials`

### Outside the subsystem

CraftedAgent depends on, but does not subsume, the following:

- operator decision-making
  - gates wait indefinitely for operator input
  - no auto-approve ever

- GitHub transport and API interaction
  - all GitHub operations must go through `GitHubTool`
  - never use the GitHub API directly
  - reference location: `src/github_tools.py`

- document storage and embedding lifecycle
  - DocumentStore is referenced as a provider of generation context and as the loader for `build_rules.md`
  - CraftedAgent consumes document context; it does not redefine the document storage protocol

- path validation utility
  - all file writes must be validated with `path_security.validate_write_path()` before execution

- CI execution environment
  - CraftedAgent triggers and consumes CI results, but generated code is never executed by the agent itself via `eval`, `exec`, or subprocess of generated content

### Explicit non-responsibilities

CraftedAgent does not:

- bypass operator approval
- silently continue after auth, crypto, identity, or security-refusal errors
- place external document context into the SYSTEM prompt
- execute generated code directly
- perform direct GitHub API access outside `GitHubTool`
- auto-clear persistent learning artifacts on clean runs

## Data Flow

The subsystem’s data flow is constrained by the platform protocol and prompt-handling invariants.

### 1. Session initialization

Over XPC, CraftedAgent participates in a line-delimited JSON protocol with nonce authentication and a maximum message size of 16 MB.

Initialization includes a `ready` message:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Credentials are provided via:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

Auth, crypto, or identity failures fail closed.

### 2. Build intent intake and scope analysis

The agent receives a plain-language build intent and enters the scope stage.

- `SCOPE_SYSTEM` evaluates the request
- returns:
  - `confidence`
  - `coverage_gaps`
- `_stage_scope` compares confidence against `_CONFIDENCE_THRESHOLD = 85`

If below threshold:

- the UI is shown the gaps
- the agent emits a `gate_card`
- operator options are `proceed`, `answer`, or `cancel`
- if answers are provided, one re-scope pass is allowed
- there is no repeated re-scope loop

### 3. Context assembly

Generation context may include repository information and external documents. External documents are untrusted input and must be validated.

Prompt placement is strict:

- context from external documents goes in the USER prompt
- never the SYSTEM prompt

Document status updates are surfaced using `doc_status` messages:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

The DocumentStore is used for:
- primary generation context
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatically loading `Mac-Docs/build_rules.md`

### 4. PR planning and orchestration

`BuildPipeline` decomposes the build into an ordered sequence of PRs. For each PR:

- the applicable `pr_type` route is selected
- stage progress is persisted via per-PR stage checkpoints
- completed work is not re-run after a crash

### 5. Parallel generation and consensus

For each PR, CraftedAgent uses two LLM providers in parallel for code and test generation.

- arbitration is handled by `ConsensusEngine`
- Claude acts as arbiter

Generation systems are defined in `src/consensus.py`:
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

### 6. Local validation and bounded repair

After generation, the subsystem runs:

- a self-correction pass
- a lint gate
- a bounded fix loop of up to 20 local attempts

Failure handling is selected by `_choose_strategy(failure_type, attempt, records)` with these rules:

- failure type is primary; attempt count is secondary
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — maximum 20 local attempts, then move on

Related automatic context controls:

- `ContextManager` auto-trims at 30k tokens
- preserves the spec-anchor first turn and the last 6 messages
- CI log output is truncated at 8k chars using 70% head / 30% tail

### 7. GitHub and CI interaction

All GitHub operations flow through `GitHubTool`.

- never use the GitHub API directly
- polling endpoints use ETag caching
- `403 primary` uses exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` respects the `Retry-After` header

CraftedAgent executes CI and consumes CI output as untrusted external input.

### 8. Operator gating and merge readiness

Before merge, the agent emits a blocking `gate_card`:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

The gate blocks indefinitely until the operator responds.

- no auto-approve ever
- human remains in the loop

### 9. Persistent learning updates

After every successful PR:

- `build_memory.record_pr()` writes to `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is written/updated

These are persistent learning artifacts and are intentionally retained across runs.

## Key Invariants

The subsystem is governed by the following invariants from Forge context and the referenced TRD content.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent via:
  - `eval`
  - `exec`
  - subprocess of generated content
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the system must stop, gate, and log.
- XPC unknown message types are discarded and logged; they are never raised as exceptions.

### Prompt and context handling

- External document context must be placed in the USER prompt only.
- External document context must never be placed in the SYSTEM prompt.
- Context windows are automatically trimmed at 30k tokens while preserving:
  - the spec-anchor first turn
  - the last 6 messages

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Scope re-evaluation is limited to one operator-assisted re-scope when confidence is below threshold.

### Write safety and repository mutation

- All file writes are path-validated through `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`.
- Direct GitHub API usage is prohibited.

### Recovery and persistence

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- `build_memory.json` is persistent and is not deleted on clean runs.
- `build_rules.md` is persistent and is not deleted on clean runs unless switching to a completely new codebase.
- Build memory and build rules are never cleared automatically.

### Retry and bounded work

- Failure handling is strategy-driven, not open-ended.
- Local repair is capped at 20 attempts.
- Network/API backoff behavior is explicit and bounded by protocol-specific rules.

## Failure Modes

CraftedAgent is designed to surface failures explicitly and either halt, gate, or move on according to the defined strategy rules.

### Scope uncertainty

Condition:
- `SCOPE_SYSTEM` returns confidence below `85`

Behavior:
- surface `coverage_gaps`
- present operator options: `proceed`, `answer`, `cancel`
- allow one re-scope if answers are provided
- do not enter an infinite clarification loop

### Auth, crypto, or identity failure

Condition:
- invalid credentials
- nonce/authentication failure on XPC
- identity mismatch or related integrity error

Behavior:
- fail closed
- do not degrade silently
- do not continue partial operation

### Security refusal

Condition:
- model or subsystem emits `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log
- do not retry by rephrasing around the refusal

### Unknown XPC message type

Condition:
- inbound XPC message type is not recognized

Behavior:
- discard
- log
- never raise as an exception

### Write-path violation

Condition:
- attempted file write does not pass `path_security.validate_write_path()`

Behavior:
- write must not execute
- failure must surface with context

### GitHub/API rate or permission issues

Condition:
- `403 primary`
- `429 secondary`

Behavior:
- `403 primary`: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary`: respect `Retry-After`
- polling should use ETag caching

### Local build/test failures

Condition:
- assertion, import, runtime, or repeated unresolved failures during self-correction/fix loop

Behavior:
- choose strategy with `_choose_strategy(failure_type, attempt, records)`
- apply failure-specific escalation:
  - `assertion_error` → `test_driven`
  - `import_error` / `runtime_error` → `converse`, then `test_driven`
  - from attempt 8 onward, every 3rd attempt may use `nuclear`
- stop local retries after 20 attempts

### Crash or restart mid-build

Condition:
- subsystem crash or interruption during a PR stage

Behavior:
- recover from per-PR stage checkpoints
- do not re-run completed stages

### Oversized or noisy context

Condition:
- long histories, large CI logs, or broad document context

Behavior:
- auto-trim conversational context at 30k tokens
- preserve spec-anchor first turn and last 6 messages
- truncate CI logs to 8k characters with 70/30 head-tail split

## Dependencies

Only dependencies explicitly referenced in the provided source material are included here.

### Internal code dependencies

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

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

- `path_security.validate_write_path()`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Platform and protocol dependencies

- XPC line-delimited JSON wire format
- nonce-authenticated messaging
- maximum 16 MB per message
- message schemas:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External service dependencies

- two LLM providers in parallel
- Claude as arbiter
- GitHub operations through `GitHubTool`
- CI system output consumed as external untrusted input
- DocumentStore for document loading and automatic `build_rules.md` inclusion