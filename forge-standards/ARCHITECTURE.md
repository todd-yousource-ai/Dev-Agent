# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem responsible for turning a plain-language build intent into a gated, reviewable sequence of GitHub pull requests.

At a high level, it:

1. Accepts operator-supplied build intent and supporting context.
2. Decomposes the intent into an ordered PR plan.
3. Generates implementation and tests for each PR using two LLM providers in parallel.
4. Uses Claude as the arbitration layer when comparing or selecting generated outputs.
5. Runs a 3-pass review cycle over generated changes.
6. Executes CI for proposed changes.
7. Presents progress and blocking decisions to the macOS client over XPC.
8. Stops at explicit human gates for approval before merge or other sensitive transitions.

The subsystem is orchestration-heavy. It does not just call models; it enforces platform safety, review discipline, operator gating, GitHub write correctness, and document/context handling rules.

Primary implementation files:

- `src/build_director.py` — pipeline orchestration and stage dispatch
- `src/consensus.py` — consensus engine and model prompting
- `src/github_tools.py` — all GitHub operations and webhook handling
- `src/build_ledger.py` — persistent build state and progress tracking

## Component Boundaries

### Inside this subsystem

#### Build pipeline orchestration
`BuildPipeline` in `src/build_director.py` coordinates end-to-end execution:

- stage progression
- PR sequencing
- generation/review/CI phases
- gate emission and gate blocking
- operator-visible progress updates

#### Consensus generation and arbitration
`ConsensusEngine` in `src/consensus.py` is responsible for:

- constructing generation requests
- sending work to two LLM providers
- applying retry/fallback policy
- arbitrating outputs using Claude
- maintaining strict prompt-boundary rules

Key prompt assets include:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM`

#### GitHub integration
`GitHubTool` in `src/github_tools.py` is the only permitted GitHub mutation and query surface. It encapsulates:

- repo reads
- branch/commit/PR operations
- status polling
- webhook-related behaviors
- write safety requirements such as SHA-based updates

`WebhookReceiver` is part of this same integration boundary.

#### Build state tracking
`BuildLedger` in `src/build_ledger.py` records:

- build progress
- stage transitions
- gate state while process is live
- context needed to surface errors and status

#### XPC-facing build state output
The subsystem emits protocol-compliant messages for the native macOS client, including:

- `ready`
- `build_card`
- `gate_card`
- `doc_status`
- credential-bearing setup messages

It must conform to the Forge XPC wire contract:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

### Outside this subsystem

#### UI rendering
The native macOS client and views such as `BuildStreamView` are consumers of emitted cards and statuses. They are not owned by this subsystem.

#### Human decision-making
The operator approves, rejects, or overrides gates. This subsystem never auto-approves and never simulates operator decisions.

#### Generated code execution
This subsystem may generate code and tests, but it must never execute generated content directly via `eval`, `exec`, or subprocess invocation of generated artifacts.

#### Direct GitHub API usage
No component outside `GitHubTool` should perform GitHub API operations for this subsystem’s workflow, and this subsystem itself must not bypass `GitHubTool`.

#### Trust of external content
External documents, PR comments, CI logs, webhook payloads, and similar inputs are treated as untrusted inputs to validate and constrain, not as authoritative instructions.

## Data Flow

### 1. Initialization and capability advertisement
On startup, the subsystem emits a `ready` message:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

This establishes protocol compatibility and operational readiness.

### 2. Credential intake
Credentials arrive via a `credentials` message containing fields such as:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Credential handling is fail-closed:

- missing, malformed, or invalid credentials halt relevant operations
- secrets are never logged, surfaced in errors, or injected into generated code

### 3. Build intent ingestion
Operator intent and document-derived context are ingested as untrusted input.

Critical prompt-routing rule:

- context from external documents goes into the **USER** prompt only
- never into the **SYSTEM** prompt

This boundary prevents external content from altering system-level safety and behavior instructions.

### 4. Planning and PR decomposition
The pipeline converts the build intent into an ordered set of PR-sized work units. Ordering matters: downstream PRs depend on earlier PR outputs and review outcomes.

Progress is streamed via `build_card` messages:

- `card_type`
- `stage`
- `content`
- `progress`

### 5. Parallel generation
For each PR unit, the consensus engine requests candidate implementations from two LLM providers in parallel.

Generation includes code and tests, but generated content is handled as inert text/artifacts. It is never executed directly by the agent.

### 6. Arbitration
Claude serves as the arbiter for competing or complementary candidate outputs. Arbitration selects or synthesizes the best acceptable result subject to system policies and safety constraints.

### 7. Review cycle
A 3-pass review cycle is applied to generated changes. Review outputs may:

- accept
- request revision
- escalate to operator gate
- stop on safety refusal or policy violation

### 8. GitHub materialization
Repository reads/writes occur only through `GitHubTool`.

Key GitHub constraints:

- never use the GitHub API directly outside `GitHubTool`
- no blind writes; writes requiring content replacement must include SHA protection
- polling endpoints use ETag caching
- rate-limit handling follows explicit policy

### 9. CI execution and routing
CI results are ingested as untrusted external output and validated before use in workflow decisions. CI influences readiness for gate presentation, not autonomous merge.

### 10. Gate emission and blocking
When approval is required, the subsystem emits a `gate_card`:

- `gate_type`
- `options[]`
- `description`

Gates are blocking:

- they wait indefinitely for operator input
- they never auto-resolve
- there is no auto-approve path

Operational semantics:

- if the backend restarts mid-gate, gate state is lost
- operator must re-approve after restart
- there is no undo on gate decisions

### 11. Merge progression
Only after explicit operator approval and successful preceding checks does the pipeline proceed to merge-related actions.

## Key Invariants

The following invariants are architectural, not optional implementation details.

### Security and trust

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, prompts that do not require them, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` is terminal for the current attempt: do not rephrase, bypass, or continue around it.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Prompt and model safety

