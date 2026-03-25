# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an ordered sequence of pull requests and drives each PR through generation, validation, correction, CI, and operator-gated merge.

At subsystem level, it is responsible for:

- Decomposing requested work into PR stages
- Running implementation and test generation using two LLM providers in parallel
- Using Claude as the arbiter in consensus
- Performing a self-correction pass
- Enforcing a lint gate
- Running a bounded 20-pass local fix loop
- Executing CI
- Blocking for operator approval before merge
- Persisting per-PR stage checkpoints so completed work is not re-run after crashes
- Persisting cross-run learning via build memory and build rules

It also integrates repository context and external documents for generation, with strict placement and trust rules:

- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt
- All external input is treated as untrusted and validated
- Generated code is never executed by the agent

The subsystem includes a scope-confidence gate before implementation proceeds:

- `SCOPE_SYSTEM` returns `confidence` (0–100) and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- If below threshold, the operator is shown gaps and may `proceed`, `answer`, or `cancel`
- If the operator answers gaps, one re-scope pass is allowed; there is no open-ended scope loop

## Component Boundaries

This subsystem is defined by the Python backend components listed in the Forge architecture context.

### In scope

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - Confidence gate handling
  - `pr_type` routing

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

- `src/build_ledger.py`
  - Per-PR stage checkpoint persistence and recovery boundary, as implied by platform invariants

- Build memory and rules persistence
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

- DocumentStore integration
  - Repository and external document loading for generation context
  - Automatic loading of `Mac-Docs/build_rules.md`

- XPC-facing message exchange relevant to build orchestration
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### Explicitly out of scope

- Direct GitHub API access outside `GitHubTool`
- Any execution of generated code via `eval`, `exec`, or subprocess of generated content
- Automatic approval of any gate
- Automatic clearing of persistent learning state
- Treating unknown XPC message types as exceptions

### Boundary enforcement rules

- All GitHub operations must go through `GitHubTool`
- All file writes must be validated via `path_security.validate_write_path()` before execution
- Unknown XPC message types are discarded and logged
- `SECURITY_REFUSAL` is terminal for the current path: stop, gate, and log; do not rephrase around it

## Data Flow

### 1. Session establishment and capabilities

The subsystem communicates over XPC using:

- Line-delimited JSON
- Nonce-authenticated messages
- Maximum 16MB per message

Startup readiness is communicated with:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

### 2. Credentials intake

Credentials are provided as:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

These credentials enable:

- Parallel LLM generation across two providers
- GitHub operations through `GitHubTool`
- Engineer-scoped persistence for build memory

Secrets are never allowed in:

- Logs
- Error messages
- Generated code

### 3. Scope and planning

The build intent is analyzed to determine scope confidence.

- `SCOPE_SYSTEM` returns:
  - `confidence`
  - `coverage_gaps`

