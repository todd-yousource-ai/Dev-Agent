# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent. In the repository architecture, it is the Swift/SwiftUI process in a two-process system:

- **Swift shell:** UI, auth, Keychain, and XPC
- **Python backend:** consensus, pipeline orchestration, GitHub operations, document retrieval, CI workflow generation

The Crafted subsystem is responsible for the macOS-native host concerns defined for the shell side of the product:

- presenting the application UI
- handling authentication flows
- managing secure secret storage via Keychain
- brokering communication to the backend through XPC

Crafted is not the implementation point for build orchestration, consensus, GitHub API access, or retrieval logic. Those responsibilities are explicitly located in `src/` Python components.

## Component Boundaries

### Inside the Crafted subsystem

Per repository identity and structure, Crafted contains the native shell responsibilities:

- **UI**
- **auth**
- **Keychain**
- **XPC**

This makes Crafted the boundary-facing macOS process and the integration point between the user/operator and backend services.

### Outside the Crafted subsystem

The following responsibilities are outside Crafted and must remain in the Python backend:

- **Pipeline orchestration** — `build_director.py`
  - confidence gate
  - `pr_type` routing
- **Consensus generation and arbitration** — `consensus.py`
- **Provider integrations** — `providers.py`
- **Multi-engineer coordination** — `build_ledger.py`
- **All GitHub API calls** — `github_tools.py`
- **Embeddings / FAISS / retrieval** — `document_store.py`
- **CI workflow generation** — `ci_workflow.py`
- **Build rules generation** — `build_rules.py`
- **Recovery tooling** — `recover.py`

### Explicit boundary rules

- Crafted must not directly perform GitHub API operations.  
  **All GitHub ops go through `GitHubTool`. Never use the GitHub API directly.**
- Crafted is not the source of truth for architecture or behavior.  
  **The 16 TRDs in `forge-docs/` are the source of truth.**
- Security-sensitive behavior must conform to the repository security model.  
  **TRD-11 governs all components.**

## Data Flow

### High-level process flow

1. The user interacts with the **Crafted** macOS UI.
2. Crafted handles local shell concerns:
   - auth
   - Keychain-backed secret handling
   - XPC communication
3. Crafted communicates with the **Python backend** over the process boundary.
4. The backend performs agent work, including:
   - scope evaluation and confidence gating
   - consensus generation
   - document retrieval
   - GitHub operations
   - CI workflow generation
5. Results are returned to Crafted for presentation in the native UI.

### Backend interactions relevant to Crafted

Although implemented outside this subsystem, Crafted must respect these backend behaviors at the integration boundary:

