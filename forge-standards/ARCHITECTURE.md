# Architecture

## System Overview

**Product:** Crafted Dev Agent / Crafted  
**Platform:** Native macOS application  
**Minimum macOS:** 13.0 (Ventura)  
**Implementation languages called out in the loaded documents:** Swift 5.9+, SwiftUI, Python 3.12

Crafted is a **two-process macOS AI coding agent**. The architecture is explicitly split into:

1. **Swift shell**
2. **Python backend**

The loaded documents define this split consistently:

- **Swift shell** owns:
  - UI
  - authentication
  - Keychain secret storage
  - installation/distribution concerns
  - session lifecycle
  - orchestration
  - XPC-related shell responsibilities
- **Python backend** owns:
  - consensus
  - generation/intelligence
  - pipeline execution
  - GitHub operations
  - document ingestion/retrieval

The two processes communicate using an **authenticated Unix socket with line-delimited JSON**.

A core product constraint stated in the source documents is:

- **Neither process ever executes generated code.**

Operationally, the product takes a repository, technical specifications (TRDs), and user intent; it assesses confidence, derives an ordered plan, decomposes work into typed pull requests, generates implementation and tests using multiple LLM providers in parallel, performs self-correction, lint/fix loops, executes CI, and opens draft pull requests for review.

The TRDs are the source of truth for all interfaces, error contracts, state machines, security controls, and performance requirements. The loaded documents explicitly identify **TRD-11** as governing all security-relevant components.

---

## Subsystem Map

This section lists each subsystem explicitly found in the loaded documents only.

### 1. macOS Application Shell
**Source:** TRD-1  
**Type:** Swift/SwiftUI native shell

**Purpose in the docs:**
The native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems of Crafted.

**Responsibilities explicitly listed:**
- Installation and distribution
  - `.app` bundle
  - drag-to-Applications
  - Sparkle auto-update
- Identity and authentication
  - biometric gate
  - Keychain secret storage
  - session lifecycle
- Swift module architecture
  - module boundaries
  - concurrency model
  - state ownership
- SwiftUI view hierarchy

**Declared dependency position:**
- Foundational TRD
- Required by TRD-2, TRD-3, TRD-4, TRD-5, TRD-8

---

### 2. Python Backend
**Source:** AGENTS.md, CLAUDE.md, README  
**Type:** Python 3.12 backend process

**Responsibilities explicitly listed across loaded docs:**
- consensus
- intelligence
- generation
- pipeline
- GitHub operations

**Communication model:**
- Authenticated Unix socket
- Line-delimited JSON

**Key behavioral constraints:**
- Must not execute generated code

---

### 3. Consensus Engine
**Source:** README, TRD-10 dependency references, CLAUDE excerpt  
**Type:** Python backend subsystem

**Purpose in the docs:**
- Uses two-model consensus
- Claude + GPT-4o run in parallel
- Claude arbitrates every result

**Known integrations from loaded docs:**
- Consumes document retrieval context from TRD-10 via `auto_context()`
- Referenced together with `ProviderAdapter`

**Functional position in product flow:**
- Participates in implementation/test generation and arbitration before downstream correction/gating stages

---

### 4. Provider Adapter
**Source:** CLAUDE excerpt  
**Type:** Python backend subsystem

**Only directly supported statement from loaded docs:**
- It is named as an implementation area alongside `ConsensusEngine`

No further behavior should be inferred beyond its existence as a distinct component area in the backend.

---

### 5. Pipeline
**Source:** AGENTS.md, README  
**Type:** Python backend subsystem

**Responsibilities explicitly stated:**
- Owns pipeline behavior
- Performs staged autonomous build flow including:
  - scope/confidence assessment
  - decomposition into ordered PRD plan
  - decomposition into typed pull requests
  - generation of implementation and tests
  - self-correction pass
  - lint gate
  - iterative fix loop
  - CI execution
  - draft PR opening

---

### 6. GitHub Operations
**Source:** AGENTS.md, CLAUDE.md, README, loaded heading fragments  
**Type:** Python backend subsystem

