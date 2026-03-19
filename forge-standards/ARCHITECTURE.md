# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge subsystem responsible for converting a plain-language build intent into a human-gated sequence of implementation pull requests.

At a high level, it:

1. Accepts operator intent and repository context.
2. Decomposes the requested change into an ordered PR plan.
3. Generates code and tests using two LLM providers in parallel.
4. Arbitrates between provider outputs via the consensus engine.
5. Runs a structured review cycle across generated changes.
6. Executes CI and collects results.
7. Presents progress and gate decisions to the operator.
8. Waits indefinitely for explicit human approval before merge or other gated transitions.

This subsystem is orchestration-heavy. It does **not** autonomously finalize changes without operator participation, and it does **not** execute generated code. Its primary responsibilities are safe generation, review orchestration, GitHub-mediated change application, CI coordination, and explicit gate enforcement.

Primary implementation surfaces:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`)
- `src/build_director.py`
  - `BuildPipeline`
  - stage dispatch and workflow orchestration
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - `BuildLedger`

## Component Boundaries

### Inside this subsystem

#### Build orchestration
`BuildPipeline` coordinates the end-to-end lifecycle of a build:

- stage progression
- PR sequencing
- generation dispatch
- review pass execution
- CI invocation and result handling
- gate emission and blocking behavior

#### Multi-provider generation and arbitration
`ConsensusEngine` manages LLM interactions across providers and selects or synthesizes outputs under a consensus/arbitration model. Claude is the arbiter in the platform design. The engine is responsible for retry/fallback behavior within bounded limits.

#### GitHub operations abstraction
All GitHub reads/writes for this subsystem must go through `GitHubTool`.

This includes:

- branch and PR management
- file reads/writes
- commit creation/update flows
- polling and webhook-related interactions
- CI status retrieval where routed through GitHub

Direct GitHub API usage outside `GitHubTool` is out of bounds.

#### Build state tracking
`BuildLedger` stores the durable build record and operational history needed to surface progress, errors, and stage transitions.

#### UI/event protocol emission
The subsystem emits protocol messages such as:

- `ready`
- `build_card`
- `gate_card`
- `doc_status`

These messages inform the macOS client and block for operator response where applicable.

### Outside this subsystem

#### Authentication, credential sourcing, and identity authority
The subsystem consumes credentials and engineer identity but is not the source of truth for auth or identity. It must fail closed on auth, crypto, or identity errors.

#### Document ingestion/embedding pipeline
The subsystem may consume document-store context and document status, but document ingestion, embedding, and storage are separate concerns.

#### UI rendering
`BuildStreamView` and other client-side presentation logic render cards emitted by this subsystem. Rendering is outside this subsystem.

#### Code execution sandbox/runtime
This subsystem never executes generated code and is not responsible for runtime execution of generated artifacts.

#### Human decision-making
Approval, override, and gate resolution authority remain with the operator. The subsystem presents options and blocks; it does not auto-resolve.

## Data Flow

### 1. Initialization and capability announcement
On startup, the subsystem participates in XPC communication using line-delimited JSON with nonce authentication and a maximum message size of 16 MB.

It emits a `ready` message of the form:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Credential and intent intake
The subsystem receives:

- operator build intent
- credentials:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- repository and document context
- optional external inputs such as PR comments, CI output, and documents

All such external inputs are treated as untrusted and validated before use.

### 3. Context assembly
Relevant repository and document context is assembled for generation.

A critical prompt-boundary rule applies:

- context from external documents goes into the **USER** prompt
- never into the **SYSTEM** prompt

This prevents privilege escalation via untrusted context injection.

### 4. Plan and PR decomposition
The build intent is decomposed into an ordered sequence of PRs. Ordering is significant and enforced by the pipeline so that dependent changes are proposed and reviewed in sequence rather than merged as an uncontrolled batch.

### 5. Parallel generation
For each PR-sized unit of work, the subsystem requests candidate implementations from two LLM providers in parallel. The consensus layer arbitrates between them.

Generation includes both implementation and tests.

Retry behavior is bounded:

- in `_claude_json`: retry after 10 seconds, then fall back to OpenAI
- in `consensus.py`: retry with the other provider
- never retry indefinitely
- maximum 3 attempts total

### 6. Review cycle
Generated changes go through a 3-pass review cycle. The subsystem coordinates the passes and records outcomes in the build ledger.

If a model emits `SECURITY_REFUSAL`:

- stop immediately
- do not retry by rephrasing
- do not bypass refusal
- emit error card
- gate
- log full prompt context in the approved secure manner, without leaking secrets
- require explicit operator override

### 7. File mutation and GitHub application
Before any write is performed, all file paths must be validated via:

```python
path_security.validate_write_path()
```

This applies to every file write path before execution.

GitHub mutations must be SHA-aware; blind writes are forbidden.

All repository modifications flow through `GitHubTool`, not direct API calls.

### 8. CI execution and status collection
The subsystem triggers or monitors CI for generated changes and routes CI outcomes back into the build flow.

Polling endpoints must use ETag caching.

Rate-limit handling rules:

- HTTP 403 primary rate limits: exponential backoff starting at 60 seconds
- HTTP 429 secondary limits: respect `Retry-After` header exactly

### 9. Gate emission and operator blocking
At decision points, the subsystem emits a `gate_card`:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

Gates are hard stops:

- they never auto-resolve
- they wait indefinitely for operator input
- there is no auto-approve path

If the backend restarts mid-gate:

- gate state is lost
- operator must re-approve

There is no undo on gate decisions; this must be treated as an explicit product constraint.

### 10. Progress streaming and completion
Progress is streamed via `build_card` messages:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": ... }
```