- **Scope confidence gate**
  - `SCOPE_SYSTEM` returns `confidence (0–100)` and `coverage_gaps`
  - `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
  - below threshold, the system shows gaps and offers:
    - proceed
    - answer
    - cancel
  - one-shot re-scope occurs if the operator provides gap answers

Crafted, as the UI shell, is the natural presentation surface for these operator-facing gate outcomes, but not the owner of the gating logic.

- **Document retrieval**
  - `DocumentStore` is used for generation context
  - specific documents may be loaded
  - `Mac-Docs/build_rules.md` is loaded automatically by `DocumentStore`

Crafted may surface retrieval-backed results, but retrieval and indexing remain backend responsibilities.

- **Cross-run memory**
  - `workspace/{engineer_id}/build_memory.json`
  - written after every successful PR via `build_memory.record_pr()`
  - must survive fresh installs and thread state wipes

Crafted must not treat clean runs as permission to remove this state.

## Key Invariants

### Architectural invariants

- The product remains a **two-process architecture**:
  - Crafted as Swift shell
  - backend as Python execution engine
- Crafted owns only shell-side responsibilities:
  - UI
  - auth
  - Keychain
  - XPC
- Backend logic remains in Python modules under `src/`.

### Security and write-safety invariants

- **TRD-11 governs all components** and therefore applies to Crafted.
- **Validate paths before ANY write**:
  - use `validate_write_path(user_supplied_path)`
  - path traversal must resolve to a safe default rather than writing to an unsafe path

Even if file writes are initiated from user-facing interactions, Crafted must preserve this invariant.

### API and integration invariants

- **All GitHub operations must route through `GitHubTool`.**
- Crafted must not bypass backend ownership of:
  - GitHub API calls
  - CI workflow generation
  - retrieval/indexing
  - build orchestration
  - failure strategy selection

### Persistence invariants

- `build_memory.json` is intentional cross-run learning state and:
  - is written after every successful PR
  - survives fresh installs
  - must not be deleted on clean runs
- `Mac-Docs/build_rules.md` is self-improving rule output and:
  - is written after build runs when 3+ recurring failure patterns are found
  - is loaded automatically by `DocumentStore`
  - must not be deleted on clean runs unless switching to a completely new codebase

### Context invariants

Backend context management enforces these constraints, which Crafted must tolerate at the UX boundary:

- `ContextManager` auto-trims at **30k tokens**
- preserves:
  - spec-anchor first turn
  - last 6 messages
- CI log output is truncated at **8k chars**
  - 70% head
  - 30% tail

Crafted must not assume full untruncated backend context or logs are always available.

## Failure Modes

The repository defines error-handling behaviors primarily in backend logic, but these failure modes shape what Crafted must handle and present correctly.

### Scope gate failure / insufficient confidence

- Scope confidence below threshold (`85`) blocks automatic progression.
- The operator is shown coverage gaps and offered:
  - proceed
  - answer
  - cancel
- Re-scope is one-shot if gap answers are provided.

Crafted must correctly represent this as a gated state, not as backend completion.

### Backend failure strategy escalation

From `failure_handler.py`:

- `_choose_strategy(failure_type, attempt, records)`
- failure type is primary signal
- attempt count is secondary escalation

Defined behaviors:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → converse first, then `test_driven`
- `attempt >= 8` → `nuclear` every 3rd attempt
- max **20 local attempts**, then move on
- never retry indefinitely

Crafted must not imply unbounded retries or hide terminal escalation states.

### Rate limiting and polling behavior

- `403 primary` → exponential backoff:
  - 2s
  - 4s
  - 8s
  - 16s
  - 32s
  - 64s
- `429 secondary` → respect `Retry-After`
- ETag caching on all polling endpoints

Crafted must tolerate delayed completion and polling-derived stale/not-modified states.

### Context and output truncation

- history auto-trim at 30k tokens
- CI logs truncated at 8k characters

Crafted must handle partial history and partial logs as expected behavior, not corruption.

### Regression-contract failure coverage

The repository contains a formal no-regression contract:

- `FAILURE_TAXONOMY.md` defines **7 FM root cause buckets**
- `tests/test_regression_taxonomy.py` contains **35 regression tests** covering **FM-1 through FM-7**

Crafted is bounded by this system-wide failure model even when the underlying implementations live outside the subsystem.

## Dependencies

### Internal repository dependencies

Crafted depends on the existence of the Python backend process and its owned subsystems:

- `src/agent.py`
- `src/build_director.py`
- `src/consensus.py`
- `src/providers.py`
- `src/build_ledger.py`
- `src/github_tools.py`
- `src/document_store.py`
- `src/ci_workflow.py`
- `src/build_rules.py`
- `recover.py`

### Platform and framework dependencies

From repository identity and structure, Crafted is implemented as:

- **Swift**
- **SwiftUI**
- **macOS-native application shell**
- **XPC**
- **Keychain**

### Specification dependencies

- The **16 TRDs in `forge-docs/`** are the source of truth.
- **TRD-11** is the governing security specification for all components.
- **TRD-1** is associated with the Swift/SwiftUI application shell.
- **TRD-9** covers XCTest suites in `CraftedTests/`.

### CI environment dependencies

Crafted-related CI is routed separately from non-Swift components:

- **Swift**
  - runner: `[self-hosted, macos, xcode, x64]`
  - workflow: `crafted-ci-macos.yml`

This boundary reinforces that Crafted is the macOS-native subsystem and not part of the Ubuntu-based backend CI path.