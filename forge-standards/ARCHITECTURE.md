# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem responsible for turning a plain-language build intent into a controlled, reviewable sequence of implementation pull requests. It is a native macOS AI coding agent that:

- decomposes a requested build into an ordered PR plan,
- generates code and tests for each PR using multiple LLM providers in parallel,
- arbitrates generation outcomes via the consensus engine,
- runs a 3-pass review cycle,
- executes CI,
- presents progress and gate states over XPC to the UI,
- requires explicit operator approval before any merge or gated progression.

This subsystem is orchestration-first, not execution-first. Its role is to coordinate planning, generation, review, GitHub operations, CI routing, and human gates while preserving Forge security and reliability invariants.

The core implementation surfaces are:

- `src/build_director.py` — pipeline orchestration and stage dispatch
- `src/consensus.py` — consensus generation engine and provider arbitration
- `src/github_tools.py` — all GitHub reads/writes and webhook handling
- `src/build_ledger.py` — persistent build state and audit trail

ConsensusDevAgent does **not** execute generated code as an agent action. It produces artifacts, routes them into repository and CI workflows, and waits for explicit human approval at all gates.

---

## Component Boundaries

### Inside this subsystem

#### Build orchestration
Implemented primarily in `src/build_director.py`.

Responsibilities:
- interpret build intent as a staged pipeline,
- dispatch generation, review, CI, and gate stages,
- emit progress updates as protocol `build_card` messages,
- block on protocol `gate_card` messages until operator response,
- sequence PR creation and promotion in the intended order.

#### Consensus generation
Implemented in `src/consensus.py`.

Responsibilities:
- construct generation requests for supported LLM providers,
- run providers in parallel where applicable,
- arbitrate outputs with Claude as the deciding model,
- apply retry/fallback policy across providers,
- enforce generation prompt separation rules,
- stop on `SECURITY_REFUSAL` rather than attempting prompt reformulation.

#### GitHub integration
Implemented in `src/github_tools.py`.

Responsibilities:
- provide the only allowed interface for GitHub API access,
- perform repository reads/writes with required SHA-based safety,
- manage PR lifecycle operations,
- receive and process webhooks,
- use ETag caching on polling endpoints,
- implement rate-limit and auth handling policy.

#### Build ledger
Implemented in `src/build_ledger.py`.

Responsibilities:
- record build state transitions,
- preserve auditability of staged actions and failures,
- support recovery-aware visibility into current build progress.

### Outside this subsystem

#### UI rendering and operator interaction
The subsystem emits XPC protocol messages such as:
- `ready`
- `build_card`
- `gate_card`
- `doc_status`

Rendering in `BuildStreamView` and collection of operator decisions are outside this subsystem. ConsensusDevAgent depends on them but does not own them.

#### Credential origination
Credentials arrive through the protocol as:
- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

ConsensusDevAgent consumes these credentials but does not provision or mint them.

#### Code execution environment
Generated code is not executed by the agent itself. CI systems may build/test repository content after commit/PR creation, but that execution boundary is external to this subsystem.

#### Document ingestion and embedding infrastructure
The subsystem consumes document status/context and may use document store content for generation context, but embedding pipelines and document-store infrastructure are separate platform components.

---

## Data Flow

### 1. Session initialization
- The subsystem establishes readiness over XPC using line-delimited JSON messages.
- Messages are nonce-authenticated and capped at 16 MB per message.
- A `ready` message advertises:
  - `agent_version`
  - `min_swift_version`
  - `capabilities[]`
  - `doc_store_status`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Input acquisition
Inputs include:
- plain-language build intent,
- repository state,
- external documents,
- PR comments,
- CI output,
- operator responses,
- credentials.

All such external inputs are treated as untrusted and must be validated before use.

### 3. Planning and decomposition
- The build director converts the intent into an ordered implementation plan.
- The plan is expressed as a sequence of PR-sized units.
- Progress is streamed via `build_card`.

### 4. Context assembly
- Repository and document context are collected for generation.
- Context from external documents is placed only in the **USER** prompt, never the **SYSTEM** prompt.
- Secrets are excluded from prompts, logs, errors, and generated code.

### 5. Multi-provider generation
- `ConsensusEngine` in `src/consensus.py` submits generation work to multiple providers.
- Claude arbitrates between provider outputs.
- Retry behavior is bounded:
  - never retry indefinitely,
  - maximum 3 attempts total,
  - provider fallback is allowed,
  - `_claude_json` retries after 10 seconds, then falls back to OpenAI,
  - in `consensus.py`, failures trigger retry with the other provider.

If a generation attempt results in `SECURITY_REFUSAL`, the subsystem:
- stops immediately,
- does not retry,
- does not rephrase,
- emits an error card,
- gates for operator action,
- logs full prompt context with secret-safe handling.

