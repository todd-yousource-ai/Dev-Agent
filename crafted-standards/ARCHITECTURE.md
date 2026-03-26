# Architecture - CraftedAgent

## What This Subsystem Does

CraftedAgent is the native macOS AI coding agent subsystem that turns a plain-language build intent into an operator-gated sequence of pull requests.

Within the Forge architecture, it is responsible for:

- decomposing requested work into an ordered PR plan
- generating implementation and tests for each PR using two LLM providers in parallel
- arbitrating generation through the consensus layer
- running self-correction, lint, and bounded local fix loops
- executing CI and surfacing results
- checkpointing per-PR stage progress so completed work is not repeated after crashes
- preserving persistent build learning via build memory and build rules
- blocking for operator decisions at explicit gates, including scope and merge approval

The subsystem is human-in-the-loop by design. Gates block indefinitely until the operator responds; there is no auto-approval path.

## Component Boundaries

CraftedAgent includes orchestration and policy enforcement for the build workflow, but it is bounded by strict interfaces and operational rules.

### Included responsibilities

- **Build orchestration**
  - `src/build_director.py` contains BuildPipeline orchestration, confidence gating, and `pr_type` routing.
- **Consensus-based generation**
  - `src/consensus.py` contains `ConsensusEngine` and generation system prompts including `GENERATION_SYSTEM` and `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`.
- **GitHub operations abstraction**
  - All GitHub interactions are mediated through `GitHubTool` in `src/github_tools.py`.
- **Persistent build learning**
  - `workspace/{engineer_id}/build_memory.json` stores cross-run build memory.
  - `Mac-Docs/build_rules.md` stores self-improving coding rules derived from build history.
- **Checkpointed execution**
  - Per-PR stage checkpoints prevent re-running completed work after a crash.
- **Operator gating**
  - Scope confidence and other blocking decisions are surfaced via gate cards and remain blocked until input is received.

### Excluded responsibilities

- **Direct GitHub API usage**
  - Forbidden. All GitHub operations must go through `GitHubTool`.
- **Execution of generated code**
  - Generated code is never executed by the agent. No `eval`, no `exec`, and no subprocess execution of generated content.
- **Unvalidated writes**
  - No file write may occur before path validation through `path_security.validate_write_path()`.
- **Silent degradation**
  - Auth, crypto, and identity errors must fail closed; the subsystem never degrades silently.
- **SYSTEM-prompt injection from external documents**
  - Context from external documents is placed in the USER prompt only, never the SYSTEM prompt.

## Data Flow

The subsystem processes build intent through a staged, gated pipeline.

### 1. Session and protocol initialization

CraftedAgent communicates over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16 MB per message

Relevant protocol messages include:

- `ready`
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator response
- `credentials`
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

Unknown XPC message types are discarded and logged, never raised as exceptions.

### 2. Scope analysis and confidence gate

Before implementation proceeds, the subsystem performs scope evaluation.

Documented behavior:

- `SCOPE_SYSTEM` returns:
  - `confidence` from 0–100
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the agent shows the identified gaps
- offers the operator:
  - proceed
  - answer
  - cancel
- if the operator answers the gaps, a one-shot re-scope is performed
- there is no repeated re-scoping loop

This gate is explicit and blocking.

### 3. Context assembly

Generation context is assembled from trusted local state plus validated external sources.

Inputs may include:

- repository context
- document store content
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- persistent build memory
- persistent build rules
- external documents, PR comments, and CI output

All external input is untrusted and must be validated.

Context handling constraints:

- external document context goes into the USER prompt, never the SYSTEM prompt
- `ContextManager` auto-trims at 30k tokens
- it preserves:
  - the spec-anchor first turn
  - the last 6 messages
- CI log output is truncated at 8k characters using:
  - 70% head
  - 30% tail

### 4. PR planning and generation

For each planned PR, CraftedAgent generates implementation and tests using two LLM providers in parallel, with Claude arbitrating through the consensus engine.

The consensus layer is implemented in:

- `src/consensus.py`

The orchestration and PR routing layer is implemented in:

- `src/build_director.py`

