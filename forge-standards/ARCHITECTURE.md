# Architecture

## System Overview (derived from the TRDs above)

**Crafted** is a **native macOS AI coding agent** that builds software autonomously from specifications. The loaded documents define it as a **two-process system**:

- a **Swift macOS application shell**
- a **Python backend**

The repository-level documents are explicit about process ownership:

- **Swift shell** owns **UI, authentication, Keychain secret storage, and XPC/orchestration**
- **Python backend** owns **intelligence, generation, consensus, pipeline, document retrieval, and GitHub operations**

The product is not specified as a chat interface or autocomplete tool. It is specified as a **directed build agent** that takes:

- a repository
- technical specifications, including **TRDs**
- a plain-language intent

It then performs a bounded autonomous workflow that includes:

- confidence assessment
- decomposition into an ordered plan
- decomposition into typed pull requests
- parallel multi-provider generation
- arbitration / consensus
- self-correction
- lint gate
- iterative fix loop
- CI execution
- opening a draft GitHub pull request for operator review

The architecture is constrained by the source documents in several important ways:

1. **Two-process separation is fundamental**  
   The shell and backend are separate processes with distinct responsibilities.

2. **Inter-process communication is authenticated**  
   The documents state that the two processes communicate over an **authenticated Unix socket** using **line-delimited JSON**.

3. **Generated code is never executed by either process**  
   This is stated explicitly in the repository guidance.

4. **The Swift shell is foundational**  
   TRD-1 defines the native shell as the container that packages, installs, authenticates, and orchestrates all subsystems.

5. **The Python document store is a required backend subsystem**  
   TRD-10 defines a Python 3.12 document store and retrieval engine that is required by multiple backend stages.

6. **Security is global and normative**  
   AGENTS.md declares that **TRD-11 governs all components** and must be consulted for any security-relevant work. Its detailed contents are not included in the provided excerpts, so this architecture references it only where the loaded documents explicitly do so.

At minimum from the loaded documents, the system is composed of the following major architectural domains:

- **macOS Application Shell**
- **SwiftUI application/UI layer**
- **identity and authentication**
- **secret storage via Keychain**
- **inter-process bridge / XPC-orchestrated backend startup**
- **authenticated Unix-socket protocol**
- **Python backend intelligence pipeline**
- **consensus engine**
- **document store and retrieval engine**
- **GitHub operations**
- **CI integration**
- **installation and auto-update**

## Subsystem Map (one entry per subsystem found in the docs)

### 1. macOS Application Shell
**Source:** TRD-1, AGENTS.md, CLAUDE.md

The **macOS Application Shell** is the native **Swift/SwiftUI container** for Crafted. TRD-1 states that it specifies the complete technical requirements for the shell and that the shell owns:

- installation and distribution
- identity and authentication
- Swift module architecture
- SwiftUI view hierarchy
- orchestration of subsystems

It is the foundational subsystem on which TRD-2, TRD-3, TRD-4, TRD-5, and TRD-8 depend.

**Technology stated in docs:**
- Swift 5.9+
- SwiftUI
- bundled Python 3.12
- minimum macOS 13.0 (Ventura)

---

### 2. Installation and Distribution
**Source:** TRD-1

TRD-1 explicitly lists installation/distribution as shell-owned, including:

- `.app` bundle packaging
- drag-to-Applications installation
- Sparkle auto-update

This subsystem is part of the Swift shell domain and exists to package and deliver the application on macOS.

---

### 3. Identity and Authentication
**Source:** TRD-1, repository headings

TRD-1 states that the shell owns **identity and authentication**, including:

- biometric gate
- session lifecycle

Repository content also references identity data fields and storage locations, including:

- `display_name` in `UserDefaults`
- `engineer_id` in Keychain
- `github_username` fetched from GitHub `/user` on first auth

This indicates an authentication/identity subsystem anchored in the Swift shell, with GitHub identity enrichment occurring after auth.

---

### 4. Secret Storage / Keychain
**Source:** AGENTS.md, CLAUDE.md, TRD-1, repository headings

The loaded documents state that the Swift process owns **secrets** and **Keychain secret storage**. Repository excerpts also reference:

- `SecretKey.engineerId` in Keychain
- GitHub App private key usage from Keychain for JWT generation

This subsystem is within the shell boundary and is security-sensitive under the global governance of TRD-11.

---

### 5. Swift Module Architecture and Concurrency / State Ownership
**Source:** TRD-1

TRD-1 explicitly includes:

- Swift module architecture
- module boundaries
- concurrency model
- state ownership

This is a shell-internal architectural subsystem defining how the native app is partitioned and how shell-side state is controlled.

---

### 6. SwiftUI View Hierarchy / UI Layer
**Source:** TRD-1, CLAUDE.md

TRD-1 says the shell owns the **SwiftUI view hierarchy**. CLAUDE.md maps SwiftUI views, cards, and panels to TRD-8, establishing a UI-specific subsystem under the shell.

This subsystem is responsible for presenting the operator-facing native interface, but the loaded excerpts do not enumerate every screen or card.

---

### 7. Backend Process Launch and Orchestration
**Source:** AGENTS.md, CLAUDE.md, repository headings

The repository-level documents define a separate **Python backend** and a shell responsibility for orchestration. The loaded headings additionally reference:

- starting the Python backend process with a test socket path and nonce
- error delivery via XPC if the connection is open
- failure modes such as:
  - Swift shell crashed before sending credentials
  - XPC connection failed to establish
  - deadlock in the credential delivery path

This establishes a dedicated orchestration subsystem in the shell for backend process lifecycle and bootstrap.

---

### 8. Inter-Process Communication Layer
**Source:** CLAUDE.md, TRD-10, repository headings

The documents state that the shell and backend communicate via:

- **authenticated Unix socket**
- **line-delimited JSON**

TRD-10 also depends on TRD-1 for **XPC progress messages**, which shows that progress/status reporting participates in shell/backend coordination.

The loaded headings further identify implementation artifacts:

- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`

Together these indicate an IPC subsystem split across both processes.

---

### 9. Python Backend
**Source:** AGENTS.md, CLAUDE.md, README

The Python backend owns:

- intelligence
- generation
- consensus
- pipeline
- GitHub operations

The README further specifies the backend workflow behavior:

- assess confidence in scope
- decompose intent into ordered PRD plan
- decompose PRD into typed pull requests
- generate implementation and tests using two LLM providers in parallel
- run self-correction
- enforce lint gate
- run iterative fix loop
- execute CI
- open draft PR

This subsystem is the autonomous planning and execution engine of Crafted.

---

### 10. Consensus Engine
**Source:** README, AGENTS.md, CLAUDE.md, TRD-10 dependency notes

The README describes Crafted as using a **two-model consensus engine** with:

- Claude
- GPT-4o
- Claude arbitrating every result

AGENTS.md/CLAUDE.md explicitly identify **consensus** as a Python backend responsibility. TRD-10 states that TRD-2 is the **Consensus Engine** and that the document store’s `auto_context()` is called per generation, making the consensus engine a consumer of retrieval context.

This subsystem is therefore responsible for multi-provider generation and arbitration, with document retrieval injected into generation-time context.

---

### 11. Generation / Self-Correction / Fix Pipeline
**Source:** README, AGENTS.md

The README defines a sequenced backend pipeline including:

- generation
- self-correction pass
- lint gate
- iterative fix loop
- CI execution

AGENTS.md states the backend owns the **pipeline**. While the loaded excerpts do not include TRD-3 in full, the architecture clearly contains a dedicated execution pipeline subsystem in Python.

---

### 12. Document Store and Retrieval Engine
**Source:** TRD-10

TRD-10 defines the **Document Store and Retrieval Engine** as a Python 3.12 subsystem. It is responsible for ingesting documents and retrieving context for backend consumers.

Key facts explicitly stated:

- storage path: `~/Library/Application Support/Crafted/cache/{project_id}/`
- depends on:
  - TRD-1 for file layout, project schema, XPC progress messages
  - TRD-2 because consensus consumes injected context
- required by:
  - TRD-2 via `auto_context()` per generation
  - TRD-3 via `doc_filter` in Stage 1/5
  - TRD-6 for review context
  - TRD-7 for `PRODUCT_CONTEXT` auto-load
- project creation behavior:
  - “Project created: empty index created in cache/{project_id}/”
- loaded note:
  - “no explicit unload — FAISS index is small enough to keep all loaded”

This is a distinct backend subsystem with persistent per-project cache state and retrieval-time context assembly.

---

### 13. Review Context / Review Support
**Source:** TRD-10 required-by notes, repository headings

TRD-10 explicitly states it is required by **TRD-6 (review context)**. The repository headings also include operator review command examples such as:

- `/review start`
- `/review exclude`
- selecting lenses
- excluding directories/files

This demonstrates a review-oriented subsystem that consumes document retrieval and applies scoped review operations. The loaded excerpts do not provide the full TRD, so only the existence and document-store dependency can be asserted.

---

### 14. Product Context Auto-Load
**Source:** TRD-10 required-by notes

TRD-10 states it is required by **TRD-7 (`PRODUCT_CONTEXT` auto-load)**. This establishes a subsystem concerned with loading product context into backend workflows, with the document store providing the retrieval foundation.

---

### 15. GitHub Operations
**Source:** AGENTS.md, CLAUDE.md, README, repository headings

The Python backend owns **GitHub** operations. The README specifies outcome-level GitHub behavior:

- opening draft pull requests
- sequencing one PR per logical unit

Repository headings additionally show file-level operations and auth mechanics, including:

- fetch file content from GitHub
- get content + SHA
- read current file from GitHub
- generate JWT using App private key from Keychain
- fetch GitHub `/user` on first auth

This defines a backend GitHub subsystem that depends on shell-managed credentials/secrets.

---

### 16. CI Integration
**Source:** README, repository headings

The README states the system **executes CI** as part of the build pipeline before opening a draft PR. Loaded headings reference CI jobs/workflows such as:

- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- Crafted CI (ubuntu) — main Python test job
- Crafted CI — macOS (Swift) — only triggers for Swift files

This establishes CI as an integrated subsystem in the end-to-end pipeline, though the full CI orchestration TRD text is not included.

---

### 17. Security Governance
**Source:** AGENTS.md, CLAUDE.md

Security is not merely a cross-cutting concern; it is explicitly governed by **TRD-11**. AGENTS.md states:

- “TRD-11 governs all components.”
- It must be read before touching security-relevant code.

CLAUDE.md additionally states:
- neither process ever executes generated code
- communication is authenticated
- secrets belong to the Swift process

Because the full TRD-11 text is not present in the excerpts, this architecture treats security governance as a mandatory controlling layer rather than expanding undocumented controls.

## Component Boundaries (what each subsystem must never do)

This section is restricted to boundaries that are directly supported by the loaded documents.

### macOS Application Shell must never
- implement backend intelligence, consensus, generation, or GitHub operations, because those are assigned to the Python backend by AGENTS.md and CLAUDE.md
- execute generated code, because CLAUDE.md states that neither process ever executes generated code
- delegate ownership of UI, authentication, or secrets to the Python backend, because those are explicitly owned by the Swift process

### Installation and Distribution must never
- assume responsibility for backend intelligence or repository mutation
- bypass the shell, because TRD-1 places installation/distribution inside the shell boundary

### Identity and Authentication must never
- be owned by the Python backend, because authentication is shell-owned in TRD-1
- rely on undocumented secret storage outside shell-controlled mechanisms, because the documents explicitly assign secrets and Keychain storage to the Swift process

### Secret Storage / Keychain must never
- be implemented in the Python backend as a source of truth for application secrets, because the Swift process owns secrets and Keychain storage
- expose private key material as a backend-owned concern, because the headings explicitly show private key use sourced from Keychain

### SwiftUI UI Layer must never
- become the owner of backend planning/generation logic
- bypass shell state ownership and shell module boundaries, because TRD-1 explicitly defines shell state ownership and module architecture

### Backend Process Launch and Orchestration must never
- treat the backend as in-process, because the architecture is explicitly two-process
- omit authentication material for IPC setup, because backend communication is defined as authenticated
- collapse into unauthenticated ad hoc local calls, because the docs define a specific authenticated Unix-socket transport

### Inter-Process Communication Layer must never
- use an undocumented transport in place of the specified one, because CLAUDE.md specifies an authenticated Unix socket with line-delimited JSON
- operate without authentication, because the transport is explicitly authenticated
- be used to execute generated code, because neither process may execute generated code

### Python Backend must never
- own the UI
- own authentication
- own shell-managed secrets
- execute generated code

All four constraints are explicit in the loaded documents.

### Consensus Engine must never
- replace the shell as authentication or secret owner
- operate without document retrieval context where `auto_context()` is required, because TRD-10 states it is called per generation
- be reduced to a single undocumented provider flow; the README explicitly specifies a two-model consensus engine with Claude and GPT-4o and Claude arbitration

### Generation / Self-Correction / Fix Pipeline must never
- skip the defined gated workflow described in README by treating generation as a single unreviewed step
- execute generated code, because neither process may do so

### Document Store and Retrieval Engine must never
- own shell concerns such as authentication, Keychain, or UI
- store outside its specified cache root when implementing its persisted index, because TRD-10 defines storage under `~/Library/Application Support/Crafted/cache/{project_id}/`
- assume explicit unload behavior for indexes, because the loaded notes state no explicit unload and that FAISS indexes are small enough to keep loaded

### Review Context / Review Support must never
- ignore document-store dependency when assembling review context, because TRD-10 explicitly says TRD-6 requires the document store
- exceed the explicit loaded scope by inventing review behaviors not present in the documents

### Product Context Auto-Load must never
- be implemented independently of the document store dependency declared by TRD-10
- redefine backend retrieval ownership away from the document store

### GitHub Operations must never
- own private secret storage, because secret ownership belongs to the Swift shell
- bypass authenticated identity/credential flow sourced from shell-managed storage
- be conflated with local code execution, because the system explicitly does not execute generated code

### CI Integration must never
- be treated as optional in the autonomous pipeline description, because README includes CI execution in the flow before draft PR creation
- redefine shell/backend ownership boundaries; CI is part of the pipeline, not a replacement for process responsibilities

### Security Governance must never
- be inferred informally where the governing TRD exists
- be separated from component implementation decisions in security-relevant areas, because AGENTS.md states TRD-11 governs all components

## Key Data Flows

## 1. Operator intent to autonomous build flow
**Sources:** README, AGENTS.md, CLAUDE.md

1. The operator provides:
   - a repository
   - TRDs / specifications
   - a plain-language intent
2. The backend assesses confidence in scope.
3. The backend decomposes intent into an ordered PRD plan.
4. The backend decomposes each PRD into typed pull requests.
5. The backend performs implementation/test generation using two LLM providers in parallel.
6. The consensus layer arbitrates results, with Claude arbitrating every result per README.
7. The pipeline performs:
   - self-correction
   - lint gate
   - iterative fix loop
   - CI execution
8. The system opens a draft GitHub pull request for operator review.

This is the primary product flow defined in the README.

---

## 2. Shell-to-backend bootstrap and communication flow
**Sources:** CLAUDE.md, repository headings

1. The Swift shell launches the Python backend process.
2. Bootstrap includes transport setup using:
   - Unix socket path
   - authentication material, including a nonce as referenced in headings
3. Shell and backend communicate over an **authenticated Unix socket**.
4. Messages are encoded as **line-delimited JSON**.
5. Progress/status can be surfaced through shell-side bridge/orchestration mechanisms; TRD-10 explicitly references **XPC progress messages**.
6. If the connection remains open, errors can be sent via XPC, as reflected in repository headings.

This flow is central to process separation.

---

## 3. Authentication and credential flow
**Sources:** TRD-1, AGENTS.md, CLAUDE.md, repository headings

1. The shell performs authentication and session lifecycle management.
2. The shell stores secrets in Keychain.
3. Identity fields are persisted using the storage called out in headings:
   - `display_name` in `UserDefaults`
   - `engineer_id` in Keychain
4. GitHub username is obtained from GitHub `/user` on first auth.
5. Backend GitHub operations consume credentials that originate from shell-owned secret storage.
6. Repository headings indicate GitHub App JWT generation uses a private key from Keychain.

The loaded documents therefore define a one-way trust relationship: credentials originate in shell-controlled secure storage and are used to enable backend operations.

---

## 4. Document ingestion and retrieval flow
**Sources:** TRD-10

1. A project is created.
2. An empty retrieval index is created at:
   - `~/Library/Application Support/Crafted/cache/{project_id}/`
3. Documents are ingested into the document store.
4. Retrieval functions provide contextual material to backend consumers.
5. `auto_context()` is called per generation by the consensus engine.
6. `doc_filter` is consumed in Stage 1/5 by TRD-3.
7. Review context (TRD-6) and `PRODUCT_CONTEXT` auto-load (TRD-7) also consume this retrieval layer.
8. FAISS indexes remain loaded; the loaded notes explicitly say there is no explicit unload.

This makes the document store the shared retrieval substrate for multiple backend workflows.

---

## 5. GitHub mutation flow
**Sources:** README, repository headings

1. The system prepares repository changes as part of typed pull request execution.
2. GitHub file content may be read first to obtain content and SHA.
3. The backend uses authenticated GitHub operations.
4. Draft pull requests are opened for operator review.
5. The operator gates, reviews, and merges.
6. The agent proceeds to the next PR while the previous one is being reviewed, per README.

Only the above can be asserted from the provided material.

---

## 6. CI validation flow
**Sources:** README, repository headings

1. Generated changes enter the pipeline validation path.
2. CI is executed before draft PR publication.
3. The repository includes referenced CI jobs for:
   - Python tests
   - macOS unit tests
   - macOS XPC integration tests
4. CI results are part of the gated progression toward draft PR creation.

## Critical Invariants

These are architecture-level invariants directly supported by the loaded documents.

### 1. Crafted is always a two-process system
The architecture is explicitly defined as:

- **Swift shell**
- **Python backend**

This separation is not optional.

### 2. Process responsibilities are fixed by ownership
The **Swift process** owns:

- UI
- authentication
- Keychain / secrets
- orchestration / XPC-related shell responsibilities

The **Python process** owns:

- intelligence
- generation
- consensus
- pipeline
- GitHub operations

No component may violate these ownership assignments.

### 3. IPC is authenticated and uses a specific message format
The shell/backend channel must be:

- an **authenticated Unix socket**
- using **line-delimited JSON**

This is a hard architectural contract stated in CLAUDE.md.

### 4. Generated code is never executed
The repository guidance explicitly states:

- neither process ever executes generated code

This is one of the strongest system-wide invariants.

### 5. The shell is the sole owner of authentication and secrets
Authentication, biometric gate, session lifecycle, and Keychain secret storage all belong to the shell per TRD-1 and repository guidance.

### 6. The Python backend is the sole owner of intelligence and repository automation
Consensus, generation, pipeline behavior, and GitHub operations are backend-owned according to AGENTS.md and CLAUDE.md.

### 7. Document retrieval is a shared backend dependency, not an optional utility
TRD-10 makes the Document Store and Retrieval Engine required by multiple subsystems:

- consensus generation context
- pipeline doc filtering
- review context
- product context auto-load

Therefore retrieval is a core backend dependency.

### 8. Document store persistence is project-scoped and path-constrained
TRD-10 fixes the cache location to:

`~/Library/Application Support/Crafted/cache/{project_id}/`

Project indexing is therefore persistent and project-scoped.

### 9. The shell is foundational for dependent TRDs
TRD-1 is foundational and explicitly required by multiple later TRDs. Shell contracts therefore anchor downstream subsystem behavior.

### 10. Security requirements are centrally governed
AGENTS.md states that **TRD-11 governs all components**. Even where detailed controls are not quoted in the loaded excerpts, the architecture must treat security requirements as centralized and mandatory.

### 11. CI is part of the build pipeline before PR creation
The README includes CI execution in the autonomous workflow before the draft pull request is opened. This makes validation part of the architecture, not a post-hoc add-on.

### 12. Operator review remains part of the system boundary
The README explicitly states:

- the agent opens draft PRs
- the operator gates, reviews, and merges

Therefore autonomy is bounded by human review and merge approval.