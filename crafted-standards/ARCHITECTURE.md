# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated sequence of pull requests.

Within the Forge architecture, it:

- decomposes build intent into an ordered PR plan
- performs scope assessment and confidence gating before implementation
- generates implementation and tests using two LLM providers in parallel
- uses Claude as the arbitrator in consensus generation flow
- runs self-correction, lint gating, and a bounded local fix loop
- executes CI and presents results to the operator
- pauses on explicit gate cards for operator input before merge-sensitive transitions
- persists cross-run learning via build memory and build rules
- resumes safely after crashes using per-PR stage checkpoints

The subsystem is human-in-the-loop by construction. Gates block indefinitely for operator response, and there is no auto-approve path.

## Component Boundaries

CraftedAgent includes orchestration, generation, context loading, persistence of learning artifacts, and controlled GitHub interaction through the approved tool boundary.

### In scope

- Build orchestration via `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate handling
  - `pr_type` routing
- Multi-model consensus generation via `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- GitHub operations through `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- Build learning persistence
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- DocumentStore-backed context retrieval for generation
- XPC protocol participation using the documented wire format and message types
- Stage checkpointing and crash-safe continuation per PR
- Failure handling and retry strategy application
- Context trimming and CI log truncation safeguards

### Explicit boundaries and exclusions

- CraftedAgent does not execute generated code via `eval`, `exec`, or subprocess invocation of generated content.
- CraftedAgent does not call the GitHub API directly; all GitHub operations must go through `GitHubTool`.
- CraftedAgent does not bypass operator gates.
- CraftedAgent does not trust external inputs by default; documents, PR comments, and CI output are treated as untrusted.
- CraftedAgent does not place external document context into the SYSTEM prompt; that context belongs only in the USER prompt.
- CraftedAgent does not silently clear persistent learning state.
- CraftedAgent does not raise exceptions for unknown XPC message types; they are discarded and logged.

## Data Flow

1. **Initialization and transport**
   - The subsystem communicates over XPC using line-delimited JSON.
   - Messages are nonce-authenticated.
   - Maximum message size is 16 MB.
   - A `ready` message advertises:
     - `agent_version`
     - `min_swift_version`
     - `capabilities[]`
     - `doc_store_status`

2. **Credential and identity intake**
   - Credentials arrive via:
     - `anthropic_api_key`
     - `openai_api_key`
     - `github_token`
     - `engineer_id`
   - Auth, crypto, and identity failures fail closed.

3. **Intent to scope**
   - A plain-language build intent enters the core loop.
   - The scope system returns:
     - `confidence` from 0–100
     - `coverage_gaps`
   - `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.

4. **Scope confidence gate**
   - If confidence is below threshold, the subsystem shows gaps and offers:
     - proceed
     - answer
     - cancel
   - If the operator supplies answers to gaps, one re-scope pass is performed.
   - There is no indefinite re-scope loop.

5. **Context assembly**
   - DocumentStore is used for generation context.
   - Specific documents may be loaded, including examples such as `PRODUCT_CONTEXT.md`.
   - External document context is inserted into the USER prompt only.
   - Build memory and build rules are included as persistent learning inputs when available.

6. **Generation and arbitration**
   - Two LLM providers generate implementation and tests in parallel.
   - Claude arbitrates through the consensus path.
   - Generated code is treated as inert output and is never executed as code by the agent.

7. **Write controls**
   - Before any file write, `path_security.validate_write_path()` must approve the target path.
   - This applies to all writes without exception.

