# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated sequence of pull requests.

At a high level, the subsystem:

- decomposes a requested build into an ordered PR plan
- evaluates scope confidence before implementation
- generates implementation and tests using two LLM providers in parallel
- arbitrates generation through consensus
- performs self-correction, lint gating, and a bounded local fix loop
- executes CI
- blocks on operator approval before merge
- records persistent build learning across runs

The subsystem is explicitly human-gated. It does not auto-approve gates, and merge progression waits indefinitely for operator input.

The architecture context identifies the following core implementation files:

- `src/build_director.py`
  - `BuildPipeline` orchestration
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

It also integrates persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

## Component Boundaries

### In Scope

This subsystem owns:

- build orchestration for the core loop
- scope confidence evaluation and gating
- consensus-driven code generation
- document-backed generation context loading
- bounded failure recovery strategy selection
- PR-stage checkpointing to avoid re-running completed work after crashes
- GitHub operations through the approved tool boundary
- operator-facing build and gate card emission over XPC
- persistence of build memory and build rules

### Out of Scope

This subsystem does not:

- execute generated code directly via `eval`, `exec`, or subprocess of generated content
- bypass operator approval
- write files without path validation
- call the GitHub API directly outside `GitHubTool`
- trust external inputs without validation
- place external document context into the system prompt
- silently suppress auth, crypto, identity, or security refusal failures

### External Interfaces

#### XPC Protocol Boundary

The subsystem communicates over a line-delimited JSON XPC wire format with:

- nonce authentication
- maximum `16MB` per message

Relevant protocol messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator responds
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are outside the accepted interface and must be discarded and logged, never raised as exceptions.

#### GitHub Boundary

All GitHub operations must pass through `GitHubTool`. The subsystem must never use the GitHub API directly.

#### Filesystem Boundary

Any file write must be validated through:

- `path_security.validate_write_path()`

before execution.

#### Document Store Boundary

The subsystem uses the document store for generation context and for automatically loading `Mac-Docs/build_rules.md`. External documents are treated as untrusted input and validated before use.

## Data Flow

### 1. Session Initialization

The subsystem initializes with XPC and credential inputs:

- receives `ready`/capability state and document store availability
- receives `credentials` containing:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`

Initialization is fail-closed for auth, crypto, and identity errors.

### 2. Build Intent Intake

A plain-language build intent enters the pipeline. This intent becomes the source for decomposition into an ordered PR plan.

External context sources such as:

- documents
- PR comments
- CI output

are all treated as untrusted and validated.

### 3. Scope Confidence Gate

Before implementation, the subsystem runs scope analysis.

Documented behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the subsystem shows gaps
- offers operator choices:
  - proceed
  - answer
  - cancel
- if the operator provides gap answers, the subsystem performs a one-shot re-scope
- there is no looping re-scope cycle

This gate is a hard decision point in the core loop.

### 4. Context Assembly for Generation

The subsystem loads generation context from the document store for the primary generation use case, including the ability to load specific documents such as `PRODUCT_CONTEXT.md`.

Prompt placement is constrained:

- context from external documents goes into the **USER** prompt
- never into the **SYSTEM** prompt

The subsystem also loads persistent learning inputs:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

`ContextManager` automatically trims context at `30k` tokens while preserving:

- the spec-anchor first turn
- the last 6 messages

### 5. Consensus Generation

Generation is performed using two LLM providers in parallel, with Claude arbitrating. The consensus layer is implemented in `src/consensus.py` through `ConsensusEngine` and the generation system prompts.

Outputs include implementation and tests for each PR.

### 6. Post-Generation Validation and Repair

After generation, the subsystem performs:

- self-correction
- lint gate
- local fix loop

Failure handling behavior is constrained by `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is the primary signal
- attempt count is secondary escalation

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 7. CI and Output Handling

The subsystem executes CI as part of the PR pipeline.

CI output is constrained for context safety:

- log output truncated at `8k` chars
- `70%` head / `30%` tail

Polling behavior uses:

- ETag caching on all polling endpoints

Rate-limit behavior:

- `403 primary` → exponential backoff:
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header

### 8. Operator Gate and Merge Progression

The subsystem emits:

- `build_card` updates for streaming progress
- `gate_card` for blocking operator decisions

Gates wait indefinitely for operator input. There is no auto-approve path.

### 9. Persistence and Checkpointing

