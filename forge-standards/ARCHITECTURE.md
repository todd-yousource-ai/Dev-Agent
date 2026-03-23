# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the Forge subsystem responsible for turning a plain-language build intent into a controlled, reviewable sequence of pull requests and gated merge decisions.

At a high level, the subsystem:

1. Accepts operator-supplied build intent and repository context.
2. Performs scope analysis and confidence gating before implementation begins.
3. Decomposes work into an ordered PR plan.
4. Retrieves repository, document, and persistent learning context.
5. Generates code and tests using parallel LLM providers via the consensus pipeline.
6. Runs self-correction, lint, and bounded local fix loops.
7. Executes CI and summarizes results.
8. Presents progress and gate decisions to the operator over XPC/UI streaming.
9. Waits indefinitely for operator approval at required gates.
10. Persists per-PR checkpoints and long-lived build learning artifacts.

This subsystem is orchestration-heavy. It does not directly expose raw model APIs, directly manipulate GitHub outside `GitHubTool`, or execute generated code as code. Its role is to coordinate planning, generation, correction, validation, CI feedback handling, and operator gating under Forge security and reliability constraints.

## Component Boundaries

### In Scope

The CraftedDevAgent subsystem includes the following responsibilities:

- Build pipeline orchestration in `src/build_director.py`
  - PR sequencing
  - stage execution
  - scope confidence gate
  - PR type routing
  - operator gate handling
- Multi-model generation and arbitration in `src/consensus.py`
  - parallel provider use
  - consensus/arbitration behavior
  - generation system prompts and provider-specific addenda
- GitHub interaction through `src/github_tools.py`
  - repository operations
  - webhook handling
  - PR creation/update flows
  - polling and status retrieval through approved abstraction only
- Build state and recovery tracking in `src/build_ledger.py`
  - per-PR stage checkpoints
  - crash recovery state
- Persistent learning artifacts
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- Document retrieval for generation context via DocumentStore usage
- XPC-facing progress/gate/status message production
  - `build_card`
  - `gate_card`
  - `doc_status`
  - `ready`

### Explicitly Out of Scope

The subsystem does **not** own:

- Direct execution of generated code
- Any `eval`, `exec`, or subprocess execution of generated content
- Direct use of GitHub APIs outside `GitHubTool`
- Silent fallback on auth, crypto, or identity failures
- Automatic gate approval or operator bypass
- Automatic deletion/reset of build memory or build rules
- Treating external documents or PR/CI content as trusted input
- Promotion of external document content into SYSTEM prompts

### Trust Boundary

CraftedDevAgent sits at a trust boundary between:

- trusted local orchestration/runtime logic, and
- untrusted external inputs, including:
  - user-provided documents
  - PR comments
  - CI output
  - GitHub/webhook payloads
  - model outputs
  - XPC inputs from peer processes

All such inputs must be validated, constrained, and treated as data rather than executable instructions.

## Data Flow

### 1. Session Initialization

On startup, the subsystem participates in the XPC readiness handshake using the line-delimited JSON wire format:

- nonce-authenticated
- maximum 16 MB per message

It emits a `ready` message with:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Intent Intake and Scope Gate

The operator provides plain-language build intent. The subsystem then runs the scope-confidence phase described by the repository documents:

- `SCOPE_SYSTEM` returns:
  - `confidence` in `[0, 100]`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

Behavior:

- If confidence is at or above threshold, the pipeline proceeds.
- If below threshold, the subsystem presents the gaps and offers:
  - proceed
  - answer
  - cancel
- If the operator answers gaps, one re-scope pass is allowed.
- There is no indefinite re-scope loop.

This gate exists to reduce implementation on underspecified requests while preserving operator control.

### 3. Context Assembly

Before generation, the subsystem assembles context from:

- repository state
- selected documents from DocumentStore
- persistent build memory
- persistent build rules
- current PR stage
- prior conversation/state retained by the ContextManager

