# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that turns a plain-language build intent into an operator-gated sequence of pull requests. It orchestrates scoped planning, document-backed code generation, multi-model consensus, validation gates, CI execution, and operator approval before merge.

At a subsystem level, ForgeAgent:

- Decomposes build intent into an ordered PR sequence
- Runs a scope-confidence gate before execution
- Generates implementation and tests using two LLM providers in parallel
- Uses Claude as the arbiter in consensus flow
- Performs self-correction, lint gating, and up to a 20-pass local fix loop
- Executes CI and surfaces results
- Blocks on operator gate decisions with no auto-approval
- Persists per-PR stage checkpoints to avoid re-running completed work after crashes
- Persists build memory and build rules as long-lived learning artifacts across runs

The subsystem also enforces strict handling of untrusted inputs, secrets, file writes, and model prompting boundaries.

## Component Boundaries

ForgeAgent includes the orchestration and enforcement logic described in the referenced files and protocol contracts.

### Included components

- **BuildPipeline orchestration**
  - Implemented in `src/build_director.py`
  - Owns pipeline execution, confidence gating, and `pr_type` routing

- **Consensus engine**
  - Implemented in `src/consensus.py`
  - Provides `ConsensusEngine`
  - Defines generation system prompts including:
    - `GENERATION_SYSTEM`
    - `SWIFT_GENERATION_SYSTEM`
    - `UI_ADDENDUM`

- **GitHub operations layer**
  - Implemented in `src/github_tools.py`
  - Provides:
    - `GitHubTool`
    - `WebhookReceiver`
  - All GitHub operations must go through this layer

- **Build ledger / checkpoint persistence**
  - Implemented in `src/build_ledger.py`
  - Stores per-PR stage checkpoints so completed work is not repeated after a crash

- **Failure handling strategy selection**
  - Implemented in `failure_handler.py`
  - Uses `_choose_strategy(failure_type, attempt, records)`

- **Document-backed context loading**
  - Uses Document Store for generation context
  - Supports loading specific documents such as `PRODUCT_CONTEXT.md`

- **Persistent learning artifacts**
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

### Explicit boundaries

ForgeAgent does **not**:

- Execute generated code via `eval`, `exec`, or subprocess invocation of generated content
- Bypass operator gates
- Call GitHub APIs directly outside `GitHubTool`
- Trust external content without validation
- Place external document context into the system prompt
- Silently continue on auth, crypto, or identity failures

## Data Flow

The subsystem data flow is constrained by the wire protocol, prompt placement rules, validation rules, and stage persistence.

### 1. Session initialization

ForgeAgent communicates over XPC using:

- Line-delimited JSON
- Nonce-authenticated messages
- Maximum 16 MB per message

The `ready` message contains:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Credentials enter via the `credentials` payload:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Secrets from credentials are operational inputs only and must never appear in logs, errors, or generated code.

### 2. Build intent and scope gating

A plain-language build intent enters the pipeline and is scoped before execution.

Scope evaluation behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- The system shows gaps
- Offers operator options:
  - proceed
  - answer
  - cancel
- If the operator answers the gaps, ForgeAgent performs a one-shot re-scope
- There is no iterative re-scope loop

### 3. Context assembly

Generation context is assembled from repository state, document store content, build memory, and build rules.

Relevant inputs include:

- Specific repository documents such as `PRODUCT_CONTEXT.md`
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

Prompt placement rule:

- Context from external documents is placed in the **USER** prompt only
- It is never placed in the **SYSTEM** prompt

Context management constraints:

- `ContextManager` auto-trims at `30k` tokens
- It preserves:
  - the spec-anchor first turn
  - the last 6 messages

### 4. Generation and arbitration

ForgeAgent generates implementation and tests using two LLM providers in parallel. Claude arbitrates the result through the consensus flow.

This generation phase is governed by the system prompt definitions in `src/consensus.py`, including Swift/UI-specific generation variants.

### 5. Local validation and repair loop

After generation, ForgeAgent runs:

- A self-correction pass
- A lint gate
- A local fix loop up to 20 attempts

Failure strategy selection is controlled by `_choose_strategy(failure_type, attempt, records)`.

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely
- Maximum 20 local attempts, then move on

### 6. CI and output handling

ForgeAgent executes CI and consumes CI output as untrusted input.

CI log handling rules:

- Output truncated at `8k` characters
- Truncation split:
  - `70%` head
  - `30%` tail
- This is automatic

### 7. Operator gating

ForgeAgent streams UI-facing protocol messages:

- `build_card`
  - `{ card_type, stage, content, progress }`