`_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.

If confidence is below threshold:

- A gate is emitted describing gaps
- Operator options are `proceed`, `answer`, or `cancel`
- If answers are supplied, exactly one re-scope pass occurs

Gate messages use:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

Gates block indefinitely until the operator responds.

### 4. Context assembly

Generation context is assembled from repository content, document store content, and persistent learning artifacts.

Inputs include:

- Repository documents
- Specific documents such as `PRODUCT_CONTEXT.md`
- `build_memory.json`
- `build_rules.md`

Constraints:

- External document context is inserted into the `USER` prompt only
- External inputs such as documents, PR comments, and CI output are untrusted and validated
- `ContextManager` auto-trims at 30k tokens
- It preserves the spec-anchor first turn and the last 6 messages
- CI log output is truncated to 8k characters using 70% head / 30% tail

Document embedding/progress state is represented by:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

### 5. Generation and arbitration

For each PR:

- Two LLM providers generate implementation and tests in parallel
- `ConsensusEngine` arbitrates output
- Claude is the arbiter per platform overview

System prompt material originates from `src/consensus.py`:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

### 6. Local correction and validation loop

After initial generation, the subsystem performs:

- A self-correction pass
- A lint gate
- A bounded local fix loop with a maximum of 20 attempts

Failure strategy selection is defined in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Required behavior:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely — max 20 local attempts, then move on

### 7. CI execution and external polling

The subsystem executes CI and consumes CI output as untrusted input.

Operational constraints:

- 403 primary responses use exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- 429 secondary responses respect the `Retry-After` header
- All polling endpoints use ETag caching

### 8. Operator gating and merge progression

Progress and gate state are streamed using build cards and gate cards.

Build progress messages use:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

Operator approval is mandatory before merging:

- Gates wait indefinitely
- No auto-approve path exists

### 9. Checkpointing and persistent learning

The subsystem persists:

- Per-PR stage checkpoints to prevent re-running completed work after a crash
- `build_memory.json` after every successful PR via `build_memory.record_pr()`
- `build_rules.md` after each build run when 3 or more recurring failure patterns are found

Persistence semantics:

- `build_memory.json` survives fresh installs and thread state wipes
- `build_memory.json` must not be deleted on clean runs
- `build_rules.md` must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The subsystem enforces the following invariants from Forge context:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent
- Gates wait indefinitely for operator input; no auto-approve ever
- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log
- XPC unknown message types are discarded and logged, never raised as exceptions
- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory and build rules are persistent learning systems and are never cleared automatically

Additional enforced operating constraints:

- Scope confidence gating at 85 before normal progression
- One-shot re-scope only if operator supplies gap answers
- All GitHub operations must go through `GitHubTool`
- Maximum 20 local correction attempts
- Context trimming is automatic and bounded
- CI log ingestion is truncated before use as context

## Failure Modes

### Scope confidence below threshold

Condition:
- `confidence < 85` from `SCOPE_SYSTEM`

Behavior:
- Surface `coverage_gaps`
- Emit a blocking gate with `proceed`, `answer`, or `cancel`
- Allow at most one re-scope if answers are provided

### Auth, crypto, or identity failure

Condition:
- Any auth, crypto, or identity error

Behavior:
- Fail closed
- Do not continue in degraded mode
- Surface the error with context

### Security refusal

Condition:
- `SECURITY_REFUSAL` output is produced

Behavior:
- Stop the current path
- Gate for operator input
- Log the event
- Do not bypass by rephrasing

### Invalid or unsafe write path

Condition:
- A file write target fails `path_security.validate_write_path()`

Behavior:
- Do not execute the write
- Surface the failure with context

### Unknown XPC message type

Condition:
- Received message type is not recognized

Behavior:
- Discard the message
- Log the occurrence
- Do not raise as an exception

### External service throttling or permission failures

Condition:
- GitHub or polling endpoint returns 403 primary or 429 secondary

Behavior:
- 403 primary: exponential backoff up to 64s
- 429 secondary: honor `Retry-After`
- Use ETag caching on polling endpoints

### Local fix-loop exhaustion

Condition:
- 20 local attempts reached without successful resolution

Behavior:
- Stop retrying locally
- Move on rather than retry indefinitely

### Strategy-specific correction escalation

Condition:
- Failure type and attempt count trigger strategy changes

Behavior:
- `assertion_error` immediately selects `test_driven`
- `import_error` / `runtime_error` select `converse` first, then `test_driven`
- At attempt 8 or above, `nuclear` is used every third attempt

### Crash or restart mid-PR

Condition:
- Process interruption during PR execution

Behavior:
- Resume using per-PR stage checkpoints
- Do not re-run completed work

### Oversized or noisy context

Condition:
- Prompt context approaches or exceeds budget, or CI logs are excessively large

Behavior:
- `ContextManager` trims to 30k tokens
- Preserve spec-anchor first turn and last 6 messages
- Truncate CI logs to 8k chars, 70% head / 30% tail

## Dependencies

### Internal components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- `build_ledger` persistence layer
- `failure_handler.py`
- `ContextManager`
- `DocumentStore`
- `path_security.validate_write_path()`
- `build_memory.record_pr()`

### Persistent data and documents

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- Repository documents and specific loaded documents such as `PRODUCT_CONTEXT.md`

### External systems

- Two LLM providers
- GitHub, accessed only through `GitHubTool`
- CI systems and CI output streams
- XPC transport using line-delimited JSON with nonce authentication

### Protocol-level artifacts

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

These dependencies are governed by the subsystem invariants above; in particular, external inputs are always untrusted, secrets are never exposed, and no generated code is ever executed by the agent.