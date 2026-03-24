# Architecture - ForgeAgent

## What This Subsystem Does

ForgeAgent is the native macOS AI coding agent subsystem responsible for turning a plain-language build intent into an operator-gated sequence of pull requests and staged implementation work.

Within the architecture context provided, ForgeAgent:

- decomposes build intent into an ordered sequence of pull requests
- generates implementation and tests for each PR using two LLM providers in parallel
- uses Claude as the arbitrating model in consensus
- runs a self-correction pass
- runs a lint gate
- runs a bounded 20-pass fix loop
- executes CI
- blocks on operator approval before merge
- streams build status and gate state over XPC to the UI

It is a human-in-the-loop subsystem. Gates do not auto-resolve; operator input is required whenever a gate is reached.

It also preserves persistent learning artifacts across runs:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

These are intentional long-lived memory systems and are not automatically cleared.

## Component Boundaries

ForgeAgent spans orchestration, consensus, document-backed context assembly, gated execution flow, and GitHub-mediated repository operations.

### Included responsibilities

#### Build orchestration
Implemented in the Python backend orchestration layer:

- `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing

This layer owns:

- stage sequencing
- scope confidence gating
- per-PR checkpoint progression
- operator gate handling
- bounded retry/fix behavior
- CI progression through the build loop

#### Consensus and generation setup
Implemented in:

- `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM + UI_ADDENDUM`

This layer owns:

- parallel use of two LLM providers
- arbitration behavior
- generation prompt system definitions
- generation context assembly constraints

A hard boundary exists around prompt placement:

- context from external documents must go in the USER prompt
- external document context must never be placed in the SYSTEM prompt

#### GitHub access
Implemented in:

- `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`

This boundary is strict:

- all GitHub operations go through `GitHubTool`
- the GitHub API must never be used directly outside this tool path

#### Build state and persistence
Referenced in the architecture context and document headings:

- per-PR stage checkpoints prevent re-running completed work after a crash
- `build_memory.record_pr()` writes persistent PR learning
- `build_memory.json` survives fresh installs and thread state wipes
- `build_rules.md` is a self-improving coding-rules artifact loaded by `DocumentStore`

This layer owns:

- crash recovery boundaries
- persistent build learning
- recurring failure pattern capture

#### XPC protocol interaction
ForgeAgent communicates over a line-delimited JSON XPC wire format with:

- nonce authentication
- maximum 16 MB per message

Message types explicitly referenced:

- `ready`
- `build_card`
- `gate_card`
- `credentials`
- `doc_status`

It is also responsible for safely handling invalid or unknown traffic.

### Explicit non-responsibilities

ForgeAgent does not:

- auto-approve gates
- execute generated code via `eval`, `exec`, or subprocess execution of generated content
- silently continue past auth, crypto, or identity failures
- trust external inputs without validation
- expose secrets in logs, errors, or generated code
- raise exceptions for unknown XPC message types; those are discarded and logged instead

## Data Flow

## 1. Session initialization

ForgeAgent initializes an XPC session using the defined wire format:

- line-delimited JSON
- nonce-authenticated
- max 16 MB per message

It can emit or process protocol messages including:

- `ready { agent_version, min_swift_version, capabilities[], doc_store_status }`
- `credentials { anthropic_api_key, openai_api_key, github_token, engineer_id }`

Credentials are treated as sensitive and must never appear in logs, error messages, or generated code.

## 2. Intent intake and scope analysis

The subsystem accepts a plain-language build intent and enters the scope phase.

The scope gate behavior is explicitly defined:

- `SCOPE_SYSTEM` returns `confidence (0–100)` and `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`

If confidence is below threshold:

- the system shows gaps
- offers `proceed / answer / cancel`
- supports a one-shot re-scope if the operator provides gap answers
- does not loop indefinitely in re-scope

This creates a hard operator decision point before implementation proceeds under low-confidence scope.

## 3. Context assembly

ForgeAgent uses document-backed context for generation.

DocumentStore usage is explicitly referenced for:

- primary generation context
- loading specific documents such as `PRODUCT_CONTEXT.md`
- automatic loading of `Mac-Docs/build_rules.md`

Context handling rules:

- all external input is untrusted and validated
- external documents, PR comments, and CI output are untrusted
- external document context goes into the USER prompt only
- external document context never goes into the SYSTEM prompt

Context sizing behavior:

- `ContextManager` auto-trims at 30k tokens
- preserves the spec-anchor first turn and the last 6 messages

## 4. Parallel generation and consensus

ForgeAgent generates implementation and tests for each PR using two LLM providers in parallel.

Consensus behavior is mediated by:

- `ConsensusEngine`
- Claude as arbitrator

Generation is constrained by the subsystem invariants:

- generated code is not executed by the agent
- no `eval`
- no `exec`
- no subprocess execution of generated content

## 5. Repository operations and file writes

Any repository modification flows through controlled paths:

- all GitHub operations through `GitHubTool`
- all file writes path-validated via `path_security.validate_write_path()` before execution

This creates two separate enforcement boundaries:

- repository/network mutation boundary via `GitHubTool`
- filesystem mutation boundary via `validate_write_path()`

## 6. Correction, lint, and fix loop

After generation, ForgeAgent runs:

- a self-correction pass
- a lint gate
- a local fix loop capped at 20 attempts

Failure strategy selection is defined in `failure_handler.py` via:

- `_choose_strategy(failure_type, attempt, records)`

Decision rules:

- failure type is the primary signal
- attempt count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

## 7. CI execution and output handling

ForgeAgent executes CI as part of the PR flow.

CI output is treated as untrusted input and is bounded before use:

- CI log output truncated at 8k chars
- truncation policy is 70% head / 30% tail
- no action required — automatic

Polling/network efficiency controls include:

- ETag caching on all polling endpoints

Rate-limit handling rules include:

- `403 primary` → exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429 secondary` → respect `Retry-After` header

