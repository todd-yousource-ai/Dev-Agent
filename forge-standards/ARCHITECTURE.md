# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding agent. It accepts a plain-language build intent and drives an ordered, operator-gated implementation workflow across multiple pull requests.

At a high level, the subsystem:

- Decomposes a requested build into an ordered PR plan, typically grouped by PRD.
- Tracks build progress and recovery state across local and GitHub-backed persistence layers.
- Resumes interrupted work from the current thread state via `/continue`.
- Restores prior state and detects divergence between persistence layers during recovery.
- Coordinates parallel code generation through two LLM providers, with Claude acting as arbiter in the consensus flow.
- Runs review and CI stages, then blocks on explicit operator approval before merge or any gate transition.
- Streams progress and gate state to the UI over XPC using Forge wire formats.

The `/continue` command resumes work from the current thread state and emits:

```text
▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]
```

Recovery behavior is part of the subsystem contract. When `/restore` is invoked without an explicit target, the subsystem loads both local and GitHub recovery layers, compares them, and either:

- restores silently if the layers agree, or
- surfaces divergence and requires explicit operator choice.

On divergence, the subsystem presents both views of state, identifies conflicting fields, and asks the operator to choose `local`, `github`, or `cancel`. The chosen source becomes authoritative and the other layer is updated to match. `cancel` leaves both layers unchanged.

This subsystem is stateful, operator-gated, and fail-closed.

## Component Boundaries

ConsensusDevAgent is responsible for build-state orchestration, recovery, provider coordination, and gated progression. It is not a general execution runtime and does not directly execute generated code.

Primary in-repo components:

- `src/consensus.py`
  - Hosts `ConsensusEngine`
  - Defines generation system prompts such as `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM`
  - Manages provider-level consensus and fallback behavior between LLM providers

- `src/build_director.py`
  - Hosts build pipeline orchestration
  - Dispatches work by stage
  - Coordinates transitions between planning, generation, review, CI, and gate waits

- `src/github_tools.py`
  - Hosts `GitHubTool` and `WebhookReceiver`
  - Sole boundary for GitHub operations
  - Enforces repository-side interaction patterns, including safe writes and polling behavior

- `src/build_ledger.py`
  - Hosts `BuildLedger`
  - Tracks build progress, PR completion state, and recovery metadata used by continue/restore flows

Subsystem responsibilities:

- Build plan progression and PR sequencing
- Local and GitHub-backed recovery state management
- Divergence detection and operator-mediated conflict resolution
- Gate presentation and indefinite wait semantics
- Build status streaming to UI
- Coordination of code generation and review routing
- Enforcement of recovery-state consistency after operator resolution

Explicit non-responsibilities:

- Direct use of GitHub APIs outside `GitHubTool`
- Execution of generated code
- Auto-approval of gates
- Silent conflict resolution in interactive recovery flows
- Placement of external document context into the system prompt
- Unvalidated file writes

## Data Flow

### 1. Build initiation and planning

1. Operator provides build intent.
2. `build_director.py` initializes or resumes a pipeline.
3. The subsystem decomposes work into an ordered PR sequence, typically associated with a PRD.
4. Build state is persisted through `BuildLedger` and mirrored to configured recovery layers.

### 2. Generation and review flow

1. The current PR task is sent into the consensus generation path in `consensus.py`.
2. Two LLM providers are used in parallel for implementation/test generation.
3. Claude arbitrates the outputs under the consensus model.
4. Generated artifacts move through the review cycle and CI routing.
5. A gate is emitted to the UI when operator approval is required.
6. The subsystem blocks indefinitely until the operator responds.

Relevant UI protocol objects:

- `build_card`
  - `{ card_type, stage, content, progress }`
  - Streamed to `BuildStreamView`

- `gate_card`
  - `{ gate_type, options[], description }`
  - Blocks until operator responds

### 3. Continue flow

`/continue` resumes from current thread state rather than reconstructing a new plan. The subsystem loads the active build context and announces the current PRD and PR position.

Behavioral contract:

- Resume must reflect current persisted thread/build state.
- Resume must not skip gates.
- Resume must not infer approval from prior incomplete state.

### 4. Restore and divergence detection

When `/restore` is run without an explicit target:

1. The subsystem loads both recovery layers:
   - local recovery state
   - GitHub-backed recovery state
2. It compares the layers field-by-field.
3. If equivalent, restore proceeds silently with a single confirmation.
4. If different, the subsystem prints a divergence warning including:
   - local summary
   - GitHub summary
   - save timestamps
   - conflicting fields

Example conflicting fields include:

- `completed_prs`
- `pr_plans_by_prd`

The operator must select one of:

- `local`
- `github`
- `cancel`

Resolution rules:

- `local`
  - restore local state
  - update GitHub-backed state to match local

- `github`
  - restore GitHub-backed state
  - update local state to match GitHub

- `cancel`
  - modify neither layer
  - return to prompt

For non-interactive mode, auto-resolution behavior is a distinct path and must remain explicit; it must not masquerade as interactive resolution.

### 5. External document and UI input handling

All external inputs are treated as untrusted, including:

- documents
- PR comments
- CI output
- webhook payloads
- operator-provided recovery targets

External document context is placed in the USER prompt only, never the SYSTEM prompt.

### 6. File and network write path

Any file write triggered by the subsystem must first pass:

- `path_security.validate_write_path()`

