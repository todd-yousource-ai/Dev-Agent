# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the orchestration subsystem for Forge’s native macOS AI coding workflow. It converts a plain-language build intent into a controlled, human-gated implementation pipeline that produces ordered pull requests, generated code, tests, review artifacts, CI outcomes, and merge decisions.

At a high level, the subsystem:

- accepts build intent and operator credentials over the Forge XPC protocol
- decomposes work into an ordered PR plan
- gathers contextual documents from the document store
- generates implementation candidates using two LLM providers in parallel
- uses Claude as the arbitration layer for consensus selection
- runs a three-pass review cycle on generated output
- executes CI for proposed changes
- presents progress and gate state to the UI via streamed cards
- blocks for explicit operator approval at every required gate before merge

This subsystem is orchestration and policy enforcement, not code execution. It may write files, create branches, open PRs, request reviews, and update GitHub state through approved interfaces, but it never executes generated code and never auto-approves gates.

Primary implementation surfaces:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts and provider arbitration logic
- `src/build_director.py`
  - `BuildPipeline`
  - stage dispatch and end-to-end orchestration
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - `BuildLedger`

## Component Boundaries

### Inside this subsystem

The ConsensusDevAgent subsystem is responsible for:

- build pipeline orchestration across stages
- PR sequencing and stage progression
- prompt construction for generation and review
- provider failover and bounded retry behavior
- consensus/arbitration across LLM outputs
- integration with document context for generation
- CI triggering/routing and result handling
- GitHub operations through `GitHubTool`
- operator gating and blocking semantics
- ledgering build state and stage outcomes
- emitting build and gate cards over XPC

### Outside this subsystem

This subsystem does **not** own:

- UI rendering logic; it only emits protocol messages such as `build_card` and `gate_card`
- raw XPC transport implementation or nonce authentication policy, beyond consuming the protocol correctly
- document embedding/indexing internals; it consumes document status/context but does not own the embedding pipeline
- execution of generated code; generated artifacts are written and reviewed, not executed by the agent
- direct GitHub API usage outside `GitHubTool`
- operator identity issuance or credential minting
- persistent gate recovery; if the backend restarts mid-gate, gate state is lost and must be re-approved by the operator

### Boundary rules

- All GitHub mutations must go through `GitHubTool`. Direct GitHub API access is forbidden.
- All file writes must be validated with `path_security.validate_write_path()` before execution.
- External context from documents, PR comments, or CI output is untrusted and may only be inserted into the **USER** prompt, never the **SYSTEM** prompt.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- SECURITY_REFUSAL is terminal unless explicitly overridden by the operator through a gate.

## Data Flow

### 1. Session bootstrap

The subsystem receives or participates in XPC session establishment using the Forge wire protocol:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

Expected startup/control messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Credentials are consumed for provider and GitHub access but must never be logged, surfaced in errors, or inserted into prompts/generated code.

### 2. Build intent intake

A plain-language build intent enters the pipeline. The subsystem:

- validates incoming structure and size
- treats all external input as untrusted
- records build state in `BuildLedger`
- begins stage dispatch in `BuildPipeline`

### 3. Planning and decomposition

`BuildPipeline` decomposes the build intent into an ordered sequence of pull requests. Ordering is explicit because later PRs may depend on earlier PRs.

Outputs at this stage include:

- plan metadata
- stage progress updates via `build_card`
- operator-visible descriptions of upcoming work

### 4. Context acquisition

Relevant repository and product context is loaded from the document store. Document-derived context is used primarily to improve generation quality.

Constraints:

