# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that executes the build workflow from plain-language intent to gated merge-ready pull requests.

At a subsystem level, ForgeAgent:

- accepts a build intent and decomposes it into an ordered sequence of pull requests
- performs scope analysis and enforces a scope confidence gate before implementation proceeds
- generates implementation and tests using two LLM providers in parallel, with Claude arbitrating
- runs a self-correction pass, a lint gate, and up to a 20-pass local fix loop
- executes CI and surfaces CI results
- blocks on explicit operator approval before merge-related progression
- persists cross-run learning through build memory and build rules
- resumes safely after crashes using per-PR stage checkpoints

ForgeAgent is human-gated. It does not auto-approve gates, and gates wait indefinitely for operator input.

## Component Boundaries

ForgeAgent is bounded by the orchestration, generation, persistence, and integration responsibilities explicitly described in the TRD material.

### Inside the subsystem

#### Build orchestration
- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - handles confidence gate behavior
  - routes by `pr_type`

#### Multi-model generation and arbitration
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines generation system prompts:
    - `GENERATION_SYSTEM`
    - `SWIFT_GENERATION_SYSTEM`
    - `UI_ADDENDUM`

#### GitHub integration
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`
  - all GitHub operations must go through `GitHubTool`

#### Build learning and persistence
- `build_memory.json`
  - persistent PR history
  - written after every successful PR via `build_memory.record_pr()`
  - stored at `workspace/{engineer_id}/build_memory.json`
- `build_rules.md`
  - persistent self-improving coding rules derived from build history
  - stored at `Mac-Docs/build_rules.md`
  - written after each build run when 3 or more recurring failure patterns are found
  - loaded automatically by `DocumentStore`

#### Failure handling
- `failure_handler.py`
  - strategy selection via `_choose_strategy(failure_type, attempt, records)`

#### Context management and document usage
- `DocumentStore`
  - used for generation context
  - loads documents such as `PRODUCT_CONTEXT.md`
  - automatically loads `build_rules.md`
- `ContextManager`
  - trims context automatically at 30k tokens
  - preserves the spec-anchor first turn and last 6 messages

#### Stage durability
- per-PR stage checkpoints
  - prevent rerunning completed work after a crash

### Outside the subsystem

ForgeAgent does not own:

- direct GitHub API usage outside `GitHubTool`
- execution of generated code by the agent
- bypassing operator decisions at gates
- trust decisions on external input without validation
- uncontrolled file system writes
- automatic clearing of build memory or build rules

## Data Flow

### 1. Build initiation
ForgeAgent starts from a plain-language build intent and decomposes work into an ordered PR sequence.

### 2. Scope analysis and gate
The scope stage evaluates coverage using the scope system.

Relevant behavior:
- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:
- the operator is shown the identified gaps
- options are:
  - proceed
  - answer
  - cancel
- if the operator provides gap answers, ForgeAgent performs a one-shot re-scope
- there is no repeated re-scope loop

### 3. Context assembly
ForgeAgent gathers generation context from:
- repository context
- document store content
- specific documents such as `PRODUCT_CONTEXT.md`
- persistent `build_rules.md`
- persistent `build_memory.json`

External document context is treated as untrusted input and must be placed in the USER prompt, never the SYSTEM prompt.

### 4. Generation and arbitration
ForgeAgent generates implementation and tests using two LLM providers in parallel. Claude performs arbitration.

Generation is controlled by the consensus subsystem in `src/consensus.py`.

### 5. Correction and local quality gates
After generation, ForgeAgent runs:
- a self-correction pass
- a lint gate
- a local fix loop

Failure handling is governed by `failure_handler.py`:
- primary signal: `failure_type`
- secondary signal: `attempt`

Decision rules:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- max 20 local attempts; never retry indefinitely

### 6. CI execution and output shaping
ForgeAgent executes CI and processes CI output.

Controls:
- CI log output is truncated at 8k characters
- truncation shape is 70% head / 30% tail
- no operator action is required for truncation behavior

### 7. Operator gate
ForgeAgent emits `gate_card` messages when operator input is required.

Protocol shape:
- `gate_card: { gate_type, options[], description }`

This stage blocks indefinitely until the operator responds. There is no auto-approve path.

### 8. Persistence and learning
After every successful PR:
- ForgeAgent records the PR in `build_memory.json` via `build_memory.record_pr()`

After each build run:
- if 3 or more recurring failure patterns are found, ForgeAgent writes `build_rules.md`

These learning artifacts persist across runs and fresh installs by design.

### 9. Crash recovery
Per-PR stage checkpoints ensure completed work is not rerun after a crash.

## Key Invariants

The following invariants are enforced by ForgeAgent and define its safety model:

- Fail closed on auth, crypto, and identity errors — never degrade silently
- No silent failure paths — every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input (documents, PR comments, CI output) is untrusted and validated
- Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content
- Gates wait indefinitely for operator input — no auto-approve ever
- All file writes are path-validated via `path_security.validate_write_path()` before execution
- Context from external documents goes in the USER prompt — never the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log
- XPC unknown message types are discarded and logged — never raised as exceptions
- Per-PR stage checkpoints prevent re-running completed work after a crash
- Build memory and build rules are never cleared automatically — they are persistent learning systems

Additional operating constraints from the protocol and runtime behavior:

- XPC wire format is line-delimited JSON
- XPC messages are nonce-authenticated
- maximum XPC message size is 16MB per message
- all GitHub operations go through `GitHubTool`
- all polling endpoints use ETag caching
- 403 primary rate limits use exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- 429 secondary rate limits honor the `Retry-After` header
- context is auto-trimmed at 30k tokens while preserving:
  - the spec-anchor first turn
  - the last 6 messages

## Failure Modes

### Scope confidence below threshold
Condition:
- scope confidence returned by `SCOPE_SYSTEM` is below 85

Behavior:
- show `coverage_gaps`
- gate the operator with proceed/answer/cancel
- if answers are supplied, perform one-shot re-scope
- do not enter an unbounded clarification loop

### Auth, crypto, or identity failure
Condition:
- any authentication, cryptographic, or identity error

Behavior:
- fail closed
- do not continue in degraded mode
- surface the error with context

### Path validation failure
Condition:
- a write target fails `path_security.validate_write_path()`

Behavior:
- write does not execute
- failure must surface explicitly

### Unsafe model output
Condition:
- model returns `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log
- do not bypass by rephrasing or retry phrasing tricks

