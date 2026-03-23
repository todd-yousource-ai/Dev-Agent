# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end orchestration subsystem for Forge’s native macOS coding agent workflow. It owns the lifecycle of a build from operator intent through scoped planning, PR decomposition, code generation, validation, CI execution, operator gating, and merge progression.

At a high level, this subsystem:

- Accepts plain-language build intent from the operator.
- Scopes the request and computes confidence/coverage gaps before execution.
- Decomposes work into an ordered sequence of pull requests.
- Coordinates parallel code generation via multiple LLM providers, with arbitration through the consensus layer.
- Runs correction and validation stages, including linting, self-correction, and bounded fix loops.
- Executes CI and presents progress/gate state to the UI over the XPC protocol.
- Persists per-PR checkpoints so completed stages are not repeated after crashes.
- Incorporates persistent learning via build memory and build rules across runs.
- Requires explicit operator approval at gates; it never auto-approves or silently continues past decision points.

This subsystem is the orchestration layer, not the implementation layer for GitHub transport, document embedding, or raw provider APIs. It composes those services and enforces platform-wide execution policy.

## Component Boundaries

### In Scope

FullPlatform includes orchestration and policy enforcement across the build pipeline, primarily centered in:

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - scope/confidence gate handling
  - PR-type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts and arbitration logic
- `src/build_ledger.py`
  - per-PR stage checkpoints and crash recovery state
- Failure handling strategy integration
  - bounded retries
  - failure-type-driven repair selection
- Build memory / build rules lifecycle integration
- XPC-facing progress/gate emission semantics as consumed by the app UI

### Explicitly Out of Scope

The subsystem does **not** directly own:

- Raw GitHub API calls  
  - all GitHub operations must go through `GitHubTool`
- Direct execution of generated code as agent instructions
  - no `eval`, `exec`, or subprocess execution of generated content
- Document embedding/index implementation details
  - these belong to the Document Store subsystem
- UI rendering
  - FullPlatform emits protocol messages such as `build_card` and `gate_card`, but does not render them
- Credential storage semantics
  - it consumes credentials but does not define secret persistence mechanisms
- Path validation implementation
  - it must call `path_security.validate_write_path()` before any file write

### Trust Boundary

FullPlatform sits at the boundary between trusted orchestration logic and untrusted external inputs. The following are always treated as untrusted:

- external documents
- PR comments
- CI output
- model outputs
- webhook payloads
- XPC payload contents beyond schema validation

It is responsible for validating, constraining, and safely routing this input into downstream stages.

## Data Flow

### 1. Session Initialization

The subsystem initializes after XPC handshake and capability exchange using line-delimited JSON messages. Relevant protocol properties:

- nonce-authenticated transport
- max 16 MB per message
- `ready` message includes:
  - `agent_version`
  - `min_swift_version`
  - `capabilities[]`
  - `doc_store_status`

Credentials are provided via:

- `credentials`
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent Intake and Scope Gating

Operator build intent enters the pipeline as natural language input. FullPlatform performs initial scoping and invokes the scope-confidence flow.

