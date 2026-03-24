# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is a native macOS AI coding-agent subsystem responsible for orchestrating repository changes from a plain-language build intent through staged pull-request execution.

Within the Forge platform, ForgeAgent:

- decomposes build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- arbitrates generation via the consensus flow
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI
- blocks on operator approval before merge
- persists cross-run learning in build memory and build rules
- interacts with GitHub exclusively through the GitHub tooling layer
- streams build and gate state over XPC to the UI layer

The subsystem is designed to be fail-closed for authentication, cryptography, and identity issues, and to surface all errors with context rather than degrading silently.

## Component Boundaries

ForgeAgent spans the agent-side orchestration and supporting logic identified in the provided architecture context.

Included components:

- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - performs confidence gating
  - routes by PR type
- `src/consensus.py`
  - owns `ConsensusEngine`
  - contains generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
  - is the only permitted path for GitHub operations
- `src/build_ledger.py`
  - participates in per-PR stage checkpointing and crash recovery behavior implied by the stage-checkpoint invariant
- build-memory and build-rules persistence surfaces
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

External to this subsystem:

- operator decision-making
  - ForgeAgent may present gates and wait indefinitely, but never auto-approves
- UI rendering
  - `build_card` is streamed to `BuildStreamView`
  - `gate_card` blocks until operator response
- document embedding/storage implementation
  - ForgeAgent consumes document status and document context, but document-store internals are separate
- LLM providers themselves
  - ForgeAgent coordinates provider usage but does not implement provider backends
- repository CI systems
  - ForgeAgent executes CI-related flows and consumes output, but CI infrastructure is external

Hard boundaries enforced by design:

- generated code is never executed by the agent
- ForgeAgent does not directly call the GitHub API; it must use `GitHubTool`
- all file writes must pass `path_security.validate_write_path()` before execution
- external-document context belongs in the USER prompt, never the SYSTEM prompt

## Data Flow

### 1. Session and transport initialization

ForgeAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum `16MB` per message

Initialization begins with a `ready` message:

```json
{ "agent_version": "...", "min_swift_version": "...", "capabilities": [], "doc_store_status": "..." }
```

Credentials are supplied via a `credentials` message containing:

```json
{ "anthropic_api_key": "...", "openai_api_key": "...", "github_token": "...", "engineer_id": "..." }
```

Auth, crypto, or identity failures are fail-closed.

### 2. Intent intake and scope gating

A plain-language build intent enters ForgeAgent and is processed by the build pipeline.

Before implementation proceeds, ForgeAgent applies the scope-confidence gate:

- `SCOPE_SYSTEM` returns:
  - `confidence` from `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- ForgeAgent shows the identified gaps
- offers operator choices:
  - proceed
  - answer
  - cancel
- supports a one-shot re-scope if the operator provides gap answers
- does not loop indefinitely at this stage

### 3. Document and persistent learning context assembly

ForgeAgent can load document context for generation, including specific documents such as `PRODUCT_CONTEXT.md`.

Document-store-related status is surfaced using `doc_status` messages:

```json
{ "doc_id": "...", "doc_name": "...", "status": "...", "chunk_count": 0, "embedded_count": 0 }
```

Persistent learning inputs include:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread-state wipes
  - written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - written after each build run when 3 or more recurring failure patterns are found

These stores are intentionally persistent and are not cleared on clean runs, except `build_rules.md` when switching to a completely new codebase.

### 4. Generation and arbitration

ForgeAgent sends generation work through the consensus layer:

- two LLM providers generate in parallel
- Claude arbitrates
- generation is governed by system prompts in `src/consensus.py`

All external context used for generation is treated as untrusted input and validated. External document context is inserted into the USER prompt only.

### 5. Repository modification and path enforcement

All repository writes are validated before execution using:

- `path_security.validate_write_path()`

Root-directory enforcement is part of the write boundary. The system must explicitly allow valid repository roots, including:

- standard roots:
  - `src`
  - `tests`
  - `docs`
  - `scripts`
- dot-prefixed infrastructure roots:
  - `.github`
- common infrastructure roots:
  - `tools`
  - `schemas`
  - `contracts`
  - `configs`

Additionally, ForgeAgent implements smart root detection for project roots matching:

```regex
^[A-Za-z][A-Za-z0-9_-]*$
```

This supports CamelCase or lowercase single-word roots such as:

- `CraftedApp`
- `CraftedTests`
- `ForgeAgent`

This root policy exists because unexpected root-directory commits may otherwise fail silently or be rejected by path-security guards. ForgeAgent therefore maintains an explicit enforcement boundary around allowed write roots.

### 6. GitHub operations

All GitHub interactions flow through `GitHubTool` and never through direct GitHub API usage.

This boundary applies to all GitHub operations, including repository modification workflows and webhook-driven interactions via `WebhookReceiver`.

### 7. Validation, correction, and CI handling

After generation, ForgeAgent performs:

- self-correction pass
- lint gate
- bounded local fix loop of up to 20 attempts
- CI execution and output handling

Failure handling is driven by `failure_handler.py` strategy selection:

- `_choose_strategy(failure_type, attempt, records)`

Selection rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Polling/network efficiency and rate handling:

- `403` primary: exponential backoff
  - `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary: respect `Retry-After`
