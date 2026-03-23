# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the Forge subsystem responsible for orchestrating end-to-end AI-assisted software delivery for a single build intent on macOS.

At a high level, it:

1. Accepts a plain-language build intent and repository context.
2. Performs scope analysis and confidence gating before implementation.
3. Decomposes work into an ordered sequence of pull requests.
4. Retrieves relevant repository and document context, including persistent build memory and build rules.
5. Generates code and tests using multiple LLM providers in parallel.
6. Arbitrates generation output through a consensus layer.
7. Applies self-correction, linting, and bounded fix loops.
8. Executes CI and interprets failures.
9. Presents progress and gate decisions to the operator over XPC/UI.
10. Waits indefinitely for explicit operator approval before merge or continuation.
11. Records durable learning artifacts after successful PRs/builds.

This subsystem is orchestration-heavy. It does not directly execute generated code as instructions, does not bypass operator gates, and does not perform ad hoc API access outside approved tool boundaries.

## Component Boundaries

### In Scope

The subsystem includes the following functional responsibilities:

- **Build orchestration**
  - Sequencing stages for scope, planning, PR generation, validation, CI, and merge gating.
  - Per-PR checkpointing to prevent re-running completed stages after crashes.

- **Scope confidence gating**
  - Running scope analysis.
  - Enforcing `_CONFIDENCE_THRESHOLD = 85`.
  - Surfacing `coverage_gaps` to the operator.
  - Allowing one re-scope pass if the operator answers gaps.
  - Preventing uncontrolled re-scope loops.

- **LLM generation orchestration**
  - Parallel generation through two providers.
  - Consensus/arbitration of outputs.
  - Self-correction and bounded iterative repair.

- **Context assembly**
  - Loading trusted local repository context.
  - Loading external document context through the DocumentStore.
  - Injecting external document content only into the USER prompt.
  - Loading persistent learning artifacts:
    - `workspace/{engineer_id}/build_memory.json`
    - `Mac-Docs/build_rules.md`

- **GitHub workflow execution**
  - All repository/PR operations through `GitHubTool`.
  - Webhook/polling integration as exposed by approved GitHub tooling.
  - PR creation, status observation, and merge flow subject to operator gating.

- **Operator interaction**
  - Streaming `build_card` updates to UI.
  - Emitting `gate_card` decisions that block indefinitely until operator input.
  - Never auto-approving continuation or merge.

- **Failure handling**
  - Strategy selection based on failure type and attempt count.
  - 20-pass bounded local fix loop.
  - Retry/backoff behavior for external API limits.
  - Context trimming and CI log truncation.

### Explicitly Out of Scope

The subsystem does **not** own or permit:

- Direct GitHub API access outside `GitHubTool`.
- Silent degradation on auth, crypto, or identity failures.
- Execution of generated code as agent instructions:
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- Automatic approval of gates or merges.
- Use of external document context in the SYSTEM prompt.
- Unvalidated file writes.
- Automatic deletion/clearing of build memory or build rules.
- Raising exceptions for unknown XPC message types; they must be discarded and logged.

### Principal Implementation Units

Based on the referenced repository structure:

- `src/build_director.py`
  - Primary pipeline orchestrator.
  - PR type routing.
  - Confidence gate handling.

- `src/consensus.py`
  - Consensus engine.
  - Generation system prompts and provider arbitration.

- `src/github_tools.py`
  - `GitHubTool` for all GitHub operations.
  - `WebhookReceiver` for GitHub event intake.

- `src/build_ledger.py`
  - Per-PR stage checkpointing and progress persistence.

Other referenced behavior is contractually part of this subsystem even if implemented in adjacent modules, including failure handling, path security validation, document retrieval, and context management.

## Data Flow

### 1. Session Establishment

The subsystem communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

Expected startup/health payload:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Input Intake

Primary inputs:

- plain-language build intent
- repository state
- operator responses
- credentials:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`
- external documents and repository docs
- PR comments, CI output, webhook payloads

All external input is treated as untrusted and validated before use.

### 3. Scope Analysis and Gate

The build director performs scope analysis and obtains:

- `confidence` in range `0–100`
- `coverage_gaps`

If confidence is below `85`:

- the subsystem emits a gate describing the gaps
- operator options are proceed / answer / cancel
- if the operator answers gaps, exactly one re-scope pass is allowed
- there is no open-ended clarification loop

This gate is blocking and waits indefinitely.

### 4. Context Assembly

Context sources are combined for generation:

- repository-local source context
- selected docs from the DocumentStore
- specific docs such as `PRODUCT_CONTEXT.md` when requested
- persistent artifacts:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

Rules enforced during assembly:

- external document content goes in the USER prompt, never SYSTEM
- secrets are excluded from prompts, logs, errors, and generated code
- ContextManager auto-trims at 30k tokens
- retained context priority:
  - spec-anchor first turn
  - last 6 messages

### 5. Multi-Provider Generation and Consensus

Generation is run through multiple LLM providers in parallel. The consensus engine:

- applies generation system prompts
- compares outputs
- selects/arbitrates a result
- supports Swift/UI generation variants as configured in `src/consensus.py`

The output then flows into:

- self-correction pass
- lint gate
- bounded repair loop

### 6. File Mutation and Repository Changes

Any file write must be validated through:

- `path_security.validate_write_path()`

This is mandatory before execution of any write.

Repository and PR operations occur only through `GitHubTool`. No direct GitHub API access is permitted.

### 7. Validation, Repair, and CI

Validation path includes:

- self-correction
- lint gate
- up to 20 local fix attempts
- CI execution and result parsing

Failure strategy selection follows `failure_handler.py:_choose_strategy(failure_type, attempt, records)`:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- stop local attempts after 20, then move on/escalate

CI log handling:

- output truncated to 8k chars
- 70% head / 30% tail

### 8. Operator Gate and Merge

Progress is streamed via:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": ... }
```

Blocking decisions are emitted via:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

Gates wait indefinitely for operator input. There is no auto-approve path.

### 9. Persistent Learning Writeback

After every successful PR:

- `build_memory.record_pr()` writes to:
  - `workspace/{engineer_id}/build_memory.json`

After build runs with 3 or more recurring failure patterns:

- `build_rules.md` is updated at:
  - `Mac-Docs/build_rules.md`

These are persistent learning systems and are never cleared automatically.

## Key Invariants

The subsystem must preserve the following invariants:

- **Fail closed on auth, crypto, and identity errors**
  - Never degrade silently.
  - Do not continue with partial identity or credential state.

- **No silent failure paths**
  - Every error surfaces with context.
  - Errors must be actionable and attributable.

- **Secrets never appear**
  - Not in logs.
  - Not in error messages.
  - Not in generated code.
  - Not in prompts beyond required secure use.

- **All external input is untrusted**
  - Includes documents, PR comments, CI output, webhook payloads, and operator-provided free text.
  - Must be validated/sanitized before use.

- **Generated code is never executed by the agent**
  - No `eval`.
  - No `exec`.
  - No subprocess invocation of generated content.

- **Operator gates are mandatory**
  - Gates block indefinitely.
  - No auto-approve.
  - No implicit continuation on timeout.

- **All file writes are path-validated**
  - `path_security.validate_write_path()` is required before any write executes.

- **Prompt isolation for untrusted documents**
  - External document context belongs only in USER prompts.
  - Never place external document text in SYSTEM prompts.

- **Security refusals are terminal within the current action**
  - `SECURITY_REFUSAL` is not bypassed by rephrasing.
  - Stop, gate, and log.

- **XPC robustness**
  - Unknown message types are discarded and logged.
  - They do not raise exceptions or crash the agent.

- **Crash recovery is stage-aware**
  - Per-PR stage checkpoints prevent repeating completed work.

- **Persistent learning is durable**
  - Build memory and build rules are not automatically cleared.
  - Cross-run learning is intentional subsystem behavior.

- **Retry behavior is bounded**
  - Local repair loops stop after 20 attempts.
  - API retries follow explicit backoff/headers, not infinite retry.

- **Polling efficiency is enforced**
  - ETag caching is used on all polling endpoints.

## Failure Modes

### Scope Confidence Failure

Condition:
- Scope confidence `< 85`

