# Architecture - Crafted

## What This Subsystem Does

`Crafted` is the Swift/SwiftUI application shell for the Crafted Dev Agent. In the repository architecture, it is the native macOS process responsible for shell-level concerns, while the Python backend implements consensus, pipeline orchestration, retrieval, and GitHub automation.

Per repository identity, the system is explicitly two-process:

- **Swift shell (`Crafted/`)**: UI, auth, Keychain, XPC
- **Python backend (`src/`)**: consensus, pipeline, GitHub

Within that split, the `Crafted` subsystem provides the native macOS host layer for:

- user-facing application shell behavior
- authentication handling
- Keychain-backed secret handling
- XPC-based process/service communication with the backend side

`Crafted` is therefore the boundary between macOS-native capabilities and backend agent execution.

## Component Boundaries

### Inside this subsystem

The `Crafted` subsystem includes the Swift/SwiftUI application shell located at:

- `Crafted/`

Its owned concerns are limited to the responsibilities named in the repository specification:

- **UI**
- **auth**
- **Keychain**
- **XPC**

### Outside this subsystem

The following concerns are explicitly not owned by `Crafted` and belong to the Python backend under `src/`:

- pipeline orchestration (`build_director.py`)
- consensus generation and arbitration (`consensus.py`)
- provider integrations (`providers.py`)
- multi-engineer coordination (`build_ledger.py`)
- GitHub API operations (`github_tools.py`)
- document retrieval and embeddings (`document_store.py`)
- CI workflow generation (`ci_workflow.py`)
- build rules generation and self-improving rules (`build_rules.py`)
- recovery tooling (`recover.py`)

### Boundary rules

`Crafted` must not absorb backend responsibilities. In particular:

- GitHub operations are owned by `GitHubTool`; direct GitHub API use is outside this subsystem.
- retrieval/document-store logic is outside this subsystem
- consensus and scope-gating logic are outside this subsystem
- build memory and build rules persistence are outside this subsystem
- CI workflow generation is outside this subsystem

The subsystem’s role is host/process/platform integration, not agent reasoning or repository automation.

## Data Flow

Based on the repository architecture, the high-level data flow through `Crafted` is:

1. **User interacts with the native macOS UI**
   - SwiftUI/UI entrypoints live in the shell process.

2. **Authentication and secrets are handled in the shell**
   - auth flows are managed in the Swift process
   - Keychain is the credential storage boundary for shell-managed secrets

3. **Shell communicates with backend over XPC**
   - XPC is the inter-process mechanism connecting the Swift shell and Python backend

4. **Backend performs agent work**
   - consensus
   - pipeline orchestration
   - document retrieval
   - GitHub operations
   - CI/workflow generation

5. **Results/status return to the shell**
   - the shell presents backend state/results through the UI

This makes `Crafted` the ingress/egress layer for operator interaction and secure macOS integration, with the backend acting as the execution engine.

## Key Invariants

The following invariants are derived from the repository-level specification and must hold for this subsystem.

### 1. Two-process architecture is preserved

The repository architecture is explicitly defined as:

- Swift shell
- Python backend

`Crafted` must remain the shell side of that split and must not collapse backend logic into the macOS app process.

### 2. `Crafted` owns only shell concerns

The subsystem enforces a narrow responsibility set:

- UI
- auth
- Keychain
- XPC

These are the authoritative shell responsibilities identified in the repository identity. Any new logic added to `Crafted` must fit within those areas.

### 3. Security-sensitive behavior must conform to TRD-11

The repository security model states:

- **TRD-11 governs all components**
- it must be read before touching security-relevant code

Because `Crafted` owns auth, Keychain, and XPC, it is inherently security-relevant. Changes to credential handling, IPC, or user-authenticated operations must comply with TRD-11.

### 4. Secrets remain within shell-owned secure handling paths

Since Keychain is explicitly a shell responsibility, secure secret handling is a shell-side invariant. Credentials should not be treated as ordinary backend data when shell-native secure storage is available and required by the architecture.

### 5. Inter-process communication is an explicit contract boundary

XPC is a named shell responsibility. Communication between `Crafted` and backend must occur through that process boundary rather than by implicitly merging responsibilities across subsystems.

### 6. Source-of-truth discipline applies

The repository specification states that the 16 TRDs in `forge-docs/` are the source of truth and code must match them. `Crafted` must therefore implement only behavior supported by those TRDs and not invent alternate architecture or ownership boundaries.

## Failure Modes

Only failure modes directly supported by the provided source material are listed here.

### Security regression in shell-owned features

Because `Crafted` owns auth, Keychain, and XPC, incorrect changes in this subsystem can create security-relevant regressions. Repository guidance explicitly marks security behavior as governed by TRD-11.

### Boundary leakage from backend into shell

A common architectural failure would be placing backend responsibilities into `Crafted`, such as:

- direct GitHub API logic
- consensus logic
- retrieval/document store logic
- pipeline orchestration

This violates the two-process split and weakens subsystem separation.

### IPC contract failure across the two-process architecture

Since XPC is the declared shell/backend connection mechanism, failures in that communication path can break execution flow between UI/auth surfaces and backend agent operations.

### Credential handling failure

Because Keychain is an explicit shell responsibility, failure to use or preserve shell-side secure secret handling would violate the architecture and create security risk.

### Spec drift

The repository requires code to match the TRDs. Any `Crafted` implementation that diverges from the documented shell responsibilities or the overall two-process design is an architecture failure.

## Dependencies

The `Crafted` subsystem depends on the following architectural elements identified in the provided documents.

### Platform/runtime dependencies

- **macOS**
- **Swift**
- **SwiftUI**
- **XPC**
- **Keychain**

These are implied directly by the subsystem description: native macOS shell, Swift/SwiftUI, Keychain, and XPC.

### Repository-level dependency

- **Python backend in `src/`**

`Crafted` depends on the backend process for:

- consensus
- pipeline execution
- GitHub operations
- document retrieval
- CI/workflow support

### Specification dependency

- **TRDs in `forge-docs/`**
- **TRD-11** for security-relevant behavior
- **TRD-1** as the application shell reference, per repository structure note: `Crafted/ ← Swift/SwiftUI application shell (TRD-1)`

### Testing dependency

- **`CraftedTests/`** as the XCTest suite for this application shell, noted in repository structure as:
  - `CraftedTests/ ← XCTest suites (TRD-9)`

This positions the subsystem within the repository’s Swift-side validation surface.