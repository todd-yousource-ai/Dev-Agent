# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge platform subsystem responsible for orchestrating end-to-end AI-assisted software delivery from a plain-language build intent to a gated mergeable pull request sequence.

At a high level, it:

- accepts operator build intent and repository context
- decomposes the requested work into an ordered PR plan
- generates implementation and tests for each PR using multiple LLM providers in parallel
- arbitrates generation outcomes via the consensus engine
- runs a structured review cycle
- executes CI and routes CI outcomes back into the build loop
- blocks on explicit operator approval at every gate before merge or irreversible progression
- persists and restores build progress across restarts using layered recovery state
- detects and resolves divergence between local and GitHub-backed recovery state

It is a workflow orchestration subsystem, not a code execution sandbox. It may generate code, review text, PR plans, and build metadata, but it must not execute generated code directly.

Recovery behavior is part of the subsystem contract:

- `/continue` resumes a build from the current thread state and emits:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`
- `/restore` loads persisted state layers
- when `/restore` is invoked without a target, the subsystem compares local and GitHub recovery layers and either:
  - restores silently if they agree, or
  - enters explicit conflict resolution if they diverge

Divergence detection specifically compares persisted build fields and surfaces conflicting fields such as:

- `completed_prs`
- `pr_plans_by_prd`

On divergence, the subsystem presents both snapshots, identifies conflict fields, and requires the operator to choose one authoritative source:

- `local` → restore local and overwrite GitHub state
- `github` → restore GitHub and overwrite local state
- `cancel` → modify neither layer and return to prompt

In non-interactive mode, auto-resolution rules apply, but the subsystem still treats divergence as a first-class recovery event rather than silently reconciling state.

## Component Boundaries

ConsensusDevAgent is bounded to orchestration, state management, provider coordination, and gate enforcement. It does not own general-purpose repository hosting, OS-level execution policy, or arbitrary external API access.

### In Scope

- build pipeline orchestration
- PR decomposition and ordered execution
- LLM generation dispatch and arbitration
- review-cycle coordination
- CI result ingestion and routing
- operator gate presentation and blocking behavior
- recovery-state persistence, restoration, and divergence handling
- build progress reporting through structured cards
- GitHub operations mediated through the approved GitHub abstraction
- path-validated file write orchestration

### Out of Scope

- direct execution of generated code
- bypassing human approval gates
- direct GitHub API usage outside the GitHub tool layer
- storage of secrets in logs, prompts, or generated artifacts
- trust of external document or CI content without validation
- modifying files without path validation
- changing transport semantics of XPC or UI rendering semantics outside the documented protocol

### Internal Component Responsibilities

#### `src/consensus.py`
Owns:

- `ConsensusEngine`
- generation system prompts and provider arbitration logic
- provider retry/fallback behavior between Claude and OpenAI

This component decides how candidate outputs from multiple providers are compared and selected, but it does not directly own GitHub mutation or build-stage orchestration.

#### `src/build_director.py`
Owns:

- `BuildPipeline` orchestration
- stage dispatch across planning, generation, review, CI, and gate phases

This is the primary workflow coordinator for the subsystem.

#### `src/github_tools.py`
Owns:

- `GitHubTool`
- `WebhookReceiver`

All GitHub reads/writes must pass through `GitHubTool`. The subsystem must never call the GitHub API directly.

#### `src/build_ledger.py`
Owns:

- `BuildLedger`

This component persists and retrieves build progress/state used for resume, restore, and divergence detection.

### External Boundary Contracts

#### XPC Boundary
The subsystem communicates over a line-delimited JSON XPC wire format with:

- nonce authentication
- maximum 16 MB per message

Relevant protocol objects include:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

The subsystem must discard and log unknown XPC message types rather than raising exceptions.

#### UI Boundary
The subsystem emits:

- `build_card` for streamed stage/progress content
- `gate_card` for blocking operator decisions

The UI renders these messages, but gate semantics are owned by ConsensusDevAgent: a gate blocks indefinitely until the operator responds.

#### Document Context Boundary
External documents are untrusted input. Their content may be supplied to the model only in the user prompt context, never the system prompt.

## Data Flow

### 1. Initialization and Readiness

On startup, the subsystem initializes provider availability, document-store status, and capability metadata, then emits a `ready` message:

- `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