- External document context belongs only in the USER prompt.
- External context must never be placed in the SYSTEM prompt.
- Security refusals cannot be bypassed by prompt rewriting.
- If a refusal occurs: stop, emit error/gate state, and log full prompt context with secret redaction constraints.

### Human-in-the-loop enforcement

- Gates wait indefinitely for operator input.
- No gate auto-approval exists.
- Gate decisions are not automatically recoverable across backend restart.
- No undo semantics exist for gate decisions; downstream actions must treat them as final unless a new explicit operator action occurs.

### File and path safety

- All file writes must be validated through `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Write destinations must remain inside approved repository boundaries.

### GitHub correctness

- All GitHub operations go through `GitHubTool`.
- Direct GitHub API use is forbidden.
- Blind writes are forbidden; use SHA-aware update semantics where applicable.
- Polling endpoints must use ETag caching.

### Retry and backoff discipline

- Never retry indefinitely.
- Maximum 3 attempts total for retryable operations.
- In `_claude_json`: retry after 10 seconds, then fall back to OpenAI.
- In `consensus.py`: retry with the other provider when appropriate.
- For HTTP 403 primary rate limit: exponential backoff starting at 60 seconds.
- For HTTP 429 secondary rate limit: respect `Retry-After` exactly.

### Forbidden patterns

The subsystem must reject or avoid these patterns entirely:

- shell injection
- credential in log
- credential in prompt when not strictly required
- direct execution of generated code
- path traversal
- blind GitHub write without SHA
- external context in system prompt
- ignoring `SECURITY_REFUSAL`

## Failure Modes

### Authentication, crypto, or identity failure
Behavior:

- fail closed immediately
- halt affected stage
- emit contextual error state
- do not continue in degraded mode

Reason:
These failures undermine trust boundaries and cannot be safely bypassed.

### LLM provider failure
Examples:

- timeout
- malformed response
- transient API error
- provider-specific refusal
- arbitration failure

Behavior:

- apply bounded retry policy
- fall back across providers where specified
- stop after max 3 attempts
- surface explicit failure if consensus cannot be achieved safely

### `SECURITY_REFUSAL`
Behavior:

- stop immediately
- do not retry by rephrasing
- do not attempt workaround prompts
- emit error card
- gate for operator decision
- log full prompt context subject to secret-redaction rules

Operator override must be explicit.

### Rate limiting
#### 403 primary rate limit
Behavior:

- exponential backoff starting at 60s

#### 429 secondary rate limit
Behavior:

- honor `Retry-After` exactly

In all cases:

- do not spin
- do not retry indefinitely
- preserve observability of the blocked state

### Invalid or untrusted external input
Examples:

- malformed documents
- hostile PR comments
- unexpected CI output
- invalid webhook payloads
- oversized or invalid XPC messages

Behavior:

- validate before use
- reject or sanitize invalid content
- surface explicit error context
- never treat unvalidated input as instructions

### Unknown XPC message type
Behavior:

- discard
- log occurrence
- do not raise exception

This preserves protocol robustness without crashing the agent on forward-incompatible or malformed traffic.

### File write path violation
Behavior:

- reject write before execution
- surface error
- do not attempt alternate unvalidated path

### GitHub write conflict or missing SHA
Behavior:

- reject blind write
- require SHA-correct write path through `GitHubTool`
- surface actionable error

### Backend restart during gate
Behavior:

- gate state is lost
- operator must re-approve
- no implicit restoration or auto-resolution occurs

### CI failure
Behavior:

- surface CI results as untrusted but validated evidence
- block progression to merge
- require subsequent operator-approved action if workflow continues

## Dependencies

### Internal Forge dependencies

- `src/build_director.py` — orchestration entrypoint and stage controller
- `src/consensus.py` — provider invocation, prompting, arbitration, retry/fallback logic
- `src/github_tools.py` — exclusive GitHub integration surface
- `src/build_ledger.py` — build state and progress tracking
- `path_security.validate_write_path()` — mandatory guard for all file writes

### External service dependencies

- Anthropic API — one generation/arbitration provider path
- OpenAI API — second generation/fallback provider path
- GitHub API — accessed only through `GitHubTool`
- CI systems — consumed as external untrusted signal sources

### Protocol/runtime dependencies

- Forge XPC transport using line-delimited JSON
- nonce authentication on XPC messages
- 16 MB maximum message size
- native macOS client consuming `ready`, `build_card`, `gate_card`, and related protocol messages

### Operational assumptions

- Human operator is available to resolve gates
- Repository writes occur only within validated paths
- Model outputs are treated as data, not executable instructions
- Error reporting infrastructure must preserve context without exposing secrets