# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the orchestration subsystem for Forge’s native macOS AI coding workflow. It accepts a plain-language build intent and drives an operator-gated implementation pipeline that:

1. decomposes intent into an ordered sequence of PRs,
2. generates code and tests using multiple LLM providers in parallel,
3. arbitrates generation outcomes through the consensus engine,
4. runs review and CI stages,
5. persists and restores execution state across interruptions, and
6. blocks on explicit operator approval at every merge or recovery gate.

Within this subsystem, recovery-state management is a first-class responsibility. In particular:

- `/continue` resumes a build from the current thread state and emits:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`
- `/restore` without an explicit target loads both persisted state layers and performs divergence detection between:
  - local recovery state, and
  - GitHub-backed recovery state.

If the two layers disagree, the subsystem must surface the divergence, identify conflicting fields, and require operator selection of the authoritative source unless running in a defined non-interactive auto-resolution mode.

This subsystem does not merely store progress; it enforces consistency of build progression, PR planning state, and operator-visible recovery semantics.

## Component Boundaries

ConsensusDevAgent spans orchestration, consensus, GitHub-mediated persistence, and recovery state comparison, but it does not own arbitrary execution or direct infrastructure control.

### In scope

- Build pipeline orchestration and stage dispatch
- PR decomposition and ordered execution
- LLM generation coordination and arbitration
- Recovery state load, compare, restore, and resume behavior
- Divergence detection between local and GitHub state layers
- Operator gating for restore conflicts and pipeline approvals
- GitHub operations through the approved abstraction only
- Build progress accounting, including fields such as:
  - current PRD
  - completed PRs
  - PR plans by PRD
  - current PR index/title
- Emission of protocol-compliant UI/status messages such as build cards and gate cards

### Out of scope

- Direct execution of generated code
- Direct GitHub API calls outside `GitHubTool`
- Silent conflict resolution in interactive mode
- Automatic approval of gates
- Persistence mechanisms outside the defined local and GitHub-backed layers
- Bypassing path validation for file writes
- Trusting external content without validation

### Primary implementation files

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts and provider arbitration logic
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - `BuildLedger`

## Data Flow

### 1. Build initiation and orchestration

1. Operator provides build intent.
2. ConsensusDevAgent creates or resumes a build thread.
3. `BuildPipeline` decomposes work into an ordered PR sequence.
4. Generation requests are sent to supported LLM providers.
5. `ConsensusEngine` arbitrates outputs and advances the selected result through review and CI.
6. Progress is recorded into recovery state layers.

### 2. State persistence model

Recovery state is maintained in two layers:

- **Local state**
  - low-latency, process-local recovery representation
- **GitHub state**
  - remote, durable recovery representation associated with the repository/build context

These layers are intended to converge on the same logical build state. They are compared during restore when no explicit target is specified.

### 3. `/continue`

`/continue` resumes from the current thread state rather than reconstructing state from scratch.

Expected operator-visible output:

- `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

Operationally, `/continue` assumes an already selected authoritative current thread state and re-enters pipeline execution from the last recorded point.

### 4. `/restore` without target

When `/restore` is invoked without a source selector:

1. Load local state.
2. Load GitHub state.
3. Compare both logical state objects field-by-field.
4. If equivalent:
   - restore silently,
   - print a single confirmation.
5. If divergent:
   - emit a conflict summary,
   - include timestamps and relative ages,
   - enumerate conflict fields,
   - gate on operator choice:
     - `local`
     - `github`
     - `cancel`

Expected conflict interaction shape:

- show local snapshot summary
- show GitHub snapshot summary
- show conflicting fields such as:
  - `completed_prs`
  - `pr_plans_by_prd`

### 5. Divergence resolution

If operator selects:

- **`local`**
  - restore local state as authoritative
  - update GitHub layer to match local
- **`github`**
  - restore GitHub state as authoritative
  - update local layer to match GitHub
- **`cancel`**
  - modify neither layer
  - return to prompt

This is a synchronization action after source-of-truth selection, not a merge of individual fields. The subsystem chooses one full authoritative state and propagates it to the other layer.

### 6. UI/protocol emission

The subsystem communicates status and operator decisions through Forge protocol objects:

- `build_card`
  - streamed progress/status to `BuildStreamView`
- `gate_card`
  - blocking operator decision requests

Recovery divergence handling must surface as a gate, not as an informational warning that the system proceeds past automatically.

## Key Invariants

The following invariants are enforced by ConsensusDevAgent and inherited from Forge platform rules.

### Recovery and gating invariants

- `/continue` resumes from current thread state only.
- `/restore` without target compares both recovery layers before selecting a state.
- Divergence in interactive mode is never resolved silently.
- Restore conflict resolution is authoritative-source selection, not field-level blending.
- Gates never auto-resolve.
- If backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo for gate decisions.

