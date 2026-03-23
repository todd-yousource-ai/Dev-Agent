# Architecture - Crafted

## What This Subsystem Does

Crafted is the Swift/SwiftUI application shell for the Crafted Dev Agent. In the repository architecture, it is the native macOS process responsible for shell concerns, while the Python backend handles consensus, pipeline orchestration, document retrieval, and GitHub operations.

Per repository identity, the overall product is a two-process system:

- **Swift shell**: UI, auth, Keychain, XPC
- **Python backend**: consensus, pipeline, GitHub

Within that split, the Crafted subsystem provides the macOS-native boundary for:

- user-facing application UI
- authentication handling
- Keychain-backed secret handling
- XPC-based communication with the backend process

Crafted is therefore the host process and trust boundary for macOS-native capabilities, not the implementation location for build orchestration or repository mutation logic.

## Component Boundaries

### Inside the Crafted subsystem

The Crafted subsystem consists of the Swift/SwiftUI application shell located at:

- `Crafted/`

Its defined responsibilities are limited to the shell concerns named in the repository identity:

- **UI**
- **auth**
- **Keychain**
- **XPC**

### Outside the Crafted subsystem

The following responsibilities are explicitly outside Crafted and belong to the Python backend under `src/`:

- agent entry point and REPL (`agent.py`)
- pipeline orchestration and confidence gating (`build_director.py`)
- parallel generation and arbitration (`consensus.py`)
- model/provider integration (`providers.py`)
- multi-engineer coordination (`build_ledger.py`)
- all GitHub API calls (`github_tools.py`)
- document retrieval, embeddings, and FAISS-backed storage (`document_store.py`)
- CI workflow generation (`ci_workflow.py`)
- recovery tooling (`recover.py`)

### Boundary rules

Crafted must not bypass backend ownership boundaries:

- **GitHub operations** are not a Crafted concern; all GitHub operations must go through `GitHubTool`.
- **Pipeline scope gating** is not a Crafted concern; `_stage_scope` and `_CONFIDENCE_THRESHOLD = 85` belong to backend orchestration.
- **Document retrieval and build-rule loading** are not a Crafted concern; `DocumentStore` owns those behaviors.
- **Build memory persistence** is not a Crafted concern; `build_memory.json` is recorded via backend build-memory mechanisms.

Crafted may present or transport data related to these systems through UI/XPC, but it does not redefine or reimplement them.

## Data Flow

### High-level flow

1. The user interacts with the native macOS UI in Crafted.
2. Crafted handles shell-local concerns:
   - authentication flow
   - Keychain access
   - XPC transport
3. Crafted communicates with the Python backend over the process boundary.
4. The Python backend performs:
   - scope analysis and gating
   - consensus generation
   - retrieval from document storage
   - GitHub operations
   - CI workflow generation
5. Results, prompts, gaps, or status are returned to Crafted for presentation.

### Scope-gate interaction flow

The backend defines the scope confidence behavior:

- `SCOPE_SYSTEM` returns:
  - confidence `0–100`
  - `coverage_gaps`
- `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
- below threshold:
  - shows gaps
  - offers proceed / answer / cancel
- one-shot re-scope occurs if the operator provides gap answers
- no loop

Within this flow, Crafted’s role is presentation and operator interaction. The enforcement logic remains backend-owned.

### State and persistence flow

Cross-run learning artifacts are backend-managed:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
- `Mac-Docs/build_rules.md`
  - written after each build run when 3+ recurring failure patterns are found
  - loaded automatically by `DocumentStore`

Crafted may expose these outcomes indirectly through UI, but it does not own their lifecycle.

## Key Invariants

### Process architecture invariant

The repository architecture remains two-process:

- Crafted is the **Swift shell**
- `src/` is the **Python backend**

Responsibilities must not be collapsed across that boundary.

### Security invariant

All components, including Crafted, are governed by **TRD-11**. Any security-relevant behavior must conform to that governing model.

### macOS shell invariant

Crafted owns only shell-native concerns:

- UI
- auth
- Keychain
- XPC

It must not become the implementation surface for backend orchestration logic.

### GitHub access invariant

All GitHub operations go through `GitHubTool`. Crafted must not directly implement or bypass GitHub API access.

### Path safety invariant

Before any write using a user-supplied path, path validation is mandatory:

```python
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)
```

This repository-level invariant applies to all write paths and protects against traversal by returning a safe default.

### Persistence invariant

The following backend artifacts are intentional durable state and must not be deleted casually:

- `build_memory.json`
  - do not delete on clean runs
- `build_rules.md`
  - do not delete on clean runs unless switching to a completely new codebase

Crafted must not assume these artifacts are ephemeral.

### Context handling invariant

Automatic context-management behaviors are backend-owned and should be treated as authoritative when surfaced in UI:

- ContextManager auto-trims at 30k tokens
- preserves spec-anchor first turn + last 6 messages
- CI log output truncated at 8k chars
  - 70% head / 30% tail

## Failure Modes

The source documents define repository-level failure-handling behaviors that affect what Crafted may observe and present.

### Scope-confidence failure mode

If scope confidence is below threshold:

- backend returns coverage gaps
- operator is offered:
  - proceed
  - answer
  - cancel
- only a one-shot re-scope occurs after answers
- no indefinite re-scope loop

Crafted should treat this as a gated interaction state, not as an internal shell failure.

### Backend failure-strategy escalation

In `failure_handler.py`, strategy selection is driven primarily by failure type, then by attempt count:

- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → converse first, then `test_driven`
- `attempt >= 8` → nuclear every 3rd attempt
- never retry indefinitely
- max 20 local attempts, then move on

Crafted may surface these states or outcomes, but does not own escalation policy.

### API throttling and polling failure modes

Repository-level retry behavior includes:

- `403` primary:
  - exponential backoff `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary:
  - respect `Retry-After`
- ETag caching on all polling endpoints

These are backend/network behaviors outside Crafted’s implementation boundary.

### Context and log truncation effects

Crafted may receive truncated or trimmed information because the backend enforces:

- history trimming at 30k tokens
- preservation of spec-anchor first turn + last 6 messages
- CI log truncation at 8k chars

These are expected operational constraints, not UI data-corruption conditions.

## Dependencies

### Internal repository dependencies

Crafted depends on the existence of the Python backend subsystem for non-shell functionality, especially:

- `build_director.py` for pipeline orchestration and scope gating
- `consensus.py` for parallel generation and arbitration
- `document_store.py` for retrieval and automatic loading of `build_rules.md`
- `github_tools.py` for all GitHub operations
- backend recovery and failure handling mechanisms defined in `src/`

### Platform dependencies

From repository identity, Crafted is a native macOS shell and therefore depends on macOS-native facilities for:

- Swift/SwiftUI application behavior
- authentication
- Keychain integration
- XPC communication

### CI relationship

Crafted is the Swift subsystem and aligns with the Swift CI route:

| Language | Runner | Workflow file |
|----------|--------|--------------|
| Swift | `[self-hosted, macos, xcode, x64]` | `crafted-ci-macos.yml` |

This CI mapping is operationally relevant to Crafted but does not change its runtime subsystem boundary.

### Governing documents

Crafted is constrained by repository-wide governing specifications and instructions, including:

- the 16 TRDs in `forge-docs/` as source of truth
- **TRD-11** for the security model
- repository agent instructions in `AGENTS.md`

These documents define behavior Crafted must conform to; they are not optional implementation guidance.