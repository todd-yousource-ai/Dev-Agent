# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an operator-gated sequence of pull requests.

At a subsystem level, it:

1. Accepts build intent and repository context.
2. Decomposes work into an ordered PR plan.
3. Runs generation using two LLM providers in parallel, with Claude arbitrating.
4. Performs self-correction, lint gating, and a bounded local fix loop.
5. Executes CI and surfaces results.
6. Waits for explicit operator input at defined gates, including merge approval.
7. Persists cross-run learning in build memory and build rules.

The subsystem is not an autonomous merger or executor of generated code. It is a gated orchestration system with persistent learning and strict security controls.

Relevant implementation anchors called out in the architecture context:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR type routing
- `src/consensus.py` — `ConsensusEngine`, generation system prompts
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing support implied by subsystem invariants

## Component Boundaries

### Inside the subsystem

The CraftedDevAgent subsystem includes:

- Build orchestration through the build pipeline
- Scope confidence evaluation and gating
- PR sequencing and stage progression
- Parallel LLM generation and consensus arbitration
- Document context loading for generation
- Build memory and build rules persistence
- GitHub operations through the approved tool layer
- CI result handling and bounded fix-loop behavior
- Operator gate presentation and blocking wait semantics
- XPC message handling under the defined wire protocol
- Error surfacing, logging, and checkpoint-based crash recovery

### Outside the subsystem

The subsystem does not own or directly perform:

- Direct GitHub API access outside `GitHubTool`
- Execution of generated code via `eval`, `exec`, or subprocess of generated content
- Automatic gate approval or automatic merge decisions without operator input
- Trust of external content without validation
- Automatic deletion/reset of persistent build memory or build rules
- Promotion of external document context into the SYSTEM prompt

### Human boundary

The human remains in the loop for gated decisions. Gates block indefinitely until the operator responds. There is no auto-approve path.

## Data Flow

### 1. Session and transport initialization

The subsystem communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum `16MB` per message

A `ready` message advertises runtime capabilities:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Input acquisition

The subsystem receives:

- plain-language build intent
- credentials:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- repository and document context
- operator responses at gates
- external signals such as PR comments and CI output

All external input is treated as untrusted and validated.

### 3. Scope evaluation

Before implementation, the subsystem runs the scope confidence gate.

Documented behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- If below threshold, the subsystem:
  - shows gaps
  - offers `proceed / answer / cancel`
- If the operator answers gaps, one-shot re-scope is allowed
- No repeated re-scope loop is permitted

This stage defines whether work proceeds with acceptable coverage or requires operator clarification.

### 4. Context assembly

Generation context is assembled from repository and document sources.

Rules:

- Document store is used for generation context
- A specific document may be loaded directly, e.g. `PRODUCT_CONTEXT.md`
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt
- `ContextManager` auto-trims at `30k` tokens
- It preserves:
  - the spec-anchor first turn
  - the last 6 messages

This keeps prompts bounded while preserving the most important anchoring context.

### 5. Generation and consensus

Implementation and tests are generated using two LLM providers in parallel.

`ConsensusEngine` in `src/consensus.py` performs arbitration, with Claude identified as the arbitrating provider in the platform overview.

This phase is bounded by the subsystem’s safety constraints:

- external context is untrusted
- secrets must not appear in logs, errors, or generated code
- generated code is never executed by the agent

### 6. PR execution pipeline

For each PR in the ordered sequence, the subsystem advances through staged work. Per-PR stage checkpoints prevent re-running completed work after a crash.

Pipeline behaviors called out by the TRD:

- self-correction pass
- lint gate
- 20-pass local fix loop maximum
- CI execution
- operator approval gate before merge

Failure handling strategy is selected in `failure_handler.py` by:

- `_choose_strategy(failure_type, attempt, records)`

Decision rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum `20` local attempts, then move on

### 7. GitHub operations

All GitHub activity is mediated by `GitHubTool`.

Explicit rule:

- ALL GitHub ops go through `GitHubTool`
- Never use the GitHub API directly

Write safety rule:

- validate paths before ANY write
- all file writes are path-validated via `path_security.validate_write_path()` before execution

### 8. CI and polling data handling

Operational controls include:

- `403 primary` → exponential backoff:
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints
- CI log output truncated at `8k` chars:
  - `70%` head
  - `30%` tail

These controls constrain external API usage and prevent unbounded context growth from logs.

### 9. UI/status streaming

The subsystem emits structured cards:

`build_card`:
```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

`gate_card`:
```json
{ "gate_type": "...", "options": [], "description": "..." }
```

`build_card` streams to `BuildStreamView`. `gate_card` blocks until operator response.

### 10. Persistent learning output

Two persistent learning artifacts are maintained:

#### Build memory

- File: `workspace/{engineer_id}/build_memory.json`
- Survives fresh installs and thread state wipes
- Written after every successful PR via `build_memory.record_pr()`
- Must not be deleted on clean runs

Purpose: cross-run learning is intentional and persistent.

#### Build rules

- File: `Mac-Docs/build_rules.md`
- Loaded automatically by `DocumentStore`
- Written after each build run when 3+ recurring failure patterns are found
- Must not be deleted on clean runs unless switching to a completely new codebase

Purpose: self-improving coding rules derived from build history.

## Key Invariants

The subsystem enforces the following invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, and no subprocess execution of generated content.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are validated via `path_security.validate_write_path()` before execution.
- Context from external documents is placed in the `USER` prompt, never the `SYSTEM` prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the subsystem must stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional operational invariants from the documented behavior:

- Scope confidence gating occurs at `85`.
- Re-scope after operator clarification is one-shot only.
- Retry behavior is bounded to a maximum of `20` local attempts.
- Polling honors rate-limit semantics and caching requirements.
- Context is automatically trimmed to bounded token limits.

## Failure Modes

### Scope ambiguity or insufficient context

Condition:
- `SCOPE_SYSTEM` returns confidence below `85`

Behavior:
- surface `coverage_gaps`
- present gate options: `proceed`, `answer`, or `cancel`
- allow one re-scope if operator answers gaps
- do not enter an infinite clarification loop

### Auth, crypto, or identity failure

Condition:
- authentication, cryptographic, or identity validation error

Behavior:
- fail closed
- do not silently downgrade behavior
- surface error with context
- do not leak secrets

### Security refusal

Condition:
- a `SECURITY_REFUSAL` output is produced

Behavior:
- stop processing
- gate for operator handling
- log the refusal
- do not bypass by rephrasing

### Invalid or malicious external input

Condition:
- untrusted input from documents, PR comments, or CI output fails validation or is unsafe

Behavior:
- validate before use
- do not promote directly into trusted system context
- surface failures explicitly

### Unknown XPC message type

Condition:
- inbound XPC message type is not recognized

Behavior:
- discard the message
- log the event
- do not throw exception paths from unknown message types

### File write path violation

Condition:
- write target fails `path_security.validate_write_path()`

Behavior:
- do not execute the write
- surface failure explicitly

### GitHub API pressure or throttling

Condition:
- `403 primary` or `429 secondary`

Behavior:
- `403 primary`: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary`: respect `Retry-After`
- use ETag caching on polling endpoints

### Repeated implementation/test failure

Condition:
- iterative fix attempts continue failing

Behavior:
- select strategy via `_choose_strategy(failure_type, attempt, records)`
- escalate based on failure type first, attempt count second
- cap local attempts at `20`
- move on rather than retry indefinitely

### Crash during PR processing

Condition:
- process interruption mid-pipeline

Behavior:
- resume using per-PR stage checkpoints
- do not re-run completed stages

## Dependencies

### Internal components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- build ledger/checkpoint support in `src/build_ledger.py`
- `failure_handler.py` for strategy selection
- `ContextManager` for prompt trimming and message preservation
- `DocumentStore` for loading document context and auto-loading build rules
- `path_security.validate_write_path()` for write-path enforcement
- `build_memory.record_pr()` for persistent build memory updates

### External providers and systems

- Two LLM providers used in parallel for generation
- GitHub, accessed only through `GitHubTool`
- CI systems producing logs and status signals
- XPC transport using the defined wire protocol
- Operator UI surfaces:
  - `BuildStreamView` for streamed `build_card`
  - gate handling for `gate_card`

### Persistent storage

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These stores are operational dependencies because the subsystem relies on persistent cross-run learning and rule accumulation rather than stateless execution.