This stage establishes protocol compatibility and runtime readiness.

### 2. Build Intent Ingestion

The operator provides plain-language build intent and repository context. The subsystem treats all external content as untrusted, including:

- attached or retrieved documents
- PR comments
- CI output
- GitHub-derived text

Relevant contextual documents are loaded and inserted into user-level prompt context only.

### 3. Planning and PR Decomposition

The build pipeline decomposes the requested work into an ordered set of PRs, grouped by PRD or equivalent planning unit. Planning state is recorded in the ledger, including structures such as:

- planned PR sequence
- per-PRD PR plans
- completed PR tracking

### 4. Generation and Consensus

For each PR:

- generation prompts are prepared
- provider calls are issued to the supported LLM backends
- outputs are compared and arbitrated by `ConsensusEngine`
- retries/fallback occur within bounded policy:
  - `_claude_json`: retry after 10 seconds, then fall back to OpenAI
  - `consensus.py`: retry with the other provider
  - never retry indefinitely; maximum 3 attempts total
  - `403` primary rate/permission failures: exponential backoff starting at 60 seconds
  - `429` secondary limits: respect `Retry-After` exactly

Generated code and tests are produced as artifacts for repository update, but are never executed directly by the subsystem.

### 5. Repository Mutation

When writing generated or transformed files:

- target paths must be validated via `path_security.validate_write_path()` before any write
- writes must fail closed on path validation errors
- all GitHub operations must go through `GitHubTool`
- blind GitHub writes are forbidden; writes must be SHA-aware where applicable

### 6. Review and CI

The subsystem performs the configured review cycle and then executes or consumes CI results. CI output is treated as untrusted input and validated before use in prompts or decision logic.

Polling behavior for remote state uses:

- ETag caching on all polling endpoints

### 7. Gating

At decision points, the subsystem emits `gate_card` messages:

- `{ gate_type, options[], description }`

Gate behavior is strict:

- gates never auto-resolve
- they block indefinitely until operator input
- if the backend restarts mid-gate, gate state is lost and the operator must re-approve
- there is no undo for gate decisions

### 8. Persistence, Continue, and Restore

Build progress is persisted to recovery layers:

- local state
- GitHub-backed state

`/continue` resumes from the current thread state.

`/restore` reloads persisted state. If no explicit target is provided, the subsystem compares both layers:

- if equal: restore normally with a single confirmation
- if divergent: present both snapshots and conflict fields, then require source selection

Selected source becomes authoritative and is propagated to the other layer unless the operator cancels.

## Key Invariants

The subsystem must preserve the following invariants at all times.

### Security and Trust Invariants

- Fail closed on authentication, cryptography, and identity errors.
- Never degrade silently on auth or identity failures.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, or generated code.
- Secrets must never appear in prompts unless explicitly required by a secure interface; credentials are not prompt context.
- All external input is untrusted and validated before use.
- Context from external documents must go in the user prompt, never the system prompt.
- `SECURITY_REFUSAL` is terminal for the attempted action: do not rephrase, bypass, or retry around it.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Execution Invariants

- Generated code is never executed by the agent.
- No `eval`, `exec`, or subprocess execution of generated content.
- Shell injection patterns are forbidden.
- Path traversal is forbidden.
- Every file write must be validated via `path_security.validate_write_path()` before execution.

### Workflow Invariants

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.
- Gate decisions are not implicitly replayed after restart.
- If restart occurs during a gate, operator approval must be re-collected.
- No undo exists for gate decisions; this must be treated as explicit workflow semantics.
- Recovery divergence is never silently reconciled when interactive operator choice is required.