### Security and trust invariants

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` is terminal unless explicitly operator-overridden through the documented gate path.
- Context from external documents goes into the USER prompt, never the SYSTEM prompt.

### File and write invariants

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Blind GitHub writes without SHA protection are forbidden.

### GitHub invariants

- All GitHub operations go through `GitHubTool`.
- The GitHub API is never called directly by this subsystem.
- Polling endpoints use ETag caching.
- Rate-limit behavior is explicit:
  - `403` primary rate limiting: exponential backoff starting at 60s
  - `429` secondary rate limiting: respect `Retry-After` exactly

### Reliability invariants

- No indefinite retry loops.
- Maximum total retry count is 3 attempts.
- In provider-specific paths:
  - `_claude_json`: retry after 10s, then fall back to OpenAI
  - `consensus.py`: retry with the other provider
- XPC unknown message types are discarded and logged, never raised as exceptions.

## Failure Modes

### 1. Recovery state divergence

**Condition**
- Local and GitHub recovery layers disagree on material build fields.

**Handling**
- Surface both snapshots and conflict fields.
- Gate on `local | github | cancel`.
- In interactive mode, do not auto-resolve.
- On authoritative selection, overwrite the non-authoritative layer.

**Risk controlled**
- Resuming from stale or contradictory build state.

### 2. Missing or unreadable state layer

**Condition**
- One recovery layer cannot be loaded due to auth, transport, serialization, or local I/O failure.

**Handling**
- Fail closed with contextual error.
- Do not silently fall back if correctness or identity is uncertain.
- Require explicit surfaced recovery path or operator decision if supported by command semantics.

**Risk controlled**
- Hidden data loss and accidental resume from partial state.

### 3. Auth, crypto, or identity failure

**Condition**
- Invalid credentials, nonce/authentication failure, signature/identity mismatch, or similar trust failure.

**Handling**
- Stop processing.
- Surface error with context, excluding secrets.
- Do not degrade to unauthenticated or weakly authenticated behavior.

**Risk controlled**
- Unauthorized state mutation or recovery corruption.

### 4. GitHub persistence failure

**Condition**
- GitHub-backed state cannot be read or updated.

**Handling**
- Use `GitHubTool` error handling patterns.
- Respect bounded retry rules and rate-limit directives.
- Surface failure explicitly if synchronization cannot be completed.
- Do not claim convergence between local and GitHub layers unless write success is confirmed.

**Risk controlled**
- False assertion that dual-layer state is synchronized.

### 5. Local persistence failure

**Condition**
- Local state cannot be written or read.

**Handling**
- Surface error explicitly.
- Validate any write path before attempting modification.
- Do not continue as though checkpointing succeeded.

**Risk controlled**
- Illusory resumability and inconsistent restore behavior.

### 6. LLM provider failure during resumed execution

**Condition**
- One provider times out, errors, or returns invalid output after resume.

**Handling**
- Apply bounded retry and provider fallback rules.
- Escalate failure via error card and gate if generation cannot proceed safely.
- Never execute generated content to “test” viability.

**Risk controlled**
- Unsafe or non-deterministic continuation behavior.

### 7. SECURITY_REFUSAL

**Condition**
- Model returns `SECURITY_REFUSAL`.

**Handling**
- Stop immediately.
- Do not retry or rephrase.
- Emit error card.
- Gate.
- Log full prompt context with secrets excluded.
- Require explicit operator override.

**Risk controlled**
- Bypass of model-enforced security boundaries.

### 8. Mid-gate backend restart

**Condition**
- Process or backend restarts while awaiting operator input.

**Handling**
- Gate state is considered lost.
- Operator must re-approve.
- No implicit replay of prior approval.

**Risk controlled**
- Acting on stale or unverifiable approval state.

## Dependencies

### Internal Forge dependencies

- `BuildPipeline` in `src/build_director.py`
  - orchestrates stages and resume points
- `ConsensusEngine` in `src/consensus.py`
  - arbitrates multi-provider generation outcomes
- `BuildLedger` in `src/build_ledger.py`
  - records build progress and recoverable state
- `GitHubTool` in `src/github_tools.py`
  - exclusive interface for GitHub reads/writes
- `WebhookReceiver` in `src/github_tools.py`
  - receives GitHub-driven state signals where applicable
- `path_security.validate_write_path()`
  - mandatory validation before all file writes

### External/system dependencies

- LLM providers:
  - Anthropic
  - OpenAI
- GitHub:
  - PR state
  - remote persistence layer
  - CI/status integration
- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - maximum 16 MB per message

### Protocol dependencies

- `ready`
  - capability and environment advertisement
- `build_card`
  - streamed stage/progress updates
- `gate_card`
  - operator decision blocking
- `credentials`
  - provider and GitHub credentials
- `doc_status`
  - document-store status reporting where build context ingestion is involved

### Dependency constraints

- External documents and CI output are untrusted input.
- Document context is injected only into USER prompts.
- Unknown XPC message types are discarded and logged.
- Secret-bearing inputs must never be logged or reflected into generated artifacts.