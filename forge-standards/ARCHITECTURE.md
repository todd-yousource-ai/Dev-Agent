# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the Forge subsystem responsible for turning a plain-language build intent into a staged, operator-gated software delivery workflow on macOS.

At a high level, the subsystem:

- accepts build intent and required credentials over the Forge XPC protocol
- scopes and decomposes work into an ordered sequence of pull requests
- runs a confidence gate on scope quality before implementation begins
- retrieves supporting repository and product context from the document store
- injects persistent build memory and build rules into future generation passes
- generates implementation and tests using multiple LLM providers in parallel
- arbitrates generation outputs through the consensus layer
- performs self-correction, lint, CI, and iterative fix loops
- presents progress and blocking decisions to the operator via streamed cards
- waits indefinitely for explicit operator approval at required gates
- persists per-PR checkpoints so completed stages are not repeated after crashes
- records successful PR outcomes back into durable learning artifacts

This subsystem is orchestration-heavy. It does not directly execute generated code as agent instructions, does not bypass approval gates, and does not perform raw GitHub API access outside the approved tooling boundary.

## Component Boundaries

The subsystem is composed of the following primary components and responsibilities.

### Build Director / Pipeline Orchestration

**Primary file:** `src/build_director.py`

Owns end-to-end workflow orchestration for a build run, including:

- stage sequencing
- PR-type routing
- scope confidence gating
- generation and correction pass ordering
- operator gate presentation
- checkpoint-aware resume behavior

It is the control plane for the subsystem.

It must enforce:

- `_stage_scope` confidence gating at `_CONFIDENCE_THRESHOLD = 85`
- one-shot re-scope only when the operator answers coverage gaps
- no infinite re-scope loop
- no progression past blocked gates without operator input

Below threshold, it must surface coverage gaps and offer:

- proceed
- answer
- cancel

### Consensus Engine

**Primary file:** `src/consensus.py`

Owns multi-model generation and arbitration behavior.

Responsibilities include:

- parallel generation across supported LLM providers
- use of generation system prompts such as `GENERATION_SYSTEM`
- use of Swift/UI-specific generation prompts such as `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- arbitration of candidate outputs, with Claude identified as arbitrator in platform behavior
- production of implementation/test artifacts for downstream validation steps

This component generates text artifacts only. It must not execute generated content.

### GitHub Operations Layer

**Primary files:** `src/github_tools.py`

All GitHub interaction is mediated exclusively through `GitHubTool` and related webhook handling.

Hard boundary:

- **All GitHub operations go through `GitHubTool`**
- direct GitHub API usage elsewhere in the subsystem is forbidden

Responsibilities include:

- PR creation/update/comment operations
- repository metadata access
- polling/webhook integration
- HTTP resilience behavior such as backoff and cache validation

Required behavior includes:

- ETag caching on all polling endpoints
- exponential backoff for `403 primary` responses: `2s -> 4s -> 8s -> 16s -> 32s -> 64s`
- honoring `Retry-After` for `429 secondary`

### Build Ledger / Checkpointing

**Primary file:** `src/build_ledger.py`

Owns durable per-PR stage checkpoints.

Purpose:

- prevent re-running completed work after crash or restart
- provide stage-aware recovery
- preserve build continuity across failures

This component is required by the Forge invariant:

- per-PR stage checkpoints prevent re-running completed work after a crash

### Document Store Integration

This subsystem consumes repository and product context from the document store.

Primary usage:

- load contextual documents for generation
- include external context in the **USER** prompt only
- report embedding/indexing state through `doc_status`

Example supported usage:

- load a specific document such as `PRODUCT_CONTEXT.md`

Boundary rules:

- external documents are untrusted input
- document-derived context must never be placed into the SYSTEM prompt
- document store loading is context retrieval, not authority elevation

### Build Memory and Build Rules

This subsystem owns read/write integration for persistent learning artifacts.

#### Build Memory

- file: `workspace/{engineer_id}/build_memory.json`
- durability: survives fresh installs and thread state wipes
- write point: after every successful PR via `build_memory.record_pr()`
- deletion policy: never automatically deleted on clean runs

Purpose:

- cross-run learning from prior successful PRs
- durable accumulation of implementation history

#### Build Rules

- file: `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- write point: after each build run when `3+` recurring failure patterns are detected
- deletion policy: never automatically deleted on clean runs unless switching to a completely new codebase

Purpose:

- self-improving coding rules derived from build history

These stores are persistent learning systems and are explicitly not ephemeral cache.

### Failure Handling Strategy Layer

**Referenced behavior:** `failure_handler.py`

Owns strategy selection for local repair attempts.

Decision rules:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary signal
- attempt count is secondary escalation

Required mappings:

- `assertion_error` -> `test_driven` immediately
- `import_error` / `runtime_error` -> `converse` first, then `test_driven`
- `attempt >= 8` -> `nuclear` every 3rd attempt
- maximum `20` local attempts, then stop and move on

This layer is bounded to remediation strategy selection; it does not override operator gates or safety constraints.

### Context Management

Responsible for token-budget enforcement during long-running conversations.

Required behavior:

- auto-trim at `30k` tokens
- preserve spec-anchor first turn
- preserve last `6` messages

This is an optimization/control concern, not a semantic authority layer.

### UI/Protocol Bridge

Consumes and emits Forge protocol messages over XPC.

Relevant message types:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

Responsibilities include:

- line-delimited JSON parsing/serialization
- nonce-authenticated message handling
- maximum `16MB` per message enforcement
- streamed progress updates to `BuildStreamView`
- operator blocking via `gate_card`

Boundary rule:

- unknown XPC message types are discarded and logged, never raised as exceptions

## Data Flow

The subsystem data flow is sequential with operator-gated branches.

### 1. Session Initialization

The subsystem receives and validates XPC input, including:

- `ready`: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Validation requirements:

- all external input is untrusted
- auth, crypto, and identity failures fail closed
- secrets are never logged, echoed in errors, or emitted into generated code

### 2. Build Intent Ingestion

A plain-language build intent enters the pipeline.

The build director:

- establishes build context
- loads repository identity/context
- prepares scoping inputs
- may load supporting documents from the document store

Any external document or PR/comment/CI-derived text is treated as untrusted.

### 3. Scope and Confidence Gate

The build director performs scoping and confidence estimation.

Expected output from scope logic:

- confidence `0-100`
- `coverage_gaps`

Gate behavior:

- if confidence `>= 85`, proceed
- if confidence `< 85`, emit a blocking gate with gaps and options:
  - proceed
  - answer
  - cancel

If the operator answers gaps:

- perform one re-scope pass
- do not enter an open-ended clarification loop

### 4. PR Decomposition and Stage Planning

The subsystem decomposes work into an ordered PR plan.

For each PR, the pipeline establishes stages such as:

- generation
- self-correction
- lint
- fix loop
- CI
- approval/merge gating

Build ledger checkpoints are written so completed stages can be resumed safely.

### 5. Context Assembly for Generation

Generation context is assembled from:

- build intent
- repository context
- selected documents from the document store
- persistent build memory
- persistent build rules
- current PR/stage state

Prompt placement rule:

- external/document-derived context goes into the USER prompt only
- never into SYSTEM

Context manager applies trimming at `30k` tokens while preserving:

- first spec-anchor turn
- last `6` messages

### 6. Parallel Generation and Arbitration

The consensus engine requests implementations/tests from multiple LLM providers in parallel.

It then arbitrates outputs and produces candidate changes for the current PR.

The subsystem may use specialized generation systems for Swift/UI work.

Generated outputs remain inert text/artifacts at this stage.

### 7. Validation and Repair Loop

The pipeline applies:

- self-correction pass
- lint gate
- CI execution
- up to `20` local repair attempts

Failure handling chooses remediation strategy based on failure type first, attempt count second.

CI log handling:

- truncate output at `8k` characters
- preserve approximately `70%` head / `30%` tail

The fix loop is bounded and cannot retry indefinitely.

### 8. Operator Gates

When a gate condition is reached, the subsystem emits:

- `build_card` for progress/status
- `gate_card` for a blocking operator decision

Operator gates wait indefinitely. There is no auto-approve path.

### 9. GitHub Operations and Merge Progression

Repository operations are executed only through `GitHubTool`.

This includes PR publication and state transitions after successful validation and operator approval.

Polling/webhook behavior uses cache validation and backoff rules as defined above.

### 10. Learning Persistence

After each successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

After each build run with `3+` recurring failure patterns:

- update `Mac-Docs/build_rules.md`

These artifacts become part of future generation context.

## Key Invariants

The subsystem must enforce the following Forge and local invariants.

### Safety and Security

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, `exec`, or subprocess execution of generated content.
- `SECURITY_REFUSAL` output is terminal for the attempted action: stop, gate, and log; rephrasing must not bypass refusal.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Human Control

- Gates wait indefinitely for operator input.
- No auto-approve behavior exists anywhere in the subsystem.
- Low-confidence scope cannot silently proceed; below-threshold scope must surface coverage gaps and require an explicit operator decision.

### Prompt/Context Discipline

- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- Document store content is contextual evidence, not trusted instruction authority.
- Context trimming preserves the first spec-anchor turn and last six messages.

### File and Path Safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- This requirement applies to any workspace write, generated artifact write, memory update, rules update, or repository file modification initiated by the subsystem.

### Recovery and Bounded Execution

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Local repair is bounded to a maximum of 20 attempts.
- One-shot re-scope is allowed only when the operator answers coverage gaps; no indefinite clarification loops.

