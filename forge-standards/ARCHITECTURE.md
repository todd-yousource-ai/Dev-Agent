# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding workflow. It converts a plain-language build intent into an ordered execution plan of PRDs and pull requests, coordinates multi-provider code generation and arbitration, drives review and CI stages, persists build progress, and blocks on explicit operator approval at every gate before merge.

At a subsystem level, it is responsible for:

- Maintaining the canonical in-progress build state for a thread/build session.
- Resuming suspended work with `/continue` from the current thread state.
- Restoring persisted state across restart/recovery flows, including divergence detection between local and GitHub-backed state layers.
- Orchestrating generation, review, CI, and approval stages through the build pipeline.
- Emitting structured progress and gate messages to the UI over the Forge protocol.
- Enforcing Forge security and operational invariants during planning, generation, persistence, and external API interaction.

It is not a generic code execution system. Generated code is produced, reviewed, written to validated paths, and submitted through GitHub/CI workflows, but is never executed directly by the agent.

## Component Boundaries

### Inside this subsystem

#### `src/build_director.py`
Primary orchestration layer for the build lifecycle.

Responsibilities:
- Stage dispatch across planning, generation, review, CI, and approval/merge flow.
- Coordination of ordered PR execution within a PRD/build plan.
- Emission of `build_card` and `gate_card` protocol messages.
- Enforcement that gates block until explicit operator input.

#### `src/consensus.py`
Consensus and generation engine.

