# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the orchestration subsystem for Forge’s native macOS AI coding workflow. It converts a plain-language build intent into an ordered sequence of implementation pull requests, coordinates multi-provider code generation and arbitration, runs review and CI stages, and blocks on explicit operator approval before merge.

At a subsystem level, ConsensusDevAgent is responsible for:

- Maintaining build progress and recovery state across a multi-PR execution thread
- Resuming an in-progress build via `/continue` from current thread state
- Restoring persisted execution state from local and GitHub-backed recovery layers
- Detecting divergence between recovery layers and requiring operator-directed resolution
- Driving the build pipeline through staged generation, review, CI, and merge gates
- Enforcing platform safety rules around prompts, credentials, file writes, and external input handling

The `/continue` command resumes execution from the current thread state and emits:

```text
▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]
```

Recovery state management includes dual-layer restore behavior. When `/restore` is invoked without a target, the subsystem loads both local and GitHub recovery state, compares them, and either:

- restores silently when both layers agree, or
- surfaces a divergence gate when material fields differ

Example divergence output:

```text
⚠  Local and GitHub state diverge:

Local  : ConsensusDevAgent — PRD-001, 3/11 PRs done
Saved: 2026-03-19 18:45:00 (2h ago)

GitHub : ConsensusDevAgent — PRD-001, 0/11 PRs done
Saved: 2026-03-19 16:30:00 (4h ago)

Conflict fields: completed_prs, pr_plans_by_prd

Which to restore? (local / github / cancel)
```

Conflict resolution semantics are strict:

- `local`: restore local state, then update GitHub to match
- `github`: restore GitHub state, then update local to match
- `cancel`: modify neither layer and return control to the operator

In non-interactive mode, divergence is auto-resolved according to the configured recovery policy, but the subsystem must still preserve fail-closed semantics and never silently discard conflicting state.

## Component Boundaries

ConsensusDevAgent is an orchestration and state-management subsystem. Its boundaries are defined by what it controls directly versus what it invokes through typed platform interfaces.

### Inside the subsystem

Primary responsibilities include:

- Build-thread state tracking
- Recovery-state persistence and restore coordination
- Divergence detection across local and GitHub persistence layers
- PR sequence progress accounting
- Stage dispatch across generation, review, CI, and approval gates
- Operator-facing continuation and restore messaging
- Enforcement of prompt-routing and safety invariants for this workflow

Primary implementation files in scope:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts/constants
  - provider arbitration and retry/fallback behavior
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch
- `src/build_ledger.py`
  - `BuildLedger`
  - persistent progress/state accounting

### Outside the subsystem

ConsensusDevAgent does not directly own:

- Raw GitHub API access
- Credential issuance or auth policy
- XPC transport definition
- Document embedding/storage internals
- Execution of generated code
- Final operator judgment at approval gates

Those concerns are delegated to other platform interfaces and must be accessed only through approved abstractions.

Notable external boundary interfaces:

- `GitHubTool` in `src/github_tools.py`
  - all GitHub operations must flow through this tool
  - direct GitHub API usage is forbidden
- `path_security.validate_write_path()`
  - all file writes must be validated before execution
- XPC messaging layer
  - line-delimited JSON
  - nonce-authenticated
  - max 16MB per message
- UI/build-stream consumers
  - `build_card`
  - `gate_card`
  - `doc_status`

### Explicit non-responsibilities

ConsensusDevAgent must not:

- execute generated code
- evaluate generated content with `eval`, `exec`, or subprocess execution
- bypass gates
- auto-approve merges
- place external document context into the system prompt
- silently resolve security refusals
- write files without validated paths
- perform blind GitHub writes without SHA protection

## Data Flow

### 1. Build initiation and planning

1. Operator provides build intent.
2. ConsensusDevAgent decomposes the intent into an ordered PR plan.
3. Build state is recorded in the ledger, including PRD association, planned PRs, and completed PR tracking.
4. Progress is streamed via `build_card` messages to the UI.

Relevant state examples include:

- current PRD
- current PR number/title
- completed PR count
- `completed_prs`
- `pr_plans_by_prd`

### 2. Generation and consensus

1. `BuildPipeline` dispatches generation for the current PR.
2. `ConsensusEngine` invokes two LLM providers in parallel.
3. Claude arbitrates outputs.
4. Generated implementation and tests are produced.
5. Review cycle runs in three passes.
6. CI executes through the platform CI routing path.
7. A gate is emitted for operator approval before merge.

Prompt-routing rule:

- context from external documents must be placed in the USER prompt, never the SYSTEM prompt

External inputs considered untrusted and validated:

- documents
- PR comments
- CI output

### 3. Persistence and recovery

ConsensusDevAgent maintains two recovery layers:

- local persisted state
- GitHub-backed persisted state

On `/continue`:

1. Load current thread state.
2. Reconstruct active build context.
3. Emit resume banner.
4. Continue from the last persisted stage.

On `/restore` without explicit target:

1. Load local layer.
2. Load GitHub layer.
3. Compare material recovery fields.
4. If equal, restore once and confirm.
5. If divergent, emit a blocking operator choice gate:
   - `local`
   - `github`
   - `cancel`

On operator selection:

- `local`
  - local becomes authoritative source
  - GitHub recovery layer is updated to match local
- `github`
  - GitHub becomes authoritative source
  - local recovery layer is updated to match GitHub