- ETag caching on all polling endpoints

Context and output controls:

- `ContextManager` auto-trims at `30k` tokens
- preserves:
  - spec-anchor first turn
  - last 6 messages
- CI log output truncated at `8k` characters
  - `70%` head / `30%` tail

### 8. Checkpointing, operator gate, and merge

ForgeAgent maintains per-PR stage checkpoints to prevent re-running completed work after a crash.

During approval points, ForgeAgent emits a `gate_card`:

```json
{ "gate_type": "...", "options": [], "description": "..." }
```

This blocks until operator response. Gates wait indefinitely; there is no auto-approve path.

Progress/status is streamed via `build_card`:

```json
{ "card_type": "...", "stage": "...", "content": "...", "progress": "..." }
```

## Key Invariants

ForgeAgent enforces the following subsystem invariants:

- fail closed on auth, crypto, and identity errors
- no silent failure paths; every error must surface with context
- secrets never appear in logs, error messages, or generated code
- all external input is untrusted and validated
  - including documents, PR comments, and CI output
- generated code is never executed by the agent
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- gates wait indefinitely for operator input
- no auto-approve ever
- all file writes are path-validated via `path_security.validate_write_path()` before execution
- external document context goes in the USER prompt, never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing
  - stop
  - gate
  - log
- XPC unknown message types are discarded and logged, never raised as exceptions
- per-PR stage checkpoints prevent replay of completed work after crashes
- build memory and build rules are persistent learning systems and are never cleared automatically
- all GitHub operations go through `GitHubTool`
- allowed write roots must satisfy the enforced root policy, including explicit support for `.github` and smart detection of roots matching `^[A-Za-z][A-Za-z0-9_-]*$`

## Failure Modes

### Path and repository-boundary failures

- writes to unexpected or non-allowed root directories are rejected by path-security guards
- dot-prefixed roots such as `.github` fail unless explicitly allowlisted
- path validation failure prevents file mutation from executing

Expected handling:
- fail the operation visibly
- do not silently skip writes
- preserve context on the error

### Auth, crypto, and identity failures

- invalid or missing credentials
- transport nonce/authentication failures
- identity mismatches

Expected handling:
- fail closed
- do not downgrade capability
- surface the failure with context

### Untrusted-input and security-refusal failures

- malformed or hostile external inputs from documents, PR comments, or CI output
- `SECURITY_REFUSAL` responses from safety controls

Expected handling:
- validate inputs before use
- never bypass refusal by prompt rephrasing
- stop, gate, and log

### XPC protocol failures

- unknown XPC message types
- oversized or malformed line-delimited JSON payloads

Expected handling:
- unknown message types are discarded and logged
- protocol violations do not convert into unhandled exceptions

### Scope uncertainty failures

- scope confidence below `85`
- unresolved `coverage_gaps`

Expected handling:
- present gaps to operator
- offer proceed/answer/cancel
- allow one re-scope after operator clarification
- do not enter an unbounded clarification loop

### Generation and correction failures

- provider disagreement or poor output quality
- assertion, import, or runtime failures during validation
- repeated unsuccessful local correction attempts

Expected handling:
- route through `ConsensusEngine`
- apply failure-specific strategy selection
- stop local repair after 20 attempts and move on rather than retry forever

### Network and API pressure failures

- GitHub/API `403` primary rate constraints
- `429` secondary limits

Expected handling:
- exponential backoff for `403`
- respect `Retry-After` for `429`
- use ETag caching on polling endpoints

### Crash/restart failures

- agent interruption after partial PR progress

Expected handling:
- recover from per-PR stage checkpoints
- do not re-run already completed stages

### Context-size and log-volume failures

- context growth beyond model budget
- oversized CI output

Expected handling:
- auto-trim context at `30k` tokens while preserving anchor and recent turns
- truncate CI logs to `8k` characters with `70%` head and `30%` tail

## Dependencies

ForgeAgent depends on the following subsystem-adjacent capabilities and contracts described in the source material:

### Internal code dependencies

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` and generation-system definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- stage-ledger/checkpoint functionality in `src/build_ledger.py`
- `path_security.validate_write_path()`
- `failure_handler.py` strategy selection via `_choose_strategy(...)`
- `ContextManager`
- `DocumentStore`

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol dependencies

- XPC line-delimited JSON transport
- nonce-authenticated messaging
- message schemas:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External service dependencies

- two LLM providers used in parallel
- GitHub, but only through `GitHubTool`
- repository CI systems
- operator responses for gated stages

### Non-dependencies / prohibited direct usage

ForgeAgent must not depend on:

- direct GitHub API calls outside `GitHubTool`
- execution of generated code
- automatic approval paths
- silent fallback behavior for security-sensitive failures