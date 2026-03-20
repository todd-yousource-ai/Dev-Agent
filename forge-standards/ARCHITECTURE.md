# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build orchestration subsystem for Forge’s native macOS AI coding agent. It converts a plain-language build intent into an ordered implementation pipeline and manages execution state across generation, review, CI, gating, merge, and recovery.

At a subsystem level, it is responsible for:

- Decomposing work into an ordered sequence of PRs grouped by PRD/build plan.
- Generating implementation and tests via parallel LLM providers, with Claude acting as arbiter in the consensus flow.
- Running the defined review loop and CI stages for each PR.
- Emitting structured progress and gate messages to the UI/runtime over XPC.
- Blocking at human approval gates; it never auto-approves or auto-resolves operator decisions.
- Persisting and restoring build progress state across local and GitHub-backed recovery layers.
- Resuming in-progress work from the current thread state via `/continue`.
- Detecting divergence between recovery layers during `/restore` and forcing explicit operator resolution when interactive.

The subsystem is orchestration and state-management focused. It does not directly execute generated code, bypass operator gates, or perform ad hoc GitHub/API access outside approved abstractions.

## Component Boundaries

### In Scope

The subsystem includes the orchestration and state components represented by:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompt constants
  - provider retry/fallback behavior
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch across generation, review, CI, and merge preparation
- `src/build_ledger.py`
  - `BuildLedger`
  - persistent tracking of build/PR progress and recoverable state

It also depends on, but does not subsume, GitHub operations through:

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

### Explicit Boundaries

#### ConsensusDevAgent does

- Track current build identity and progress, including PRD context and per-PR completion state.
- Resume from current thread state using `/continue`.
- Restore from persisted state layers.
- Compare local and GitHub recovery state during restore without target selection.
- Surface divergence details, including conflicting fields.
- Apply operator-chosen reconciliation:
  - `local`: restore local and overwrite GitHub state
  - `github`: restore GitHub and overwrite local state
  - `cancel`: modify neither layer
- Emit build and gate cards to the UI.
- Enforce human-in-the-loop gates indefinitely.

#### ConsensusDevAgent does not

- Call GitHub APIs directly; all GitHub operations must go through `GitHubTool`.
- Execute generated code or shell out generated content.
- Place external document content into the system prompt.
- Silently recover from auth, crypto, identity, or security policy failures.
- Auto-resolve gates, approvals, or security refusals.
- Perform unchecked filesystem writes.

### Interface Boundary with UI / Runtime

The subsystem communicates over the Forge XPC protocol using line-delimited JSON, nonce-authenticated, with a max message size of 16MB.

Relevant protocol surfaces:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

`build_card` is used for streamed progress/status updates.  
`gate_card` is used for blocking operator decisions and must halt progression until a response is received.

## Data Flow

### 1. Build Initiation and Planning

1. The subsystem receives build intent and credentials/context from the runtime.
2. It establishes build identity and current state in the ledger.
3. It decomposes the work into an ordered set of PRs under a PRD/build plan.
4. It emits progress via `build_card`.

### 2. Generation and Consensus

1. `BuildPipeline` dispatches implementation stages.
2. `ConsensusEngine` invokes the configured LLM providers in parallel.
3. Claude arbitrates the resulting outputs.
4. Retry/fallback behavior is bounded:
   - `_claude_json`: retry after 10s, then fall back to OpenAI
   - `consensus.py`: retry with the other provider
   - never retry indefinitely; max 3 attempts total
5. Generated outputs are treated as untrusted artifacts until reviewed and validated.

### 3. Review, CI, and Gating

1. The subsystem runs the review cycle and CI routing for the current PR.
2. It emits `build_card` updates for progress and stage changes.
3. At approval or exception boundaries, it emits a `gate_card`.
4. Execution blocks until explicit operator input is received.
5. If the backend restarts mid-gate, gate state is lost; operator must re-approve.
6. Gate decisions have no undo path.

### 4. Persistence and Recovery

The subsystem maintains recoverable state in two layers:

- local persisted state
- GitHub-backed saved state

State includes current build identity and progress, including fields such as:

- completed PRs
- PR plans by PRD

### 5. `/continue`

`/continue` resumes build execution from the current thread state and returns:

`▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

This command does not create a new build plan; it resumes the active one represented by the current state.

### 6. `/restore` Divergence Detection

When `/restore` is run without a target, the subsystem loads both local and GitHub state and compares them.

#### No divergence

- If both layers agree, the subsystem restores silently and prints a single confirmation.

#### Divergence detected

The subsystem presents both states and the conflicting fields, e.g.:

- local build identity/progress
- save timestamps/relative age
- GitHub build identity/progress
- conflict field list such as `completed_prs`, `pr_plans_by_prd`

It then requires an explicit operator choice:

- `local`
- `github`
- `cancel`

#### Resolution semantics

- `local`
  - restore local
  - update GitHub to match local
- `github`
  - restore GitHub
  - update local to match GitHub
- `cancel`
  - modify neither layer
  - return to prompt

In non-interactive mode, divergence may be auto-resolved only according to explicit non-interactive policy; the subsystem must not silently pick a side without such policy.

## Key Invariants

These invariants are mandatory and subsystem-defining.

### Security and Trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and validated:
  - documents
  - PR comments
  - CI output
  - GitHub/webhook payloads
- Generated code is never executed by the agent.
- SECURITY_REFUSAL is terminal for the current action:
  - do not retry
  - do not rephrase
  - emit error card
  - gate
  - log full prompt context per policy
  - require explicit operator override

### Human-in-the-Loop Gating

- Gates never auto-resolve.
- Gates wait indefinitely for operator input.
- There is no auto-approve path.
- If backend restarts mid-gate, gate approval state is lost and must be re-acquired.
- Gate decisions have no undo.

### Filesystem Safety

- All file writes must be validated through `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Writes outside approved repository boundaries are forbidden.

