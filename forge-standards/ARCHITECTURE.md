# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem responsible for turning a plain-language build intent into a gated, reviewable sequence of GitHub pull requests.

At a high level, it:

1. Accepts operator-provided build intent and supporting context.
2. Decomposes the requested work into an ordered PR plan.
3. Generates implementation and tests for each PR using two LLM providers in parallel.
4. Uses Claude as the arbitration layer in consensus generation flows.
5. Runs a structured 3-pass review cycle over generated changes.
6. Executes CI for proposed changes.
7. Presents progress and gate state to the native macOS frontend over XPC.
8. Blocks at explicit human gates for approval before merge or other sensitive transitions.
9. Persists operational state in the build ledger and interacts with GitHub only through the GitHub tool layer.

This subsystem is autonomous in orchestration, but not autonomous in authorization: operator approval is required at defined gates, and gates never auto-resolve.

Primary implementation surfaces called out by the repository context:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts and provider arbitration logic
- `src/build_director.py`
  - `BuildPipeline` orchestration and stage dispatch
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - `BuildLedger`

## Component Boundaries

### Inside this subsystem

The ConsensusDevAgent subsystem includes:

- Build orchestration for the end-to-end coding workflow
- Consensus generation across LLM providers
- Review-cycle coordination
- CI-trigger and CI-result handling as part of the build pipeline
- GitHub PR creation/update/merge orchestration through `GitHubTool`
- Gate emission and operator-blocking behavior
- Build/event persistence in `BuildLedger`
- XPC messaging needed to stream build status and present gates
- Document/context ingestion for generation, subject to validation and prompt-placement rules

### Outside this subsystem

The subsystem does **not** own:

- The macOS UI rendering layer itself
  - It emits `build_card` and `gate_card` messages; UI presentation is external.
- Raw provider infrastructure
  - It consumes LLM APIs but does not define provider platforms.
- Direct GitHub API access outside `GitHubTool`
  - All GitHub operations must transit the tool abstraction.
- Execution of generated code
  - Generated code is never executed by the agent.
- Automatic approval or policy override
  - Human approval is external and mandatory at gates.
- Trust in external artifacts
  - PR comments, CI output, documents, and webhook payloads are inputs to validate, not trusted internal state.

### Hard boundary rules

- All GitHub operations go through `GitHubTool`. Never call the GitHub API directly.
- All file writes must be validated with `path_security.validate_write_path()` before execution.
- External document context must be placed in the **USER** prompt, never the **SYSTEM** prompt.
- SECURITY_REFUSAL is terminal for the current action path unless an operator explicitly overrides.
- Unknown XPC message types are discarded and logged; they are not raised as exceptions.

## Data Flow

### 1. Session/bootstrap

The subsystem initializes an XPC session using the Forge wire protocol:

- Line-delimited JSON
- Nonce-authenticated
- Maximum 16 MB per message

It emits a `ready` message with:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Credentials are received via the `credentials` message:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Auth, crypto, or identity errors fail closed.

### 2. Intent intake and context acquisition

Input sources include:

- Operator build intent
- Repository documents
- Product/technical context documents
- PR comments
- CI output
- Webhook events

All such inputs are treated as untrusted and validated before use.

Document ingestion status is surfaced via `doc_status` messages:

- `doc_id`
- `doc_name`
- `status`
- `chunk_count`
- `embedded_count`

When document content is used for generation, it is injected into the USER prompt only.

### 3. Planning and PR decomposition

`BuildPipeline` in `src/build_director.py` converts intent into staged work:

- ordered PR sequence
- stage dispatch
- gate points
- CI transitions
- merge eligibility transitions

Operational progress is streamed via `build_card`:

- `card_type`
- `stage`
- `content`
- `progress`

These cards are consumed by `BuildStreamView` on the frontend side.

### 4. Consensus generation

`ConsensusEngine` in `src/consensus.py` performs generation with multiple providers in parallel.

Expected behavior:

- Two LLM providers are used in parallel for implementation/test generation.
- Claude arbitrates in consensus flows.
- Provider failures may trigger bounded retry/fallback behavior.
- Retries are capped at 3 attempts total; never retry indefinitely.

Provider-specific reliability rules from repository guidance:

- In `_claude_json`: retry after 10 seconds, then fall back to OpenAI.
- In `consensus.py`: retry with the other provider.
- For GitHub/API rate behavior:
  - `403` primary rate limit: exponential backoff starting at 60 seconds
  - `429` secondary rate limit: honor `Retry-After` exactly

Generated outputs are treated as artifacts for review and commit preparation, not as executable code.

### 5. Review cycle

The subsystem runs a 3-pass review cycle over generated changes before merge progression.

Review consumes:

- generated diffs
- repository context
- test results
- CI signals
- policy/security constraints

The review cycle is enforcement-oriented, not advisory-only: failures surface as explicit errors/cards/gates rather than being silently downgraded.

### 6. GitHub interaction

All repository operations are mediated by `GitHubTool` in `src/github_tools.py`.

This includes:

- PR creation
- branch and commit operations
- comment handling
- status polling
- merge orchestration
- webhook handling through `WebhookReceiver`

Required GitHub safety properties:

- No blind writes; writes requiring object identity must include SHA semantics.
- Use ETag caching on all polling endpoints.
- Respect rate-limit/backoff behavior exactly.
- Never bypass `GitHubTool` for direct API calls.