### Integration Invariants

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Blind GitHub writes without SHA protection are forbidden.
- Retry behavior is bounded to a maximum of 3 attempts total.
- `429` handling must respect `Retry-After` exactly.
- `403` primary failures use exponential backoff starting at 60 seconds.
- ETag caching is required on polling endpoints.

### Resource Invariant

- Allocations must be kept minimal.
- Every allocation should be explicit and documented, per unresolved OI-13 guidance.

## Failure Modes

### Recovery-State Divergence

**Condition:** local and GitHub recovery layers disagree during `/restore` without an explicit target.

**Behavior:**

- display both state snapshots
- show save timestamps and relative age
- enumerate conflicting fields
- require operator choice: `local`, `github`, or `cancel`

**Resolution semantics:**

- `local`: local restored, GitHub updated to match
- `github`: GitHub restored, local updated to match
- `cancel`: no mutation to either layer

This is not a warning-only state; it is a blocking recovery decision.

### Provider Failure or Rate Limiting

**Condition:** provider timeout, malformed response, provider outage, `403`, or `429`.

**Behavior:**

- apply bounded retry policy
- fail over to alternate provider where defined
- surface contextual error if retries are exhausted
- do not retry indefinitely

### Security Refusal

**Condition:** policy or security layer emits `SECURITY_REFUSAL`.

**Behavior:**

- stop the attempted action immediately
- do not rephrase and resubmit
- emit error card
- gate
- log full prompt context with secret-safe handling
- require explicit operator override to proceed, if override is allowed by higher-level policy

### Path Validation Failure

**Condition:** target file path fails validation.

**Behavior:**

- abort write
- surface explicit error
- perform no partial write
- do not attempt alternative unvalidated paths

### GitHub Mutation Failure

**Condition:** API/tooling failure, SHA mismatch, auth error, permission failure, webhook inconsistency.

**Behavior:**

- surface contextual error
- preserve ledger consistency as much as possible
- avoid blind retries beyond policy
- never bypass `GitHubTool`

### XPC Protocol Error

**Condition:** malformed message, invalid nonce/auth context, unsupported message type, oversized payload.

**Behavior:**

- reject invalid messages
- discard and log unknown message types
- fail closed on auth/integrity failures
- do not convert protocol violations into undefined workflow state

### Restart Mid-Gate

**Condition:** backend process restarts while waiting for operator approval.

**Behavior:**

- gate state is lost
- no auto-reconstruction of approval
- operator must explicitly re-approve after restoration/resume

### Untrusted Input Poisoning

**Condition:** malicious or malformed content from docs, PR comments, CI, or external systems attempts prompt injection or workflow manipulation.

**Behavior:**

- treat as untrusted input
- validate and constrain before use
- keep such context out of system prompts
- never allow external content to bypass gate or security invariants

## Dependencies

### Internal Code Dependencies

- `src/consensus.py`
  - `ConsensusEngine`
  - generation-system prompt definitions
  - provider arbitration and retry/fallback logic
- `src/build_director.py`
  - `BuildPipeline`
  - stage dispatch/orchestration
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - `BuildLedger`

### Platform Dependencies

- XPC transport using line-delimited JSON with nonce authentication
- BuildStreamView consumer for `build_card` streaming
- gate UI consumer for `gate_card` blocking interactions
- document store/status reporting interfaces
- credentials delivery for:
  - Anthropic API key
  - OpenAI API key
  - GitHub token
  - engineer identity

### External Service Dependencies

- Anthropic provider
- OpenAI provider
- GitHub

These dependencies are all treated as failure-capable and untrusted at the transport/content level. The subsystem must preserve core invariants even when any external dependency is degraded, inconsistent, or unavailable.

### Required Cross-Cutting Utilities

- `path_security.validate_write_path()` for every file write
- logging/error-card pathways that preserve context without exposing secrets
- caching support for ETag-based polling optimization

### Prohibited Dependency Patterns

- direct GitHub API access outside `GitHubTool`
- execution runtimes for generated code
- any path write mechanism that bypasses `path_security.validate_write_path()`
- prompt-construction paths that place external document context into the system prompt