# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s macOS native AI coding agent. It coordinates the complete lifecycle from operator build intent to gated merge, spanning:

- scope interpretation and confidence gating
- document/context loading
- PR-plan decomposition
- code and test generation using multiple LLM providers
- arbitration and self-correction
- lint and iterative fix loops
- CI execution and result handling
- operator gates and approval
- GitHub PR lifecycle operations
- persistent learning via build memory and build rules
- crash-safe checkpointing across per-PR stages

Operationally, this subsystem is the top-level runtime that turns a plain-language request into an ordered sequence of pull requests, while preserving Forge-wide security, validation, checkpointing, and human-in-the-loop constraints.

It is responsible for enforcing that:

- no generated code is executed by the agent
- all external input is treated as untrusted
- all merge decisions remain operator-gated
- auth/identity/crypto failures fail closed
- completed PR stages are not re-run after crash/restart
- persistent learning artifacts are retained across runs

## Component Boundaries

FullPlatform includes orchestration logic and policy enforcement across the following components.

### Included Responsibilities

#### Build orchestration
Primarily implemented in:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR-type routing
- `src/consensus.py` — consensus generation/arbitration systems and generation system prompts
- `src/build_ledger.py` — stage/checkpoint persistence for crash recovery

This layer owns stage sequencing, gate presentation, retry boundaries, provider coordination, and progression across PRs.

#### Scope confidence gate
FullPlatform includes the pre-implementation scoping flow:

- `SCOPE_SYSTEM` produces:
  - `confidence` in range `0–100`
  - `coverage_gaps`
- `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`

If below threshold, the subsystem must surface gaps and offer exactly these operator paths:

- proceed
- answer
- cancel

If the operator answers coverage gaps, only a one-shot re-scope is performed. There is no unbounded re-scoping loop.

#### Document/context integration
FullPlatform is responsible for acquiring build context from the document store and injecting it into generation flows correctly.

Primary usage includes:

- retrieving contextual documents for generation
- loading specific documents such as `PRODUCT_CONTEXT.md`
- ensuring external document content is placed in the `USER` prompt, never the `SYSTEM` prompt

#### Persistent learning
FullPlatform owns integration with the persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

It records successful PR outcomes to build memory after every successful PR via `build_memory.record_pr()` and consumes persistent build rules loaded automatically by the document store.

This subsystem must not automatically clear either artifact.

#### GitHub lifecycle operations
FullPlatform coordinates repository operations only through:

- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`

All GitHub interactions for branches, PRs, comments, status inspection, and merge-related actions must route through `GitHubTool`. Direct GitHub API access is out of bounds.

#### Operator gating and UI protocol emission
FullPlatform emits protocol messages for UI/build-stream presentation and blocking gates:

- `build_card` — streamed progress/status content
- `gate_card` — operator decision points that block indefinitely until answered

It also participates in startup/session protocol exchange such as:

- `ready`
- `credentials`
- `doc_status`

### Excluded Responsibilities

FullPlatform does **not** own:

- low-level XPC transport implementation, beyond obeying the protocol contract
- direct secret storage implementation
- direct execution of generated code
- direct GitHub API usage outside `GitHubTool`
- automatic approval or merge bypass logic
- automatic deletion/reset of build memory or build rules
- treating unknown XPC message types as exceptional control flow

Those concerns belong to transport/security/utilities or are explicitly prohibited by system invariants.

## Data Flow

### 1. Session initialization
The subsystem starts after transport/session establishment and consumes protocol-level startup inputs such as:

- `ready`:  
  `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`:  
  `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Credentials are used for provider and GitHub access, but secrets must never appear in logs, error messages, or generated code.

### 2. Intent ingestion and scoping
The operator supplies a plain-language build intent. FullPlatform:

1. evaluates scope using the scope system
2. receives `confidence` and `coverage_gaps`
3. applies the threshold gate at `85`

If below threshold, a blocking `gate_card` is shown with gap details and operator options:

- proceed
- answer
- cancel

If answers are provided, the subsystem performs a single re-scope pass and then continues or exits based on the new result and operator choice.

### 3. Context acquisition
Before generation, FullPlatform loads contextual material from the document store, including project-specific sources such as `PRODUCT_CONTEXT.md` and automatically available files like `build_rules.md`.

All such external content is untrusted. It must be validated/sanitized according to the subsystem’s input-handling rules and placed only in user-context prompts.

Document ingestion/status may be represented through `doc_status` messages:

- `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### 4. PR decomposition and stage execution
The build intent is decomposed into an ordered sequence of PRs. For each PR, FullPlatform executes staged work under checkpoint control.

Per-PR stage checkpoints ensure that after a crash or restart, completed work is not repeated. This is a hard recovery invariant.

Typical stage progression includes:

1. scope/context establishment
2. implementation and test generation
3. provider consensus/arbitration
4. self-correction
5. lint gate
6. fix loop
7. CI execution
8. operator gate
9. merge or stop

Progress is streamed through `build_card` messages:

- `{ card_type, stage, content, progress }`

### 5. Multi-provider generation and arbitration
Generation is performed with two LLM providers in parallel, with Claude acting as arbiter per platform overview.

`src/consensus.py` provides the consensus engine and generation system definitions, including specialized system prompts for Swift/UI generation.

FullPlatform is responsible for:

- invoking provider generation paths
- collecting outputs
- arbitrating/choosing results
- preserving prompt-boundary rules
- ensuring generated code is treated as data, never executable input to the agent runtime

### 6. Correction and local quality loop
After initial generation, the subsystem runs:

- a self-correction pass
- a lint gate
- up to a 20-pass local fix loop

Failure strategy selection is driven by `failure_handler.py` semantics:

- `_choose_strategy(failure_type, attempt, records)`
- primary signal: `failure_type`
- secondary escalation: `attempt`

Required strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely; max `20` local attempts, then move on

### 7. CI execution and result handling
The subsystem runs CI and consumes CI output as untrusted external input.

Relevant handling constraints:

- CI log output truncated at `8k` chars
- truncation preserves `70%` head / `30%` tail
- no action required from callers; truncation is automatic

Polling and remote status handling must respect:

- `403` on primary endpoints → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429` on secondary endpoints → respect `Retry-After`
- ETag caching on all polling endpoints

