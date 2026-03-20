# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem that converts a plain-language build intent into a controlled, multi-PR software delivery workflow.

At a high level, it:

1. Decomposes requested work into an ordered PR plan, typically grouped by PRD.
2. Generates candidate implementations and tests using multiple LLM providers in parallel.
3. Uses consensus/arbitration logic to select or synthesize an implementation outcome.
4. Runs a structured review and CI flow for each PR.
5. Presents progress and approval gates to the operator.
6. Persists and restores build state across interruptions.
7. Synchronizes recovery state between local and GitHub-backed storage layers.

This subsystem is explicitly human-gated. It does not autonomously merge or bypass approval points. It is responsible for maintaining build continuity, surfacing state, and enforcing recovery semantics when interrupted or restarted.

The subsystem’s recovery-facing operator commands include:

- `/continue`  
  Resumes the build from the current thread state and emits:

  `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

- `/restore`  
  Restores persisted state. When no target is specified, it loads both local and GitHub-backed recovery layers and performs divergence detection before restoring.

The subsystem is part of a native macOS agent architecture, but its responsibility is workflow orchestration and state correctness, not UI rendering, OS-level IPC transport, or direct execution of generated artifacts.

---

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- Build orchestration across ordered PRs and PRDs
- Consensus generation flow across LLM providers
- Build progress tracking
- Recovery state persistence and restoration
- Divergence detection between local and GitHub-backed state layers
- Operator gating for recovery conflicts and build approvals
- Emission of build and gate cards to the UI stream
- Enforcement of repository and Forge safety invariants during its workflow

Primary implementation files in scope:

- `src/consensus.py`  
  Owns `ConsensusEngine` and generation system prompts/constants.
- `src/build_director.py`  
  Owns build pipeline orchestration and stage dispatch.
- `src/build_ledger.py`  
  Owns durable tracking of build progress/state.
- `src/github_tools.py`  
  Accessed by this subsystem for all GitHub operations.

### Out of Scope

ConsensusDevAgent does **not** own:

- Direct GitHub API access outside `GitHubTool`
- UI implementation details such as `BuildStreamView`
- XPC transport implementation beyond conforming to protocol contracts
- Execution of generated code
- Bypassing operator gates
- Secret storage policy beyond consuming credential inputs securely
- Document embedding/indexing internals, except as a consumer of document context
- Authentication/identity policy implementation beyond fail-closed behavior

### External Interfaces

This subsystem interacts with:

- Operator commands such as `/continue` and `/restore`
- XPC messages using line-delimited JSON
- GitHub via `GitHubTool` only
- LLM providers for generation/arbitration
- CI systems via routed build/review stages
- Document/context stores as untrusted input sources

Relevant protocol payloads include:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

ConsensusDevAgent must treat all external inputs as untrusted, including PR comments, CI output, and external documents.

---

## Data Flow

### 1. Build Initiation and Planning

1. Operator provides build intent.
2. ConsensusDevAgent loads repository/document context.
3. Work is decomposed into an ordered plan of PRs, typically grouped by PRD.
4. Plan and progress metadata are recorded in the build ledger.

Representative tracked fields include:

- current PRD
- ordered PR list
- completed PR count
- per-PR planning state such as `pr_plans_by_prd`

### 2. Generation and Consensus

1. `build_director.py` dispatches the current stage.
2. `consensus.py` invokes multiple LLM providers in parallel.
3. Claude arbitrates or participates in consensus selection per platform design.
4. Candidate code/tests are produced.
5. Review cycles and CI stages are executed.
6. Results are emitted as `build_card` updates.

Generated code is treated as data only. It is never executed by the agent.

### 3. Operator Gating

At required checkpoints, the subsystem emits a `gate_card` and blocks until the operator responds.

Rules:

- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- If the backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo for gate decisions.

### 4. Persistence and Recovery

The subsystem maintains recovery state in two layers:

- Local state
- GitHub-backed saved state

These layers enable restoration after interruption, restart, or host failure.

#### `/continue`

`/continue` resumes from current thread state without recomputing planning from scratch. It restores the current in-memory/thread-associated build position and emits:

`▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

#### `/restore`

When `/restore` is invoked without a target:

1. Load local recovery state.
2. Load GitHub-backed recovery state.
3. Compare the two state snapshots.
4. If equivalent on tracked recovery fields, restore silently and emit one confirmation.
5. If divergent, surface a conflict gate to the operator.

### 5. Divergence Detection and Resolution

When divergence is detected, the subsystem presents a recovery conflict summary:

- local state summary
- GitHub state summary
- timestamps
- conflicting fields

Example conflicting fields:

- `completed_prs`
- `pr_plans_by_prd`

The operator must choose:

- `local`
- `github`
- `cancel`

Resolution semantics are strict:

- If `local` is selected:
  - restore local state
  - update GitHub-backed state to match local

- If `github` is selected:
  - restore GitHub-backed state
  - update local state to match GitHub

- If `cancel` is selected:
  - modify neither layer
  - return to prompt

In non-interactive mode, auto-resolution behavior must still preserve deterministic, explicit conflict handling. It must not silently discard one side without a defined rule path.

---

## Key Invariants

The subsystem must preserve the following Forge-wide and subsystem-specific invariants.

### Safety and Security

