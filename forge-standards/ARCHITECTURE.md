# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent.

Within the repository’s two-process architecture, Crafted is the Swift/SwiftUI process responsible for:

- UI
- auth
- Keychain integration
- XPC integration

It is the macOS-native shell around the Python backend, which separately owns:

- consensus
- pipeline orchestration
- GitHub operations

Crafted is therefore the frontend/system-integration side of the product, not the implementation point for backend build orchestration or repository mutation logic.

## Component Boundaries

### Inside the Crafted subsystem

Per repository identity and structure, Crafted contains the Swift/SwiftUI application shell and is responsible for:

- Native macOS UI
- Authentication handling
- Keychain access and secure credential storage/use
- XPC communication with the backend process

### Outside the Crafted subsystem

The following capabilities are explicitly outside Crafted and belong to the Python backend under `src/`:

- Entry point / REPL / version handling in `src/agent.py`
- Pipeline orchestration in `src/build_director.py`
- Consensus generation and arbitration in `src/consensus.py`
- Provider integrations in `src/providers.py`
- Multi-engineer coordination in `src/build_ledger.py`
- All GitHub API calls in `src/github_tools.py`
- Embeddings / FAISS / retrieval in `src/document_store.py`
- CI workflow generation in `src/ci_workflow.py`

Crafted also does not define repository-wide security policy independently; the repository security model is governed by TRD-11 for all components.

### Boundary rules

- Crafted must operate as the Swift shell in a two-process architecture.
- Crafted must not directly assume ownership of backend responsibilities such as consensus, pipeline routing, document retrieval, or GitHub API execution.
- All GitHub operations are centralized in `GitHubTool`; direct GitHub API use is not permitted in subsystem behavior.
- Security-relevant behavior must conform to the repository-wide security model governed by TRD-11.

## Data Flow

The repository defines a two-process split. For the Crafted subsystem, the data flow is:

1. User interacts with the native macOS UI in Crafted.
2. Crafted performs shell-side responsibilities:
   - presents UI
   - handles auth
   - accesses Keychain as needed
3. Crafted communicates with the Python backend over XPC.
4. The backend performs orchestration and external-service operations, including:
   - consensus
   - pipeline decisions
   - GitHub API access
   - document retrieval
   - CI workflow generation
5. Results are returned back through the process boundary to Crafted for presentation in the macOS application shell.

### Write-path interaction constraint

Where Crafted performs any write based on user-supplied paths, path validation is mandatory before the write:

```python
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
```

This constraint is repository-wide and applies before any write operation.

## Key Invariants

The Crafted subsystem must preserve the following architectural invariants derived from repository-level specifications and agent instructions:

1. **Two-process invariant**
   - Crafted remains the Swift shell.
   - Backend logic remains in Python.

2. **Responsibility separation invariant**
   - Crafted owns UI, auth, Keychain, and XPC.
   - Backend owns consensus, pipeline, and GitHub operations.

3. **GitHub access invariant**
   - All GitHub operations go through `GitHubTool`.
   - Direct GitHub API usage is disallowed.

4. **Security-governance invariant**
   - TRD-11 governs all components, including Crafted.
   - Security-relevant changes must be aligned to that shared model.

5. **Path-safety invariant**
   - Paths must be validated before any write.
   - Traversal must resolve to a safe default rather than being written unchecked.

6. **CI/platform separation invariant**
   - Swift changes are routed to macOS CI via `crafted-ci-macos.yml`.
   - Non-Swift language families are routed to Ubuntu CI via `crafted-ci.yml`.

## Failure Modes

Only failure modes stated or implied by the provided source material are included here.

### 1. Process-boundary failure
If the XPC boundary between Crafted and the Python backend fails, Crafted cannot fulfill backend-dependent actions because orchestration and service integrations are not implemented in the Swift shell.

### 2. Authentication or credential handling failure
Because Crafted owns auth and Keychain responsibilities, failures in those areas block authenticated product behavior at the shell layer.

### 3. Security-policy violation
Any Crafted behavior that diverges from TRD-11 or bypasses required path validation constitutes an architectural failure against the repository security model.

### 4. Boundary violation
If Crafted begins directly implementing backend-owned concerns such as GitHub API calls, consensus, or pipeline routing, the subsystem violates the defined two-process architecture.

### 5. CI misrouting
Swift-related validation must run on the macOS workflow and runner class defined for Swift. Routing Swift validation to the Ubuntu workflow would violate the repository’s CI partitioning.

### 6. Unsafe write-path handling
Any write derived from user-supplied paths without `validate_write_path` is a subsystem-integrity and security failure.

## Dependencies

Crafted depends on the following repository-defined architectural elements:

### Runtime architecture dependencies

- The Python backend process in `src/`
- XPC as the inter-process communication mechanism
- Keychain for credential handling
- Repository-wide auth flow integration

### Repository policy dependencies

- `forge-docs/` TRDs as the source of truth
- TRD-11 as the governing security model
- Repository instructions in `AGENTS.md`

### Operational dependencies

- `crafted-ci-macos.yml` for Swift/macOS CI validation
- The defined self-hosted macOS runner: `[self-hosted, macos, xcode, x64]`

### Explicit non-dependencies for responsibility ownership

Crafted does not own or directly depend on itself to implement:

- `GitHubTool` behavior as a direct in-shell API client
- consensus arbitration
- build pipeline routing
- document retrieval/indexing
- CI workflow generation

Those remain backend-owned concerns across the subsystem boundary.