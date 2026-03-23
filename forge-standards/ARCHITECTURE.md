# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS AI coding agent. It owns the complete build lifecycle from intake of a plain-language build intent through scoped planning, pull-request decomposition, code generation, validation, CI execution, operator gating, and merge progression.

At a high level, this subsystem:

- Accepts a user build intent and repository context.
- Decomposes work into an ordered sequence of PRs.
- Performs scope-confidence evaluation before implementation begins.
- Collects repository, document-store, and persistent learning context for generation.
- Runs multi-provider code generation and arbitration.
- Executes post-generation correction and iterative repair loops.
- Runs linting and CI validation.
- Presents progress and gate state to the UI over XPC.
- Persists per-PR stage checkpoints so interrupted builds resume without redoing completed work.
- Persists build memory and build rules across runs as a learning system.
- Requires explicit operator approval at defined gates; it never auto-approves.

This subsystem is the orchestration layer, not a code execution sandbox. It coordinates generation and validation, but generated code is never executed by the agent via `eval`, `exec`, or subprocess execution of generated content.

## Component Boundaries

FullPlatform is defined by orchestration responsibilities and enforced interfaces to planning, generation, persistence, UI messaging, document retrieval, and GitHub operations.

### Inside this subsystem

Primary owned responsibilities include:

- Build pipeline orchestration.
- PR sequencing and per-stage progression.
- Scope-confidence gating.
- Consensus-driven generation workflow coordination.
- Build progress streaming and operator gate presentation.
- Failure handling strategy selection and bounded repair loops.
- Persistent checkpointing for crash recovery.
- Persistent build memory and build rules updates.
- Context assembly from repository state and external documents.
- Safe invocation of GitHub operations through the platform wrapper.

Known implementation anchors from the repository:

- `src/build_director.py`
  - Owns `BuildPipeline` orchestration.
  - Implements confidence gating.
  - Routes by `pr_type`.
- `src/consensus.py`
  - Owns `ConsensusEngine`.
  - Defines generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`.
- `src/build_ledger.py`
  - Owns per-PR stage checkpoint persistence and resume behavior.
- `failure_handler.py`
  - Owns strategy selection via `_choose_strategy(failure_type, attempt, records)`.
- DocumentStore integration
  - Supplies external and repository-adjacent context to generation.
- Build memory / build rules persistence
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

### Outside this subsystem

The following are dependencies or adjacent systems, not responsibilities owned by FullPlatform:

- **LLM providers**: external model execution backends. FullPlatform coordinates them but does not implement the providers.
- **GitHub API transport**: must be accessed only through `GitHubTool`; direct API calls are out of bounds.
- **XPC transport runtime**: message delivery layer is external, though FullPlatform must conform to protocol and message-handling invariants.
- **UI rendering**: `BuildStreamView` and gate presentation consume cards, but rendering is not owned here.
- **Path security primitive**: `path_security.validate_write_path()` is a required precondition for writes, but its implementation is external.
- **CI execution environment**: external execution surface; FullPlatform consumes results and logs.
- **Embedding/indexing implementation for documents**: FullPlatform uses document status and retrieval, but does not own embedding internals.

### Explicit non-goals

FullPlatform does **not**:

- Execute generated code dynamically.
- Bypass operator gates.
- Write files without prior path validation.
- Place external document context into the SYSTEM prompt.
- Clear build memory or build rules automatically.
- Raise exceptions for unknown XPC message types; those must be discarded and logged.
- Call GitHub APIs directly outside `GitHubTool`.

## Data Flow

The subsystem follows a staged, checkpointed pipeline.

### 1. Session initialization and transport handshake

On startup, the platform participates in the XPC handshake using line-delimited JSON messages, nonce-authenticated, with a maximum size of 16 MB per message.

Relevant protocol messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`

Unknown XPC message types are discarded and logged. They are never surfaced as exceptions.

### 2. Intake and context acquisition

Input sources include:

- User build intent.
- Repository state.
- External documents from the document store.
- PR comments, CI output, and other external text streams.

All such external input is treated as untrusted and validated before use.

DocumentStore is used primarily for generation context assembly. External document context must be placed in the **USER** prompt only, never in the SYSTEM prompt. A specific document such as `PRODUCT_CONTEXT.md` may be loaded when needed. Document ingestion/index status may be surfaced via:

- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### 3. Scope stage

Before implementation, FullPlatform performs a scope-confidence evaluation.

