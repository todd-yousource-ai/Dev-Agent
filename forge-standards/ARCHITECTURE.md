# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into a staged, operator-gated implementation workflow.

Within the Forge architecture, ForgeAgent:

- decomposes requested work into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitration path in consensus
- performs self-correction, lint gating, and a bounded local fix loop
- executes CI
- blocks on operator approval before merge
- persists per-PR stage checkpoints so completed work is not re-run after crashes
- preserves cross-run learning through persistent build memory and build rules

ForgeAgent is also the enforcement point for several platform-wide controls:

- all file writes are path-validated before execution
- all GitHub operations are routed through `GitHubTool`
- all untrusted external input is validated
- generated code is never executed by the agent
- approval gates never auto-resolve
- auth, crypto, identity, and security refusal conditions fail closed

The subsystem includes Python backend components explicitly named in the architecture context:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`
- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
- `src/build_ledger.py` — per-PR stage checkpointing and run progress persistence implied by stage checkpoint invariants

## Component Boundaries

### Inside ForgeAgent

ForgeAgent owns:

- build orchestration and stage progression
- scope-confidence gating before implementation proceeds
- PR decomposition and `pr_type` routing
- multi-provider generation and consensus arbitration
- self-correction, lint gate, and bounded fix-loop behavior
- CI execution and CI-result handling
- operator gate presentation and indefinite waiting semantics
- GitHub interaction through `GitHubTool`
- path validation prior to file writes
- persistence of build memory and build rules
- per-PR checkpointing to support crash recovery
- document loading and context assembly for generation

### Outside ForgeAgent

ForgeAgent does not own:

- direct GitHub API usage outside `GitHubTool`
- execution of generated code via `eval`, `exec`, or subprocess of generated content
- bypass of operator approval gates
- silent fallback behavior for auth, crypto, identity, or refusal conditions
- arbitrary filesystem writes outside validated repository roots
- treating external documents or PR comments as trusted input
- promotion of external context into the SYSTEM prompt

### Filesystem Boundary

All writes must pass `path_security.validate_write_path()` before execution.

Allowed root behavior is constrained by path security:

- standard explicit roots: `src`, `tests`, `docs`, `scripts`
- infrastructure roots: `.github`, `tools`, `schemas`, `contracts`, `configs`
- CamelCase roots for Swift/Xcode projects, including roots such as `CraftedApp`, `CraftedTests`, and `ForgeAgent`
- smart root detection should allow roots matching `^[A-Za-z][A-Za-z0-9_-]*$`

Dot-prefixed roots require explicit allowlisting, specifically `.github`.

This boundary exists to prevent silent write failures and path-security rejection when committing into unexpected root directories.

## Data Flow

### 1. Intent Ingress

ForgeAgent accepts a plain-language build intent from the operator.

Related protocol state is exchanged over XPC using:

- line-delimited JSON
- nonce-authenticated messages
- maximum 16MB per message

Startup readiness is communicated with:

- `ready`: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`

### 2. Scope and Confidence Gate

Before implementation, ForgeAgent performs a scope-confidence evaluation.

The documented gating behavior is:

- `SCOPE_SYSTEM` returns `confidence` from 0–100 and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold, the system shows gaps and offers `proceed`, `answer`, or `cancel`
- if the operator provides gap answers, a one-shot re-scope occurs
- no repeated re-scope loop is allowed

This makes scope insufficiency an explicit operator decision rather than an implicit continuation.

### 3. Context Assembly

Generation context is assembled from trusted internal state plus validated external sources.

Inputs include:

- repository documents via the Document Store
- specific loaded documents such as `PRODUCT_CONTEXT.md`
- persistent `build_memory.json`
- persistent `build_rules.md`
- prior conversation state, trimmed by `ContextManager`

Context constraints:

- context from external documents goes in the USER prompt, never the SYSTEM prompt
- external documents, PR comments, and CI output are untrusted and must be validated
- `ContextManager` auto-trims at 30k tokens
- it preserves the spec-anchor first turn plus the last 6 messages
- CI log output is truncated at 8k chars using 70% head / 30% tail

### 4. Generation and Consensus

ForgeAgent generates implementation and tests for a PR using two LLM providers in parallel.

Consensus behavior is owned by `ConsensusEngine` in `src/consensus.py`, with generation system prompts including:

- `GENERATION_SYSTEM`
- `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

Claude is the arbitration path in the platform overview.

### 5. Write and GitHub Execution

Generated changes are applied only through validated write paths and approved GitHub tooling.

Enforced routing:

- all GitHub operations go through `GitHubTool`
- never use the GitHub API directly
- validate paths before any write

### 6. Validation and Repair Loop

After generation, ForgeAgent runs:

- a self-correction pass
- a lint gate
- a bounded local fix loop of up to 20 attempts

Failure strategy selection is driven by `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely — max 20 local attempts, then move on

### 7. CI and Operator Gate

ForgeAgent executes CI, surfaces results, and then blocks for operator approval before merge.

Protocol surfaces include:

- `build_card`: `{ card_type, stage, content, progress }` streamed to `BuildStreamView`
- `gate_card`: `{ gate_type, options[], description }` which blocks until operator responds

