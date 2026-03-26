# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS build agent responsible for executing the end-to-end build workflow from plain-language build intent to gated merge-ready pull requests.

Within the Forge architecture, CraftedAgent:

- accepts build intent and repository context
- decomposes work into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitration path in consensus
- performs self-correction, lint gating, and a bounded 20-pass fix loop
- executes CI
- blocks on operator approval before merge
- maintains persistent build learning through build memory and build rules
- streams build status and gate requests over XPC to the macOS UI

It is a human-in-the-loop system. Gates never auto-resolve and operator input is mandatory wherever a gate is raised.

## Component Boundaries

CraftedAgent is bounded by the following responsibilities and non-responsibilities.

### In scope

- Build orchestration through `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gating
  - PR type routing
- Consensus generation through `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts including `GENERATION_SYSTEM`
  - Swift/UI generation variants including `SWIFT_GENERATION_SYSTEM` and `UI_ADDENDUM`
- GitHub interaction through `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- Persistent build-learning behavior
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- Stage checkpointing per PR to prevent re-running completed work after a crash
- DocumentStore-backed context loading for generation
- XPC communication using the defined wire protocol
- Operator gate presentation via `gate_card`
- Build progress streaming via `build_card`

### Out of scope / enforced boundaries

- CraftedAgent does not use the GitHub API directly.
  - All GitHub operations must go through `GitHubTool`.
- CraftedAgent does not execute generated code.
  - No `eval`
  - No `exec`
  - No subprocess execution of generated content
- CraftedAgent does not trust external inputs by default.
  - Documents, PR comments, and CI output are all treated as untrusted and validated
- CraftedAgent does not place external document context into the system prompt.
  - External document context is placed in the USER prompt only
- CraftedAgent does not auto-approve gates.
  - Gates wait indefinitely for operator input
- CraftedAgent does not silently continue through auth, crypto, or identity failures.
  - It fails closed
- CraftedAgent does not clear persistent learning state automatically.
  - build memory and build rules persist across runs
- CraftedAgent does not raise exceptions for unknown XPC message types.
  - They are discarded and logged

## Data Flow

### 1. Session initialization

CraftedAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

On readiness it emits:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

Credentials are provided as:

- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

This establishes provider access, GitHub access, and the `engineer_id` used for persistent workspace state.

### 2. Build intent to scoped plan

The core loop begins from plain-language build intent.

A scope confidence stage evaluates completeness:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

Behavior at this gate:

- if confidence is at or above threshold, the build proceeds
- below threshold, the operator is shown gaps and offered:
  - proceed
  - answer
  - cancel
- if the operator answers coverage gaps, a one-shot re-scope is performed
- there is no indefinite re-scope loop

### 3. Context loading

CraftedAgent uses the Document Store for generation context.

Primary behavior includes:

- loading relevant repository and product context documents
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatically loading `Mac-Docs/build_rules.md` through `DocumentStore`

Context constraints:

- external document context is inserted into the USER prompt only
- external context is untrusted and validated
- `ContextManager` auto-trims at 30k tokens
- trimming preserves:
  - the spec-anchor first turn
  - the last 6 messages

### 4. Generation and consensus

For each PR in the ordered build sequence:

- implementation and tests are generated using two LLM providers in parallel
- Claude arbitrates via the consensus path
- generation is routed through `ConsensusEngine` in `src/consensus.py`

Generation is informed by:

- repository context
- scoped build intent
- loaded documents
- persistent build learning from:
  - `build_memory.json`
  - `build_rules.md`

### 5. Correction, lint, and fix loop

After generation, CraftedAgent runs:

- a self-correction pass
- a lint gate
- a bounded local fix loop of up to 20 passes

Failure handling is strategy-driven in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Strategy rules:

- failure type is the primary signal
- attempt count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- after 20 local attempts, move on

### 6. CI execution and log handling

CraftedAgent executes CI after local correction phases.

CI output handling rules:

- CI log output is truncated at 8k characters
- truncation preserves:
  - 70% head
  - 30% tail

Polling behavior for remote operations includes:

- ETag caching on all polling endpoints
- `403 primary` uses exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429 secondary` respects the `Retry-After` header

