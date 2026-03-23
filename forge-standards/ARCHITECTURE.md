# Architecture - CraftedDevAgent

## What This Subsystem Does

CraftedDevAgent is the Forge subsystem that turns a plain-language build intent into a staged, operator-gated sequence of pull requests for a macOS-native AI coding workflow.

At a high level, this subsystem:

1. Accepts a build intent and repository context.
2. Performs scope analysis and confidence gating before implementation begins.
3. Decomposes work into an ordered PR plan.
4. Retrieves supporting context from the document store and persistent build learning artifacts.
5. Generates code and tests using multiple LLM providers in parallel.
6. Arbitrates candidate outputs through the consensus engine.
7. Applies self-correction, linting, and bounded fix-loop remediation.
8. Executes CI and interprets failures.
9. Surfaces progress and gate decisions to the operator.
10. Waits indefinitely for explicit operator approval before merge actions.
11. Records persistent learning into build memory and build rules after successful runs.

The subsystem is orchestration-heavy. It does not directly execute generated code as an instruction source; generated artifacts are treated as untrusted output and handled only through controlled repository write and CI pathways.

Primary implementation anchors:

- `src/build_director.py`
  - Build pipeline orchestration
  - Scope confidence gate
  - PR-type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - Generation system prompts and arbitration flow
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
  - Per-PR stage checkpointing and resumability

## Component Boundaries

### Inside this subsystem

The CraftedDevAgent subsystem owns:

- Build intent intake and orchestration
- Scope confidence assessment and operator gating
- PR decomposition and per-PR execution sequencing
- LLM generation fan-out and arbitration
- Context assembly for generation
- Self-correction, lint gating, and bounded local fix loops
- CI invocation/inspection flow
- Operator-facing progress and gate card emission
- Stage checkpoint persistence for crash recovery
- Persistent build learning writes:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

### Outside this subsystem

The subsystem does **not** own:

- Direct GitHub API usage outside `GitHubTool`
- Arbitrary filesystem writes outside validated write paths
- Execution of generated code via `eval`, `exec`, or subprocess interpretation of generated content
- Identity, authentication, or credential issuance policy
- UI rendering details beyond emitting protocol messages
- Document embedding/storage internals beyond consuming document store interfaces
- Automatic approval or merge decisions without operator input

### Explicit interfaces

#### XPC / transport-facing protocol

The subsystem communicates over XPC using:

- Line-delimited JSON
- Nonce-authenticated messages
- Maximum `16MB` per message

Relevant message shapes:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
- `gate_card`
  - `{ gate_type, options[], description }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

#### GitHub boundary

All GitHub operations must pass through `GitHubTool`. The subsystem must never call the GitHub API directly.

#### Filesystem boundary

All file writes must be validated through:

- `path_security.validate_write_path()`

before execution.

#### Prompt boundary

Context loaded from external documents is inserted into the **USER** prompt only, never into the **SYSTEM** prompt.

## Data Flow

### 1. Session initialization

1. Transport establishes XPC connectivity.
2. Subsystem emits `ready` with capability and document-store status metadata.
3. Credentials are received:
   - Anthropic API key
   - OpenAI API key
   - GitHub token
   - Engineer ID
4. Identity/auth failures fail closed; the pipeline does not continue in degraded mode.

### 2. Scope analysis and confidence gate

1. Build intent is analyzed by the scope system.
2. Scope stage returns:
   - `confidence` in `[0, 100]`
   - `coverage_gaps`
3. `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.

If confidence is below threshold:

- The subsystem presents gaps to the operator.
- Offers:
  - proceed
  - answer
  - cancel
- If the operator answers gaps, a one-shot re-scope occurs.
- There is no indefinite re-scope loop.

This gate determines whether implementation proceeds with acknowledged uncertainty or improved clarified scope.

### 3. Context assembly

For each PR or generation phase, the subsystem assembles context from:

- Repository state
- Build intent and clarified scope
- Document store content
- Specific documents such as `PRODUCT_CONTEXT.md`
- Persistent learning artifacts:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

Document store usage is primarily generation context retrieval. External documents are treated as untrusted input and validated before use. ContextManager trims context automatically at `30k` tokens while preserving:

- Spec-anchor first turn
- Last 6 messages

### 4. PR planning and staged execution

1. Build intent is decomposed into an ordered PR sequence.
2. Each PR progresses through staged checkpoints.
3. Per-PR stage checkpoints are persisted so a crash or restart does not rerun already completed work.

This resumability is a hard invariant and is part of `build_ledger.py` responsibility.

### 5. Multi-model generation and consensus

1. Candidate implementations and tests are generated using two LLM providers in parallel.
2. `ConsensusEngine` arbitrates outputs.
3. Generation uses system prompts defined in `src/consensus.py`, including language- and UI-specific addenda.
4. Context from external docs is confined to USER-level prompt material.

If a model emits a security refusal (`SECURITY_REFUSAL`), that result is terminal for that path:

- Stop
- Gate
- Log

It is never bypassed by rephrasing.

### 6. Repository mutation

1. Candidate file writes are prepared.
2. Every write path is validated using `path_security.validate_write_path()`.
3. Only validated writes are applied.

Secrets must never appear in:

- Logs
- Error messages
- Generated code

### 7. Validation and repair loop

After initial generation, the subsystem performs:

- Self-correction pass
- Lint gate
- Local fix loop up to 20 attempts maximum

Failure handling strategy is selected in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Policy:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- Never retry indefinitely
- Max 20 local attempts, then move on

This loop is bounded by design and escalates based on failure type first, attempt count second.

