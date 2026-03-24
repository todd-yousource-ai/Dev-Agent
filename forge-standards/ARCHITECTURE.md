# Architecture

## System Overview

**Crafted Dev Agent** is a native macOS AI coding agent. The repository documents a **two-process architecture**:

- a **Swift macOS application shell**
- a **Python backend**

The loaded documents define the split consistently:

- **Swift shell** owns:
  - UI
  - authentication
  - secrets / Keychain
  - XPC
  - installation and distribution
  - session lifecycle orchestration
- **Python backend** owns:
  - intelligence
  - consensus
  - generation pipeline
  - GitHub operations

Per the repository guidance, the two processes communicate over an **authenticated Unix socket** using **line-delimited JSON**. The documents also state a strict execution boundary: **neither process ever executes generated code**.

The product behavior described in the README is a directed autonomous build workflow driven by repository specifications and operator intent:

1. load technical specifications / TRDs
2. accept plain-language operator intent
3. assess confidence in scope
4. decompose intent into an ordered PRD plan
5. decompose PRD work into typed pull requests
6. generate implementation and tests using two LLM providers in parallel
7. run self-correction, lint gating, iterative fix loop, and CI
8. open a **draft pull request** for operator review
9. after approval and merge, continue with the next planned unit

The loaded sources identify **Claude + GPT-4o** as the two-model consensus pair, with **Claude arbitrating every result**.

The shell is foundational. TRD-1 defines it as the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems of Crafted. It specifies:

- **Min macOS:** 13.0 (Ventura)
- **Language stack:** Swift 5.9+, SwiftUI, bundled Python 3.12
- **Distribution:** `.app` bundle, drag-to-Applications, Sparkle auto-update

Repository-level authority is explicit:

- the product is specified in **16 TRDs**
- those TRDs are the **source of truth**
- **TRD-11 governs security-relevant behavior across all components**

## Subsystem Map

The following subsystem map is derived only from the loaded documents.

### 1. macOS Application Shell

**Source:** TRD-1, AGENTS.md, CLAUDE.md

**Responsibility:**

- native Swift/SwiftUI application container
- package, install, authenticate, and orchestrate all subsystems
- own UI
- own auth and biometric gate
- own Keychain secret storage
- own XPC-facing shell responsibilities
- manage session lifecycle
- distribute as macOS app bundle with Sparkle auto-update

**Declared scope in TRD-1:**

- installation and distribution
- identity and authentication
- session lifecycle/orchestration

**Technology:**

- Swift 5.9+
- SwiftUI
- macOS 13.0+
- bundled Python 3.12 runtime

---

### 2. SwiftUI Presentation Layer

**Source:** CLAUDE.md, TRD mapping table fragment

**Responsibility:**

- SwiftUI views, cards, and panels

This is identified as a distinct implementation area by the repository instructions, which direct SwiftUI views/cards/panels work to **TRD-8**.

---

### 3. Authentication and Identity Subsystem

**Source:** TRD-1 headings and extracted content

**Responsibility:**

- biometric gate
- identity and authentication
- session-lifetime control
- storage/retrieval of user identity material

**Documented data examples from loaded content:**

- `display_name` stored in `UserDefaults`
- `engineer_id` stored in Keychain as `SecretKey.engineerId`
- `github_username` fetched from GitHub `/user` endpoint on first auth

This subsystem is owned by the Swift shell per the product split.

---

### 4. Secret Storage / Keychain Subsystem

**Source:** AGENTS.md, CLAUDE.md, TRD-1

**Responsibility:**

- store secrets in Keychain
- keep credentials on the Swift side
- support authentication and GitHub/App credential flows

The source documents consistently assign secrets ownership to the Swift shell.

---

### 5. Interprocess Communication Subsystem

**Source:** AGENTS.md, CLAUDE.md, extracted headings

**Responsibility:**

- communication between Swift shell and Python backend
- authenticated local IPC
- transport of credentials and control messages

**Documented protocol/material:**

- authenticated Unix socket
- line-delimited JSON
- test/startup references include:
  - `Crafted/XPCBridge.swift`
  - `src/xpc_server.py`
  - “Start Python backend process with test socket path and nonce”
  - “Send error via XPC if connection is open”

