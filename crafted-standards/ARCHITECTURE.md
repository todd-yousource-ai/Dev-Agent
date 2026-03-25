# Architecture

## System Overview (derived from the TRDs above)

**Product:** Crafted Dev Agent, also referred to in the shell TRD as **Crafted**.

Crafted is a **native macOS AI coding agent** that autonomously builds software from specifications and opens GitHub pull requests for operator review. The loaded documents define a **two-process architecture**:

- a **Swift macOS shell** responsible for native application concerns
- a **Python backend** responsible for intelligence and repository automation

The authoritative process split is stated consistently across the repository documents:

- **Swift shell owns:** UI, authentication, Keychain secret storage, session lifecycle, native orchestration, and local IPC/XPC-related integration
- **Python backend owns:** consensus, generation pipeline, self-correction/fix loops, and GitHub operations

The processes communicate over an **authenticated Unix socket** using **line-delimited JSON**. The documents also explicitly state a key execution boundary: **neither process ever executes generated code**.

From the README, the end-to-end product behavior is:

1. Operator provides a repository, technical specifications (TRDs), and intent.
2. The agent evaluates confidence and scope.
3. The agent decomposes intent into an ordered PRD plan.
4. The agent decomposes each PRD into typed pull requests.
5. Two LLM providers generate implementation and tests in parallel.
6. Claude arbitrates results.
7. The system runs self-correction, lint gating, iterative fix loops, and CI.
8. The system opens a **draft GitHub pull request** for operator review.
9. After approval and merge, the system continues with the next logical unit.

TRD-1 defines the shell as the native container that **packages, installs, authenticates, and orchestrates all subsystems** of the product. It is foundational and is required by multiple other TRDs.

The architecture rules supplied in the source content apply system-wide:

- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Crafted components must default to policy enforcement, not policy suggestion.
- Local agents must minimize user friction while preserving strong enforcement guarantees.
- Administrative workflows must be simple, explicit, and understandable in plain language.
- Protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments.

## Subsystem Map (one entry per subsystem found in the docs)

### 1. macOS Application Shell
**Source:** TRD-1, AGENTS.md, CLAUDE.md

The native Swift/SwiftUI container for the product. TRD-1 states that it owns:

- installation and distribution
  - `.app` bundle
  - drag-to-Applications
  - Sparkle auto-update
- identity and authentication
  - biometric gate
  - Keychain secret storage
  - session lifecycle
- orchestration of all subsystems

Repository-level guidance further assigns to the shell:

- UI
- auth
- secrets
- XPC-related integration

### 2. SwiftUI UI Layer
**Source:** CLAUDE.md, TRD-1 references, README

The native operator-facing interface implemented in SwiftUI. The loaded docs explicitly associate:

- SwiftUI views, cards, panels
- operator review/gating workflow
- native shell presentation and control surface

This UI is part of the Swift shell process rather than an independent runtime.

### 3. Authentication and Identity Subsystem
**Source:** TRD-1 excerpts, heading fragments

Authentication and identity management are explicitly owned by the shell. Loaded content identifies:

- biometric gate
- Keychain-backed secret storage
- session lifecycle
- identity fields such as:
  - `display_name` stored in `UserDefaults`
  - `engineer_id` stored in Keychain as `SecretKey.engineerId`
  - `github_username` fetched from GitHub `/user` endpoint on first auth

### 4. Secret Storage / Keychain Subsystem
**Source:** AGENTS.md, CLAUDE.md, TRD-1 excerpts

The shell owns secret handling. The docs explicitly mention:

- Keychain secret storage
- App private key stored in Keychain for GitHub App JWT generation
- engineer identity secret storage in Keychain

### 5. Session Lifecycle Subsystem
**Source:** TRD-1 excerpt, heading fragments

The shell owns session lifecycle, including limits and gating. Loaded content references:

- session lifecycle
- session token total enforcement
- `OI-13 session limit: blocks generation if session token total exceeded`

### 6. IPC Transport: Authenticated Unix Socket Protocol
**Source:** CLAUDE.md

The inter-process boundary between shell and backend. The documents explicitly define:

- authenticated Unix socket
- line-delimited JSON framing
- shell/backend communication over this channel