8. **Local validation and repair**
   - Self-correction pass runs.
   - Lint gate runs.
   - A bounded local fix loop runs, with a maximum of 20 attempts.
   - Failure strategy selection is driven by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`.

9. **CI and operator presentation**
   - CI is executed.
   - CI log output is truncated to 8k characters using 70% head / 30% tail.
   - Progress is streamed via `build_card` messages:
     - `card_type`
     - `stage`
     - `content`
     - `progress`
   - Blocking operator decisions are emitted via `gate_card`:
     - `gate_type`
     - `options[]`
     - `description`

10. **GitHub operations**
    - All repository interactions go through `GitHubTool`.
    - No direct GitHub API usage is permitted.

11. **Persistence and resume**
    - Per-PR stage checkpoints prevent repeating completed work after crash.
    - After every successful PR, build memory is updated via `build_memory.record_pr()`.
    - `build_rules.md` is updated after a build run when 3 or more recurring failure patterns are found.

12. **Document status reporting**
    - Embedding/document ingestion status may be surfaced via `doc_status`:
      - `doc_id`
      - `doc_name`
      - `status`
      - `chunk_count`
      - `embedded_count`

## Key Invariants

The subsystem must preserve the following invariants:

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; there is no auto-approve behavior.
- All file writes are validated by `path_security.validate_write_path()` before execution.
- Context from external documents goes into the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is terminal for the attempted action: stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after crashes.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional enforced rules from subsystem behavior:

- `_stage_scope` gates below `_CONFIDENCE_THRESHOLD = 85`.
- Re-scope after operator clarification is one-shot only.
- All GitHub operations must route through `GitHubTool`.
- Never retry indefinitely; the local repair loop stops after 20 attempts.
- `ContextManager` auto-trims at 30k tokens.
- Context preservation during trimming keeps the spec-anchor first turn plus the last 6 messages.
- Polling endpoints use ETag caching.
- 403 primary rate/authorization failures use exponential backoff:
  - 2s, 4s, 8s, 16s, 32s, 64s
- 429 secondary responses honor the `Retry-After` header.

## Failure Modes

### Scope uncertainty

- **Condition:** Scope confidence below 85.
- **Behavior:** The subsystem gates and presents `coverage_gaps`.
- **Operator options:** proceed, answer, cancel.
- **Limit:** At most one re-scope pass after gap answers.

### Auth, crypto, or identity failure

- **Condition:** Invalid or unverifiable credentials/identity state.
- **Behavior:** Fail closed.
- **Constraint:** No degraded or best-effort continuation.

### Invalid or unsafe write target

- **Condition:** `path_security.validate_write_path()` rejects a path.
- **Behavior:** Write does not occur.
- **Constraint:** There is no bypass path.

### Security refusal

- **Condition:** `SECURITY_REFUSAL` is produced.
- **Behavior:** Stop, gate, and log.
- **Constraint:** Rephrasing does not bypass the refusal.

### Unknown XPC message type

- **Condition:** Received XPC message type is not recognized.
- **Behavior:** Discard and log.
- **Constraint:** Do not raise as an exception.

### Generation / validation failures

Failure strategy is selected by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`.

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- hard cap of 20 local attempts, then move on

This makes failure type the primary routing signal and attempt count the secondary escalation signal.

### Polling and API pressure

- **403 primary:** exponential backoff from 2s to 64s
- **429 secondary:** respect `Retry-After`
- **Constraint:** polling endpoints use ETag caching

### Oversized context or logs

- **Context overflow:** `ContextManager` auto-trims at 30k tokens while preserving the spec-anchor first turn and last 6 messages.
- **CI log overflow:** truncate to 8k chars with 70% head / 30% tail.
- **Behavior:** automatic; no operator action required.

### Crash / restart during PR execution

- **Condition:** Process interruption mid-pipeline.
- **Behavior:** Resume using per-PR stage checkpoints.
- **Guarantee:** Completed work is not re-run.

### Persistent learning artifact mishandling

- **Condition:** Clean-run or reset logic attempts to remove learning artifacts.
- **Behavior required by architecture:** do not delete automatically.
- **Protected artifacts:**
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md` unless switching to a completely new codebase

## Dependencies

### Internal code units

- `src/build_director.py`
  - `BuildPipeline`
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
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
- `ContextManager`

### Persistent stores and files

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md`
  - loaded by `DocumentStore` automatically
  - written after each build run when 3+ recurring failure patterns are found

### External services and protocols

- XPC transport
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB max per message
- LLM providers
  - two providers generate in parallel
  - Claude arbitrates
- GitHub
  - accessed only through `GitHubTool`
- DocumentStore
  - used for retrieval of generation context and automatic loading of build rules

### UI/protocol message contracts

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

These protocol contracts define how CraftedAgent exposes state, blocks for decisions, and reports document availability/status to the rest of the system.