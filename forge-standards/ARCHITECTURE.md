# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding agent. It converts a plain-language build intent into a controlled, operator-gated implementation pipeline that:

1. decomposes work into an ordered sequence of PRs,
2. generates implementation and test changes using multiple LLM providers in parallel,
3. arbitrates generation outcomes through the consensus engine,
4. runs a structured review cycle,
5. executes CI,
6. blocks on explicit operator approval before merge,
7. persists and restores build progress state across restarts.

This subsystem is responsible for coordinating the end-to-end build loop, not for silently completing it. Human approval is a hard requirement at every gate.

It also owns recovery semantics for in-progress builds:

- `/continue` resumes a build from the current thread state and emits:
  - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`
- `/restore` loads persisted state layers and performs divergence detection when no explicit target is provided.
- If local and GitHub recovery layers differ, the subsystem must surface the conflict, identify conflicting fields, and require an operator choice of:
  - `local`
  - `github`
  - `cancel`

On recovery conflict resolution:

- `local`: restore local state and update GitHub to match
- `github`: restore GitHub state and update local to match
- `cancel`: modify neither layer and return control to the operator

In non-interactive mode, divergence handling follows explicit auto-resolution rules defined by recovery-state management; it must not silently discard state differences.

## Component Boundaries

### Inside this subsystem

The ConsensusDevAgent subsystem includes the orchestration and state-management logic implemented primarily in:

- `src/build_director.py`
  - Build pipeline orchestration
  - Stage dispatch
  - Gate sequencing
  - Coordination of generation, review, CI, and merge workflow
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts/constants
  - provider arbitration and fallback logic
- `src/build_ledger.py`
  - persistent build state / progress tracking
  - recovery and resume state
- portions of `src/github_tools.py`
  - only where GitHub operations are used as part of pipeline state synchronization, PR lifecycle, CI polling, and restore-layer reconciliation

This subsystem owns:

- PRD/PR planning progression state
- completed PR tracking
- per-PRD PR plans (`pr_plans_by_prd`)
- current stage and gate status
- recovery-layer comparison and reconciliation
- operator-facing progress and gate cards for build execution

### Outside this subsystem

This subsystem does **not** own:

- direct UI rendering
  - it emits protocol messages such as `build_card` and `gate_card`, but does not implement `BuildStreamView`
- document embedding/indexing internals
  - it consumes document-store status/context but is not the embedding pipeline
- transport/runtime IPC
  - XPC framing, nonce authentication, and message transport are platform concerns
- raw GitHub API integration outside approved abstractions
  - all GitHub operations must go through `GitHubTool`; direct GitHub API access is forbidden
- credential issuance or storage
  - it consumes credential payloads, but does not define auth infrastructure
- execution of arbitrary generated code
  - generated code is written, reviewed, and validated, but never executed by the agent as arbitrary code content

### Explicit non-goals / prohibited scope

ConsensusDevAgent must not:

- auto-approve gates
- bypass operator review after restart
- execute generated content via `eval`, `exec`, or subprocess
- write files without path validation via `path_security.validate_write_path()`
- place external document context into the system prompt
- bypass `SECURITY_REFUSAL` handling by rephrasing or retry loops
- perform blind GitHub writes without SHA protection where required

## Data Flow

### 1. Session start / resume

Inputs:

- operator build intent or recovery command
- credentials:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- repository and document context
- persisted build ledger state
- GitHub PR/build state as needed

On `/continue`:

1. load current thread/build state,
2. reconstruct active PRD and PR position,
3. emit resume confirmation:
   - `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`,
4. continue from the last safe orchestration point.

### 2. Recovery / restore

When `/restore` runs without a target:

1. load local recovery layer,
2. load GitHub recovery layer,
3. compare the two representations,
4. if equal:
   - restore silently,
   - emit a single confirmation,
5. if divergent:
   - display both summaries,
   - display timestamps/relative age,
   - enumerate conflicting fields,
   - gate on operator selection.

Example conflict fields include:

- `completed_prs`
- `pr_plans_by_prd`

Resolution effects:

- selecting `local` causes local state to become authoritative, then synchronizes GitHub
- selecting `github` causes GitHub state to become authoritative, then synchronizes local
- selecting `cancel` aborts restore with no modifications to either layer

### 3. Planning and generation

1. ingest build intent and repository/document context,
2. decompose work into an ordered PR sequence,
3. request candidate implementations from two LLM providers in parallel,
4. use Claude as arbiter in the consensus flow,
5. apply retry/fallback policy:
   - provider-level fallback allowed
   - no indefinite retries
   - maximum 3 attempts total
   - `_claude_json`: retry after 10s, then fall back to OpenAI
   - in `consensus.py`: retry with the other provider
   - 403 primary rate limits: exponential backoff starting at 60s
   - 429 secondary limits: respect `Retry-After` exactly

External context handling rule:

- context from external documents must go into the **USER** prompt only
- never into the **SYSTEM** prompt

### 4. Review, CI, and gating

1. generated changes enter a 3-pass review cycle,
2. GitHub operations for PR creation/update/status polling go exclusively through `GitHubTool`,
3. CI status is polled using approved GitHub mechanisms with ETag caching on polling endpoints,
4. operator-facing updates are streamed as:
   - `build_card { card_type, stage, content, progress }`
5. decision points are emitted as:
   - `gate_card { gate_type, options[], description }`

Gate behavior:

- gates block indefinitely until operator input
- no auto-resolution
- if backend restarts mid-gate, gate state is lost
- operator must re-approve after restart
- there is no undo on gate decisions

### 5. Persistence and synchronization

Build progress is written to the build ledger and, where required by recovery design, synchronized to GitHub-backed state. This provides two recovery layers used during restore/divergence detection.

All file writes in this process must be path-validated before execution.

## Key Invariants

The subsystem must enforce the following invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in:
  - logs
  - error messages
  - prompts where prohibited
  - generated code
- All external input is untrusted and must be validated:
  - documents
  - PR comments
  - CI output
  - recovery metadata from external sources
- Generated code is never executed by the agent.

### Prompting and model safety

- External document context goes in the USER prompt only.
- Never place external context in the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the current action:
  - do not bypass by rephrasing
  - do not keep retrying
  - emit error card
  - gate
  - log full prompt context using approved redaction rules
  - require explicit operator override

### Operator control

- Gates never auto-resolve.
- Human approval is required before merge and at other defined decision points.
- If gate state is lost due to restart, approval must be reacquired.
- No undo on gate decisions.

### File and repository integrity

- Every file write must pass `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Direct execution of generated code is forbidden.
- Shell injection patterns are forbidden.
- Blind GitHub writes are forbidden; use SHA-aware operations where applicable.
- All GitHub operations must go through `GitHubTool`.