### Unknown XPC message type
Condition:
- inbound XPC message type is unrecognized

Behavior:
- discard message
- log event
- do not raise as an exception

### Generation or repair loop exhaustion
Condition:
- local correction attempts reach the retry ceiling

Behavior:
- stop after 20 local attempts
- do not retry indefinitely
- move on according to pipeline handling

### Failure-strategy escalation
Condition:
- repeated local failures during correction

Behavior:
- strategy chosen by `_choose_strategy(failure_type, attempt, records)`
- escalation depends first on failure type, then attempt count
- from attempt 8 onward, every 3rd attempt may escalate to `nuclear`

### Rate limiting
Condition:
- GitHub or related polling endpoints return throttling responses

Behavior:
- 403 primary limit: exponential backoff up to 64 seconds
- 429 secondary limit: respect `Retry-After`
- use ETag caching on polling endpoints

### Oversized or long-running context
Condition:
- context size approaches token limit

Behavior:
- `ContextManager` trims automatically at 30k tokens
- preserves the spec-anchor first turn and last 6 messages

### CI output overload
Condition:
- CI logs are too large for direct inclusion

Behavior:
- truncate to 8k characters
- preserve 70% head and 30% tail

### Crash during PR processing
Condition:
- process interruption after some stages complete

Behavior:
- per-PR stage checkpoints prevent re-running completed work after restart

## Dependencies

### Internal code modules
- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `failure_handler.py`

### Persistent artifacts
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Runtime services and systems
- `DocumentStore`
- `ContextManager`
- `GitHubTool`
- `WebhookReceiver`
- XPC transport

### XPC protocol messages
- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### External providers and integrations
- two LLM providers used in parallel
- Claude used for arbitration
- GitHub, accessed only through `GitHubTool`

### Required security and control surfaces
- `path_security.validate_write_path()`
- operator approval gates
- nonce-authenticated XPC messaging