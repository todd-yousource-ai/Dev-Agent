# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding agent. It owns the end-to-end execution state of a build request after intent intake, including:

- decomposing a build intent into an ordered PR plan
- tracking build progress at PRD and PR granularity
- coordinating multi-provider code generation and arbitration
- driving review, CI, and operator approval gates
- persisting and restoring execution state across restarts
- detecting and resolving divergence between local and GitHub-backed recovery state

This subsystem is responsible for **stateful build continuation**. In particular:

- `/continue` resumes execution from the current thread state
- `/restore` reloads saved recovery state
- recovery state may exist in two layers:
  - local persisted state
  - GitHub-backed persisted state
- when restoring without an explicit target, the subsystem compares both layers and detects divergence

Expected `/continue` operator-visible output:

```text
▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]
```

The subsystem does **not** bypass approval gates, auto-merge without operator participation, or execute generated code. It is orchestration and state-management logic, not a sandbox runner or autonomous merge authority.

---

## Component Boundaries

### Owned by ConsensusDevAgent

The subsystem owns:

- build execution state for the current thread/session
- PRD-to-PR planning progress
- completed PR tracking
- recovery state serialization/deserialization
- divergence detection between local and GitHub recovery layers
- restore conflict prompting and operator selection handling
- build-stage dispatch orchestration through the pipeline
- emission of protocol messages representing progress and gates

Primary implementation surfaces from repository structure:

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/build_ledger.py`
  - `BuildLedger`
  - durable tracking of build state/progress
- `src/consensus.py`
  - `ConsensusEngine`
  - provider arbitration and generation coordination
- `src/github_tools.py`
  - `GitHubTool`
  - all GitHub interactions used by this subsystem

### Explicitly not owned by ConsensusDevAgent

This subsystem does **not** own:

- direct GitHub API usage outside `GitHubTool`
- arbitrary filesystem writes without path validation
- execution of generated source code, tests, or scripts via eval/exec/subprocess of model output
- authentication, credential issuance, or identity policy
- operator intent approval semantics beyond presenting gates and waiting
- document-store embedding implementation details
- transport-level XPC parsing rules beyond consuming valid protocol messages

### External interaction boundaries

#### UI / transport boundary
ConsensusDevAgent emits structured cards over Forge’s XPC protocol:

- `build_card`
  - streamed progress/status updates to `BuildStreamView`
- `gate_card`
  - blocking operator decision requests

It also consumes operator responses and thread commands such as `/continue` and `/restore`.

#### GitHub boundary
All GitHub operations must go through `GitHubTool`. Direct GitHub API calls are forbidden.

This includes:

- persisted recovery state synchronization
- PR metadata reads/writes
- polling and webhook-driven coordination as implemented by platform components

#### Filesystem boundary
All writes performed by this subsystem must be validated via:

- `path_security.validate_write_path()`

No write occurs before path validation succeeds.

---

## Data Flow

### 1. Build resume flow (`/continue`)

1. Operator issues `/continue`.
2. ConsensusDevAgent loads current thread-associated execution state.
3. The subsystem reconstructs the current build position:
   - active PRD
   - active PR number
   - active PR title/stage
4. It emits the resume banner:

   ```text
   ▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]
   ```

5. Control returns to the orchestration pipeline in `BuildPipeline`.
6. Progress updates are streamed via `build_card`.
7. If the next step requires human approval, a `gate_card` is emitted and execution blocks indefinitely until the operator responds.

### 2. Recovery restore flow (`/restore` without target)

1. The subsystem loads both recovery layers:
   - local saved state
   - GitHub saved state
2. It compares the two representations field-by-field.
3. If both agree:
   - restore proceeds silently
   - emit a single confirmation
4. If they diverge:
   - emit a conflict summary showing both states
   - list conflicting fields
   - prompt the operator:

   ```text
   Which to restore? (local / github / cancel)
   ```

5. Resolution handling:
   - `local`
     - restore local state
     - update GitHub layer to match local
   - `github`
     - restore GitHub state
     - update local layer to match GitHub
   - `cancel`
     - modify neither layer
     - return to prompt

Example divergence payload semantics:

- local summary: current subsystem name, PRD identifier, completed PR count
- saved timestamp and relative age
- GitHub summary: same shape
- conflict fields explicitly enumerated, e.g.:
  - `completed_prs`
  - `pr_plans_by_prd`

### 3. Non-interactive restore behavior

The TRD defines auto-resolution for non-interactive mode. In this subsystem, that means divergence logic must support a non-interactive decision path rather than assuming an interactive gate is always available.

However, Forge-wide invariants still apply:

- no silent failure paths
- errors must surface with context
- gate semantics may not be bypassed when operator approval is required

Where non-interactive restore is supported, the resolution policy must be explicit, logged, and deterministic. It must never silently discard one layer without an auditable decision rule.

### 4. Generation and review orchestration flow

1. Build intent and contextual documents are supplied to generation components.
2. `ConsensusEngine` coordinates two LLM providers in parallel.
3. Claude arbitrates provider output.
4. Generated implementation and tests move through a 3-pass review cycle.
5. CI is executed by the platform pipeline.
6. Merge or progression actions are blocked on operator gates.

ConsensusDevAgent tracks the state transitions across these phases but must not execute generated code directly.

### 5. State persistence flow

1. Build progress is recorded in durable state via `BuildLedger`.
2. Relevant progress may also be mirrored to GitHub-backed state.
3. On restart or restore:
   - local state is read
   - GitHub state is read
   - divergence detection is performed when required
4. Selected restored state becomes the authoritative in-memory execution state.

---

## Key Invariants

These are hard requirements for this subsystem.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and must be validated:
  - documents
  - PR comments
  - CI output
  - GitHub-originated state
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` is terminal within the flow:
  - do not retry
  - do not rephrase
  - emit error card
  - gate
  - log full prompt context safely without exposing secrets
  - require explicit operator override