The ledger records stage outcomes, errors, and transitions for traceability.

## Key Invariants

The subsystem must preserve the following invariants at all times.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Context from external documents is placed only in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is never bypassed by rephrasing.
- Unknown XPC message types are discarded and logged.

### Human-in-the-loop enforcement

- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Gate decisions are not auto-replayed after restart.
- No undo on gate decisions.

### File and repository safety

- All file writes must be path-validated with `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Blind GitHub writes without SHA protection are forbidden.
- All GitHub operations go through `GitHubTool`.

### Execution safety

Forbidden patterns include:

- shell injection
- credential in logs
- credential in prompts
- direct execution of generated code
- path traversal
- blind GitHub write without SHA
- context in system prompt
- ignoring `SECURITY_REFUSAL`

### Reliability constraints

- Retry behavior is bounded to a maximum of 3 attempts total.
- No infinite retry loops.
- Polling uses ETag caching where supported.
- Rate-limit handling follows explicit backoff/header rules.

## Failure Modes

### LLM provider failure
Examples:

- timeout
- invalid JSON / malformed structured output
- transient provider outage
- refusal to answer
- one-provider disagreement

Handling:

- retry/fallback per bounded consensus rules
- switch provider where permitted
- stop after 3 total attempts
- surface error with context
- gate if progress cannot continue safely

### Security refusal
If any generation/review path returns `SECURITY_REFUSAL`:

- stop immediately
- do not rephrase and retry
- emit error card
- gate for operator decision
- log the event with full context under secret-safe logging rules

This is a hard-stop condition.

### Auth, crypto, or identity failure
Examples:

- missing or invalid credentials
- nonce/authentication failure on XPC
- identity mismatch

Handling:

- fail closed
- do not degrade to reduced-security behavior
- surface explicit error
- halt affected operations

### Path validation failure
If `path_security.validate_write_path()` rejects a write target:

- abort the write
- surface the validation error
- do not attempt alternate unvalidated paths

### GitHub API failure or race
Examples:

- stale SHA on write
- rate limiting
- webhook/polling inconsistency
- permission failure

Handling:

- all writes remain mediated through `GitHubTool`
- use SHA-aware operations only
- obey 403/429 backoff policy
- use ETag caching on polling endpoints
- surface errors rather than silently skipping writes

### CI failure
Examples:

- test failure
- workflow infrastructure failure
- missing or incomplete status

Handling:

- record failure in ledger
- emit progress/error cards
- gate before merge or further destructive progression as required by stage policy

### Gate interruption
If the backend restarts while waiting on a gate:

- in-memory gate state is lost
- operator must explicitly re-approve
- no implicit restoration to approved state occurs

### Protocol/input validation failure
Examples:

- malformed XPC message
- oversized message
- unknown message type
- malformed external document content

Handling:

- reject or discard invalid input according to protocol rules
- log with context
- never raise unknown XPC message types as exceptions

## Dependencies

### Internal Forge dependencies

- `src/consensus.py`
  - consensus/arbitration logic
  - provider retry/fallback behavior
- `src/build_director.py`
  - stage orchestration and pipeline control
- `src/github_tools.py`
  - the sole allowed GitHub integration surface
- `src/build_ledger.py`
  - build state and history tracking
- `path_security.validate_write_path()`
  - mandatory pre-write path validation

### External service dependencies

- Anthropic provider APIs
- OpenAI provider APIs
- GitHub APIs, exclusively through `GitHubTool`
- CI systems as routed through repository/GitHub integration
- document store status/context providers

### Protocol dependencies

- XPC line-delimited JSON transport
- nonce-authenticated messaging
- message size cap of 16 MB
- supported message schemas:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### Operational assumptions

- Operator input is available to resolve gates.
- The subsystem may block indefinitely awaiting approval.
- Repository changes are applied only through validated file paths and mediated GitHub operations.
- External content sources are not trusted by default.