### Recovery correctness

- Restore without a target must compare both recovery layers.
- Divergence must be surfaced explicitly, including conflict fields.
- Conflict resolution must update the non-authoritative layer to match the selected source.
- `cancel` must leave both layers unchanged.
- No silent preference for local or GitHub state in interactive divergence cases.

### Protocol handling

- XPC messages use line-delimited JSON with nonce authentication and a 16 MB maximum message size.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

## Failure Modes

### LLM provider failures

Possible failures:

- provider timeout
- malformed structured response
- auth failure
- rate limit
- provider refusal / `SECURITY_REFUSAL`

Required behavior:

- retry according to bounded retry policy only
- fall back to alternate provider where defined
- never retry indefinitely
- surface error context to operator
- gate when the workflow cannot safely continue

### Recovery-state divergence

Failure condition:

- local and GitHub state disagree during `/restore` without explicit target

Required behavior:

- do not silently choose one
- present both states, timestamps, and conflicting fields
- require operator choice unless explicit non-interactive resolution policy applies
- if `cancel`, preserve both layers unchanged

### Mid-gate restart

Failure condition:

- backend restarts while a gate is pending

Required behavior:

- treat gate approval as lost
- require re-approval
- do not infer prior operator consent from partial state

### GitHub operation failures

Possible failures:

- API auth/permission errors
- stale SHA / optimistic concurrency failures
- webhook/polling inconsistencies
- rate limiting
- network interruption

Required behavior:

- access GitHub only via `GitHubTool`
- use ETag caching on polling endpoints
- fail closed on auth/identity issues
- do not perform blind writes
- surface actionable error state to operator

### Unsafe input or forbidden action request

Failure condition:

- external content attempts prompt injection
- generated plan implies unsafe file access
- operator or model output would bypass invariants

Required behavior:

- reject unsafe action
- emit explicit error/gate path
- do not silently sanitize into a different semantic action
- preserve auditability of why the action was blocked

### Write-path validation failure

Failure condition:

- target path fails `path_security.validate_write_path()`

Required behavior:

- abort write
- report validation failure with context
- do not attempt alternative unchecked writes

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - primary orchestration entry point for the build pipeline
- `src/consensus.py`
  - consensus generation engine, provider arbitration, retry/fallback behavior
- `src/build_ledger.py`
  - persisted build state and recovery metadata
- `src/github_tools.py`
  - exclusive GitHub integration surface for PRs, status, and related operations

### Platform/runtime dependencies

- XPC protocol transport
  - line-delimited JSON
  - nonce-authenticated messages
  - message types including `ready`, `build_card`, `gate_card`, `credentials`, `doc_status`
- BuildStream/UI consumer
  - consumes streamed `build_card` and `gate_card` payloads
- document store
  - supplies contextual documents and document status
- GitHub
  - repository state, PR state, CI state, and recovery synchronization layer as designed
- LLM providers
  - Anthropic/Claude
  - OpenAI

### Dependency constraints

- direct GitHub API access is prohibited outside `GitHubTool`
- direct execution of generated code is prohibited
- all external content from dependencies is treated as untrusted input
- credentials are required for provider/GitHub operations and must never be logged or leaked