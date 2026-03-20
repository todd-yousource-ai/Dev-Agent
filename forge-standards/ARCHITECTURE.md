# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the build-orchestration subsystem for Forge’s native macOS AI coding agent. It converts a plain-language build intent into an ordered sequence of pull requests, coordinates multi-provider code generation and arbitration, drives review and CI stages, and blocks on explicit operator approval at every gate.

At a subsystem level, it is responsible for:

- Decomposing work into PRD/PR units and tracking ordered execution state
- Resuming execution from persisted thread/build state via `/continue`
- Restoring state from local and GitHub-backed recovery layers
- Detecting divergence between recovery layers and forcing explicit conflict resolution
- Orchestrating generation, review, CI, and merge progression
- Streaming build status and gate requests over the Forge XPC protocol
- Persisting build progress in ledger/state structures

It is not an autonomous merge engine. Human approval remains mandatory for all gated transitions. It is also not a code execution environment: generated code is produced, reviewed, and routed to CI, but never executed directly by the agent.

## Component Boundaries

### Inside this subsystem

Primary implementation surfaces identified in Forge context:

- `src/consensus.py`
  - `ConsensusEngine`
  - provider selection/fallback logic
  - generation system prompt definitions
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - stage dispatch and progression through the core loop
- `src/build_ledger.py`
  - build state persistence and recovery bookkeeping
- Recovery-state handling for `/continue` and `/restore`
- Divergence detection between local and GitHub state layers
- Gate emission and build progress streaming over XPC

### Outside this subsystem

The following are dependencies or adjacent systems, not owned by ConsensusDevAgent:

- LLM providers (Anthropic/OpenAI)
- GitHub platform API access
- CI runners and CI result production
- Operator UI/rendering surfaces such as `BuildStreamView`
- Document storage/embedding infrastructure
- Authentication, credential acquisition, and secret provisioning

### Explicit non-responsibilities

ConsensusDevAgent does **not**:

- Call the GitHub API directly outside `GitHubTool`
- Execute generated code via `eval`, `exec`, or subprocess
- Auto-resolve gates or operator approvals
- Silently recover from auth, crypto, identity, or security-policy failures
- Trust external inputs without validation
- Write files without path validation

## Data Flow

### 1. Build initiation and planning

1. Operator provides build intent.
2. ConsensusDevAgent decomposes the intent into an ordered PRD/PR sequence.
3. Build state is recorded in the ledger and exposed to the UI through streamed build cards.

Relevant protocol surface:

- `build_card: { card_type, stage, content, progress }`

### 2. Generation and arbitration

1. For each PR, the subsystem requests implementation/test generation from two LLM providers in parallel.
2. Claude performs arbitration per platform overview.
3. Retry/fallback behavior is bounded:
   - `_claude_json`: retry after 10s, then fall back to OpenAI
   - `consensus.py`: retry with the other provider
   - max 3 attempts total
4. Outputs move into review and CI stages; generated code is never executed directly by the agent.

### 3. Review, CI, and gating

1. The subsystem runs the defined review cycle and routes work to CI.
2. At every approval boundary, it emits a gate card and blocks indefinitely until operator action.
3. No auto-approval exists.
4. If the backend restarts mid-gate, gate state is lost and the operator must re-approve.

Relevant protocol surface:

- `gate_card: { gate_type, options[], description }`

### 4. State persistence and recovery

ConsensusDevAgent maintains recoverable progress in two layers:

- Local state
- GitHub-backed saved state

#### `/continue`

`/continue` resumes the build from the current thread state.

Expected output:

- `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]`

This command assumes current thread state is authoritative for resumption and re-enters the pipeline at the saved stage boundary.

#### `/restore` without target

When `/restore` is invoked without an explicit target, the subsystem loads both state layers and compares them.

Outcomes:

- **No divergence**: both layers agree; restore silently and print one confirmation
- **Divergence detected**: operator must choose authoritative state

Required divergence presentation:

- local summary
- GitHub summary
- save times
- conflict fields

Example shape:

- `completed_prs`
- `pr_plans_by_prd`

Prompted resolution options:

- `local`
- `github`
- `cancel`

Resolution semantics:

- `local`: restore local state, then update GitHub to match
- `github`: restore GitHub state, then update local to match
- `cancel`: modify neither layer; return to prompt

In non-interactive mode, divergence uses auto-resolution rules defined by the recovery-state management design; it must still preserve fail-closed semantics and must not silently discard conflict information.

### 5. GitHub interaction boundary

All GitHub operations flow through `GitHubTool`. ConsensusDevAgent may request GitHub reads/writes only through this abstraction. Blind writes are forbidden; SHA-aware operations are required.

### 6. XPC communication boundary

ConsensusDevAgent exchanges messages over Forge’s XPC wire format:

- line-delimited JSON
- nonce-authenticated
- max 16MB per message

Unknown XPC message types are discarded and logged, never raised as exceptions.

