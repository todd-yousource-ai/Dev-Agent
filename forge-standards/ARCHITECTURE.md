# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent.

Within the repository’s two-process architecture, Crafted is the Swift/SwiftUI process responsible for shell-level platform integration, while the Python backend owns consensus, pipeline orchestration, document retrieval, and GitHub operations.

From the source material, Crafted is responsible for:

- UI
- auth
- Keychain integration
- XPC integration

Crafted is explicitly part of:

- `Crafted/` — Swift/SwiftUI application shell
- governed by TRD-1
- tested by `CraftedTests/` under TRD-9

Its role is to host the native macOS experience and mediate access to platform capabilities that are not part of the Python backend.

## Component Boundaries

### Inside the Crafted subsystem

The Crafted subsystem includes the native shell concerns named in the repository identity:

- Swift application shell
- SwiftUI user interface
- authentication handling
- Keychain interactions
- XPC interactions

These are macOS-native responsibilities and define the subsystem’s scope.

### Outside the Crafted subsystem

The following responsibilities are explicitly outside Crafted and belong to the Python backend under `src/`:

- consensus generation and arbitration
- pipeline orchestration
- confidence gate handling
- PR type routing
- GitHub API operations
- document retrieval, embeddings, and FAISS-backed search
- CI workflow generation
- build memory persistence
- self-improving build rules generation
- recovery tooling
- failure taxonomy and regression enforcement

Examples of out-of-scope modules include:

- `src/build_director.py`
- `src/consensus.py`
- `src/github_tools.py`
- `src/document_store.py`
- `src/ci_workflow.py`

### External boundary rules

Crafted must respect repository-wide integration rules:

- All GitHub operations go through `GitHubTool`. Crafted must not call the GitHub API directly.
- Security-relevant behavior is governed by TRD-11 across all components.
- Any filesystem write using user-supplied paths must use `validate_write_path` before writing.

## Data Flow

The documented architecture defines a two-process flow:

1. The user interacts with the native macOS UI in Crafted.
2. Crafted handles shell-level concerns:
   - presenting UI
   - auth
   - secure credential handling through Keychain
   - interprocess communication through XPC
3. Crafted communicates with the Python backend process.
4. The Python backend performs agent behaviors such as:
   - consensus generation
   - pipeline orchestration
   - scope confidence evaluation
   - document retrieval
   - GitHub operations
5. Results are returned to Crafted for presentation in the native shell.

This establishes a strict shell/backend split:

- Crafted is the macOS-native control and presentation layer.
- The Python backend is the execution and orchestration layer.

Where persistent cross-run learning exists, it is maintained by backend-owned artifacts, not by Crafted:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`

Crafted may surface outcomes derived from these backend systems, but ownership of those files and their lifecycle is not assigned to the Crafted subsystem in the provided material.

## Key Invariants

The following invariants are directly supported by the provided documents and apply to Crafted’s architecture and interactions:

### 1. Two-process separation is architectural, not optional

The product architecture is explicitly:

- Swift shell
- Python backend

Crafted must remain the shell-side subsystem and not absorb backend responsibilities such as consensus, GitHub orchestration, or document retrieval.

### 2. Crafted owns native macOS concerns only

Crafted’s responsibilities are limited to the named shell concerns:

- UI
- auth
- Keychain
- XPC

This boundary must be preserved.

### 3. GitHub access is centralized

All GitHub operations must go through `GitHubTool`.

Therefore, Crafted must not implement or bypass direct GitHub API access.

### 4. Path validation is mandatory before writes

Before any write using a user-supplied path:

```python
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)
```

Although the example is shown in Python, the invariant is repository-wide: path traversal protection is mandatory before writes.

### 5. Security governance is centralized in TRD-11

Any Crafted behavior involving security-relevant concerns, especially auth and Keychain-adjacent interactions, is subject to TRD-11.

### 6. Specification documents are the source of truth

The repository is governed by 16 TRDs in `forge-docs/`, and code must match them. Crafted must therefore be implemented as a specification-driven shell subsystem, not by inferred or ad hoc behavior beyond the documented boundaries.

## Failure Modes

Only limited subsystem-specific failure behavior is present in the supplied material. Based strictly on that material, the relevant failure modes for Crafted are boundary and integration failures.

### 1. Boundary violation: backend logic implemented in Crafted

If Crafted begins to directly own backend responsibilities such as:

- GitHub API operations
- consensus logic
- pipeline orchestration
- document retrieval

then the subsystem violates the documented two-process architecture.

### 2. Unauthorized direct GitHub access

Any direct GitHub API use from Crafted bypasses the required `GitHubTool` boundary and violates repository rules.

### 3. Unsafe filesystem writes

Any write using a user-supplied path without `validate_write_path` creates a path traversal risk and violates the repository’s mandatory write-validation rule.

### 4. Security model drift

Because Crafted includes auth and Keychain responsibilities, implementation drift from TRD-11 is a critical failure mode for this subsystem.

### 5. XPC integration failure

Crafted owns XPC on the shell side. Failure in this boundary would prevent correct communication between the native shell and the Python backend, breaking the documented two-process model.

### 6. Test coverage regression

Crafted is tested under `CraftedTests/` and associated with TRD-9. Missing or regressed coverage in the shell subsystem creates risk that native shell, auth, Keychain, or XPC behavior diverges from specification.

## Dependencies

The Crafted subsystem depends on the following entities named in the provided materials:

### Platform and implementation dependencies

- Swift
- SwiftUI
- macOS-native shell capabilities
- Keychain
- XPC

### Repository dependencies

- Python backend process for:
  - consensus
  - pipeline
  - GitHub operations
  - document retrieval
- TRD-1 as the subsystem specification for the Swift/SwiftUI application shell
- TRD-9 for testing via `CraftedTests/`
- TRD-11 for security governance

### Integration dependencies and rules

- `GitHubTool` for any GitHub operations, indirectly via the backend
- `validate_write_path` for any user-supplied filesystem destination before write

### Non-dependencies by design

Crafted does not own or directly depend on implementing the logic in:

- `src/consensus.py`
- `src/build_director.py`
- `src/document_store.py`
- `src/ci_workflow.py`

Those are backend subsystem concerns and remain outside Crafted’s implementation boundary.