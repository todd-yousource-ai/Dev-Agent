# Architecture - FullPlatform

## What This Subsystem Does

FullPlatform is the end-to-end build orchestration subsystem for Forge’s native macOS AI coding agent. It owns the lifecycle that starts from a plain-language build intent and proceeds through scoped planning, pull-request decomposition, code generation, validation, CI execution, operator gating, and merge readiness.

At a high level, this subsystem:

- Accepts a build intent and establishes repository/build context
- Retrieves supporting documentation and persistent build knowledge
- Runs scope analysis and enforces a confidence gate before implementation
- Decomposes work into an ordered sequence of PRs with per-PR stage checkpoints
- Orchestrates parallel LLM generation across providers, with arbitration
- Applies self-correction, linting, and iterative repair loops
- Executes CI and surfaces results to the operator
- Blocks on explicit operator decisions at required gates
- Persists learning artifacts across runs via build memory and build rules

This subsystem is the control plane for build execution. It coordinates other services but does not relax repository, security, or operator-control invariants on behalf of any dependency.

## Component Boundaries

FullPlatform includes orchestration logic and policy enforcement for the build pipeline. It is responsible for sequencing, gating, state persistence, and validated interactions with external systems.

Included responsibilities:

- Build pipeline orchestration in `src/build_director.py`
  - PR sequencing
  - stage routing
  - confidence gating
  - checkpointed progress across crashes/restarts
- Multi-model generation consensus in `src/consensus.py`
  - parallel provider usage
  - arbitration behavior
  - generation system prompt selection
- GitHub interaction mediation through `src/github_tools.py`
  - all GitHub operations must flow through `GitHubTool`
  - webhook/event integration via `WebhookReceiver`
- Persistent build learning/state via `src/build_ledger.py` and workspace artifacts
  - per-PR checkpoints
  - build memory persistence
  - build rules derivation/use
- Operator-facing gate/card emission over the platform protocol
  - `build_card`
  - `gate_card`
  - progress/status signaling

Explicitly out of scope:

- Direct execution of generated code by the agent
- Direct raw GitHub API access outside `GitHubTool`
- Trusting external documents, PR comments, or CI output without validation
- Automatic approval or merge decisions without operator input
- Automatic deletion/reset of persistent learning artifacts
- Treating external document context as privileged system instruction

Boundary rules:

- External document context belongs in the user prompt only, never the system prompt
- File mutations are not performed unless path-validated with `path_security.validate_write_path()`
- Unknown XPC message types are dropped and logged, not escalated as runtime exceptions

## Data Flow

1. **Session establishment**
   - The platform receives a `ready` message over XPC:
     - `agent_version`
     - `min_swift_version`
     - `capabilities[]`
     - `doc_store_status`
   - Transport uses line-delimited JSON with nonce authentication and a 16 MB maximum message size.

2. **Credentialed subsystem initialization**
   - Credentials are received via the protocol payload:
     - `anthropic_api_key`
     - `openai_api_key`
     - `github_token`
     - `engineer_id`
   - Secrets are used for runtime access only and must never be logged, echoed, or written into generated artifacts.

3. **Context acquisition**
   - The subsystem loads:
     - repository/build intent
     - document-store context
     - optional targeted documents such as product/context specs
     - persistent `build_memory.json`
     - persistent `build_rules.md`
   - Document ingestion status may be surfaced through `doc_status` events.
   - External document content is treated as untrusted input and validated before use.

4. **Scope analysis and confidence gate**
   - Scope evaluation uses the scope system to produce:
     - `confidence` in the range 0–100
     - `coverage_gaps`
   - `_stage_scope` enforces `_CONFIDENCE_THRESHOLD = 85`.
   - If below threshold, the operator is shown gaps and offered:
     - proceed
     - answer
     - cancel
   - If the operator supplies answers, one re-scope pass is allowed; there is no open-ended re-scope loop.

5. **PR decomposition and checkpointing**
   - Work is decomposed into an ordered PR plan.
   - Per-PR stage checkpoints are persisted so completed work is not re-run after a crash.