**Responsibilities explicitly stated or directly evidenced:**
- Owns GitHub operations
- Opens pull requests
- Fetches `/user` endpoint on first auth
- Reads current file content from GitHub and obtains content + SHA
- Pushes to main branch is listed as a heading fragment in the loaded content
- Uses GitHub App authentication flow indicated by:
  - generate JWT using App private key from Keychain

Because the shell owns Keychain, any use of key material must respect that boundary.

---

### 7. Document Store and Retrieval Engine
**Source:** TRD-10  
**Type:** Python backend subsystem

**Purpose in the docs:**
A subsystem that ingests documents and supports retrieval for generation/review context.

**Language:** Python 3.12  
**Storage location:** `~/Library/Application Support/Crafted/cache/{project_id}/`

**Declared dependencies:**
- TRD-1 for:
  - file layout
  - project schema
  - XPC progress messages
- TRD-2 for:
  - context injection consumer

**Required by:**
- TRD-2: `auto_context()` called per generation
- TRD-3: `doc_filter` in Stage 1/5
- TRD-6: review context
- TRD-7: `PRODUCT_CONTEXT` auto-load

**Lifecycle/storage facts explicitly given:**
- Project created: empty index created in `cache/{project_id}/`
- “no explicit unload — FAISS index is small enough to keep all loaded”
- “10 projects = ~3MB total — negligible”

---

### 8. SwiftUI View System
**Source:** TRD-1, AGENTS.md, CLAUDE excerpt  
**Type:** Swift shell subsystem

**Responsibilities explicitly stated:**
- SwiftUI view hierarchy
- UI panels/cards
- Root UI ownership resides in the shell

This subsystem is part of the shell and not a separate process.

---

### 9. Authentication and Identity
**Source:** TRD-1, AGENTS.md, CLAUDE.md, loaded heading fragments  
**Type:** Swift shell subsystem

**Responsibilities explicitly stated:**
- biometric gate
- Keychain secret storage
- session lifecycle
- authentication

**Specific identity/secret facts present in loaded content:**
- `display_name`: stored in UserDefaults
- `engineer_id`: stored as `SecretKey.engineerId` in Keychain
- `github_username`: fetched from GitHub `/user` endpoint on first auth

---

### 10. Secrets and Keychain Management
**Source:** TRD-1, CLAUDE.md, loaded heading fragments  
**Type:** Swift shell subsystem

**Responsibilities explicitly stated:**
- Swift process owns secrets
- Keychain secret storage
- GitHub App private key is in Keychain

This is a distinct boundary-critical responsibility within the shell.

---

### 11. XPC / Bridge / Interprocess Transport Layer
**Source:** AGENTS.md, TRD-1, TRD-10 dependency notes, loaded heading fragments  
**Type:** Cross-process interface area

**Direct evidence in loaded docs:**
- Swift shell architecture includes XPC responsibilities
- `Crafted/XPCBridge.swift` (Swift)
- `src/xpc_server.py` (Python)
- TRD-10 depends on XPC progress messages from TRD-1
- Possible failure conditions listed:
  - deadlock in credential delivery path
  - Swift shell crashed before sending credentials
  - XPC connection failed to establish

**Transport fact that is explicit in CLAUDE.md:**
- Processes communicate via an authenticated Unix socket with line-delimited JSON

Because both XPC artifacts and Unix-socket transport are present in the loaded material, the safe architectural statement is that cross-process coordination/bridging exists and is security-sensitive; exact layering beyond that should remain TRD-defined.

---

### 12. Installation, Packaging, and Update System
**Source:** TRD-1, loaded heading fragments  
**Type:** Swift shell subsystem

**Responsibilities explicitly stated:**
- `.app` bundle packaging
- drag-to-Applications install
- Sparkle auto-update
- Developer ID signing context is evidenced by:
  - `Developer ID Application: YouSource.ai ({TEAM_ID})`

---

