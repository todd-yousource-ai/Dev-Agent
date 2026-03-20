# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding workflow. It owns the end-to-end execution state of a build request after intent has been accepted, including:

- decomposition of build intent into an ordered PR plan,
- parallel code generation via supported LLM providers,
- provider arbitration and retry/fallback behavior,
- review/CI progression across PRs,
- operator gating before irreversible actions,
- recovery and restoration of build state across restarts,
- synchronization of persisted state between local and GitHub-backed layers.

In Forge platform terms, this subsystem is the stateful execution engine behind the “Consensus Dev Agent” flow. It does not merely generate code; it advances a build through staged PR delivery while preserving operator control and auditability.

Recovery-specific responsibilities include:

- `/continue`: resume a build from current thread state and emit:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`
- `/restore` state reconciliation across persistence layers
- divergence detection between local and GitHub state when restore is invoked without an explicit target
- operator-mediated conflict resolution when persisted state differs

The subsystem must treat state recovery as part of normal operation, not as a best-effort enhancement.

## Component Boundaries

This subsystem is centered on the Python backend components below:

- `src/build_director.py`
  - owns build pipeline orchestration
  - dispatches stages
  - advances PR lifecycle
  - coordinates gates, CI progression, and resume behavior
- `src/consensus.py`
  - owns multi-provider generation orchestration
  - defines generation system prompts/constants
  - arbitrates between model outputs
  - implements provider fallback behavior
- `src/build_ledger.py`
  - owns durable build state representation
  - tracks PRD/PR progress, completed PRs, and planning metadata
  - is the authoritative local persistence layer used for restore/continue
- `src/github_tools.py`
  - the only permitted boundary for GitHub operations
  - used for reading/writing GitHub-backed state and PR metadata
  - must encapsulate API semantics such as SHA-safe writes, polling, and webhook handling

This subsystem does **not** own:

- direct UI rendering, though it emits protocol messages consumed by UI components such as `BuildStreamView`
- raw XPC transport implementation, though it must conform to protocol message contracts
- execution of generated code
- arbitrary GitHub API access outside `GitHubTool`
- authentication/credential issuance
- document embedding/indexing internals, beyond consuming document context

Operational boundary rules:

- all GitHub interactions must go through `GitHubTool`; direct GitHub API usage is forbidden
- all file writes must be path-validated via `path_security.validate_write_path()` before execution
- external documents and other untrusted context may inform generation, but must be injected only via the USER prompt, never the SYSTEM prompt
- generated code is output only; it is never executed by this subsystem

## Data Flow

### 1. Build initiation and staged execution

1. Operator provides plain-language build intent.
2. ConsensusDevAgent decomposes the request into an ordered PR sequence.
3. For each PR:
   - generation context is assembled from trusted internal state plus validated external documents
   - multiple LLM providers generate implementation/test proposals in parallel
   - `consensus.py` arbitrates or falls back per retry policy
   - review and CI stages run
   - operator gate blocks further progression until explicit approval
4. Merge/progression continues PR-by-PR under human control.

### 2. State persistence

The subsystem maintains build progress in at least two persistence layers:

- **local state**
  - persisted by `BuildLedger`
  - used for restart continuity and `/continue`
- **GitHub-backed state**
  - persisted via `GitHubTool`
  - used as a remote/shared recovery source

Relevant state includes, at minimum:

- current PRD identifier
- current PR number/title in execution
- completed PR count/list
- PR plans by PRD
- last-saved timestamps for each layer

### 3. Continue flow

`/continue` resumes execution from current thread state.

Expected behavior:

- load current execution state
- rehydrate the active PR/PRD context
- emit:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

This command resumes from the existing in-thread state; it is not a reconciliation command.

### 4. Restore and divergence detection

When `/restore` is run **without a target**, the subsystem must:

1. load both local and GitHub state layers
2. compare them field-by-field
3. determine whether they agree

#### No divergence

If both layers agree:

- restore silently
- print a single confirmation
- do not prompt for conflict resolution

#### Divergence detected

If layers differ, the subsystem must surface a conflict summary, including:

- local state summary
- local saved timestamp
- GitHub state summary
- GitHub saved timestamp
- explicit conflicting fields

Example shape:

- `completed_prs`
- `pr_plans_by_prd`

It must then gate on operator choice:

- `local`
- `github`
- `cancel`

Resolution semantics:

- if `local` is selected:
  - restore local state
  - update GitHub to match local
- if `github` is selected:
  - restore GitHub state
  - update local to match GitHub
- if `cancel` is selected:
  - modify neither layer
  - return to prompt

In non-interactive mode, divergence handling may auto-resolve only according to explicit non-interactive policy. It must not silently choose a side without a defined rule.

### 5. UI/protocol emission

The subsystem emits structured protocol messages for presentation and gating, including:

- `build_card`
  - streamed progress/status for active stages
- `gate_card`
  - blocking operator decision points
- readiness/status metadata where required by surrounding platform flow

All emitted messages must respect the XPC protocol shape and constraints:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

Unknown XPC message types are discarded and logged by the platform; this subsystem must not depend on them being raised as exceptions.

## Key Invariants

The following invariants are mandatory for this subsystem.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts where prohibited, or generated code.
- All external input is untrusted and must be validated before use, including:
  - documents
  - PR comments
  - CI output
- Context from external documents must go in the USER prompt, never the SYSTEM prompt.
- Generated code must never be executed by the agent.
- `SECURITY_REFUSAL` is terminal for the current action path:
  - do not bypass by rephrasing
  - stop
  - gate
  - log
  - require explicit operator override
- All write paths must be validated through `path_security.validate_write_path()` before file mutation.

### Human-in-the-loop gating

- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- No auto-approve behavior is permitted.
- If the backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo on gate decisions; this must be treated as irreversible workflow state.

### GitHub interaction

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Blind GitHub writes are forbidden; writes must be SHA-safe where applicable.
- Polling endpoints must use ETag caching.
- Rate-limit handling must be explicit:
  - `403` primary rate limit: exponential backoff starting at 60s
  - `429` secondary rate limit: respect `Retry-After` exactly

### Retry behavior

Retry loops are bounded:

- `_claude_json`: retry after 10s, then fall back to OpenAI
- `consensus.py`: retry with the other provider
- never retry indefinitely
- maximum 3 attempts total

### Recovery consistency

- `/continue` resumes from current thread state and must not mutate unrelated persisted state as a side effect.
- `/restore` without target must compare both persistence layers before restoring.
- Divergence must be surfaced explicitly with conflicting fields.
- Conflict resolution must be operator-directed unless an explicit non-interactive policy applies.
- After conflict selection, the non-selected layer must be updated to match the chosen source, except on `cancel`.
- `cancel` must leave both layers untouched.

## Failure Modes

### Persistence divergence

**Mode:** Local and GitHub layers contain different build progress.

**Detection:**
- field-level comparison during `/restore` without target

**Handling:**
- present both snapshots and conflict fields
- gate on `local | github | cancel`
- synchronize the losing layer to the chosen source
- no mutation on cancel

**Risk if violated:**
- resuming wrong PR
- duplicate or skipped PR execution
- corrupted PRD progress accounting

### Lost gate state after restart

**Mode:** Backend restarts while awaiting operator input.

**Handling:**
- prior gate decision is not inferred
- operator must re-approve
- subsystem must not auto-progress on restart

**Risk if violated:**
- unauthorized merge/progression
- broken human-approval guarantees

### Provider failure or degraded generation path

**Mode:** LLM provider request fails, times out, or returns invalid output.

**Handling:**
- retry/fallback per bounded provider policy
- surface error context if attempts exhaust
- do not loop indefinitely

**Risk if violated:**
- hung pipeline
- hidden quality degradation
- unbounded spend or latency

### Auth/identity/crypto errors

**Mode:** Credential or identity validation fails.

**Handling:**
- fail closed
- emit contextual error
- do not continue in degraded mode

**Risk if violated:**
- unauthorized actions
- state corruption under wrong identity
- leakage across operator/build contexts

### GitHub API/rate-limit failures

**Mode:** GitHub rejects reads/writes or rate-limits requests.

**Handling:**
- route through `GitHubTool`
- apply ETag caching
- obey `403`/`429` handling rules
- surface errors when recovery fails

**Risk if violated:**
- remote state drift
- blind overwrite
- non-deterministic restore behavior

### Invalid or malicious external context

**Mode:** Documents, PR comments, or CI output contain malformed or adversarial content.

**Handling:**
- treat all such input as untrusted
- validate before use
- never elevate into SYSTEM prompt
- stop on `SECURITY_REFUSAL`

**Risk if violated:**
- prompt injection
- policy bypass
- unsafe code or workflow actions

### Unsafe write target

**Mode:** File mutation targets an invalid or traversing path.

**Handling:**
- validate with `path_security.validate_write_path()` before write
- fail the operation with surfaced error context

**Risk if violated:**
- path traversal
- repository escape
- unauthorized file modification

### Protocol contract violation

**Mode:** Emitted messages exceed protocol constraints or use invalid shape.

**Handling:**
- conform to line-delimited JSON contracts
- respect max message size
- avoid reliance on unsupported message semantics

**Risk if violated:**
- dropped UI updates
- broken gating UX
- inconsistent frontend/backend state perception

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - orchestration entrypoint for staged build execution
- `src/consensus.py`
  - provider orchestration, arbitration, and fallback logic
- `src/build_ledger.py`
  - local durable build state
- `src/github_tools.py`
  - sole GitHub integration surface
- `path_security.validate_write_path()`
  - mandatory precondition for any file write

### Platform/protocol dependencies

- Forge XPC protocol
  - line-delimited JSON
  - nonce-authenticated messaging
  - 16 MB max message size
- build/gate card contracts
  - `build_card`
  - `gate_card`
- readiness/status message formats where needed by agent lifecycle

### External service dependencies

- LLM providers used in consensus generation
  - Anthropic
  - OpenAI
- GitHub
  - PR metadata
  - remote state persistence
  - polling/webhook surfaces
- document store inputs
  - used as generation context only after validation

### Operational assumptions

- operator remains available for all required gates
- persisted local state is available for `/continue`
- GitHub-backed state is available for reconciliation when `/restore` needs both layers
- backend restart may occur at any time; recovery behavior must preserve invariants rather than infer missing approval state