### 7. Gates and operator approval

When human approval is required, the subsystem emits a `gate_card` with:

- `gate_type`
- `options[]`
- `description`

Gate behavior is strict:

- Gates block indefinitely until operator response.
- No auto-approve ever.
- Gates never auto-resolve.
- If the backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo on gate decisions.

### 8. Merge and ledger persistence

State transitions and build history are recorded in `BuildLedger`.

The ledger is the subsystem’s durable record for:

- build progress
- stage results
- gate transitions
- PR linkage
- error states
- CI outcomes

Final merge progression occurs only after required reviews, CI success, and explicit operator approval.

## Key Invariants

The following invariants are mandatory for this subsystem:

- **Fail closed on auth, crypto, and identity errors**
  - Never degrade silently.
- **No silent failure paths**
  - Every error must surface with context.
- **Secrets never appear in logs, error messages, or generated code**
  - Includes API keys, tokens, and other credentials.
- **All external input is untrusted**
  - Documents, PR comments, CI output, and webhook data must be validated.
- **Generated code is never executed by the agent**
  - No `eval`, no `exec`, no subprocess execution of generated content.
- **Gates wait indefinitely for operator input**
  - No auto-approve.
- **All file writes are path-validated**
  - Must use `path_security.validate_write_path()` before execution.
- **External document context goes only in the USER prompt**
  - Never in the SYSTEM prompt.
- **SECURITY_REFUSAL is terminal**
  - Do not retry, rephrase, or bypass.
  - Emit error card, gate, and log full prompt context safely.
  - Operator must explicitly override to proceed.
- **Unknown XPC message types are discarded and logged**
  - Never raised as exceptions.

Additional enforced repository rules:

- Never retry indefinitely; maximum 3 attempts total.
- No direct GitHub API access outside `GitHubTool`.
- No blind GitHub writes without SHA/context protection.
- No shell injection patterns.
- No path traversal.
- No credentials in logs or prompts.
- No ignoring SECURITY_REFUSAL.

## Failure Modes

### LLM provider failure

Examples:

- timeout
- malformed structured output
- provider outage
- arbitration disagreement

Handling:

- bounded retry only
- provider fallback according to configured rules
- maximum 3 attempts total
- surface failure via error/build card
- gate when operator decision is required

### SECURITY_REFUSAL from model output

This is a hard-stop condition.

Required behavior:

1. Stop immediately.
2. Do not retry.
3. Do not rephrase.
4. Emit an error card.
5. Gate for operator action.
6. Log full prompt context with secret-safe handling.
7. Require explicit operator override before any continuation.

### Auth/identity/crypto failure

Examples:

- invalid nonce
- credential mismatch
- missing required credential
- signature/authentication failure

Handling:

- fail closed
- do not continue in degraded mode
- emit explicit error with context
- do not silently skip protections

### XPC protocol violations

Examples:

- malformed line-delimited JSON
- message exceeds 16 MB
- unknown message type
- missing required fields

Handling:

- malformed/invalid protocol data is rejected
- unknown message types are discarded and logged
- no exception propagation for unknown message types
- stream remains robust where safe to do so

### GitHub API failure

Examples:

- `403` primary rate limit
- `429` secondary rate limit
- stale SHA / write conflict
- webhook inconsistency
- polling inefficiency

Handling:

- `403`: exponential backoff starting at 60 seconds
- `429`: respect `Retry-After` exactly
- use ETag caching on polling endpoints
- require SHA-aware write semantics
- surface conflicts explicitly; do not perform blind overwrite

### Gate interruption

If the backend restarts while waiting on a gate:

- gate state is lost
- the operator must re-approve
- no implicit restoration as approved
- no undo semantics exist for prior gate decisions

### Filesystem safety failure

Examples:

- invalid target path
- traversal attempt
- write outside allowed workspace

Handling:

- reject write
- require `path_security.validate_write_path()` before any write executes
- surface explicit error; never silently redirect

### CI/review failure

Examples:

- failing tests
- review rejection
- missing required evidence
- ambiguous CI state

Handling:

- stop pipeline progression
- emit contextual failure state
- gate where operator action is required
- do not merge on partial or ambiguous success

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - consensus generation, provider arbitration, retry/fallback behavior
- `src/build_director.py`
  - pipeline orchestration and stage management
- `src/github_tools.py`
  - all GitHub interactions, webhook handling
- `src/build_ledger.py`
  - durable build state and event recording

### External service dependencies

- Anthropic API
- OpenAI API
- GitHub API / webhooks
- CI systems integrated through repository/GitHub workflows

### Protocol/runtime dependencies

- Forge XPC transport
  - line-delimited JSON
  - nonce-authenticated messages
  - 16 MB max message size
- macOS native host/UI
  - consumes `ready`, `build_card`, `gate_card`, `doc_status`, and credential messages

### Security-critical dependencies

- `path_security.validate_write_path()`
- credential handling path for API keys and GitHub token
- prompt-construction logic enforcing USER-vs-SYSTEM placement
- logging/redaction mechanisms preventing secret disclosure

### Dependency constraints

- GitHub operations must depend on `GitHubTool`, not direct API clients in arbitrary call sites.
- Generated artifacts must not be passed to execution primitives.
- Untrusted external content must be validated before entering planning, generation, review, or GitHub write paths.
- Operator approval is a runtime dependency for all gated transitions; absence of approval blocks indefinitely.