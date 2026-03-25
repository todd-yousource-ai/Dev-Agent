# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an ordered sequence of pull requests and drives each PR through generation, validation, correction, CI, and operator-gated merge.

At a subsystem level, it is responsible for:

- Decomposing build intent into staged PR work
- Running generation with two LLM providers in parallel, with Claude arbitrating
- Performing a self-correction pass
- Enforcing a lint gate
- Running a bounded 20-pass fix loop
- Executing CI
- Blocking on operator approval before merge
- Persisting per-PR stage checkpoints so completed work is not re-run after a crash
- Persisting cross-run learning in build memory and build rules

The subsystem also manages build-time context assembly from repository documents and persisted learning artifacts. External document context is used for generation, but must be placed in the USER prompt and never the SYSTEM prompt.

The scope phase includes a confidence gate:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- If below threshold, the agent shows gaps and offers `proceed`, `answer`, or `cancel`
- If the operator answers gaps, exactly one re-scope pass is allowed; there is no open-ended loop

## Component Boundaries

The subsystem boundary is defined by orchestration, context assembly, persistence of learned build state, protocol messaging, and controlled integration with GitHub and document storage.

### In scope

#### Build orchestration
- `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate
  - `pr_type` routing

#### Consensus and generation policy
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

#### GitHub integration
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

All GitHub operations are required to pass through `GitHubTool`. Direct GitHub API use is outside the allowed architecture.

#### Build state persistence
- `src/build_ledger.py`
  - per-PR stage checkpoints used for crash recovery and re-entry control

#### Persistent learning artifacts
- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md`
  - self-improving coding rules derived from build history
  - written after each build run when 3 or more recurring failure patterns are found
  - loaded automatically by `DocumentStore`

#### Operator gating and UI protocol messages
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator response

#### XPC protocol participation
- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message
- readiness and status messages including:
  - `ready`
  - `credentials`
  - `doc_status`

### Out of scope

- Executing generated code
- Auto-approving any gate
- Bypassing security refusals by prompt reformulation
- Treating unknown XPC message types as exceptions
- Clearing build memory or build rules automatically on clean runs
- Using external documents as privileged system instruction material
- Unvalidated writes to the filesystem
- Direct GitHub API calls outside `GitHubTool`

## Data Flow

### 1. Session initialization
The subsystem participates in XPC startup using nonce-authenticated, line-delimited JSON messages. A `ready` message communicates:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Credentials arrive as:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Auth, crypto, and identity failures fail closed.

### 2. Build intent intake and scope assessment
A plain-language build intent enters the build pipeline. The subsystem performs scope analysis and computes:

- `confidence`
- `coverage_gaps`

`_stage_scope` compares confidence against `_CONFIDENCE_THRESHOLD = 85`.

If below threshold:
- gaps are surfaced explicitly
- the operator is offered `proceed`, `answer`, or `cancel`
- if answers are provided, one re-scope pass is performed
- if still unresolved, the workflow remains gated; there is no autonomous escalation or auto-approval

### 3. Context assembly
Generation context is assembled from repository and persistent artifacts, including document-store content and learned rules.

DocumentStore usage includes:
- primary generation context loading
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatic loading of `Mac-Docs/build_rules.md`

Context handling constraints:
- all external input is untrusted and validated
- context from external documents is placed in the USER prompt only
- never in the SYSTEM prompt
- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn and the last 6 messages
- CI log output is truncated at 8k characters using 70% head / 30% tail

### 4. PR decomposition and generation
The build intent is decomposed into an ordered sequence of PRs. For each PR, generation is performed with two LLM providers in parallel, and Claude arbitrates through the consensus path.

The consensus layer is implemented in `src/consensus.py` and governed by the generation system prompts defined there.

### 5. Validation and repair
For each PR, the subsystem performs:
- self-correction
- lint gating
- local fix attempts, bounded to 20 passes

Failure handling follows the documented pattern in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- primary signal is `failure_type`
- secondary signal is `attempt`

