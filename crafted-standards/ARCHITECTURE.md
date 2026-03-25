# Architecture

## System Overview

**Product:** Crafted Dev Agent, referred to in the TRDs as **Crafted**.

Crafted is a **native macOS AI coding agent** implemented as a **two-process architecture**:

1. **Swift macOS Application Shell**
2. **Python backend**

This architecture is stated consistently across the repository guidance and product documents:

- AGENTS.md: “Two-process. Swift shell (UI, auth, Keychain, XPC) + Python backend (consensus, pipeline, GitHub).”
- CLAUDE.md: “Two processes. Swift shell + Python backend.”
- README: native macOS build agent that takes TRDs plus operator intent and opens GitHub pull requests through a multi-stage generation and review pipeline.
- TRD-1: the macOS Application Shell is the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems.

### Primary architectural split

The documented responsibility boundary is explicit:

- **Swift process owns**
  - UI
  - authentication
  - secrets / Keychain
  - orchestration
  - XPC / local IPC ownership in repository guidance
  - installation and distribution
  - session lifecycle

- **Python process owns**
  - intelligence
  - generation
  - consensus
  - pipeline execution
  - GitHub operations

### Inter-process communication

CLAUDE.md specifies the transport and message framing:

- Communication is via an **authenticated Unix socket**
- Messages are **line-delimited JSON**

### Global execution constraint

A repository-wide invariant is stated directly in CLAUDE.md:

- **Neither process ever executes generated code.**

### Product-level operational model

From README, Crafted operates as a directed build system rather than a chat interface:

1. Operator loads TRDs/specifications
2. Operator states intent
3. Agent assesses confidence in scope
4. Agent decomposes intent into an ordered PRD plan
5. Agent decomposes each PRD into typed pull requests
6. Agent generates implementation and tests using **two LLM providers in parallel**
7. Claude arbitrates results
8. Agent runs self-correction, lint gate, iterative fix loop, and CI
9. Agent opens a **draft PR** for operator review
10. After approval/merge, agent proceeds to the next PR

This is the system behavior the architecture must support.

---

## Subsystem Map

Only subsystems explicitly present in the loaded documents are listed.

### 1. macOS Application Shell

**Source:** TRD-1, AGENTS.md, CLAUDE.md

**Implementation domain:** Swift 5.9+, SwiftUI

**Purpose:** Native container and orchestrator for the product.

**Documented responsibilities:**
- package and install the application
- distribute as `.app`
- support drag-to-Applications install flow
- support Sparkle auto-update
- own identity and authentication
- own biometric gate
- own Keychain secret storage
- own session lifecycle
- own UI
- orchestrate all subsystems

**Depends on:** None in TRD-1; it is foundational.

---

### 2. SwiftUI User Interface

**Source:** AGENTS.md, CLAUDE.md, TRD-1, README

**Implementation domain:** SwiftUI in the Swift shell

**Purpose:** Native operator-facing interface for the macOS application.

**Documented responsibilities:**
- present the product’s native macOS UI
- support operator review/gating workflow implied by README
- host views, cards, and panels as referenced in CLAUDE.md
- surface shell-owned state such as auth/session/orchestration status

This is not described as a separate process; it is a shell subsystem.

---

### 3. Authentication and Identity Subsystem

**Source:** TRD-1, AGENTS.md, README

**Implementation domain:** Swift shell

**Purpose:** Establish and protect operator identity/session.

**Documented responsibilities:**
- biometric gate
- authentication
- identity ownership
- session lifecycle

**Related persisted fields explicitly mentioned in source content:**
- `display_name`: stored in `UserDefaults`
- `engineer_id`: stored as `SecretKey.engineerId` in Keychain
- `github_username`: fetched from GitHub `/user` endpoint on first auth

---

### 4. Secrets and Keychain Storage

**Source:** AGENTS.md, CLAUDE.md, TRD-1, GitHub lessons document

**Implementation domain:** Swift shell

**Purpose:** Secure secret custody.

**Documented responsibilities:**
- own secrets
- store credentials in Keychain
- hold GitHub App private key in Keychain for JWT generation when applicable

This subsystem is explicitly shell-owned.

---

### 5. Local IPC / Backend Bridge