### Prompt and Context Handling

- Context from external documents must go in the USER prompt, never the SYSTEM prompt.
- Credentials must never appear in prompts.
- Rephrasing must not be used to bypass a refusal or security boundary.

### GitHub Consistency

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Blind GitHub writes are forbidden; operations requiring optimistic concurrency must include SHA/ETag protections as appropriate.
- ETag caching is required on polling endpoints.
- Rate-limit handling must follow policy:
  - 403 primary rate limit: exponential backoff starting at 60s
  - 429 secondary rate limit: respect `Retry-After` exactly

### Transport and Protocol

- XPC unknown message types are discarded and logged; they are never raised as exceptions.
- XPC messages are line-delimited JSON and nonce-authenticated.
- Message size must remain within the 16MB protocol limit.

## Failure Modes

### Recovery State Divergence

Condition:
- Local and GitHub recovery layers differ on one or more tracked fields.

Behavior:
- Surface both states and list conflict fields.
- Require explicit resolution in interactive mode.
- Do not silently merge field-by-field.
- On `cancel`, do not modify either layer.

Risk controlled:
- Restoring stale or partially-complete state without operator awareness.

### Auth / Crypto / Identity Failure

Condition:
- Invalid or missing credentials, nonce/auth validation failure, identity mismatch.

Behavior:
- Fail closed.
- Surface error with context.
- Do not continue with degraded trust.

Risk controlled:
- Unauthorized actions, state corruption, cross-identity restore.

### Provider Failure or Degraded Generation

Condition:
- Claude/OpenAI request failure, malformed provider response, transient upstream issue.

Behavior:
- Use bounded retry/fallback only.
- Maximum 3 attempts total.
- If exhausted, surface failure; do not loop indefinitely.

Risk controlled:
- Infinite retry loops, hidden partial failure, inconsistent generation state.

### Mid-Gate Restart

Condition:
- Backend restart/crash while awaiting operator input.

Behavior:
- Gate state is lost.
- Operator must explicitly re-approve after recovery.
- No assumption of prior approval.

Risk controlled:
- Implicit approval due to process loss.

### GitHub Write Inconsistency

Condition:
- Missing SHA, stale remote state, webhook/API mismatch, poll cache inconsistency.

Behavior:
- Route all writes through `GitHubTool`.
- Use concurrency-safe write semantics.
- Surface conflicts rather than overwriting blindly.

Risk controlled:
- Lost updates and remote state corruption.

### Filesystem Write Violation

Condition:
- Invalid path, traversal attempt, non-validated write target.

Behavior:
- Reject write before execution.
- Surface error; do not attempt fallback path writing.

Risk controlled:
- Repository escape and unauthorized file modification.

### Security Refusal from Model or Policy Layer

Condition:
- Model returns `SECURITY_REFUSAL` or policy identifies forbidden behavior.

Behavior:
- Stop immediately.
- Do not retry or rephrase.
- Emit error card, gate, and log according to policy.
- Require explicit operator override.

Risk controlled:
- Refusal bypass and unsafe code generation.

### Unknown XPC Message Types

Condition:
- Runtime receives unrecognized protocol message.

Behavior:
- Discard and log.
- Never raise as an exception.

Risk controlled:
- Transport instability from forward-compatibility cases.

## Dependencies

### Internal Modules

- `src/consensus.py`
  - consensus generation orchestration
  - provider selection, arbitration, and retry/fallback logic
- `src/build_director.py`
  - build stage orchestration and dispatch
- `src/build_ledger.py`
  - persistent build state and recovery tracking
- `src/github_tools.py`
  - sole GitHub integration surface
  - webhook handling and repository operations

### External Services / Protocols

- Anthropic provider
- OpenAI provider
- GitHub
- Forge XPC transport

### Required Runtime Contracts

- Nonce-authenticated XPC transport
- Structured message schemas for `ready`, `build_card`, `gate_card`, `credentials`, and `doc_status`
- Valid credential injection from runtime
- Operator availability for gate resolution
- Recovery storage in both local and GitHub-backed layers

### Security / Platform Contracts

- `path_security.validate_write_path()` must guard every file write
- External content validation must occur before use
- Secrets redaction/logging policy must be enforced across all execution paths
- Generated code must never be executed by this subsystem