DocumentStore is used for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

Rules governing prompt construction:

- external document context goes in the **USER** prompt, never the SYSTEM prompt
- all external content is untrusted and validated before use

ContextManager behavior:

- auto-trims at 30k tokens
- preserves:
  - spec-anchor first turn
  - last 6 messages

### 4. PR Planning and Sequencing

The build intent is decomposed into an ordered PR sequence. The build director coordinates stage progression per PR and records stage checkpoints in the ledger so completed work is not repeated after crashes.

Per-PR checkpoints are mandatory crash-recovery boundaries. On restart, the subsystem resumes from the last incomplete stage rather than re-running completed stages.

### 5. Code/Test Generation via Consensus Engine

For each PR, generation is executed through the consensus pipeline in `src/consensus.py`.

The subsystem uses two LLM providers in parallel for implementation/test generation, with Claude acting as arbiter per platform overview. The output of this phase is candidate code and test changes, not executable instructions.

Generated artifacts are then subject to:

- self-correction
- lint gate
- local fix loop

### 6. File Modification

Any file write produced by the generation/correction pipeline must be validated through:

- `path_security.validate_write_path()`

This validation occurs before execution of the write. No write may bypass this path validation requirement.

### 7. Validation, Fixing, and CI

After generation:

- lint gate runs
- self-correction runs
- a bounded fix loop runs for up to 20 local attempts

Failure handling follows the documented strategy in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary

Escalation rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- max 20 local attempts, then move on

CI output handling:

- CI logs truncated to 8k chars
- 70% head / 30% tail split
- automatic, no operator action required

Polling/network efficiency and rate limiting:

- ETag caching on all polling endpoints
- `403` primary rate limit:
  - exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary rate limit:
  - respect `Retry-After`

### 8. GitHub Operations

All GitHub operations are routed exclusively through `GitHubTool`.

This includes:

- reading repository state
- creating/updating PRs
- polling statuses
- handling webhooks

Direct GitHub API usage is prohibited within this subsystem. This keeps auth, retries, rate limiting, ETag behavior, and request semantics centralized.

### 9. Operator Gates and UI Streaming

The subsystem emits structured progress to the UI as `build_card` messages:

- `card_type`
- `stage`
- `content`
- `progress`

When human approval or direction is required, it emits `gate_card` messages:

- `gate_type`
- `options[]`
- `description`

Gate semantics are strict:

- gates block indefinitely until operator response
- no auto-approve ever

### 10. Persistent Learning Updates

After every successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

This file survives:

- fresh installs
- thread state wipes
- clean runs

It must not be deleted automatically.

After each build run, if 3 or more recurring failure patterns are found:

- update `Mac-Docs/build_rules.md`

This file is loaded automatically by DocumentStore and is also persistent. It must not be deleted on clean runs unless switching to a completely new codebase.

## Key Invariants

The following invariants are enforced by this subsystem and inherited from Forge platform rules.

### Security and Trust

- Fail closed on auth, crypto, and identity errors.
- Never silently degrade on security-sensitive paths.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- External document context is placed only in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is terminal for the attempted action:
  - no bypass by rephrasing
  - stop
  - gate
  - log
- Unknown XPC message types are discarded and logged, never raised.

### Human Control

- Operator approval gates wait indefinitely.
- No auto-approve path exists.
- Low-confidence scope requests must gate before implementation.

### File and Repository Safety

- All file writes must pass `path_security.validate_write_path()` before execution.
- All GitHub operations must go through `GitHubTool`.
- Direct GitHub API access is not permitted in this subsystem.

### Reliability and Recovery

- No silent failure paths; every error surfaces with context.
- Per-PR stage checkpoints prevent re-running completed work after crash/restart.
- Fix attempts are bounded to 20 local attempts.
- Polling uses ETag caching and explicit backoff/retry behavior.

