# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS AI coding agent. It owns the lifecycle that turns a plain-language build intent into an operator-gated sequence of pull requests, with generation, validation, repair, CI execution, and merge control.

At a high level, this subsystem:

- Accepts build intent and repository context
- Decomposes work into an ordered PR plan
- Performs scope-confidence analysis before implementation begins
- Loads persistent repository knowledge from document storage, build memory, and build rules
- Generates implementation and tests using multiple LLM providers in parallel
- Arbitrates generation outputs through consensus
- Runs self-correction, linting, and bounded repair loops
- Executes CI and summarizes results
- Emits progress and gate messages to the UI over XPC
- Waits indefinitely for operator decisions at required approval points
- Persists per-PR checkpoints so crashed runs resume without redoing completed stages
- Records successful outcomes into persistent learning artifacts

This subsystem is the orchestration layer, not a generic code execution environment. It coordinates controlled generation and validation while enforcing Forge’s security, path, identity, and human-gating rules.

## Component Boundaries

FullPlatform includes the orchestration and coordination responsibilities centered around the build pipeline.

Included responsibilities:

- Build pipeline orchestration in `src/build_director.py`
  - Stage ordering
  - PR-type routing
  - Scope-confidence gating
  - Operator gate presentation and handling
  - Checkpoint-aware stage progression
- Consensus-based generation in `src/consensus.py`
  - Parallel provider generation
  - Arbitration logic
  - Use of generation system prompts, including Swift/UI variants
- Persistent build progress tracking in `src/build_ledger.py`
  - Per-PR stage checkpoints
  - Crash-safe resume behavior
- GitHub operation mediation through `src/github_tools.py`
  - All repository and PR operations
  - Webhook/event integration where applicable
- Document and repository-context consumption
  - DocumentStore-backed retrieval for generation context
  - Loading persistent build rules
  - Access to build memory for cross-run learning
- UI protocol emission
  - `build_card` streaming updates
  - `gate_card` blocking gates
  - `doc_status` updates where document ingestion state matters

Explicitly out of scope:

- Direct execution of generated code as an agent-controlled action
- Arbitrary shell execution of generated content
- Direct GitHub API usage outside `GitHubTool`
- Rewriting XPC transport semantics
- Long-term document embedding implementation details
- LLM provider internals
- Automatic approval, auto-merge without gates, or silent continuation past a blocked decision

Boundary rules:

- FullPlatform may request generation, validation, testing, CI, and GitHub actions, but must route through approved subsystem interfaces.
- FullPlatform may write files only after path validation via `path_security.validate_write_path()`.
- FullPlatform may consume external documents only as untrusted input and must place such context in the USER prompt, never the SYSTEM prompt.
- FullPlatform must stop on security refusal conditions rather than attempting prompt reformulations to bypass them.

## Data Flow

1. **Session initialization**
   - The subsystem establishes platform readiness over XPC using line-delimited JSON messages.
   - It consumes `ready` metadata:
     - `agent_version`
     - `min_swift_version`
     - `capabilities[]`
     - `doc_store_status`

2. **Credential intake**
   - Credentials arrive via the `credentials` message:
     - `anthropic_api_key`
     - `openai_api_key`
     - `github_token`
     - `engineer_id`
   - Auth, crypto, or identity failures fail closed.

3. **Intent and repository context ingestion**
   - User build intent and repository context are collected.
   - External documents, PR comments, and CI output are treated as untrusted input.
   - Relevant context is loaded from DocumentStore and injected only into USER prompts.

4. **Persistent context loading**
   - Build memory is loaded from:
     - `workspace/{engineer_id}/build_memory.json`
   - Build rules are loaded from:
     - `Mac-Docs/build_rules.md`
   - These stores are persistent and are not automatically cleared.