- `gate_card`
  - `{ gate_type, options[], description }`

`gate_card` blocks until the operator responds.

The subsystem waits indefinitely for operator input. There is no auto-approve path.

### 8. Persistence and cross-run learning

After every successful PR:

- `build_memory.record_pr()` writes to:
  - `workspace/{engineer_id}/build_memory.json`

Build rules behavior:

- `Mac-Docs/build_rules.md` is loaded automatically by DocumentStore
- It is written after each build run when 3 or more recurring failure patterns are found

Persistence rules:

- Build memory is not cleared on clean runs
- Build rules are not cleared on clean runs
- These are persistent learning systems
- `build_rules.md` should only be deleted when switching to a completely new codebase

## Key Invariants

ForgeAgent is defined by the following non-negotiable invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors
- Never degrade silently on these failures
- No silent failure paths; every error must surface with context
- Secrets never appear in:
  - logs
  - error messages
  - generated code
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the system must stop, gate, and log
- Unknown XPC message types are discarded and logged, never raised as exceptions

### Prompting and context separation

- External document context belongs only in the USER prompt
- External document context must never be inserted into the SYSTEM prompt

### Human control

- Gates wait indefinitely for operator input
- There is never an auto-approve behavior

### File system safety

- All file writes must be path-validated before execution via:
  - `path_security.validate_write_path()`

### Recovery and persistence

- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory is persistent across fresh installs and thread state wipes
- Build rules are persistent across runs unless switching to a completely new codebase
- These learning artifacts are never cleared automatically

### Network and polling discipline

- `403` from primary: exponential backoff sequence `2s → 4s → 8s → 16s → 32s → 64s`
- `429` from secondary: respect `Retry-After`
- ETag caching applies on all polling endpoints

## Failure Modes

ForgeAgent surfaces failures explicitly and routes them through defined gates or strategies.

### Scope uncertainty

Condition:

- Scope confidence below `_CONFIDENCE_THRESHOLD = 85`

Behavior:

- Surface `coverage_gaps`
- Gate on operator choice:
  - proceed
  - answer
  - cancel
- Allow one-shot re-scope if answers are provided
- Do not loop indefinitely

### Auth, crypto, or identity errors

Condition:

- Any authentication, cryptographic, or identity validation failure

Behavior:

- Fail closed
- Do not degrade or continue silently
- Surface the error with context
- Do not leak secrets in the surfaced error

### Security refusal from model output

Condition:

- Model emits `SECURITY_REFUSAL`

Behavior:

- Stop processing
- Gate
- Log the event
- Do not retry by rephrasing around the refusal

### Invalid or unknown XPC input

Condition:

- Unknown XPC message type

Behavior:

- Discard the message
- Log it
- Do not raise it as an exception

### Write-path violations

Condition:

- A file write has not passed `path_security.validate_write_path()`

Behavior:

- Write must not execute

### Generation/test/lint/runtime failures

Condition:

- Local validation or execution failures during repair loop

Behavior:

- Use `_choose_strategy(failure_type, attempt, records)`
- Apply strategy by failure type first, attempt count second
- Escalate to `nuclear` every third attempt once `attempt >= 8`
- Stop local retries after 20 attempts

### GitHub/API throttling and access failures

Condition:

- `403` on primary
- `429` on secondary

Behavior:

- `403`: exponential backoff through 64 seconds
- `429`: honor `Retry-After`
- Use ETag caching on polling endpoints

### Crash/restart during PR execution

Condition:

- Subsystem crash or restart mid-pipeline

Behavior:

- Resume from per-PR stage checkpoints
- Do not re-run already completed stages

## Dependencies

ForgeAgent depends on the following subsystem interfaces, stores, and protocol contracts.

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

- `src/build_ledger.py`
  - per-PR stage checkpoint persistence

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

- `path_security.validate_write_path()`
  - mandatory precondition for all writes

### Data and document dependencies

- DocumentStore
  - used for generation context
  - automatically loads `Mac-Docs/build_rules.md`

- `workspace/{engineer_id}/build_memory.json`
  - persistent build memory
  - survives fresh installs and thread state wipes

- `Mac-Docs/build_rules.md`
  - persistent self-improving coding rules derived from build history

- Repository documents such as `PRODUCT_CONTEXT.md`
  - loadable as specific generation context

### External service dependencies

- Two LLM providers used in parallel generation
- Claude used as arbiter
- GitHub accessed only through `GitHubTool`

### Protocol dependencies

- XPC wire format
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB max message size

- Message contracts
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

These protocol contracts define the transport and operator-visible status surface for ForgeAgent.