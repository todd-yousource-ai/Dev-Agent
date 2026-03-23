# Architecture - Crafted

## What This Subsystem Does

Crafted is the Swift/SwiftUI application shell for the Crafted Dev Agent. Within the repository’s two-process architecture, this subsystem owns the native macOS-facing responsibilities and serves as the frontend shell around the Python backend.

Per repository identity, Crafted is responsible for:

- UI
- auth
- Keychain integration
- XPC integration

This places Crafted on the shell side of the system boundary:

- **Swift shell:** UI, auth, Keychain, XPC
- **Python backend:** consensus, pipeline, GitHub

Crafted is the native macOS subsystem corresponding to `Crafted/` and is covered by macOS-specific CI via `crafted-ci-macos.yml`.

## Component Boundaries

### Inside the Crafted subsystem

Crafted includes the native shell concerns explicitly assigned to the Swift process:

- **User interface**
  - Native macOS UI implemented in Swift/SwiftUI
- **Authentication**
  - Local shell-side auth handling
- **Keychain**
  - Secure credential storage and retrieval through macOS Keychain integration
- **XPC**
  - Interprocess communication between the Swift shell and the backend-side functionality

### Outside the Crafted subsystem

The following are explicitly outside Crafted and belong to the Python backend or repository infrastructure:

- **Consensus generation and arbitration**
  - `src/consensus.py`
- **Pipeline orchestration**
  - `src/build_director.py`
- **GitHub operations**
  - `src/github_tools.py`
  - All GitHub API calls must go through `GitHubTool`
- **Document retrieval and embeddings**
  - `src/document_store.py`
- **Build coordination**
  - `src/build_ledger.py`
- **CI workflow generation**
  - `src/ci_workflow.py`
- **Recovery tooling**
  - `recover.py`
- **Backend tests**
  - `tests/`

### Boundary rules

- Crafted must not assume ownership of backend pipeline, consensus, or GitHub API behavior.
- Crafted is a shell process, not the source of truth for repository specification; the 16 TRDs in `forge-docs/` are the source of truth.
- Security-relevant behavior across all components is governed by **TRD-11**.
- Swift-specific validation belongs to the macOS workflow `crafted-ci-macos.yml`, not the Ubuntu workflow.

## Data Flow

### High-level flow

1. The user interacts with the native macOS UI in Crafted.
2. Crafted performs shell-side responsibilities:
   - UI event handling
   - auth flows
   - Keychain access
3. Crafted communicates across the process boundary via XPC.
4. The Python backend executes agent logic such as:
   - consensus
   - pipeline orchestration
   - GitHub operations
   - document retrieval
5. Results are returned to the shell for presentation in the macOS UI.

### Security-sensitive flow

For any shell-side operation involving credentials or protected local state:

1. Crafted receives user intent through the UI.
2. Crafted uses its auth and Keychain responsibilities to obtain or store necessary credentials.
3. Crafted passes only the required information across the XPC boundary.
4. Backend operations proceed in the Python process according to repository policy and TRD-11.

### CI flow relevant to Crafted

1. Swift changes under the Crafted subsystem are validated on macOS runners.
2. The workflow file used is:
   - `crafted-ci-macos.yml`
3. The configured runner class is:
   - `[self-hosted, macos, xcode, x64]`

## Key Invariants

- **Two-process architecture is preserved**
  - Crafted remains the Swift shell; backend logic remains in Python.
- **Crafted owns only shell concerns**
  - UI, auth, Keychain, and XPC are in scope.
- **GitHub API access does not originate from Crafted**
  - All GitHub operations must go through `GitHubTool`.
- **Specification authority is external to implementation**
  - The 16 TRDs in `forge-docs/` are the source of truth.
- **Security model is governed by TRD-11**
  - Any security-relevant change affecting Crafted must conform to TRD-11.
- **Swift validation runs on macOS CI**
  - Swift is routed to `crafted-ci-macos.yml`, not `crafted-ci.yml`.
- **Path validation is mandatory before any write**
  - Repository-wide rule:
    - `from path_security import validate_write_path`
    - `safe_path = validate_write_path(user_supplied_path)`

## Failure Modes

The provided source material does not define Crafted-specific internal failure taxonomies, but it does establish repository-level operational and integration risks relevant to this subsystem.

### Process-boundary failures

- **XPC communication failure**
  - Crafted may be unable to hand off work to or receive results from the backend process.
  - Impact: UI can no longer drive backend capabilities.

### Authentication or credential failures

- **Auth failure**
  - Shell-side authentication does not complete successfully.
  - Impact: user access to protected operations is blocked.
- **Keychain access failure**
  - Crafted cannot read or persist required secure data.
  - Impact: credential-dependent operations fail or require re-entry.

### Security and write-safety failures

- **Unsafe path usage**
  - Any write path not validated with `validate_write_path` violates repository write-safety rules.
  - Impact: traversal risk or incorrect write target selection.

### CI and validation failures

- **Incorrect CI routing**
  - Swift changes validated on the wrong workflow would violate repository CI routing.
  - Required workflow for Crafted:
    - `crafted-ci-macos.yml`

### Cross-subsystem contract failures

- **Boundary violation**
  - Crafted attempts to implement or directly call backend-owned concerns such as GitHub API operations, consensus, or pipeline orchestration.
  - Impact: architectural drift from the defined two-process model.

## Dependencies

### Direct architectural dependencies

- **Swift / SwiftUI**
  - Implementation technology for the native macOS shell
- **macOS Keychain**
  - Secure credential storage and retrieval
- **XPC**
  - Interprocess communication with the backend process

### Repository and process dependencies

- **Python backend**
  - Crafted depends on the backend for:
    - consensus
    - pipeline orchestration
    - GitHub operations
    - document retrieval
- **TRD documentation in `forge-docs/`**
  - Source of truth for subsystem behavior
- **TRD-11**
  - Governs security-relevant behavior across components
- **macOS CI workflow**
  - `crafted-ci-macos.yml`
- **Crafted test target**
  - `CraftedTests/`

### Non-dependencies by boundary

These are repository components but are not owned by Crafted:

- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `src/document_store.py`
- `src/build_ledger.py`
- `src/ci_workflow.py`
- `recover.py`
- `tests/`