After every successful PR:

- `build_memory.record_pr()` writes to `workspace/{engineer_id}/build_memory.json`

Build memory characteristics:

- survives fresh installs
- survives thread state wipes
- must not be deleted on clean runs
- cross-run learning is intentional

Build rules characteristics:

- stored at `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- written after each build run when 3+ recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

Per-PR stage checkpoints prevent re-running completed work after a crash.

## Key Invariants

The subsystem must enforce the following invariants.

### Security and Trust

- Fail closed on auth, crypto, and identity errors.
- Never degrade silently on these errors.
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
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Prompt and Context Isolation

- External document context must be placed in the `USER` prompt.
- External document context must never be placed in the `SYSTEM` prompt.
- Context trimming is automatic at `30k` tokens while preserving required anchors.

### Operator Control

- Gates wait indefinitely for operator input.
- There is no auto-approve behavior ever.

### Filesystem Safety

- All file writes must be path-validated via `path_security.validate_write_path()` before execution.

### Protocol Robustness

- XPC messages are line-delimited JSON with nonce authentication.
- Maximum message size is `16MB`.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Recovery and Durability

- Per-PR stage checkpoints prevent duplicate completed work after crashes.
- Build memory is persistent and must never be cleared automatically.
- Build rules are persistent and must never be cleared automatically except when switching to a completely new codebase.
- Retry loops are bounded to 20 local attempts.

### Integration Discipline

- All GitHub operations go through `GitHubTool`.
- The GitHub API must never be used directly by this subsystem.

## Failure Modes

### Scope Confidence Failure

Condition:
- `SCOPE_SYSTEM` returns `confidence < 85`

Behavior:
- show `coverage_gaps`
- present operator options: proceed / answer / cancel
- allow one-shot re-scope only if operator answers gaps
- do not enter an unbounded clarification loop

Impact:
- implementation does not proceed as a normal high-confidence flow until operator resolution

### Auth, Crypto, or Identity Failure

Condition:
- authentication, cryptographic, or identity establishment error

Behavior:
- fail closed
- surface the error with context
- do not continue in degraded mode

Impact:
- session or dependent operation halts safely

### Security Refusal

Condition:
- model or policy returns `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log

Impact:
- generation flow cannot continue through prompt rephrasing or bypass logic

### Invalid External Input

Condition:
- malformed or untrusted external content fails validation

Examples:
- document content
- PR comments
- CI output

Behavior:
- reject or gate with surfaced error context

Impact:
- prevents tainted context from silently entering generation or control flow

### Invalid Write Path

Condition:
- target path fails `path_security.validate_write_path()`

Behavior:
- do not write
- surface error with context

Impact:
- blocks unauthorized or unsafe filesystem mutation

### Unknown XPC Message Type

Condition:
- received message type is not recognized

Behavior:
- discard
- log
- do not raise as an exception

Impact:
- protocol remains robust against unsupported or stray inputs

### Generation / Test / Runtime Failure

Condition:
- local validation fails during self-correction, linting, tests, or repair

Behavior:
- choose strategy via `_choose_strategy(failure_type, attempt, records)`

Required strategy mappings:
- `assertion_error` → `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- maximum 20 local attempts, then move on

Impact:
- failures are actively managed without infinite retry

### Rate Limiting and Polling Failure

Condition:
- GitHub or related polling endpoints rate-limit requests

Behavior:
- `403 primary` → exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After`
- use ETag caching on all polling endpoints

Impact:
- subsystem reduces request pressure while preserving correctness

### Crash / Restart During PR Processing

Condition:
- process crash or interruption after partial PR-stage completion

Behavior:
- resume from per-PR stage checkpoints
- do not re-run completed stages

Impact:
- avoids duplicate work and preserves build progress integrity

### Persistence Artifact Mismanagement

Condition:
- clean-run or reset logic attempts to delete persistent learning artifacts

Behavior:
- disallowed for:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- exception only for `build_rules.md` when switching to a completely new codebase

Impact:
- protects cross-run learning guarantees

## Dependencies

### Internal Components

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
- `ContextManager`
- `DocumentStore`

### External Services / Providers

- two LLM providers in parallel
- Claude as arbiter
- GitHub through `GitHubTool`

### Persistent Artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol / UI Surfaces

- XPC line-delimited JSON transport
- `BuildStreamView` via `build_card`
- operator gate UI via `gate_card`