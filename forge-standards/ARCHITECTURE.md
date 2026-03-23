# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS AI coding agent. It owns the lifecycle that transforms a plain-language build intent into staged, reviewable pull requests with human gating and persistent learning across runs.

At a high level, this subsystem:

- accepts operator-provided build intent and repository context
- decomposes work into an ordered PR plan
- performs scope analysis and confidence gating before implementation
- gathers contextual inputs from repository state, document store, prior build memory, and build rules
- runs parallel code generation through multiple LLM providers, with arbitration
- executes validation and correction stages:
  - self-correction
  - lint gate
  - bounded fix loop
  - CI execution
- presents progress and gate states to the macOS UI over XPC
- blocks indefinitely for operator decisions at approval gates
- persists per-PR stage checkpoints for crash recovery
- records successful outcomes into persistent build learning artifacts

This subsystem is orchestration-centric. It coordinates planning, generation, validation, GitHub interaction, operator gating, and persistence, but it does not relax platform security rules and must fail closed on any auth, crypto, or identity fault.

## Component Boundaries

FullPlatform spans orchestration, coordination, and persistence for a build run. It is not the place for direct provider-specific API usage, unsafe filesystem access, or direct GitHub API calls.

### In scope

#### Build orchestration
Implemented primarily in:

- `src/build_director.py`
  - owns `BuildPipeline`
  - routes by PR type
  - performs confidence gating
  - sequences stages

Responsibilities include:

- stage ordering
- PR-by-PR execution
- gate presentation and handling
- checkpoint-aware resume behavior
- bounded retry/fix policies
- CI progression management

#### Consensus and generation coordination
Implemented primarily in:

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompts such as `GENERATION_SYSTEM`
  - Swift/UI generation prompt variants such as `SWIFT_GENERATION_SYSTEM` and `UI_ADDENDUM`

Responsibilities include:

- invoking multiple LLM providers in parallel
- arbitration of generation outputs
- constructing generation context
- enforcing prompt-placement rules for external document context

#### GitHub operation mediation
Implemented primarily in:

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

Responsibilities include:

- all repository and PR operations
- webhook/event ingestion
- polling behavior with caching and rate-limit handling

Constraint:

- all GitHub operations must flow through `GitHubTool`
- direct GitHub API use is outside subsystem policy

#### Build persistence and learning
From repository guidance and architecture context:

- per-PR stage checkpoints in build ledger/state
- persistent build memory:
  - `workspace/{engineer_id}/build_memory.json`
- persistent build rules:
  - `Mac-Docs/build_rules.md`

Responsibilities include:

- crash-safe stage resumption
- post-success PR learning capture via `build_memory.record_pr()`
- carrying learning across fresh installs and thread state wipes
- deriving coding rules from repeated failure patterns

#### Document context integration
FullPlatform consumes document store outputs for generation context and status reporting.

Responsibilities include:

- loading contextual documents for generation
- consuming document status such as:
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`
- ensuring untrusted document content is treated as external input

#### UI protocol participation
Over XPC, FullPlatform emits and consumes protocol messages such as:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

Responsibilities include:

- streaming build progress to `BuildStreamView`
- surfacing blocking gates
- receiving operator responses and credentials
- discarding unknown XPC message types safely

### Out of scope

FullPlatform does **not**:

- execute generated code via `eval`, `exec`, or subprocess invocation of generated content
- bypass operator approval gates
- write files without prior path validation
- place external document context into SYSTEM prompts
- directly own low-level auth/crypto primitives
- silently recover from identity, auth, or crypto errors
- clear build memory or build rules automatically
- treat unknown XPC messages as exceptions

## Data Flow

### 1. Session establishment

The subsystem initializes over XPC using line-delimited JSON messages with nonce authentication and a maximum message size of 16 MB.

Expected startup message:

- `ready: { agent_version, min_swift_version, capabilities[], doc_store_status }`

Credential intake occurs through:

- `credentials: { anthropic_api_key, openai_api_key, github_token, engineer_id }`

Security requirements at this stage:

- fail closed on auth, crypto, and identity errors
- never log secrets
- do not continue on malformed or unauthenticated protocol input

### 2. Intent intake and scoping

The operator supplies build intent. FullPlatform performs scope analysis before implementation.

Scope gate behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` in range `0–100`
  - `coverage_gaps`