### 13. CI Integration
**Source:** README, loaded heading fragments  
**Type:** Product workflow/integration subsystem

**Explicitly referenced jobs/workflows:**
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- `Crafted CI (ubuntu) — main Python test job`
- `Crafted CI — macOS (Swift) — only triggers for Swift files`

**Functional role from README:**
- CI is executed as part of the autonomous pipeline before a draft PR is opened.

---

## Component Boundaries

This section states what each subsystem must never do, using only boundaries explicitly supported by the loaded documents.

### macOS Application Shell must never
- Implement backend intelligence, consensus, generation, or GitHub operations that the documents assign to the Python backend
- Execute generated code
- Infer trust implicitly where it can be asserted and verified explicitly

### Python Backend must never
- Own UI
- Own authentication
- Own Keychain secret storage
- Execute generated code
- Bypass the authenticated interprocess communication contract

### SwiftUI View System must never
- Become the source of truth for backend pipeline, consensus, or GitHub behavior
- Handle secrets outside the shell’s explicit authentication/Keychain ownership model

### Authentication and Identity subsystem must never
- Store Keychain-owned secrets outside the shell-controlled secret storage model
- Collapse session, identity, and secret responsibilities into backend-owned logic
- Weaken the biometric gate/session lifecycle controls defined by TRD-1 and TRD-11

### Secrets and Keychain Management must never
- Transfer secret ownership to the Python backend
- Assume shell/backend trust without explicit authenticated exchange
- Allow generated code execution as part of any secret-handling workflow

### Consensus Engine must never
- Own UI/auth/Keychain concerns
- Substitute for the retrieval subsystem’s responsibility to provide context
- Violate the documented arbitration model stated in the README

### Provider Adapter must never
- Expand into shell responsibilities
- Bypass consensus/arbitration and transport/security contracts defined elsewhere in the TRDs

### Pipeline must never
- Execute generated code
- Bypass lint, self-correction, fix-loop, or CI stages that are explicitly part of the documented flow
- Replace explicit operator review/approval with implicit merge authority

### GitHub Operations must never
- Own Keychain or biometric authentication
- Read or use credentials outside the shell-controlled authentication/secret model
- Bypass repository state checks such as file content/SHA interactions evidenced in the loaded docs

### Document Store and Retrieval Engine must never
- Replace the consensus engine
- Assume ownership of shell concerns such as UI, auth, installation, or Keychain
- Store project cache outside the documented application-support cache path
- Omit per-generation context injection where TRD-10 says `auto_context()` is required

### XPC / Bridge / Interprocess Transport must never
- Operate without authentication
- Violate the line-delimited JSON transport contract stated in the loaded docs
- Deadlock or silently fail credential delivery without surfacing error paths
- Blur process ownership boundaries between shell and backend

### Installation / Packaging / Update System must never
- Redefine runtime ownership boundaries between shell and backend
- Bypass signing/update controls implied by Developer ID and Sparkle-based distribution

### CI Integration must never
- Be treated as optional in the documented PR production flow
- Blur the distinction between macOS Swift test jobs and Python test jobs where the loaded docs explicitly separate them

---

## Key Data Flows

## 1. User intent to draft PR flow
Derived from the README product flow.

1. Operator provides:
   - repository
   - TRDs/specifications
   - plain-language intent
2. System assesses confidence in scope
3. System decomposes intent into an ordered PRD plan
4. System decomposes each PRD into a sequence of typed pull requests
5. Python backend generates implementation and tests using two LLM providers in parallel
6. Consensus/arbitration occurs
7. Self-correction pass runs
8. Lint gate runs
9. Iterative fix loop runs
10. CI executes
11. Draft pull request is opened for review
12. After approval, subsequent work continues

## 2. Shell-to-backend control flow
Derived from AGENTS.md and CLAUDE.md.

1. Swift shell orchestrates subsystems
2. Python backend performs intelligence/generation/pipeline/GitHub work
3. Communication occurs over an authenticated Unix socket
4. Message framing is line-delimited JSON

