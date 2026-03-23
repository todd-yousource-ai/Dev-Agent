# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end orchestration subsystem for Forge’s native macOS coding agent workflow. It coordinates the full build lifecycle from operator intent to gated merge, spanning:

- intake of plain-language build intent
- scope analysis and confidence gating
- decomposition into ordered pull requests
- context assembly from persistent memory and document sources
- parallel code generation via multiple LLM providers
- consensus/arbitration over generated outputs
- self-correction, lint, and bounded fix-loop execution
- CI execution and result handling
- operator gating for approval-sensitive transitions
- GitHub PR lifecycle operations
- persistent cross-run learning via build memory and build rules
- crash-safe progress recovery using per-PR stage checkpoints

This subsystem is the top-level build pipeline coordinator. It is responsible for enforcing platform-wide safety, gating, and persistence rules while delegating specialized work to lower-level components such as consensus, document retrieval, GitHub operations, path validation, and failure handling.

Operationally, FullPlatform maps most directly to:

- `src/build_director.py` — primary orchestration via `BuildPipeline`, confidence gate, PR routing
- `src/consensus.py` — provider arbitration and generation system prompts
- `src/github_tools.py` — all GitHub interaction via `GitHubTool`, webhook reception
- `src/build_ledger.py` — persistent stage/checkpoint tracking

## Component Boundaries

### In Scope

FullPlatform owns:

- build-stage orchestration across the entire PR pipeline
- stage ordering and transition rules
- operator-visible gates and indefinite waits for operator input
- scope confidence evaluation and threshold enforcement
- PR-by-PR checkpointing and crash recovery semantics
- assembly of generation context from documents, memory, and rules
- invocation of generation, correction, lint, fix-loop, and CI phases
- enforcement of max local retry/fix limits
- recording successful PR outcomes into persistent learning artifacts
- coordination of streamed UI/protocol messages such as `build_card`, `gate_card`, and readiness/status messages

### Out of Scope

FullPlatform does not own:

- direct GitHub API access; all such operations must go through `GitHubTool`
- raw provider-specific model transport details beyond orchestration interfaces
- document embedding/index internals beyond consuming `DocumentStore` outputs
- low-level path canonicalization/validation logic beyond requiring `path_security.validate_write_path()`
- execution of generated code as agent instructions; generated content is treated as artifact, never as executable control input
- XPC transport implementation details beyond complying with protocol contracts and message semantics
- automatic approval or merge decisions without operator input

### Explicit Boundary Rules

- External documents, PR comments, CI output, and all inbound protocol content are untrusted inputs.
- Context sourced from external documents must be placed in the USER prompt, never the SYSTEM prompt.
- Secrets handling, credential transport, and log redaction are mandatory cross-cutting constraints, not optional caller behavior.
- Unknown XPC message types are not propagated as exceptions; they are discarded and logged.
- Persistent learning artifacts (`build_memory.json`, `build_rules.md`) are retained across runs and are not cleanup targets in normal operation.

## Data Flow

### 1. Session Initialization

On startup, FullPlatform participates in the XPC/session handshake using line-delimited JSON messages, nonce-authenticated, with a maximum size of 16 MB per message.

Relevant protocol messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

At this point, FullPlatform establishes:

- runtime capability awareness
- document store availability status
- provider credentials
- engineer/workspace identity for persistent state locations

### 2. Intent Intake and Scope Analysis

The operator provides a build intent. FullPlatform initiates scope analysis and confidence estimation.

The scope gate behavior is:

- `SCOPE_SYSTEM` returns:
  - `confidence` in range `0–100`
  - `coverage_gaps`
