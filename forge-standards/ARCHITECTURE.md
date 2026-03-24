# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated sequence of pull requests and driving each PR through generation, correction, validation, CI, and merge preparation.

Within the Forge platform, this subsystem:

- decomposes build intent into an ordered PR sequence
- performs scope assessment and confidence gating before implementation work
- generates implementation and tests using two LLM providers in parallel, with Claude arbitrating
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI and presents results
- blocks on operator gates before merge or continuation
- persists per-PR checkpoints to avoid replaying completed work after crashes
- records persistent learning artifacts:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

The subsystem operates under strict security and reliability constraints:

- all external input is untrusted and validated
- generated code is never executed by the agent
- all file writes are path-validated before execution
- auth, crypto, and identity failures fail closed
- operator approval is mandatory; no auto-approve path exists

Primary implementation anchors named in the source material are:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpoint persistence

## Component Boundaries

ForgeAgent owns orchestration and enforcement of the build workflow, but does not own arbitrary execution, direct external API usage outside approved tools, or silent fallback behavior.

### In scope

- Build pipeline orchestration via `BuildPipeline`
- Scope confidence evaluation and threshold gating
- Consensus-based code/test generation
- Prompt construction using approved context placement rules
- Build card and gate card production for UI streaming
- Use of document context for generation
- Use and persistence of build memory and build rules
- GitHub operations through `GitHubTool`
- Per-PR checkpointing and crash recovery
- Failure handling strategy selection and bounded retry behavior
- CI result intake and truncation for context safety

### Out of scope

- Direct GitHub API access outside `GitHubTool`
- Execution of generated code by the agent (`eval`, `exec`, subprocess of generated content)
- Automatic approval or merge without operator input
- Automatic clearing of persistent learning stores
- Promotion of external document context into the system prompt
- Raising exceptions for unknown XPC message types

### Boundary rules

- **GitHub boundary:** all GitHub operations must go through `GitHubTool`; direct GitHub API use is forbidden.
- **Filesystem boundary:** any write must be validated with `path_security.validate_write_path()` before execution.
- **Prompting boundary:** context from external documents belongs in the `USER` prompt only, never the `SYSTEM` prompt.
- **Security boundary:** `SECURITY_REFUSAL` is terminal for the current path; it is not bypassed by rephrasing.
- **Operator boundary:** gate cards block indefinitely until the operator responds.
- **Transport boundary:** XPC uses line-delimited JSON with nonce authentication and a 16 MB maximum message size.

## Data Flow

### 1. Session initialization

ForgeAgent communicates over XPC using line-delimited JSON, nonce-authenticated messages, with a maximum size of 16 MB per message.

A `ready` message advertises:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Credentials are provided as:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Build intent to scope gate

A plain-language build intent enters the build pipeline.

The subsystem performs scope analysis using the documented scope-confidence mechanism:

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold, ForgeAgent:

- shows the coverage gaps
- offers operator choices:
  - proceed
  - answer
  - cancel

If the operator provides gap answers, ForgeAgent performs a one-shot re-scope. There is explicitly no iterative loop beyond that single re-scope pass.

### 3. Context assembly

Generation context is assembled from:

- repository context
- document store content
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- persistent build memory from `workspace/{engineer_id}/build_memory.json`
- persistent build rules from `Mac-Docs/build_rules.md`

Context handling constraints:

- external document content is treated as untrusted input
- external document context is placed in the `USER` prompt, never the `SYSTEM` prompt
- `ContextManager` auto-trims at 30k tokens
- it preserves:
  - the spec-anchor first turn
  - the last 6 messages

### 4. Consensus generation

ForgeAgent uses two LLM providers in parallel for implementation and test generation, with Claude arbitrating. The implementation anchor is `ConsensusEngine` in `src/consensus.py`.

Named prompt assets include:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

Generated outputs are code artifacts only; the subsystem does not execute generated code directly.

### 5. PR-stage orchestration

For each PR in the ordered sequence, ForgeAgent runs the core loop through staged orchestration in `BuildPipeline`. The documented platform behavior includes:

- generation
- self-correction pass
- lint gate
- 20-pass fix loop
- CI execution
- operator gate before merge

