# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem that drives the end-to-end build workflow from plain-language build intent to gated merge-ready pull requests.

At a subsystem level, ForgeAgent:

- decomposes a build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbiter in consensus generation flow
- runs self-correction, a lint gate, and a bounded local fix loop
- executes CI
- blocks on explicit operator approval before merge-related progression
- persists per-PR progress so completed stages are not re-run after crashes
- retains long-lived build learning through persistent build memory and build rules

ForgeAgent also integrates repository context and external documentation into generation, while treating all such input as untrusted and validated. Document-derived context is placed in the USER prompt only, never in the SYSTEM prompt.

The subsystem enforces a human-in-the-loop operating model. Gates do not auto-approve and wait indefinitely for operator input.

## Component Boundaries

ForgeAgent is bounded by the components and responsibilities explicitly defined in the source material.

### Included responsibilities

#### Build orchestration
`src/build_director.py` contains build pipeline orchestration, including:

- BuildPipeline orchestration
- scope confidence gating
- `pr_type` routing

This is the control plane for staging work through the core loop.

#### Consensus generation
`src/consensus.py` contains:

- `ConsensusEngine`
- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

This component is responsible for multi-provider generation behavior and arbitration.

#### GitHub operations
`src/github_tools.py` contains:

- `GitHubTool`
- `WebhookReceiver`

All GitHub operations must go through `GitHubTool`. Direct GitHub API access is outside subsystem policy and forbidden.

#### Build state persistence
`src/build_ledger.py` is identified as part of the Python backend file set and, together with the documented checkpoint behavior, defines persisted build progress across failures.

The subsystem uses per-PR stage checkpoints to prevent re-running completed work after a crash.

#### Persistent learning artifacts
ForgeAgent owns and preserves:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are persistent learning systems and are not automatically cleared on clean runs.

#### Document-store-backed context usage
ForgeAgent consumes document store content for generation context, including loading specific documents such as `PRODUCT_CONTEXT.md`.

### Excluded responsibilities

ForgeAgent does not:

- execute generated code via `eval`, `exec`, or subprocess of generated content
- bypass operator gating
- directly call GitHub APIs outside `GitHubTool`
- silently discard identity, auth, crypto, or validation errors
- promote external document context into SYSTEM prompts
- automatically clear build memory or build rules
- treat unknown XPC messages as exceptions

Unknown XPC message types are discarded and logged.

## Data Flow

### 1. Agent initialization and transport

ForgeAgent operates over an XPC wire protocol with these constraints:

- line-delimited JSON
- nonce-authenticated
- maximum 16 MB per message

On readiness, the agent emits:

- `ready` message with  
  - `agent_version`
  - `min_swift_version`
  - `capabilities[]`
  - `doc_store_status`

### 2. Credentials ingress

Credentials are provided as:

- `credentials`
  - `anthropic_api_key`
  - `openai_api_key`
  - `github_token`
  - `engineer_id`

These secrets are operational inputs only. They must never appear in logs, error messages, or generated code.

### 3. Build intent to scoped plan

ForgeAgent accepts a plain-language build intent and enters the scope phase.

The scope gate behavior is defined by the documented headings:

- `SCOPE_SYSTEM` returns `confidence (0–100)` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the subsystem shows gaps
- offers `proceed / answer / cancel`
- allows one-shot re-scope if the operator provides gap answers
- does not loop indefinitely at this stage

### 4. Context assembly

Generation context is assembled from repository and document-store inputs.

Relevant constraints:

- external documents are untrusted and validated
- context from external documents goes in the USER prompt only
- never in the SYSTEM prompt
- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn and the last 6 messages

DocumentStore usage includes:

- primary generation context
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatic loading of `Mac-Docs/build_rules.md`

### 5. Parallel generation and arbitration

ForgeAgent generates implementation and tests using two LLM providers in parallel.

Consensus behavior uses:

- `ConsensusEngine`
- provider parallelism
- Claude arbitration