6. **Generation and arbitration**
   - FullPlatform invokes the consensus engine in `src/consensus.py`.
   - Two LLM providers generate in parallel.
   - Claude arbitrates according to the configured consensus flow.
   - Prompt construction preserves the boundary that external document context is user-level context, not system-level instruction.

7. **Validation and repair**
   - Generated changes proceed through:
     - self-correction pass
     - lint gate
     - iterative local repair loop
   - Repair loop maximum is 20 local attempts.
   - Failure strategy selection is driven by `failure_handler.py:_choose_strategy(failure_type, attempt, records)`:
     - `assertion_error` → immediate `test_driven`
     - `import_error` / `runtime_error` → `converse` first, then `test_driven`
     - `attempt >= 8` → `nuclear` every 3rd attempt
   - Retries are bounded; the subsystem must not retry indefinitely.

8. **CI execution and result shaping**
   - CI runs after local validation stages.
   - CI output is untrusted input.
   - Log output presented to the model/operator is truncated to 8k chars with a 70% head / 30% tail split.
   - Polling endpoints use ETag caching where applicable.

9. **GitHub operations**
   - Any PR, branch, status, comment, or merge-related action is performed only through `GitHubTool`.
   - No direct GitHub API calls are permitted from orchestration code.

10. **Operator gating**
    - When human approval or intervention is required, FullPlatform emits a `gate_card`:
      - `gate_type`
      - `options[]`
      - `description`
    - Gates block indefinitely until the operator responds.
    - There is no auto-approve path.

11. **Learning persistence**
    - After every successful PR, `build_memory.record_pr()` updates:
      - `workspace/{engineer_id}/build_memory.json`
    - After a build run, if 3 or more recurring failure patterns are found, rules may be written to:
      - `Mac-Docs/build_rules.md`
    - These artifacts persist across runs and are not auto-cleared.

## Key Invariants

The subsystem enforces the following platform invariants:

- **Fail closed on auth, crypto, and identity errors**
  - No silent degradation or fallback behavior is allowed in these classes of failure.

- **No silent failure paths**
  - Every error must surface with actionable context.

- **Secrets never appear in logs, error messages, or generated code**
  - Applies to credentials, tokens, API keys, and equivalent sensitive material.

- **All external input is untrusted**
  - Includes documents, PR comments, webhook payloads, and CI output.
  - Such input must be validated before use.

- **Generated code is never executed by the agent**
  - No `eval`
  - No `exec`
  - No subprocess execution of generated content

- **Operator gates are mandatory and indefinite**
  - Gates wait indefinitely for operator input.
  - No auto-approve behavior exists.

- **All file writes are path-validated**
  - `path_security.validate_write_path()` must be called before any write executes.

- **External document context is never elevated to system instruction**
  - It must appear only in the user prompt.

- **SECURITY_REFUSAL is terminal for the current path**
  - It is not bypassed by rephrasing.
  - The subsystem must stop, gate, and log.

- **Unknown XPC message types are non-fatal**
  - They are discarded and logged, never raised as exceptions.

- **Per-PR stage checkpoints are authoritative**
  - Completed work is not repeated after crashes.

- **Build memory and build rules are persistent**
  - They are learning systems and are never cleared automatically.

Additional operational invariants:

- Scope confidence gate threshold is 85
- Re-scope after operator clarification is one-shot only
- ContextManager trims automatically at 30k tokens while preserving:
  - the spec-anchor first turn
  - the last 6 messages
- Retry/backoff behavior is bounded and policy-driven:
  - 403 primary: exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
  - 429 secondary: respect `Retry-After`

## Failure Modes

### Scope uncertainty
- **Condition:** scope confidence < 85
- **Behavior:** build does not proceed automatically
- **Handling:** present coverage gaps and gate for proceed/answer/cancel
- **Constraint:** only one re-scope pass after operator answers

