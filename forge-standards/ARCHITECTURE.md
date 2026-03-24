# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that turns a plain-language build intent into an operator-gated sequence of pull requests and implementation work.

Within the Forge architecture, this subsystem:

- decomposes build intent into an ordered PR plan
- generates implementation and tests using two LLM providers in parallel
- uses Claude for arbitration in the consensus path
- runs a self-correction pass
- runs a lint gate
- runs a bounded local fix loop of up to 20 passes
- executes CI
- pauses on explicit operator gates before merge
- persists per-PR stage checkpoints so completed work is not re-run after a crash
- persists build memory and build rules as cross-run learning state

It also owns the main guardrails around scope confidence, generation context use, untrusted input handling, write-path validation, and failure handling behavior.

Relevant implementation anchors named in the TRDs:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM` + `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — stage checkpoint persistence for PR progress
- `failure_handler.py` — `_choose_strategy(failure_type, attempt, records)`

## Component Boundaries

ForgeAgent is bounded by the following responsibilities and exclusions.

### In scope

- Build pipeline orchestration
- Scope confidence gating before implementation proceeds
- Consensus-based code/test generation using the defined LLM flow
- Use of document context for generation
- Build memory and build rules persistence
- GitHub operations through the approved tool layer
- CI execution and bounded fix-loop remediation
- Operator gating and indefinite wait behavior
- Build status and gate streaming over the XPC protocol
- Error surfacing, logging, and crash-safe checkpointing

### Out of scope / enforced boundaries

- ForgeAgent does not auto-approve gates
- ForgeAgent does not execute generated code via `eval`, `exec`, or subprocess invocation of generated content
- ForgeAgent does not trust external input; documents, PR comments, and CI output are treated as untrusted and validated
- ForgeAgent does not write files without `path_security.validate_write_path()` validation
- ForgeAgent does not call the GitHub API directly; all GitHub operations must go through `GitHubTool`
- ForgeAgent does not place external document context into the SYSTEM prompt; such context is placed in the USER prompt only
- ForgeAgent does not silently continue past auth, crypto, identity, or refusal conditions
- ForgeAgent does not clear `build_memory.json` or `build_rules.md` automatically

## Data Flow

### 1. Session and protocol initialization

ForgeAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

The subsystem emits or consumes the following protocol structures:

- `ready`  
  `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`  
  `{ card_type, stage, content, progress }`  
  streamed to `BuildStreamView`
- `gate_card`  
  `{ gate_type, options[], description }`  
  blocks until operator responds
- `credentials`  
  `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`  
  `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Scope intake and confidence gate

A plain-language build intent enters the core loop. Before implementation proceeds, ForgeAgent runs the scope confidence gate.

TRD-defined behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If below threshold, the subsystem:

- shows the identified gaps
- offers `proceed / answer / cancel`

If the operator answers the gaps:

- ForgeAgent performs a one-shot re-scope
- there is no indefinite re-scope loop

This makes scope sufficiency an explicit, operator-visible gate rather than an implicit heuristic.

### 3. Context assembly for generation

Generation context may include repository content, document store content, persistent build memory, and build rules.

Document store usage is a primary generation context source. The TRDs explicitly define:

- context from external documents goes in the USER prompt
- never in the SYSTEM prompt

A specific document such as `PRODUCT_CONTEXT.md` may be loaded when needed.

Context handling constraints:

- `ContextManager` auto-trims at 30k tokens
- it preserves:
  - the spec-anchor first turn
  - the last 6 messages

These rules bound context growth while preserving the most important instruction anchors and recent working state.

### 4. Consensus-based generation

ForgeAgent uses two LLM providers in parallel for generation, with Claude arbitrating via the consensus path.

Implementation anchors:

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`

Generated implementation and tests then move into the downstream correction and verification stages.

### 5. File mutation and repository operations

All repository mutation is constrained by two mandatory rules:

- all file writes are validated through `path_security.validate_write_path()` before execution
- all GitHub operations go through `GitHubTool`

Direct GitHub API use is prohibited by design.

`src/github_tools.py` provides:

- `GitHubTool`
- `WebhookReceiver`

This establishes a single tool boundary for PR, webhook, and repository operations.

### 6. Verification and repair loop

After generation, ForgeAgent runs:

- self-correction
- lint gate
- CI
- local failure-repair attempts

Failure strategy selection is defined in `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`

Decision rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

Associated operational controls:

- `403 primary` → exponential backoff  
  `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints
- CI log output truncated at 8k chars using `70% head / 30% tail`
- no action required for the above behaviors; they are automatic

### 7. Operator gate and merge boundary

ForgeAgent is human-gated. `gate_card` blocks until the operator responds.

A core invariant applies here:

- gates wait indefinitely for operator input
- no auto-approve ever

### 8. Persistence and recovery

ForgeAgent persists both execution progress and cross-run learning state.

#### Per-PR execution checkpoints

Per-PR stage checkpoints prevent re-running completed work after a crash.

This persistence is associated with the build ledger subsystem anchor:

- `src/build_ledger.py`

#### Build memory

Persistent learning state:

- file: `build_memory.json`
- location: `workspace/{engineer_id}/build_memory.json`
- written after every successful PR via `build_memory.record_pr()`
- survives fresh installs and thread state wipes
- must not be deleted on clean runs

#### Build rules

Persistent coding rules derived from build history:

- file: `build_rules.md`
- location: `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- written after each build run when 3+ recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The subsystem enforces the following architecture-level invariants from the Forge context and TRDs.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error surfaces with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log

### Execution safety

- Generated code is never executed by the agent
- No `eval`
- No `exec`
- No subprocess execution of generated content

### File and repository safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution
- All GitHub operations go through `GitHubTool`
- Direct GitHub API usage is not allowed

### Prompt and context separation

- Context from external documents goes in the USER prompt
- Never in the SYSTEM prompt

### Protocol robustness

- XPC unknown message types are discarded and logged
- They are never raised as exceptions
- XPC messages are line-delimited JSON, nonce-authenticated, and capped at 16 MB

### Human control

- Gates wait indefinitely for operator input
- No auto-approve ever

### Recovery and learning persistence

- Per-PR stage checkpoints prevent repeated completed work after crashes
- Build memory is persistent and is never cleared automatically
- Build rules are persistent and are never cleared automatically under normal clean runs

### Scope gating

- `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`
- below-threshold scope proceeds only through explicit operator choice
- operator-provided gap answers trigger a single re-scope pass only

### Repair-loop bounds

- Never retry indefinitely
- Maximum 20 local attempts, then move on

## Failure Modes

### Scope uncertainty

Condition:
- `SCOPE_SYSTEM` returns confidence below `85`

Behavior:
- surface `coverage_gaps`
- present `proceed / answer / cancel`
- if answers are provided, run one re-scope pass only

Enforcement:
- uncertain scope does not silently transition into implementation

### Auth, crypto, or identity failure

Condition:
- auth, crypto, or identity errors occur

Behavior:
- fail closed
- do not degrade silently
- surface error context

Enforcement:
- secure default over partial operation

### Security refusal

Condition:
- model or guardrail returns `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log

Enforcement:
- refusal cannot be bypassed by rephrasing

### Unknown XPC message type

Condition:
- received XPC message type is not recognized

Behavior:
- discard and log

Enforcement:
- do not raise an exception for unknown message types

### Write-path violation

Condition:
- target path fails `path_security.validate_write_path()`

Behavior:
- do not execute write

Enforcement:
- all writes are validated before execution

### GitHub transport or rate-limit failures

Condition:
- GitHub operation encounters throttling or access issues

Behavior:
- `403 primary` uses exponential backoff: `2s, 4s, 8s, 16s, 32s, 64s`
- `429 secondary` respects `Retry-After`
- polling endpoints use ETag caching

Enforcement:
- retries are controlled and protocol-aware

### Build/test failure during local repair

Condition:
- assertion, import, runtime, or recurring failures occur during correction/fix loop

Behavior:
- select strategy with `_choose_strategy(failure_type, attempt, records)`
- `assertion_error` → `test_driven`
- `import_error` / `runtime_error` → `converse`, then `test_driven`
- from attempt `>= 8`, use `nuclear` every 3rd attempt
- cap total local attempts at 20

Enforcement:
- bounded repair with deterministic escalation

### Excessive context or oversized logs

Condition:
- context or CI output grows beyond safe operating bounds

Behavior:
- `ContextManager` trims at `30k` tokens while preserving the spec-anchor first turn and last 6 messages
- CI logs truncate to `8k` chars with `70%` head and `30%` tail

Enforcement:
- bounded prompt and log size without dropping core navigation context

### Crash or restart during multi-stage PR execution

Condition:
- ForgeAgent crashes or restarts mid-pipeline

Behavior:
- per-PR stage checkpoints prevent re-running completed stages

Enforcement:
- progress resumes from persisted ledger state rather than replaying the full PR stage set

## Dependencies

### Internal code modules

- `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate
  - `pr_type` routing
- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - per-PR stage checkpoint persistence
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

### Persistent stores and files

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Tooling and services

- `DocumentStore`
  - used for generation context
  - auto-loads `build_rules.md`
- two LLM providers in parallel
- Claude as arbitration path in consensus
- GitHub through `GitHubTool`
- XPC transport for host communication and UI streaming

### Protocol/UI consumers

- `BuildStreamView` for streamed `build_card` updates
- operator gate handling via blocking `gate_card` responses