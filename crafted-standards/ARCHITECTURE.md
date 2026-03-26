# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding subsystem that executes the build workflow for Crafted Dev Agent. It accepts a plain-language build intent, scopes the work, decomposes it into an ordered sequence of pull requests, generates implementation and tests, runs validation and correction stages, executes CI, and pauses on explicit operator gates before merge.

Within that workflow, the subsystem is responsible for:

- orchestrating the build pipeline
- enforcing stage-by-stage execution with per-PR checkpoints
- using two LLM providers in parallel for generation, with Claude arbitration
- applying a scope confidence gate before implementation proceeds
- incorporating repository and document context into generation
- persisting cross-run learning via build memory and build rules
- surfacing progress and operator decisions over the XPC protocol
- routing all GitHub operations through the approved GitHub abstraction
- enforcing path validation before any file write
- handling failures with bounded retry and typed recovery strategies

The subsystem is not a general code execution environment. Generated code is produced and validated, but never executed directly by the agent via `eval`, `exec`, or subprocess execution of generated content.

## Component Boundaries

CraftedAgent is bounded by the following responsibilities and exclusions.

### Inside the subsystem

#### Build orchestration
- `src/build_director.py` owns BuildPipeline orchestration.
- It performs confidence gating and PR-type routing.
- It coordinates ordered PR execution and stage progression.

#### Consensus generation
- `src/consensus.py` provides `ConsensusEngine`.
- It defines generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`.
- It performs parallel generation across two LLM providers, with Claude arbitration.

#### GitHub integration
- `src/github_tools.py` provides `GitHubTool` and `WebhookReceiver`.
- All GitHub operations are mediated here.

#### Persistent learning
- Build memory persists at `workspace/{engineer_id}/build_memory.json`.
- It is written after every successful PR via `build_memory.record_pr()`.
- Build rules persist at `Mac-Docs/build_rules.md`.
- Build rules are written after each build run when 3 or more recurring failure patterns are found.

#### Operator interaction and transport
- XPC messages are line-delimited JSON, nonce-authenticated, and limited to 16MB per message.
- The subsystem emits:
  - `ready`
  - `build_card`
  - `gate_card`
  - `doc_status`
- Gates block indefinitely until operator response.

#### Failure handling
- `failure_handler.py:_choose_strategy(failure_type, attempt, records)` selects recovery strategy.
- Recovery is bounded to a maximum of 20 local attempts.

### Outside the subsystem

#### Direct GitHub API usage
- Forbidden. The subsystem must never use the GitHub API directly; it must use `GitHubTool`.

#### Silent auto-approval or autonomous merge decisions
- Forbidden. Operator gates wait indefinitely. No auto-approve path exists.

#### Execution of generated content
- Forbidden. The agent never executes generated code through dynamic evaluation or as a subprocess of generated content.

#### Trusting external inputs
- Forbidden. Documents, PR comments, and CI output are treated as untrusted input and validated.

#### Prompt elevation of external context
- Forbidden. Context from external documents is placed in the USER prompt only, never the SYSTEM prompt.

#### Automatic deletion of persistent learning state
- Forbidden. Build memory and build rules are persistent and are never cleared automatically.

## Data Flow

### 1. Session establishment
The subsystem initializes over XPC using line-delimited JSON messages with nonce authentication.

Relevant protocol payloads:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

This establishes versioning, capabilities, document store status, and provider credentials.

### 2. Scope and confidence gate
The build intent enters the core loop and is evaluated by the scope system.

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:
- the subsystem shows coverage gaps
- offers `proceed / answer / cancel`
- supports one-shot re-scope if the operator supplies gap answers
- does not enter an open-ended clarification loop

This stage determines whether implementation can proceed with sufficient scoped understanding.

### 3. Context assembly
The subsystem loads repository and document context for generation.

DocumentStore is used for the primary context path and can load specific documents such as `PRODUCT_CONTEXT.md`.

Additional persistent context includes:

- build memory from `workspace/{engineer_id}/build_memory.json`
- build rules from `Mac-Docs/build_rules.md`

Context shaping constraints:
- external document context goes into the USER prompt
- ContextManager auto-trims at 30k tokens
- the spec-anchor first turn and last 6 messages are preserved

### 4. PR planning and staged execution
The build is decomposed into an ordered sequence of pull requests.

Per-PR stage checkpoints ensure completed work is not rerun after a crash.

For each PR, the subsystem advances through the build pipeline stages, emits progress to the UI, and blocks at required gates.

Progress is streamed via:

- `build_card`
  - `{ card_type, stage, content, progress }`

### 5. Code and test generation
Generation is performed through the consensus path:

- two LLM providers run in parallel
- Claude arbitrates output
- repository context, documents, build memory, and build rules inform the generation step

The subsystem then performs:
- self-correction
- lint gate
- a 20-pass fix loop
- CI execution

### 6. Failure-guided correction
When failures occur, recovery strategy is selected by failure type first and attempt count second.

`_choose_strategy(failure_type, attempt, records)` applies these rules:

- `assertion_error` → `test_driven` immediately
- `import_error` or `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Related transport and context limits:
- CI log output truncated at 8k chars using 70% head / 30% tail
- polling endpoints use ETag caching
- `403` primary uses exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary respects `Retry-After`

