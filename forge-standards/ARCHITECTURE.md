# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding agent. It converts a plain-language build intent into a controlled, human-gated implementation pipeline.

At a subsystem level, it is responsible for:

- Decomposing work into an ordered sequence of PRs aligned to PRDs.
- Generating implementation and tests using multiple LLM providers in parallel.
- Arbitrating generation output through the consensus engine.
- Running a 3-pass review cycle.
- Executing CI and surfacing results.
- Emitting streamed build state and gate prompts to the UI layer.
- Persisting and restoring recovery state across local and GitHub-backed storage.
- Resuming interrupted work from current thread state via `/continue`.

It is not an autonomous executor. The operator remains in the loop at every gate, and merge/approval actions never auto-resolve.

Recovery behavior is part of the subsystem contract:

- `/continue` resumes from the current thread state.
- Output format is:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

State restoration supports dual-layer recovery state (local and GitHub). When `/restore` is invoked without an explicit target, the subsystem compares both layers and detects divergence before restoring.

## Component Boundaries

### Inside this subsystem

Primary implementation units identified in the architecture context:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompt constants
  - provider arbitration and fallback behavior
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/build_ledger.py`
  - `BuildLedger`
  - durable build/progress tracking
- Recovery-state logic associated with `/continue`, `/restore`, and divergence handling

Responsibilities owned here:

- Build-stage progression
- PRD/PR sequencing state
- LLM generation coordination
- Review/CI orchestration
- Recovery-state read/compare/restore/update logic
- Gate emission and blocking semantics
- Progress card emission for UI consumers

### Outside this subsystem

The following are dependencies or adjacent systems, not responsibilities of ConsensusDevAgent:

- `src/github_tools.py`
  - All GitHub reads/writes must go through `GitHubTool`
  - Direct GitHub API usage is forbidden
- XPC transport/runtime
  - Message framing, nonce authentication, capability negotiation
- BuildStreamView/UI
  - Renders `build_card` and `gate_card`
- Credential acquisition and secure storage
- Document store embedding/indexing lifecycle
- Operator identity/authn/authz enforcement
- Path-security implementation
  - Writes must be validated through `path_security.validate_write_path()`

ConsensusDevAgent may consume these services but does not redefine their contracts.

## Data Flow

### 1. Session start and readiness

The subsystem operates inside the Forge platform runtime and communicates over XPC wire protocol:

- Line-delimited JSON
- Nonce-authenticated
- Maximum 16 MB per message

The surrounding runtime provides readiness metadata such as:

- `ready { agent_version, min_swift_version, capabilities[], doc_store_status }`

ConsensusDevAgent uses this environment to determine whether required capabilities and supporting services are available before proceeding.

### 2. Build intent to execution plan

Input enters as operator-provided plain-language intent plus validated external context. External documents are untrusted input and must be placed in the USER prompt, never the SYSTEM prompt.

The subsystem then:

1. Interprets build intent.
2. Decomposes work into PRDs / ordered PR plan.
3. Records plan state in ledger/recovery storage.
4. Dispatches stages through `BuildPipeline`.

### 3. Code generation and arbitration

For each PR/stage:

1. Context is assembled from repository state and approved documents.
2. Multiple LLM providers generate candidate outputs in parallel.
3. `ConsensusEngine` arbitrates results.
4. Retry/fallback policy is applied:
   - In `_claude_json`: retry after 10s, then fall back to OpenAI
   - In `consensus.py`: retry with the other provider
   - Never retry indefinitely
   - Maximum 3 attempts total
   - `403` primary rate/availability handling: exponential backoff starting at 60s
   - `429` secondary limits: respect `Retry-After` exactly

Generated code is treated strictly as data. It is never executed by the agent.

### 4. Review, CI, and gating

After generation:

1. The subsystem performs the review cycle.
2. It routes CI execution and captures results.
3. It emits progress updates using:
   - `build_card { card_type, stage, content, progress }`
4. When human approval is required, it emits:
   - `gate_card { gate_type, options[], description }`

Gate semantics are strict:

- Gates block until operator response.
- Gates never auto-resolve.
- If backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo on gate decisions.

### 5. Recovery, restore, and continue

ConsensusDevAgent maintains recovery state in two layers:

- Local state
- GitHub-backed state

`/continue`:
- Resumes build from current thread state
- Announces resumed context using the required status line

`/restore` without explicit target:
1. Load local layer.
2. Load GitHub layer.
3. Compare state.
4. If both layers agree:
   - Restore silently
   - Print single confirmation
5. If divergence exists:
   - Surface both snapshots
   - Surface conflicting fields
   - Prompt operator: `local / github / cancel`

Conflict fields may include, at minimum:

- `completed_prs`
- `pr_plans_by_prd`

Conflict resolution behavior:

- `local`
  - Restore local state
  - Update GitHub to match
- `github`
  - Restore GitHub state
  - Update local to match
- `cancel`
  - Modify neither layer
  - Return to prompt

Non-interactive mode supports auto-resolution behavior, but the subsystem must still preserve explicit, deterministic conflict handling semantics.

## Key Invariants

The subsystem must preserve the following platform-level invariants and subsystem-specific enforcement rules.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors.
- Never degrade silently on security-sensitive failures.
- No silent failure paths; all errors surface with context.
- Secrets never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and validated:
  - documents
  - PR comments
  - CI output
- Context from external documents belongs only in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the current action:
  - do not rephrase
  - do not retry
  - emit error card
  - gate
  - log full prompt context
  - require explicit operator override

### Execution safety

- Generated code is never executed by the agent.
- No `eval`, `exec`, or subprocess execution of generated content.
- Forbidden patterns include:
  - shell injection
  - credential in log
  - credential in prompt
  - direct execution of generated code
  - path traversal
  - blind GitHub write without SHA
  - context in system prompt
  - ignoring `SECURITY_REFUSAL`

### File and repository safety

- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- GitHub operations must go through `GitHubTool` only.
- Never use the GitHub API directly.
- Blind GitHub writes are forbidden; write operations must include SHA-aware safety semantics where required.

### Gate and operator-control semantics

- Human approval is mandatory at every gate.
- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Gate decisions are not undoable within the subsystem.
- Mid-gate backend restart invalidates gate memory; operator must re-approve.

### Transport and protocol robustness

- XPC unknown message types are discarded and logged, never raised as exceptions.
- Protocol payloads must conform to the documented wire format and size limits.

### Recovery-state consistency

- Restore without explicit target must compare both recovery layers.
- Divergence must be surfaced explicitly with conflicting fields.
- Resolution must be operator-selected in interactive mode unless an explicit non-interactive policy applies.
- After conflict resolution, the non-selected layer must be updated to match the chosen source, except on `cancel`.

## Failure Modes

### LLM/provider failures

Examples:

- provider timeout
- malformed provider response
- authentication failure
- rate limiting
- provider-specific refusal/error

Handling requirements:

- Surface the error with context.
- Apply bounded retry/fallback only.
- Maximum 3 attempts total.
- Never retry indefinitely.
- Respect provider-specific backoff contracts (`403`, `429`, `Retry-After`).
- If recovery is not possible, emit an error/gate rather than silently skipping work.

### Security refusal or unsafe generation path

If a generation or action path triggers `SECURITY_REFUSAL` or violates forbidden-pattern checks:

- Stop immediately.
- Do not retry.
- Do not rephrase around refusal.
- Emit error card.
- Gate for operator intervention.
- Log sufficient context without exposing secrets.

### Recovery divergence

When local and GitHub recovery state differ:

- The subsystem must not silently pick one.
- It must present both states, timestamps, and conflict fields.
- It must request resolution or apply an explicit non-interactive policy.
- `cancel` must leave both layers untouched.

### Persistence/update asymmetry

Possible scenario:

- local restore succeeds
- GitHub sync-back fails

Required behavior:

- Surface partial failure explicitly.
- Do not claim convergence if both layers were not updated successfully.
- Preserve enough state for operator-directed retry/recovery.

### Gate-state loss on restart

If the backend restarts while awaiting a gate response:

- prior gate approval state is lost
- operator must re-approve

This is expected behavior and must be documented in emitted operator-facing flow.

### Transport/protocol errors

Examples:

- oversized XPC message
- malformed line-delimited JSON
- unknown XPC message type

Handling requirements:

- Reject or discard invalid input safely.
- Log with context.
- Do not convert unknown message types into raised exceptions.

### Invalid external input

Examples:

- malformed documents
- adversarial PR comments
- corrupted CI output
- invalid restore metadata

Handling requirements:

- Treat as untrusted
- validate before use
- fail closed where identity/auth/security implications exist
- never promote untrusted content into SYSTEM prompt context

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - consensus arbitration
  - provider fallback/retry logic
- `src/build_director.py`
  - pipeline orchestration
  - stage dispatch
- `src/build_ledger.py`
  - build progress/state tracking
- `src/github_tools.py`
  - all GitHub interactions

### Platform/runtime dependencies

- XPC transport with Forge wire protocol
- BuildStreamView/UI consumers of `build_card` and `gate_card`
- credentials payload:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- document-store status and retrieval facilities
- path security validation

### External service dependencies

- LLM providers used for parallel generation and fallback
- GitHub as source of repository state and one recovery-state layer
- CI systems as producers of build/test status

### Dependency constraints

- All GitHub ops go through `GitHubTool`.
- All polling endpoints should use ETag caching where applicable.
- External inputs from documents, GitHub comments, and CI are untrusted.
- Credentials must never be logged or injected into prompts.
- The subsystem depends on operator interaction for gate completion and cannot autonomously finalize gated steps.