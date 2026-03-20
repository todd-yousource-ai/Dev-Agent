# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding workflow. It converts a plain-language build intent into an ordered, operator-gated sequence of pull requests, coordinates multi-provider code generation and review, persists execution state for recovery, and resumes interrupted work deterministically.

At a high level, the subsystem is responsible for:

- decomposing a requested build into PRD-scoped and PR-scoped work
- orchestrating implementation generation and test generation across LLM providers
- arbitrating between provider outputs via the consensus engine
- driving the staged build pipeline and CI execution
- presenting progress and gate state to the UI through protocol cards
- persisting and restoring build state across local and GitHub-backed storage layers
- requiring explicit operator approval at every gate before merge or equivalent irreversible action

The subsystem includes explicit recovery semantics:

- `/continue` resumes the build from the current thread state
- `/restore` reloads saved state from persistence layers
- when `/restore` is invoked without a target, the subsystem loads both local and GitHub state layers and performs divergence detection before restoring

The `/continue` command emits:

- `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

The subsystem is not an autonomous merge engine. It remains human-gated throughout execution and does not auto-approve, auto-resolve gates, or silently reconcile conflicting persisted state.

---

## Component Boundaries

### In Scope

The ConsensusDevAgent subsystem includes the following core responsibilities and implementation surfaces:

- **Pipeline orchestration**
  - `src/build_director.py`
  - Owns build stage dispatch and overall `BuildPipeline` sequencing

- **Consensus generation and arbitration**
  - `src/consensus.py`
  - Owns `ConsensusEngine`
  - Defines generation system prompts and provider fallback behavior
  - Runs multi-provider generation and arbitration logic

- **GitHub interaction facade**
  - `src/github_tools.py`
  - All GitHub operations must go through `GitHubTool`
  - Also includes webhook receiving responsibilities where applicable
  - Direct use of the GitHub API outside this abstraction is forbidden

- **Build state persistence**
  - `src/build_ledger.py`
  - Owns persisted execution state, progress tracking, and recovery metadata

- **Protocol emission**
  - Produces protocol-compliant messages such as:
    - `build_card`
    - `gate_card`
    - readiness and status payloads as defined by Forge protocol references

- **Recovery/state reconciliation**
  - Local state load/save
  - GitHub-backed state load/save
  - Divergence detection and explicit operator-selected reconciliation

### Out of Scope

The subsystem does **not** own:

- direct execution of generated code
- bypassing operator gates
- arbitrary shell execution of generated content
- unmanaged filesystem writes
- direct raw GitHub API calls outside `GitHubTool`
- silent recovery or silent conflict resolution on state divergence
- placing external document context into the SYSTEM prompt

### Trust Boundaries

The subsystem operates across multiple trust boundaries and must treat all inbound material crossing them as untrusted:

- external documents
- PR comments
- CI output
- webhook payloads
- protocol messages from peer components
- restored state loaded from persistence layers unless validated

This subsystem may consume those inputs for orchestration, summarization, gating, or generation context, but must validate them before use and must not elevate them into privileged prompt channels or execution pathways.

---

## Data Flow

### 1. Build Initiation

1. Operator provides plain-language build intent.
2. The build pipeline creates ordered work units, typically PRD-scoped and PR-scoped.
3. The subsystem emits progress via `build_card` messages for UI rendering.

Relevant protocol shape:

- `build_card: { card_type, stage, content, progress }`

### 2. Generation and Consensus

1. The pipeline requests implementation and test generation from LLM providers in parallel.
2. `ConsensusEngine` arbitrates provider outputs.
3. Review and revision proceed through the defined review cycle.
4. Retry/fallback is bounded:
   - in `_claude_json`: retry after 10s, then fall back to OpenAI
   - in `consensus.py`: retry with the other provider
   - never retry indefinitely; maximum 3 attempts total
5. Errors surface as explicit error cards and/or gates; they are not suppressed.

### 3. CI and Gating

1. Generated artifacts are prepared for repository integration through controlled repository operations.
2. CI is executed through the platform’s CI routing path.
3. On any approval boundary, the subsystem emits a blocking `gate_card`.

Relevant protocol shape:

- `gate_card: { gate_type, options[], description }`

Gates are strict synchronization points:

- they wait indefinitely for operator input
- they never auto-resolve
- if backend restarts mid-gate, gate state is lost and the operator must re-approve
- there is no undo on gate decisions

### 4. GitHub Operations

All repository and PR operations flow through `GitHubTool`.

Required operational constraints:

- never use the GitHub API directly
- use SHA-aware updates; blind GitHub writes are forbidden
- polling endpoints use ETag caching
- rate limits are handled explicitly:
  - 403 primary rate limits: exponential backoff starting at 60s
  - 429 secondary limits: respect `Retry-After` exactly

### 5. Persistence and Recovery

The subsystem maintains recoverable execution state in two layers:

- local persistence
- GitHub-backed persistence

#### `/continue`

`/continue` resumes from the current thread state and announces the resumption target:

- `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