- Fail closed on auth, crypto, and identity errors.
- Never degrade silently on security-sensitive failures.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and must be validated.
- Generated code is never executed by the agent.
- All file writes must be validated via `path_security.validate_write_path()` before execution.
- Context from external documents belongs in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal unless explicitly operator-overridden through the required gate/log path.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Control-Flow and Approval

- Gates never auto-approve or auto-resolve.
- Recovery conflicts require explicit resolution unless a documented non-interactive rule applies.
- If state is lost mid-gate, the operator must re-approve.
- Gate decisions have no undo.

### GitHub Access

- All GitHub operations go through `GitHubTool`.
- Never use the GitHub API directly.
- Never perform blind GitHub writes; writes must respect SHA/update preconditions.
- Polling endpoints use ETag caching.

### Retry and Backoff Behavior

- In `_claude_json`, retry after 10 seconds, then fall back to OpenAI.
- In `consensus.py`, retry with the other provider.
- Never retry indefinitely; maximum 3 attempts total.
- On GitHub `403` primary rate limiting, use exponential backoff starting at 60 seconds.
- On GitHub `429` secondary rate limiting, respect the `Retry-After` header exactly.
- `STOP. Do not retry. Do not rephrase.` applies to refusal/security-stop conditions.

### Recovery Correctness

- Restore must compare both layers when no explicit target is provided.
- Divergence detection must identify and report conflicting fields.
- Chosen recovery source becomes the canonical state and the other layer must be synchronized to match.
- `cancel` must leave both layers untouched.

---

## Failure Modes

### 1. Local/GitHub Recovery Divergence

**Cause:** Local and GitHub-backed snapshots disagree on tracked progress fields.  
**Detection:** Field-by-field comparison during `/restore` with no target.  
**Behavior:** Emit conflict summary and block on operator decision.  
**Recovery:** Synchronize the non-selected layer to the selected layer after explicit choice.  
**Prohibited behavior:** Silent preference for one layer.

### 2. Lost In-Memory or Mid-Gate State

**Cause:** Backend restart or crash during an approval gate.  
**Behavior:** Gate state is not recoverable as approved.  
**Recovery:** Operator must re-approve.  
**Prohibited behavior:** Assuming prior approval still holds.

### 3. Provider Failure During Generation

**Cause:** Timeout, malformed response, provider outage, or refusal.  
**Behavior:** Retry/fallback according to bounded provider rules.  
**Recovery path:**
- retry after 10 seconds where specified
- fall back to alternate provider
- cap total attempts at 3  
**Escalation:** Emit error card, gate, and log full prompt context where required by policy.  
**Prohibited behavior:** Infinite retries or silent provider substitution without surfaced context.

### 4. GitHub API Failure or Rate Limiting

**Cause:** auth failure, permission issue, `403`, `429`, stale SHA, network error.  
**Behavior:** Fail closed with contextual error.  
**Recovery:**
- `403`: exponential backoff starting at 60s
- `429`: honor `Retry-After`
- stale state: re-read through `GitHubTool` and retry within bounded limits  
**Prohibited behavior:** Direct API calls, blind writes, or dropping synchronization errors.

### 5. Path Validation Failure

**Cause:** attempted write outside allowed repository boundaries or path traversal input.  
**Behavior:** Reject write before execution.  
**Recovery:** Surface error with context.  
**Prohibited behavior:** Writing first and validating later.

### 6. Security Refusal or Unsafe Prompt/Content Path

**Cause:** prompt or output triggers `SECURITY_REFUSAL`, credential leakage risk, unsafe external context handling.  
**Behavior:** Stop, do not retry, do not rephrase. Emit error card, gate, and log required context.  
**Recovery:** Operator must explicitly override where policy permits.  
**Prohibited behavior:** Bypassing refusal through prompt reformulation.

### 7. Malformed or Unknown XPC Input

**Cause:** unexpected message shape, unknown type, oversized payload, invalid nonce/auth semantics.  
**Behavior:** Discard unknown message types and log; fail closed on auth/integrity errors.  
**Prohibited behavior:** Treating unknown wire messages as valid workflow state.

---

## Dependencies

### Internal Code Dependencies

- `src/consensus.py`
  - `ConsensusEngine`
  - generation prompt constants/systems
  - provider retry/fallback orchestration

- `src/build_director.py`
  - build pipeline orchestration
  - stage dispatch
  - coordination of generation, review, CI, and gating

- `src/build_ledger.py`
  - durable build progress/state tracking
  - recovery metadata used by `/continue` and `/restore`

- `src/github_tools.py`
  - `GitHubTool`
  - all repository, PR, and persisted GitHub-state interactions
  - webhook-related integration as applicable

### Platform Dependencies

- XPC transport using line-delimited JSON
- Nonce-authenticated messaging
- 16 MB maximum message size
- `BuildStreamView` consumer for streamed `build_card` output
- Gate UI consumer for `gate_card` blocking interactions
- Credential delivery via `credentials` payload
- Document store/status services for contextual inputs

### External Service Dependencies

- Anthropic provider
- OpenAI provider
- GitHub
- CI systems

### Dependency Constraints

- LLM providers are interchangeable only within bounded retry/fallback policy.
- GitHub is accessed exclusively through `GitHubTool`.
- Document/context inputs are always untrusted and must not be promoted into SYSTEM prompt context.
- No dependency may introduce execution of generated code or auto-approval semantics.