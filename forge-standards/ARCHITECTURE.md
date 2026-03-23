# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent.

Per repository identity, the product uses a **two-process architecture**:

- **Swift shell**: UI, auth, Keychain, and XPC
- **Python backend**: consensus, pipeline, and GitHub operations

Within that architecture, the **Crafted subsystem** is the Swift/SwiftUI shell, located at:

- `Crafted/` — Swift/SwiftUI application shell (TRD-1)

This subsystem is responsible for the macOS-native host concerns explicitly assigned to the shell:

- presenting the user interface
- handling authentication
- integrating with Keychain
- brokering cross-process communication via XPC

It is not the implementation site for backend orchestration, consensus generation, GitHub API access, document retrieval, CI generation, or recovery logic.

## Component Boundaries

### Inside the Crafted subsystem

The Crafted subsystem includes the native macOS shell responsibilities named in repository identity:

- **UI**
- **auth**
- **Keychain**
- **XPC**

It is the macOS-facing process in the two-process system.

### Outside the Crafted subsystem

The following concerns are explicitly outside this subsystem and belong to the Python backend under `src/`:

- **pipeline orchestration**
  - `build_director.py`
- **consensus generation and arbitration**
  - `consensus.py`
- **provider integrations**
  - `providers.py`
- **multi-engineer coordination**
  - `build_ledger.py`
- **all GitHub API calls**
  - `github_tools.py`
- **document embeddings / FAISS / retrieval**
  - `document_store.py`
- **CI workflow generation**
  - `ci_workflow.py`
- **recovery tooling**
  - `recover.py`

Boundary rule from AGENTS:

- **ALL GitHub ops go through `GitHubTool`. Never use the GitHub API directly.**

Therefore, Crafted must not bypass backend ownership of GitHub operations.

### Test boundary

- `CraftedTests/` contains XCTest suites for the Swift shell (referenced as TRD-9)
- Python behavior is validated separately in `tests/`

## Data Flow

The documented architecture defines a strict shell/backend separation.

### Primary flow

1. **User interacts with Crafted UI**
2. Crafted performs shell-owned concerns:
   - auth handling
   - Keychain access
   - XPC communication
3. Crafted communicates across the process boundary to the **Python backend**
4. Backend-owned systems execute requested work:
   - scope and pipeline orchestration
   - consensus/arbitration
   - document retrieval
   - GitHub operations
   - CI workflow generation
5. Results are returned to the Swift shell for presentation in the macOS UI

### Supporting flow constraints

Because the backend is the owner of build and repository operations, several data paths are implicitly constrained:

- repository and CI interactions terminate in backend modules, not in Crafted
- document retrieval is performed by `DocumentStore`
- branching, PR behavior, and GitHub calls are mediated by backend tooling
- persistent build learning artifacts are backend-managed:
  - `workspace/{engineer_id}/build_memory.json`
  - `Mac-Docs/build_rules.md`

Crafted may surface state and results, but the TRD-derived repository instructions do not assign ownership of these artifacts to the Swift shell.

## Key Invariants

The following subsystem invariants are directly supported by the provided repository instructions.

### 1. Two-process separation is architectural, not optional

Crafted is the **Swift shell** in a two-process system. Backend responsibilities remain in Python.

Enforced split:

- Swift shell: UI, auth, Keychain, XPC
- Python backend: consensus, pipeline, GitHub

### 2. Crafted does not own GitHub API access

All GitHub operations must route through backend ownership:

- **ALL GitHub ops go through `GitHubTool`**
- **Never use the GitHub API directly**

This prevents the shell from becoming an alternate control plane for repository mutation.

### 3. Security-sensitive behavior is governed repository-wide by TRD-11

Repository identity states:

- **TRD-11 governs all components**
- read it before touching security-relevant code

For Crafted, this applies especially to:

- auth
- Keychain
- XPC
- any file-write path originating from user input

### 4. Path validation is required before any write