**Source:** AGENTS.md, CLAUDE.md, loaded headings mentioning `Crafted/XPCBridge.swift` and `src/xpc_server.py`

**Implementation domain:** Swift shell + Python backend boundary

**Purpose:** Connect the shell and backend.

**Documented responsibilities and characteristics:**
- authenticated local process-to-process communication
- authenticated Unix socket transport
- line-delimited JSON protocol
- credential delivery path exists and has failure modes noted in docs
- bridge-related implementation files are explicitly referenced:
  - `Crafted/XPCBridge.swift`
  - `src/xpc_server.py`

**Observed documented failure cases:**
- deadlock in the credential delivery path
- Swift shell crashed before sending credentials
- XPC connection failed to establish
- send error via XPC if connection is open
- start Python backend process with test socket path and nonce

Because both “XPC” and “authenticated Unix socket” appear in the loaded material, the safe architectural statement is:
- the shell/backend bridge is a local authenticated IPC subsystem, with explicit bridge files in Swift and Python, and the repository guidance treats this boundary as part of the shell/backend split.

---

### 6. Python Backend

**Source:** AGENTS.md, CLAUDE.md, README, TRD-1 dependencies context

**Implementation domain:** Python 3.12 (bundled)

**Purpose:** All intelligence and automation logic not owned by the shell.

**Documented responsibilities:**
- consensus
- generation
- pipeline
- GitHub operations
- intelligence

The backend is subordinate to shell orchestration and must communicate only through the authenticated local bridge.

---

### 7. Consensus Engine

**Source:** README, CLAUDE.md, AGENTS.md

**Implementation domain:** Python backend

**Purpose:** Multi-model generation and arbitration.

**Documented responsibilities:**
- use two LLM providers in parallel
- specifically referenced providers in README:
  - Claude
  - GPT-4o
- Claude arbitrates every result
- produce implementation and tests as inputs to later pipeline stages

This is explicitly backend-owned.

---

### 8. Provider Adapter Layer

**Source:** CLAUDE.md snippet referencing `ConsensusEngine, ProviderAdapter`

**Implementation domain:** Python backend

**Purpose:** Provider-facing abstraction supporting consensus generation.

**Documented role:**
- support backend intelligence components associated with consensus/provider interaction

Only the existence of this subsystem is explicit in loaded source; no further behavior should be inferred beyond its role in provider integration.

---

### 9. Planning and Decomposition Pipeline

**Source:** README

**Implementation domain:** Python backend

**Purpose:** Convert operator intent and specifications into executable delivery units.

**Documented responsibilities:**
- assess confidence in scope before committing
- decompose intent into an ordered PRD plan
- decompose each PRD into a sequence of typed pull requests

This is part of the backend pipeline.

---

### 10. Self-Correction and Quality Gates Pipeline

**Source:** README

**Implementation domain:** Python backend

**Purpose:** Refine generated changes before PR creation.

**Documented responsibilities:**
- self-correction pass
- lint gate
- iterative fix loop

This subsystem exists as part of the backend pipeline.

---

### 11. CI Integration Subsystem

**Source:** README, loaded headings

**Implementation domain:** pipeline/backend with repository CI workflows

**Purpose:** Validate generated work before operator review.

**Documented responsibilities and referenced jobs:**
- execute CI before opening PR
- interact with repository CI jobs including:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
  - Crafted CI (ubuntu) — main Python test job
  - Crafted CI — macOS (Swift) — only triggers for Swift files

This subsystem is part of the delivery pipeline rather than the shell.

---

### 12. GitHub Integration Subsystem

**Source:** AGENTS.md, CLAUDE.md, README, GitHub-Integration-Lessons-Learned

**Implementation domain:** Python backend

**Purpose:** Repository automation and pull-request lifecycle management.

**Documented responsibilities:**
- GitHub operations are backend-owned
- open one PR per logical unit
- open every PR as a **draft** so CI can run before operator review
- perform file/repository interactions through GitHub APIs
- use GraphQL where required by GitHub behavior

**Explicit GitHub API requirements from the lessons-learned document:**
- `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}` does **not** convert draft to ready-for-review
- must use GraphQL `markPullRequestReadyForReview`
- draft PR lifecycle differs from regular PR lifecycle
- merging a draft PR returns `405`
- API behavior around file update flow includes:
  1. read current file from GitHub to get content + SHA
  2. fetch file content from GitHub
  3. compute new content hash