Documented behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` in range 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- gaps are surfaced to the operator
- operator options are:
  - proceed
  - answer
  - cancel
- if the operator answers gaps, one re-scope pass is allowed
- there is no unbounded re-scope loop

This stage prevents low-coverage execution from proceeding without explicit human acknowledgment.

### 3. Context Assembly

Generation context is assembled from:

- operator intent
- repository state
- selected documents from the Document Store
- persistent build memory
- persistent build rules
- prior stage outputs
- current PR/stage state from the build ledger

Constraints:

- external document context goes into the **USER** prompt, never the **SYSTEM** prompt
- Document Store is used for generation context and targeted document loading
- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - persists across fresh installs and thread-state wipes
  - must not be auto-deleted
- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded automatically by Document Store
  - written after a build run when 3+ recurring failure patterns are found
  - must not be auto-deleted except when intentionally switching to a completely new codebase

### 4. PR Planning and Sequencing

FullPlatform decomposes the build into an ordered sequence of PRs. The sequence is durable and checkpointed per PR/stage so that crashes do not cause already-completed work to be rerun.

Primary checkpoint invariant:

- per-PR stage checkpoints prevent re-running completed work after a crash

### 5. Generation and Consensus

For each PR, FullPlatform invokes parallel generation through multiple LLM providers and routes outputs through the consensus layer.

`ConsensusEngine` is responsible for:

- coordinating provider outputs
- arbitration behavior
- generation prompt selection and composition
- maintaining controlled generation contracts

FullPlatform consumes consensus outputs but continues to enforce platform execution constraints, including no execution of generated content as instructions.

### 6. Validation, Repair, and Fix Loop

After generation, the subsystem runs validation stages including:

- self-correction pass
- lint gate
- bounded local fix loop
- CI execution

Repair strategy selection follows documented failure-handling rules:

- primary signal: `failure_type`
- secondary signal: `attempt`
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

This subsystem owns the bounded orchestration of these retries, not unlimited repair recursion.

### 7. GitHub and CI Interaction

All GitHub operations are mediated through `GitHubTool`. FullPlatform must never call the GitHub API directly.

Operational rules include:

- 403 on primary requests: exponential backoff
  - 2s → 4s → 8s → 16s → 32s → 64s
- 429 on secondary requests: respect `Retry-After`
- ETag caching on all polling endpoints

CI output is treated as untrusted input and truncated automatically:

- max 8k chars
- 70% head / 30% tail

### 8. Progress and Gates

Progress is streamed to the UI via:

- `build_card`
  - `{ card_type, stage, content, progress }`

Blocking operator decisions are presented via:

- `gate_card`
  - `{ gate_type, options[], description }`

Gate semantics are strict:

- gates wait indefinitely for operator input
- there is no auto-approve behavior

### 9. Persistence and Completion

On successful PR completion:

- build memory is updated with `build_memory.record_pr()`
- recurring failure analysis may update `build_rules.md`
- stage checkpoints are committed so completed work remains durable across crashes/restarts

## Key Invariants

The subsystem must enforce the following invariants at all times:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; never auto-approve.
- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- External document context goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional operational invariants for this subsystem:

- All GitHub operations go through `GitHubTool`.
- Scope confidence below 85 requires explicit operator involvement.
- Re-scope is limited to one additional pass after operator clarification.
- Context trimming is automatic at 30k tokens.
- Context preservation prioritizes:
  - the spec-anchor first turn
  - the last 6 messages

## Failure Modes

### Scope Underconfidence

Condition:

- `SCOPE_SYSTEM.confidence < 85`

Behavior:

- show coverage gaps
- gate on operator choice: proceed / answer / cancel
- if answers are provided, perform one re-scope pass only

This is a controlled stop, not a silent downgrade.

### Auth / Crypto / Identity Failures

Condition:

- invalid credentials
- failed nonce/authentication
- identity mismatch
- cryptographic validation errors

Behavior:

- fail closed immediately
- do not continue in degraded mode
- surface contextual error without exposing secrets

### Invalid or Malicious External Input

Condition:

- malformed documents
- hostile PR comments
- malformed webhook/XPC payloads
- adversarial CI output
- unsafe model output

Behavior:

- validate and constrain input
- reject, discard, or gate as appropriate
- never elevate untrusted content into privileged prompt channels

### Unknown XPC Message Types

Condition:

- unsupported message kind received

Behavior:

- discard
- log occurrence
- do not raise exception solely due to unknown type

### Path Validation Failure

Condition:

- attempted write to disallowed or unvalidated path

Behavior:

- do not write
- surface explicit error
- no bypass around `path_security.validate_write_path()`

### GitHub Rate Limiting / Access Errors

Condition:

- 403 primary rate/access issue
- 429 secondary rate limit

Behavior:

- apply exponential backoff for 403 primary
- honor `Retry-After` for 429 secondary
- use ETag caching on polling endpoints
- do not spin aggressively or ignore server throttling

### Generation / Validation Failures

Condition:

- test failures
- import/runtime failures
- lint failures
- CI failures

Behavior:

- choose repair strategy via failure handler rules
- bound attempts to 20 local retries maximum
- escalate strategy based on failure type and attempt count
- move on or surface failure when bounded retries are exhausted

### Crash / Restart Mid-PR

Condition:

- process crash or interruption after partial completion

Behavior:

- resume from build ledger checkpoints
- do not re-run completed PR stages

### Oversized Context or Logs

Condition:

- context exceeds token budget
- CI logs exceed display budget

Behavior:

- auto-trim context at 30k tokens
- preserve spec-anchor first turn + last 6 messages
- truncate CI logs to 8k chars with 70/30 head-tail split

## Dependencies

### Internal Dependencies

- `src/build_director.py`
  - primary build orchestration entrypoint
- `src/consensus.py`
  - provider coordination and arbitration
- `src/build_ledger.py`
  - checkpoint persistence and recovery
- failure handler logic
  - strategy selection by failure type and attempt count
- Document Store
  - retrieval of generation context and automatic loading of `build_rules.md`
- build memory subsystem
  - persistence at `workspace/{engineer_id}/build_memory.json`
- path security module
  - `path_security.validate_write_path()`
- GitHub operations layer
  - `GitHubTool`
  - `WebhookReceiver`

### External Dependencies

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB message cap
- LLM providers
  - multiple providers used in parallel
  - consensus arbitration over outputs
- GitHub
  - only through `GitHubTool`
- CI systems
  - outputs consumed as untrusted input
- operator/UI
  - receives `build_card`
  - responds to `gate_card`

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- per-PR/stage checkpoint state in build ledger
- repository working tree and PR state managed through approved tool boundaries

### Dependency Rules

- Never bypass `GitHubTool` for GitHub operations.
- Never bypass path validation before writes.
- Never place external document context in the system prompt.
- Never treat provider output, CI output, or document content as trusted executable instructions.