- `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the subsystem shows identified gaps
- offers operator choices:
  - proceed
  - answer
  - cancel
- if the operator answers gaps, one re-scope pass is allowed
- no indefinite re-scope loop is permitted

This stage converts ambiguous intent into an execution plan while preserving human control.

### 3. Context assembly

FullPlatform assembles generation context from:

- repository state
- selected documents from DocumentStore
- persistent `build_memory.json`
- persistent `build_rules.md`
- PR/stage history and checkpoints

Rules for context handling:

- all external input is untrusted and validated
- context from external documents goes into the USER prompt only
- never place external document content into the SYSTEM prompt
- context window trimming is automatic at 30k tokens
- context preservation keeps:
  - the spec-anchor first turn
  - the last 6 messages

### 4. PR decomposition and staged execution

The build intent is decomposed into an ordered sequence of PRs. For each PR, FullPlatform executes staged work with persisted checkpoints so completed stages are not re-run after a crash.

Typical per-PR flow:

1. scope / plan confirmation
2. generation via parallel LLM providers
3. arbitration by consensus
4. self-correction
5. lint gate
6. local fix loop, bounded to 20 attempts
7. CI execution
8. operator approval gate
9. merge via GitHubTool
10. post-success learning persistence

Progress is streamed via:

- `build_card: { card_type, stage, content, progress }`

Blocking approvals are presented via:

- `gate_card: { gate_type, options[], description }`

### 5. Generation and arbitration

The subsystem invokes multiple LLM providers in parallel and uses Claude as the arbiter per platform overview.

Consensus responsibilities include:

- comparing candidate implementations
- selecting or synthesizing the best result
- applying generation prompt variants based on target type, including Swift/UI cases

Hard constraint:

- generated code is never executed by the agent as code-generation output

### 6. Validation, correction, and failure strategy

After generation, FullPlatform performs automated validation and bounded correction.

Failure handling policy includes:

- `_choose_strategy(failure_type, attempt, records)` in `failure_handler.py`
- primary signal is `failure_type`
- secondary signal is `attempt`

Required routing:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

Ancillary runtime controls:

- CI log output truncated to 8k chars
  - 70% head
  - 30% tail
- no action required by callers; truncation is automatic

### 7. GitHub and CI interaction

Repository operations, PR creation, status polling, and merge actions flow through `GitHubTool`.

Operational requirements:

- all GitHub ops go through `GitHubTool`
- path validation occurs before any file write
- polling endpoints use ETag caching
- `403` from primary path uses exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429` from secondary path respects `Retry-After`

### 8. Human gate and completion

Before merge, FullPlatform blocks on operator approval.

Invariant behavior:

- gates wait indefinitely for operator input
- no auto-approve ever

On successful PR completion:

- persist stage completion
- record PR outcome in `build_memory.json`
- potentially update `build_rules.md` when 3 or more recurring failure patterns are detected

Persistence is intentionally long-lived and cross-run.

## Key Invariants

The following invariants are mandatory for FullPlatform:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and must be validated, including:
  - documents
  - PR comments
  - CI output
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve.
- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents belongs only in USER prompts, never SYSTEM prompts.
- `SECURITY_REFUSAL` output is terminal for that path: stop, gate, and log; do not bypass by rephrasing.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints must prevent re-running completed work after crash/restart.
- Build memory and build rules are persistent learning systems and are never cleared automatically.
- All GitHub operations must be mediated by `GitHubTool`.
- Scope confidence below threshold must gate operator interaction before implementation proceeds.
- Fix/correction loops are bounded; local attempts max out at 20.

## Failure Modes

### Authentication, crypto, or identity failure
Behavior:

- fail closed immediately
- do not continue with degraded trust
- surface explicit error context without leaking secrets

### Malformed or unknown XPC input
Behavior:

- malformed authenticated payloads should surface as protocol errors
- unknown message types are discarded and logged
- they must not crash the subsystem by exception propagation

### Low-confidence scoping
Behavior:

- block progression at scope gate when confidence is below 85
- present coverage gaps
- allow operator-driven proceed/answer/cancel
- permit only one re-scope after answers

Risk addressed:

- implementing against underspecified intent

### Provider disagreement or poor generation quality
Behavior:

- use consensus/arbitration path
- continue through correction/validation pipeline
- fail with surfaced context if no acceptable artifact emerges

### Validation or test failures
Behavior:

- route via failure strategy based on failure type
- escalate by attempt count
- stop local retries after 20 attempts

Risk addressed:

- infinite repair loops
- low-signal repeated retries

### CI failure
Behavior:

- capture and truncate logs to 8k chars
- treat CI output as untrusted input
- feed failure context into bounded correction flow or surface for operator review

### GitHub rate limiting or polling pressure
Behavior:

- `403` primary path: exponential backoff through 64 seconds
- `429` secondary path: respect `Retry-After`
- use ETag caching on polling endpoints

### Unsafe filesystem write target
Behavior:

- reject write before execution if `path_security.validate_write_path()` fails
- do not attempt partial fallback writes

### Crash or process interruption
Behavior:

- resume from per-PR stage checkpoints
- do not re-run already completed stages for that PR

### Persistent learning artifact misuse
Behavior:

- do not delete `build_memory.json` on clean runs
- do not delete `build_rules.md` on clean runs unless switching to a completely new codebase

## Dependencies

### Internal components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` and generation prompt definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- build ledger/checkpoint persistence in `src/build_ledger.py`
- failure routing in `failure_handler.py`
- path validation via `path_security.validate_write_path()`
- DocumentStore for contextual document retrieval and auto-loading of `Mac-Docs/build_rules.md`

### External services and protocols

- XPC transport using line-delimited JSON with nonce authentication
- LLM providers:
  - Anthropic
  - OpenAI
- GitHub APIs, but only through `GitHubTool`
- CI systems and CI log streams
- macOS UI consumer of `build_card` and `gate_card`

### Persistent data

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- per-PR stage checkpoints / ledger state

### Dependency constraints

- external documents are treated as untrusted inputs
- secrets from credentials are never logged or reflected
- generated artifacts are inputs to validation and VCS operations, not executable instructions for the agent runtime