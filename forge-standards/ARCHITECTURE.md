# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem that turns a plain-language build intent into a controlled, reviewable sequence of pull requests, while preserving operator control and resumable execution state.

At a high level, the subsystem:

- decomposes a requested build into an ordered PR plan, typically grouped by PRD
- generates implementation and tests for each PR using multiple LLM providers in parallel
- arbitrates generation outcomes through the consensus engine
- runs a 3-pass review cycle
- executes CI and surfaces results
- blocks on explicit operator gates before advancing or merging
- persists and restores build progress across backend restarts or operator sessions

This subsystem also owns recovery semantics for in-progress builds, including:

- `/continue`: resume the current build from thread state and emit:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`
- `/restore`: restore saved state from persistence layers
- divergence detection between local and GitHub-backed saved state when restoring without an explicit target
- conflict resolution between those layers, including interactive operator choice and synchronization of the non-selected layer to the selected source of truth

The subsystem is part of a native macOS AI coding platform, but its responsibility is orchestration, state progression, consensus-driven generation, and gate-controlled advancement. It does not autonomously bypass human approval.

## Component Boundaries

### Inside this subsystem

The following responsibilities belong to ConsensusDevAgent:

- build orchestration and stage dispatch
- PRD/PR planning and progress tracking
- LLM generation coordination and provider fallback
- consensus arbitration between providers
- review cycle coordination
- CI result routing into the build flow
- operator gate emission and waiting semantics
- recovery state persistence, restoration, and divergence handling
- rendering structured progress/gate updates to the UI protocol
- enforcing build-loop invariants around retries, approvals, and error surfacing

Primary implementation surfaces identified in repository context:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts/constants
  - provider retry/fallback behavior
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/build_ledger.py`
  - `BuildLedger`
  - build progress/state tracking
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

### Outside this subsystem

The following are external dependencies or adjacent subsystems and are not owned by ConsensusDevAgent logic itself:

- LLM providers
  - Anthropic
  - OpenAI
- GitHub as remote state and PR/CI system of record
- XPC transport and host integration
- document store and embedding pipeline
- UI rendering layer such as `BuildStreamView`
- authentication/credential acquisition
- path validation implementation in `path_security.validate_write_path()`

### Explicit non-responsibilities

ConsensusDevAgent must not:

- execute generated code
- eval or exec generated content
- spawn subprocesses from generated content
- write files without prior path validation
- call the GitHub API directly outside `GitHubTool`
- auto-approve gates
- silently ignore errors, refusals, or state conflicts
- place external document context into the SYSTEM prompt
- expose secrets in logs, prompts, generated code, or error messages

## Data Flow

### 1. Build initiation and planning

1. Operator supplies build intent.
2. ConsensusDevAgent creates or loads build state.
3. The build is decomposed into an ordered set of PRs, associated to PRDs.
4. Progress is recorded in ledger/state structures such as:
   - current PRD
   - current PR index
   - completed PRs
   - per-PRD plan data such as `pr_plans_by_prd`

### 2. Context assembly

1. Relevant repository and document context is gathered.
2. External documents are treated as untrusted input and validated.
3. External context is inserted into the USER prompt only.
4. SYSTEM prompts remain reserved for internal generation policy.

### 3. Parallel generation and arbitration

1. The subsystem requests candidate implementations from two LLM providers in parallel.
2. `ConsensusEngine` arbitrates or selects output according to subsystem policy.
3. Retry behavior follows bounded fallback rules:
   - `_claude_json`: retry after 10s, then fall back to OpenAI
   - `consensus.py`: retry with the other provider
   - never retry indefinitely
   - maximum 3 attempts total

### 4. Review and CI loop

1. Generated changes enter a 3-pass review cycle.
2. CI is executed and routed back into the build pipeline.
3. Results are emitted as structured stream updates, including:
   - `build_card: { card_type, stage, content, progress }`
4. If a decision is required, a blocking gate is emitted:
   - `gate_card: { gate_type, options[], description }`

### 5. Operator gating

1. The subsystem stops at defined approval points.
2. Gates block indefinitely until operator input is received.
3. No gate auto-resolves.
4. If the backend restarts mid-gate:
   - gate state is lost
   - operator must re-approve
5. There is no undo on gate decisions.

### 6. Persistence, continue, and restore

#### `/continue`

- Resumes from current thread state.
- Emits:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

#### `/restore`

When restore is invoked without a target, the subsystem loads both persistence layers:

- local state
- GitHub-backed state

It compares them for divergence.

##### No divergence

- If both layers agree, state is restored silently.
- A single confirmation is printed.

##### Divergence detected

The subsystem reports both states and conflicting fields, for example:

- local summary
- local save timestamp and relative age
- GitHub summary
- GitHub save timestamp and relative age
- conflicting fields such as:
  - `completed_prs`
  - `pr_plans_by_prd`

It then blocks for operator choice:

- `local`
- `github`
- `cancel`

##### Conflict resolution rules

- If `local` is selected:
  - restore local
  - update GitHub state to match local
- If `github` is selected:
  - restore GitHub
  - update local state to match GitHub
