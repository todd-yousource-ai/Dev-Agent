# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is a native macOS AI coding agent subsystem within the Crafted Dev Agent platform. It takes a plain-language build intent and participates in an end-to-end build pipeline that:

1. decomposes work into an ordered sequence of pull requests,
2. generates implementation and tests for each PR using two LLM providers in parallel,
3. arbitrates generation through the consensus path,
4. runs self-correction, lint gating, and a 20-pass local fix loop,
5. executes CI,
6. blocks on operator approval before merge.

Within that platform, ForgeAgent is responsible for safe, gated code-generation and repository mutation behavior under strict security and operational constraints.

It enforces:

- path-validated file writes before execution,
- explicit repository root controls with smart root detection,
- fail-closed behavior on auth, crypto, and identity errors,
- operator-gated progression at key decision points,
- persistent per-PR checkpointing to avoid re-running completed work after crashes,
- persistent build learning via build memory and build rules,
- strict handling of untrusted external inputs,
- prohibition on executing generated code.

It also participates in scoped planning behavior through a confidence gate:

- `SCOPE_SYSTEM` returns `confidence` (0–100) and `coverage_gaps`,
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`,
- below threshold, the operator is shown gaps and offered `proceed`, `answer`, or `cancel`,
- if the operator answers the gaps, ForgeAgent performs a one-shot re-scope only; no repeated loop.

## Component Boundaries

ForgeAgent is bounded by the following responsibilities and non-responsibilities.

### Inside the subsystem

- Build pipeline orchestration via `src/build_director.py`
  - `BuildPipeline` orchestration
  - confidence gate handling
  - `pr_type` routing
- Consensus generation via `src/consensus.py`
  - `ConsensusEngine`
  - `GENERATION_SYSTEM`
  - `SWIFT_GENERATION_SYSTEM`
  - `UI_ADDENDUM`
- GitHub operations through `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`
- Build state persistence through `src/build_ledger.py`
- Persistent learning artifacts
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`
- Document-backed generation context through the Document Store
- Operator-facing gate and build-card protocol participation
- Path validation before any write operation

### Outside the subsystem

- Direct use of the GitHub API
  - all GitHub operations must go through `GitHubTool`
- Execution of generated code
  - no `eval`
  - no `exec`
  - no subprocess execution of generated content
- Automatic operator approval
  - gates block indefinitely until operator input
- Automatic clearing of persistent learning state
  - build memory and build rules are never cleared on clean runs
- Promotion of external context into privileged system instructions
  - external document context belongs in the `USER` prompt, never the `SYSTEM` prompt
- Raising unknown XPC message types as exceptions
  - they are discarded and logged

### Repository root boundary

ForgeAgent must constrain file mutations to allowed repository roots.

Required explicitly allowed roots for a standard project include:

- `src`
- `tests`
- `docs`
- `scripts`
- `.github`
- `tools`
- `schemas`
- `contracts`
- `configs`

Additionally, CamelCase roots for Swift/Xcode-style projects are supported through smart root detection rather than exhaustive enumeration. The allowed root rule is:

- allow any root matching `^[A-Za-z][A-Za-z0-9_-]*$`

This covers CamelCase or lowercase single-word roots such as:

- `CraftedApp`
- `CraftedTests`
- `ForgeAgent`

Dot-prefixed roots such as `.github` still require explicit allowlisting.

All writes remain subject to strict path validation through `path_security.validate_write_path()`.

## Data Flow

### 1. Build intent ingestion

- ForgeAgent receives a plain-language build intent.
- External inputs are treated as untrusted, including:
  - documents,
  - PR comments,
  - CI output.

These inputs are validated before use.

### 2. Scope and confidence gating

- Scope analysis runs through the scope system.
- `SCOPE_SYSTEM` returns:
  - `confidence`
  - `coverage_gaps`
- `_stage_scope` compares confidence against `_CONFIDENCE_THRESHOLD = 85`.

Behavior at the gate:

- at or above threshold: proceed,
- below threshold: present gaps and offer:
  - proceed,
  - answer,
  - cancel.
- if the operator provides answers, perform one one-shot re-scope,
- no iterative re-scope loop is allowed.

### 3. Context assembly

Generation context is assembled from:

- repository state,
- Document Store content,
- specific loaded documents such as `PRODUCT_CONTEXT.md`,
- persistent `build_memory.json`,
- persistent `build_rules.md`.

Context management constraints:

- external document context goes into the `USER` prompt only,
- `ContextManager` auto-trims at 30k tokens,
- it preserves the spec-anchor first turn and the last 6 messages.

### 4. Parallel generation and arbitration

- Implementation and tests are generated using two LLM providers in parallel.
- Claude arbitrates through the consensus path.
- Consensus-related logic resides in `src/consensus.py`.

### 5. File mutation

Before any write:

- the target path must pass `path_security.validate_write_path()`.

Write eligibility is constrained by:

- allowed repository roots,
- smart root detection for standard named roots matching `^[A-Za-z][A-Za-z0-9_-]*$`,
- explicit allowlisting for dot-prefixed roots such as `.github`.

### 6. Local correction and validation loop

After generation, ForgeAgent runs:

- a self-correction pass,
- a lint gate,
- a local fix loop with a hard maximum of 20 attempts.

