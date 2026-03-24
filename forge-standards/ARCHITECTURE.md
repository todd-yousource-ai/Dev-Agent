# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated, pull-request-based implementation workflow.

Within the platform, ForgeAgent:

- decomposes build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitration layer for consensus
- runs a self-correction pass
- runs a lint gate
- runs a 20-pass fix loop
- executes CI
- blocks on operator approval before merge
- persists per-PR progress so completed work is not re-run after a crash
- preserves cross-run learning via persistent build memory and build rules

The subsystem is explicitly human-gated. Gates wait indefinitely for operator input; there is no auto-approve behavior.

ForgeAgent also integrates document and repository context into generation, but external context is treated as untrusted input and must be validated. Context from external documents is placed in the USER prompt only, never in the SYSTEM prompt.

## Component Boundaries

ForgeAgent spans the build orchestration, generation consensus, repository interaction, checkpointing, and persistent learning surfaces identified in the TRD.

### In scope

#### Build orchestration
Defined in:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing

Responsibilities:

- stage execution across the core loop
- scope-confidence gating
- PR-type routing
- operator gating
- enforcing the ordered PR workflow

#### Consensus and generation control
Defined in:

- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

Responsibilities:

- parallel generation with two LLM providers
- arbitration through Claude
- application of generation system prompts
- ensuring external document context is injected only into the USER prompt

#### GitHub interaction
Defined in:

- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`

Responsibilities:

- all GitHub operations
- repository-facing actions for PRs and related workflows

Boundary rule:

- all GitHub operations go through `GitHubTool`
- the GitHub API is never used directly outside this interface

#### Checkpointing and build history
Defined in part by:

- `src/build_ledger.py`

Responsibilities:

- per-PR stage checkpoints
- crash recovery without replaying completed stages

#### Persistent learning
Artifacts:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

Responsibilities:

- storing cross-run build memory via `build_memory.record_pr()`
- storing self-improving coding rules derived from build history

Boundary rule:

- build memory and build rules are persistent learning systems
- they are never cleared automatically
- they are not deleted on clean runs
- `build_rules.md` is deleted only when switching to a completely new codebase

#### Document context usage
Responsibilities:

- loading repository and product context for generation
- automatic loading of `Mac-Docs/build_rules.md` by `DocumentStore`
- use of specific documents such as `PRODUCT_CONTEXT.md`

Boundary rule:

- external document context is generation input only
- it must not be elevated into the SYSTEM prompt

### Out of scope

The following are outside ForgeAgent’s authority, even if consumed by it:

- operator judgment and approval decisions
- execution of generated code as agent instructions
- any direct GitHub API usage bypassing `GitHubTool`
- auto-approval or auto-merge without gate completion
- automatic clearing of persistent learning artifacts

## Data Flow

### 1. Session initialization and transport
ForgeAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

Initial capability exchange uses:

- `ready` message  
  `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

Unknown XPC message types are discarded and logged; they are never raised as exceptions.

### 2. Credential intake
ForgeAgent receives credentials in the structured form:

- `credentials`  
  `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Credentials are sensitive inputs and must never appear in logs, error messages, or generated code.

### 3. Build intent intake and scoping
A plain-language build intent enters the build pipeline. ForgeAgent performs scope analysis and evaluates confidence.

The scope gate behavior is defined as:

- `SCOPE_SYSTEM` returns `confidence` from 0–100 and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- gaps are shown to the operator
- options are `proceed`, `answer`, or `cancel`
- if the operator provides gap answers, one one-shot re-scope is performed
- there is no looping re-scope cycle

### 4. Context assembly
Generation context may include:

- repository context
- document-store context
- specific documents such as `PRODUCT_CONTEXT.md`
- persistent build memory
- persistent build rules

Context handling constraints:

- external input is untrusted and validated
- document context from external documents goes into the USER prompt only
- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn plus the last 6 messages
- CI log output is truncated to 8k characters using a 70% head / 30% tail split

### 5. Parallel generation and arbitration
ForgeAgent generates implementation and tests using two LLM providers in parallel. Claude arbitrates between candidate outputs through the consensus engine.

This stage is governed by the generation system configuration in `src/consensus.py`.

### 6. Correction, lint, and fix loop
After generation, ForgeAgent executes:

- a self-correction pass
- a lint gate
- a local fix loop with a maximum of 20 attempts

Failure handling is selected by `failure_handler.py` through:

- `_choose_strategy(failure_type, attempt, records)`

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

### 7. CI and external polling behavior
ForgeAgent executes CI and consumes CI output as untrusted external input.

Network and polling rules include:

- `403` primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary: respect `Retry-After` header
- ETag caching on all polling endpoints

### 8. Operator gating
ForgeAgent emits structured UI cards during execution:

- `build_card`  
  `{ card_type, stage, content, progress }`  
  streamed to `BuildStreamView`

- `gate_card`  
  `{ gate_type, options[], description }`  
  blocks until the operator responds

Gates wait indefinitely for operator input. No auto-approve path exists.

### 9. Repository mutation and persistence
Any repository write is subject to path validation before execution:

- all file writes must pass `path_security.validate_write_path()`

GitHub operations are executed only through `GitHubTool`.

After each successful PR:

- build memory is written via `build_memory.record_pr()`
- the file is stored at `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is written or updated