Behavior:
- Surface `coverage_gaps`
- Gate the operator with proceed/answer/cancel
- Allow one re-scope if answers are provided
- Do not loop indefinitely

### Auth / Crypto / Identity Failure

Condition:
- Credential invalidity, missing identity, nonce/authentication mismatch, or related integrity failure

Behavior:
- Fail closed
- Stop the affected operation
- Surface contextual error
- Do not continue in degraded mode

### XPC Protocol Failure

Condition:
- Unknown message type, malformed line-delimited JSON, oversized payload, nonce/auth issue

Behavior:
- Unknown type: discard and log
- Protocol/auth/integrity failures: surface error and stop affected flow
- Never convert unknown messages into uncaught exceptions

### Path Validation Failure

Condition:
- `path_security.validate_write_path()` rejects a target path

Behavior:
- Abort the write
- Surface explicit validation failure
- Do not attempt alternate unvalidated write paths

### GitHub Operation Failure

Condition:
- API errors, webhook issues, rate limiting, permission denial

Behavior:
- Route through `GitHubTool` handling only
- `403` primary rate/abuse style responses: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary limits: respect `Retry-After`
- Use ETag caching on polling endpoints
- Surface terminal failures with context

### Generation or Consensus Failure

Condition:
- Provider failure, arbitration failure, malformed model output, or safety refusal

Behavior:
- Surface the error with context
- If `SECURITY_REFUSAL`, stop, gate, and log
- Do not bypass refusal by prompt rephrasing
- Continue only through explicit operator-controlled workflow where permitted

### Validation / Repair Loop Exhaustion

Condition:
- Local repair attempts reach 20 without success

Behavior:
- Stop retrying
- Surface bounded-loop exhaustion
- Move to next escalation path or operator decision
- Never retry indefinitely

### Test / Runtime Failure Handling

Condition:
- Failure observed in lint/test/runtime/import/assertion phases

Behavior:
- Use `_choose_strategy(failure_type, attempt, records)`
- `assertion_error` → `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt

### Context Overflow

Condition:
- Prompt/context exceeds token budget

Behavior:
- Auto-trim at 30k tokens
- Preserve spec-anchor first turn and last 6 messages
- No manual intervention required for ordinary overflow handling

### CI Log Volume Failure

Condition:
- CI output too large for efficient prompt/UI handling

Behavior:
- Truncate to 8k chars
- Preserve 70% head / 30% tail
- Prevent unbounded context growth while retaining likely failure signal

### Crash / Restart During PR Processing

Condition:
- Process interruption mid-stage

Behavior:
- Resume from per-PR stage checkpoints
- Do not re-run completed stages
- Preserve ledger state and learning artifacts

## Dependencies

### Internal Dependencies

- **BuildDirector** (`src/build_director.py`)
  - Pipeline orchestration
  - Scope gate enforcement
  - PR routing

- **ConsensusEngine** (`src/consensus.py`)
  - Multi-provider generation arbitration
  - System prompt definitions

- **GitHubTool / WebhookReceiver** (`src/github_tools.py`)
  - Sole interface for GitHub operations

- **Build ledger** (`src/build_ledger.py`)
  - Stage checkpoint persistence
  - Crash recovery support

- **DocumentStore**
  - Document loading
  - Status reporting via `doc_status`
  - Automatic loading of `build_rules.md`

- **ContextManager**
  - Token trimming
  - Preservation policy for retained turns

- **failure_handler.py**
  - Failure classification and strategy escalation

- **path_security**
  - Mandatory write-path validation

### External Dependencies

- **LLM providers**
  - Anthropic
  - OpenAI

- **GitHub**
  - Repository, PR, status, and webhook integration exclusively via `GitHubTool`

- **XPC transport**
  - Native macOS integration
  - Line-delimited JSON protocol
  - Nonce-authenticated messaging

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - Cross-run PR learning
  - Updated after every successful PR

- `Mac-Docs/build_rules.md`
  - Cross-run failure-pattern-derived coding rules
  - Updated when recurring failure thresholds are met

These persistence artifacts are required subsystem inputs on subsequent runs and are intentionally durable across fresh installs, thread state wipes, and clean executions.