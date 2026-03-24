# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that executes the build workflow from plain-language build intent through pull-request-based implementation and gated merge.

At a system level, ForgeAgent:

- decomposes a build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitrator in consensus generation
- runs a self-correction pass
- runs a lint gate
- runs a 20-pass local fix loop
- executes CI
- blocks on operator approval before merge
- persists cross-run learning in build memory and build rules

The subsystem also owns the operator-facing gating behavior for uncertain scope and approval-required transitions. In particular, the scope-confidence flow is explicitly staged:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the operator is shown gaps and offered `proceed`, `answer`, or `cancel`
- if the operator answers the gaps, ForgeAgent performs a one-shot re-scope only; it does not loop indefinitely

ForgeAgent is responsible for ensuring that generated code is produced, corrected, validated, and proposed as PRs, but not executed as arbitrary generated content.

Relevant implementation ownership called out in the source material:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — named in architecture context as part of the backend file set

## Component Boundaries

ForgeAgent’s boundaries are defined by the orchestration, generation, gating, persistence, and GitHub-operation rules in the TRD material.

### Inside this subsystem

ForgeAgent includes:

- build pipeline orchestration
- PR sequencing and stage management
- scope confidence evaluation and operator gating
- multi-provider generation consensus
- self-correction, lint, and local fix-loop orchestration
- CI execution handling
- operator gate presentation and blocking behavior
- persistent build-learning state management
- document-context loading for generation
- GitHub operations through the approved tool abstraction

Concrete owned concepts include:

- `BuildPipeline`
- `ConsensusEngine`
- `GitHubTool`
- stage checkpoints per PR
- build memory persistence
- build rules persistence
- document-store-backed context retrieval for generation

### Outside this subsystem

ForgeAgent does not own:

- direct GitHub API access outside `GitHubTool`
- arbitrary execution of generated code
- automatic approval decisions
- silent degradation when authentication, cryptography, or identity handling fails
- bypass of security refusal behavior
- trust of external inputs without validation

ForgeAgent also does not redefine XPC protocol behavior; it consumes the defined wire protocol and must conform to its constraints.

### Explicit operational boundaries

- All GitHub operations must go through `GitHubTool`. Direct GitHub API usage is out of bounds.
- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- External document context belongs in the `USER` prompt only, never the `SYSTEM` prompt.
- Build memory and build rules are persistent learning systems and must not be automatically cleared during normal clean runs.

## Data Flow

The subsystem’s data flow is a staged orchestration pipeline with persistent checkpoints and operator gates.

### 1. Session and protocol initialization

ForgeAgent communicates over XPC using:

- line-delimited JSON
- nonce authentication
- maximum `16MB` per message

The protocol surface includes:

- `ready` message  
  `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`  
  `{ card_type, stage, content, progress }`  
  streamed to `BuildStreamView`
- `gate_card`  
  `{ gate_type, options[], description }`  
  blocks until operator responds