### Persistent Learning

- Build memory is never cleared automatically.
- Build rules are never cleared automatically except when intentionally switching to a completely new codebase.
- Both are persistent learning systems and must survive clean runs.

### GitHub Boundary

- All GitHub operations go through `GitHubTool`.
- No direct GitHub API calls are permitted elsewhere in the subsystem.

## Failure Modes

### Scope Confidence Failure

Condition:

- scope confidence below `85`

Behavior:

- present coverage gaps
- block on operator decision
- optionally perform one re-scope if the operator supplies answers

Must not:

- silently continue as if confidence were sufficient
- enter an endless clarification loop

### Auth / Identity / Crypto Failure

Condition:

- invalid credentials
- nonce/authentication failure on XPC
- identity mismatch or related trust failure

Behavior:

- fail closed
- stop affected operation
- surface contextual error without leaking secrets

Must not:

- degrade into partial/trusting mode
- continue with guessed or cached identity assumptions

### Document / External Input Validation Failure

Condition:

- malformed or suspicious external content
- invalid document metadata/state
- unsafe content in PR comments or CI output

Behavior:

- treat as untrusted input
- validate before use
- stop or gate when safety requirements are not met

Must not:

- elevate external content into trusted instruction space

### Generation Refusal or Safety Stop

Condition:

- consensus/generation output includes `SECURITY_REFUSAL` or equivalent safety refusal

Behavior:

- stop current action
- gate/log
- do not retry by rephrasing to bypass the refusal

### Lint / Test / Runtime / Import / Assertion Failures

Condition:

- validation or CI failure during local repair loop

Behavior:

- choose strategy via `_choose_strategy(failure_type, attempt, records)`
- follow mapped escalation rules
- stop after max 20 attempts

Specific strategy rules:

- `assertion_error` -> immediate `test_driven`
- `import_error` / `runtime_error` -> `converse` first, then `test_driven`
- `attempt >= 8` -> `nuclear` every third attempt

Must not:

- retry indefinitely
- hide repeated failure state

### GitHub API Degradation or Rate Limiting

Condition:

- `403 primary`
- `429 secondary`
- polling churn

Behavior:

- exponential backoff for primary limit
- respect `Retry-After` for secondary limit
- use ETag caching on polling endpoints

Must not:

- hammer endpoints
- bypass `GitHubTool`

### XPC Protocol Errors

Condition:

- malformed JSON
- unsupported message shape
- unknown message type
- oversized payload beyond `16MB`

Behavior:

- validate and reject/ignore as appropriate
- discard unknown message types and log them
- surface protocol errors with context

Must not:

- throw unknown-type exceptions up the stack as control flow

### Crash / Restart During PR Processing

Condition:

- process interruption after some stages complete

Behavior:

- resume from build ledger checkpoints
- avoid re-running completed per-PR stages

Must not:

- lose durable success state
- rerun already-completed stages without explicit reason

### Learning Store Write Failure

Condition:

- failure writing `build_memory.json` or `build_rules.md`

Behavior:

- surface explicit error with context
- preserve existing files if write cannot be completed safely
- validate write path before any file operation

Must not:

- silently drop learning updates
- auto-delete persistent learning artifacts

## Dependencies

### Internal Dependencies

- `src/build_director.py`
  - pipeline orchestration
  - scope confidence gate
  - PR routing/staging
- `src/consensus.py`
  - parallel generation
  - arbitration
  - generation system definitions
- `src/github_tools.py`
  - all GitHub operations
  - webhook/poll behavior
- `src/build_ledger.py`
  - per-PR checkpoint persistence
- `failure_handler.py`
  - failure strategy selection
- `path_security.validate_write_path()`
  - mandatory validation before any write
- context manager
  - token trimming and conversation preservation
- document store
  - repository/product context retrieval
  - automatic loading of `Mac-Docs/build_rules.md`

### External/Platform Dependencies

- Forge XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - max `16MB` message size
- LLM providers
  - Anthropic
  - OpenAI
  - parallel generation inputs through the consensus engine
- GitHub
  - accessed only through `GitHubTool`
- macOS host environment
  - native runtime for the agent subsystem
- BuildStreamView
  - consumer of streamed `build_card` messages

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - durable PR learning memory
- `Mac-Docs/build_rules.md`
  - durable, self-improving coding rules
- document embeddings/index state
  - exposed through `doc_status`
- build ledger/checkpoint storage
  - resume and crash recovery state

### Explicit Non-Dependencies / Prohibited Couplings

The subsystem must not depend on:

- direct GitHub API access outside `GitHubTool`
- execution of generated code as agent instructions
- automatic approval/merge decisions without operator action
- SYSTEM-prompt injection of untrusted external document content
- automatic clearing of build memory or build rules during normal clean runs