### 8. CI execution and result processing

1. CI is run for the PR.
2. CI output is treated as untrusted external input.
3. Logs are truncated to `8k` chars using a `70%` head / `30%` tail split.
4. Polling endpoints use ETag caching.
5. Rate limiting behavior:
   - `403` primary limit → exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
   - `429` secondary limit → respect `Retry-After`

### 9. Operator gate and merge progression

The subsystem emits:

- `build_card` for streaming progress
- `gate_card` for blocking decisions

Any gate requiring approval waits indefinitely for operator input. There is no auto-approve path.

### 10. Persistent learning updates

After every successful PR:

- `build_memory.record_pr()` updates `workspace/{engineer_id}/build_memory.json`

After each build run, if 3 or more recurring failure patterns are found:

- `Mac-Docs/build_rules.md` is updated

These artifacts are intentionally persistent and are not cleared on clean runs.

## Key Invariants

The subsystem must preserve all Forge-level invariants plus the following subsystem-specific enforcement rules.

### Security and trust

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted, including:
  - Documents
  - PR comments
  - CI output
- Generated code is never executed by the agent as instructions.
- `SECURITY_REFUSAL` is terminal for the affected flow and is never bypassed by prompt rephrasing.
- Unknown XPC message types are discarded and logged.

### Human control

- Gates wait indefinitely for operator input.
- No automatic approval or merge occurs.
- Below-threshold scope confidence always surfaces gaps and requires explicit operator choice.

### Filesystem and repository safety

- All writes are path-validated via `path_security.validate_write_path()` before execution.
- All GitHub operations go through `GitHubTool`; no direct GitHub API access is allowed.

### Prompting and context isolation

- External document context is placed in the USER prompt only.
- SYSTEM prompt content is not contaminated with untrusted document text.

### Execution boundedness and resumability

- Per-PR stage checkpoints prevent rerunning completed work after a crash.
- Local repair attempts are capped at 20.
- Scope clarification allows at most one re-scope pass after operator answers.

### Persistent learning

- `build_memory.json` persists across fresh installs and thread state wipes.
- `build_rules.md` persists across clean runs unless intentionally switching to a completely new codebase.
- Build memory and build rules are never cleared automatically.

## Failure Modes

### Auth / identity / credential failures

Examples:

- Missing or invalid API keys
- Invalid GitHub token
- Engineer identity resolution failure
- Nonce/authentication failure on XPC messages

Behavior:

- Fail closed immediately
- Do not continue in degraded mode
- Surface explicit, contextual error without exposing secrets

### Scope uncertainty

Trigger:

- Scope confidence below `85`

Behavior:

- Emit gate with coverage gaps
- Offer proceed / answer / cancel
- Allow one-shot re-scope if answers are provided
- Do not loop indefinitely

### LLM refusal or safety stop

Trigger:

- `SECURITY_REFUSAL`

Behavior:

- Stop affected path
- Gate and log
- Never bypass through rephrasing or alternate wording

### Invalid or unsafe filesystem target

Trigger:

- `path_security.validate_write_path()` rejection

Behavior:

- Abort write
- Surface explicit error
- Do not fall back to unvalidated writes

### GitHub/API rate limits and polling pressure

Trigger:

- GitHub `403` primary rate limit
- GitHub `429` secondary rate limit

Behavior:

- `403`: exponential backoff up to 64s
- `429`: honor `Retry-After`
- Use ETag caching on polling endpoints

### Validation and test failures

Trigger:

- Assertion, import, runtime, lint, or CI failures

Behavior:

- Route through failure strategy selection
- Escalate according to failure type and attempt count
- Cap local attempts at 20
- Move on or surface failure after exhaustion; never retry forever

### Oversized or noisy context/logs

Trigger:

- Context growth beyond model budget
- Excessive CI log volume

Behavior:

- Auto-trim context at 30k tokens, preserving anchor and recent turns
- Truncate CI logs to 8k chars with head/tail retention

### Crash / restart during build

Trigger:

- Process interruption mid-PR

Behavior:

- Resume from persisted per-PR stage checkpoints
- Do not rerun completed stages

### Unknown XPC input

Trigger:

- Unrecognized message type

Behavior:

- Discard and log
- Never raise as transport-fatal exception solely due to unknown type

## Dependencies

### Internal code dependencies

- `src/build_director.py`
  - Primary orchestration entrypoint
  - Scope gate enforcement
  - PR routing and stage progression
- `src/consensus.py`
  - Multi-provider generation orchestration
  - Arbitration logic
  - System prompt definitions
- `src/github_tools.py`
  - GitHub repository operations
  - Webhook/event handling
- `src/build_ledger.py`
  - Stage checkpoint persistence and crash recovery
- `failure_handler.py`
  - Failure strategy selection logic
- `path_security.validate_write_path()`
  - Mandatory write-path validation
- `ContextManager`
  - Context trimming and retention policy

### External service dependencies

- Anthropic API
- OpenAI API
- GitHub APIs, but only via `GitHubTool`
- Document store / embedding pipeline for repository and product context retrieval

### Persistent data dependencies

- `workspace/{engineer_id}/build_memory.json`
  - Cross-run PR learning store
- `Mac-Docs/build_rules.md`
  - Persistent, self-improving coding rules
- Stage checkpoint storage managed by build ledger
- Repository working tree and PR state

### Protocol dependencies

- XPC line-delimited JSON transport
- Nonce-authenticated message framing
- Message schemas for:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

This subsystem assumes these dependencies are available and valid; when they are not, it stops safely rather than degrading silently.