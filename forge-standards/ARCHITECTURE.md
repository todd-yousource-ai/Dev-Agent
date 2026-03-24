# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that drives end-to-end build execution from a plain-language build intent through gated pull request delivery.

At a high level, the subsystem:

- decomposes a build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as arbiter within the consensus flow
- runs a self-correction pass
- runs a lint gate
- runs a 20-pass local fix loop
- executes CI
- pauses on operator approval gates before merge
- persists per-PR progress so completed work is not re-run after a crash
- persists cross-run learning via build memory and build rules

The subsystem is explicitly human-gated. Gates block indefinitely for operator input and are never auto-approved.

The subsystem also acts as the boundary enforcer for several security and execution guarantees:

- generated code is produced but never executed by the agent
- untrusted external inputs are validated before use
- all writes are path-validated before execution
- auth, crypto, and identity failures fail closed
- security refusals are terminal within the current flow and cannot be bypassed by prompt rephrasing

Relevant implementation anchors from the repository mapping:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR type routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing and build progress persistence implied by platform invariants and stage checkpoint requirements

## Component Boundaries

ForgeAgent owns orchestration, gating, context assembly, provider coordination, persistence of build learning, and controlled interaction with GitHub and the UI transport.

### Inside the subsystem

#### Build orchestration
Owned by `BuildPipeline` in `src/build_director.py`:

- intake of build intent
- PR decomposition and ordered execution
- stage progression
- scope confidence evaluation and gating
- PR type routing
- fix-loop orchestration
- CI execution orchestration
- operator gate handling

#### Consensus and generation coordination
Owned by `ConsensusEngine` in `src/consensus.py`:

- parallel use of two LLM providers
- arbitration via Claude
- application of generation system prompts
- use of Swift/UI-specific generation variants where applicable

#### Document and context usage
ForgeAgent consumes document context for generation, with external document context placed only in the USER prompt.

Document use includes:

- loading specific documents such as `PRODUCT_CONTEXT.md`
- consuming `build_rules.md` via `DocumentStore`
- reporting document embedding/availability status via `doc_status`

#### Persistent learning
ForgeAgent owns two persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - never automatically deleted on clean runs
- `Mac-Docs/build_rules.md`
  - self-improving coding rules derived from build history
  - loaded automatically by `DocumentStore`
  - written after build runs when 3 or more recurring failure patterns are found
  - not deleted on clean runs unless switching to a completely new codebase

#### GitHub interaction boundary
All GitHub operations are mediated through `GitHubTool` in `src/github_tools.py`.

This subsystem enforces the rule:

- never use the GitHub API directly
- all GitHub reads/writes, including PR-related operations, go through `GitHubTool`

#### XPC messaging and UI streaming
ForgeAgent participates in the XPC wire protocol for communicating status and gates to the macOS host UI.

It emits or handles:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### Outside the subsystem

ForgeAgent does not own:

- direct GitHub API usage outside `GitHubTool`
- operator decisions
- execution of generated code
- bypass of security refusals
- automatic approval of any gate
- arbitrary filesystem writes that have not passed `path_security.validate_write_path()`

ForgeAgent also does not treat external documents, PR comments, or CI output as trusted; these remain external, untrusted inputs crossing into the subsystem boundary.

## Data Flow

### 1. Session initialization
The subsystem establishes readiness over XPC using line-delimited JSON with nonce authentication and a maximum message size of 16MB.

The `ready` message contains:

- `agent_version`
- `min_swift_version`
- `capabilities[]`
- `doc_store_status`

Credentials arrive as:

- `anthropic_api_key`
- `openai_api_key`
- `github_token`
- `engineer_id`

Auth, crypto, or identity errors fail closed.

### 2. Build intent intake and scope gating
A plain-language build intent enters the pipeline.

`BuildPipeline` performs scope analysis using the scope confidence mechanism:

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the subsystem shows the coverage gaps
- offers operator actions:
  - proceed
  - answer
  - cancel
- if the operator provides gap answers, a one-shot re-scope occurs
- there is no indefinite re-scope loop

### 3. Context assembly
The subsystem assembles generation context from repository state and documents.

Context sources include:

- repository materials
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- persistent `build_rules.md`
- build memory from `workspace/{engineer_id}/build_memory.json`

Context handling constraints:

- all external input is untrusted and validated
- context from external documents goes into the USER prompt only
- it never enters the SYSTEM prompt
- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn plus the last 6 messages
- CI log output is truncated to 8k characters using 70% head / 30% tail

### 4. Parallel generation and consensus
For each PR, ForgeAgent invokes two LLM providers in parallel.

The consensus layer in `src/consensus.py` applies:

- generation system prompts
- Swift/UI-specific prompt variants where required
- Claude arbitration across provider outputs

Generated code and tests are produced as artifacts for review and repository application, but generated code is never executed by the agent.

### 5. Write validation and repository operations
Before any file write is executed, the target path must be validated with:

- `path_security.validate_write_path()`

GitHub-facing operations are routed exclusively through:

- `GitHubTool`

No direct GitHub API access is permitted.

### 6. Correction, lint, and fix loop
After initial generation, the subsystem executes:

- a self-correction pass
- a lint gate
- a local fix loop capped at 20 attempts

Failure handling follows the documented strategy selection rules from `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary

Defined strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- maximum 20 local attempts, then move on

### 7. CI and remote feedback
The subsystem executes CI and consumes CI output as untrusted input.

Protocol and rate-limit handling requirements include:

- `403` on primary: exponential backoff of `2s → 4s → 8s → 16s → 32s → 64s`
- `429` on secondary: respect `Retry-After`
- ETag caching on all polling endpoints

CI output presented back into model context is truncated automatically per the context rules above.

### 8. Operator gate and completion persistence
Before merge, the subsystem presents gate UI via `gate_card`:

- `gate_type`
- `options[]`
- `description`

The gate blocks until the operator responds. There is no auto-approve path.

Progress and completion state are persisted per PR stage so that after a crash the subsystem does not re-run completed work.

After successful PR completion:

- `build_memory.record_pr()` updates `build_memory.json`
- recurring failure patterns may update `build_rules.md`

Build progress/status is streamed using `build_card`:

- `card_type`
- `stage`
- `content`
- `progress`

## Key Invariants

The subsystem enforces the following invariants.

### Security and trust
- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the flow stops, gates, and logs.

### Execution safety
- Generated code is never executed by the agent.
- No `eval`, no `exec`, and no subprocess execution of generated content.

### Filesystem and repository safety
- All file writes must be path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.

### Human control
- Gates wait indefinitely for operator input.
- There is no auto-approve behavior.

### Protocol robustness
- XPC wire format is line-delimited JSON, nonce-authenticated, with a maximum of 16MB per message.
- Unknown XPC message types are discarded and logged, never raised as exceptions.

### Recovery and persistence
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### Retry and context bounds
- Local repair attempts are capped at 20.
- Scope re-questioning is one-shot only after operator gap answers.
- Context is auto-trimmed at 30k tokens while preserving the spec-anchor first turn and last 6 messages.
- CI logs are truncated to 8k characters with a 70/30 head/tail split.

## Failure Modes

### Authentication, crypto, or identity failure
Behavior:

- fail closed immediately
- do not degrade silently
- surface the error with context
- do not expose secrets

### Security refusal from model or policy layer
Behavior:

- treat `SECURITY_REFUSAL` as terminal for the current path
- do not retry by rephrasing to bypass refusal
- stop, gate, and log

### Unknown XPC message type
Behavior:

- discard the message
- log occurrence
- do not raise an exception

### Low scope confidence
Trigger:

- `confidence < 85` from `SCOPE_SYSTEM`

Behavior:

- present coverage gaps
- offer proceed/answer/cancel
- if answers are provided, perform one re-scope pass
- otherwise remain operator-driven; no auto-progression

### Local generation/test failure
Behavior is selected by `_choose_strategy(failure_type, attempt, records)`:

- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- after attempt 8, escalate to `nuclear` every third attempt
- stop after 20 attempts; do not retry indefinitely

### GitHub or polling rate-limit / access issues
Behavior:

- `403` on primary endpoints → exponential backoff through 64 seconds
- `429` on secondary endpoints → honor `Retry-After`
- apply ETag caching on polling endpoints

### Crash or interruption mid-build
Behavior:

- recover using per-PR stage checkpoints
- skip stages already completed
- preserve build memory and build rules across runs

### Oversized or noisy context
Behavior:

- trim automatically at 30k tokens
- preserve spec-anchor first turn and last 6 messages
- truncate CI logs to 8k characters with 70% head and 30% tail

## Dependencies

### Internal repository components
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
  - build/stage persistence for checkpointed recovery

### Persistent data artifacts
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Supporting subsystems and utilities
- `DocumentStore`
- `ContextManager`
- `failure_handler.py`
- `path_security.validate_write_path()`

### External integrations
- two LLM providers in parallel
- Claude as arbitration path in consensus
- GitHub, only through `GitHubTool`
- macOS host/UI over XPC using the documented message schema

### Protocol contracts
- XPC line-delimited JSON transport
- nonce-authenticated messages
- maximum 16MB per message
- structured payloads:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`