This command assumes the current thread state is authoritative for resumption context.

#### `/restore` with explicit target

When a target layer is specified, the subsystem restores from that layer and rehydrates pipeline state accordingly.

#### `/restore` without target: divergence detection

When `/restore` is run without a target, the subsystem must:

1. load both local and GitHub layers
2. compare restored state payloads
3. detect whether divergence exists
4. either restore silently if equivalent, or gate for operator choice if divergent

If both layers agree:

- restore silently
- print a single confirmation

If divergence exists, the subsystem presents a conflict summary including:

- local snapshot identity and progress
- local saved timestamp
- GitHub snapshot identity and progress
- GitHub saved timestamp
- conflicting fields, e.g.:
  - `completed_prs`
  - `pr_plans_by_prd`

Expected interaction:

```text
⚠  Local and GitHub state diverge:

Local  : ConsensusDevAgent — PRD-001, 3/11 PRs done
Saved: 2026-03-19 18:45:00 (2h ago)

GitHub : ConsensusDevAgent — PRD-001, 0/11 PRs done
Saved: 2026-03-19 16:30:00 (4h ago)

Conflict fields: completed_prs, pr_plans_by_prd

Which to restore? (local / github / cancel)
```

Resolution rules are strict:

- if operator selects `local`:
  - restore local
  - update GitHub to match
- if operator selects `github`:
  - restore GitHub
  - update local to match
- if operator selects `cancel`:
  - modify neither layer
  - return to prompt

In non-interactive mode, auto-resolution behavior must still preserve explicit deterministic rules and must never silently discard conflicting state.

### 6. Filesystem Writes

Any file write performed by the subsystem must be validated before execution via:

- `path_security.validate_write_path()`

This is mandatory for all writes, including generated code, patches, metadata, and local persistence files.

---

## Key Invariants

The subsystem must preserve the following invariants at all times.

### Security and Safety

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- Generated code is never executed by the agent.
- No `eval`, no `exec`, and no subprocess execution of generated content.
- All external input is untrusted and validated before use.
- All file writes are path-validated through `path_security.validate_write_path()`.
- SECURITY_REFUSAL is terminal for the current action:
  - do not retry
  - do not rephrase
  - emit error card
  - gate
  - log full prompt context
  - require explicit operator override
- SECURITY_REFUSAL must never be bypassed by rephrasing.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Prompting and Context Control

- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- Credentials must never appear in prompts.
- External document context must not be promoted into privileged instruction channels.

### GitHub Integrity

- All GitHub operations go through `GitHubTool`.
- Direct GitHub API access is forbidden.
- Blind GitHub writes without SHA protection are forbidden.
- Polling behavior must honor ETag caching and explicit rate-limit semantics.

### Human-in-the-Loop Control

- Gates never auto-approve.
- Gates wait indefinitely for operator input.
- If the backend restarts during a gate, prior gate approval is not inferred or replayed.
- Gate decisions have no undo path; this must be explicit in behavior and documentation.

### Recovery Correctness