### 7. GitHub operations

All GitHub operations are mediated by `GitHubTool`.

This includes repository operations and webhook handling through:

- `GitHubTool`
- `WebhookReceiver`

A hard write boundary is enforced:

- all file writes are validated by `path_security.validate_write_path()` before execution
- path validation is required before any write

### 8. Progress and gating to UI

CraftedAgent streams progress to the UI using:

- `build_card`
  - `{ card_type, stage, content, progress }`

It raises blocking operator gates using:

- `gate_card`
  - `{ gate_type, options[], description }`

Gate semantics are strict:

- gates block until the operator responds
- there is no auto-approve path

### 9. Persistence after successful work

After every successful PR:

- `build_memory.record_pr()` writes to:
  - `workspace/{engineer_id}/build_memory.json`

Build rules persistence:

- `Mac-Docs/build_rules.md` is written after each build run when 3 or more recurring failure patterns are found

Persistence semantics:

- build memory survives fresh installs and thread state wipes
- build memory is not deleted on clean runs
- build rules are not deleted on clean runs unless switching to a completely new codebase

## Key Invariants

CraftedAgent must preserve all Forge context invariants relevant to this subsystem.

### Security and trust

- Fail closed on auth, crypto, and identity errors
- No silent failure paths; every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent

### Prompt and context handling

- Context from external documents goes in the USER prompt, never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log
- Context trimming occurs automatically at 30k tokens while preserving the spec-anchor first turn and last 6 messages

### Operator control

- Gates wait indefinitely for operator input
- No auto-approve ever
- Scope confidence below `_CONFIDENCE_THRESHOLD = 85` must gate with gaps and explicit operator choice

### Write and integration safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution
- All GitHub operations go through `GitHubTool`
- Unknown XPC message types are discarded and logged, never raised as exceptions

### Reliability and recovery

- Per-PR stage checkpoints prevent re-running completed work after a crash
- Never retry indefinitely; the local fix loop is capped at 20 attempts
- Build memory and build rules are persistent learning systems and are never cleared automatically

## Failure Modes

### Scope ambiguity or incomplete intent

Detection:

- low `confidence` from `SCOPE_SYSTEM`
- populated `coverage_gaps`

Handling:

- `_stage_scope` blocks the pipeline below threshold 85
- operator may proceed, answer, or cancel
- if answers are provided, only one re-scope pass is allowed

### Auth, crypto, or identity failure

Handling:

- fail closed
- do not degrade silently
- surface the error with context
- do not continue the affected operation

### Security refusal from model output

Handling:

- do not bypass by rephrasing
- stop processing
- gate
- log the refusal event

### Invalid or unsafe write target

Handling:

- reject the write if `path_security.validate_write_path()` does not validate it
- no write is executed before validation

### Unknown XPC message type

Handling:

- discard the message
- log the event
- do not raise an exception path for the unknown type

### GitHub rate limiting or access throttling

Handling:

- `403 primary`: exponential backoff from 2s up to 64s
- `429 secondary`: honor `Retry-After`
- polling endpoints use ETag caching to reduce repeated fetch cost

### Generation/test failure during local iteration

Handling is selected by `failure_handler.py`:

- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- at attempt 8 and beyond, escalate with `nuclear` every third attempt
- stop after 20 local attempts and move on

### Excessive context or oversized logs

Handling:

- prompt context auto-trims at 30k tokens
- CI logs are truncated to 8k characters with 70/30 head-tail preservation

### Crash or restart during PR execution

Handling:

- per-PR stage checkpoints prevent re-running completed work after a crash

## Dependencies

### Internal code modules

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - PR type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`

### Persistent stores and files

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Platform services and protocols

- XPC transport using line-delimited JSON, nonce authentication, and 16 MB max message size
- Document Store for context retrieval and automatic build rules loading
- BuildStreamView as the consumer of streamed `build_card` messages

### External provider classes of dependency

- two LLM providers used in parallel for generation
- GitHub access through `GitHubTool`
- CI execution environment

### Operator-facing protocol messages

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`