## 8. Operator gating and merge boundary

Before merge, ForgeAgent blocks on operator approval.

Gate messages are represented as:

- `gate_card { gate_type, options[], description }`

This gate is mandatory:

- gates wait indefinitely for operator input
- no auto-approve ever

Build progress is streamed using:

- `build_card { card_type, stage, content, progress }`

## 9. Persistence and crash recovery

ForgeAgent persists progress and learning in two different forms.

### Per-PR checkpoints
- prevent re-running completed work after a crash

### Persistent build memory
- file: `workspace/{engineer_id}/build_memory.json`
- written after every successful PR via `build_memory.record_pr()`
- survives fresh installs and thread state wipes
- must not be deleted on clean runs

### Persistent build rules
- file: `Mac-Docs/build_rules.md`
- loaded automatically by `DocumentStore`
- written after each build run when 3+ recurring failure patterns are found
- must not be deleted on clean runs unless switching to a completely new codebase

## Key Invariants

The following are subsystem-level architectural invariants.

### Security and trust
- fail closed on auth, crypto, and identity errors
- never degrade silently on those classes of failure
- no silent failure paths; every error must surface with context
- secrets never appear in logs, error messages, or generated code
- all external input is untrusted and validated

### Prompt and model safety
- context from external documents goes in the USER prompt
- external document context never goes in the SYSTEM prompt
- `SECURITY_REFUSAL` output is never bypassed by rephrasing; stop, gate, and log

### Execution safety
- generated code is never executed by the agent
- no `eval`
- no `exec`
- no subprocess execution of generated content

### Human control
- gates wait indefinitely for operator input
- no auto-approve ever

### Filesystem and repository safety
- all file writes are path-validated via `path_security.validate_write_path()` before execution
- all GitHub operations go through `GitHubTool`

### Protocol safety
- XPC unknown message types are discarded and logged
- unknown message types are never raised as exceptions

### Recovery and persistence
- per-PR stage checkpoints prevent duplicate work after crashes
- build memory is persistent and never automatically cleared
- build rules are persistent and never automatically cleared except when switching to a completely new codebase

## Failure Modes

### Scope confidence below threshold
Condition:
- `_stage_scope` receives confidence below `85`

Behavior:
- present `coverage_gaps`
- gate with options to proceed, answer, or cancel
- allow one-shot re-scope on operator-provided gap answers
- do not enter an unbounded clarification loop

### Auth, crypto, or identity error
Condition:
- authentication, cryptographic, or identity validation failure

Behavior:
- fail closed
- do not silently degrade
- surface the error with context

### Unknown XPC message type
Condition:
- inbound XPC message type is not recognized

Behavior:
- discard message
- log occurrence
- do not raise as an exception

### File write path validation failure
Condition:
- `path_security.validate_write_path()` rejects a write target

Behavior:
- block the write
- treat as an enforced safety boundary
- surface failure rather than bypassing

### GitHub API/rate-limit failures
Condition:
- GitHub primary or secondary rate limiting / service refusal

Behavior:
- `403 primary` uses exponential backoff: `2s, 4s, 8s, 16s, 32s, 64s`
- `429 secondary` respects `Retry-After`
- polling uses ETag caching

### Local correction loop exhaustion
Condition:
- fix loop reaches max local attempts

Behavior:
- never retry indefinitely
- cap at 20 local attempts
- then move on

### Failure-specific correction routing
Condition:
- failure classification in `failure_handler.py`

Behavior:
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- at `attempt >= 8`, escalate to `nuclear` every 3rd attempt

### Security refusal from model layer
Condition:
- model returns `SECURITY_REFUSAL`

Behavior:
- stop
- gate
- log
- do not bypass by rephrasing

### Oversized or noisy context/log data
Condition:
- context or CI output exceeds configured bounds

Behavior:
- `ContextManager` trims at 30k tokens while preserving the spec-anchor first turn and last 6 messages
- CI logs truncate to 8k chars using 70% head / 30% tail

### Crash during PR processing
Condition:
- subsystem interruption after partial PR completion

Behavior:
- resume from per-PR stage checkpoints
- do not re-run completed work

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

### Persistent data/artifact dependencies
- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

### Platform/protocol dependencies
- XPC line-delimited JSON transport
- nonce-authenticated messaging
- BuildStreamView as the consumer for streamed `build_card`
- operator gate handling for `gate_card`

### External service dependencies
- two LLM providers in parallel
- Claude arbitration
- GitHub via `GitHubTool`

### Document/context dependencies
- `DocumentStore`
- primary generation context documents
- specific document loading such as `PRODUCT_CONTEXT.md`
- automatic loading of `build_rules.md`