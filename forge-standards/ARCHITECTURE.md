# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS coding agent. It is responsible for turning a plain-language build intent into a gated, checkpointed, multi-stage implementation workflow that produces reviewed pull requests, executes validation, and waits for operator approval before merge.

At a high level, this subsystem:

- Accepts operator intent and repository context
- Performs scope analysis and confidence gating before implementation
- Decomposes work into an ordered sequence of PRs
- Retrieves supporting context from the document store and persistent build knowledge
- Coordinates parallel code generation through multiple LLM providers, with arbitration
- Runs correction, lint, and bounded fix loops
- Executes CI and surfaces results
- Emits build and gate cards to the UI over XPC
- Persists per-PR checkpoints to allow crash-safe resume
- Persists cross-run learning in build memory and build rules

This subsystem is orchestration-centric. It does not directly own provider-specific inference internals, low-level GitHub API calls, or arbitrary code execution of generated outputs. It composes those capabilities under strict safety, validation, and gating rules.

## Component Boundaries

### In Scope

FullPlatform owns the orchestration of the build lifecycle, including:

- Build stage sequencing and PR progression
- Scope confidence evaluation and operator gating
- Routing by PR type and stage
- Consensus-driven generation flow
- Integration of document context into generation inputs
- Integration of persistent build memory and build rules
- Fix-loop orchestration with bounded retry policy
- CI result handling and truncation policy
- Build/gate card emission for UI consumption
- Crash recovery using per-PR stage checkpoints

Primary implementation anchors:

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate
  - PR-type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts and arbitration behavior
- `src/build_ledger.py`
  - stage checkpointing and durable progress tracking
- Related failure handling logic
  - strategy selection based on failure type and attempt count

### Out of Scope

FullPlatform does not directly own:

- Raw GitHub API access
  - All GitHub operations must go through `GitHubTool`
- UI rendering
  - It emits protocol messages/cards; UI components render them
- Arbitrary execution of generated code
  - Generated code is never executed by the agent via `eval`, `exec`, or subprocess of generated content
- Authentication or credential issuance
  - It consumes credentials supplied over the platform protocol
- Low-level XPC transport implementation
  - It conforms to the wire protocol and message semantics
- Long-term document embedding internals
  - It consumes document store state and retrieval results

### Trust Boundary

FullPlatform sits at the boundary between trusted internal orchestration and multiple untrusted inputs:

- operator-provided build intent
- external documents
- PR comments
- CI output
- GitHub-originated content
- LLM outputs from external providers
- XPC messages from counterpart processes

All such inputs are treated as untrusted and must be validated, constrained, or sanitized before use.

## Data Flow

### 1. Session Establishment

The subsystem participates in platform initialization via XPC line-delimited JSON messages, with nonce authentication and a maximum message size of 16 MB.

Relevant protocol messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

These inputs establish:

- runtime capability negotiation
- document store availability
- identity-scoped persistence location
- provider access for generation
- GitHub access for repository operations

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Build Intent Intake and Scope Analysis

The operator supplies a build intent. FullPlatform performs a scope analysis pass before implementation.

The scope stage:

- evaluates confidence on a 0–100 scale
- identifies `coverage_gaps`
- gates in `_stage_scope` at `_CONFIDENCE_THRESHOLD = 85`

Behavior below threshold:

- present gaps to the operator
- offer `proceed`, `answer`, or `cancel`
- if the operator answers the gaps, perform one re-scope pass only
- no open-ended re-scoping loop is allowed

This stage prevents low-confidence implementation from silently proceeding without explicit operator choice.

### 3. Context Assembly

Before generation, FullPlatform assembles context from:

- repository state
- operator intent
- document store retrieval
- specific project documents where needed
- persistent `build_memory.json`
- persistent `build_rules.md`

Document usage constraints:

- context from external documents goes into the `USER` prompt only
- never place external document content in the `SYSTEM` prompt

Persistent knowledge sources:

- `workspace/{engineer_id}/build_memory.json`
  - updated after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread state wipes
  - never automatically deleted
- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - updated after a build run when 3 or more recurring failure patterns are detected
  - never automatically deleted unless switching to a completely new codebase

### 4. PR Planning and Sequencing

FullPlatform decomposes the build into an ordered sequence of PRs. It tracks each PR independently with stage checkpoints so completed work is not repeated after a crash.

Checkpointing guarantees:

- per-PR stage durability
- resume from last completed checkpoint
- no unnecessary re-execution of completed stages

This is a hard invariant: completed work for a PR must not be rerun solely because of process interruption.

### 5. Multi-Provider Generation and Arbitration

Implementation generation is coordinated through the consensus engine.

Expected flow:

- prepare system and user prompts
- invoke multiple LLM providers in parallel
- arbitrate outputs using the consensus mechanism
- produce candidate implementation and tests
- proceed to validation/correction stages

Consensus is defined centrally in:

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`

The subsystem may tailor generation behavior by PR type and stage via routing logic in `BuildPipeline`.

### 6. Correction, Lint, and Fix Loop

After generation, FullPlatform executes a bounded validation and repair process:

- self-correction pass
- lint gate
- local fix loop
- CI execution

Failure-handling behavior is strategy-driven, using failure type as the primary signal and attempt count as secondary escalation.

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- attempt `>= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Operational controls:

- CI log output truncated to 8k chars
  - 70% head / 30% tail
- Context manager auto-trims at 30k tokens
  - preserves the spec-anchor first turn
  - preserves the last 6 messages

### 7. GitHub and Merge Gating

All GitHub operations are mediated through `GitHubTool`.

Hard rule:

- never use the GitHub API directly from FullPlatform

This includes operations such as:

