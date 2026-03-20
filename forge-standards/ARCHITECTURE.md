# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the orchestration subsystem for Forge’s native macOS AI coding workflow. It converts a plain-language build intent into an ordered, operator-gated implementation pipeline composed of pull requests, while preserving recoverable execution state across local and GitHub-backed storage.

At a high level, the subsystem is responsible for:

- Decomposing a product/build request into PRD-scoped work and ordered PR plans
- Driving implementation generation through parallel LLM providers, with consensus/arbitration
- Running review and CI stages for each PR
- Emitting streamed build status and gate requests over XPC to the UI
- Blocking on explicit operator approval at every gate
- Persisting and restoring build state, including recovery after restart
- Detecting divergence between local and GitHub-backed saved state during restore
- Resuming an in-progress build from current thread state via `/continue`

The `/continue` command resumes execution from the current in-memory/thread-associated state and reports the active work item in the form:

`▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

Recovery logic is part of the subsystem’s core behavior, not a convenience feature. The subsystem treats state continuity, divergence detection, and explicit operator-directed conflict resolution as first-class requirements.

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- Build orchestration and stage dispatch
- PRD and PR planning state
- Progress tracking, including completed PRs and per-PRD plans
- Recovery state management across local and GitHub persistence layers
- Divergence detection and conflict prompting during restore
- XPC emission of progress and gate messages
- Coordination of LLM generation, arbitration, review, and CI stages
- Enforcement of operator gating semantics
- Use of repository documents as generation context through approved document-store pathways

Primary implementation files identified in the platform context:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts/constants
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/build_ledger.py`
  - build state / ledger tracking
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

### Out of Scope

This subsystem does not own:

- Direct GitHub API access outside `GitHubTool`
- UI rendering semantics beyond emitting protocol-compliant XPC messages
- Credential acquisition or long-term secret storage policy
- Execution of generated code
- Arbitrary shell execution of generated content
- Mutation of paths not validated through path security controls
- Automatic approval, automatic merge override, or silent conflict resolution in interactive mode

### External Interfaces

ConsensusDevAgent interacts through the following boundaries:

- **XPC transport**
  - Line-delimited JSON
  - Nonce-authenticated
  - Maximum 16MB per message
- **UI/host process**
  - `ready`
  - `build_card`
  - `gate_card`
  - other protocol-defined status events
- **GitHub**
  - Exclusively through `GitHubTool`
- **LLM providers**
  - Multiple providers used in parallel or failover patterns
- **Document store**
  - Repository and product context retrieval for generation inputs
- **Path security**
  - All writes validated via `path_security.validate_write_path()`

## Data Flow

### 1. Build Initiation

1. Operator provides build intent.
2. ConsensusDevAgent constructs internal build state for the requested repository/work item.
3. The subsystem decomposes intent into PRD-scoped work and ordered PR plans.
4. Initial progress is streamed to the UI via `build_card`.

### 2. Generation and Review Pipeline

1. `BuildPipeline` dispatches stages in order.
2. `ConsensusEngine` requests candidate outputs from multiple LLM providers.
3. Arbitration/consensus selects or synthesizes implementation direction.
4. Generated artifacts are reviewed in a 3-pass review cycle.
5. CI is executed for the staged PR work.
6. At each operator decision point, a `gate_card` is emitted and the pipeline blocks indefinitely until input is received.

No gate auto-resolves. If the backend restarts while blocked on a gate, gate state is lost and operator re-approval is required.

### 3. State Persistence

Build execution state is persisted in two layers:

- **Local state**
- **GitHub-backed state**

These layers contain overlapping recovery data sufficient to restore build progress, including fields such as:

- active PRD
- completed PRs
- `pr_plans_by_prd`
- other ledger/progress metadata

### 4. Restore Without Target

When `/restore` is invoked without selecting a specific source, ConsensusDevAgent loads both persistence layers and compares them.

Outcomes:

- **No divergence**
  - Both layers agree
  - Restore proceeds silently
  - A single confirmation is printed
- **Divergence detected**
  - The subsystem computes differing fields
  - It presents local and GitHub summaries, timestamps, and conflicting fields
  - It prompts the operator to choose `local`, `github`, or `cancel`

Example decision surface from the TRD:

- Local: `ConsensusDevAgent — PRD-001, 3/11 PRs done`
- GitHub: `ConsensusDevAgent — PRD-001, 0/11 PRs done`
- Conflict fields: `completed_prs`, `pr_plans_by_prd`

### 5. Divergence Resolution

Conflict resolution is deterministic:

- If operator selects **`local`**
  - restore local state
  - update GitHub state to match local
- If operator selects **`github`**
  - restore GitHub state
  - update local state to match GitHub
- If operator selects **`cancel`**
  - modify neither layer
  - return to prompt

In non-interactive mode, the subsystem may apply auto-resolution logic as defined by runtime policy, but interactive operation requires explicit operator choice when divergence exists.

### 6. Continue Command

`/continue` resumes from the current thread-associated build state rather than recomputing planning from scratch. It emits a resume banner indicating the active PRD and PR:

`▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

This command assumes valid current state exists; it is a resume operation, not a restore/repair operation.

## Key Invariants

The subsystem must enforce the following architectural invariants.

### Security and Trust Boundaries

- Fail closed on authentication, cryptographic, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and must be validated, including:
  - documents
  - PR comments
  - CI output
  - XPC payloads
- Generated code is never executed by the agent.
- No `eval`, `exec`, or subprocess execution of generated content is permitted.
- `SECURITY_REFUSAL` is terminal unless explicitly operator-overridden through the required gating path; it is never bypassed by rephrasing.

### Human-in-the-Loop Guarantees

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.
- No undo exists for gate decisions.
- If the backend restarts mid-gate, prior gate approval state is not assumed; the operator must re-approve.

### Persistence and Recovery Guarantees

- Restore compares both persistence layers when no target is specified.
- Divergence must be surfaced explicitly; it cannot be silently overwritten in interactive mode.
- Conflict resolution updates the non-selected layer to match the selected source when a source is chosen.
- Cancel leaves both layers unchanged.
- `/continue` resumes only from current state; it does not silently repair missing or invalid state.

### Repository and Write Safety

- All file writes must be path-validated through `path_security.validate_write_path()` before execution.
- Direct GitHub writes outside `GitHubTool` are forbidden.
- Blind GitHub writes without SHA protection are forbidden.
- Path traversal is forbidden.

### Prompt/Context Separation

- External document context belongs in the USER prompt only.
- External context must never be inserted into the SYSTEM prompt.

### Protocol Discipline

- XPC unknown message types are discarded and logged, not raised as exceptions.
- All protocol messages must respect wire-format and size constraints.

### Retry and Backoff Discipline

- Retries are bounded: maximum 3 attempts total.
- In `_claude_json`, retry after 10 seconds, then fall back to OpenAI.
- In `consensus.py`, retry with the alternate provider as defined.
- Never retry indefinitely.
- `403` primary rate/abuse responses use exponential backoff starting at 60 seconds.
- `429` secondary limits must honor `Retry-After` exactly.
- Polling endpoints use ETag caching.

## Failure Modes

### State Divergence Between Local and GitHub

**Condition:** Restore without target loads two different valid states.

**Behavior:**
- Present both states, timestamps, and conflicting fields
- Require operator selection in interactive mode
- On selection, restore chosen state and synchronize the other layer
- On cancel, leave both unchanged

**Risk if violated:** Silent rollback, duplicated work, merge ordering corruption, or loss of completed PR accounting.

### Missing or Invalid Current State on `/continue`

**Condition:** Operator invokes `/continue` but current thread state is missing, corrupted, or incomplete.

**Behavior:**
- Do not invent or recompute state silently
- Surface an explicit error with context
- Require restore or operator intervention as appropriate

### Mid-Gate Restart

**Condition:** Backend process restarts while awaiting operator approval.

**Behavior:**
- Gate state is lost
- Prior approval is not assumed valid
- Operator must explicitly re-approve after recovery

**Risk if violated:** Unauthorized progression past approval boundaries.

### Auth/Crypto/Identity Failures

**Condition:** Credential validation, nonce/authentication checks, or identity binding fails.

**Behavior:**
- Fail closed
- Emit contextual error
- Do not continue in degraded mode

### Provider Failure or Rate Limiting

**Condition:** LLM provider request fails, times out, or is rate-limited.

**Behavior:**
- Retry according to bounded retry policy
- Fall back to alternate provider where defined
- Respect `Retry-After` and backoff requirements
- Surface failure if attempts are exhausted

### Invalid External Input

**Condition:** Untrusted input is malformed, hostile, or exceeds protocol constraints.

**Behavior:**
- Validate and reject invalid input
- Log safely without secret disclosure
- Do not promote untrusted content into privileged prompt or execution contexts

### Unsafe Write Attempt

**Condition:** A file write targets an invalid or unapproved path.

**Behavior:**
- Reject the write before execution
- Do not attempt partial write
- Surface error with context

### Direct or Unsafe GitHub Mutation

**Condition:** Code path attempts direct GitHub API use or write without required SHA semantics.

**Behavior:**
- Treat as architectural violation
- Route through `GitHubTool` only
- Do not proceed with blind update behavior

### SECURITY_REFUSAL Encountered

**Condition:** Safety subsystem returns `SECURITY_REFUSAL`.

**Behavior:**
- Stop
- Do not retry or rephrase
- Emit error card
- Gate
- Log full prompt context safely
- Require explicit operator override

## Dependencies

### Internal Code Dependencies

- `src/consensus.py`
  - consensus generation logic
  - provider failover/retry behavior
- `src/build_director.py`
  - build orchestration
  - stage sequencing
- `src/build_ledger.py`
  - persisted build/progress state
- `src/github_tools.py`
  - all GitHub operations
  - webhook-related integration

### Platform Dependencies

- XPC messaging layer implementing the Forge wire protocol
- Path security validation via `path_security.validate_write_path()`
- Document store for repository/product context retrieval
- Credential delivery mechanism providing:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`

### External Service Dependencies

- LLM providers used for generation and arbitration
- GitHub for PR/state persistence and repository operations
- CI systems whose output is consumed as untrusted input

### Protocol Dependencies

ConsensusDevAgent relies on these protocol contracts:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
- `gate_card`
  - `{ gate_type, options[], description }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

All protocol consumers and producers must preserve schema correctness, authentication requirements, and size limits.