Per-PR stage checkpoints are persisted so that after a crash the subsystem does not re-run completed work.

### 6. GitHub and repository operations

All GitHub interactions are routed through `GitHubTool`. Webhook handling is anchored by `WebhookReceiver`.

Repository modifications are subject to path validation before any write. This applies universally to file writes and prevents writes outside approved locations.

### 7. UI/event streaming

Progress and decisions are surfaced through structured cards:

- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator response

Document ingestion and embedding progress can be surfaced as:

- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### 8. Failure handling and bounded recovery

Local repair behavior is strategy-driven. In `failure_handler.py`, `_choose_strategy(failure_type, attempt, records)` selects the next action with these rules:

- failure type is the primary signal
- attempt count is the secondary escalation signal
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — maximum 20 local attempts, then move on

Associated transport and polling resilience rules:

- HTTP `403` on primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- HTTP `429` on secondary: respect `Retry-After`
- ETag caching on all polling endpoints

CI log output is truncated at 8k characters with a 70% head / 30% tail split.

### 9. Persistent learning update

Persistent learning artifacts are updated as follows:

- `build_memory.json`
  - location: `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - survives fresh installs and thread state wipes
  - must not be deleted on clean runs
- `build_rules.md`
  - location: `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The Forge context defines the following subsystem invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, and no subprocess of generated content.
- Gates wait indefinitely for operator input; there is no auto-approve path.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional operational constraints from the TRD content:

- scope gating threshold is fixed at `_CONFIDENCE_THRESHOLD = 85`
- below-threshold re-scoping is one-shot only
- retries are bounded to 20 local attempts
- context is auto-trimmed at 30k tokens while preserving the spec anchor and last 6 turns
- CI logs are truncated automatically to 8k characters

## Failure Modes

### Scope uncertainty

If scope confidence is below 85, the subsystem does not silently proceed as if complete. It surfaces `coverage_gaps` and requires operator choice to proceed, answer gaps, or cancel. Only one re-scope pass is permitted after operator answers.

### Auth, crypto, or identity errors

These fail closed. The subsystem does not fall back to degraded or anonymous behavior.

### Security refusal

If a `SECURITY_REFUSAL` occurs, the subsystem stops the current path, gates, and logs. Rephrasing or prompt variation is not used to bypass the refusal.

### Invalid or unsafe write targets

Any attempted file write outside allowed validated paths must be blocked by `path_security.validate_write_path()` prior to execution.

### Unknown XPC message types

Unknown message types are discarded and logged. They are not escalated as exceptions.

### Generation or repair failure

Local remediation follows `_choose_strategy(failure_type, attempt, records)` and is bounded:

- strategy depends first on failure type
- escalation depends second on attempt count
- local attempts stop after 20

This prevents infinite retry loops.

### GitHub/API throttling or access issues

The subsystem applies documented recovery behavior:

- `403` primary: exponential backoff up to 64 seconds
- `429` secondary: obey `Retry-After`
- polling uses ETag caching

### Oversized or noisy context

The subsystem automatically trims context at 30k tokens and truncates CI logs to 8k characters, reducing overflow risk while preserving the defined retained segments.

### Crash during PR execution

Per-PR stage checkpoints in the build ledger prevent re-running already completed stages after restart.

## Dependencies

The TRD content identifies the following direct subsystem dependencies and integration surfaces.

### Internal components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- `GitHubTool` in `src/github_tools.py`
- `WebhookReceiver` in `src/github_tools.py`
- build ledger in `src/build_ledger.py`
- `DocumentStore`
- `ContextManager`
- failure strategy logic in `failure_handler.py`
- `path_security.validate_write_path()`

### Persistent data

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External providers and services

- Anthropic provider
- OpenAI provider
- GitHub, exclusively through `GitHubTool`

### Transport/UI protocol

- XPC line-delimited JSON transport with nonce authentication
- `ready` message
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`
- `BuildStreamView`

### Inputs treated as untrusted

- external documents
- PR comments
- CI output

These dependencies are governed by the subsystem invariants above and may not be used in ways that violate the enforced boundaries.