Repository-wide rule:

```python
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
```

Although the example is shown in Python, the invariant is subsystem-relevant: user-supplied paths must be validated before writes are performed anywhere in the system.

### 5. Crafted is the native macOS shell only

This subsystem must remain focused on shell concerns and not absorb backend logic such as:

- consensus arbitration
- scope gating
- document retrieval
- build memory persistence
- CI workflow generation
- failure recovery strategies

## Failure Modes

Only failure behaviors explicitly present in the provided documents are included here.

### Cross-process / shell-to-backend boundary failures

Because Crafted’s role includes XPC and the backend owns execution logic, failures at this subsystem boundary can manifest as:

- inability to dispatch user intent from UI to backend
- inability to return backend results to UI
- degraded user experience when backend operations fail

The provided documents do not define XPC-specific retry semantics, so those must remain consistent with the broader architecture and TRDs rather than inventing shell-local policy.

### Security-related failures

Crafted touches the most security-sensitive shell concerns:

- auth
- Keychain
- XPC

Given the repository-wide requirement that TRD-11 governs all components, failures in this subsystem are security-relevant when they involve:

- improper auth handling
- insecure credential handling around Keychain
- invalid trust or message handling across XPC
- unsafe path usage before writes

### Write-path traversal risk

The repository explicitly requires path validation before any write. Failure to enforce this can lead to:

- traversal outside intended write roots
- writes to unsafe or unintended filesystem locations

### Backend dependency failures surfaced through Crafted

Crafted is not the source of backend logic, but it is the presentation surface for backend failures such as:

- GitHub operation failures
- pipeline or consensus failures
- document retrieval failures
- CI generation failures

The AGENTS content defines repository-wide error-handling patterns relevant to these downstream failures:

- failure strategy selection is based primarily on `failure_type`
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → `converse` first, then `test_driven`
- `attempt >= 8` → nuclear every 3rd attempt
- max 20 local attempts, then move on
- `403` primary rate limits use exponential backoff
- `429` secondary rate limits respect `Retry-After`
- ETag caching is used on polling endpoints

These strategies are backend-owned; Crafted should surface them rather than re-implement them.

### Context and log truncation effects

Repository-wide automatic controls can affect what Crafted receives or displays from backend interactions:

- `ContextManager` auto-trims at 30k tokens
- preserves spec-anchor first turn + last 6 messages
- CI log output truncated at 8k chars (70% head / 30% tail)

This means the shell must tolerate partial context and truncated logs as valid backend outputs.

## Dependencies

### Architectural dependencies

Crafted depends on the documented two-process contract:

- Swift shell process
- Python backend process

Its communication boundary is defined by the shell’s XPC role and the backend’s ownership of execution.

### Repository dependencies outside the subsystem

Crafted depends on backend modules for non-shell functionality, including:

- `build_director.py` — pipeline orchestration
- `consensus.py` — consensus engine
- `providers.py` — model providers
- `build_ledger.py` — multi-engineer coordination
- `github_tools.py` — GitHub operations
- `document_store.py` — retrieval and document loading
- `ci_workflow.py` — CI workflow generation
- `recover.py` — recovery tool

### Specification dependencies

The subsystem is constrained by repository source-of-truth documents:

- **16 TRDs in `forge-docs/`**
- **TRD-11** for security-relevant behavior
- `AGENTS.md` repository instructions
- TRD references called out for shell and tests:
  - `Crafted/` — Swift/SwiftUI application shell (TRD-1)
  - `CraftedTests/` — XCTest suites (TRD-9)

### Data and artifact dependencies

While not owned by Crafted, the shell may interact indirectly with backend-managed artifacts and outputs:

- `workspace/{engineer_id}/build_memory.json`
- `Mac-Docs/build_rules.md`
- `.github/workflows/crafted-ci.yml`
- `.github/workflows/crafted-ci-macos.yml`

These remain backend-generated or backend-managed artifacts, not native shell-owned state.