- JWT generation using App private key from Keychain is part of GitHub App auth flows when applicable

---

### 13. Installation and Update Subsystem

**Source:** TRD-1

**Implementation domain:** Swift shell

**Purpose:** Native macOS distribution and update mechanics.

**Documented responsibilities:**
- `.app` bundle packaging
- drag-to-Applications installation
- Sparkle auto-update

---

### 14. Session Management Subsystem

**Source:** TRD-1, loaded headings

**Implementation domain:** Swift shell

**Purpose:** Govern authenticated runtime continuity.

**Documented responsibilities:**
- session lifecycle ownership
- enforce session-related constraints referenced in source content, including:
  - “OI-13 session limit: blocks generation if session token total exceeded”

Only the existence of this enforcement point is explicit from loaded text; no further semantics should be invented.

---

## Component Boundaries

This section states only boundaries directly supported by the loaded materials.

### macOS Application Shell must never do

Because the shell/backend split is explicit, the shell must not assume backend-owned responsibilities.

The shell must never:
- own consensus logic
- own generation logic
- own GitHub operations
- execute the intelligence pipeline in place of the backend
- execute generated code

### Python Backend must never do

By explicit ownership split, the backend must never:
- own the native macOS UI
- own authentication
- own biometric gating
- own Keychain secret storage
- bypass shell ownership of secrets/session
- execute generated code

### UI subsystem must never do

Derived from shell/backend ownership:
- must not directly own secrets
- must not directly perform backend intelligence tasks
- must not directly perform GitHub automation outside shell-orchestrated/backend-owned paths

### Authentication / Identity subsystem must never do

Derived from stated scope:
- must not delegate secret custody away from shell-owned storage
- must not perform backend intelligence/generation duties
- must not execute generated code

### Secrets / Keychain subsystem must never do

Derived from explicit shell ownership and security model:
- must not expose raw secrets as general backend-owned state
- must not transfer secret ownership to the Python backend
- must not bypass the shell’s authentication/session controls

### Local IPC / Backend Bridge must never do

Derived from communication contract:
- must not operate as an unauthenticated channel
- must not use arbitrary framing; the documented protocol is line-delimited JSON
- must not allow either side to bypass declared ownership boundaries
- must not execute generated code during transport or validation

### Python backend and consensus/provider subsystems must never do

Derived from ownership and README behavior:
- must not merge shell/UI/auth concerns into backend logic
- must not bypass quality gates and CI when opening PRs
- must not skip arbitration where the product defines two-model consensus with Claude arbitrating
- must not execute generated code

### GitHub integration subsystem must never do

Derived from README and GitHub lessons:
- must not treat a draft PR as a regular PR lifecycle object
- must not rely on REST `PATCH` with `{"draft": false}` to mark ready for review
- must not attempt to merge a draft PR directly
- must not assume undocumented GitHub API behavior contrary to discovered production behavior

### Installation / Update subsystem must never do

Derived from TRD-1 scope:
- must not absorb backend intelligence functions
- must not bypass shell authentication and security controls
- must not alter process boundaries defined by the product architecture

---

## Key Data Flows

## 1. Operator intent to draft pull request

**Source basis:** README, AGENTS.md, CLAUDE.md

1. Operator provides repository, TRDs/specifications, and plain-language intent.
2. The system assesses confidence in scope.
3. The backend decomposes intent into an ordered PRD plan.
4. The backend decomposes each PRD into a sequence of typed pull requests.
5. The backend runs two-model generation in parallel.
6. Claude arbitrates the result.
7. The backend runs:
   - self-correction pass
   - lint gate
   - iterative fix loop
   - CI
8. The GitHub integration subsystem opens a **draft PR** for operator review.
9. After approval/merge, the agent proceeds to the next PR while the operator reviews prior output.

## 2. Shell-to-backend control flow

**Source basis:** AGENTS.md, CLAUDE.md, TRD-1, loaded headings

