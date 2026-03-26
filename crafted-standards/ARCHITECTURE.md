# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is a native macOS AI coding agent responsible for turning a plain-language build intent into an operator-gated sequence of pull requests and associated implementation work.

At a subsystem level, it:

- accepts a build intent and repository context
- decomposes work into an ordered sequence of PRs
- performs scope analysis with a confidence gate
- retrieves supporting context from the document store
- generates implementation and tests using two LLM providers in parallel
- arbitrates generation via consensus
- runs self-correction, lint, and bounded fix-loop recovery
- executes CI
- presents progress and gate state to the UI over XPC
- waits for operator approval before merge-related progression
- persists cross-run learning in build memory and build rules
- checkpoints per-PR stage progress to avoid re-running completed work after crashes

The subsystem is explicitly human-gated. Gates block indefinitely for operator input; there is no auto-approve path.

## Component Boundaries

The subsystem boundary is defined by the orchestration and support components named in the Forge context.

### Included components

#### Build orchestration
- `src/build_director.py`
  - owns `BuildPipeline` orchestration
  - handles confidence gate behavior
  - performs `pr_type` routing

#### Consensus and generation systems
- `src/consensus.py`
  - owns `ConsensusEngine`
  - defines generation system prompts including:
    - `GENERATION_SYSTEM`
    - `SWIFT_GENERATION_SYSTEM`
    - `UI_ADDENDUM`

This component is responsible for parallel LLM generation and arbitration behavior referenced by the platform overview.

#### GitHub integration boundary
- `src/github_tools.py`
  - owns `GitHubTool`
  - owns `WebhookReceiver`

All GitHub operations are required to go through `GitHubTool`. Direct GitHub API use is outside subsystem contract.

#### Persistent build learning and state
- `src/build_ledger.py`
  - named as a Python backend file in the architecture context
- build memory
  - persisted at `workspace/{engineer_id}/build_memory.json`
  - updated after every successful PR via `build_memory.record_pr()`
- build rules
  - persisted at `Mac-Docs/build_rules.md`
  - loaded automatically by `DocumentStore`
  - updated after build runs when 3+ recurring failure patterns are found

#### Document context handling
- `DocumentStore`
  - used for generation context
  - supports loading specific documents such as `PRODUCT_CONTEXT.md`
  - automatically loads `build_rules.md`

#### Failure handling
- `failure_handler.py`
  - owns `_choose_strategy(failure_type, attempt, records)`

#### Prompt/context management
- `ContextManager`
  - auto-trims at 30k tokens
  - preserves the spec-anchor first turn and last 6 messages
  - truncates CI logs at 8k chars using 70% head / 30% tail

### External interfaces at the boundary

#### XPC protocol
The subsystem communicates state outward over XPC using line-delimited JSON with nonce authentication and a maximum size of 16 MB per message.

Referenced message shapes:
- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator responds
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are outside accepted protocol and must be discarded and logged.

### Explicit non-responsibilities

This subsystem does not:
- execute generated code
- `eval`, `exec`, or spawn subprocesses for generated content
- auto-approve gates
- silently continue after auth, crypto, identity, or security-refusal conditions
- write files without `path_security.validate_write_path()`
- place external document context into the SYSTEM prompt
- call GitHub APIs directly outside `GitHubTool`

## Data Flow

### 1. Session initialization
1. The subsystem establishes XPC communication using line-delimited JSON with nonce authentication.
2. It emits or processes `ready` protocol state including:
   - `agent_version`
   - `min_swift_version`
   - `capabilities`
   - `doc_store_status`
3. It receives `credentials` containing:
   - `anthropic_api_key`
   - `openai_api_key`
   - `github_token`
   - `engineer_id`

Auth, crypto, or identity failures fail closed.

### 2. Build intent intake and scope gating
1. A plain-language build intent is accepted.
2. The core loop performs scope analysis.
3. `SCOPE_SYSTEM` returns:
   - `confidence` in the range `0–100`
   - `coverage_gaps`
4. `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`.

If below threshold:
- the subsystem shows gaps
- offers `proceed`, `answer`, or `cancel`
- permits a one-shot re-scope if the operator provides gap answers
- does not enter an unbounded clarification loop

### 3. Context assembly
1. Repository and supporting documents are loaded via `DocumentStore`.
2. Specific documents may be loaded explicitly, such as `PRODUCT_CONTEXT.md`.
3. Build rules from `Mac-Docs/build_rules.md` are auto-loaded.
4. Build memory from `workspace/{engineer_id}/build_memory.json` contributes cross-run learning context.
5. External document context is inserted into the USER prompt only.

All external inputs, including documents, PR comments, and CI output, are treated as untrusted and validated.

### 4. PR decomposition and generation
1. The build intent is decomposed into an ordered sequence of PRs.
2. For each PR, `BuildPipeline` orchestrates stage progression.
3. Generation runs against two LLM providers in parallel.
4. `ConsensusEngine` arbitrates between the generated outputs.
5. Implementation and tests are produced for the PR.

Generated code is never executed by the agent.

### 5. Correction and local quality gates
For each PR, the subsystem performs:
1. a self-correction pass
2. a lint gate
3. a bounded local fix loop of up to 20 passes

