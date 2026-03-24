# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem within the Crafted Dev Agent platform. It takes a plain-language build intent and drives an ordered pull-request-based implementation workflow.

Within that workflow, ForgeAgent is responsible for:

- decomposing work into an ordered sequence of pull requests
- generating implementation and tests for each PR using two LLM providers in parallel
- arbitrating generation through Claude
- running a self-correction pass
- running a lint gate
- running a bounded 20-pass fix loop
- executing CI
- blocking on operator approval before merge
- maintaining per-PR stage checkpoints so completed work is not re-run after a crash

ForgeAgent also manages persistent project learning inputs:

- `build_memory.json`, which survives fresh installs and thread state wipes
- `build_rules.md`, which is a self-improving rule set derived from build history

It integrates with GitHub exclusively through `GitHubTool`, uses a document store for generation context, and emits protocol messages such as `build_card`, `gate_card`, and `doc_status` over the XPC wire format.

## Component Boundaries

ForgeAgent is bounded by the following responsibilities and constraints.

### In scope

- PR-oriented build orchestration
- scope confidence gating before implementation
- generation orchestration across LLM providers
- self-correction, lint, local fix-loop, and CI progression
- operator gating for decisions that must block progress
- persistent build learning via build memory and build rules
- document-backed context loading for generation
- path-validated file writes
- GitHub operations through the repository abstraction

### Out of scope

- direct GitHub API access
- execution of generated code by the agent
- auto-approval of gates
- silent degradation on auth, crypto, or identity failures
- bypass of `SECURITY_REFUSAL` behavior by prompt rephrasing
- trusting external inputs without validation
- throwing exceptions for unknown XPC message types

### Boundary-enforcing interfaces

Documented file ownership indicates these subsystem boundaries:

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - owns confidence gate behavior
  - owns `pr_type` routing
- `src/consensus.py`
  - owns `ConsensusEngine`
  - owns generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
- `src/build_ledger.py`
  - participates in build state tracking; per-PR stage checkpoints are an explicit platform invariant

ForgeAgent must place context from external documents in the USER prompt, never the SYSTEM prompt.

## Data Flow

### 1. Intake and readiness

ForgeAgent participates in the XPC protocol using:

- line-delimited JSON
- nonce authentication
- maximum 16 MB per message

The `ready` message reports:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Scope evaluation

Before code generation, ForgeAgent performs a scope confidence gate.

Documented behavior:

- `SCOPE_SYSTEM` returns:
  - confidence `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the system:
  - shows gaps
  - offers `proceed / answer / cancel`
- if the operator provides gap answers, there is a one-shot re-scope only
- there is no looping re-scope dialogue

This gate is part of build orchestration and is owned by `BuildPipeline` in `src/build_director.py`.

### 3. Context assembly

ForgeAgent gathers generation context from the document store.

Documented usage includes:

- primary generation context loading
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatic loading of `Mac-Docs/build_rules.md` by `DocumentStore`

All context from external documents is treated as untrusted input and must be validated. External document context is inserted into the USER prompt only.

### 4. Generation and arbitration

For each PR, ForgeAgent:

- generates implementation and tests
- uses two LLM providers in parallel
- arbitrates with Claude through the consensus layer

This behavior is centered in `ConsensusEngine` in `src/consensus.py`.

### 5. File write enforcement

Any file write produced during generation or correction is constrained by path validation.

Mandatory enforcement:

- all file writes are validated via `path_security.validate_write_path()` before execution
- validate paths before any write
- committing to unexpected root directories fails silently or is rejected by path security guards unless roots are allowed

Allowed root handling must support:

- standard roots:
  - `src`
  - `tests`
  - `docs`
  - `scripts`
  - `.github`
  - `tools`
  - `schemas`
  - `contracts`
  - `configs`
- smart root detection:
  - allow any root matching `^[A-Za-z][A-Za-z0-9_-]*$`
  - this covers CamelCase or lowercase single-word roots
  - examples called out include Swift/Xcode-style roots such as:
    - `CraftedApp`
    - `CraftedTests`
    - `ForgeAgent`

Dot-prefixed roots require explicit allowlisting because most path validators reject leading dots. `.github` is therefore a special explicit root.

### 6. Correction and bounded retry loop

After generation, ForgeAgent runs:

- a self-correction pass
- a lint gate
- a local fix loop with a hard maximum of 20 attempts

Failure handling is governed by documented strategy selection in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is the primary signal
- attempt count is secondary escalation

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

### 7. CI and remote interaction

ForgeAgent executes CI and interacts with GitHub only through `GitHubTool`.

Operational controls:

- all GitHub operations go through `GitHubTool`
- never use the GitHub API directly
- `403` primary rate behavior uses exponential backoff:
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate behavior respects the `Retry-After` header
- ETag caching is used on all polling endpoints

### 8. Operator gating and presentation

ForgeAgent streams status via:

- `build_card`
  - `{ card_type, stage, content, progress }`
  - rendered to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator responds

Platform rule: gates wait indefinitely for operator input. There is no auto-approve behavior ever.

### 9. Persistence and recovery

ForgeAgent preserves state across failures and runs.

Persistent artifacts:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - must not be deleted on clean runs
- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

Recovery control:

- per-PR stage checkpoints prevent re-running completed work after a crash

### 10. Context and log shaping

ForgeAgent applies bounded context and output shaping automatically:

- `ContextManager` auto-trims at `30k` tokens
- preserves:
  - the spec-anchor first turn
  - the last 6 messages
- CI log output is truncated at `8k` characters
  - `70%` head
  - `30%` tail

## Key Invariants

ForgeAgent must enforce the following invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors.
- Never degrade silently on auth, crypto, or identity failures.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent.
- No `eval`, no `exec`, and no subprocess execution of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### File-system safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Dot-prefixed roots are rejected unless explicitly allowlisted.
- `.github` is explicitly allowlisted.
- Smart root detection permits roots matching `^[A-Za-z][A-Za-z0-9_-]*$`.
- Unexpected roots must not be written without allowlist or pattern approval.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve behavior is allowed.
- Scope confidence below threshold must surface gaps and require an operator decision.

### Protocol and robustness

- Unknown XPC message types are discarded and logged.
- They are never raised as exceptions.
- XPC messages are line-delimited JSON with nonce authentication and a 16 MB limit.
- Per-PR stage checkpoints prevent replay of already completed work after crashes.

### Persistence and learning

- Build memory is persistent and intentionally cross-run.
- Build rules are persistent and intentionally self-improving.
- Neither is automatically cleared on clean runs.

### Integration discipline

- All GitHub operations go through `GitHubTool`.
- External document context goes into the USER prompt only, never the SYSTEM prompt.

## Failure Modes

### Scope confidence failure

Condition:
- scope confidence returned by `SCOPE_SYSTEM` is below `85`

Behavior:
- surface `coverage_gaps`
- gate with `proceed / answer / cancel`
- if answers are supplied, perform one re-scope pass only
- do not enter an unbounded clarification loop

Impact:
- implementation may not proceed automatically without explicit operator choice

### Path security rejection

Condition:
- a generated or requested write targets a root outside the allowed set or smart-root pattern
- a dot-prefixed root is used without explicit allowlisting

Behavior:
- write is blocked by path validation
- unexpected roots fail due to path security guards

Impact:
- generated changes cannot be applied until paths are corrected

### Auth, crypto, or identity failure

Condition:
- any authentication, cryptographic, or identity validation error

Behavior:
- fail closed
- surface the error with context
- do not degrade silently

Impact:
- affected operation stops immediately

### Untrusted external input failure

Condition:
- documents, PR comments, or CI output contain invalid or unsafe content

Behavior:
- treat as untrusted input
- validate before use
- refuse unsafe progression where required

Impact:
- context ingestion or downstream actions may be blocked

### Security refusal

Condition:
- the model or subsystem produces `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log
- do not retry by rephrasing around the refusal

Impact:
- protected operation terminates pending operator action

### Unknown XPC message type

Condition:
- an unrecognized XPC message is received

Behavior:
- discard and log
- do not raise an exception

Impact:
- message is ignored without crashing the agent

### Fix-loop exhaustion

Condition:
- local correction attempts reach the maximum of 20

Behavior:
- do not retry indefinitely
- move on after the bounded attempt limit

Impact:
- PR progression leaves the local retry phase without infinite looping

### Strategy-specific failure escalation

Condition:
- failure handling classifies the error type and attempt number

Behavior:
- `assertion_error` uses `test_driven` immediately
- `import_error` and `runtime_error` use `converse` first, then `test_driven`
- at `attempt >= 8`, use `nuclear` every third attempt

Impact:
- retry strategy changes deterministically based on failure class and attempt count

### GitHub rate limiting or access throttling

Condition:
- GitHub returns `403` primary rate limiting or `429` secondary limiting

Behavior:
- `403`: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429`: respect `Retry-After`
- polling uses ETag caching

Impact:
- GitHub interaction slows or pauses, but does so through bounded and protocol-aware recovery behavior

### Crash during PR execution

Condition:
- subsystem crashes mid-stage

Behavior:
- resume using per-PR stage checkpoints
- do not re-run completed work

Impact:
- completed work is preserved and duplicate execution is prevented

## Dependencies

### Internal components

- `BuildPipeline` in `src/build_director.py`
- confidence gate logic in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- generation system prompt definitions in `src/consensus.py`
- `GitHubTool` in `src/github_tools.py`
- `WebhookReceiver` in `src/github_tools.py`
- build state tracking in `src/build_ledger.py`
- `failure_handler.py` strategy selection
- `ContextManager`
- `DocumentStore`
- `path_security.validate_write_path()`
- `build_memory.record_pr()`

### External/system interfaces

- XPC transport using line-delimited JSON
- nonce-authenticated message exchange
- `BuildStreamView` for streamed `build_card` rendering
- GitHub, accessed only through `GitHubTool`

### Persistent storage

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol objects

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

