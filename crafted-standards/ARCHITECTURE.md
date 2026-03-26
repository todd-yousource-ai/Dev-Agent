# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding agent subsystem that executes the build workflow for a plain-language build intent.

At a system level, it:

- decomposes build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR
- uses two LLM providers in parallel, with Claude arbitrating
- runs a self-correction pass
- runs a lint gate
- runs a bounded 20-pass fix loop
- executes CI
- blocks on operator approval before merge

It is a human-gated build subsystem, not an autonomous merge system. Gates block indefinitely until operator input is provided; there is no auto-approve behavior.

Within the repository structure called out by the TRDs, the subsystem’s core orchestration is centered in:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM` + `UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py`

The subsystem also participates in persistent learning via:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These stores are intentionally durable across runs and fresh installs.

## Component Boundaries

CraftedAgent is responsible for:

- build orchestration across PR stages
- scope evaluation and gating
- LLM-driven code and test generation
- consensus/arbitration across providers
- self-correction, lint, and local fix-loop execution
- CI execution handling
- operator gating before merge
- emitting protocol messages for UI/host integration
- recording persistent build memory and build rules
- path-validated file writes
- GitHub operations exclusively through `GitHubTool`
- using document context for generation through the document store flow

CraftedAgent is not responsible for:

- bypassing operator review or approval gates
- executing generated code via `eval`, `exec`, or subprocess invocation of generated content
- trusting external documents, PR comments, or CI output without validation
- writing files without `path_security.validate_write_path()`
- calling the GitHub API directly outside `GitHubTool`
- placing external document context into the SYSTEM prompt
- auto-clearing `build_memory.json` or `build_rules.md`
- re-running already completed per-PR stages after crash recovery checkpoints
- raising exceptions on unknown XPC message types; those are discarded and logged

Boundary-critical storage and integration constraints:

- All GitHub operations must go through `GitHubTool`.
- All file writes must be path-validated before execution.
- Build memory and build rules are persistent learning systems and must not be cleared automatically.
- External document context belongs in the USER prompt only.

## Data Flow

1. **Initialization / Host handshake**
   - CraftedAgent communicates over XPC using line-delimited JSON.
   - Messages are nonce-authenticated.
   - Maximum message size is 16MB.
   - The `ready` message reports:
     - `agent_version`
     - `min_swift_version`
     - `capabilities[]`
     - `doc_store_status`

2. **Credential intake**
   - Credentials are provided via the `credentials` payload:
     - `anthropic_api_key`
     - `openai_api_key`
     - `github_token`
     - `engineer_id`
   - Auth, crypto, and identity failures fail closed.

3. **Intent intake and scope stage**
   - A plain-language build intent enters the build pipeline.
   - The subsystem evaluates scope using the documented scope confidence gate.
   - `SCOPE_SYSTEM` returns:
     - `confidence` from `0–100`
     - `coverage_gaps`
   - `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`.
   - If below threshold, the operator is shown gaps and offered:
     - proceed
     - answer
     - cancel
   - If the operator answers coverage gaps, one one-shot re-scope is allowed; there is no loop.

4. **Context assembly**
   - DocumentStore is used for generation context.
   - A specific document may be loaded, e.g. `PRODUCT_CONTEXT.md`.
   - External document context is inserted into the USER prompt, never the SYSTEM prompt.
   - ContextManager automatically trims at 30k tokens.
   - It preserves:
     - the spec-anchor first turn
     - the last 6 messages

5. **Generation and consensus**
   - For each PR, implementation and tests are generated.
   - Two LLM providers run in parallel.
   - `ConsensusEngine` arbitrates.
   - Prompting is rooted in the generation systems defined in `src/consensus.py`.

6. **Correction and validation**
   - Generated output goes through:
     - self-correction pass
     - lint gate
     - bounded fix loop up to 20 local attempts
   - Failure strategy selection in `failure_handler.py` uses:
     - primary signal: `failure_type`
     - secondary signal: `attempt`
   - Documented strategy rules:
     - `assertion_error` → `test_driven` immediately
     - `import_error` / `runtime_error` → `converse` first, then `test_driven`
     - `attempt >= 8` → `nuclear` every 3rd attempt
     - never retry indefinitely

7. **CI handling**
   - CraftedAgent executes CI and processes CI output as untrusted input.
   - CI log output is truncated to 8k chars using:
     - 70% head
     - 30% tail
   - Polling behavior includes:
     - ETag caching on all polling endpoints
     - `403` primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
     - `429` secondary: respect `Retry-After`

8. **Operator gate**
   - Approval is surfaced via `gate_card`:
     - `gate_type`
     - `options[]`
     - `description`
   - This gate blocks until the operator responds.
   - There is no auto-approve path.

9. **Streaming status**
   - Progress is streamed via `build_card`:
     - `card_type`
     - `stage`
     - `content`
     - `progress`
   - Build stream output is intended for `BuildStreamView`.

10. **Persistence and checkpointing**
    - Per-PR stage checkpoints prevent re-running completed work after a crash.
    - After every successful PR, `build_memory.record_pr()` writes to:
      - `workspace/{engineer_id}/build_memory.json`
    - After each build run, if 3+ recurring failure patterns are found, build rules are written to:
      - `Mac-Docs/build_rules.md`
    - `build_rules.md` is loaded automatically by DocumentStore.

11. **Document ingestion status**
    - Document embedding / store state is surfaced via `doc_status`:
      - `doc_id`
      - `doc_name`
      - `status`
      - `chunk_count`
      - `embedded_count`

## Key Invariants

The subsystem must enforce the following invariants exactly as specified in the TRDs:

- Fail closed on auth, crypto, and identity errors — never degrade silently.
- No silent failure paths — every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content.
- Gates wait indefinitely for operator input — no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the USER prompt — never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
- XPC unknown message types are discarded and logged — never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are never cleared automatically — they are persistent learning systems.

Operationally significant enforcement details from the TRDs:

- `_stage_scope` gates below confidence threshold `85`.
- Scope re-answering permits only one re-scope attempt.
- Retry behavior is bounded to 20 local attempts.
- Context trimming is automatic at 30k tokens while preserving anchor context.
- CI log truncation is automatic and bounded.

## Failure Modes

### Scope ambiguity or insufficient coverage
- Detected by the scope confidence gate.
- Below-threshold confidence returns `coverage_gaps`.
- System behavior is to gate and ask operator whether to proceed, answer, or cancel.
- Only one follow-up re-scope is permitted.

### Auth, crypto, or identity failure
- Must fail closed.
- No degraded or fallback execution path is allowed.

### Security refusal
- If `SECURITY_REFUSAL` is produced, the system must stop, gate, and log.
- Rephrasing is not a valid bypass.

### Invalid or unsafe external input
- Documents, PR comments, and CI output are untrusted.
- They must be validated before use.
- Unsafe input is not silently tolerated.

### Unsafe file write target
- Any write failing `path_security.validate_write_path()` must not execute.
- There is no exception to pre-write path validation.

### Unknown XPC message type
- Must be discarded and logged.
- Must not be raised as an exception.

### Generation / test / runtime failures during local fix loop
Failure handling strategy is selected by `_choose_strategy(failure_type, attempt, records)` in `failure_handler.py`.

Required escalation behavior:

- `assertion_error` → immediate `test_driven`
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- hard upper bound: 20 local attempts

The subsystem must never retry indefinitely.

### API throttling and polling failures
- `403` on primary uses exponential backoff:
  - 2s
  - 4s
  - 8s
  - 16s
  - 32s
  - 64s
- `429` on secondary respects `Retry-After`
- Polling endpoints use ETag caching

### Crash recovery
- Per-PR stage checkpoints ensure completed work is not re-run after crash.
- Recovery must resume from checkpointed state rather than replay finished stages.

### Context overflow
- ContextManager auto-trims at 30k tokens.
- It preserves the spec-anchor first turn and last 6 messages.
- This is automatic and requires no operator action.

### Oversized or noisy CI output
- CI log output is truncated to 8k characters using a 70% head / 30% tail split.
- This bounds context size while preserving beginning and terminal failure information.

## Dependencies

Code-level and subsystem dependencies explicitly identified in the TRDs:

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

- `src/build_ledger.py`

- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`

- `path_security.validate_write_path()`
  - mandatory validation before any file write

- `DocumentStore`
  - used for generation context
  - auto-loads `Mac-Docs/build_rules.md`

- `ContextManager`
  - auto-trims context at 30k tokens
  - preserves anchor and recent conversational state

- Persistent data files
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

- XPC protocol
  - line-delimited JSON
  - nonce-authenticated
  - 16MB max message size

- LLM provider credentials
  - `anthropic_api_key`
  - `openai_api_key`

- GitHub credentialing and operations
  - `github_token`
  - all GitHub operations through `GitHubTool` only

- Operator-facing protocol payloads
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

Dependency constraints that are part of architecture, not implementation detail:

- Direct GitHub API usage outside `GitHubTool` is prohibited.
- External document context may influence generation only through the USER prompt path.
- Persistent learning stores are architectural dependencies and must survive clean runs unless switching to a completely new codebase for `build_rules.md`.