Gate semantics are strict:

- gates wait indefinitely for operator input
- no auto-approve ever

### 8. Persistence and Recovery

ForgeAgent persists run and learning state.

Persistent learning artifacts:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - must not be deleted on clean runs
- `Mac-Docs/build_rules.md`
  - loaded by `DocumentStore` automatically
  - written after each build run when 3 or more recurring failure patterns are found
  - must not be deleted on clean runs unless switching to a completely new codebase

Crash recovery behavior:

- per-PR stage checkpoints prevent re-running completed work after a crash

## Key Invariants

ForgeAgent must enforce the following invariants from the Forge context.

### Security and Trust

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input, including documents, PR comments, and CI output, is untrusted and validated.
- Generated code is never executed by the agent; no `eval`, no `exec`, no subprocess of generated content.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.

### Human Control

- Gates wait indefinitely for operator input.
- No auto-approve ever.
- Below-threshold scope confidence requires explicit operator disposition.

### Filesystem and Repository Safety

- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- ForgeAgent must enforce allowed root directory policy.
- `.github` must be explicitly allowlisted due to dot-prefix handling.
- CamelCase project roots such as `ForgeAgent` are valid through smart root detection.
- Smart root detection should accept roots matching `^[A-Za-z][A-Za-z0-9_-]*$`.

### Prompt and Context Discipline

- Context from external documents belongs in the USER prompt, never the SYSTEM prompt.
- Build memory and build rules are persistent learning systems and are never cleared automatically.
- Context trimming is automatic and bounded.

### Reliability and Progress

- Per-PR stage checkpoints prevent duplicate execution after crashes.
- Retry behavior is bounded to 20 local attempts.
- Polling behavior uses ETag caching on all polling endpoints.
- `403 primary` errors use exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`.
- `429 secondary` errors must respect the `Retry-After` header.

## Failure Modes

### Scope Confidence Below Threshold

Condition:
- `_stage_scope` receives confidence below 85

Behavior:
- present coverage gaps
- offer `proceed`, `answer`, or `cancel`
- allow one re-scope only if operator answers gaps
- do not loop indefinitely

### Path Validation Failure

Condition:
- write target fails `path_security.validate_write_path()`
- or target root is outside the allowed root policy

Behavior:
- reject the write
- surface the error with context
- do not silently skip or redirect the write

Relevant triggers include:
- missing allowlisting for `.github`
- unexpected repository roots
- path-security rejection of invalid dot-prefixed or nonconforming roots

### GitHub Operation Misuse

Condition:
- a component attempts direct GitHub API access instead of using `GitHubTool`

Behavior:
- this is out of policy for ForgeAgent
- all GitHub operations must be routed through `GitHubTool`

### Auth, Crypto, or Identity Errors

Condition:
- authentication, cryptographic, or identity validation fails

Behavior:
- fail closed
- no degraded or permissive fallback
- surface the error with context

### Security Refusal

Condition:
- model or policy emits `SECURITY_REFUSAL`

Behavior:
- stop processing
- gate
- log
- do not attempt bypass via rephrasing

### Unknown XPC Message Type

Condition:
- ForgeAgent receives an unknown XPC message type

Behavior:
- discard and log
- do not raise as an exception

### Generation/Build/Test Failure

Condition:
- local validation, test, import, runtime, or assertion failures occur

Behavior:
- choose recovery strategy using `_choose_strategy(failure_type, attempt, records)`
- route:
  - `assertion_error` → `test_driven`
  - `import_error` / `runtime_error` → `converse` then `test_driven`
  - `attempt >= 8` → `nuclear` every 3rd attempt
- stop after 20 local attempts and move on

### Rate Limiting and Polling Failures

Condition:
- polling or API operations encounter rate limiting or permission throttling

Behavior:
- use ETag caching on polling endpoints
- on `403 primary`, exponential backoff from 2s to 64s
- on `429 secondary`, honor `Retry-After`

### Crash During PR Processing

Condition:
- ForgeAgent crashes mid-stage or mid-PR

Behavior:
- recover from per-PR stage checkpoints
- do not re-run already completed work

### Secret Exposure Risk

Condition:
- logs, errors, prompts, or generated artifacts may include secrets

Behavior:
- secrets must never appear in logs, error messages, or generated code

## Dependencies

### Internal Components

- `BuildPipeline` in `src/build_director.py`
- `ConsensusEngine` in `src/consensus.py`
- generation system prompt definitions in `src/consensus.py`
- `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
- `build_ledger` functionality in `src/build_ledger.py`
- `path_security.validate_write_path()`
- `failure_handler.py` strategy selection
- `ContextManager`
- `DocumentStore`
- `build_memory`

### Persistent Artifacts

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Protocol Dependencies

- XPC line-delimited JSON transport
- nonce authentication on XPC messages
- `ready`, `build_card`, `gate_card`, `credentials`, and `doc_status` protocol objects

Defined protocol objects from the context include:

- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### External Service Classes

ForgeAgent depends on external providers only through the architecture described in the TRDs:

- two LLM providers operating in parallel
- GitHub through `GitHubTool`
- CI execution as part of the build pipeline

Direct external API usage outside these mediated components is outside subsystem policy.