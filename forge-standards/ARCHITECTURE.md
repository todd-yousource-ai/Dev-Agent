# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end orchestration subsystem for Forge’s native macOS AI coding agent workflow. It coordinates the complete build lifecycle from user build intent through scoped planning, pull-request decomposition, multi-provider code generation, validation, CI execution, operator gating, and merge progression.

At a high level, this subsystem is responsible for:

- Accepting a plain-language build intent and turning it into an ordered sequence of PR-sized work units.
- Running scope analysis and confidence gating before implementation begins.
- Loading persistent contextual knowledge from the document store, build memory, and build rules.
- Driving generation through parallel LLM providers with consensus/arbitration.
- Running correction and validation stages, including lint, self-correction, and bounded fix loops.
- Executing GitHub operations exclusively through the GitHubTool abstraction.
- Streaming progress and gate state to the macOS frontend over XPC.
- Persisting per-PR stage checkpoints so interrupted builds resume without re-running completed stages.
- Preserving long-lived learning artifacts across runs.

This subsystem is the execution spine of the platform. It does not merely invoke tools; it enforces workflow sequencing, gating semantics, retry limits, persistence behavior, and platform safety constraints.

## Component Boundaries

FullPlatform includes orchestration logic and policy enforcement for the build pipeline, but it is not the implementation owner of every lower-level concern. Its boundaries are as follows.

### In Scope

- Build pipeline orchestration in `src/build_director.py`
- Multi-model generation consensus in `src/consensus.py`
- GitHub operation routing through `src/github_tools.py`
- Build checkpoint and stage persistence in `src/build_ledger.py`
- Scope confidence gating and re-scope behavior
- DocumentStore-backed contextual retrieval for generation
- Build memory and build rules loading/writing behavior
- Failure handling strategy selection and bounded retry behavior
- XPC message production/consumption for platform coordination
- Operator gate enforcement for any blocking approval or clarification step

### Out of Scope

- Direct implementation of LLM provider SDK internals
- Direct GitHub API calls outside `GitHubTool`
- UI rendering details of `BuildStreamView`
- Execution of generated code via dynamic evaluation mechanisms
- Automatic policy override when safety or refusal conditions trigger
- Non-platform-specific editor or IDE integration logic
- Autonomous merge approval without explicit operator action

### Boundary Rules

- All GitHub interactions must traverse `GitHubTool`; FullPlatform must not call GitHub APIs directly.
- All file writes performed under this subsystem must be path-validated via `path_security.validate_write_path()` before execution.
- External content consumed by the subsystem is treated as untrusted input and validated before use.
- FullPlatform may generate code and patch files, but must never execute generated content via `eval`, `exec`, or subprocess invocation of generated artifacts.

## Data Flow

### 1. Session Initialization

The subsystem initializes over XPC using line-delimited JSON messages with nonce authentication and a maximum message size of 16 MB. The platform consumes or emits:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent Intake and Scoping

A build begins from a plain-language user intent. FullPlatform performs initial decomposition and scope analysis. The scope stage uses a confidence gate:

- The scope system returns:
  - `confidence` in `[0, 100]`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- The operator is shown the identified gaps.
- Available actions are:
  - proceed
  - answer
  - cancel
- If the operator answers the gaps, the subsystem performs exactly one re-scope pass.
- There is no unbounded clarification loop.

### 3. Context Assembly

Generation context is assembled from persistent and retrieved sources:

- Repository and workspace state
- DocumentStore retrieval
- Specific loaded documents such as `PRODUCT_CONTEXT.md`
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

Context from external documents is placed in the USER prompt only, never in the SYSTEM prompt.

The context manager auto-trims at 30k tokens while preserving:

- The spec-anchor first turn
- The last 6 messages

### 4. PR Planning and Execution

The build intent is decomposed into an ordered sequence of PRs. For each PR, FullPlatform orchestrates staged execution with persisted checkpoints to prevent duplicate work after interruption.

Typical stage progression includes:

1. Scope / planning
2. Code generation
3. Consensus / arbitration
4. Self-correction pass
5. Lint gate
6. Local fix loop
7. CI execution
8. Operator approval gate
9. Merge progression

Per-PR stage checkpoints ensure a crash or restart does not re-run already completed stages.

### 5. Generation and Consensus

Generation is executed against two LLM providers in parallel. Claude serves as arbiter in the consensus path. The consensus subsystem, defined in `src/consensus.py`, owns the generation system prompts and provider-comparison flow.

FullPlatform uses this layer to obtain implementation output, compare alternatives, and select the accepted candidate for downstream validation.

### 6. Validation and Repair

After initial generation:

- A self-correction pass is run.
- Lint is executed as a gate.
- A bounded local repair loop runs for up to 20 attempts.

Failure strategy selection follows `failure_handler.py:_choose_strategy(failure_type, attempt, records)`:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely; max 20 local attempts, then move on

### 7. CI and Log Handling

CI is executed as part of PR validation. CI output is treated as untrusted input. Log handling behavior:

- CI log output is truncated to 8k chars
- Truncation preserves 70% head / 30% tail

Polling behavior must use:

- ETag caching on all polling endpoints
- Exponential backoff for 403 primary:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `Retry-After` compliance for 429 secondary responses

### 8. Streaming and Operator Gates