### 8. Operator gating and merge
The subsystem presents gate decisions through `gate_card` and waits indefinitely for operator input. There is no auto-approve path.

Only after operator approval may merge-related GitHub actions proceed, and those actions must still be executed exclusively through `GitHubTool`.

### 9. Persistent learning update
After every successful PR:

- `build_memory.record_pr()` writes to `workspace/{engineer_id}/build_memory.json`

After each build run, if `3+` recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is updated

Neither persistent artifact is automatically deleted on clean runs.

## Key Invariants

The following invariants are enforced by FullPlatform and are non-negotiable.

### Security and trust boundaries

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated, including:
  - documents
  - PR comments
  - CI output
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.

### Code generation safety

- Generated code is never executed by the agent.
- No `eval`, `exec`, or subprocess execution of generated content is permitted.

### Human-in-the-loop enforcement

- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Merge progression is blocked until explicit operator action is received.

### File and repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Transport/protocol robustness

- XPC wire format is line-delimited JSON.
- Messages are nonce-authenticated.
- Maximum message size is `16MB`.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Recovery and persistence

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory is persistent and survives fresh installs and thread-state wipes.
- Build rules are persistent, self-improving rules derived from build history.
- Build memory and build rules are never cleared automatically.

### Context management constraints

- `ContextManager` auto-trims at `30k` tokens.
- It preserves:
  - the spec-anchor first turn
  - the last 6 messages

## Failure Modes

### Low scope confidence
Condition:
- scope confidence `< 85`

Behavior:
- block progression
- show coverage gaps
- require operator choice to proceed, answer, or cancel
- if answers are provided, perform one re-scope only

Failure posture:
- no silent continuation as if confidence were sufficient

### Auth, crypto, or identity failure
Condition:
- invalid or missing credentials
- authentication failure
- identity ambiguity
- cryptographic validation failure

Behavior:
- fail closed
- stop affected operation
- surface explicit contextual error
- do not downgrade to partial or anonymous behavior

### Untrusted or malformed external input
Condition:
- malformed document/CI/comment input
- prompt-injection-like content
- invalid protocol payload

Behavior:
- validate before use
- reject or sanitize as appropriate
- never promote external content to system-level instruction authority

### Unknown XPC message type
Condition:
- message type not recognized by the subsystem

Behavior:
- discard and log
- do not throw as an exception
- do not terminate normal processing solely due to unknown type

### Write-path violation
Condition:
- attempted filesystem write fails `path_security.validate_write_path()`

Behavior:
- abort the write
- surface the violation with context
- do not attempt alternate unvalidated write paths

### GitHub API/rate-limit failures
Condition:
- GitHub operation failure, including rate limiting

Behavior:
- all operations remain mediated by `GitHubTool`
- `403` primary endpoints use exponential backoff up to `64s`
- `429` secondary endpoints respect `Retry-After`
- polling uses ETag caching
- errors surface with context rather than being swallowed

### Generation/correction loop exhaustion
Condition:
- local fix loop reaches max attempts (`20`)

Behavior:
- do not retry indefinitely
- advance to the next handling path or fail the PR stage explicitly
- preserve failure context for operator visibility and learning systems

### Test/runtime/import/assertion failures
Condition:
- build/test failures during local correction

Behavior:
- strategy selection follows `failure_handler.py`
- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- after attempt `>= 8`, every 3rd attempt may escalate to `nuclear`

### Crash/restart during staged execution
Condition:
- process interruption after one or more completed PR stages

Behavior:
- resume from ledger/checkpoint state
- do not re-run completed stages
- continue with remaining incomplete work only

### Oversized or verbose context
Condition:
- prompt/context growth beyond token budget

Behavior:
- `ContextManager` trims automatically at `30k` tokens
- preserve first-turn spec anchor and last six messages
- avoid uncontrolled context expansion

## Dependencies

### Internal modules

- `src/build_director.py`
  - primary orchestration entrypoint
  - scope gate enforcement
  - PR routing and stage progression

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts
  - arbitration across provider outputs

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
  - sole allowed path for GitHub operations

- `src/build_ledger.py`
  - per-PR checkpoint/state persistence
  - crash recovery support

- `failure_handler.py`
  - failure-strategy selection for iterative correction

- `path_security.validate_write_path()`
  - mandatory validation for all file writes

- `ContextManager`
  - token-budget trimming and message preservation policy

- `DocumentStore`
  - retrieval of contextual documents
  - automatic loading of `build_rules.md`

- build memory subsystem
  - persistence at `workspace/{engineer_id}/build_memory.json`
  - successful-PR learning updates

### External providers and services

- LLM provider integrations:
  - Anthropic
  - OpenAI

- GitHub
  - accessed only through `GitHubTool`

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - max `16MB` per message

### Persistent artifacts

- `workspace/{engineer_id}/build_memory.json`
  - persistent per-engineer build learning store
  - must survive fresh installs and thread resets

- `Mac-Docs/build_rules.md`
  - persistent learned coding-rule corpus
  - updated when recurring failure patterns justify rule extraction

### Boundary note

FullPlatform depends on these components to perform orchestration, but it does not relax their contracts. In particular, any dependency failure that touches authentication, identity, cryptographic validation, path safety, or operator approval must preserve the subsystem’s fail-closed behavior.