Required strategy mapping:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 6. CI execution and external polling
CI is executed as part of PR validation.

Polling and API-related behavior includes:
- `403 primary` → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints

### 7. Operator gate and merge
Before merge, the subsystem emits a `gate_card` and blocks indefinitely until operator input is received.

There is never auto-approval.

### 8. Persistence and recovery
After every successful PR:
- build memory is updated via `build_memory.record_pr()`

After each build run:
- if 3 or more recurring failure patterns are found, `build_rules.md` is updated

Per-PR stage checkpoints prevent re-running completed work after crashes.

## Key Invariants

The subsystem enforces the following architectural invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input, including documents, PR comments, and CI output, is untrusted and validated
- Generated code is never executed by the agent; no `eval`, no `exec`, no subprocess of generated content
- Gates wait indefinitely for operator input; no auto-approve ever
- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log
- XPC unknown message types are discarded and logged; never raised as exceptions
- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory and build rules are persistent learning systems and are never cleared automatically

Additional subsystem-specific enforcement rules:

- All GitHub operations go through `GitHubTool`
- Validate paths before any write
- Scope confidence below 85 must surface coverage gaps and operator options
- Re-scope after operator answers is one-shot only
- Retry behavior is bounded to 20 local attempts
- Build memory must survive fresh installs and thread state wipes
- `build_rules.md` must not be deleted on clean runs unless switching to a completely new codebase

## Failure Modes

### Scope uncertainty
If scope confidence is below threshold:
- the subsystem does not silently proceed as fully understood
- it surfaces `coverage_gaps`
- it gates on operator choice
- at most one re-scope occurs after operator answers

### Auth, crypto, or identity failure
These failures are terminal for the affected operation and fail closed. The subsystem does not fall back to degraded identity or unauthenticated behavior.

### Invalid or unsafe external input
Because all external input is untrusted:
- invalid input must be validated before use
- unsafe input must not be promoted into privileged prompt context
- document-derived context must not enter the SYSTEM prompt

### Unsafe filesystem write
Any file write that fails `path_security.validate_write_path()` must not execute.

### Security refusal
If generation or policy produces `SECURITY_REFUSAL`:
- processing stops
- a gate is raised
- the event is logged
- rephrasing is not a bypass path

### Unknown XPC message type
Unknown message types are discarded and logged, not raised as exceptions.

### Generation/test failure
Repair strategy is selected by `_choose_strategy(failure_type, attempt, records)` using failure type as the primary signal. Attempts are bounded; after 20 local attempts the subsystem moves on rather than retrying indefinitely.

### GitHub/API throttling or access issues
- `403 primary` triggers exponential backoff up to 64 seconds
- `429 secondary` respects `Retry-After`
- polling endpoints use ETag caching

### Crash or interruption
Per-PR stage checkpoints prevent re-running already completed work after restart.

### Context overflow
`ContextManager` automatically trims context at 30k tokens while preserving:
- the spec-anchor first turn
- the last 6 messages

### CI log overload
CI output is automatically truncated to 8k characters using a 70/30 head-tail split.

## Dependencies

### Internal code modules
- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `src/build_ledger.py`
- `failure_handler.py`
- `path_security.validate_write_path()`
- `ContextManager`
- `DocumentStore`

### Persistent data and documents
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- repository documents loaded through the document store, including specific documents such as `PRODUCT_CONTEXT.md`

### Protocol and platform dependencies
- XPC wire format
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB maximum message size
- BuildStreamView consumer for `build_card`
- operator response handling for `gate_card`

### External service dependencies
- LLM providers via credentials:
  - Anthropic
  - OpenAI
- GitHub access through `GitHubTool`

### Required control constraints on dependencies
- GitHub must only be accessed through `GitHubTool`
- document-derived context must remain in USER prompt space
- filesystem writes must be path-validated before execution
- polling behavior must use ETag caching and documented backoff handling