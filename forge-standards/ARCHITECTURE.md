# Architecture - Crafted

## What This Subsystem Does

Crafted is the Swift/SwiftUI application shell for the Crafted Dev Agent. In the repository architecture, it is the native macOS process responsible for shell-level concerns in a two-process system:

- UI
- authentication
- Keychain access
- XPC integration

Per repository identity, Crafted is the Swift side of a split architecture:

- **Swift shell:** UI, auth, Keychain, XPC
- **Python backend:** consensus, pipeline, GitHub

Crafted therefore provides the native macOS host environment for the agent while delegating build orchestration, consensus generation, retrieval, CI generation, and GitHub operations to the Python backend.

## Component Boundaries

Crafted is bounded by the repository’s two-process architecture and must remain within the Swift shell responsibilities defined in the source documents.

### Inside this subsystem

Crafted owns:

- native macOS application behavior
- Swift/SwiftUI UI surfaces
- authentication handling
- Keychain interactions
- XPC-related shell integration

### Outside this subsystem

The following capabilities are explicitly outside Crafted and belong to Python backend components under `src/`:

- **pipeline orchestration** via `build_director.py`
- **confidence gating and `pr_type` routing** via `build_director.py`
- **parallel generation and arbitration** via `consensus.py`
- **provider integrations** via `providers.py`
- **multi-engineer coordination** via `build_ledger.py`
- **all GitHub API calls** via `github_tools.py`
- **embeddings, FAISS, and retrieval** via `document_store.py`
- **CI workflow generation** via `ci_workflow.py`
- **recovery tooling** via `recover.py`

### Enforced interface boundary

Crafted must not bypass backend ownership boundaries. In particular:

- All GitHub operations must go through `GitHubTool`.
- Crafted is not the owner of direct GitHub API interaction.
- Retrieval and document loading are owned by `DocumentStore`.
- Scope confidence gating is owned by the build pipeline, not the Swift shell.

### Security boundary

Repository-wide security is governed by TRD-11 for all components. For write operations involving user-supplied paths, the required repository pattern is:

```python
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)
```

This establishes a cross-subsystem invariant that path traversal protection must be applied before any write. Crafted must respect this repository security model at its own boundaries when initiating or mediating file writes.

## Data Flow

Crafted participates in the front-end side of the repository’s two-process flow.

### High-level flow

1. The macOS user interacts with the Crafted UI.
2. Crafted handles shell-level concerns:
   - UI state
   - authentication
   - Keychain access
   - XPC communication
3. Work requiring agent execution is delegated across the process boundary to the Python backend.
4. The backend performs:
   - scope evaluation and confidence gating
   - generation and consensus
   - retrieval from document store
   - build orchestration
   - GitHub operations
   - CI workflow generation
5. Results are returned to the shell for presentation in the native macOS interface.

### Relevant backend flow that constrains Crafted

Although implemented outside this subsystem, Crafted must align with these backend behaviors because they shape user-visible interaction:

- `SCOPE_SYSTEM` returns:
  - confidence `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- Below threshold, the system:
  - shows gaps
  - offers proceed / answer / cancel
- If the operator provides gap answers, one-shot re-scope occurs
- There is no re-scope loop

This means Crafted’s UI must be compatible with a finite scope-gating interaction model rather than an open-ended clarification loop.

### Persistent and generated data relevant to subsystem interactions

Repository documents define durable artifacts the system depends on:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - must not be deleted on clean runs
- `Mac-Docs/build_rules.md`
  - self-improving coding rules derived from build history
  - written after each build run when 3+ recurring failure patterns are found
  - loaded by `DocumentStore` automatically
  - must not be deleted on clean runs unless switching to a completely new codebase

Crafted does not own these artifacts, but its user-facing behavior must not assume they are ephemeral.

## Key Invariants

The following invariants are stated or implied by the provided repository documents and define what Crafted must preserve at subsystem boundaries.

### Architectural invariants

- The product uses a **two-process architecture**.
- Crafted is the **Swift shell**.
- The Python backend owns consensus, pipeline, and GitHub functionality.
- Responsibilities must not collapse across that boundary.

### GitHub invariants

- **All GitHub ops go through `GitHubTool`.**
- The GitHub API must never be used directly outside that tool boundary.

### Path safety invariant

- Paths must be validated before any write.
- `validate_write_path()` is the required repository pattern for user-supplied paths.

### Scope gating invariants

- Scope confidence is numeric from `0–100`.
- The confidence threshold is `85`.
- Below threshold, the system exposes `coverage_gaps`.
- The operator gets three choices: proceed, answer, cancel.
- If answers are provided, re-scope happens once.
- There is no indefinite clarification loop.

### Build memory invariants

- `build_memory.json` is intentionally persistent across runs.
- It survives fresh installs and thread state wipes.
- It is written after every successful PR.
- It must not be deleted on clean runs.

### Build rules invariants

- `build_rules.md` is a persistent, self-improving rules artifact.
- It is generated after runs when recurring failure patterns reach the required threshold.
- It is automatically loaded by `DocumentStore`.
- It must not be deleted on clean runs unless switching to a completely new codebase.

### Error-handling invariants that affect user-visible behavior

The repository defines strict handling patterns in `failure_handler.py`:

- `failure_type` is the primary signal
- `attempt` count is secondary escalation
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → converse first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

Crafted must not present or imply an unbounded retry model that contradicts these backend rules.

### Operational invariants

- 403 primary rate limits use exponential backoff:
  - 2s → 4s → 8s → 16s → 32s → 64s
- 429 secondary rate limits must respect `Retry-After`
- ETag caching is used on all polling endpoints
- ContextManager auto-trims at 30k tokens
- It preserves:
  - spec-anchor first turn
  - last 6 messages
- CI log output is truncated at 8k chars with:
  - 70% head
  - 30% tail

These behaviors are automatic and shape what Crafted can expect from backend status and logs.

## Failure Modes

The repository documents identify failure-handling behavior and a regression contract relevant to Crafted.

### Backend-driven failures surfaced through Crafted

Crafted may need to surface outcomes resulting from backend failure classes such as:

- `assertion_error`
- `import_error`
- `runtime_error`

These are not shell-owned classifications, but they determine remediation flow and therefore user-visible state.

### Retry exhaustion

The backend never retries indefinitely and stops after:

- maximum 20 local attempts

Crafted must handle terminal failure states after bounded retry exhaustion.

### Scope gate failure

If scope confidence is below `85`, execution does not proceed directly. Instead the system presents:

- `coverage_gaps`
- proceed / answer / cancel options

A failure to achieve sufficient confidence after the one-shot re-scope still remains bounded; there is no endless clarification cycle.

### Rate limiting and polling degradation

External interactions may be delayed by:

- 403 primary rate limiting with exponential backoff
- 429 secondary rate limiting honoring `Retry-After`

Crafted should expect delayed completion rather than immediate failure in these cases.

### Context and log truncation effects

Backend safeguards can reduce available detail:

- context auto-trims at 30k tokens
- CI logs are truncated at 8k chars

Crafted must tolerate partial backend context/log payloads as normal operating behavior, not corruption.

### Regression-contract context

The repository includes:

- `FAILURE_TAXONOMY.md` — 7 FM root cause buckets
- `tests/test_regression_taxonomy.py` — 35 regression tests for FM-1 through FM-7

This indicates a no-regression contract around failure categorization and handling that Crafted must not contradict at the subsystem boundary.

## Dependencies

Crafted depends on repository-wide architectural and behavioral contracts rather than owning the implementation of backend systems.

### Internal repository dependencies

- **TRD-1**
  - Defines Crafted as the Swift/SwiftUI application shell.
- **TRD-9**
  - Defines XCTest coverage location in `CraftedTests/`.
- **TRD-11**
  - Governs security for all components and must be read before touching security-relevant code.

### Backend subsystem dependencies

Crafted depends on the existence and contracts of these backend modules:

- `src/build_director.py`
- `src/consensus.py`
- `src/providers.py`
- `src/build_ledger.py`
- `src/github_tools.py`
- `src/document_store.py`
- `src/ci_workflow.py`

### Test dependency boundary

- Swift-side tests live in `CraftedTests/`
- Python-side behavior is validated in `tests/`

### CI dependency context

Repository CI routing separates subsystem validation by language:

- **Swift** → `crafted-ci-macos.yml` on `[self-hosted, macos, xcode, x64]`
- **Python, Go, TypeScript, Rust** → `crafted-ci.yml` on `ubuntu-latest`

This means Crafted’s verification path is the macOS CI workflow, distinct from the backend’s Ubuntu-oriented workflow.