Responsibilities:
- Running parallel generation/review workflows across LLM providers.
- Provider arbitration logic.
- Retry/fallback behavior across supported model providers.
- Maintaining generation system prompts (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`) while ensuring external document context is supplied only in the user prompt.

#### `src/build_ledger.py`
Persistent state management for build progress.

Responsibilities:
- Recording canonical progress state such as current PRD, PR completion counts, and per-PR planning data.
- Supporting recovery/restore semantics.
- Participating in divergence comparison across local and GitHub-backed persistence layers.
- Providing the state basis used by `/continue`.

#### `src/github_tools.py`
All GitHub interactions for this subsystem.

Responsibilities:
- Pull request, branch, commit-status, and repository interactions through `GitHubTool`.
- Webhook reception where applicable.
- ETag-cached polling and rate-limit-aware retry behavior.
- Ensuring no direct GitHub API access bypasses the tool abstraction.

### Outside this subsystem

ConsensusDevAgent does **not** own:

- UI rendering behavior beyond emitting protocol-compliant `build_card` / `gate_card` messages.
- Credential acquisition UX beyond consuming `credentials` payloads.
- Raw XPC transport implementation beyond producing/consuming protocol-defined messages.
- Document embedding/indexing implementation, though it consumes document context/status.
- CI execution engine itself; it triggers and evaluates CI status but does not implement CI runners.
- Any direct execution of generated artifacts.

## Data Flow

### 1. Build initiation and planning
1. Operator provides build intent and required credentials/context.
2. ConsensusDevAgent decomposes the intent into ordered PRDs and PRs.
3. Planning state is persisted in the build ledger.
4. Progress is streamed via `build_card` messages.

### 2. Generation and consensus
1. For the active PR, the subsystem gathers repository/document context.
2. External document context is inserted into the **user** prompt only.
3. `consensus.py` dispatches generation/review requests to two LLM providers in parallel.
4. Claude arbitrates where required by the platform design.
5. Retry behavior is bounded:
   - `_claude_json`: retry after 10s, then fall back to OpenAI.
   - `consensus.py`: retry with the other provider.
   - Never retry indefinitely; maximum 3 attempts total.
6. Generated outputs are treated as untrusted until validated and written through approved paths.

### 3. File mutation
1. Candidate file changes are computed.
2. Every write path is validated via `path_security.validate_write_path()` before execution.
3. Writes proceed only after validation succeeds.
4. Generated code is stored in the repo/worktree; it is never executed by the agent.

### 4. Review, CI, and gates
1. The subsystem runs the required review cycle and CI checks.
2. Status/progress is emitted through `build_card`.
3. When human approval is required, a `gate_card` is emitted.
4. Gates block indefinitely until operator response.
5. There is no auto-approve path.
6. If the backend restarts mid-gate, gate state is lost and operator approval must be re-issued.
7. Gate decisions have no undo path.

### 5. Persistence, continue, and restore
#### `/continue`
`/continue` resumes build execution from the current thread state held by the build ledger and associated recovery state.

Required output format:
- `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

#### Restore with dual-layer state
On `/restore` without an explicit target, the subsystem loads:
- Local persisted state
- GitHub-backed persisted state

It compares the layers for divergence.

#### Divergence handling
If both layers agree:
- Restore silently
- Emit a single confirmation

If they diverge:
- Present both snapshots
- Identify conflicting fields, e.g.:
  - `completed_prs`
  - `pr_plans_by_prd`
- Prompt operator to choose:
  - `local`
  - `github`
  - `cancel`

Resolution semantics:
- `local`: restore local state and update GitHub to match
- `github`: restore GitHub state and update local to match
- `cancel`: modify neither layer and return to prompt

Non-interactive restore may apply auto-resolution rules if explicitly configured by the broader platform, but no silent divergence overwrite is permitted.

## Key Invariants

The subsystem must preserve all Forge-wide invariants plus its own recovery/orchestration constraints.

### Security and trust invariants
- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and must be validated:
  - documents
  - PR comments
  - CI output
  - webhook/event payloads
- Generated code is never executed by the agent:
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- All file writes must pass `path_security.validate_write_path()` before execution.
- Context from external documents must go in the **user** prompt, never the system prompt.
- `SECURITY_REFUSAL` is terminal within the current flow:
  - do not bypass by rephrasing
  - stop
  - gate
  - log full prompt context
  - require explicit operator override
- XPC unknown message types are discarded and logged; they are never raised as exceptions.

### GitHub and remote state invariants
- All GitHub operations go through `GitHubTool`; never call the GitHub API directly.
- No blind GitHub writes; writes requiring repository state must be SHA-aware.
- Polling endpoints use ETag caching.
- Rate limiting behavior is explicit:
  - `403` primary rate limit: exponential backoff starting at 60s
  - `429` secondary limit: respect `Retry-After` exactly

### Gate and operator-control invariants
- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- No auto-approve ever.
- If restart occurs during a gate, approval state is not assumed to persist; operator must re-approve.
- No undo on gate decisions.

### Recovery-state invariants
- `/continue` resumes from current thread/build state only.
- Restore without target must compare both persistence layers before choosing a state.
- Divergence must be surfaced explicitly with conflicting fields.
- Choosing one state layer makes that layer canonical and synchronizes the other to match.
- `cancel` must be non-destructive.

## Failure Modes

### Provider failure or malformed model output
Symptoms:
- Provider timeout
- Invalid structured output
- Provider-side refusal/failure

Handling:
- Apply bounded retry/fallback rules.
- Switch provider per documented fallback path.
- Stop after 3 total attempts.
- Surface an error card with context if unresolved.
- Gate for operator decision where required.

### Security refusal
Symptoms:
- Model emits `SECURITY_REFUSAL`
- Validation logic detects forbidden operation pattern

Handling:
- Do not retry by rephrasing.
- Do not continue generation.
- Emit error card.
- Gate.
- Log full prompt context without secrets.
- Require explicit operator override.

### Auth/identity/credential failure
Symptoms:
- Missing/invalid `github_token`
- Provider API auth failure
- Engineer identity mismatch or unavailable credentials

Handling:
- Fail closed.
- Do not continue with degraded functionality.
- Surface the error with context.
- Do not leak credential material.

### Path validation failure
Symptoms:
- Attempted write outside allowed repo/worktree
- Path traversal or unsafe path construction

Handling:
- Reject the write.
- Surface the validation failure.
- Do not attempt alternate unsafe writes.

### GitHub divergence during restore
Symptoms:
- Local and GitHub state snapshots differ on canonical fields

Handling:
- Present both snapshots and conflict fields.
- Require operator selection unless explicit non-interactive policy exists.
- On selection, synchronize the losing layer to the chosen canonical state.
- On `cancel`, make no changes.

### Mid-gate restart
Symptoms:
- Backend restarts while awaiting operator approval

Handling:
- Gate state is considered lost.
- Previously pending approval does not auto-resume.
- Operator must re-approve after restoration.

### XPC/message-level protocol issues
Symptoms:
- Unknown message type
- Oversize/invalid payload upstream of subsystem processing

Handling:
- Unknown types are discarded and logged.
- They are not raised as exceptions inside the subsystem.
- Subsystem proceeds only on protocol-valid inputs.

## Dependencies

### Internal Forge dependencies
- `src/consensus.py`
- `src/build_director.py`
- `src/build_ledger.py`
- `src/github_tools.py`
- Path security validation utilities, specifically `path_security.validate_write_path()`
- Document store/status inputs for context retrieval
- Forge XPC messaging layer and protocol schema

### External services
- Anthropic API
- OpenAI API
- GitHub API, exclusively through `GitHubTool`
- CI providers/status endpoints as integrated by the platform

### Protocol dependencies
ConsensusDevAgent consumes/emits Forge protocol objects including:

#### Input/handshake
- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

#### Streamed status
- `build_card`
  - `{ card_type, stage, content, progress }`

#### Operator gates
- `gate_card`
  - `{ gate_type, options[], description }`

#### Document-state signals
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### Operational constraints
- XPC wire format is line-delimited JSON.
- Messages are nonce-authenticated.
- Maximum message size is 16 MB.

### Explicit non-dependencies
ConsensusDevAgent does not depend on:
- Shelling out to execute generated code
- Direct GitHub API clients outside `GitHubTool`
- Any mechanism that auto-approves gates
- Any recovery path that silently overwrites divergent state