### Human-in-the-loop gating

- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- No auto-approve ever.
- If backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo on gate decisions; this must remain explicit in operator-facing semantics.

### Recovery correctness

- Restore without target must compare both recovery layers.
- Divergence must be surfaced explicitly, including conflicting fields.
- `cancel` must leave both layers unchanged.
- Selecting one layer makes it authoritative and synchronizes the other layer to match.
- State reconciliation must be deterministic and auditable.

### API and filesystem discipline

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Blind GitHub writes are forbidden; writes must honor SHA/consistency protections.
- XPC unknown message types are discarded and logged, never raised as exceptions.

### Prompt/context handling

- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- Credentials must never appear in prompts.
- Credential material must never appear in logs.

### Retry and backoff constraints

- Never retry indefinitely; maximum 3 attempts total.
- In `_claude_json`: retry after 10s, then fall back to OpenAI.
- In `consensus.py`: retry with the other provider.
- GitHub/API throttling behavior:
  - `403` primary rate limit: exponential backoff starting at 60s
  - `429` secondary rate limit: respect `Retry-After` exactly
- ETag caching is required on polling endpoints.

---

## Failure Modes

### Recovery-state divergence

**Condition**
- local and GitHub recovery layers disagree on one or more tracked fields

**Detection**
- field-by-field comparison during `/restore` without explicit target

**Required behavior**
- display both state summaries
- enumerate conflicting fields
- request operator choice unless a defined non-interactive policy applies

**Forbidden behavior**
- silently choosing one layer
- partially merging fields without a defined reconciliation rule

### Missing or corrupt local state

**Condition**
- local state file unreadable, missing, malformed, or fails validation

**Required behavior**
- surface explicit error context
- if GitHub state is available, permit explicit restore from GitHub path
- do not fabricate progress state

### Missing or inconsistent GitHub-backed state

**Condition**
- GitHub persistence unavailable, malformed, stale, or rejected by API constraints

**Required behavior**
- surface error context
- fail closed on auth/identity failures
- do not silently ignore synchronization failure when authoritative state should be mirrored

### Mid-gate restart

**Condition**
- backend process restarts while waiting on operator gate

**Effect**
- gate state is lost

**Required behavior**
- operator must re-approve
- subsystem must not infer prior approval from partially persisted execution state

### Provider failure during generation

**Condition**
- one provider errors, times out, or returns unusable output

**Required behavior**
- bounded retry/fallback according to policy
- arbitration proceeds only with valid provider outputs under consensus rules
- surface terminal failure if retries are exhausted

### Security refusal from model layer

**Condition**
- model returns `SECURITY_REFUSAL`

**Required behavior**
- stop immediately
- do not retry or rephrase
- emit error card
- gate for operator action
- log context safely

### Rate limiting and transport degradation

**Condition**
- GitHub or provider APIs return `403`/`429`, or polling endpoints become stale

**Required behavior**
- apply specified backoff/retry discipline
- respect `Retry-After`
- use ETag caching
- surface delays or terminal exhaustion explicitly

### Unknown XPC messages

**Condition**
- transport receives unknown message type

**Required behavior**
- discard and log
- do not raise exception into build orchestration flow

### Path validation failure

**Condition**
- attempted filesystem write fails `validate_write_path()`

**Required behavior**
- abort write
- surface explicit error
- never continue with unvalidated path writes

---

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - `BuildPipeline` stage orchestration and dispatch
- `src/build_ledger.py`
  - `BuildLedger` for durable build-state tracking
- `src/consensus.py`
  - `ConsensusEngine`
  - generation coordination
  - provider fallback behavior
- `src/github_tools.py`
  - `GitHubTool`
  - required abstraction for all GitHub operations

### Platform protocol dependencies

ConsensusDevAgent depends on Forge XPC protocol contracts, including:

- line-delimited JSON wire format
- nonce authentication
- max 16MB message size
- `ready` message
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

This subsystem assumes protocol-valid inputs and must tolerate unknown message types by discarding and logging them.

### External service dependencies

- LLM providers used in parallel generation and arbitration flow
- GitHub for PR state and GitHub-backed recovery persistence
- CI systems as downstream execution signals consumed by orchestration

### Security/runtime dependencies

- `path_security.validate_write_path()` for every file write
- platform auth/identity mechanisms, which must fail closed
- logging/error infrastructure that preserves context without exposing secrets

### Documentary/context dependencies

ConsensusDevAgent may consume external repository and product documents for generation context, but all such content is treated as untrusted input and must be placed in the USER prompt only, never the SYSTEM prompt.