The docs use both **XPC** terminology and explicit **authenticated Unix socket** wording. The architecture document should preserve both because both appear in the loaded materials, without reconciling beyond what is stated.

---

### 6. Python Backend

**Source:** AGENTS.md, CLAUDE.md

**Responsibility:**

- intelligence
- code generation
- consensus
- pipeline execution
- GitHub operations

The Python backend is the non-UI process and does not own authentication or secret storage.

---

### 7. Consensus Engine

**Source:** README, AGENTS.md, CLAUDE.md fragment

**Responsibility:**

- run two-model generation/comparison workflow
- use Claude + GPT-4o in parallel
- have Claude arbitrate the result

The README explicitly states the agent uses a **two-model consensus engine** and names the providers.

---

### 8. Provider Adapter Layer

**Source:** CLAUDE.md fragment

**Responsibility:**

- provider-facing abstraction supporting consensus execution

The loaded content references `ConsensusEngine, ProviderAdapter` as an implementation area, so ProviderAdapter is a distinct subsystem boundary.

---

### 9. Planning and Decomposition Pipeline

**Source:** README

**Responsibility:**

- assess confidence in scope before committing
- decompose intent into an ordered PRD plan
- decompose each PRD into a sequence of typed PRs

This is part of the Python-owned intelligence/pipeline side.

---

### 10. Generation, Self-Correction, and Fix Loop Pipeline

**Source:** README

**Responsibility:**

- generate implementation and tests
- run self-correction pass
- run lint gate
- run iterative fix loop
- drive toward CI-passing draft PR output

This belongs to the Python backend per the ownership split.

---

### 11. GitHub Integration Subsystem

**Source:** AGENTS.md, CLAUDE.md, README, GitHub lessons-learned doc

**Responsibility:**

- repository reads/writes through GitHub APIs
- PR creation
- PR draft lifecycle handling
- merge operations
- user lookup (`/user` endpoint on first auth)

**Documented behaviors from lessons learned:**