- `SCOPE_SYSTEM` returns:
  - `confidence` in the range `0–100`
  - `coverage_gaps`
- `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`

Behavior:

- If confidence is at or above threshold, the pipeline proceeds.
- If below threshold, the system presents the gaps and offers:
  - proceed
  - answer
  - cancel
- If the operator provides answers, one re-scope pass is allowed.
- There is no unbounded clarification loop.

This stage is a hard control on planning quality before code generation.

### 4. PR decomposition and ordered execution

The build intent is decomposed into an ordered sequence of PRs. Execution is staged per PR, with checkpoints preventing completed work from being rerun after interruption or crash.

Per-PR stage checkpoints are persisted in the build ledger. Resume behavior must skip already completed stages rather than replaying them.

### 5. Generation and consensus

For each PR, FullPlatform assembles context from:

- repository content
- scoped build intent
- relevant documents
- persistent build memory
- persistent build rules

Generation is run through multiple LLM providers in parallel, with Claude acting as arbiter through the consensus engine. FullPlatform coordinates this process but does not directly implement provider backends.

Context window management is bounded:

- `ContextManager` auto-trims at 30k tokens
- Preserves:
  - the spec-anchor first turn
  - the last 6 messages

### 6. Post-generation validation and repair

After initial generation, the subsystem runs:

- a self-correction pass
- a lint gate
- a bounded fix loop of up to 20 passes

Failure handling behavior is selected by failure type first, attempt count second:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt

The loop is strictly bounded:

- never retry indefinitely
- maximum 20 local attempts, then move on

### 7. CI and GitHub operations

GitHub interactions must flow exclusively through `GitHubTool` / `WebhookReceiver`. FullPlatform must never use the GitHub API directly.

Operational controls include:

- 403 on primary requests:
  - exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- 429 on secondary requests:
  - respect `Retry-After`
- ETag caching on all polling endpoints

CI output is treated as untrusted input. Log presentation is bounded:

- truncate CI output at 8k chars
- preserve approximately 70% head / 30% tail

### 8. Operator gating and streaming

Progress is streamed to the UI using build cards:

- `build_card`
  - `{ card_type, stage, content, progress }`

Blocking decisions are surfaced using gate cards:

- `gate_card`
  - `{ gate_type, options[], description }`

Gates block indefinitely until the operator responds. There is no auto-approve path.

### 9. Persistence and learning

After every successful PR:

- build memory is updated via `build_memory.record_pr()`
- file location:
  - `workspace/{engineer_id}/build_memory.json`

After build runs with 3 or more recurring failure patterns:

- build rules are updated
- file location:
  - `Mac-Docs/build_rules.md`

Both are persistent learning systems and must not be cleared automatically, including on clean runs, except manual codebase-switch scenarios for build rules.

## Key Invariants

The subsystem enforces the following architectural invariants:

- **Fail closed on auth, crypto, and identity errors.**
  - No degraded or fallback behavior is allowed for these classes.
- **No silent failure paths.**
  - Every error must surface with context.
- **Secrets never appear in logs, error messages, or generated code.**
- **All external input is untrusted and validated.**
  - Includes documents, PR comments, and CI output.
- **Generated code is never executed by the agent.**
  - No `eval`, `exec`, or subprocess execution of generated content.
- **Operator gates wait indefinitely.**
  - Never auto-approve.
- **All file writes are path-validated before execution.**
  - Must call `path_security.validate_write_path()`.
- **External document context goes only in the USER prompt.**
  - Never in the SYSTEM prompt.
- **`SECURITY_REFUSAL` is terminal for the attempted action.**
  - It is never bypassed by rephrasing; stop, gate, and log.
- **Unknown XPC message types are discarded and logged.**
  - Never raised as exceptions.
- **Per-PR stage checkpoints prevent replay after crash.**
- **Build memory and build rules persist across runs.**
  - They are not automatically cleared.

Additional subsystem-specific operational invariants:

- **Scope must be confidence-gated at 85.**
- **Rescoping is one-shot when gaps are answered.**
- **Failure strategy selection is deterministic from failure type and attempt count.**
- **Retry/fix loops are bounded to 20 local attempts.**
- **All GitHub operations go through `GitHubTool`.**
- **Polling uses ETag caching.**
- **Rate limiting and permission failures are handled explicitly, not implicitly.**
- **Context trimming preserves anchor context and recent conversational state.**

## Failure Modes

### Scope uncertainty