### Persistence and Learning

- Build memory is persistent and must not be auto-cleared.
- Build rules are persistent and must not be auto-cleared under normal clean-run behavior.

## Failure Modes

### Scope Confidence Below Threshold

Condition:
- `SCOPE_SYSTEM` returns `confidence < 85`

Behavior:
- present `coverage_gaps`
- gate with proceed/answer/cancel
- allow one re-scope if operator supplies answers
- otherwise halt or continue only by explicit operator choice

This is not treated as a crash, but as a controlled ambiguity gate.

### Auth, Crypto, or Identity Failure

Condition:
- credential validation failure
- identity mismatch
- nonce/authentication failure on XPC
- crypto verification failure

Behavior:
- fail closed
- do not continue in degraded mode
- surface contextual error without leaking secrets

### Invalid or Unsafe Write Path

Condition:
- file write target fails `path_security.validate_write_path()`

Behavior:
- block write
- surface error
- do not attempt bypass or alternate direct write path

### Unsupported or Malformed XPC Input

Condition:
- unknown XPC message type
- malformed line-delimited JSON payload
- oversized payload beyond protocol limits

Behavior:
- unknown types are discarded and logged
- malformed input is rejected with context
- no exception escalation for unknown message classes

### GitHub/API Rate Limits or Transport Failures

Condition:
- `403` primary rate limit
- `429` secondary rate limit
- transient polling/network issues

Behavior:
- apply documented exponential backoff for `403`
- respect `Retry-After` for `429`
- use ETag caching for polling endpoints
- surface failures with context if unrecoverable

### Model Generation or Correction Failure

Condition:
- provider error
- arbitration failure
- invalid output
- repeated failed corrections

Behavior:
- route through failure strategy selection
- escalate by failure type and attempt count
- stop after 20 local attempts
- move to next controlled outcome rather than infinite retry

### CI/Test Failure

Condition:
- lint/test/build/CI errors

Behavior:
- summarize/truncate CI logs to bounded context
- feed failure into bounded fix loop
- if unresolved after max attempts, surface failure and gate/escalate as required

### Crash or Mid-Run Termination

Condition:
- process crash
- restart during PR execution

Behavior:
- resume from per-PR stage checkpoints
- do not re-run already completed stages

### SECURITY_REFUSAL

Condition:
- subsystem or provider emits `SECURITY_REFUSAL`

Behavior:
- terminate attempted path
- do not rephrase around refusal
- gate and log

## Dependencies

### Internal Forge Dependencies

- `src/build_director.py`
  - primary build orchestration
  - stage transitions
  - scope confidence gate
  - PR routing
- `src/consensus.py`
  - consensus engine
  - multi-provider generation
  - arbitration prompts/systems
- `src/github_tools.py`
  - all GitHub operations
  - webhook receiver
- `src/build_ledger.py`
  - checkpointing and recovery state
- `failure_handler.py`
  - strategy selection for fix-loop escalation
- `path_security.validate_write_path()`
  - mandatory file write path validation
- DocumentStore
  - repository/document context retrieval
  - automatic loading of `build_rules.md`
- ContextManager
  - token trimming and conversation retention

### External Services / Protocols

- LLM providers used by the consensus engine
- GitHub, exclusively through `GitHubTool`
- XPC peer processes using:
  - line-delimited JSON
  - nonce authentication
  - 16 MB message max

### Persistent Data Dependencies

- `workspace/{engineer_id}/build_memory.json`
  - cross-run build learning
  - updated after each successful PR
- `Mac-Docs/build_rules.md`
  - derived coding/build rules
  - updated when recurring failure patterns are detected
- DocumentStore-managed repository documents
  - including targeted loads such as `PRODUCT_CONTEXT.md`

### Required Credentials

The subsystem depends on credential material delivered through the `credentials` payload:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Credential handling must preserve the global invariant that secrets never appear in logs, errors, or generated code.