- draft PRs are opened intentionally so CI can run before operator review
- converting draft to ready-for-review must use **GraphQL `markPullRequestReadyForReview`**
- REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}` does not work
- merge behavior differs for draft PRs, including a documented **405** case

This subsystem is explicitly owned by the Python backend.

---

### 12. CI and Validation Subsystem

**Source:** README, extracted headings

**Responsibility:**

- execute CI before PR presentation/merge workflow
- validate Python and macOS/Swift paths

**Named jobs surfaced in loaded content:**

- `Forge CI — Python / test`
- `Crafted CI (ubuntu) — main Python test job`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- `Crafted CI — macOS (Swift) — only triggers for Swift files`

---

### 13. Auto-Update / Distribution Subsystem

**Source:** TRD-1

**Responsibility:**

- `.app` packaging
- drag-to-Applications install flow
- Sparkle auto-update

This is shell-owned.

---

### 14. Project/Cache/Index Lifecycle Subsystem

**Source:** extracted headings

**Responsibility:**

- project-local cache/index initialization and maintenance

**Documented behavior surfaced in loaded content:**

- “Project created: empty index created in `cache/{project_id}/`”
- “no explicit unload — FAISS index is small enough to keep all loaded”
- “Changing the embedding model will require re-embedding all ...”

Only the existence of this index/cache lifecycle should be asserted here; loaded content does not fully define broader behavior.

---

### 15. Operator Command / Review Control Surface

**Source:** extracted headings and README

**Responsibility:**

- accept operator intent
- support review and exclusion controls

**Documented examples from loaded content:**

- `/ledger note <text>`
- `/review start`
- `/review exclude`
- “adjust scope” with directory/file exclusions
- “exclude files”
- “select lenses”
- exclusion examples:
  - `exclude src/legacy/`
  - `exclude src/old_api.py`
  - `exclude security in src/vendor/`

This is a user-facing control surface, but the loaded documents do not assign all implementation details to one process.

## Component Boundaries

This section states only boundaries directly supported by the loaded documents.

### macOS Application Shell must never

- execute generated code
- delegate ownership of authentication to Python
- delegate ownership of secrets / Keychain to Python
- delegate UI ownership to Python

**Basis:** shell owns UI, auth, Keychain, orchestration; neither process executes generated code.

---

### SwiftUI Presentation Layer must never

- own GitHub operations
- own consensus/generation logic
- own secret storage policy

**Basis:** UI belongs to Swift shell; intelligence and GitHub belong to Python; secrets belong to shell authentication/Keychain subsystem rather than view layer.

---

### Authentication and Identity Subsystem must never

- be implemented as a Python-owned concern
- rely on Python as the source of truth for secrets

**Basis:** Swift shell owns authentication and secrets.

---

### Secret Storage / Keychain Subsystem must never

- be handled by the Python backend
- expose credentials through an unauthenticated process boundary

**Basis:** shell owns secrets; process communication is explicitly authenticated.

---

### Interprocess Communication Subsystem must never

- operate without authentication
- use an undocumented message framing different from line-delimited JSON, where the documented socket protocol applies

**Basis:** authenticated Unix socket with line-delimited JSON is explicitly specified.

---

### Python Backend must never

- own UI
- own biometric/authentication flows
- own Keychain secrets
- execute generated code

**Basis:** product split and global execution rule.

---

### Consensus Engine must never

- replace the documented two-model consensus pattern with a single-model path when implementing the README-described build flow
- bypass Claude arbitration of results

**Basis:** README explicitly states two-model consensus engine with Claude arbitrating every result.

---

### Provider Adapter Layer must never

- absorb shell responsibilities such as auth, UI, or Keychain
- substitute for consensus arbitration logic

**Basis:** ownership split and distinct existence of ConsensusEngine and ProviderAdapter.

---

### Planning and Decomposition Pipeline must never

- skip decomposition directly from intent to undifferentiated code output in the README-defined workflow

**Basis:** README defines intent → ordered PRD plan → typed PR sequence.

---

### Generation / Fix Loop Pipeline must never

- omit validation stages described in the README-defined flow when implementing that flow
- execute generated code

**Basis:** self-correction, lint gate, iterative fix loop, and CI are explicit stages; execution ban is global.

---

### GitHub Integration Subsystem must never

- assume REST `PATCH ... {"draft": false}` converts draft PRs to ready-for-review
- ignore documented draft PR lifecycle differences

**Basis:** lessons-learned document explicitly records this behavior and required GraphQL mutation.

---

### CI and Validation Subsystem must never

- be treated as optional in the documented PR pipeline

**Basis:** README states CI is executed before opening the draft PR for review.

---

### Auto-Update / Distribution Subsystem must never

- be reassigned to the Python backend

**Basis:** installation and distribution are shell-owned in TRD-1.

## Key Data Flows

## 1. Application startup and orchestration

1. The **macOS Application Shell** launches as the native `.app`.
2. The shell initializes the native environment and bundled Python runtime context.
3. The shell starts and orchestrates the **Python backend**.
4. Communication is established over the documented authenticated local IPC channel.

**Documented startup-related references:**

- shell orchestrates all subsystems
- “Start Python backend process with test socket path and nonce”

---

## 2. Authentication and secret access flow

1. The operator interacts with the shell.
2. The shell performs identity/authentication handling, including biometric gating.
3. Secrets are stored and retrieved through **Keychain** on the Swift side.
4. Identity metadata may also use local storage where documented:
   - `display_name` in `UserDefaults`
   - `engineer_id` in Keychain
5. GitHub user identity may be enriched from `/user` on first auth.

This flow is intentionally shell-owned.

---

## 3. Shell ↔ backend communication flow

1. The shell and backend exchange messages through an **authenticated Unix socket**.
2. Messages are encoded as **line-delimited JSON**.
3. Credentials and control information cross the process boundary only through this authenticated channel.
4. Error propagation may occur back through the bridge if the connection is open.

**Documented references:**

- authenticated Unix socket
- line-delimited JSON
- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`
- “Send error via XPC if connection is open”

---

## 4. Operator intent to pull request flow

1. The operator provides a repository, TRDs/specifications, and plain-language intent.
2. The backend assesses confidence in scope.
3. The backend decomposes intent into an **ordered PRD plan**.
4. The backend decomposes the PRD into a sequence of **typed pull requests**.
5. The backend generates implementation and tests using **Claude + GPT-4o** in parallel.
6. **Claude arbitrates** the result.
7. The backend runs:
   - self-correction
   - lint gate
   - iterative fix loop
   - CI
