# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the Forge subsystem responsible for converting a human build intent into a gated, auditable sequence of implementation pull requests for a native macOS coding workflow.

At a high level, the subsystem:

1. Accepts a plain-language build request from an operator.
2. Scopes the request and computes confidence/coverage gaps.
3. Decomposes accepted scope into an ordered PR plan.
4. Retrieves supporting context from the document store and persistent build-learning artifacts.
5. Generates implementation and tests using multiple LLM providers in parallel.
6. Arbitrates generation through a consensus layer.
7. Runs self-correction, linting, and bounded local fix loops.
8. Executes CI and summarizes results.
9. Blocks on explicit operator approval at required gates.
10. Performs GitHub operations only through the platform GitHub abstraction.
11. Persists per-PR checkpoints and cross-run learning artifacts.

The subsystem is intentionally human-gated. It does not auto-approve scope, merge, or bypass security refusals. It is designed to fail closed on security-sensitive paths and to surface all failures with context.

## Component Boundaries

### Inside this subsystem

The CraftedDevAgent subsystem owns:

- Build orchestration and stage sequencing.
- Scope-confidence evaluation and gating.
- PR decomposition and per-PR execution order.
- LLM generation orchestration across providers.
- Consensus/arbitration logic for generated outputs.
- Retrieval of contextual documents for generation.
- Use and persistence of build memory and build rules.
- Local correction flow:
  - self-correction pass
  - lint gate
  - bounded fix loop up to 20 attempts
- CI invocation/result handling within agent policy.
- Operator gate presentation and indefinite wait behavior.
- Per-PR stage checkpoint persistence for crash recovery.
- Streaming build status via protocol cards.
- Enforcement of repository write-path validation before file mutation.

Primary implementation anchors from the repository context:

- `src/build_director.py`
  - BuildPipeline orchestration
  - confidence gate
  - PR-type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - stage/checkpoint persistence

### Outside this subsystem

The subsystem does **not** own:

- Direct UI rendering logic, beyond emitting protocol messages such as `build_card` and `gate_card`.
- Direct GitHub API access outside `GitHubTool`.
- Execution of generated code via `eval`, `exec`, or subprocess invocation of generated content.
- Authentication or credential issuance mechanisms.
- The underlying XPC transport implementation, beyond conforming to its wire contract.
- Arbitrary document trust decisions; all external content remains untrusted input.
- Automatic clearing of persistent learning artifacts.

### External interfaces

The subsystem interacts with:

- Operator-facing clients over XPC using line-delimited JSON messages.
- LLM providers via provider adapters/orchestrators.
- GitHub exclusively through `GitHubTool`.
- DocumentStore for contextual retrieval and document loading.
- Persistent storage for checkpoints and learning artifacts.

Relevant protocol payloads include:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

## Data Flow

### 1. Session initialization

On startup, the subsystem participates in the XPC session handshake and emits/consumes protocol messages according to the platform wire format:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

A `ready` message communicates capability and document-store status to the client.

Unknown XPC message types are not treated as exceptional control flow. They are discarded and logged.

### 2. Build intent intake

The operator supplies build intent and supporting context. External inputs may include:

- natural-language request text
- uploaded or indexed documents
- PR comments
- CI output
- repository state metadata

All such inputs are treated as untrusted and must be validated/sanitized before use.

Per platform rule, context from external documents is placed in the **USER** prompt only, never the **SYSTEM** prompt.

### 3. Scope evaluation and gate

The subsystem performs a scope-confidence pass before implementation.

From the documented core loop:

- `SCOPE_SYSTEM` returns:
  - `confidence` in range `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

Behavior:

- If confidence is at or above threshold, the build may proceed.
- If below threshold, the subsystem presents the gaps and offers:
  - proceed
  - answer
  - cancel
- If the operator answers the gaps, the subsystem performs a one-shot re-scope.
- There is no infinite clarification loop.

This preserves operator control while preventing uncontrolled autonomous expansion of scope.

### 4. PR planning and stage execution

Accepted scope is decomposed into an ordered sequence of pull requests. Each PR is processed through staged execution with checkpoint persistence.

Per-PR stage checkpoints prevent re-running completed work after a crash. Recovery resumes from the last persisted safe stage rather than replaying already completed work.

### 5. Context assembly

For each PR, the subsystem assembles generation context from:

- repository-local source state
- document store retrieval
- specific loaded documents where requested
- persistent build memory
- persistent build rules

Document store usage is a primary source of generation context. Build learning artifacts are explicitly persistent:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread-state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - never auto-deleted on clean runs
- `Mac-Docs/build_rules.md`
  - loaded automatically by DocumentStore
  - updated after build runs when at least 3 recurring failure patterns are found
  - not auto-deleted except when intentionally switching to a completely new codebase

### 6. Parallel generation and consensus

Implementation/test generation is performed using two LLM providers in parallel. The consensus layer arbitrates outputs.

`ConsensusEngine` is the subsystem authority for combining or selecting candidate generations. System prompt assets for generation are maintained in `src/consensus.py`.

Security-sensitive generation behavior includes:

- no execution of generated content
- no secret emission into logs, error messages, or generated code
- no bypass of `SECURITY_REFUSAL`; refusal causes stop/gate/log behavior

### 7. Write preparation and repository mutation

Before any file write occurs, the target path must be validated through:

- `path_security.validate_write_path()`

This is a hard invariant for all write operations. The subsystem must not write to repository or workspace paths that have not passed validation.

All GitHub operations go through `GitHubTool`. The subsystem never uses the GitHub API directly.

### 8. Correction, lint, and bounded fix loop

After initial generation, the subsystem applies local quality/correction stages:

- self-correction pass
- lint gate
- local fix loop with a maximum of 20 attempts

Failure-strategy selection is controlled by `failure_handler.py:_choose_strategy(failure_type, attempt, records)` with these documented rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

### 9. CI and result summarization

The subsystem executes CI as part of validation. CI output is treated as untrusted input and is truncated automatically for context control:

- max 8k chars
- approximately 70% head / 30% tail

Polling/network behavior follows documented rate-limit handling:

- `403` primary rate limits: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate limits: respect `Retry-After`
- ETag caching on all polling endpoints

### 10. Operator gates and merge control

At required decision points, the subsystem emits `gate_card` messages and blocks indefinitely until the operator responds.

This includes approval-sensitive transitions such as proceeding past uncertain scope or approving merge-relevant actions. There is no auto-approve path.

### 11. Build stream and status reporting

The subsystem streams progress to the UI via `build_card` messages containing:

- `card_type`
- `stage`
- `content`
- `progress`

Document ingestion/embedding status may be surfaced via `doc_status`.

## Key Invariants

The following invariants are mandatory for this subsystem:

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including documents, PR comments, and CI output.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` is terminal for the attempted action: stop, gate, and log; rephrasing does not bypass it.