- If `cancel` is selected:
  - modify neither layer
  - return to prompt

Auto-resolution behavior may exist for non-interactive mode, but it must still preserve subsystem invariants around explicit error surfacing and deterministic state choice.

### 7. File and remote writes

1. Any file write is path-validated via `path_security.validate_write_path()` before execution.
2. Any GitHub operation is performed only through `GitHubTool`.
3. Polling endpoints should use ETag caching.
4. Writes to GitHub must not be blind writes; SHA-aware semantics are required.

## Key Invariants

The subsystem must enforce the following invariants.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors.
- Never degrade silently on security-sensitive failures.
- Secrets never appear in:
  - logs
  - error messages
  - prompts where forbidden
  - generated code
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent.
- SECURITY_REFUSAL handling is terminal unless explicitly overridden by the operator.
- Rephrasing must not bypass SECURITY_REFUSAL.
- External document context goes in the USER prompt, never the SYSTEM prompt.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Human-in-the-loop control

- Gates never auto-approve.
- Gates wait indefinitely for operator input.
- No silent progression past an approval boundary.
- Mid-gate restart loses gate state; re-approval is required.
- No undo on gate decisions.

### State management and recovery

- Restore without target must compare local and GitHub layers.
- Divergence must be surfaced explicitly.
- Conflicting fields must be identified.
- Operator-selected restore source becomes canonical and is propagated to the other layer.
- Cancel leaves both layers untouched.
- `/continue` resumes from current thread state, not from inferred or fabricated state.

### Reliability and retry discipline

- No silent failure paths.
- Every error must surface with context.
- Retries are bounded:
  - max 3 attempts total
- Provider failover is explicit and limited.
- 403 primary rate limits use exponential backoff starting at 60s.
- 429 secondary rate limits respect `Retry-After` exactly.
- No indefinite retry loops.

### Write and API discipline

- All file writes require path validation before execution.
- All GitHub operations go through `GitHubTool`.
- No direct GitHub API usage from other code paths.
- No blind GitHub writes without SHA protection.

### Allocation discipline

- Keep allocations minimal.
- Document every allocation explicitly.

This requirement is currently called out as unresolved architectural guidance and must be preserved as a design constraint for modifications in this subsystem.

## Failure Modes

### Provider generation failure

Symptoms:

- provider timeout
- malformed response
- provider refusal
- unavailable provider

Handling:

- apply bounded retry/fallback policy
- switch provider where specified
- stop after maximum attempts
- emit an error card
- gate for operator input if the build cannot safely continue

### SECURITY_REFUSAL or policy refusal

Symptoms:

- model returns refusal on unsafe or prohibited action

Handling:

- stop immediately
- do not retry
- do not rephrase
- emit error card
- gate
- log full prompt context in accordance with secret-handling rules
- require explicit operator override before proceeding

### Auth, crypto, or identity failure

Symptoms:

- invalid credentials
- nonce/authentication mismatch
- identity verification error

Handling:

- fail closed
- surface error with context
- do not silently degrade to reduced-trust behavior

### Restore-state divergence

Symptoms:

- local and GitHub persistence layers disagree on tracked fields

Handling:

- print divergence summary
- identify conflict fields
- require operator selection in interactive mode
- if `cancel`, mutate nothing
- after `local` or `github`, synchronize the non-selected layer to the selected one

### Mid-gate restart

Symptoms:

- backend exits or restarts while awaiting operator decision

Handling:

- gate state is lost
- prior non-persisted approval is not inferred
- operator must re-approve

### Invalid external input

Symptoms:

- malformed document payload
- untrusted CI output content
- unknown XPC message type
- invalid PR comment content

Handling:

- validate input before use
- discard and log unknown XPC message types
- do not elevate malformed external data into trusted control flow

### Path validation failure

Symptoms:

- attempted write outside allowed repository or workspace boundaries
- path traversal patterns

Handling:

- reject the write
- surface error
- do not perform partial write

### GitHub write conflict or unsafe mutation

Symptoms:

- missing SHA precondition
- stale ETag/state
- conflicting remote updates

Handling:

- do not perform blind write
- route through `GitHubTool`
- use polling/cache discipline and conflict-aware update logic

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - consensus arbitration
  - provider retry/fallback logic
- `src/build_director.py`
  - build pipeline orchestration
  - stage dispatch
- `src/build_ledger.py`
  - persisted build/progress state
- `src/github_tools.py`
  - all GitHub operations
  - webhook integration

### Platform/protocol dependencies

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - maximum 16 MB per message
- ready message contract:
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- build stream contract:
  - `build_card: { card_type, stage, content, progress }`
- gate contract:
  - `gate_card: { gate_type, options[], description }`
- credential payload:
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- document status payload:
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### External service dependencies

- Anthropic provider
- OpenAI provider
- GitHub
- CI systems surfaced through GitHub/tooling integration
- document store / embedding subsystem

### Required integration rules

- all GitHub ops go through `GitHubTool`
- all writes are path-validated first
- ETag caching is used on polling endpoints
- rate-limit handling follows documented backoff rules
- context loading from external documents uses USER prompt placement only