Any GitHub mutation must go through:

- `GitHubTool`

No direct GitHub API usage is permitted outside that boundary.

## Key Invariants

These invariants are subsystem-level requirements inherited from Forge architecture and reinforced by ConsensusDevAgent behavior.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and validated before use.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` is terminal for the attempted action: do not rephrase, bypass, or silently continue.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Gating and operator control

- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- There is no auto-approve path.
- If backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo on gate decisions; decisions are final for that transition.

### Recovery and consistency

- `/continue` resumes from current thread state only.
- `/restore` without target compares both recovery layers before choosing a state.
- Divergence between local and GitHub state must be surfaced explicitly.
- Interactive divergence resolution requires explicit operator selection.
- After operator selection, the non-authoritative layer must be overwritten to match the selected authoritative state.
- `cancel` must leave both layers unchanged.
- Recovery must never silently merge divergent fields.

### File, prompt, and GitHub discipline

- All file writes must be path-validated before execution.
- All GitHub operations must go through `GitHubTool`; never call GitHub directly.
- Blind GitHub writes are forbidden; operations must preserve expected SHA semantics.
- External context belongs in the USER prompt, never the SYSTEM prompt.
- Context from documents must not be promoted into privileged instruction channels.

### Retry and backoff behavior

- Do not retry indefinitely; maximum 3 total attempts.
- In `_claude_json`, retry once after 10 seconds, then fall back to OpenAI.
- In `consensus.py`, retry with the other provider when applicable.
- For GitHub `403` primary rate limits, use exponential backoff starting at 60 seconds.
- For GitHub `429` secondary rate limits, respect `Retry-After` exactly.
- Use ETag caching on all polling endpoints.

### Allocation discipline

- Keep allocations minimal.
- Document every allocation explicitly.

This is an unresolved architecture concern but still a required operating constraint for the subsystem.

## Failure Modes

### Recovery-layer divergence

Condition:
- Local and GitHub recovery state differ during `/restore` without target.

System response:
- Print divergence summary and conflicting fields.
- Gate on operator choice in interactive mode.
- Do not mutate either layer until a valid resolution is selected.
- If resolved to one side, overwrite the other side to match.

Risk if violated:
- Resuming from stale or mixed build state
- PR sequence corruption
- Incorrect completed-PR accounting

### Lost gate state after restart

Condition:
- Backend restarts while awaiting operator input at a gate.

System response:
- Prior gate wait is not implicitly resumed as approved.
- Operator must explicitly re-approve.

Risk if violated:
- Unauthorized transition across merge, restore, or release boundaries

### Provider failure or degraded generation

Condition:
- LLM provider error, timeout, malformed result, or refusal

System response:
- Apply bounded retry/fallback policy
- Surface error context
- Emit error card and gate when required
- Do not silently substitute success

Risk if violated:
- Corrupt generated output
- Hidden failure in consensus arbitration
- Unsafe continuation after refusal or malformed output

### GitHub API constraints and write safety

Condition:
- Rate limit, auth failure, SHA mismatch, webhook anomaly, or direct-write attempt

System response:
- Route all operations through `GitHubTool`
- Respect backoff/retry rules
- Fail closed on auth/identity issues
- Reject blind writes

Risk if violated:
- Repository state corruption
- Write races
- Unauthorized mutations

### Path validation failure

Condition:
- A file write target fails path validation.

System response:
- Reject the write before execution.
- Surface the error with context.

Risk if violated:
- Path traversal
- Unsafe writes outside allowed repository scope

### Security refusal handling

Condition:
- Security subsystem or model returns `SECURITY_REFUSAL`.

System response:
- Stop immediately.
- Do not retry.
- Do not rephrase.
- Emit error card.
- Gate.
- Log full prompt context with secrets still excluded.

Risk if violated:
- Policy bypass
- Unsafe code generation or action execution

### XPC protocol anomalies

Condition:
- Malformed payload, oversized message, or unknown message type

System response:
- Enforce line-delimited JSON protocol constraints
- Discard unknown message types and log them
- Do not escalate unknown-type handling into exceptions

Risk if violated:
- UI/backend desynchronization
- Crash-on-input behavior
- Potential denial of service

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - Consensus generation and provider arbitration
- `src/build_director.py`
  - Pipeline stage orchestration
- `src/build_ledger.py`
  - Persistent build and recovery state tracking
- `src/github_tools.py`
  - Exclusive GitHub integration boundary

### Platform and protocol dependencies

- XPC transport
  - Line-delimited JSON
  - Nonce-authenticated
  - Maximum 16 MB per message

- Ready message contract
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

- Build stream contract
  - `build_card: { card_type, stage, content, progress }`

- Gate contract
  - `gate_card: { gate_type, options[], description }`

- Credentials contract
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

- Document status contract
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### External service dependencies

- Anthropic provider
- OpenAI provider
- GitHub APIs, but only through `GitHubTool`

### Cross-cutting operational dependencies

- Path validation via `path_security.validate_write_path()`
- Logging/error-card infrastructure for surfaced failures
- Operator-interaction channel for all gates and divergence resolution
- Document-store pipeline for external context ingestion, with strict prompt-boundary enforcement

### Dependency rules

- Never call GitHub directly outside `GitHubTool`.
- Never place external document context into the SYSTEM prompt.
- Never execute generated code.
- Never permit unbounded retries.
- Never allow gate transitions without explicit operator input.