- PR creation/update
- status polling
- merge-related actions
- webhook-driven events

Operator approval is mandatory before merge. Gates block indefinitely until the operator responds; there is no auto-approval path.

UI-visible gating uses `gate_card` messages:

- `{ gate_type, options[], description }`

Progress/status is streamed via `build_card` messages:

- `{ card_type, stage, content, progress }`

## Key Invariants

The following invariants are enforced by FullPlatform and must not be weakened:

- Fail closed on auth, crypto, and identity errors
  - never degrade silently
- No silent failure paths
  - every error must surface with context
- Secrets never appear in:
  - logs
  - error messages
  - generated code
- All external input is untrusted and validated
  - documents
  - PR comments
  - CI output
  - XPC payloads
  - LLM outputs
- Generated code is never executed by the agent
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- Gates wait indefinitely for operator input
  - no auto-approve ever
- All file writes must be path-validated through `path_security.validate_write_path()` before execution
- External document context must be placed in the `USER` prompt only
  - never in the `SYSTEM` prompt
- `SECURITY_REFUSAL` output is terminal for that action
  - do not bypass by rephrasing
  - stop, gate, and log
- Unknown XPC message types are discarded and logged
  - never raised as exceptions
- Per-PR stage checkpoints prevent rerunning completed work after a crash
- Build memory and build rules are persistent learning systems
  - never automatically cleared on clean runs

Additional operational invariants:

- Scope confidence gate threshold is 85
- Re-scope on gap answers is one-shot only
- Retry behavior is bounded to 20 local attempts
- Failure strategy is selected primarily by failure type, not raw retry count
- All GitHub operations go through `GitHubTool`
- Polling should use ETag caching where supported
- `403` primary rate/abuse handling uses exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429` secondary handling must respect `Retry-After`

## Failure Modes

### Scope Confidence Below Threshold

Condition:

- scope confidence `< 85`

Behavior:

- show coverage gaps
- gate operator with options to proceed, answer, or cancel
- if answers are provided, perform one re-scope pass
- otherwise do not silently continue as though confidence were sufficient

Risk controlled:

- under-specified implementation
- missing requirements
- false confidence in generated plans

### Auth, Credential, Crypto, or Identity Failure

Condition:

- invalid or missing credentials
- identity mismatch
- cryptographic verification failure
- nonce/authentication issue on protocol messages

Behavior:

- fail closed
- stop affected operation
- surface contextual error
- never downgrade to unauthenticated or partially authenticated execution

Risk controlled:

- unauthorized access
- cross-identity contamination
- protocol spoofing

### Untrusted Input Validation Failure

Condition:

- malformed external document content
- invalid PR comment payload
- oversized or malformed XPC message
- unsafe CI output handling
- invalid path for file write

Behavior:

- reject or constrain input
- log with context, excluding secrets
- do not continue with unsafe assumptions

Risk controlled:

- prompt injection
- filesystem escape
- parser abuse
- state corruption

### Generation Refusal or Security Refusal

Condition:

- model emits `SECURITY_REFUSAL`
- output violates security constraints

Behavior:

- stop the action
- gate/log appropriately
- never attempt bypass by paraphrasing or retrying around the refusal

Risk controlled:

- policy circumvention
- unsafe code generation
- adversarial prompt adaptation

### Local Validation Failure

Condition:

- generated code fails lint, tests, import checks, runtime checks, or assertions

Behavior:

- choose repair strategy using failure type and attempt count
- remain within bounded retry budget
- after 20 attempts, stop local retry and move forward to the next handling path

Risk controlled:

- infinite correction loops
- unstructured retries
- repeated ineffective repair attempts

### GitHub Rate Limiting / API Pressure

Condition:

- `403` primary rate or abuse responses
- `429` throttling responses

Behavior:

- `403`: exponential backoff up to 64 seconds
- `429`: honor `Retry-After`
- use ETag caching on polling endpoints

Risk controlled:

- API bans
- excessive polling
- wasted retries

### Crash or Process Interruption

Condition:

- agent or host process exits mid-build

Behavior:

- recover from per-PR stage checkpoints
- do not rerun completed PR stages

Risk controlled:

- duplicate changes
- repeated external actions
- wasted provider/API spend

### Unknown XPC Message Type

Condition:

- message type not recognized by the protocol handler

Behavior:

- discard
- log occurrence
- do not raise exception

Risk controlled:

- protocol fragility
- crash on forward-incompatible messages

## Dependencies

### Internal Dependencies

- `BuildPipeline` in `src/build_director.py`
  - orchestrates stage flow, routing, and confidence gate
- `ConsensusEngine` in `src/consensus.py`
  - coordinates multi-provider generation and arbitration
- `build_ledger` in `src/build_ledger.py`
  - persists stage checkpoints and recovery state
- failure handling subsystem
  - selects repair strategy by failure type / attempt
- path security subsystem
  - `path_security.validate_write_path()` for every write
- document store
  - retrieval and automatic loading of `build_rules.md`
- build memory persistence
  - identity-scoped durable learning across runs

### External Dependencies

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - max 16 MB per message
- LLM providers
  - Anthropic
  - OpenAI
- GitHub via `GitHubTool`
  - never direct API access from this subsystem
- CI systems and their output streams
- operator-driven UI components consuming:
  - `build_card`
  - `gate_card`
  - `doc_status`
  - `ready`

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - durable per-engineer build learning
- `Mac-Docs/build_rules.md`
  - durable repository-level learned rules

### Dependency Constraints

- External document content must remain in user-level prompt context
- Secrets provided through credentials must never be logged or reflected
- All filesystem writes dependent on this subsystem must be path-validated before execution
- External service failures must surface explicitly; no silent degradation is permitted