### Operator control

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists for scope, merge, or security-sensitive decisions.
- Low-confidence scope does not proceed silently; it must gate with explicit options.

### Repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; no direct GitHub API usage.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Determinism and recovery

- Per-PR stage checkpoints prevent replay of completed work after crash/restart.
- Retry loops are bounded; local fix attempts stop after 20 attempts.
- Build memory and build rules are persistent learning systems and are never automatically cleared.

### Prompt/context discipline

- External document context goes into the USER prompt, never the SYSTEM prompt.
- ContextManager auto-trims at 30k tokens.
- The first spec-anchor turn and last 6 messages are preserved during trimming.

## Failure Modes

### Scope uncertainty

**Condition**
- Scope confidence below threshold (`< 85`) with unresolved coverage gaps.

**Handling**
- Present gaps to operator.
- Offer `proceed`, `answer`, or `cancel`.
- Allow one re-scope if operator provides answers.
- Do not loop indefinitely.

### LLM disagreement or low-quality generation

**Condition**
- Parallel providers return divergent or insufficient outputs.

**Handling**
- Route through `ConsensusEngine`.
- Continue through self-correction/lint/fix stages if candidate output is admissible.
- Surface failure with context if no acceptable result can be produced.

### Security refusal

**Condition**
- Model or policy layer emits `SECURITY_REFUSAL`.

**Handling**
- Stop the attempted action immediately.
- Gate/log; do not retry by paraphrase.
- Do not downgrade refusal into best-effort behavior.

### Invalid write target

**Condition**
- Path validation fails for a pending file write.

**Handling**
- Refuse the write.
- Surface explicit error context.
- Do not attempt alternate unvalidated paths.

### Auth, crypto, or identity failure

**Condition**
- Credential invalidity, missing identity, nonce/authentication mismatch, or related security fault.

**Handling**
- Fail closed.
- Do not continue in degraded mode.
- Surface explicit failure context without exposing secrets.

### XPC protocol anomalies

**Condition**
- Unknown message types or malformed/oversized payloads.

**Handling**
- Unknown message types are discarded and logged.
- Wire-contract violations are treated as protocol errors with surfaced context.
- No exception-based crash path for merely unknown message kinds.

### GitHub rate limiting or polling inefficiency

**Condition**
- `403` primary rate limit or `429` secondary rate limit.

**Handling**
- Primary: exponential backoff up to 64s.
- Secondary: respect `Retry-After`.
- Use ETag caching on polling endpoints.

### Repeated local correction failure

**Condition**
- Tests/lint/runtime issues persist through iterative repair.

**Handling**
- Select strategy using failure type first, attempt count second.
- Escalate according to documented policy.
- Stop after 20 attempts; do not retry indefinitely.
- Move control to the next higher-level decision path with visible failure context.

### Crash or restart mid-build

**Condition**
- Agent crash, process restart, or interrupted execution during PR processing.

**Handling**
- Resume from per-PR stage checkpoints.
- Do not repeat stages already marked complete.

### Context overflow

**Condition**
- Prompt/context growth exceeds operating budget.

**Handling**
- Auto-trim at 30k tokens.
- Preserve spec anchor and most recent conversational state.
- Truncate CI logs automatically to bounded length.

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - primary build orchestration
  - scope gate
  - PR routing/staging
- `src/consensus.py`
  - consensus arbitration
  - generation prompt definitions
- `src/github_tools.py`
  - `GitHubTool`
  - webhook integration
- `src/build_ledger.py`
  - stage ledger/checkpoint persistence
- `failure_handler.py`
  - repair-strategy selection logic
- `path_security.validate_write_path()`
  - mandatory write-path validation

### Platform services

- XPC transport using Forge wire protocol
- DocumentStore
- BuildStreamView consumer of `build_card`
- persistent workspace storage
- Mac-Docs shared document space

### External systems

- LLM providers:
  - Anthropic
  - OpenAI
- GitHub, mediated only through `GitHubTool`
- CI systems and their emitted logs/output

### Persistent artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- per-PR checkpoint/ledger state

### Credentials and identity inputs

Via protocol `credentials` payload:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

These inputs are security-sensitive and must never be logged or echoed.