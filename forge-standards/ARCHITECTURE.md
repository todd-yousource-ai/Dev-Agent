# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is a native macOS AI coding agent subsystem responsible for executing the end-to-end build workflow from plain-language build intent to gated pull request delivery.

Within the Forge platform, ForgeAgent:

- decomposes a requested build into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- arbitrates generation through the consensus path
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI and presents progress and gate states to the operator
- blocks on operator approval before merge-related progression
- persists per-PR checkpoints so completed work is not re-run after a crash
- persists cross-run learning via build memory and build rules

The subsystem is security-constrained. It treats all external inputs as untrusted, validates all file writes through path validation, never executes generated code directly, and fails closed on authentication, cryptography, and identity errors.

## Component Boundaries

ForgeAgent includes the following responsibilities and components explicitly referenced in the source material:

### Build orchestration

`src/build_director.py` contains `BuildPipeline` orchestration, including:

- PR sequencing
- confidence gate handling
- `pr_type` routing
- stage progression and gating behavior

The scope stage includes a confidence gate:

- `SCOPE_SYSTEM` returns `confidence` in the range `0–100` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the subsystem shows gaps and offers:
  - proceed
  - answer
  - cancel
- if the operator provides gap answers, ForgeAgent performs a one-shot re-scope only; it does not loop indefinitely

### Consensus and generation

`src/consensus.py` contains:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM`
- `UI_ADDENDUM`

This component is responsible for multi-provider generation behavior and arbitration in the implementation workflow.

### GitHub operations

`src/github_tools.py` contains:

- `GitHubTool`
- `WebhookReceiver`

Boundary rule:

- all GitHub operations go through `GitHubTool`
- ForgeAgent never uses the GitHub API directly outside this tool boundary

GitHub write operations are constrained by path security validation before execution.

### Build persistence and learning

The subsystem owns two persistent learning stores:

#### Build memory

- file: `workspace/{engineer_id}/build_memory.json`
- survives fresh installs and thread state wipes
- written after every successful PR via `build_memory.record_pr()`
- must not be deleted on clean runs because cross-run learning is intentional

#### Build rules

- file: `Mac-Docs/build_rules.md`
- loaded by `DocumentStore` automatically
- written after each build run when 3 or more recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

### Document context handling

ForgeAgent uses `DocumentStore` for retrieval and context assembly.

Primary documented usage includes:

- loading generation context
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatically loading persistent build rules from `Mac-Docs/build_rules.md`

Boundary rule:

- context from external documents belongs in the `USER` prompt, never the `SYSTEM` prompt

### Operator interaction and streaming

ForgeAgent communicates progress and gate states over the XPC channel using documented message types:

- `build_card` for streamed build progress to `BuildStreamView`
- `gate_card` for operator-blocking decisions

Boundary rule:

- gates block indefinitely until operator input is received
- there is no auto-approve path

### Path security boundary

All file writes performed by ForgeAgent are bounded by path validation:

- every write must be validated with `path_security.validate_write_path()` before execution

Allowed root behavior is part of this boundary:

- standard roots explicitly required for a standard project include:
  - `src`
  - `tests`
  - `docs`
  - `scripts`
  - `.github`
  - `tools`
  - `schemas`
  - `contracts`
  - `configs`
- dot-prefixed roots such as `.github` require explicit allowlisting
- CamelCase roots for Swift/Xcode-style projects are supported through smart root detection
- the smart root rule allows any root matching:
  - `^[A-Za-z][A-Za-z0-9_-]*$`

This boundary exists to prevent silent failure or rejection when committing into valid repository roots, while still enforcing strict path rules.

## Data Flow

### 1. Build intent intake

ForgeAgent receives a plain-language build intent and begins staged pipeline execution under `BuildPipeline`.

### 2. Scope analysis and confidence gate

During scope analysis:

- `SCOPE_SYSTEM` produces:
  - `confidence`
  - `coverage_gaps`
- `_stage_scope` evaluates confidence against threshold `85`

If confidence is below threshold:

- ForgeAgent surfaces coverage gaps
- presents operator choices:
  - proceed
  - answer
  - cancel
- if the operator answers gaps, ForgeAgent performs one re-scope pass only

### 3. Context assembly

ForgeAgent retrieves document context from `DocumentStore`, including:

- general generation context
- specific requested documents such as `PRODUCT_CONTEXT.md`
- persistent `build_rules.md`

External document content is treated as untrusted and placed only in the `USER` prompt.

### 4. Parallel generation and arbitration

ForgeAgent invokes two LLM providers in parallel for implementation and test generation.

The consensus path in `ConsensusEngine` arbitrates generated outputs using the generation system configurations defined in `src/consensus.py`.

### 5. Local correction and bounded retry loop

After initial generation, ForgeAgent applies:

- self-correction
- lint gate
- local fix loop

Failure handling follows explicit strategy selection in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Documented routing rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum local attempts: `20`, then move on

### 6. CI execution and status handling

ForgeAgent executes CI and processes CI output with bounded context behavior:

- CI log output truncated to 8k characters
- truncation split: 70% head / 30% tail

Polling and rate-limit behavior include:

- ETag caching on all polling endpoints
- `403` primary rate limit:
  - exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate limit:
  - respect `Retry-After` header

### 7. Progress and gate presentation

ForgeAgent emits XPC messages using line-delimited JSON with nonce authentication and a maximum message size of 16MB.

Relevant messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
- `gate_card`
  - `{ gate_type, options[], description }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