1. Swift shell authenticates operator and owns session.
2. Shell starts/orchestrates backend process.
3. Shell and backend communicate over an authenticated local IPC channel.
4. Messages are line-delimited JSON over an authenticated Unix socket per CLAUDE.md.
5. Test/integration flows may start backend with a test socket path and nonce.
6. If connection remains open and an error occurs, error is sent via the bridge.

## 3. Secret and credential custody flow

**Source basis:** TRD-1, AGENTS.md, CLAUDE.md, loaded headings, GitHub lessons

1. Shell stores secrets in Keychain.
2. Shell owns authentication and identity state.
3. Backend receives only what is needed through the authenticated local bridge.
4. GitHub App auth flows, where used, require JWT generation using private key material from Keychain.
5. Credential delivery path is sensitive and explicitly known to have failure modes:
   - deadlock in credential delivery path
   - shell crash before credential send
   - connection establishment failure

## 4. GitHub pull request lifecycle flow

**Source basis:** README, GitHub lessons

1. Backend prepares repository changes.
2. CI runs before the operator sees the PR.
3. Backend opens PR as **draft**.
4. To convert draft to ready for review, the system must use GraphQL `markPullRequestReadyForReview`.
5. The system must not rely on REST patching of the `draft` field.
6. Draft PR cannot be merged directly; attempting to merge returns `405`.

## 5. File update flow against GitHub

**Source basis:** GitHub lessons

1. Read current file from GitHub to obtain content and SHA.
2. Fetch file content from GitHub.
3. Compute new content hash.
4. Proceed through GitHub update flow using current remote state.

Only these explicit steps are included.

## 6. Identity/profile persistence flow

**Source basis:** loaded headings

1. `display_name` is stored in `UserDefaults`.
2. `engineer_id` is stored in Keychain as `SecretKey.engineerId`.
3. `github_username` is fetched from GitHub `/user` endpoint on first auth.

---

## Critical Invariants

These are architecture-level invariants explicitly supported by the loaded documents.

### 1. Two-process separation is mandatory

Crafted is a **two-process** system:
- Swift shell
- Python backend

The shell/backend split is not optional and defines ownership boundaries.

### 2. Ownership boundaries are strict

- Swift shell owns UI, auth, Keychain/secrets, session/orchestration.
- Python backend owns intelligence, generation, consensus, pipeline, GitHub operations.

No subsystem may silently absorb responsibilities assigned to the other side.

### 3. Local communication must be authenticated

The shell and backend communicate over an **authenticated** local channel.

At minimum, the architecture requires:
- authenticated Unix socket communication
- line-delimited JSON framing

### 4. Generated code is never executed

This is an explicit product-wide rule:
- neither process ever executes generated code

Any component that would run generated artifacts directly violates the documented architecture.

### 5. Draft PRs are the default review artifact

The product opens PRs as **drafts** so CI can run before operator review.

This behavior is part of the product model and GitHub integration architecture.

### 6. GitHub draft-state transitions must follow discovered API behavior

From the loaded GitHub lessons document:
- REST patching `draft: false` is not a valid way to make a PR ready for review
- GraphQL `markPullRequestReadyForReview` is required
- draft PRs cannot be merged directly

These are operational invariants for the GitHub subsystem.

### 7. Secret custody remains in the shell

Secrets and identity-critical material are shell-owned, with Keychain explicitly named as the storage boundary.

The backend may participate in authenticated workflows but is not the system of record for secret custody.

### 8. Security requirements are cross-cutting and governed externally

AGENTS.md states:
- “TRD-11 governs all components.”
- It must be read before touching security-relevant code.

Therefore the architecture must treat security as a global constraint across all subsystems, not as a local property of a single component.

### 9. The shell is foundational

TRD-1 states the macOS Application Shell is foundational and required by multiple other TRDs.

Architecturally, this means packaging, auth, secret custody, native UI, and orchestration originate from the shell layer.

### 10. CI is part of the delivery architecture, not an optional afterthought

README explicitly includes CI execution before draft PR creation, and the repository contains distinct Python and macOS CI jobs.

Therefore:
- validation is a first-class architectural stage
- backend/pipeline/GitHub flow must account for CI outcomes before review handoff

### 11. Operator review remains an explicit gate

README describes a gated workflow:
- the system opens PRs
- the operator reviews, gates, approves, and merges

The architecture therefore preserves a human review boundary rather than autonomous direct integration into main.