- `cancel`
  - no writes performed
  - return to prompt

### 4. Gate handling

Gates are emitted as `gate_card` messages and block indefinitely until operator response.

Required gate semantics:

- no auto-approve ever
- no silent gate resolution
- if backend restarts mid-gate, gate state is lost and operator must re-approve
- there is no undo on gate decisions

### 5. Error handling and provider fallback

Error behavior is explicit and bounded:

- no silent failure paths
- every error must surface with context
- provider retries are limited to a maximum of 3 attempts total
- `_claude_json` retries after 10 seconds, then falls back to OpenAI
- in `consensus.py`, failures retry with the other provider
- never retry indefinitely

Rate/permission handling:

- `403` primary rate limit: exponential backoff starting at 60s
- `429` secondary rate limit: respect `Retry-After` exactly
- polling endpoints use ETag caching

Security refusal handling:

- stop immediately
- do not retry
- do not rephrase
- emit error card
- gate
- log full prompt context
- require explicit operator override

## Key Invariants

These are enforced subsystem rules, not preferences.

### Safety and trust boundaries

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; all errors surface with contextual information.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and must be validated before use.
- Generated code is never executed by the agent.
- Context from external documents is placed in USER prompts only, never SYSTEM prompts.
- `SECURITY_REFUSAL` is terminal unless explicitly overridden by the operator.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Human-in-the-loop guarantees

- Gates wait indefinitely for operator input.
- Gates never auto-resolve.
- There is no auto-approve path.
- If restart occurs during a gate, prior gate approval is not assumed.
- Gate decisions have no undo path; subsequent actions must be explicit and newly gated if needed.

### State correctness

- Recovery restore without target compares both persistence layers before selection.
- Divergent state is never silently overwritten.
- Conflict resolution writes exactly one source of truth into the other layer after explicit selection.
- `cancel` performs no mutation.
- `/continue` resumes from current persisted thread state only; it does not synthesize missing approval or completion state.

### File and GitHub integrity

- Every write path must be validated by `path_security.validate_write_path()` before write execution.
- All GitHub operations go through `GitHubTool`.
- Blind GitHub writes without SHA are forbidden.
- Direct GitHub API access from this subsystem is forbidden.

### Resource discipline

OI-13 remains unresolved, but current architectural expectation is:

- keep allocations minimal
- document every allocation explicitly where recovery/state structures or streamed payloads are introduced

## Failure Modes

### Recovery-state divergence

Condition:
- local and GitHub recovery layers differ on material fields such as `completed_prs` or `pr_plans_by_prd`

Behavior:
- emit explicit divergence summary
- require operator or configured non-interactive policy resolution
- do not mutate either layer before resolution

Risk controlled:
- accidental rollback or overwrite of authoritative progress state

### Missing or invalid recovery state

Condition:
- one or both recovery layers cannot be loaded, parsed, authenticated, or validated

Behavior:
- fail closed
- surface the error with context
- do not fabricate replacement state silently

Risk controlled:
- restoring from corrupted, spoofed, or partial state

### Auth, crypto, or identity errors

Condition:
- invalid credentials, nonce/authentication failure, identity mismatch, or cryptographic validation failure

Behavior:
- fail closed immediately
- no degraded mode
- no partial continuation

Risk controlled:
- unauthorized actions and state corruption

### Provider generation failure

Condition:
- LLM provider error, timeout, malformed output, or arbitration failure

Behavior:
- bounded retry/fallback behavior only
- maximum 3 attempts total
- then emit surfaced failure and gate/escalate as required

Risk controlled:
- infinite retry loops and hidden degraded quality

### Security refusal

Condition:
- model emits `SECURITY_REFUSAL` or equivalent policy stop condition

Behavior:
- stop
- no retry
- no rephrase
- emit error card
- gate
- require explicit operator override

Risk controlled:
- bypass of safety constraints through prompt mutation or repeated attempts

### Rate limits and GitHub operation failures

Condition:
- GitHub/API throttling or access denial

Behavior:
- `403`: exponential backoff starting at 60s
- `429`: honor `Retry-After`
- use ETag caching on polling endpoints
- all failures remain visible

Risk controlled:
- abusive retry behavior and hidden sync drift

### Gate loss on restart

Condition:
- backend process restarts while awaiting approval

Behavior:
- gate state is lost
- operator must re-approve
- no implicit continuation through prior gate

Risk controlled:
- unintended progression without live approval

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - consensus generation engine
  - provider selection, retries, fallback, arbitration
- `src/build_director.py`
  - pipeline orchestration and stage transitions
- `src/build_ledger.py`
  - persisted build/recovery state
- `src/github_tools.py`
  - `GitHubTool`
  - webhook and GitHub interaction boundary

### Platform/interface dependencies

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - 16MB max message size
- UI streaming protocol
  - `build_card`
  - `gate_card`
  - `doc_status`
- credentials object
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- path validation service
  - `path_security.validate_write_path()`
- document store/status plumbing for external context retrieval

### Operational dependencies

- LLM providers:
  - Anthropic/Claude
  - OpenAI
- GitHub as external persistence and PR system of record
- CI routing infrastructure for validation stages
- operator presence for all approval gates and divergence choices

### Dependency constraints

- GitHub must be accessed only through `GitHubTool`
- external document context must not enter the system prompt
- generated code must never be executed as part of dependency interaction
- unknown XPC messages must be discarded and logged rather than surfaced as runtime exceptions