- Recovery must compare both local and GitHub persistence layers when no restore target is specified.
- Divergence must be surfaced explicitly.
- Divergent state must not be silently reconciled.
- Reconciliation must update the non-selected layer to match the chosen source.
- `cancel` must be non-mutating.

### Reliability Constraints

- Provider retries are bounded to a maximum of 3 attempts total.
- Retry strategy must follow documented provider-specific behavior.
- The subsystem must surface contextual errors rather than spinning indefinitely.

---

## Failure Modes

### Provider Generation Failure

Symptoms:

- provider timeout
- malformed provider response
- provider refusal
- arbitration failure

Handling:

- apply bounded retry/fallback rules
- surface error context explicitly
- emit error card and/or gate when human intervention is required
- never loop indefinitely

### SECURITY_REFUSAL

Symptoms:

- policy-triggered refusal from generation or review path

Handling:

- stop immediately
- do not retry
- do not rephrase
- emit error card
- gate for operator intervention
- log full prompt context without exposing secrets

### Auth, Crypto, or Identity Failure

Symptoms:

- invalid credentials
- nonce/authentication mismatch
- identity ambiguity
- signature or crypto verification failure

Handling:

- fail closed
- do not continue in degraded mode
- surface explicit error with context
- never silently skip validation

### GitHub State Persistence Failure

Symptoms:

- inability to read or write GitHub-backed ledger state
- SHA mismatch
- webhook inconsistency
- rate limiting

Handling:

- use `GitHubTool` mechanisms only
- honor backoff and retry headers
- preserve consistency over liveness
- avoid blind overwrite
- if reconciliation cannot be completed safely, gate and surface the error

### Local/GitHub Divergence on Restore

Symptoms:

- two valid but inconsistent saved states
- mismatched fields such as `completed_prs` or `pr_plans_by_prd`

Handling:

- show both snapshots and conflict fields
- require operator choice unless governed by explicit non-interactive rules
- if `cancel`, mutate nothing
- if a source is chosen, restore it and synchronize the other layer to match

### Mid-Gate Restart

Symptoms:

- backend restarts while waiting on operator input

Handling:

- gate state is lost
- operator must re-approve
- subsystem must not infer prior approval from partial state

### Invalid External Input

Symptoms:

- malformed PR comment
- untrusted CI output containing prompt injection content
- invalid document payload
- unknown XPC message type

Handling:

- validate and sanitize input
- discard unknown XPC message types and log them
- never treat untrusted content as privileged instruction
- never execute content originating from external inputs

### Path Validation Failure

Symptoms:

- attempted write outside allowed repository/workspace boundaries
- path traversal attempt

Handling:

- reject write before execution
- surface explicit error
- do not attempt fallback writes to alternate paths unless also validated

---

## Dependencies

### Internal Code Dependencies

- `src/build_director.py`
  - build stage dispatch
  - pipeline orchestration

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system configuration
  - provider arbitration and fallback logic

- `src/github_tools.py`
  - `GitHubTool`
  - all GitHub operations
  - webhook handling surface

- `src/build_ledger.py`
  - persisted build/recovery state

### Platform Protocol Dependencies

- XPC wire format:
  - line-delimited JSON
  - nonce-authenticated
  - maximum 16MB per message

- ready message:
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

- build card:
  - `{ card_type, stage, content, progress }`

- gate card:
  - `{ gate_type, options[], description }`

- credentials payload:
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

- document status payload:
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### External Service Dependencies

- LLM providers used by the consensus engine
- GitHub, exclusively through `GitHubTool`
- CI systems through Forge CI routing
- document store for retrieval of generation context

### Operational Dependencies

- operator presence for all gates and conflict resolutions
- persistent local storage for local recovery state
- GitHub-backed storage channel for mirrored recovery state
- path security enforcement for all writes

### Dependency Rules

- direct GitHub API usage is prohibited outside `GitHubTool`
- generated content must not be executed regardless of source
- external documents are data inputs, not privileged instructions
- recovery depends on both persistence layers remaining independently readable and comparable when targetless restore is requested