## Key Invariants

The subsystem must enforce the following invariants from Forge architecture and its own recovery semantics:

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
  - GitHub-derived state
- Context from external documents belongs in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the attempted action: do not bypass by rephrasing; stop, gate, and log.
- Generated code is never executed by the agent.

### File and write safety

- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Direct writes outside validated repository scope are forbidden.

### GitHub correctness

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Blind GitHub writes are forbidden; use SHA-aware write/update patterns.
- Polling endpoints use ETag caching.
- Rate-limit handling is explicit:
  - `403` primary rate limit: exponential backoff starting at 60s
  - `429` secondary rate limit: respect `Retry-After` exactly

### Operator control and gating

- Gates never auto-resolve; they wait indefinitely for operator input.
- There is no undo on gate decisions.
- If backend restarts during a gate, approval state is lost and must be re-issued by the operator.
- Recovery divergence cannot be silently resolved in interactive mode when both layers disagree.

### Retry and fallback discipline

- Retry count is bounded to 3 total attempts.
- Do not retry indefinitely.
- Provider fallback is explicit and controlled.
- Security refusal paths are not retried/rephrased.

### Recovery consistency

- `/continue` resumes from current thread state and must emit a concrete resume banner.
- `/restore` without a target must compare both local and GitHub layers before choosing state.
- Divergent state requires explicit authority selection or cancellation.
- Once one side is selected as authoritative, the other layer is updated to match exactly.

## Failure Modes

### State divergence

**Condition:** Local and GitHub recovery layers disagree on build progress or plan content.

**Handling:**
- Detect and enumerate conflicting fields
- Present both summaries and timestamps
- Gate for operator choice in interactive mode
- Apply selected state as authoritative and synchronize the other layer
- On `cancel`, leave both untouched

**Forbidden behavior:**
- Silent precedence of one layer over the other
- Partial merge of conflicting fields without explicit design support

### Mid-gate restart

**Condition:** Backend restarts after a gate has been emitted but before operator response is durably re-associated.

**Handling:**
- Gate state is considered lost
- Operator must explicitly re-approve

**Implication:**
- No assumption of implicit approval persistence across restart

### Provider failure or degraded generation path

**Condition:** Provider timeout, malformed response, or provider-specific API failure.

**Handling:**
- Retry/fallback according to bounded provider policy
- Surface failure with context if attempts are exhausted
- Emit error card, gate, and log prompt context where policy requires

**Forbidden behavior:**
- Infinite retry loops
- Silent provider substitution beyond configured fallback sequence

### Auth/crypto/identity failure

**Condition:** Credential invalidity, missing identity, nonce/authentication failure on protocol boundary, or related security-critical validation error.

**Handling:**
- Fail closed
- Surface explicit error context
- Do not continue in degraded mode

### Security refusal

**Condition:** Model or policy layer returns `SECURITY_REFUSAL`.

**Handling:**
- Stop
- Do not retry
- Do not rephrase
- Emit error card
- Gate
- Log full prompt context
- Require explicit operator override

### Invalid external input

**Condition:** Malformed documents, hostile PR comments, malformed CI output, oversized or invalid XPC messages, unknown XPC message types.

**Handling:**
- Validate and reject/contain as appropriate
- Unknown XPC message types are discarded and logged
- Do not raise unknown message types as exceptions

### Unsafe write attempt

**Condition:** File write targets an unvalidated or traversed path.

**Handling:**
- Reject before write
- Surface error with context

### GitHub write correctness failure

**Condition:** Attempted direct GitHub API usage, missing SHA on write, or synchronization mismatch during recovery reconciliation.

**Handling:**
- Route through `GitHubTool`
- Reject blind writes
- Fail loudly on synchronization errors rather than assuming success

## Dependencies

### Internal Forge dependencies

- `ConsensusEngine` in `src/consensus.py`
- `BuildPipeline` orchestration in `src/build_director.py`
- `BuildLedger` in `src/build_ledger.py`
- `GitHubTool` in `src/github_tools.py`
- `WebhookReceiver` in `src/github_tools.py`
- `path_security.validate_write_path()`
- Document store/document loading surfaces
- XPC transport and UI card consumers

### External services

- Anthropic provider APIs
- OpenAI provider APIs
- GitHub APIs, accessed only through `GitHubTool`
- CI infrastructure

### Protocol dependencies

- XPC ready message:
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- build stream messages:
  - `build_card: { card_type, stage, content, progress }`
- gate messages:
  - `gate_card: { gate_type, options[], description }`
- credentials envelope:
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- document status messages:
  - `doc_status: { doc_id, doc_name, status, chunk_count, embedded_count }`

### Dependency constraints

- Secrets from credential surfaces must never be logged or copied into prompts
- External document context must be injected only into USER prompts
- GitHub access must remain fully encapsulated by `GitHubTool`
- Generated content must remain data, not executable instructions for the runtime