- `credentials`  
  `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`  
  `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are not raised as exceptions; they are discarded and logged.

### 2. Build intent to scoped plan

A plain-language build intent enters ForgeAgent. The subsystem performs scope analysis and computes:

- confidence score
- coverage gaps

If confidence is below `_CONFIDENCE_THRESHOLD = 85`, `_stage_scope` emits a gate to the operator with options to:

- proceed
- answer
- cancel

If the operator provides gap answers, ForgeAgent performs one re-scope pass. There is no repeated clarification loop.

### 3. Context assembly for generation

ForgeAgent assembles generation context from repository state and document sources.

Document Store is used for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

Context handling constraints:

- all external input is untrusted and validated
- document-derived context is placed in the `USER` prompt
- document-derived context is never placed in the `SYSTEM` prompt

ContextManager behavior is automatic:

- trims at `30k` tokens
- preserves the spec-anchor first turn
- preserves the last 6 messages

### 4. Generation and consensus

For each PR in the ordered sequence, ForgeAgent invokes parallel generation across two LLM providers. Consensus behavior is owned by `ConsensusEngine` in `src/consensus.py`, with Claude acting as arbitrator.

Generation system prompts are defined in that component:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

### 5. Correction and validation loop

After generation, ForgeAgent runs:

- self-correction pass
- lint gate
- local fix loop with a maximum of 20 attempts

Failure handling is strategy-driven. In `failure_handler.py`, `_choose_strategy(failure_type, attempt, records)` uses:

- failure type as the primary signal
- attempt count as secondary escalation

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — max 20 local attempts, then move on

### 6. CI processing

ForgeAgent executes CI and processes CI output as untrusted external input.

Polling and API interaction behavior includes:

- `403 primary` → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints

CI log handling is automatic:

- output truncated at `8k` chars
- truncation preserves `70%` head and `30%` tail

### 7. Operator gate and merge boundary

Before merge, ForgeAgent emits `gate_card` and waits indefinitely for operator input.

This gate:

- does not auto-approve
- does not timeout into approval
- blocks further progression until the operator responds

### 8. Persistence and crash recovery

ForgeAgent maintains per-PR stage checkpoints to prevent re-running completed work after a crash.

It also persists long-lived learning state:

- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread state wipes
  - must not be deleted on clean runs
- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3+ recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

ForgeAgent is constrained by the following non-negotiable invariants from the architecture context and subsystem headings.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, and no subprocess execution of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Operator control

- Gates wait indefinitely for operator input.
- There is no auto-approve behavior ever.
- Scope clarification below threshold supports at most one re-scope cycle when the operator answers gaps.

### File and path safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Validate paths before any write.

### Prompt and context isolation

- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.

### Protocol robustness

- XPC unknown message types are discarded and logged, never raised as exceptions.
- XPC messages are line-delimited JSON, nonce-authenticated, and capped at `16MB`.

### Work progression and durability

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### Retry and escalation discipline

- Failure type drives local repair strategy selection.
- Local retries are bounded at 20 attempts.
- Network/API retry behavior follows the documented backoff and rate-limit handling rules.

## Failure Modes

ForgeAgent is designed to surface, contain, and gate failures rather than masking them.

### Scope-confidence failure mode

If scoping confidence is below the threshold:

- ForgeAgent does not silently continue as if scope were adequate
- it surfaces `coverage_gaps`
- it gates on operator choice
- it permits only one answer-driven re-scope pass

Primary effect: uncertain scope becomes an explicit operator decision point.

### Auth, crypto, and identity failure mode

On authentication, cryptographic, or identity errors:

- ForgeAgent fails closed
- it does not degrade to reduced-trust operation
- errors must be surfaced with context

Primary effect: protected operations stop instead of proceeding insecurely.

### Security refusal failure mode

If a `SECURITY_REFUSAL` is produced:

- ForgeAgent stops
- gates
- logs
- does not attempt to bypass by rephrasing

Primary effect: refusal is terminal for that path until operator intervention.

### Invalid external input failure mode

Because documents, PR comments, and CI output are untrusted:

- invalid or unsafe input must be validated and contained
- it must not be implicitly promoted into trusted system instructions

Primary effect: untrusted content may influence user-context generation, but not privileged instruction channels.

### Unknown XPC message failure mode

If an unknown XPC message type is received:

- the message is discarded
- the event is logged
- no exception is raised

Primary effect: protocol evolution or malformed traffic does not crash the agent on unknown types.

### File write safety failure mode

If a write path does not pass `path_security.validate_write_path()`:

- the write must not execute

Primary effect: filesystem mutation is blocked before unsafe writes occur.

### Generation and fix-loop exhaustion

If generated changes fail validation or tests repeatedly:

- strategy selection follows `_choose_strategy(failure_type, attempt, records)`
- retries are capped at 20 local attempts
- ForgeAgent does not retry indefinitely

Primary effect: the subsystem escalates deterministically and then moves on rather than livelocking.

### GitHub and polling failure modes

For GitHub or polling-related failures:

- all operations remain within `GitHubTool`
- `403 primary` triggers exponential backoff from `2s` to `64s`
- `429 secondary` honors `Retry-After`
- polling uses ETag caching

Primary effect: API pressure and transient denial are handled with bounded, protocol-aware retry behavior.

### Crash recovery failure mode

If ForgeAgent crashes mid-PR:

- per-PR stage checkpoints prevent re-running already completed work

Primary effect: resumed execution is stage-aware and avoids duplicating successful stages.

### Logging and disclosure failure mode

Even during failures:

- secrets must not appear in logs
- secrets must not appear in error messages
- secrets must not appear in generated code

Primary effect: failure reporting remains non-secret-bearing.

## Dependencies

The subsystem depends on the following components and interfaces named in the source material.

### Internal backend modules

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - owns confidence gate behavior
  - owns `pr_type` routing
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines `GENERATION_SYSTEM`
  - defines `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
- `src/build_ledger.py`
  - present in the backend file naming inventory

### Supporting subsystems and utilities

- `DocumentStore`
  - used for generation context
  - auto-loads `Mac-Docs/build_rules.md`
- `ContextManager`
  - trims context at `30k` tokens
  - preserves spec-anchor first turn and last 6 messages
- `failure_handler.py`
  - provides `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
  - required before all file writes

### External/provider dependencies

- two LLM providers in parallel
- Anthropic credentials via `anthropic_api_key`
- OpenAI credentials via `openai_api_key`
- GitHub access via `github_token`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol/UI dependencies

- XPC transport using the documented line-delimited JSON format
- `BuildStreamView` as the consumer for streamed `build_card` messages
- operator interaction via blocking `gate_card` messages