**Condition**
- Scope confidence below threshold.

**Behavior**
- Present `coverage_gaps`.
- Gate on operator decision: proceed, answer, or cancel.
- If answers are provided, allow one re-scope pass.
- Do not enter an unbounded clarification loop.

### Auth / crypto / identity failures

**Condition**
- Credential invalidity, nonce/authentication failure, identity mismatch, or related trust break.

**Behavior**
- Fail closed.
- Stop affected operations.
- Surface explicit error context without leaking secrets.

### Secret exposure risk

**Condition**
- Sensitive values present in logs, errors, prompts, or generated artifacts.

**Behavior**
- Treat as invariant violation.
- Redact or block propagation.
- Do not emit secrets in diagnostic output.

### Invalid or unsafe write target

**Condition**
- Any attempted file write without successful `path_security.validate_write_path()` validation.

**Behavior**
- Block the write.
- Surface the failure.
- Do not fall back to unchecked writes.

### Unsafe external context handling

**Condition**
- Untrusted external content proposed for privileged prompt placement or unvalidated downstream use.

**Behavior**
- Keep document context in USER prompt only.
- Validate prior to use.
- Refuse unsafe prompt-boundary escalation.

### Unknown XPC message types

**Condition**
- Receipt of unrecognized message type over XPC.

**Behavior**
- Discard and log.
- Never raise as exception.
- Continue processing subsequent valid messages where possible.

### Oversized or malformed XPC payloads

**Condition**
- Message exceeds protocol constraints or is malformed line-delimited JSON.

**Behavior**
- Reject the message according to protocol handling.
- Surface context.
- Do not process partially trusted content.

### Generation failure or low-quality output

**Condition**
- Provider failure, arbitration failure, invalid patch, or output that does not satisfy constraints.

**Behavior**
- Route through failure handler strategy selection.
- Apply self-correction, lint gate, and bounded repair loop.
- Do not retry indefinitely.

### Test / import / runtime / assertion failures

**Condition**
- Local validation failures after generation.

**Behavior**
- Use `_choose_strategy(failure_type, attempt, records)`:
  - `assertion_error` → `test_driven`
  - `import_error` / `runtime_error` → `converse`, then `test_driven`
  - `attempt >= 8` → `nuclear` every 3rd attempt
- Stop after 20 local attempts.

### GitHub rate limiting or permissions errors

**Condition**
- GitHub API wrapper reports:
  - `403` on primary path
  - `429` on secondary path

**Behavior**
- `403`: exponential backoff up to 64 seconds
- `429`: obey `Retry-After`
- Use ETag caching on polling endpoints
- Never bypass `GitHubTool`

### Crash or restart during a build

**Condition**
- Process interruption after some PR stages completed.

**Behavior**
- Resume from persisted ledger checkpoints.
- Do not rerun completed per-PR stages.

### CI log overload

**Condition**
- Excessive CI output volume.

**Behavior**
- Truncate to 8k characters.
- Preserve 70% head / 30% tail.
- Prevent context-window exhaustion while still surfacing meaningful diagnostics.

## Dependencies

### Internal platform dependencies

- `src/build_director.py`
  - `BuildPipeline`
  - scope confidence gate
  - PR type routing
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompt definitions
- `src/build_ledger.py`
  - stage checkpoint persistence and resume
- `failure_handler.py`
  - strategy selection for repair attempts
- `ContextManager`
  - prompt assembly and token-budget trimming
- `DocumentStore`
  - document retrieval and status visibility
- build memory subsystem
  - `workspace/{engineer_id}/build_memory.json`
- build rules subsystem
  - `Mac-Docs/build_rules.md`
- `path_security.validate_write_path()`
  - mandatory write precondition

### External service dependencies

- LLM providers
  - Anthropic
  - OpenAI
- GitHub, accessed only via:
  - `GitHubTool`
  - `WebhookReceiver`
- CI system
- XPC transport using:
  - line-delimited JSON
  - nonce authentication
  - max 16 MB/message

### Data and protocol dependencies

- XPC message schemas:
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`
- Credential inputs:
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`

### Dependency constraints

- FullPlatform must not bypass `GitHubTool`.
- FullPlatform must not treat external documents as trusted system instructions.
- FullPlatform must not weaken auth or transport checks for availability.
- FullPlatform must preserve persistent learning artifacts across runs.
- FullPlatform must depend on explicit operator input at human gates rather than inferred approval.