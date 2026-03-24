# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent system.

Within the repository’s two-process architecture, Crafted is the Swift/SwiftUI process responsible for:

- UI
- auth
- Keychain interaction
- XPC integration

Crafted is the macOS-facing shell around the Python backend, which separately owns:

- consensus
- pipeline orchestration
- GitHub operations

Crafted exists to host the native application experience and platform-integrated capabilities on macOS while keeping backend build, consensus, and repository automation logic out of the Swift process.

The subsystem is identified in the repository structure as:

- `Crafted/` — Swift/SwiftUI application shell
- `CraftedTests/` — XCTest suites

This subsystem is governed by the repository-wide security model defined by TRD-11.

## Component Boundaries

### Inside the Crafted subsystem

The Crafted subsystem includes the native macOS shell concerns explicitly assigned to the Swift process:

- Swift application shell
- SwiftUI user interface
- authentication handling
- Keychain handling
- XPC-related integration

### Outside the Crafted subsystem

The following responsibilities are explicitly outside Crafted and belong to the Python backend under `src/`:

- pipeline orchestration
- scope confidence gating
- consensus and arbitration
- provider integrations
- build ledger / multi-engineer coordination
- GitHub API operations
- document retrieval, embeddings, and FAISS-backed storage
- CI workflow generation
- recovery tooling
- failure handling strategy selection

Specific backend ownership called out in repository materials includes:

- `src/build_director.py` — pipeline orchestration, confidence gate, `pr_type` routing
- `src/consensus.py` — `ConsensusEngine`
- `src/github_tools.py` — all GitHub API calls
- `src/document_store.py` — `DocumentStore`
- `src/ci_workflow.py` — CI workflow generation

### Boundary enforcement rules

Crafted must not bypass backend ownership boundaries:

- All GitHub operations must go through `GitHubTool`. Never use the GitHub API directly.
- Security-relevant behavior is governed by TRD-11 across all components.
- Path validation is mandatory before any write when handling user-supplied paths:
  - `from path_security import validate_write_path`
  - `safe_path = validate_write_path(user_supplied_path)`

These rules constrain the subsystem even when the implementation entrypoint is in Swift, because repository-level operational and security requirements apply across components.

## Data Flow

The repository defines a two-process model:

1. Crafted runs as the native macOS shell process.
2. The Python backend runs separately and owns build/automation logic.
3. Integration between the shell and backend occurs via XPC responsibilities assigned to the Swift side.

At subsystem level, the data flow is:

- User interacts with the SwiftUI interface in Crafted.
- Crafted handles native-shell concerns such as auth and Keychain access.
- Crafted communicates across the process boundary using XPC integration.
- The Python backend performs orchestration, consensus, document retrieval, GitHub operations, and CI-related automation.
- Results are surfaced back through the shell for user interaction.

A repository-wide supporting flow relevant to subsystem interaction is:

- build history is persisted in `workspace/{engineer_id}/build_memory.json`
- self-improving rules are written to `Mac-Docs/build_rules.md`
- `DocumentStore` loads `build_rules.md` automatically

These data stores are backend-owned and must be treated as external to Crafted’s core responsibility, though Crafted may participate in user flows that depend on backend outputs derived from them.

## Key Invariants

The following invariants are explicitly established by the repository documentation and constrain Crafted’s architecture:

### Architectural invariants

- The product uses a two-process architecture.
- Crafted is the Swift shell process.
- The Python backend is the execution and automation process.
- Native macOS concerns stay in Crafted; backend orchestration concerns stay in `src/`.

### Ownership invariants

- UI, auth, Keychain, and XPC belong to the Swift shell.
- Consensus, pipeline, and GitHub belong to the Python backend.
- All GitHub API calls must flow through `GitHubTool`.

### Security invariants

- TRD-11 governs all components.
- Security-relevant code changes require conformance to the TRD-11 security model.
- User-supplied write paths must be validated before any write.

### Operational invariants

- Crafted is a macOS subsystem and pairs with macOS CI routing:
  - Swift runs on `[self-hosted, macos, xcode, x64]`
  - workflow file: `crafted-ci-macos.yml`
- Tests for this subsystem live in `CraftedTests/` as XCTest suites.

### Persistence and learning invariants relevant to integration

Although backend-owned, the following repository invariants must not be violated by any subsystem workflow:

- `build_memory.json` survives fresh installs and thread state wipes.
- `build_memory.record_pr()` writes after every successful PR.
- `build_memory.json` must not be deleted on clean runs.
- `Mac-Docs/build_rules.md` is written after build runs when 3+ recurring failure patterns are found.
- `build_rules.md` must not be deleted on clean runs unless switching to a completely new codebase.

## Failure Modes

The source material does not define Crafted-specific failure taxonomy entries, but it does define repository-level failure handling and operational constraints that affect subsystem behavior at boundaries.

### Boundary misuse

- Direct GitHub API use outside `GitHubTool` violates repository architecture.
- Writing to user-supplied paths without `validate_write_path` violates path security rules.
- Moving backend logic into Crafted violates the two-process separation.

### Security non-compliance

- Any security-relevant implementation that does not conform to TRD-11 is out of spec.
- Mishandling auth or Keychain responsibilities in the shell would violate Crafted’s security-sensitive role.

### Process-integration failures

Because XPC is part of Crafted’s defined responsibility, failures at the shell/backend boundary are in-scope for the subsystem. The provided documents do not enumerate exact XPC failure classes, but architectural impact is clear:

- shell cannot delegate backend-owned work correctly
- native UI cannot reflect backend state/results
- auth or Keychain mediated flows cannot complete end-to-end

### Test and CI coverage failures

- Swift/macOS changes that are not validated under the macOS workflow boundary risk escaping the intended CI path.
- Crafted regressions should be covered by `CraftedTests/` XCTest suites and routed through `crafted-ci-macos.yml`.

### Repository-level error-handling context

The repository also defines global handling patterns that may affect end-to-end flows involving Crafted:

- failure strategy is selected in `failure_handler.py` via `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary
- retries are bounded:
  - max 20 local attempts
  - attempt `>= 8` may escalate to nuclear every 3rd attempt
- API/backoff rules:
  - 403 primary uses exponential backoff from 2s to 64s
  - 429 secondary respects `Retry-After`
  - ETag caching on polling endpoints
- context/log controls:
  - `ContextManager` auto-trims at 30k tokens
  - preserves spec-anchor first turn + last 6 messages
  - CI log output truncated at 8k chars with 70% head / 30% tail

These are backend-level behaviors, but they define the surrounding operational environment in which Crafted participates.

## Dependencies

The subsystem’s explicit dependencies from the provided documents are:

### Platform and implementation dependencies

- Swift
- SwiftUI
- macOS
- XPC
- Keychain

### Repository dependencies

- Python backend process under `src/`
- TRD-11 security model
- `CraftedTests/` for XCTest validation
- macOS CI workflow:
  - `.github/workflows/crafted-ci-macos.yml`

### Cross-subsystem dependencies

Crafted depends on backend-owned services for non-shell responsibilities, including:

- pipeline orchestration via `src/build_director.py`
- consensus via `src/consensus.py`
- GitHub operations via `src/github_tools.py`
- document retrieval via `src/document_store.py`
- CI workflow generation via `src/ci_workflow.py`

### Constrained shared utilities and policies

- `path_security.validate_write_path` for safe write-path handling
- repository branch naming convention:
  - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

These dependencies and policies define Crafted as a native macOS shell subsystem, not a general-purpose execution engine or repository automation layer.