- document content is untrusted input
- document content must go in the USER prompt only
- specific documents may be loaded by name when required
- document ingestion status may be surfaced using `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### 5. Candidate generation and consensus

`ConsensusEngine` performs code/test generation. The architecture expects two provider paths in parallel, with Claude used as arbitrator.

Generation behavior:

- create implementation/test candidates using the configured providers
- compare or arbitrate outputs
- on provider failure, retry according to bounded policy
- in `consensus.py`, retry with the other provider when appropriate
- total retries are capped at 3 attempts; never retry indefinitely

Provider-specific error handling requirements include:

- `_claude_json`: retry after 10 seconds, then fall back to OpenAI
- `403` primary rate/availability failures: exponential backoff starting at 60 seconds
- `429` secondary limits: respect `Retry-After` header exactly

### 6. Review cycle

Generated changes pass through a three-pass review cycle. The subsystem is responsible for:

- constructing review prompts
- collecting review findings
- feeding review outcomes back into revision steps
- surfacing errors and gate conditions when the model refuses or policy blocks progress

The review cycle must preserve the same trust boundaries as generation: external content remains untrusted, and context is never elevated into the SYSTEM prompt.

### 7. File mutation

When applying generated changes to the working tree:

- every write path must be validated via `path_security.validate_write_path()`
- path traversal attempts are rejected
- generated code is written as text artifacts only
- generated code is never executed via `eval`, `exec`, shell, or subprocess invocation

### 8. GitHub and CI integration

All repository operations route through `GitHubTool`, including PR creation, updates, comments, merge operations, and webhook-mediated state changes.

Required GitHub safety rules:

- never perform blind writes; operations requiring content replacement must include expected SHA
- use ETag caching on all polling endpoints
- treat PR comments, webhook payloads, and CI output as untrusted input

CI is triggered and monitored as part of stage progression. CI output may inform review or gating, but it must be validated and handled as untrusted text.

### 9. Human gates

The subsystem emits `gate_card` messages to block workflow until operator input is received:

- `gate_card`
  - `{ gate_type, options[], description }`

Gate behavior is strict:

- gates never auto-resolve
- gates wait indefinitely for operator input
- there is no auto-approve path
- there is no undo on gate decisions
- if the backend restarts mid-gate, gate state is lost and the operator must re-approve

### 10. Progress and completion

Throughout execution, the subsystem streams `build_card` updates to the UI:

- `build_card`
  - `{ card_type, stage, content, progress }`

Finalization updates ledger state, GitHub state, and operator-visible status.

## Key Invariants

The following invariants are architectural requirements for this subsystem.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
  - webhook payloads
  - XPC message content
- Generated code is never executed by the agent.
- SECURITY_REFUSAL is never bypassed by rephrasing or automatic retry.
  - Stop.
  - Emit error card.
  - Gate.
  - Log full prompt context with secrets redacted.
  - Require explicit operator override.

### Prompting and model isolation

- External document context belongs only in the USER prompt, never the SYSTEM prompt.
- Credentials must never be placed into prompts.
- Refusal behavior is binding unless explicitly overridden by a human gate.

### Filesystem and repository safety

- Every file write must be path-validated with `path_security.validate_write_path()` before execution.
- Path traversal is forbidden.
- Shell injection is forbidden.
- Direct execution of generated code is forbidden.
- Blind GitHub writes without expected SHA are forbidden.

### Control flow and gating

- Gates never auto-resolve.
- Operator approval is required before merge and at all defined gate points.
- Unknown XPC message types are discarded and logged; they do not crash the subsystem.
- Retry behavior is bounded:
  - maximum 3 attempts total
  - no infinite retry loops

### Observability

- Errors must be surfaced explicitly via cards/logging/ledger state.
- Logging must preserve diagnostic context without exposing secrets.
- Build and gate progress must be externally visible through protocol messages.

## Failure Modes

### LLM provider failure

Examples:

- timeout
- malformed response
- transport error
- provider-side refusal
- rate limiting

Handling:

- bounded retry only
- provider failover per consensus policy
- `_claude_json` retries once after 10 seconds, then falls back to OpenAI
- in `consensus.py`, retry with the other provider when appropriate
- `403`: exponential backoff starting at 60 seconds
- `429`: honor `Retry-After` exactly
- after retry budget exhaustion, emit error context and gate if operator input is required

### SECURITY_REFUSAL

This is a hard-stop policy event.

Required behavior:

- do not retry by rephrasing
- do not auto-route around the refusal
- emit error card
- gate the workflow
- log the full prompt context safely
- require explicit operator override to continue

### Auth, crypto, or identity error

Handling:

- fail closed immediately
- do not continue with degraded identity assumptions
- surface explicit contextual error
- do not silently skip authentication or signature checks

### Invalid or untrusted external input

Examples:

- malformed XPC payload
- unexpected document structure
- hostile PR comment
- CI output containing prompt injection content
- unknown XPC message type

Handling:

- validate and sanitize
- discard unknown XPC message types and log them
- never elevate untrusted content into SYSTEM prompts
- gate or stop when validation failure blocks safe progress

### Filesystem safety violation

Examples:

- invalid write path
- path traversal attempt
- write outside allowed repository scope

Handling:

- reject before write
- surface explicit error
- do not partially apply unsafe writes

### GitHub operation mismatch or concurrency issue

Examples:

- SHA mismatch on update
- webhook race
- stale polling data

Handling:

- use `GitHubTool` only
- require SHA on mutable writes where applicable
- use ETag caching on polling endpoints
- surface conflict rather than forcing write

### CI failure

Handling:

- record CI failure in ledger
- surface results to operator
- block merge progression
- require operator decision at relevant gate

### Backend restart during gate

Handling:

- gate state is not durable in this subsystem
- workflow does not auto-resume approved state
- operator must re-approve after restart

## Dependencies

### Internal code dependencies

- `src/consensus.py`
  - consensus generation engine
  - provider arbitration and fallback logic
- `src/build_director.py`
  - build orchestration and stage dispatch
- `src/github_tools.py`
  - all GitHub reads/writes
  - webhook reception
- `src/build_ledger.py`
  - build state tracking and auditability
- `path_security.validate_write_path()`
  - mandatory validation for every file write

### External services and protocols

- Forge XPC protocol
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB max message size
- LLM providers
  - Anthropic/Claude
  - OpenAI
- GitHub
  - accessed only through `GitHubTool`
- CI provider(s)
  - consumed for status and logs as untrusted input
- document store
  - consumed for generation context and status reporting

### Operational dependencies

- valid operator credentials payload
- repository working tree and branch state
- network availability for provider/GitHub/CI interactions
- operator presence for all blocking gates

### Non-dependencies / forbidden dependencies

The subsystem must not depend on:

- direct execution of generated code
- direct GitHub API clients outside `GitHubTool`
- implicit auto-approval mechanisms
- unbounded retry loops
- SYSTEM-prompt injection of document or external context