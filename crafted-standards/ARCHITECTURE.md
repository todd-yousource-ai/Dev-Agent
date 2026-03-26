# Architecture

## System Overview

**Product:** Crafted / Crafted Dev Agent

Crafted is a **native macOS AI coding agent** that builds software autonomously from specifications. The repository documents define a **two-process architecture**:

- a **Swift macOS shell** responsible for native application concerns
- a **Python backend** responsible for intelligence and repository automation

The shell and backend communicate over an **authenticated Unix socket** using **line-delimited JSON**. The documents state that:

- the **Swift process owns**:
  - UI
  - authentication
  - secrets / Keychain
  - orchestration
  - XPC-related shell-side integration
- the **Python process owns**:
  - consensus
  - generation pipeline
  - GitHub operations

A core system rule stated in the loaded documents is that **neither process ever executes generated code**.

The product operates as a directed build agent rather than a chat interface. Per the repository README, the end-to-end behavior is:

1. operator loads TRDs and provides intent
2. system assesses confidence in scope
3. system decomposes intent into an ordered PRD plan
4. system decomposes each PRD into typed pull requests
5. implementation and tests are generated using **two LLM providers in parallel**
6. a self-correction pass, lint gate, and iterative fix loop run
7. CI is executed
8. a **draft GitHub pull request** is opened for review
9. after operator approval and merge, the agent proceeds to the next PR

The loaded documents repeatedly identify the consensus configuration as **Claude + GPT-4o**, with **Claude arbitrating every result**.

The foundational platform specification available in the provided content is **TRD-1: macOS Application Shell**. It specifies that the macOS shell is the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems of Crafted.

## Subsystem Map

The following subsystem map is derived only from names and responsibilities explicitly present in the loaded documents.

### 1. macOS Application Shell

**Primary source:** TRD-1, AGENTS.md, CLAUDE.md

**Technology:**
- Swift 5.9+
- SwiftUI
- bundled Python 3.12

**Responsibilities explicitly stated:**
- native macOS container for Crafted
- packaging and installation
- orchestration of all subsystems
- UI
- authentication
- secrets handling
- Keychain integration
- XPC-related integration
- backend process startup and coordination

**TRD-1 shell-owned areas explicitly listed:**
- installation and distribution:
  - `.app` bundle
  - drag-to-Applications
  - Sparkle auto-update
- identity and authentication:
  - biometric gate
  - Keychain secret storage
  - session lifecycle

### 2. SwiftUI UI Layer

**Primary source:** CLAUDE.md, TRD-1 excerpt

**Responsibilities explicitly stated or directly implied by loaded text:**
- SwiftUI views, cards, panels
- operator-facing native UI
- display of shell-owned workflow state
- authentication and review-related interaction surface

This is treated as a subsystem because the loaded documents separately direct implementers to a UI-specific TRD for SwiftUI views, cards, and panels.

### 3. Authentication and Identity Subsystem

**Primary source:** TRD-1 excerpt, AGENTS.md, heading inventory

**Responsibilities explicitly stated:**
- biometric gate
- identity and authentication
- session lifecycle
- storage of identity data and secrets

**Explicit data items found in loaded content:**
- `display_name` stored in `UserDefaults`
- `engineer_id` stored in Keychain as `SecretKey.engineerId`
- `github_username` fetched from GitHub `/user` endpoint on first auth

### 4. Secret Storage / Keychain Subsystem

**Primary source:** TRD-1 excerpt, AGENTS.md, GitHub integration lessons

**Responsibilities explicitly stated:**
- Keychain secret storage
- shell ownership of secrets
- storage of credentials needed for external operations

**Explicit secret-related usage found in loaded content:**
- GitHub App private key used to generate JWT
- engineer identity secret storage in Keychain

### 5. Backend Process

**Primary source:** AGENTS.md, CLAUDE.md, heading inventory

**Technology:**
- Python 3.12

**Responsibilities explicitly stated:**
- intelligence
- generation
- consensus
- pipeline
- GitHub operations

**Implementation artifact explicitly named:**
- `src/xpc_server.py (Python)`

### 6. Interprocess Communication Subsystem

**Primary source:** CLAUDE.md, AGENTS.md, heading inventory

**Protocol explicitly stated:**
- authenticated Unix socket
- line-delimited JSON

**Explicit operational details found:**
- shell starts Python backend process with test socket path and nonce
- shell sends error via XPC if connection is open
- named integration points include:
  - `Crafted/XPCBridge.swift`
  - `src/xpc_server.py`

The loaded repository identity text mentions both **XPC** and an **authenticated Unix socket**. The shell is documented as owning XPC-related integration; the Swift/Python process boundary is documented as using the authenticated Unix socket.

### 7. Consensus Engine

**Primary source:** README, CLAUDE.md