- `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold, the subsystem:

- surfaces identified gaps to the operator
- offers `proceed`, `answer`, or `cancel`
- allows a one-shot re-scope if the operator answers gaps
- does not enter an unbounded clarification loop

This gate is mandatory before continuing normal build planning.

### 3. Context Assembly

For generation and planning, FullPlatform assembles context from:

- operator intent and current conversation state
- repository state
- `DocumentStore` retrievals and explicit document loads
- persistent build memory
- persistent build rules

Context handling constraints:

- external document content is injected only into USER prompt space
- context manager auto-trims at 30k tokens
- preserved context includes:
  - the spec-anchor first turn
  - the last 6 messages

Relevant persistent sources:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are loaded and reused across runs.

### 4. PR Planning and Stage Execution

The build is decomposed into an ordered sequence of PRs. For each PR, FullPlatform executes staged work with checkpoint persistence so completed stages are not rerun after a crash.

Typical stage progression includes:

1. scope/planning
2. implementation generation
3. consensus/arbitration
4. self-correction
5. lint gate
6. bounded local fix loop
7. CI execution
8. operator approval gate
9. merge/finalization
10. post-PR learning persistence

Checkpoint semantics are strict:

- per-PR stage checkpoints are durable
- after crash/restart, completed stages are skipped
- the subsystem resumes from the last incomplete stage rather than replaying the full PR lifecycle

### 5. Multi-Provider Generation and Consensus

FullPlatform invokes two LLM providers in parallel for implementation generation. Consensus logic is delegated to the consensus engine, with Claude serving as arbiter per platform design.

Consensus is used to:

- compare candidate implementations
- select or synthesize the preferred output
- support subsequent correction passes

The subsystem uses consensus outputs as build artifacts, not executable instructions.

### 6. File Mutation and Validation

Any file write generated or proposed during the pipeline must be validated through:

- `path_security.validate_write_path()`

This is required before execution of the write operation. No write path is trusted by default.

### 7. Failure Handling and Bounded Repair

When build/test failures occur, FullPlatform routes through failure-handling policy.

In `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`

Policy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- maximum 20 local attempts; never retry indefinitely

Additional constraints:

- lint and CI failures are surfaced, not suppressed
- CI log output is truncated to 8k chars using 70% head / 30% tail
- no silent fallback path is allowed

### 8. Network Polling and Rate Limits

For polling-based external operations, FullPlatform relies on:

- ETag caching on all polling endpoints
- `403` primary rate-limit handling with exponential backoff:
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate-limit handling respecting `Retry-After`

These are resilience mechanisms, not optional optimizations.

### 9. Operator Gates and Completion

Approval-sensitive transitions emit `gate_card` messages:

- `{ gate_type, options[], description }`

These gates block indefinitely until operator response. There is no auto-approve path.

Streaming progress is emitted via `build_card`:

- `{ card_type, stage, content, progress }`

After successful PR completion:

- `build_memory.record_pr()` persists outcome data
- recurring failure analysis may update `build_rules.md` when 3 or more recurring patterns are detected

## Key Invariants

The following invariants are enforced by FullPlatform and must not be relaxed:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
  - protocol payloads
- Generated code is never executed by the agent as instructions:
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent rerunning completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional subsystem-specific invariants:

- Scope confidence below threshold cannot pass silently into implementation.
- Re-scoping after operator clarification is one-shot, not an unbounded loop.
- GitHub operations are centralized through `GitHubTool`; direct API usage is prohibited.
- Local repair attempts are bounded to 20 iterations maximum.
- Context trimming preserves specification anchor and recent conversational state.

## Failure Modes

### Scope Confidence Failure

Condition:

- scope confidence `< 85`

Behavior:

- pipeline does not silently proceed
- operator is shown `coverage_gaps`
- operator must choose to proceed, answer, or cancel
- optional one-shot re-scope occurs if answers are provided

### Authentication / Credential / Identity Failure

Condition:

- invalid or missing credentials
- auth handshake failure
- identity mismatch

Behavior:

- fail closed
- stop further sensitive operations
- surface explicit error context
- never substitute degraded anonymous behavior

### Document Store Unavailable or Partial

Condition:

- `doc_store_status` unavailable/degraded
- document load failure
- embedding status incomplete

Behavior:

- surface status explicitly
- continue only where policy permits and only with clear context
- never fabricate document-backed context
- never elevate external content into SYSTEM prompt

### Invalid or Unsafe Write Path

Condition:

- `path_security.validate_write_path()` rejects a path

Behavior:

- write is not executed
- failure is surfaced with context
- no bypass or fallback write location is used

### Provider Generation Failure or Consensus Failure

Condition:

- one or both model providers fail
- arbitration cannot determine an acceptable result

Behavior:

- error is surfaced
- no silent provider substitution without policy visibility
- downstream stages do not treat missing/invalid output as success

### Fix Loop Exhaustion

Condition:

- 20 local repair attempts reached without resolution

Behavior:

- stop local retries
- surface bounded-failure result
- move on according to orchestration policy rather than retry indefinitely

### CI Failure

Condition:

- CI reports failing status or unusable output

Behavior:

- logs are truncated to 8k chars with 70/30 head-tail preservation
- failure is surfaced to operator/pipeline
- no hidden pass-through or ignore behavior

### GitHub Rate Limiting / Polling Failure

Condition:

- `403` primary rate limit
- `429` secondary rate limit
- stale polling state

Behavior:

- apply exponential backoff for `403`
- respect `Retry-After` for `429`
- use ETag caching
- surface persistent failure if recovery does not succeed

### Crash / Restart Mid-PR

Condition:

- process crash or restart during staged PR execution

Behavior:

- resume from durable per-PR checkpoint
- do not rerun completed stages
- preserve persistent learning artifacts

### Unknown XPC Message Type

Condition:

- inbound protocol message type not recognized

Behavior:

- discard and log
- do not throw transport-level exception solely for unknown type

## Dependencies

### Internal Components

- `BuildPipeline` / orchestration logic in `src/build_director.py`
- `ConsensusEngine` and generation system prompts in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- build stage ledger/checkpoint persistence in `src/build_ledger.py`
- failure strategy selection in `failure_handler.py`
- `ContextManager` for token trimming and message preservation
- `DocumentStore` for retrieval and document loading
- `path_security.validate_write_path()` for write authorization

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - persistent per-engineer build memory
  - written after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread-state wipes
- `Mac-Docs/build_rules.md`
  - persistent self-improving coding rules
  - auto-loaded by `DocumentStore`
  - updated after build runs when 3+ recurring failure patterns are detected

### External Services and Interfaces

- Anthropic provider
- OpenAI provider
- GitHub, but only via `GitHubTool`
- XPC transport using line-delimited JSON with nonce authentication
- CI systems producing build/test output consumed as untrusted input

### Dependency Constraints

- FullPlatform must not call GitHub APIs directly.
- FullPlatform must not trust provider output as executable control logic.
- FullPlatform must treat all protocol and document inputs as hostile until validated.
- FullPlatform depends on operator presence for approval gates and cannot substitute automated approval behavior.