### 6. File production
- Generated repository modifications are prepared for write.
- Every write path is validated via `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Generated code is never executed by the agent.

### 7. GitHub operations
- All GitHub interactions go through `GitHubTool`.
- Direct GitHub API usage outside `GitHubTool` is forbidden.
- Blind writes are forbidden; SHA-aware mutation semantics are required.
- Polling endpoints use ETag caching.
- Rate limit handling:
  - HTTP 403 primary rate limit: exponential backoff starting at 60 seconds,
  - HTTP 429 secondary rate limit: respect `Retry-After` exactly.

### 8. Review and CI
- The subsystem runs a 3-pass review cycle on generated changes.
- CI is executed through external repository/CI systems.
- CI output is treated as untrusted input on re-entry to the subsystem.
- Build progress continues to stream via `build_card`.

### 9. Human gating
At required decision points, the subsystem emits a `gate_card`:
- `{ gate_type, options[], description }`

Behavior:
- gates block indefinitely until operator response,
- no auto-approve ever,
- gates never auto-resolve,
- if the backend restarts mid-gate, gate state is lost and the operator must re-approve,
- there is no undo on gate decisions.

### 10. Merge progression
After explicit operator approval:
- PRs may be advanced or merged through `GitHubTool`,
- subsequent planned PRs proceed in order,
- all state transitions are recorded in the build ledger.

---

## Key Invariants

### Security invariants
- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, no subprocess execution of generated content.
- All file writes must pass `path_security.validate_write_path()` before execution.
- Context from external documents belongs only in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the attempted action: do not bypass by rephrasing.
- Unknown XPC message types are discarded and logged.

### Human-control invariants
- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.
- Operator override must be explicit.
- Gate decisions are not undoable within the subsystem.
- Restart during a gate requires re-approval.

### GitHub and repository safety invariants
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Blind GitHub writes are forbidden; writes require SHA-aware safety checks.
- Polling should use ETag caching where supported.
- Repository mutations must respect path validation boundaries.

### Reliability invariants
- Retries are bounded to a maximum of 3 attempts total.
- Rate-limit behavior must follow protocol:
  - 403 primary: exponential backoff starting at 60s,
  - 429 secondary: honor `Retry-After` exactly.
- Errors must be emitted as visible cards and logged with context, subject to secret redaction rules.

### Forbidden patterns
- shell injection
- credential in log
- credential in prompt
- direct execution of generated code
- path traversal
- blind GitHub write without SHA
- context in system prompt
- ignoring `SECURITY_REFUSAL`

---

## Failure Modes

### LLM provider failure
Examples:
- timeout,
- malformed structured response,
- provider auth failure,
- provider refusal,
- transport error.

Handling:
- retry/fallback according to bounded provider policy,
- maximum 3 attempts total,
- if `SECURITY_REFUSAL`, stop immediately,
- surface failure through error card and logs,
- gate for operator action when required.

### Authentication, crypto, or identity failure
Handling:
- fail closed,
- do not continue in degraded mode,
- emit explicit error with context,
- do not silently substitute missing identity/credential state.

### Invalid or malicious external input
Examples:
- poisoned documents,
- malformed PR comments,
- adversarial CI output,
- unknown XPC messages.

Handling:
- validate before use,
- reject or discard invalid input,
- log with context,
- never escalate unknown XPC message types to exceptions.

### Unsafe file write attempt
Examples:
- path traversal,
- write outside allowed repository scope.

Handling:
- block write before execution via path validation,
- surface explicit failure,
- do not attempt alternate unsafe write paths.

### GitHub mutation conflict or unsafe write
Examples:
- missing SHA,
- stale SHA,
- write conflict,
- webhook inconsistency.

Handling:
- use `GitHubTool` safety semantics,
- do not perform blind writes,
- surface conflict and require normal pipeline handling or operator intervention.

### Rate limiting
Handling:
- 403 primary rate limit: exponential backoff starting at 60 seconds,
- 429 secondary limit: respect `Retry-After` exactly,
- no infinite retry loops.

### Gate interruption
If the backend restarts while waiting on a gate:
- gate state is lost,
- the operator must re-approve,
- the subsystem does not infer prior approval.

### CI failure
Handling:
- treat CI output as untrusted input,
- surface failure context to the operator,
- block progression until explicit operator decision where gating applies.

---

## Dependencies

### Internal Forge dependencies
- `src/build_director.py` for pipeline orchestration
- `src/consensus.py` for provider orchestration and arbitration
- `src/github_tools.py` for all GitHub interactions
- `src/build_ledger.py` for build state tracking
- `path_security.validate_write_path()` for mandatory write-path enforcement

### External service dependencies
- Anthropic provider APIs
- OpenAI provider APIs
- GitHub API via `GitHubTool`
- external CI systems associated with the repository

### Protocol dependencies
- XPC line-delimited JSON transport
- nonce-authenticated messages
- 16 MB maximum message size
- protocol message types:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### Data dependencies
- repository contents and metadata
- external documents from the document store
- PR comments and review state
- CI output
- operator approvals and gate responses

### Dependency constraints
- external document context must not be promoted into system prompts
- untrusted inputs must be validated before use
- secrets from credentials must never be logged, echoed, or embedded in generated artifacts
- generated outputs must not be executed by the subsystem itself