Generation system prompts are defined in `src/consensus.py` as:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`

### 6. Build execution and iterative repair

After generation, ForgeAgent runs:

- self-correction pass
- lint gate
- local fix loop up to 20 attempts

Failure handling is guided by `failure_handler.py` strategy selection:

- `_choose_strategy(failure_type, attempt, records)`
- primary signal: `failure_type`
- secondary escalation: `attempt count`

Documented strategy rules:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

### 7. CI processing

ForgeAgent executes CI and consumes CI output as untrusted input.

Operational constraints:

- CI output is validated as external input
- CI log output is truncated at 8k chars
- truncation policy is 70% head / 30% tail
- no action required for truncation; it is automatic

### 8. Operator gate

When a gate is reached, ForgeAgent emits:

- `gate_card`
  - `gate_type`
  - `options[]`
  - `description`

This blocks until the operator responds. Gates wait indefinitely. There is no auto-approve path.

### 9. UI/status streaming

ForgeAgent streams build progress as:

- `build_card`
  - `card_type`
  - `stage`
  - `content`
  - `progress`

These are rendered in `BuildStreamView`.

Document embedding/status updates are emitted as:

- `doc_status`
  - `doc_id`
  - `doc_name`
  - `status`
  - `chunk_count`
  - `embedded_count`

### 10. Persistence after successful PRs and runs

After every successful PR:

- `build_memory.record_pr()` writes to `workspace/{engineer_id}/build_memory.json`

After each build run, when 3 or more recurring failure patterns are found:

- ForgeAgent writes `Mac-Docs/build_rules.md`

Both stores persist across fresh installs, thread state wipes, and clean runs unless explicitly switching to a completely new codebase.

## Key Invariants

ForgeAgent is constrained by the following hard invariants.

### Security and trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; the subsystem stops, gates, and logs.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- XPC unknown message types are discarded and logged, never raised as exceptions.

### Human control

- Gates wait indefinitely for operator input.
- There is no auto-approve behavior.
- Below-threshold scope confidence requires explicit operator choice: proceed, answer, or cancel.

### Prompting and context isolation

- Context from external documents goes in the USER prompt only.
- External document context never goes in the SYSTEM prompt.
- Consensus generation system prompts are defined centrally in `src/consensus.py`.

### Recovery and bounded execution

- Per-PR stage checkpoints prevent re-running completed work after a crash.
- Local repair attempts are bounded at 20.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

### GitHub interaction policy

- All GitHub operations go through `GitHubTool`.
- Direct GitHub API usage is disallowed.

## Failure Modes

### Scope uncertainty

If `SCOPE_SYSTEM` returns confidence below 85 in `_stage_scope`:

- ForgeAgent does not silently continue as if scope were complete
- it presents `coverage_gaps`
- it gates on operator input
- it permits one-shot re-scope if answers are provided

### Auth, crypto, or identity failure

These failures are fail-closed. ForgeAgent must not degrade behavior or continue in a reduced-trust mode.

### Unsafe write path

Any file write that does not pass `path_security.validate_write_path()` must not execute.

### Security refusal from model output

If model output yields `SECURITY_REFUSAL`:

- ForgeAgent stops
- gates
- logs the event

It must not retry by rephrasing to bypass the refusal.

### Unknown XPC message type

Unknown message types are:

- discarded
- logged

They are not surfaced as transport exceptions.

### Generation or repair failures

Repair strategy follows `failure_handler.py` policy:

- `assertion_error` routes immediately to `test_driven`
- `import_error` and `runtime_error` route to `converse` first, then `test_driven`
- from attempt 8 onward, every 3rd attempt may use `nuclear`
- attempts stop after 20 local tries

This prevents infinite local retry loops.

### Rate limiting and polling failures

Documented network handling includes:

- `403 primary`: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary`: respect `Retry-After`
- ETag caching on all polling endpoints

### Context overflow

`ContextManager` automatically trims at 30k tokens while preserving:

- the spec-anchor first turn
- the last 6 messages

### CI log volume

CI logs are truncated automatically at 8k characters using a 70/30 head-tail split to keep error review bounded.

## Dependencies

ForgeAgent depends on the following internal interfaces, files, and platform contracts documented in the source material.

### Internal modules

- `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM+UI_ADDENDUM`
- `src/build_director.py`
  - build pipeline orchestration
  - confidence gate
  - `pr_type` routing
- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- `src/build_ledger.py`
- `failure_handler.py`
  - `_choose_strategy(failure_type, attempt, records)`
- `path_security.validate_write_path()`
- `ContextManager`
- `DocumentStore`
- `BuildStreamView`

### Persistent data stores

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### External providers and credentials

- Anthropic provider via `anthropic_api_key`
- OpenAI provider via `openai_api_key`
- GitHub access via `github_token`
- engineer-scoped persistence via `engineer_id`

### Transport and protocol

- XPC wire format
  - line-delimited JSON
  - nonce-authenticated
  - 16 MB max message size
- message contracts
  - `ready`
  - `build_card`
  - `gate_card`
  - `credentials`
  - `doc_status`

### External systems

- GitHub, only through `GitHubTool`
- CI systems, treated as untrusted input sources
- document sources consumed through the document store