Failure strategy is selected by `failure_handler.py` through `_choose_strategy(failure_type, attempt, records)`.

Documented selection rules:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely; stop local recovery after 20 attempts and move on

### 6. CI and output shaping
1. CI is executed after local quality steps.
2. CI output is treated as untrusted input.
3. CI log output is truncated automatically to 8k characters using 70% head / 30% tail.
4. Polling endpoints use ETag caching.
5. Rate-limit handling:
   - `403 primary` → exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
   - `429 secondary` → respect `Retry-After`

### 7. Operator gating and stream updates
1. Progress is streamed as `build_card` messages to `BuildStreamView`.
2. Any operator decision point is represented as a `gate_card`.
3. Gates block until operator response.
4. There is no auto-approve path.

### 8. File and repository mutation
1. Any file write must first pass `path_security.validate_write_path()`.
2. GitHub operations must go through `GitHubTool`.
3. Repository changes are applied only through those validated and bounded paths.

### 9. Persistence and crash recovery
1. Per-PR stage checkpoints prevent re-running completed work after a crash.
2. After every successful PR, build memory is written via `build_memory.record_pr()`.
3. After each build run, build rules are updated when 3 or more recurring failure patterns are identified.
4. Build memory and build rules are intentionally persistent and are not auto-cleared.

## Key Invariants

The subsystem enforces the following invariants.

### Security and trust
- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- External document context goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Generated code is never executed by the agent.

### Operator control
- Gates wait indefinitely for operator input.
- No auto-approve behavior exists.

### File and repository safety
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Protocol correctness
- XPC messages use line-delimited JSON.
- XPC messages are nonce-authenticated.
- Maximum XPC message size is 16 MB.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Build progression and recovery
- Per-PR stage checkpoints prevent rerunning completed work after crashes.
- Scope gating blocks low-confidence execution below threshold unless the operator explicitly proceeds.
- Local automated repair is bounded to 20 attempts; no infinite retry loops.

### Persistent learning
- `build_memory.json` survives fresh installs and thread state wipes.
- `build_memory.json` is not deleted on clean runs.
- `build_rules.md` is not deleted on clean runs unless switching to a completely new codebase.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

## Failure Modes

### Scope confidence failure
Condition:
- `_stage_scope` receives confidence below `_CONFIDENCE_THRESHOLD = 85`

Behavior:
- present coverage gaps
- offer `proceed`, `answer`, or `cancel`
- permit one-shot re-scope from operator-provided gap answers
- do not loop indefinitely

### Auth, crypto, or identity failure
Condition:
- failure in credentials, authentication, cryptographic verification, or identity handling

Behavior:
- fail closed
- do not degrade silently
- surface the error with context

### Security refusal
Condition:
- generation or validation yields `SECURITY_REFUSAL`

Behavior:
- stop processing
- gate for operator input
- log the event
- do not attempt bypass through rephrasing

### Unknown XPC message type
Condition:
- received message does not match known XPC protocol types

Behavior:
- discard message
- log occurrence
- do not raise exception

### File write validation failure
Condition:
- `path_security.validate_write_path()` rejects a write target

Behavior:
- block the write
- surface the error
- do not continue with an unvalidated write path

### GitHub operation boundary violation
Condition:
- attempted repository or GitHub action outside `GitHubTool`

Behavior:
- outside architecture contract
- must be prevented at implementation/review time

### Local generation/test/lint failure
Condition:
- assertion, import, runtime, lint, or similar local failure during PR processing

Behavior:
- select strategy through `_choose_strategy(failure_type, attempt, records)`
- escalate by failure type first, then attempt count
- cap retries at 20 local attempts
- move on rather than retry indefinitely

Strategy rules:
- `assertion_error` → `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- at attempt `>= 8` → `nuclear` every 3rd attempt

### Rate limiting and polling degradation
Condition:
- GitHub or related polling endpoints return rate limit responses

Behavior:
- `403 primary` → exponential backoff from 2s to 64s
- `429 secondary` → honor `Retry-After`
- use ETag caching on all polling endpoints

### Context overflow
Condition:
- accumulated prompt/context exceeds model budget

Behavior:
- `ContextManager` auto-trims at 30k tokens
- preserve spec-anchor first turn and last 6 messages
- truncate CI logs to 8k characters automatically

### Crash during PR execution
Condition:
- process interruption after partial PR-stage completion

Behavior:
- resume using per-PR stage checkpoints
- do not rerun already completed stages

## Dependencies

### Internal subsystem dependencies
- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` and generation system definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- `build_ledger` in `src/build_ledger.py`
- `failure_handler.py`
- `ContextManager`
- `DocumentStore`
- `path_security.validate_write_path()`

### External service dependencies
- Anthropic provider, via `anthropic_api_key`
- OpenAI provider, via `openai_api_key`
- GitHub, via `github_token`

### Persistent storage dependencies
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### UI/protocol dependencies
- XPC transport with:
  - line-delimited JSON
  - nonce authentication
  - 16 MB max message size
- `BuildStreamView` as the consumer of streamed `build_card` messages

### Input classes treated as dependencies and trust boundaries
- external documents
- PR comments
- CI output
- operator responses
- repository contents

All of these inputs are untrusted at ingress and must be validated according to subsystem invariants.