**Responsibilities explicitly stated:**
- two-model consensus
- provider coordination
- arbitration of results

**Explicit behavior found in README:**
- uses two LLM providers in parallel
- providers identified as Claude and GPT-4o
- Claude arbitrates every result

**Explicit component names found in loaded content:**
- `ConsensusEngine`
- `ProviderAdapter`

### 8. Planning and Decomposition Pipeline

**Primary source:** README

**Responsibilities explicitly stated:**
- confidence assessment of requested scope
- decomposition of operator intent into ordered PRD plan
- decomposition of PRD into a sequence of typed pull requests

### 9. Code Generation and Self-Correction Pipeline

**Primary source:** README, CLAUDE.md

**Responsibilities explicitly stated:**
- implementation generation
- test generation
- self-correction pass
- lint gate
- iterative fix loop

### 10. GitHub Integration Subsystem

**Primary source:** README, GitHub-Integration-Lessons-Learned, AGENTS.md

**Responsibilities explicitly stated:**
- GitHub operations
- pull request creation
- PR lifecycle actions
- user information fetch on first auth
- API interactions via REST and GraphQL

**Explicit GitHub behaviors documented in loaded content:**
- every PR is opened as a **draft**
- converting draft to ready for review must use GraphQL `markPullRequestReadyForReview`
- REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}` does not work
- merging a draft PR returns `405`
- `/user` endpoint is used to fetch `github_username` on first auth
- GitHub App flow uses JWT generated from App private key

### 11. CI Integration Subsystem

**Primary source:** heading inventory, README, GitHub lessons

**Explicit CI jobs / workflows named in loaded content:**
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- Crafted CI (ubuntu) — main Python test job
- Crafted CI — macOS (Swift) — only triggers for Swift files

**Responsibilities explicitly stated or directly implied by README:**
- execute CI before PR review/merge progression
- validate generated implementation through automated checks

### 12. Update and Distribution Subsystem

**Primary source:** TRD-1 excerpt

**Responsibilities explicitly stated:**
- `.app` bundle packaging
- drag-to-Applications installation
- Sparkle auto-update

### 13. Local Project Cache / Indexing Subsystem

**Primary source:** heading inventory

**Explicit behavior found:**
- on project creation, empty index created in `cache/{project_id}/`
- “no explicit unload — FAISS index is small enough to keep all loaded”
- “Changing the embedding model will require re-embedding all ...”

This subsystem can be named only to the extent supported by the loaded text: it is a cache/index facility associated with project state and FAISS-backed index residency.

### 14. Review / Exclusion Control Surface

**Primary source:** heading inventory

**Explicit operator controls found:**
- `adjust scope` → operator can type directory or file exclusions
- `exclude files` → operator lists files/issues to exclude before fixing
- `exclude security in src/vendor/` → exclude lens in directory
- `exclude src/legacy/` → exclude entire directory
- `exclude src/old_api.py` → exclude specific file
- `select lenses` → operator types comma-separated lens IDs
- `/review start examples`
- `/review exclude examples`

The loaded content supports a subsystem for operator-directed review scoping and lens selection, but not further internal behavior beyond these controls.

### 15. Security and Enforcement Model

**Primary source:** AGENTS.md, CLAUDE.md, architecture rules, heading inventory

**Responsibilities explicitly stated:**
- governed by TRD-11 for all security-relevant code
- applies to credentials, external content, generated code, and CI
- enforcement-oriented architecture rules

**Explicit architecture rules present in loaded content:**
- trust must never be inferred implicitly when it can be asserted and verified explicitly
- identity, policy, telemetry, and enforcement must remain separable but tightly linked
- all control decisions must be explainable, observable, and reproducible
- components must default to policy enforcement, not policy suggestion
- local agents must minimize user friction while preserving strong enforcement guarantees
- administrative workflows must be simple, explicit, and understandable in plain language
- protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments

## Component Boundaries

This section states what each subsystem must never do, using only boundaries explicitly supported by the provided documents.

### macOS Application Shell
**Must do:**
- own UI, authentication, Keychain/secrets, orchestration
- package and install the app
- manage native macOS lifecycle concerns

**Must never do:**
- own consensus, generation, or GitHub operations, which are assigned to the Python backend
- execute generated code

### SwiftUI UI Layer
**Must do:**
- present native views, cards, and panels
- collect operator interaction within the shell boundary

**Must never do:**
- directly own secrets storage
- directly own generation, consensus, or GitHub operations
- execute generated code

### Authentication and Identity Subsystem
**Must do:**
- enforce biometric gate
- manage session lifecycle
- coordinate identity state with shell-owned storage

**Must never do:**
- bypass shell-owned secret handling
- infer trust implicitly where explicit assertion/verification is required
- execute generated code

### Secret Storage / Keychain Subsystem
**Must do:**
- store secrets in Keychain
- support credential use needed by shell-owned and backend-coordinated workflows through approved interfaces

**Must never do:**
- expose secrets as backend-owned state
- shift shell-owned secrets responsibility into the Python backend
- execute generated code

### Backend Process
**Must do:**
- own intelligence, generation, consensus, pipeline, and GitHub operations

**Must never do:**
- own UI
- own authentication
- own Keychain/secrets
- execute generated code

### Interprocess Communication Subsystem
**Must do:**
- use authenticated Unix socket transport
- use line-delimited JSON framing
- authenticate the process connection

**Must never do:**
- rely on unauthenticated backend communication
- collapse shell and backend responsibilities into a single process boundary contrary to the documented two-process model

### Consensus Engine
**Must do:**
- coordinate two-model consensus
- arbitrate results as documented

**Must never do:**
- replace the documented two-provider consensus model with a single implicit source of truth
- bypass the documented arbitration behavior
- execute generated code

### Planning and Decomposition Pipeline
**Must do:**
- assess confidence in scope
- decompose intent into ordered PRD plan
- decompose PRDs into typed PRs

**Must never do:**
- skip specification-driven decomposition when operating in the documented build flow
- execute generated code

### Code Generation and Self-Correction Pipeline
**Must do:**
- generate implementation and tests
- run self-correction, lint, and iterative fix loops

**Must never do:**
- execute generated code
- bypass validation stages described in the README flow

### GitHub Integration Subsystem
**Must do:**
- open draft pull requests
- use the correct GitHub API mode for draft lifecycle operations
- support GitHub user lookup and App-authenticated flows as documented

**Must never do:**
- assume REST can convert draft PRs to ready for review
- attempt to merge draft PRs
- deviate from documented GitHub API behavior where production lessons learned define required handling

### CI Integration Subsystem
**Must do:**
- run CI as part of the PR pipeline
- support named Python and macOS validation jobs documented in repository materials

**Must never do:**
- substitute CI execution with unverified assumptions of correctness
- execute generated code outside the documented validation pipeline

### Update and Distribution Subsystem
**Must do:**
- package the app as a macOS `.app`
- support drag-to-Applications install
- support Sparkle auto-update

**Must never do:**
- redefine distribution outside the documented macOS application shell model

### Local Project Cache / Indexing Subsystem
**Must do:**
- maintain per-project cache/index state in `cache/{project_id}/`
- retain loaded FAISS index state per the documented behavior

**Must never do:**
- require explicit unload behavior when the loaded documents state none exists
- ignore embedding-model change implications on re-embedding

### Review / Exclusion Control Surface
**Must do:**
- allow operator-provided exclusion and lens-selection controls as documented

**Must never do:**
- remove operator control over exclusions implied by the documented commands/examples
- silently broaden review scope against explicit operator exclusions

### Security and Enforcement Model
**Must do:**
- follow TRD-11 for all security-relevant concerns
- preserve explicit trust assertion and verification
- keep identity, policy, telemetry, and enforcement separable but linked

**Must never do:**
- default to policy suggestion instead of enforcement
- make non-explainable or non-reproducible control decisions
- weaken enforcement in favor of reduced friction
- permit generated code execution

## Key Data Flows

## 1. Application startup and backend orchestration

Derived from AGENTS.md, CLAUDE.md, TRD-1 excerpt, and heading inventory.

1. The macOS shell launches as the native `.app`.
2. The shell owns local application lifecycle, UI, authentication, and secret access.
3. The shell starts the Python backend process.
4. The shell provides connection parameters including a **socket path** and **nonce**.
5. Shell and backend establish communication over an **authenticated Unix socket**.
6. Messages are exchanged as **line-delimited JSON**.
7. If an error occurs and the connection is open, the shell can send error information through the documented bridge path.

## 2. Authentication and identity establishment

Derived from TRD-1 excerpt and heading inventory.

1. The shell initiates identity/authentication flow.
2. Biometric gate is used.
3. Secrets are stored in Keychain.
4. Identity-related non-secret display state may be stored in `UserDefaults`.
5. On first GitHub auth, `github_username` is fetched from GitHub `/user`.
6. Session lifecycle remains shell-owned.

## 3. Operator intent to PR plan to typed PRs

Derived from README.

1. Operator loads TRDs and provides plain-language intent.
2. System assesses confidence in requested scope.
3. Intent is decomposed into an ordered PRD plan.
4. Each PRD is decomposed into a sequence of typed pull requests.
5. The system proceeds through those PRs one logical unit at a time.

## 4. Consensus-driven implementation generation

Derived from README and CLAUDE.md.

1. For a selected unit of work, the backend invokes two LLM providers in parallel.
2. Providers are the documented consensus pair: Claude and GPT-4o.
3. Generated implementation and tests are produced through the backend-owned intelligence pipeline.
4. Claude arbitrates the result.
5. Self-correction pass runs.
6. Lint gate runs.
7. Iterative fix loop runs.

## 5. CI-gated pull request flow

Derived from README and GitHub lessons.

1. After generation and correction stages, CI is executed.
2. The system opens a **draft pull request** for operator review.
3. Draft state is intentional so CI can run before operator review.
4. When transitioning a PR from draft to ready for review, the system must use GraphQL `markPullRequestReadyForReview`.
5. A draft PR must not be merged directly because GitHub returns `405`.
6. Operator reviews, gates, and merges.
7. The agent begins the next PR while the operator reads the previous one.

## 6. GitHub App authentication flow

Derived from heading inventory and GitHub lessons.

1. The system generates a JWT using the GitHub App private key stored in Keychain.
2. The JWT is used for GitHub App-authenticated API interactions.
3. GitHub user/account data may also be retrieved through GitHub API endpoints such as `/user` where documented.

## 7. Project cache / index lifecycle

Derived from heading inventory.

1. When a project is created, an empty index is created at `cache/{project_id}/`.
2. FAISS index state is kept loaded; no explicit unload behavior is required.
3. If embedding model changes, re-embedding is required.

## 8. Operator review scoping

Derived from heading inventory.

1. Operator starts review flow.
2. Operator may adjust scope.
3. Operator may exclude files or directories.
4. Operator may exclude security review in a directory or specific file paths.
5. Operator may select lenses via comma-separated lens IDs.
6. The system respects those scope selections during review/fix operations.

## Critical Invariants

The following invariants are directly supported by the loaded documents and should be treated as architecture-level requirements.

### 1. Two-process invariant
Crafted is a **two-process system**:
- Swift shell
- Python backend

This boundary is fundamental and repeatedly stated.

### 2. Responsibility partition invariant
Ownership is fixed as follows:
- **Swift shell:** UI, auth, Keychain/secrets, orchestration, shell-side platform integration
- **Python backend:** consensus, intelligence, generation pipeline, GitHub operations

Changes must not blur or invert this split.

### 3. Authenticated IPC invariant
Shell/backend communication must use:
- authenticated Unix socket
- line-delimited JSON

Unauthenticated or differently framed communication violates the documented architecture.

### 4. No generated code execution invariant
Neither process ever executes generated code.

This is one of the clearest cross-cutting rules in the loaded documents.

### 5. Specification-driven implementation invariant
The codebase is defined by the TRDs in `forge-docs/`, and repository instructions state they are the source of truth. Architecture, interfaces, error contracts, state machines, security controls, and performance requirements must match those documents.

### 6. Security-governance invariant
TRD-11 governs security-relevant code, especially for:
- credentials
- external content
- generated code
- CI

Any architecture change touching those areas must remain subordinate to that security model.

### 7. Secret ownership invariant
Secrets are shell-owned and stored via Keychain. The backend does not own Keychain or authentication responsibilities.

### 8. Draft-PR lifecycle invariant
The automation opens pull requests as **drafts**. Draft lifecycle behavior must conform to the documented GitHub API realities:
- draft → ready-for-review requires GraphQL mutation
- draft PRs cannot be merged directly

### 9. Consensus invariant
The generation system uses a **two-model consensus engine** with:
- Claude
- GPT-4o
- Claude as arbiter

This is the documented operating model in the provided repository materials.

### 10. Enforcement-first invariant
From the architecture rules:
- trust must be explicit and verifiable
- identity, policy, telemetry, and enforcement remain separable but linked
- control decisions must be explainable, observable, and reproducible
- components default to enforcement, not suggestion

These are architecture constraints, not implementation preferences.

### 11. Native macOS distribution invariant
Crafted is a native macOS application distributed as an `.app`, installed via drag-to-Applications, with Sparkle auto-update per TRD-1.

### 12. Session and identity persistence invariant
The loaded documents explicitly define persistence locations for at least some identity fields:
- `display_name` → `UserDefaults`
- `engineer_id` → Keychain
- `github_username` → fetched from GitHub `/user` on first auth

Implementations must preserve these documented storage/derivation boundaries.

### 13. CI-before-review pipeline invariant
The README-defined flow includes validation stages before PR review progression:
- self-correction
- lint gate
- iterative fix loop
- CI
- draft PR creation

The architecture must preserve this ordering as the documented product behavior.

### 14. Project index persistence invariant
A project has cache/index state under `cache/{project_id}/`; FAISS index state remains loaded without explicit unload; embedding-model changes require re-embedding.

### 15. Operator scope-control invariant
The operator has explicit control over review scope through exclusions and lens selection. The system must preserve those explicit controls rather than infer a broader scope automatically.