# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding subsystem that drives an end-to-end build workflow from plain-language intent to gated pull request delivery.

Within the Forge architecture, it:

- accepts a build intent
- decomposes work into an ordered sequence of pull requests
- generates implementation and tests for each PR
- uses two LLM providers in parallel, with Claude arbitrating
- runs a self-correction pass
- runs a lint gate
- runs a bounded 20-pass fix loop
- executes CI
- blocks on operator approval before merge

It is explicitly human-gated. Gates wait indefinitely for operator input, and there is no auto-approve path.

The subsystem also manages persistent learning inputs across runs:

- `build_memory.json` records successful PR outcomes and survives fresh installs and thread state wipes
- `build_rules.md` accumulates self-improving coding rules derived from recurring build failures

CraftedAgent operates as an orchestrated backend with streamed status and gate messages over XPC, GitHub integration through a single tool boundary, document-backed context loading, and per-PR stage checkpoints to prevent duplicate work after crashes.

## Component Boundaries

CraftedAgent includes the following responsibilities and owned components, as identified in the source material:

### Orchestration and routing

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - owns the confidence gate
  - owns `pr_type` routing

### Multi-model generation and arbitration

- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines `GENERATION_SYSTEM`
  - defines `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

### GitHub operations

- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`

All GitHub operations must pass through `GitHubTool`. CraftedAgent must never use the GitHub API directly outside this boundary.

### Build state persistence

- `src/build_ledger.py`
  - referenced as a subsystem file in the Forge architecture context
  - participates in persisted build progress and checkpoint behavior

### Persistent learning artifacts

- `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - persists across fresh installs and thread state wipes
  - must not be automatically deleted on clean runs

- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be automatically deleted on clean runs unless switching to a completely new codebase

### Document-backed context ingestion

CraftedAgent uses `DocumentStore` to load repository and product context for generation, including specific documents such as `PRODUCT_CONTEXT.md`.

### Failure handling strategy selection

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)` selects remediation strategy
  - failure type is primary
  - attempt count is secondary escalation

### Out of scope / external boundaries

The subsystem does not own:

- direct GitHub API access outside `GitHubTool`
- execution of generated code via `eval`, `exec`, or subprocess of generated content
- implicit approval or autonomous gate bypass
- trust of external content without validation
- silent fallback behavior on auth, crypto, or identity failures

## Data Flow

### 1. Session initialization and transport

CraftedAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

On readiness, it emits:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Credential intake

The subsystem receives credentials via:

- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

These credentials are security-sensitive input. Secrets must never appear in logs, error messages, or generated code.

### 3. Intent intake and scope gating

The build intent enters the core loop and is evaluated by the scope confidence stage.

Documented scope behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the subsystem shows gaps
- offers operator options:
  - proceed
  - answer
  - cancel
- allows a one-shot re-scope if the operator provides gap answers
- does not loop indefinitely at this stage

### 4. Context assembly

CraftedAgent loads relevant document context through `DocumentStore`.

Rules for context placement:

- context from external documents goes in the `USER` prompt
- never in the `SYSTEM` prompt

Context sources include:

- repository documents
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- persistent learning inputs:
  - `build_memory.json`
  - `build_rules.md`

All external input is treated as untrusted and validated, including:

- documents
- PR comments
- CI output

### 5. Code and test generation

For each ordered PR:

- implementation and tests are generated
- two LLM providers run in parallel
- Claude arbitrates through the consensus path

Generation behavior is bounded by subsystem-wide safety rules:

- generated code is never executed by the agent
- no `eval`
- no `exec`
- no subprocess execution of generated content

### 6. Correction and local validation loop

After generation, CraftedAgent performs:

- self-correction pass
- lint gate
- bounded fix loop up to 20 local attempts

Failure handling uses `_choose_strategy(failure_type, attempt, records)` with these documented rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Associated automatic context controls:

- `ContextManager` auto-trims at 30k tokens
- preserves:
  - spec-anchor first turn
  - last 6 messages

CI log handling:

- output truncated at 8k chars
- 70% head / 30% tail

### 7. File mutation and repository operations

Before any file write:

- the path must be validated through `path_security.validate_write_path()`

This requirement applies to all file writes before execution.

All GitHub operations route through `GitHubTool`, including PR-related actions.

### 8. Streaming status and gating

Progress is streamed using:

- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`

Blocking operator decisions are emitted using:

- `gate_card`
  - `{ gate_type, options[], description }`

Gate semantics are strict:

- gates block until operator responds
- they wait indefinitely
- there is no auto-approve path

### 9. CI, merge gating, and checkpoint persistence

After local correction and linting:

- CI is executed
- merge remains operator-gated

Per-PR stage checkpoints are persisted so that after a crash the subsystem does not re-run completed work.

### 10. Post-PR and post-run learning updates

After every successful PR:

- `build_memory.record_pr()` writes to:
  - `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `build_rules.md` is updated at:
  - `Mac-Docs/build_rules.md`

These are persistent learning systems and are never cleared automatically.

## Key Invariants

The subsystem enforces the following architectural invariants from Forge context and referenced TRD content:

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Below-threshold scope confidence requires explicit operator choice.
- Re-scope after operator clarification is one-shot, not an autonomous loop.

### Write and repository safety

- All file writes are path-validated through `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`.
- Direct GitHub API usage is disallowed.

### Prompt and context hygiene

- External document context goes in the `USER` prompt only.
- External document context never goes in the `SYSTEM` prompt.
- `DocumentStore` is the document-loading path for generation context.

### Reliability and bounded execution

- Unknown XPC message types are discarded and logged, never raised.
- Per-PR stage checkpoints prevent re-running completed work after crashes.
- The local repair loop is bounded to 20 attempts.
- Build memory and build rules persist across runs and are not automatically cleared.

### Transport and protocol constraints

- XPC payloads are line-delimited JSON.
- XPC messages are nonce-authenticated.
- XPC message size is capped at 16 MB.

## Failure Modes

### Scope uncertainty

Condition:

- `SCOPE_SYSTEM` returns confidence below 85

Behavior:

- subsystem surfaces `coverage_gaps`
- operator is offered:
  - proceed
  - answer
  - cancel
- if operator answers gaps, one re-scope pass is allowed
- no indefinite scope-looping

### Auth, crypto, or identity failure

Condition:

- any auth, crypto, or identity error

Behavior:

- fail closed
- do not silently degrade
- surface error with context
- do not continue on implicit fallback paths

### Security refusal

Condition:

- model output produces `SECURITY_REFUSAL`

Behavior:

- stop
- gate
- log
- never attempt bypass by prompt rephrasing

### XPC protocol anomalies

Condition:

- unknown message type

Behavior:

- discard
- log
- do not raise exception

Condition:

- oversized or invalid message relative to protocol constraints

Behavior:

- constrained by line-delimited JSON / nonce-authenticated / 16 MB maximum protocol expectations

### File write safety failure

Condition:

- write path fails `path_security.validate_write_path()`

Behavior:

- write must not execute

### Generation and repair failures

Condition:

- generated changes fail tests, lint, imports, runtime, or assertions

Behavior:

- handled through `_choose_strategy(failure_type, attempt, records)`

Specific strategy rules:

- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → escalate to `nuclear` every 3rd attempt
- stop after 20 local attempts

This subsystem explicitly avoids infinite retry behavior.

### API throttling and polling pressure

Condition:

- GitHub or related API throttling

Behavior:

- `403 primary` → exponential backoff:
  - 2s
  - 4s
  - 8s
  - 16s
  - 32s
  - 64s
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints

### Crash or restart during a PR

Condition:

- agent crash or restart mid-stage

Behavior:

- per-PR stage checkpoints prevent re-running already completed work

### Context overflow and oversized CI output

Condition:

- context grows too large

Behavior:

- `ContextManager` auto-trims at 30k tokens
- preserves spec-anchor first turn and last 6 messages

Condition:

- CI logs are too large

Behavior:

- truncate to 8k chars
- retain 70% head / 30% tail

## Dependencies

### Internal subsystem files

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - `pr_type` routing

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

- `src/build_ledger.py`

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

### Persistent data and document dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- `DocumentStore`
- repository documents including targeted loads such as `PRODUCT_CONTEXT.md`

### Protocol dependencies

- XPC transport
- line-delimited JSON wire format
- nonce authentication
- message types:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External service dependencies

- Anthropic provider
- OpenAI provider
- GitHub, but only through `GitHubTool`

### UI integration dependencies

- `BuildStreamView` as the sink for streamed `build_card` updates

### Safety and utility dependencies

- `path_security.validate_write_path()`
- `ContextManager` token trimming and retention behavior