### 7. Operator gating
When human approval is required, the subsystem emits:

- `gate_card`
  - `{ gate_type, options[], description }`

This gate blocks indefinitely until operator input is received. There is no auto-approval path.

### 8. Persistence
After every successful PR:
- build memory is written via `build_memory.record_pr()`

After each build run, if 3 or more recurring failure patterns are detected:
- build rules are written to `Mac-Docs/build_rules.md`

These artifacts intentionally persist across fresh installs, thread state wipes, and clean runs.

## Key Invariants

The subsystem enforces the following invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents is placed in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional operational constraints:

- All GitHub operations go through `GitHubTool`.
- Validate paths before any write.
- Scope confidence must meet the `_CONFIDENCE_THRESHOLD = 85` or explicitly gate.
- Retry is bounded to 20 local attempts maximum.
- ContextManager trims automatically at 30k tokens while preserving required anchors.

## Failure Modes

### Scope confidence below threshold
Condition:
- `SCOPE_SYSTEM` returns confidence below `85`

Behavior:
- coverage gaps are surfaced
- operator is offered `proceed / answer / cancel`
- a single re-scope pass may occur if gap answers are provided

Enforcement:
- implementation does not silently continue as if the scope were complete

### Auth, crypto, or identity failure
Condition:
- credential, cryptographic, or identity validation error

Behavior:
- fail closed
- do not degrade to partial or anonymous behavior

Enforcement:
- error must surface with context

### Security refusal
Condition:
- generation or processing emits `SECURITY_REFUSAL`

Behavior:
- stop, gate, and log

Enforcement:
- no bypass by paraphrase or re-prompting around the refusal

### Unknown XPC message type
Condition:
- incoming XPC payload has an unknown message type

Behavior:
- discard and log

Enforcement:
- never raise as an exception path

### Invalid write path
Condition:
- a file write has not passed `path_security.validate_write_path()`

Behavior:
- write must not execute

Enforcement:
- applies to all writes

### GitHub transport throttling or denial
Condition:
- `403` primary or `429` secondary responses

Behavior:
- `403`: exponential backoff through `64s`
- `429`: honor `Retry-After`
- polling uses ETag caching

Enforcement:
- bounded, protocol-aware retry behavior

### Test or runtime failure during fix loop
Condition:
- local validation or CI indicates failure

Behavior:
- strategy chosen by failure type:
  - assertion failures go directly to test-driven correction
  - import/runtime failures start with converse, then test-driven
  - at higher attempt counts, periodic nuclear strategy is used
- hard stop after 20 local attempts

Enforcement:
- no infinite local retry loop

### Crash during PR execution
Condition:
- process interruption after some stages complete

Behavior:
- per-PR stage checkpoints prevent rerunning completed work

Enforcement:
- recovery resumes from durable stage state rather than replaying finished stages

### Oversized or noisy context
Condition:
- prompt context exceeds practical limits or CI output is too large

Behavior:
- ContextManager trims at 30k tokens
- CI logs truncate to 8k chars with 70/30 head-tail split

Enforcement:
- automatic containment without changing invariant-preserved anchors

## Dependencies

The subsystem depends on the following defined components and interfaces.

### Internal modules
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - PR-type routing
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

### Persistent stores
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Supporting services and protocols
- XPC transport using line-delimited JSON
- nonce-authenticated messaging
- DocumentStore for document loading and context assembly
- BuildStreamView as the consumer of streamed `build_card` messages

### External credentials
- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

### Required enforcement utilities
- `path_security.validate_write_path()`

### External systems accessed through approved boundaries
- GitHub, exclusively via `GitHubTool`
- LLM providers, used in parallel by the consensus path
- CI systems, whose output is consumed as untrusted input and truncated for bounded context use