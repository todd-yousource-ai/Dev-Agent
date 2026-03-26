# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent that converts a plain-language build intent into an operator-gated sequence of pull requests and drives each PR through generation, validation, correction, CI, and merge approval.

At a subsystem level, it is responsible for:

- decomposing build intent into an ordered PR plan
- routing work through staged build orchestration
- generating implementation and tests using two LLM providers in parallel
- arbitrating generation via Claude-based consensus
- applying a self-correction pass, lint gate, and bounded local fix loop
- executing CI and surfacing results
- blocking on explicit operator approval before merge
- persisting per-PR checkpoints to avoid re-running completed work after crashes
- preserving cross-run learning via persistent build memory and build rules
- presenting progress and gate state over XPC to the macOS UI

This subsystem is explicitly human-gated. Gates wait indefinitely for operator input and are never auto-approved.

## Component Boundaries

The subsystem boundary is defined by the files and responsibilities called out in the Forge context.

### In-scope components

#### `src/build_director.py`
Owns build pipeline orchestration, including:

- staged execution of the build pipeline
- confidence gate handling
- `pr_type` routing

It is the primary coordinator for moving a build through scope analysis, PR sequencing, generation, validation, and approval gates.

#### `src/consensus.py`
Owns consensus-driven generation behavior, including:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

It provides the parallel multi-provider generation and arbitration path used to create implementation and test changes.

#### `src/github_tools.py`
Owns all GitHub interactions through:

- `GitHubTool`
- `WebhookReceiver`

This is the only allowed interface for GitHub operations. Direct GitHub API usage is out of bounds.

#### `src/build_ledger.py`
Owns stage persistence and recovery behavior implied by:

- per-PR stage checkpoints
- crash-safe prevention of re-running already completed work

### Persistent knowledge assets

#### `workspace/{engineer_id}/build_memory.json`
Persistent build memory store.

Characteristics:

- survives fresh installs
- survives thread state wipes
- written after every successful PR via `build_memory.record_pr()`
- intentionally not deleted on clean runs

This file is part of the subsystem’s long-lived learning behavior.

#### `Mac-Docs/build_rules.md`
Persistent self-improving rule set.

Characteristics:

- loaded by `DocumentStore` automatically
- written after each build run when 3 or more recurring failure patterns are found
- intentionally not deleted on clean runs unless switching to a completely new codebase

### Out-of-scope behavior

The subsystem does not:

- execute generated code via `eval`, `exec`, or subprocess execution of generated content
- bypass operator gates
- place external document context into the system prompt
- perform direct GitHub API calls outside `GitHubTool`
- write files without path validation
- silently ignore auth, crypto, identity, or security refusal conditions

## Data Flow

The subsystem data flow is staged and checkpointed.

### 1. Session initialization over XPC

The subsystem communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum message size of 16 MB

Initialization includes a `ready` message with:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent intake and scope evaluation

A plain-language build intent enters the build pipeline.

Scope evaluation uses the documented confidence gate behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold, the subsystem:

- shows coverage gaps
- offers operator choices:
  - proceed
  - answer
  - cancel

If the operator provides gap answers, the subsystem performs a one-shot re-scope. It does not loop indefinitely.

### 3. Context assembly

Generation context may include repository and document context via the document store.

Rules for context handling:

- external documents are untrusted input and must be validated
- context from external documents goes in the USER prompt, never the SYSTEM prompt
- `build_rules.md` is loaded automatically by `DocumentStore`
- build memory persists separately and informs cross-run learning

Context handling is constrained by `ContextManager` behavior:

- auto-trims at 30k tokens
- preserves the spec-anchor first turn
- preserves the last 6 messages

### 4. PR-oriented build orchestration

The build is decomposed into an ordered sequence of pull requests.

For each PR, the orchestrator executes staged work and persists checkpoints so that after a crash, completed stages are not repeated.

### 5. Parallel generation and consensus

Implementation and tests are generated using two LLM providers in parallel.

`ConsensusEngine` arbitrates the outputs, with Claude serving as the arbitration authority per the platform overview.

This stage uses the generation system prompts defined in `src/consensus.py`, including the Swift/UI variant where applicable.

### 6. Validation and bounded repair

After generation, the subsystem performs:

- a self-correction pass
- a lint gate
- a bounded fix loop of up to 20 local attempts

Failure handling follows the documented strategy selection rules in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- primary signal: `failure_type`
- secondary signal: `attempt`

Specific routing rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely; maximum 20 local attempts, then move on

### 7. CI execution and output shaping

The subsystem executes CI and surfaces results.

Operational constraints:

- CI log output is truncated at 8k characters
- truncation split is 70% head / 30% tail

Polling behavior uses:

- ETag caching on all polling endpoints
- exponential backoff for `403 primary`: 2s → 4s → 8s → 16s → 32s → 64s
- `429 secondary`: respect `Retry-After` header

### 8. Operator gating and merge decision

UI progress and gate state are streamed using protocol messages:

- `build_card`: `{ card_type, stage, content, progress }`
- `gate_card`: `{ gate_type, options[], description }`

A `gate_card` blocks until the operator responds.

There is no auto-approve path. Merge only proceeds after explicit operator approval.

### 9. Post-success learning updates

After each successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is updated

These stores are intentionally persistent and are not automatically cleared.

## Key Invariants

The subsystem inherits and must enforce the Forge architecture invariants.

### Security and trust invariants

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Human control invariants

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.
- Below-threshold scope confidence requires explicit operator choice to proceed, answer gaps, or cancel.

### File and repository safety invariants

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Validate paths before any write.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Prompt and context invariants

- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `DocumentStore`-supplied context is treated as untrusted input.
- Context trimming preserves the spec-anchor first turn and last 6 messages.

### Progress and recovery invariants

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.
- Local repair is bounded to 20 attempts; no infinite retry loops.

## Failure Modes

### Scope uncertainty

Condition:

- `SCOPE_SYSTEM` returns confidence below 85

Behavior:

- surface `coverage_gaps`
- gate the operator with proceed/answer/cancel
- permit at most one re-scope after operator answers
- do not silently continue as fully scoped

### Auth, crypto, or identity failure

Condition:

- any auth, crypto, or identity error

Behavior:

- fail closed
- do not degrade functionality silently
- surface the error with context
- do not continue with weakened guarantees

### Security refusal

Condition:

- generation or decisioning returns `SECURITY_REFUSAL`

Behavior:

- stop processing
- gate the operator
- log the event
- do not retry by rephrasing around the refusal

### Invalid or unsafe external input

Condition:

- malformed or untrusted document, PR comment, CI output, or protocol payload

Behavior:

- validate before use
- reject or gate as appropriate
- never elevate untrusted content into the system prompt

### Unknown XPC message type

Condition:

- inbound XPC message type is not recognized

Behavior:

- discard
- log
- do not raise as an exception

### Unsafe write target

Condition:

- a file write target fails `path_security.validate_write_path()`

Behavior:

- do not perform the write
- surface failure with context

### GitHub transport or rate-limit issues

Condition:

- polling or API-related failures through `GitHubTool`

Behavior:

- use ETag caching on polling endpoints
- on `403 primary`, exponential backoff from 2s to 64s
- on `429 secondary`, respect `Retry-After`
- continue within bounded retry policy rather than retrying indefinitely

### Build/test/lint failure during local repair

Condition:

- generated changes fail assertion, import, runtime, lint, or related checks

Behavior:

- choose repair strategy with `_choose_strategy(failure_type, attempt, records)`
- route:
  - `assertion_error` to `test_driven`
  - `import_error` / `runtime_error` to `converse`, then `test_driven`
  - `attempt >= 8` to `nuclear` every third attempt
- stop after 20 local attempts and move on

### Crash or restart mid-PR

Condition:

- process interruption during staged execution

Behavior:

- recover from per-PR stage checkpoints
- do not re-run already completed stages

### Oversized context or CI logs

Condition:

- context exceeds token budget or CI output becomes too large

Behavior:

- `ContextManager` auto-trims at 30k tokens while preserving critical turns
- CI logs are truncated to 8k chars using 70% head / 30% tail

## Dependencies

### Internal code dependencies

- `src/build_director.py` for orchestration, confidence gate, and PR routing
- `src/consensus.py` for consensus generation and system prompt definitions
- `src/github_tools.py` for all GitHub operations and webhook handling
- `src/build_ledger.py` for checkpointing and crash-safe stage recovery
- `failure_handler.py` for strategy selection via `_choose_strategy(...)`
- `path_security.validate_write_path()` for mandatory write-path validation
- `ContextManager` for token-budget trimming behavior
- `DocumentStore` for document loading, including automatic `build_rules.md` ingestion

### External protocol dependencies

- XPC transport using line-delimited JSON
- nonce authentication on XPC messages
- protocol message types:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### Persistent storage dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Provider dependencies

- two LLM providers used in parallel for generation
- Claude used for arbitration in consensus

### Operational dependencies

- GitHub access exclusively through `GitHubTool`
- CI execution and polling infrastructure compatible with:
  - ETag caching
  - backoff handling
  - `Retry-After` compliance