# Architecture - Crafted

## What This Subsystem Does

Crafted is the native macOS application shell for the Crafted Dev Agent.

Per repository identity, the product is a **two-process architecture**:

- **Swift shell**: UI, auth, Keychain, XPC
- **Python backend**: consensus, pipeline, GitHub

Within that split, the **Crafted subsystem** is the Swift/SwiftUI application shell defined as `Crafted/` and identified in repository structure as the shell described by **TRD-1**.

Its responsibilities are therefore limited to the native macOS host concerns:

- presenting the application UI
- handling authentication
- managing secure local credential storage via Keychain
- brokering cross-process communication via XPC to the backend

It does **not** own backend orchestration logic such as:

- pipeline orchestration
- scope confidence gating
- consensus generation and arbitration
- GitHub API operations
- document retrieval, embeddings, or FAISS indexing
- CI workflow generation
- build memory or build rules generation

Those capabilities are explicitly located in Python modules under `src/`.

## Component Boundaries

### Inside Crafted

The Crafted subsystem includes the macOS-native shell responsibilities:

- **UI**
- **auth**
- **Keychain**
- **XPC**

This makes Crafted the local host process and operator-facing entry point for the product.

### Outside Crafted

The following responsibilities are outside the Crafted boundary and belong to the Python backend:

- `agent.py` — entry point, REPL, version
- `build_director.py` — pipeline orchestration, confidence gate, `pr_type` routing
- `consensus.py` — `ConsensusEngine`, parallel generation and arbitration
- `providers.py` — model providers
- `build_ledger.py` — multi-engineer coordination
- `github_tools.py` — all GitHub API calls
- `document_store.py` — embeddings, FAISS, retrieval
- `ci_workflow.py` — CI workflow generation
- build-memory and self-improving rule generation
- failure strategy selection and retry handling

### Boundary Rules

Crafted must respect these repository-wide constraints where applicable:

- **Security model** is governed by **TRD-11** for all components.
- **All GitHub operations go through `GitHubTool`**. Crafted must not call the GitHub API directly.
- **Validate paths before any write** using `validate_write_path`; path traversal protection is mandatory.
- Workflow and CI concerns are generated and owned by backend tooling, not by the Crafted shell.

## Data Flow

### High-level process flow

1. The operator interacts with the **Crafted** macOS UI.
2. Crafted handles local application concerns:
   - auth
   - Keychain-backed secret handling
   - XPC communication
3. Crafted communicates with the **Python backend** over the process boundary.
4. The Python backend performs agent execution, including:
   - scope analysis and confidence gating
   - consensus generation
   - document retrieval
   - GitHub operations
   - CI workflow handling
   - failure recovery logic
5. Results are returned back across XPC to Crafted for presentation in the UI.

### Backend interaction constraints relevant to Crafted

Although implemented in Python, the following behaviors shape the contract that Crafted surfaces to the operator:

- **Scope confidence gate**
  - `SCOPE_SYSTEM` returns `confidence (0–100)` and `coverage_gaps`
  - `_stage_scope` gates at `_CONFIDENCE_THRESHOLD = 85`
  - below threshold, the operator is shown gaps and offered:
    - proceed
    - answer
    - cancel
  - one-shot re-scope occurs if the operator provides gap answers

Crafted is therefore expected to host or relay these operator choices, but the gating decision itself belongs to backend orchestration.

### Persistent and generated artifacts

Crafted is not the owner of these artifacts, but it may expose their effects through UI:

- `workspace/{engineer_id}/build_memory.json`
  - survives fresh installs and thread state wipes
  - written after every successful PR via `build_memory.record_pr()`
  - intentionally retained across runs
- `Mac-Docs/build_rules.md`
  - self-improving coding rules derived from build history
  - written when recurring failure patterns are detected
  - loaded automatically by `DocumentStore`

Ownership of reading/writing these artifacts remains outside the Crafted subsystem.

## Key Invariants

### Architectural invariants

- Crafted is the **Swift/SwiftUI macOS shell**, not the backend execution engine.
- The product remains a **two-process system**:
  - Crafted hosts native macOS concerns
  - Python hosts agent logic and integrations
- Cross-process coordination occurs via **XPC**.

### Security and access invariants

- Security-sensitive behavior must conform to **TRD-11**.
- Credentials and secure local secrets are handled through **Keychain**.
- Any filesystem write using a user-supplied path must be validated with:
  - `validate_write_path`
- Crafted must not bypass backend-enforced GitHub boundaries:
  - **never use the GitHub API directly**
  - all GitHub operations must go through `GitHubTool`

### Behavioral invariants inherited from backend contract

These are not implemented by Crafted, but Crafted must not violate or obscure them:

- scope gate threshold is **85**
- below-threshold scope handling presents **coverage gaps** and limited operator choices
- re-scope after operator answers is **one-shot**, not an unbounded loop
- retries are bounded:
  - max **20 local attempts**
- context management auto-trims at **30k tokens**
- CI log output is truncated at **8k chars**
- polling respects caching and backoff rules:
  - ETag caching on polling endpoints
  - 403 primary uses exponential backoff
  - 429 secondary respects `Retry-After`

## Failure Modes

The provided documents do not define Crafted-specific internal failure taxonomy, but they define repository-level operational failure handling that constrains subsystem behavior at the boundary.

### Cross-process or operator-visible failures

Crafted may surface failures originating in the backend, including:

- scope confidence below threshold
- import/runtime/assertion failures handled by backend strategy selection
- GitHub API rate limiting or access failures
- CI/test output truncation and partial presentation
- context trimming due to token budget constraints

### Repository-defined failure handling behaviors

Relevant backend failure policies that Crafted may need to present accurately:

- strategy selection occurs in `failure_handler.py` via:
  - `_choose_strategy(failure_type, attempt, records)`
- failure type is primary; attempt count is secondary
- `assertion_error` → `test_driven` immediately
- `import_error` / `runtime_error` → converse first, then `test_driven`
- attempt `>= 8` → nuclear every 3rd attempt
- never retry indefinitely
  - max **20 local attempts**, then move on

### GitHub/API-related failures

Crafted must expect backend-mediated failures such as:

- `403` primary rate/control failures
  - exponential backoff: `2s → 4s → 8s → 16s → 32s → 64s`
- `429` secondary limits
  - respect `Retry-After`
- polling behavior uses **ETag caching**

### Data safety failures

A critical repository-level failure mode is unsafe path handling. The required mitigation is explicit:

- validate paths before any write with `validate_write_path`

Crafted must not introduce write paths that bypass this rule.

## Dependencies

### Direct subsystem dependencies

From repository identity and structure, Crafted depends on:

- **Swift / SwiftUI**
- native macOS platform services for:
  - auth
  - Keychain
  - XPC

### Runtime dependency on backend

Crafted depends on the Python backend for all agent execution and automation behaviors, including:

- `build_director.py`
- `consensus.py`
- `providers.py`
- `build_ledger.py`
- `github_tools.py`
- `document_store.py`
- `ci_workflow.py`

### Specification and governance dependencies

- `forge-docs/` TRDs are the source of truth
- **TRD-1** defines the Swift/SwiftUI application shell
- **TRD-11** governs the security model for all components
- `CraftedTests/` contains XCTest coverage for the subsystem
- repository-wide operational rules in `AGENTS.md` apply to changes affecting Crafted boundaries