### 10. Recovery
Per-PR stage checkpoints ensure that after a crash, completed work is not re-run.

## Key Invariants

ForgeAgent enforces the following subsystem invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, and no subprocess execution of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Prompting and context isolation

- Context from external documents goes in the USER prompt only.
- External document context is never placed in the SYSTEM prompt.
- Generation system prompts are controlled through the consensus subsystem definitions.

### Human control

- Gates wait indefinitely for operator input.
- No auto-approve ever.

### Repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`.
- Direct GitHub API usage is prohibited.

### Transport and protocol robustness

- XPC uses line-delimited JSON, nonce-authenticated, with a 16 MB maximum message size.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Execution durability

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### Retry and bounded repair

- Failure handling is strategy-driven by failure type first, then attempt count.
- Retry behavior is bounded to 20 local attempts.
- External polling uses explicit backoff and cache semantics.

## Failure Modes

### Scope confidence below threshold
Condition:

- `_stage_scope` receives `confidence < 85`

Behavior:

- present `coverage_gaps`
- gate operator with `proceed`, `answer`, or `cancel`
- allow one one-shot re-scope if answers are provided
- do not enter an unbounded clarification loop

### Auth, crypto, or identity failure
Condition:

- authentication, cryptographic verification, or identity validation error

Behavior:

- fail closed
- do not degrade functionality silently
- surface the error with context

### Security refusal
Condition:

- generation or policy path returns `SECURITY_REFUSAL`

Behavior:

- stop processing
- gate
- log
- do not retry by rephrasing around the refusal

### Unknown XPC message type
Condition:

- inbound XPC message type is not recognized

Behavior:

- discard
- log
- do not raise an exception

### Path validation failure
Condition:

- write target fails `path_security.validate_write_path()`

Behavior:

- block the write
- surface the failure
- do not attempt the write through alternate paths

### Generation/test/lint/runtime failure
Condition:

- local validation fails during correction or fix loop

Behavior:

- choose strategy via `_choose_strategy(failure_type, attempt, records)`
- escalate based on failure type and attempt count
- stop local retries after 20 attempts
- move on rather than retry indefinitely

### Rate limiting or polling throttling
Condition:

- `403` primary or `429` secondary from polled endpoints

Behavior:

- apply exponential backoff for `403` primary
- honor `Retry-After` for `429` secondary
- use ETag caching on all polling endpoints

### Crash or restart during a PR stage
Condition:

- process interruption after partial stage completion

Behavior:

- resume from per-PR stage checkpoints
- do not re-run completed work

### Persistent learning artifact misuse
Condition:

- clean run or reset path attempts to delete learning state

Behavior:

- do not automatically clear `build_memory.json`
- do not automatically clear `build_rules.md`
- only remove `build_rules.md` when switching to a completely new codebase

## Dependencies

### Internal modules

- `src/build_director.py`
  - `BuildPipeline`
  - confidence gate
  - `pr_type` routing

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

- `src/build_ledger.py`

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

- `path_security.validate_write_path()`

- `ContextManager`

- `DocumentStore`

- `build_memory.record_pr()`

### Persistent files and stores

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External integrations and protocols

- XPC transport with line-delimited JSON and nonce authentication
- two LLM providers for parallel generation
- Claude as arbitration provider
- GitHub, accessed exclusively through `GitHubTool`
- CI systems, whose output is consumed as untrusted input

### UI protocol messages

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`