Progress is streamed to the frontend using:

- `build_card`
  - `{ card_type, stage, content, progress }`

Blocking decisions are surfaced with:

- `gate_card`
  - `{ gate_type, options[], description }`

Gates wait indefinitely for operator input. There is no auto-approve behavior.

### 9. Persistence and Learning

After each successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are detected:

- `Mac-Docs/build_rules.md` is updated

These learning artifacts are persistent and must not be automatically cleared on clean runs.

## Key Invariants

The following invariants are enforced by FullPlatform and must hold across all execution paths:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets must never appear in logs, error messages, prompts, or generated code.
- All external inputs are untrusted and must be validated.
- Generated code is never executed by the agent through `eval`, `exec`, or subprocess execution of generated content.
- Gates wait indefinitely for explicit operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents belongs in USER prompts only, never SYSTEM prompts.
- `SECURITY_REFUSAL` output is terminal for the current action: stop, gate, and log; do not bypass by rephrasing.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent replay of already completed work after crashes.
- Build memory and build rules are persistent learning systems and are never automatically cleared.

Additional subsystem-specific enforcement:

- Scope confidence below threshold requires explicit operator involvement.
- Clarification allows at most one re-scope pass per gating event.
- Retry loops are bounded to 20 local attempts.
- All GitHub operations must go through `GitHubTool`.
- Polling and rate-limit behavior must respect cache and backoff policy.
- Context trimming is automatic and deterministic at 30k tokens.

## Failure Modes

### Auth, Crypto, or Identity Failure

Behavior:

- Immediate fail-closed behavior
- No fallback to degraded or anonymous operation
- Error must surface with context, excluding secrets

### Low Scope Confidence

Behavior:

- Build does not silently proceed as fully trusted scope
- Operator receives coverage gaps and must choose proceed, answer, or cancel
- At most one re-scope occurs after operator answers

Risk controlled:

- Implementing under-specified or mis-scoped work without human review

### Provider Disagreement or Weak Generation Output

Behavior:

- Consensus/arbitration path selects between parallel provider outputs
- Downstream self-correction and repair loop may attempt recovery
- If unresolved within bounded attempts, stage fails and surfaces

Risk controlled:

- Unvetted single-model output progressing unchecked

### Local Validation Failure

Examples:

- Lint failure
- Assertion failure
- Import/runtime failure

Behavior:

- Failure strategy selected by failure type
- Escalation based on attempt count
- Hard stop after 20 attempts

Risk controlled:

- Infinite repair loops
- Incorrect retry strategy selection

### GitHub API / Remote Service Failure

Examples:

- 403 primary rate/permission failure
- 429 secondary rate limit
- Polling inconsistency

Behavior:

- 403 primary uses exponential backoff
- 429 honors `Retry-After`
- Polling uses ETag caching
- Operations remain mediated by `GitHubTool`

Risk controlled:

- API abuse, unstable polling, direct API misuse

### Crash / Restart Mid-Build

Behavior:

- Resume from per-PR stage checkpoint
- Do not repeat completed stages

Risk controlled:

- Duplicate commits, duplicate PR actions, inconsistent state progression

### XPC Protocol Anomalies

Examples:

- Unknown message type
- Oversized or malformed payload

Behavior:

- Unknown message types are discarded and logged
- Message handling must remain robust and non-throwing for unknown types

Risk controlled:

- Frontend/backend desynchronization causing agent crash

### Unsafe Write or Path Traversal Attempt

Behavior:

- Reject write before execution unless validated by `path_security.validate_write_path()`

Risk controlled:

- Repository escape, arbitrary file overwrite, unsafe filesystem mutation

### Security Refusal Trigger

Behavior:

- Stop current action
- Gate and log refusal outcome
- Do not retry by paraphrasing around the refusal

Risk controlled:

- Policy bypass through prompt rewording

## Dependencies

### Internal Components

- `src/build_director.py`
  - Primary orchestration entrypoint for BuildPipeline, confidence gate, and PR-type routing
- `src/consensus.py`
  - ConsensusEngine and generation/arbitration system prompts
- `src/github_tools.py`
  - `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py`
  - Stage and checkpoint persistence
- `failure_handler.py`
  - Failure strategy selection and escalation policy
- `path_security`
  - Required write-path validation before filesystem mutation
- Context/document management layer
  - Document retrieval and prompt-context assembly

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - Cross-run build memory
- `Mac-Docs/build_rules.md`
  - Persistent self-improving rule set
- DocumentStore-managed project and product documents
  - Including documents such as `PRODUCT_CONTEXT.md`

### External Interfaces

- XPC transport
  - Line-delimited JSON
  - Nonce-authenticated
  - 16 MB max message size
- LLM providers
  - Two providers in parallel for generation
  - Claude as arbitration authority in consensus flow
- GitHub
  - Accessed only through `GitHubTool`
- CI systems
  - Output treated as untrusted input

### Dependency Constraints

- External document context must never be elevated into SYSTEM prompts.
- Secret-bearing dependencies must not leak values into logs or surfaced errors.
- Generated artifacts are data for review and validation, not executable instructions for the agent runtime.
- Persistent learning dependencies (`build_memory.json`, `build_rules.md`) are part of normal operation and must survive clean runs.