8. The backend opens a **draft PR** for operator review.
9. After approval/merge, the agent proceeds to the next planned PR.

This is the primary product workflow described in the README.

---

## 5. GitHub pull request lifecycle flow

1. The backend creates pull requests as **drafts**.
2. CI runs before the operator sees the final reviewable result.
3. When converting a draft PR to ready-for-review, the system must use the **GraphQL** `markPullRequestReadyForReview` mutation.
4. The system must account for the fact that draft PR merge behavior differs from regular PR behavior, including a documented 405 case.

---

## 6. CI validation flow

1. Changes produced by the backend are validated in CI.
2. Python validation runs in the main Python test job.
3. macOS/Swift validation runs in named macOS jobs, including unit and XPC integration tests.
4. PR presentation is downstream of CI in the README-defined flow.

---

## 7. Project index/cache lifecycle flow

1. When a project is created, an empty index is created under `cache/{project_id}/`.
2. The loaded content indicates the FAISS index is small enough to remain loaded without explicit unload.
3. A change to the embedding model requires re-embedding.

Only these lifecycle points are explicitly supported by the loaded documents here.

## Critical Invariants

The following invariants are directly grounded in the loaded source material.

### 1. Two-process architecture is mandatory

The product is defined as:

- **Swift shell**
- **Python backend**

This split is not optional or interchangeable.

---

### 2. Ownership boundaries are strict

The **Swift shell** owns:

- UI
- authentication
- secrets / Keychain
- orchestration

The **Python backend** owns:

- intelligence
- consensus
- generation pipeline
- GitHub operations

---

### 3. Neither process executes generated code

This is explicitly stated in the repository instructions and is a hard architectural invariant.

---

### 4. IPC must be authenticated

Communication between processes is over an **authenticated** local channel. Trust is not implicit.

This aligns with both the product-specific docs and the architecture rule: **trust must never be inferred implicitly when it can be asserted and verified explicitly.**

---

### 5. IPC message framing is line-delimited JSON

Where the documented Unix socket protocol is used, message framing is **line-delimited JSON**.

---

### 6. Security is governed centrally

**TRD-11 governs all components** for security-relevant changes. Any component that touches credentials, external content, generated code, or CI must conform to that authority.

---

### 7. Draft PRs are part of the product contract

The agent opens **every PR as a draft** in the documented build pipeline. This is not an incidental implementation detail.

---

### 8. Draft-to-ready conversion must use GraphQL

The GitHub integration must not rely on REST `PATCH` with `{"draft": false}` for draft conversion. The loaded lessons-learned document states that GitHub ignores that field and the only supported path is the GraphQL `markPullRequestReadyForReview` mutation.

---

### 9. Consensus requires two providers with Claude arbitration

The README defines a **two-model consensus engine** using **Claude + GPT-4o**, with **Claude arbitrating every result**.

---

### 10. The README workflow stages are architectural, not cosmetic

The documented sequence:

- confidence assessment
- PRD planning
- typed PR decomposition
- dual-provider generation
- self-correction
- lint gate
- iterative fix loop
- CI
- draft PR creation

is part of the product architecture described by the loaded docs.

---

### 11. Distribution is a shell concern

Packaging, installation, and Sparkle auto-update belong to the macOS shell, not the backend.

---

### 12. macOS baseline is fixed by TRD-1

The shell targets **macOS 13.0 (Ventura)** minimum, with **Swift 5.9+** and bundled **Python 3.12**.

---

### 13. Control decisions should remain explicit, explainable, and enforceable

The loaded architecture rules require:

- trust to be explicitly asserted and verified
- identity, policy, telemetry, and enforcement to remain separable but linked
- control decisions to be explainable, observable, and reproducible
- default posture to be enforcement, not suggestion

These rules should be treated as cross-cutting architectural constraints for all subsystems.

---

### 14. TRDs are the source of truth

The repository-level documents state that the 16 TRDs completely specify interfaces, error contracts, state machines, security controls, and performance requirements. Implementation must derive from them rather than undocumented assumptions.