`gate_card` blocks until the operator responds.

### 8. Persistence after successful PRs and runs

After every successful PR:

- ForgeAgent records learning to `workspace/{engineer_id}/build_memory.json` using `build_memory.record_pr()`

After each build run, when at least 3 recurring failure patterns are identified:

- ForgeAgent updates `Mac-Docs/build_rules.md`

Per-PR stage checkpoints are persisted to prevent replay of completed work after a crash.

## Key Invariants

ForgeAgent enforces the following invariants:

- fail closed on auth, crypto, and identity errors; never degrade silently
- no silent failure paths; every error must surface with context
- secrets never appear in logs, error messages, or generated code
- all external input, including documents, PR comments, and CI output, is untrusted and validated
- generated code is never executed by the agent
- no `eval`, no `exec`, and no subprocess execution of generated content
- gates wait indefinitely for operator input
- no auto-approve ever
- all file writes are validated by `path_security.validate_write_path()` before execution
- external document context is placed in the `USER` prompt, never the `SYSTEM` prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the subsystem must stop, gate, and log
- XPC unknown message types are discarded and logged, never raised as exceptions
- per-PR stage checkpoints prevent re-running completed work after a crash
- build memory and build rules are persistent learning systems and are never cleared automatically

Additional operational invariants:

- all GitHub operations go through `GitHubTool`
- context windows are auto-trimmed at 30k tokens by `ContextManager`
- trimming preserves:
  - the spec-anchor first turn
  - the last 6 messages
- retries are bounded to 20 local attempts maximum

## Failure Modes

### Scope uncertainty

Condition:

- `SCOPE_SYSTEM` returns confidence below `85`

Behavior:

- surface `coverage_gaps`
- present operator options
- allow at most one re-scope pass after operator gap answers
- do not enter an open-ended scope clarification loop

### Path validation rejection

Condition:

- a requested write targets a path outside validated roots
- a dot-prefixed or unexpected root is not allowed
- repository root detection rejects the root

Behavior:

- write is blocked by `path_security.validate_write_path()`
- path security prevents silent writes to unexpected locations
- smart root detection permits valid single-root names matching `^[A-Za-z][A-Za-z0-9_-]*$`, including CamelCase project roots

### Auth, crypto, or identity failure

Condition:

- authentication, cryptographic, or identity verification error

Behavior:

- fail closed
- never silently degrade

### Untrusted input or prompt-boundary violation

Condition:

- external document content, PR comments, or CI output is malformed, unsafe, or improperly routed

Behavior:

- treat as untrusted input
- validate before use
- never promote external document context into the `SYSTEM` prompt

### Security refusal handling

Condition:

- `SECURITY_REFUSAL` is returned

Behavior:

- stop
- gate
- log
- do not attempt bypass via rephrasing

### Unknown XPC message type

Condition:

- an unrecognized XPC message arrives

Behavior:

- discard and log
- do not raise an exception for unknown message types

### Iterative fix exhaustion

Condition:

- local fix attempts reach maximum retry bound

Behavior:

- stop retrying after 20 attempts
- strategy escalation follows `_choose_strategy(failure_type, attempt, records)`
- move on rather than retry indefinitely

### GitHub API throttling

Condition:

- `403` primary rate limit or `429` secondary rate limit

Behavior:

- `403`: exponential backoff from 2s through 64s
- `429`: honor `Retry-After`
- polling uses ETag caching

### Crash recovery

Condition:

- process or run interruption after some PR stages completed

Behavior:

- per-PR stage checkpoints prevent completed work from being re-run

## Dependencies

ForgeAgent depends on the following internal and protocol-level components documented in the source material.

### Internal components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` and generation system definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- `DocumentStore`
- `ContextManager`
- `path_security.validate_write_path()`
- `failure_handler.py` strategy selection via `_choose_strategy(...)`
- build memory persistence via `build_memory.record_pr()`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External service dependencies

- two LLM providers operating in parallel:
  - Anthropic
  - OpenAI
- GitHub, accessed only through `GitHubTool`

### XPC protocol dependency

ForgeAgent communicates over an XPC wire format with these constraints:

- line-delimited JSON
- nonce-authenticated
- maximum 16MB per message

Supported documented message structures include:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

### Repository layout dependency

ForgeAgent assumes path validation against repository roots that include standard project directories and smart detection for valid single-token root names, including CamelCase Swift/Xcode project roots.