## 3. Authentication and credential flow
Derived from TRD-1 and loaded heading fragments.

1. Swift shell owns authentication
2. Biometric gate controls access
3. Secrets are stored in Keychain
4. Session lifecycle is maintained in the shell
5. Identity attributes include:
   - `display_name` in UserDefaults
   - `engineer_id` in Keychain
   - `github_username` fetched from GitHub on first auth
6. If GitHub App authentication is used, JWT generation relies on App private key material from Keychain

## 4. Document ingestion and retrieval flow
Derived from TRD-10.

1. Project is created
2. Empty index is created in `~/Library/Application Support/Crafted/cache/{project_id}/`
3. Document store ingests project/spec content
4. Retrieval context is supplied to generation via `auto_context()`
5. TRD-3 Stage 1/5 can consume `doc_filter`
6. TRD-6 consumes retrieval output for review context
7. TRD-7 consumes retrieval output for `PRODUCT_CONTEXT` auto-load

## 5. GitHub file operation flow
Derived from loaded heading fragments.

1. Read current file from GitHub
2. Obtain content + SHA
3. Compute new content hash
4. Use GitHub credentials/auth flow mediated by shell-owned secrets

## 6. Error signaling / bridge flow
Derived from loaded heading fragments.

1. Start Python backend process with socket path and nonce
2. If connection is open, send error via XPC
3. Failure conditions explicitly identified include:
   - XPC connection failed to establish
   - Swift shell crashed before sending credentials
   - deadlock in credential delivery path

## 7. CI verification flow
Derived from README and workflow headings.

1. Pipeline reaches CI phase
2. Python CI jobs run
3. macOS Swift unit tests run where applicable
4. macOS XPC integration tests run where applicable
5. Results gate draft PR creation in the documented workflow

---

## Critical Invariants

These are the strongest architecture-level invariants directly supported by the loaded documents.

1. **Crafted is a two-process system.**  
   The architecture is split into a Swift shell and a Python backend.

2. **Process ownership is strict.**  
   - Swift shell owns UI, authentication, and secrets/Keychain.
   - Python backend owns intelligence, generation, consensus/pipeline, and GitHub operations.

3. **Generated code is never executed.**  
   This applies to both processes.

4. **Interprocess communication is authenticated.**  
   The documented transport is an authenticated Unix socket using line-delimited JSON.

5. **Security is centralized by TRD-11.**  
   Any component touching credentials, external content, generated code, or CI is governed by the security model in TRD-11.

6. **The shell is the only owner of secret material.**  
   The backend may consume authenticated capabilities/workflows but does not own Keychain storage.

7. **Document retrieval is part of generation-time context assembly.**  
   TRD-10 requires `auto_context()` per generation and defines downstream consumers in TRD-2, TRD-3, TRD-6, and TRD-7.

8. **Document store data location is fixed.**  
   Retrieval cache is stored under `~/Library/Application Support/Crafted/cache/{project_id}/`.

9. **The autonomous build flow is gated, not freeform.**  
   The documented path includes confidence assessment, planning, decomposition, generation, self-correction, lint, iterative fixing, CI, and draft PR creation.

10. **Operator review remains part of the workflow.**  
    The README states draft PRs are opened for review and approval.

11. **Trust must be explicit and verifiable.**  
    This is reinforced by the loaded architecture rules: trust must never be inferred implicitly when it can be asserted and verified explicitly.

12. **Control decisions must be explainable, observable, and reproducible.**  
    This applies across identity, policy, telemetry, and enforcement according to the architecture rules included in the loaded content.

13. **Components must default to enforcement, not suggestion.**  
    The architecture rules explicitly require policy enforcement by default.

14. **Transport and credential delivery are failure-sensitive paths.**  
    The loaded documents explicitly call out:
    - XPC connection establishment failure
    - shell crash before credential delivery
    - deadlock in credential delivery path

15. **CI is part of the production architecture, not an external afterthought.**  
    The documented product flow includes CI before draft PR creation, and separate Python/macOS jobs are explicitly identified.