### 7. XPC Integration Layer
**Source:** AGENTS.md, heading fragments

Repository-level identity assigns XPC to the shell architecture. Loaded content references:

- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`
- XPC connection establishment failures
- credential delivery path failure modes

This is an integration surface inside the two-process local architecture.

### 8. Python Backend
**Source:** AGENTS.md, CLAUDE.md

The second process in the system. It owns:

- consensus
- intelligence
- generation
- GitHub operations
- pipeline execution

### 9. Consensus Engine
**Source:** README, CLAUDE.md

The core decision subsystem for model output generation and arbitration. README defines:

- two-model consensus engine
- Claude + GPT-4o run in parallel
- Claude arbitrates every result

### 10. Provider Adapter Layer
**Source:** CLAUDE.md fragment

A backend-owned model-provider integration layer referenced alongside `ConsensusEngine, ProviderAdapter`. This subsystem mediates model-provider-specific interactions required by consensus execution.

### 11. Planning Subsystem
**Source:** README

The planning layer converts operator intent into staged implementation work:

- assess confidence in scope
- decompose intent into ordered PRD plan
- decompose each PRD into typed pull requests

### 12. Generation Pipeline
**Source:** AGENTS.md, CLAUDE.md, README

The backend execution pipeline that produces implementation artifacts. README explicitly includes:

- implementation generation
- test generation
- self-correction pass
- lint gate
- iterative fix loop

### 13. Repository and GitHub Integration Subsystem
**Source:** AGENTS.md, CLAUDE.md, README, GitHub lessons document

The backend-owned GitHub automation layer. Explicit responsibilities and behaviors in loaded docs include:

- GitHub operations
- opening draft pull requests
- fetching current repository file content and SHA
- updating repository contents through GitHub APIs
- fetching `/user` on first auth
- generating GitHub App JWT using App private key from Keychain
- handling draft PR lifecycle nuances
- using GraphQL mutation to mark PR ready for review
- draft PR merge behavior constraints

### 14. CI Orchestration / Validation Subsystem
**Source:** README, heading fragments, workflow names

The pipeline includes CI execution before PR review. Loaded content names CI jobs/workflows including:

- Forge CI — Python / test
- Forge CI — macOS / unit-test
- Forge CI — macOS / xpc-integration-test
- Crafted CI (ubuntu) — main Python test job
- Crafted CI — macOS (Swift) — only triggers for Swift files

### 15. Installation, Packaging, and Distribution Subsystem
**Source:** TRD-1 excerpts

TRD-1 explicitly assigns the shell ownership of packaging and app distribution:

- `.app` bundle
- drag-to-Applications install flow
- Sparkle auto-update

### 16. Local Project/Index Cache Subsystem
**Source:** heading fragments

Loaded content references project-local cache/index behavior:

- `Project created: empty index created in cache/{project_id}/`
- `(no explicit unload — FAISS index is small enough to keep all loaded)`
- `Changing the embedding model will require re-embedding all ...`

This indicates a project-scoped local indexing/cache subsystem, though only the above behaviors are explicitly present in the supplied content.

### 17. Operator Review and Exclusion Control Surface
**Source:** heading fragments, README

The loaded docs expose operator review controls and exclusion mechanisms such as:

- `/review start`
- `/review exclude`
- `adjust scope`
- `exclude files`
- `select lenses`
- exclusion examples for directories and files

This subsystem exists at the operator interaction layer and constrains what is reviewed or fixed.

### 18. Security Governance
**Source:** AGENTS.md, CLAUDE.md, architecture rules

Security is a cross-cutting subsystem governed by TRD-11. The loaded repository instructions state:

- TRD-11 governs all components
- it must be read before touching credentials, external content, generated code, or CI

The loaded docs also supply explicit security-sensitive conditions:

- authenticated local transport
- Keychain secret custody
- biometric gating
- no execution of generated code
- external API integration controls

## Component Boundaries (what each subsystem must never do)

### macOS Application Shell
Must never:

- own consensus, generation, or GitHub operations
- execute generated code
- infer trust implicitly rather than asserting and verifying it explicitly

### SwiftUI UI Layer
Must never:

- directly implement backend intelligence responsibilities
- bypass shell-owned authentication or secret custody
- perform GitHub automation as a UI concern

### Authentication and Identity Subsystem
Must never:

- delegate shell-owned credential custody outside approved secret storage
- treat unauthenticated state as implicitly trusted
- bypass biometric gate where the shell requires it

### Secret Storage / Keychain Subsystem
Must never:

- expose long-lived secrets as plain configuration
- move secret authority into the Python backend
- store shell-owned secrets outside the shell-owned secret boundary described in the docs

### Session Lifecycle Subsystem
Must never:

- allow generation to proceed after documented session token limits are exceeded
- decouple session enforcement from authentication state

### IPC Transport: Authenticated Unix Socket Protocol
Must never:

- operate without authentication
- deviate from line-delimited JSON framing
- collapse the process boundary between shell and backend

### XPC Integration Layer
Must never:

- become the source of truth for shell/backend ownership
- bypass authenticated credential delivery guarantees
- obscure transport failures such as deadlock, shell crash before credential send, or connection establishment failure

### Python Backend
Must never:

- own UI, native auth, or Keychain secret storage
- execute generated code
- take over shell-owned installation/distribution concerns

### Consensus Engine
Must never:

- replace the documented two-model consensus behavior with a single implicit model path
- bypass Claude arbitration where the README says Claude arbitrates every result

### Provider Adapter Layer
Must never:

- redefine consensus policy
- bypass backend pipeline control
- blur provider-specific integration with shell responsibilities

### Planning Subsystem
Must never:

- skip confidence/scope assessment as described in README
- skip decomposition into ordered PRD plan and typed pull requests

### Generation Pipeline
Must never:

- omit the documented self-correction, lint gate, iterative fix loop, or test generation stages where applicable
- execute generated code
- bypass CI before draft PR creation as described in README

### Repository and GitHub Integration Subsystem
Must never:

- live in the Swift shell as an ownership concern
- ignore documented GitHub API behavior for draft PR lifecycle
- assume unsupported REST behavior for converting draft PRs to ready for review

### CI Orchestration / Validation Subsystem
Must never:

- be treated as optional relative to the README pipeline
- conflate Python and macOS validation paths where the loaded docs distinguish them

### Installation, Packaging, and Distribution Subsystem
Must never:

- migrate out of the shell boundary
- bypass native macOS packaging/distribution mechanisms specified by TRD-1

### Local Project/Index Cache Subsystem
Must never:

- assume embedding-model changes are compatible with existing embeddings when the loaded docs indicate re-embedding is required
- force explicit unload behavior when the supplied docs state no explicit unload is required for the FAISS index

### Operator Review and Exclusion Control Surface
Must never:

- remove the operator’s ability to gate, review, and merge
- silently alter exclusion scope outside operator-specified controls

### Security Governance
Must never:

- be treated as advisory only; architecture rules require enforcement by default
- be separated from explainability, observability, and reproducibility
- permit generated code execution

## Key Data Flows

### 1. Operator Intent to Draft Pull Request
Derived from the README and process ownership documents:

1. Operator provides:
   - repository
   - TRDs/specifications
   - plain-language intent
2. System assesses confidence in scope.
3. System decomposes intent into an ordered PRD plan.
4. System decomposes PRD work into typed pull requests.
5. Python backend runs two-model generation in parallel.
6. Claude arbitrates results.
7. Backend executes:
   - self-correction pass
   - lint gate
   - iterative fix loop
   - CI
8. Backend opens a **draft** GitHub pull request for operator review.

### 2. Shell-to-Backend Control Flow
Derived from CLAUDE.md and repository guidance:

1. Swift shell authenticates operator and manages session state.
2. Shell retains secret custody in Keychain.
3. Shell communicates with Python backend through an authenticated Unix socket using line-delimited JSON.
4. Backend performs intelligence/pipeline/GitHub work.
5. Results and errors are returned across the local IPC boundary.

### 3. Credential and Identity Flow
Derived from TRD-1 excerpts and heading fragments:

1. Operator authenticates through shell-controlled identity flow, including biometric gate.
2. Shell stores sensitive identity/secret material in Keychain.
3. `display_name` is stored in `UserDefaults`.
4. `engineer_id` is stored in Keychain.
5. `github_username` is fetched from GitHub `/user` on first auth.
6. GitHub App JWT is generated using an App private key sourced from Keychain.

### 4. GitHub Draft PR Lifecycle Flow
Derived from README and GitHub lessons document:

1. Backend creates pull requests as **drafts**.
2. CI runs before the operator sees or acts on the change.
3. Conversion from draft to ready-for-review must use the GraphQL `markPullRequestReadyForReview` mutation.
4. The system must not rely on REST `PATCH /pulls/{number}` with `{"draft": false}` because the loaded document states GitHub ignores this field.

### 5. Repository Update Flow
Derived from heading fragments:

1. Read current file from GitHub to obtain content and SHA.
2. Compute new content hash.
3. Update content through GitHub API operations.
4. Use the backend-owned GitHub integration boundary for these operations.

### 6. Local Index/Cache Flow
Derived from heading fragments:

1. Project creation initializes an empty index at `cache/{project_id}/`.
2. Index remains loaded; no explicit unload is required because the supplied docs state the FAISS index is small enough to keep loaded.
3. Embedding model changes require re-embedding all indexed content.

### 7. XPC Credential/Error Flow
Derived from heading fragments:

1. Shell starts backend process with test socket path and nonce in test/integration scenarios referenced by headings.
2. Credentials are delivered across the local integration boundary.
3. If the connection is open, errors are sent via XPC.
4. Failure cases explicitly documented include:
   - deadlock in credential delivery path
   - shell crash before sending credentials
   - XPC connection failed to establish

## Critical Invariants

### Process and Ownership Invariants
- Crafted is a **two-process** system.
- The **Swift shell** owns UI, authentication, Keychain secret storage, session lifecycle, installation/distribution, and subsystem orchestration.
- The **Python backend** owns consensus, generation pipeline, intelligence, and GitHub operations.
- Ownership must not be blurred across these boundaries.

### Execution Safety Invariants
- **Neither process ever executes generated code.**

### IPC Invariants
- Shell and backend communicate via an **authenticated Unix socket**.
- Messages are **line-delimited JSON**.
- Authentication on the local transport is mandatory.

### Security Invariants
- TRD-11 governs security-relevant behavior across components.
- Trust must be asserted and verified explicitly.
- Components default to enforcement, not suggestion.
- Identity, policy, telemetry, and enforcement remain separable but tightly linked.
- Control decisions must be explainable, observable, and reproducible.

### Secret Custody Invariants
- Shell-owned secrets remain in the shell security boundary.
- Keychain is the secret store explicitly named in the docs for sensitive material.
- The Python backend does not own Keychain secret storage.

### Planning and Generation Invariants
- Intent is assessed for confidence/scope before commitment.
- Intent is decomposed into ordered PRD plans.
- PRDs are decomposed into typed pull requests.
- Generation uses a two-model consensus flow.
- Claude arbitrates every result.

### Validation Invariants
- The generation pipeline includes:
  - test generation
  - self-correction
  - lint gate
  - iterative fix loop
  - CI
- CI occurs before operator review of the resulting PR, per the README flow.

### GitHub Workflow Invariants
- Pull requests are opened as **drafts**.
- Draft-to-ready conversion must follow the documented GitHub-supported GraphQL mutation path.
- The system must not depend on unsupported REST draft-conversion semantics.

### Operator Control Invariants
- The operator gates, reviews, and merges.
- Exclusion/scope controls remain operator-directed.
- The product is **not** a chat interface, autocomplete tool, or copilot; it is a directed build agent.

### Packaging and Platform Invariants
- The shell is a **native macOS** application.
- Minimum macOS version in TRD-1 is **13.0 (Ventura)**.
- Core implementation technologies named in TRD-1 are:
  - Swift 5.9+
  - SwiftUI
  - bundled Python 3.12

### Local Index Invariants
- Project creation creates an empty cache/index at `cache/{project_id}/`.
- The FAISS index does not require explicit unload according to the supplied docs.
- Changing embedding models requires full re-embedding of indexed content.