5. **Scope analysis and confidence gate**
   - The scope stage evaluates implementation readiness using the scope system.
   - The scope system returns:
     - `confidence` in the range 0–100
     - `coverage_gaps`
   - `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.
   - If confidence is below threshold, the subsystem presents the operator with:
     - proceed
     - answer
     - cancel
   - If the operator answers coverage gaps, one re-scope pass occurs. There is no unbounded re-scope loop.

6. **PR planning and staged execution**
   - Work is decomposed into an ordered PR sequence.
   - Each PR is processed through staged checkpoints so completed stages are not repeated after interruption.

7. **Generation and arbitration**
   - The subsystem invokes multiple LLM providers in parallel through the consensus engine.
   - `src/consensus.py` applies the appropriate generation system prompt set.
   - Arbitration selects the output to carry forward.

8. **Validation and repair loop**
   - Generated changes move through:
     - self-correction
     - lint gate
     - bounded fix loop
   - Failure handling uses failure-type-driven strategy selection in `failure_handler.py`:
     - `assertion_error` → `test_driven` immediately
     - `import_error` / `runtime_error` → `converse` first, then `test_driven`
     - `attempt >= 8` → `nuclear` every 3rd attempt
   - Local retry count is capped at 20 attempts.

9. **CI execution and result handling**
   - CI is run for candidate changes.
   - CI output is treated as untrusted input.
   - Logs are truncated to 8k characters with a 70% head / 30% tail split.
   - Polling uses ETag caching.
   - Rate limits are handled as follows:
     - 403 primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
     - 429 secondary: respect `Retry-After`

10. **Operator gate and merge control**
    - Required decisions are emitted as `gate_card` messages:
      - `gate_type`
      - `options[]`
      - `description`
    - Gates block indefinitely until the operator responds.
    - There is no auto-approve behavior.

11. **Progress streaming**
    - Status is streamed via `build_card`:
      - `card_type`
      - `stage`
      - `content`
      - `progress`
    - Document ingestion state may be surfaced via `doc_status`:
      - `doc_id`
      - `doc_name`
      - `status`
      - `chunk_count`
      - `embedded_count`

12. **Persistence after success**
    - After every successful PR, build memory is updated via `build_memory.record_pr()`.
    - After each build run, if 3 or more recurring failure patterns are found, build rules may be updated.
    - These artifacts persist across runs and fresh installs by design.

## Key Invariants

The subsystem must preserve all Forge platform invariants, plus the following subsystem-specific operational rules.

Security and trust invariants:

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, prompts intended for generated code, or generated code itself.
- All external input is untrusted and validated.
- Generated code is never executed by the agent via `eval`, `exec`, or subprocess invocation of generated content.
- `SECURITY_REFUSAL` is terminal for the attempted action: stop, gate, and log. Rephrasing must not be used to bypass refusal.
- XPC unknown message types must be discarded and logged, never raised as exceptions.

Human-control invariants:

- Gates wait indefinitely for operator input.
- No auto-approve path exists.
- Merge progression requires explicit operator approval where gating is defined.

Filesystem invariants:

- Every file write must pass `path_security.validate_write_path()` before execution.
- Clean runs must not delete persistent learning artifacts by default.

Prompting and context invariants:

- External-document context must go into USER prompts only, never SYSTEM prompts.
- Consensus generation must use approved system prompt definitions from `src/consensus.py`.
- ContextManager auto-trims at 30k tokens while preserving:
  - the spec-anchor first turn
  - the last 6 messages

Progress and recovery invariants:

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent learning systems and are never cleared automatically.
- Scope re-analysis below threshold is limited to one operator-informed retry, not an open-ended loop.

Integration invariants:

- All GitHub operations must go through `GitHubTool`.
- Polling endpoints must use ETag caching where supported.
- Protocol messages are line-delimited JSON with nonce authentication and a 16 MB maximum message size.

## Failure Modes

### Scope confidence below threshold
Condition:
- Scope stage returns `confidence < 85`

Behavior:
- Show `coverage_gaps`
- Gate operator with proceed/answer/cancel
- If operator answers, perform one re-scope pass only
- If still unresolved, remain gated or terminate per operator choice

### Auth, crypto, or identity failure
Condition:
- Invalid credentials, nonce/authentication errors, or identity mismatch

Behavior:
- Fail closed immediately
- Do not continue in degraded mode
- Surface the error with context, without exposing secrets

### Invalid or unsafe filesystem write
Condition:
- Target path fails `path_security.validate_write_path()`

Behavior:
- Reject the write
- Surface explicit error context
- Do not attempt alternate unchecked paths

### Security refusal from model or policy layer
Condition:
- `SECURITY_REFUSAL` emitted during generation or action planning

Behavior:
- Stop the attempted operation
- Gate/log according to policy
- Do not retry by paraphrasing or prompt mutation intended to evade the refusal

### Unknown XPC message type
Condition:
- Incoming XPC message type is not recognized

Behavior:
- Discard and log
- Never raise as a transport-fatal exception solely due to unknown type

### Generation or validation failure
Condition:
- Generated code fails lint, tests, import/runtime checks, or assertions

Behavior:
- Route using failure-type-driven strategy:
  - `assertion_error` → immediate `test_driven`
  - `import_error` / `runtime_error` → `converse`, then `test_driven`
  - attempt `>= 8` → `nuclear` every 3rd attempt
- Cap local repair attempts at 20
- If unresolved after cap, stop local retries and move on to the next higher-level decision path

### Rate limiting or polling degradation
Condition:
- GitHub or related endpoints respond with 403/429 or require polling

Behavior:
- 403 primary: apply exponential backoff up to 64s
- 429 secondary: honor `Retry-After`
- Use ETag caching on polling endpoints
- Do not spin aggressively or retry indefinitely

### Oversized or noisy context
Condition:
- Prompt/context volume exceeds model budget or CI logs are too large

Behavior:
- ContextManager trims at 30k tokens while preserving anchor and recent turns
- CI logs truncate to 8k chars using 70/30 head-tail split
- Automatic behavior; no silent omission beyond defined truncation rules

### Crash or process interruption
Condition:
- Build process exits mid-PR or mid-stage

Behavior:
- Resume from persisted per-PR stage checkpoint
- Do not re-run already completed stages
- Preserve build memory and build rules

## Dependencies

Core code dependencies:

- `src/build_director.py`
  - Primary build pipeline orchestration
  - Scope gate and PR routing
- `src/consensus.py`
  - ConsensusEngine
  - Generation system prompt definitions
- `src/build_ledger.py`
  - Per-PR checkpoint persistence
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

Platform/service dependencies:

- XPC transport
  - Line-delimited JSON
  - Nonce-authenticated
  - 16 MB max message size
- BuildStreamView consumer for `build_card`
- Operator-interaction surface for `gate_card`
- DocumentStore
  - Repository and product context retrieval
  - Automatic loading of `Mac-Docs/build_rules.md`
- Persistent workspace storage
  - `workspace/{engineer_id}/build_memory.json`
- GitHub
  - Accessed only through `GitHubTool`
- LLM providers
  - Parallel generation providers
  - Claude used for arbitration per platform overview
- CI system
  - Source of execution feedback
  - Produces untrusted logs and status

Behavioral dependencies and contracts:

- `path_security.validate_write_path()` must be invoked before any file write
- `build_memory.record_pr()` must be called after every successful PR
- Failure handling must use `failure_handler.py:_choose_strategy(failure_type, attempt, records)`
- Context trimming and log truncation are automatic and must be preserved as subsystem behavior

Persistent artifact dependencies:

- `workspace/{engineer_id}/build_memory.json`
  - Cross-run learning store
  - Must survive fresh installs and thread state wipes
- `Mac-Docs/build_rules.md`
  - Self-improving repository rule set
  - Must not be deleted on clean runs unless switching to a completely new codebase