### 5. Local correction and bounded retry behavior

After generation, CraftedAgent runs local quality and repair passes, including:

- self-correction
- lint gate
- bounded fix loop
- maximum 20 local attempts, then move on

Failure handling rules are selected in `failure_handler.py` through:

- `_choose_strategy(failure_type, attempt, records)`

Strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely

### 6. CI and remote interaction behavior

CraftedAgent executes CI and reacts to service-side throttling and polling constraints.

Required behaviors:

- `403 primary` → exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429 secondary` → respect `Retry-After` header
- ETag caching on all polling endpoints

### 7. Persistence and learning updates

After every successful PR:

- `build_memory.record_pr()` writes to:
  - `workspace/{engineer_id}/build_memory.json`

After each build run, when 3 or more recurring failure patterns are found:

- `build_rules.md` is written to:
  - `Mac-Docs/build_rules.md`

These stores are persistent learning systems and must not be automatically cleared.

### 8. Operator gate before merge

The subsystem blocks on operator approval before merging.

Invariant behavior:

- gates wait indefinitely for operator input
- no auto-approve ever

## Key Invariants

The subsystem must enforce the following architectural invariants:

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve path exists.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- Unknown XPC message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Build memory and build rules are persistent and are never cleared automatically.

Additional operational invariants from the TRDs:

- All GitHub operations go through `GitHubTool`.
- `_stage_scope` gates when confidence is below 85.
- Re-scope after operator clarification is one-shot only.
- Local repair is bounded to 20 attempts maximum.
- Context trimming is automatic and bounded.
- CI log inclusion is truncated automatically.

## Failure Modes

CraftedAgent treats failures as first-class surfaced states rather than hidden retries.

### Scope uncertainty

When scope confidence is below threshold:

- the subsystem does not silently continue
- it presents `coverage_gaps`
- it blocks on operator choice:
  - proceed
  - answer
  - cancel

### Auth, crypto, and identity failures

These fail closed immediately. The subsystem must not continue in a degraded state.

### Untrusted or malformed external input

External inputs such as documents, PR comments, and CI output are treated as untrusted and validated before use. Invalid input must not be promoted into trusted execution or prompt channels.

### Security refusal

If `SECURITY_REFUSAL` is produced:

- it is not bypassed through rephrasing
- the subsystem stops
- gates
- logs the event

### Unknown XPC message types

Unknown message types are:

- discarded
- logged
- not raised as exceptions

This avoids protocol crashes while preserving observability.

### Write path violations

Any attempted file write that fails `path_security.validate_write_path()` must not execute.

### Generation/test/build failure during local repair

Repair strategy depends on failure type and attempt count:

- assertion failures immediately switch to test-driven handling
- import/runtime failures begin with conversational diagnosis, then escalate
- high-attempt scenarios periodically escalate to nuclear handling
- retries stop after 20 attempts

### Rate limiting and polling failures

Remote service failures are handled deterministically:

- `403 primary` uses fixed exponential backoff up to 64 seconds
- `429 secondary` honors `Retry-After`
- polling uses ETag caching

### Crash recovery

Per-PR stage checkpoints prevent re-running completed work after a crash. Recovery resumes from the last incomplete stage rather than replaying the entire PR flow.

## Dependencies

Documented subsystem dependencies are:

### Internal components

- `src/build_director.py`
  - BuildPipeline orchestration
  - confidence gate
  - `pr_type` routing
- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompt definitions
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `failure_handler.py`
  - failure strategy selection via `_choose_strategy(...)`
- `path_security.validate_write_path()`
  - required for all file writes
- `ContextManager`
  - automatic prompt trimming and message preservation behavior
- `build_memory.record_pr()`
  - persistence update after successful PR
- `DocumentStore`
  - document loading and automatic `build_rules.md` loading

### Persistent stores

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External integrations

- XPC transport using the documented wire format
- LLM providers used in parallel generation
- GitHub, accessed only through `GitHubTool`
- CI systems whose output is consumed as untrusted input

The subsystem depends on these interfaces but preserves strict boundaries around validation, gating, persistence, and non-execution of generated content.