### Auth / crypto / identity failure
- **Condition:** credential failure, nonce/auth mismatch, identity ambiguity, cryptographic validation failure
- **Behavior:** fail closed
- **Handling:** stop affected flow, surface contextual error, do not degrade silently

### XPC protocol anomalies
- **Condition:** malformed line-delimited JSON, oversized payload, unknown message type
- **Behavior:**
  - malformed/invalid authenticated payloads surface as protocol errors
  - unknown message types are discarded and logged
- **Handling:** preserve subsystem availability where safe; do not convert unknown message types into exceptions

### Invalid or unsafe file writes
- **Condition:** target path fails `path_security.validate_write_path()`
- **Behavior:** write is blocked
- **Handling:** surface validation failure; do not attempt alternate unchecked write paths

### GitHub operation failure
- **Condition:** API/network/permission issues during GitHub actions
- **Behavior:** operation fails through `GitHubTool`
- **Handling:**
  - use defined retry/backoff where applicable
  - never bypass `GitHubTool`
  - never switch to direct API usage

### LLM generation or arbitration failure
- **Condition:** one or more providers fail, arbitration fails, or generation yields unusable output
- **Behavior:** error surfaces with context; pipeline enters correction or failure handling path
- **Handling:** follow bounded retry/repair strategy; do not silently accept partial or low-confidence output

### Validation/test/runtime failures
- **Condition:** lint, tests, import, runtime, or assertion failures
- **Behavior:** route through failure strategy selector
- **Handling:**
  - assertion failures → test-driven repair immediately
  - import/runtime failures → converse, then test-driven
  - max 20 local attempts
  - escalation to nuclear strategy every 3rd attempt after attempt 8

### CI failure or noisy CI output
- **Condition:** CI reports failure or emits large logs
- **Behavior:** CI output is treated as untrusted; output is truncated before downstream use
- **Handling:** surface meaningful summary, preserve bounded context size, continue gating/repair flow as appropriate

### Crash or restart during build
- **Condition:** process interruption mid-PR or mid-stage
- **Behavior:** resume from per-PR stage checkpoints
- **Handling:** completed stages are not re-run

### SECURITY_REFUSAL from model/policy layer
- **Condition:** refusal triggered by security policy
- **Behavior:** current path terminates
- **Handling:** stop, gate, and log; no bypass via rephrasing

## Dependencies

Core code dependencies referenced by this subsystem:

- `src/build_director.py`
  - primary build orchestration
  - confidence gate
  - PR-type routing

- `src/consensus.py`
  - `ConsensusEngine`
  - generation system prompt definitions
  - multi-provider arbitration flow

- `src/github_tools.py`
  - `GitHubTool`
  - `WebhookReceiver`

- `src/build_ledger.py`
  - persistent progress/checkpoint tracking
  - build history support

Supporting platform dependencies:

- **DocumentStore**
  - provides repository/product/build context
  - automatically loads `Mac-Docs/build_rules.md`
  - emits document ingestion/status metadata

- **Path security utilities**
  - `path_security.validate_write_path()`
  - mandatory precondition for every file write

- **Failure handling subsystem**
  - `failure_handler.py:_choose_strategy(failure_type, attempt, records)`

- **Context management**
  - automatic trim behavior at 30k tokens
  - preservation of spec-anchor first turn and last 6 messages

- **XPC transport layer**
  - line-delimited JSON
  - nonce-authenticated messages
  - max 16 MB per message

- **LLM providers**
  - Anthropic
  - OpenAI
  - used in parallel generation flow with arbitration

- **GitHub**
  - accessed only via `GitHubTool`

Persistent data dependencies:

- `workspace/{engineer_id}/build_memory.json`
  - cross-run learning memory
  - updated after every successful PR

- `Mac-Docs/build_rules.md`
  - persistent self-improving coding rules
  - updated when recurring failure patterns justify rule synthesis

Dependency constraints:

- FullPlatform may orchestrate these dependencies, but must not weaken their safety contracts.
- No dependency may be used to bypass operator gating, path validation, secret handling, or failure visibility requirements.