Failure strategy selection follows `failure_handler.py:_choose_strategy(failure_type, attempt, records)`:

- `failure_type` is the primary signal,
- `attempt` count is the secondary escalation signal,
- `assertion_error` → `test_driven` immediately,
- `import_error` / `runtime_error` → `converse` first, then `test_driven`,
- `attempt >= 8` → `nuclear` every 3rd attempt,
- never retry indefinitely.

### 7. CI and truncation behavior

- ForgeAgent executes CI as part of pipeline validation.
- CI log output is truncated at 8k characters using:
  - 70% head,
  - 30% tail.

### 8. GitHub operations

All repository and PR operations flow through `GitHubTool`.

Operational controls include:

- no direct GitHub API usage,
- ETag caching on all polling endpoints,
- `403` primary rate/permission handling with exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- `429` secondary handling by respecting `Retry-After`.

### 9. Operator gating and merge progression

ForgeAgent emits protocol cards:

- `build_card`
  - `{ card_type, stage, content, progress }`
  - streamed to `BuildStreamView`
- `gate_card`
  - `{ gate_type, options[], description }`
  - blocks until operator responds

There is no auto-approve path.

### 10. Persistence and recovery

ForgeAgent persists progress and learning in two forms.

Per-PR execution state:

- per-PR stage checkpoints prevent re-running completed work after a crash.

Persistent learning:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes,
  - written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md`
  - loaded by DocumentStore automatically,
  - written after each build run when 3 or more recurring failure patterns are found.

These artifacts are intentionally persistent and are not deleted on clean runs.

## Key Invariants

ForgeAgent operates under the following hard invariants.

- Fail closed on auth, crypto, and identity errors.
- No silent failure paths; every error must surface with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no auto-approve ever.
- All file writes are path-validated via `path_security.validate_write_path()` before execution.
- Context from external documents goes in the `USER` prompt, never the `SYSTEM` prompt.
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log.
- XPC unknown message types are discarded and logged, never raised as exceptions.
- Per-PR stage checkpoints prevent duplicate completed work after crashes.
- Build memory and build rules are persistent learning systems and are never cleared automatically.

Additional repository-path invariant:

- writes must remain within validated allowed roots,
- `.github` requires explicit allowlisting,
- CamelCase and lowercase single-word roots are accepted via `^[A-Za-z][A-Za-z0-9_-]*$`.

## Failure Modes

### Scope uncertainty

Condition:
- `SCOPE_SYSTEM` returns confidence below `85`.

Behavior:
- stop at `_stage_scope`,
- surface `coverage_gaps`,
- offer operator choices: `proceed`, `answer`, `cancel`,
- if answered, allow one re-scope pass only.

### Path security rejection

Condition:
- write target fails `path_security.validate_write_path()`,
- or target root is not explicitly allowed / does not match the smart-root rule.

Behavior:
- block the write,
- do not silently redirect or degrade.

### Auth, crypto, or identity failure

Condition:
- any authentication, cryptographic, or identity validation error.

Behavior:
- fail closed,
- do not continue in degraded mode.

### Untrusted input violations

Condition:
- external documents, PR comments, or CI output fail validation or trigger security refusal behavior.

Behavior:
- stop,
- gate,
- log,
- do not bypass `SECURITY_REFUSAL` via rephrasing.

### Unknown XPC message type

Condition:
- receipt of an unknown XPC message type.

Behavior:
- discard and log,
- never raise as an exception.

### Local build/test failure escalation

Condition:
- local generation output fails assertions, imports, runtime checks, lint, or tests.

Behavior:
- choose strategy via `_choose_strategy(failure_type, attempt, records)`,
- escalate by failure type first, attempt count second,
- stop local retries at 20 attempts maximum.

### GitHub polling or API pressure

Condition:
- polling endpoints or GitHub operations encounter throttling or access pressure.

Behavior:
- use ETag caching on polling endpoints,
- apply exponential backoff for `403` primary:
  - 2s, 4s, 8s, 16s, 32s, 64s
- respect `Retry-After` on `429` secondary.

### Crash recovery

Condition:
- crash during PR execution.

Behavior:
- resume from per-PR stage checkpoints,
- do not re-run stages already marked complete.

### Oversized conversational/runtime context

Condition:
- context growth exceeds model budget.

Behavior:
- `ContextManager` auto-trims at 30k tokens,
- preserve spec-anchor first turn and last 6 messages.

## Dependencies

### Internal code modules

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

### Platform services and protocols

- XPC wire format
  - line-delimited JSON
  - nonce-authenticated
  - max 16MB per message
- ready message
  - `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- build card protocol
  - `build_card: { card_type, stage, content, progress }`
- gate card protocol
  - `gate_card: { gate_type, options[], description }`
- credentials payload
  - `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- document status payload
  - `{ doc_id, doc_name, status, chunk_count, embedded_count }`

### Data dependencies

- Document Store
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- repository working tree and PR state

### External provider dependencies

- two LLM providers in parallel
- GitHub access exclusively through `GitHubTool`

### Operational dependency constraints

- no direct GitHub API access outside `GitHubTool`
- no execution of generated code
- no automatic deletion of build memory or build rules
- no auto-approval path for gated actions