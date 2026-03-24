# Architecture

## System Overview

**Crafted** is a native macOS AI coding agent that builds software autonomously from specifications. The repository documents define a **two-process architecture**:

- a **Swift macOS application shell**
- a **Python backend**

This split is explicitly described in the loaded product documents:

- the Swift process owns **UI, authentication, Keychain secret storage, and interprocess orchestration**
- the Python process owns **intelligence, generation, consensus, pipeline execution, document retrieval, and GitHub operations**

The two processes communicate over an **authenticated Unix socket** using **line-delimited JSON**. The shell packages and launches the backend, manages session and credential boundaries, and presents operator state and controls. The backend performs specification-driven planning and implementation work, but per the product definition, **neither process executes generated code**.

At the product level, Crafted is not a chat interface or autocomplete tool. It is a **directed build agent** driven by:

1. a repository
2. technical specifications such as TRDs
3. operator intent

From the README, the end-to-end behavior is:

1. assess confidence in scope
2. decompose intent into an ordered PRD plan
3. decompose each PRD into a sequence of typed pull requests
4. generate implementation and tests using **two LLM providers in parallel**
5. perform a self-correction pass
6. apply a lint gate
7. run an iterative fix loop
8. execute CI
9. open a draft GitHub pull request for operator review

The loaded TRDs establish that the shell is foundational and that additional subsystems depend on it for file layout, project schema, state ownership, and progress transport.

---

## Subsystem Map

The following subsystem list is derived only from the loaded documents and their explicit references.

### 1. macOS Application Shell

**Source:** TRD-1: macOS Application Shell

**Technology:** Swift 5.9+, SwiftUI  
**Platform:** macOS 13.0+  
**Role:** Native container and orchestrator for the entire product.

**Owned responsibilities explicitly stated in TRD-1:**

- installation and distribution
  - `.app` bundle
  - drag-to-Applications
  - Sparkle auto-update
- identity and authentication
  - biometric gate
  - Keychain secret storage
  - session lifecycle
- Swift module architecture
  - module boundaries
  - concurrency model
  - state ownership
- SwiftUI view hierarchy
- orchestration of all subsystems

**Repository-level ownership from AGENTS/CLAUDE:**

- UI
- authentication
- secrets
- XPC / process bridge responsibilities

### 2. Python Backend

**Source:** AGENTS.md, CLAUDE.md, README, TRD dependency references

**Technology:** Python 3.12  
**Role:** Intelligence and execution backend for autonomous software production.

**Owned responsibilities explicitly stated in repository docs:**

- consensus
- generation
- GitHub operations
- pipeline execution

**Implied by TRD references, but still explicit in loaded text:**

- consumer of document retrieval context
- sender/receiver of progress messages via shell-defined transport expectations
- hosted as a separate process started by the shell

### 3. Consensus Engine

**Source:** README, TRD-10 dependency reference, CLAUDE TRD routing table fragment

**Role:** Multi-model decision and generation subsystem.

**Explicit behavior from README:**

- uses **two-model consensus**
- providers named in README: **Claude + GPT-4o**
- **Claude arbitrates every result**

**Explicit dependency from TRD-10:**

- document retrieval calls `auto_context()` **per generation**
- the document store is required by **TRD-2 (Consensus Engine — context injection consumer)**

### 4. Document Store and Retrieval Engine

**Source:** TRD-10: Document Store and Retrieval Engine

**Technology:** Python 3.12  
**Storage root:** `~/Library/Application Support/Crafted/cache/{project_id}/`  
**Role:** Ingests and retrieves project/specification context for generation and review flows.

**Explicit responsibilities from TRD-10 excerpt:**

- ingestion
- storage
- retrieval
- context injection support for generation

**Explicit integration points:**

- depends on TRD-1 for:
  - file layout
  - project schema
  - XPC progress messages
- depends on TRD-2 because the Consensus Engine consumes retrieved context
- required by:
  - TRD-2 via `auto_context()` called per generation
  - TRD-3 via `doc_filter` in Stage 1/5
  - TRD-6 via review context
  - TRD-7 via `PRODUCT_CONTEXT` auto-load

### 5. Planning / PRD Decomposition System

**Source:** README

**Role:** Converts operator intent into a structured implementation plan.

**Explicit behavior:**

- assesses confidence in scope before committing
- decomposes operator intent into an **ordered PRD plan**
- decomposes each PRD into a sequence of **typed pull requests**

### 6. Generation Pipeline

**Source:** README, AGENTS.md, CLAUDE.md

**Role:** Produces implementation artifacts and tests from specifications.

**Explicit stages mentioned in loaded docs:**

- two-provider parallel generation
- self-correction pass
- lint gate
- iterative fix loop
- CI execution
- draft PR creation

### 7. GitHub Operations Subsystem

**Source:** README, AGENTS.md, CLAUDE.md, loaded headings

**Role:** Repository and pull request interaction layer.

**Explicit responsibilities in loaded docs:**

- GitHub operations are owned by the Python backend
- opens draft pull requests
- fetches GitHub user information on first auth
- uses GitHub `/user` endpoint on first auth
- file operations include:
  - reading current file content from GitHub
  - retrieving content + SHA
- explicit headings mention:
  - pushes to main branch
  - content hash computation
  - conflict detection

### 8. Authentication, Identity, and Secret Storage

**Source:** TRD-1, AGENTS.md, CLAUDE.md, loaded headings

**Role:** Maintains operator identity and secures secrets.

**Explicitly owned by the Swift shell:**

- biometric auth
- Keychain secret storage
- session lifecycle
- authentication

**Explicit fields from loaded headings:**

- `display_name` stored in `UserDefaults`
- `engineer_id` stored in Keychain as `SecretKey.engineerId`
- `github_username` fetched from GitHub `/user` endpoint on first auth

### 9. Interprocess Communication Layer

**Source:** CLAUDE.md, TRD-10 dependency notes, loaded headings

**Transport explicitly defined in loaded docs:**

- authenticated Unix socket
- line-delimited JSON

**Explicit related artifacts/headings:**

- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`
- shell starts Python backend process with test socket path and nonce
- XPC progress messages are referenced by TRD-10
- explicit failure headings:
  - deadlock in the credential delivery path
  - Swift shell crashed before sending credentials
  - XPC connection failed to establish

### 10. SwiftUI User Interface

**Source:** TRD-1, CLAUDE.md TRD routing table fragment

**Role:** Native operator-facing interface for project state, orchestration, review flow, and controls.

**Explicit evidence in loaded docs:**

- TRD-1 owns SwiftUI view hierarchy
- CLAUDE routes SwiftUI views, cards, and panels to TRD-8

### 11. Review Context / Review Workflow Support

**Source:** TRD-10 dependency references, loaded headings

**Role:** Supplies contextualized material for operator review and review commands.

**Explicit evidence:**

- TRD-10 is required by TRD-6 for **review context**
- loaded headings include review command examples:
  - `/review start`
  - `/review exclude`
  - lens selection and exclusions

### 12. Product Context Auto-Load

**Source:** TRD-10 dependency references

**Role:** Injects product-level context into backend flows.

**Explicit evidence:**

- TRD-10 is required by TRD-7 for `PRODUCT_CONTEXT` auto-load

### 13. CI Integration

**Source:** README, loaded headings

**Role:** Executes validation before PR creation and supports repository test automation.

**Explicit evidence in loaded docs:**

- pipeline executes CI before opening draft PR
- headings mention:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
  - Crafted CI (ubuntu) main Python test job
  - Crafted CI — macOS (Swift) only triggers for Swift files

### 14. Distribution and Update System

**Source:** TRD-1

**Role:** Delivers and updates the macOS application.

**Explicitly includes:**

- `.app` bundle packaging
- drag-to-Applications installation
- Sparkle auto-update

---

## Component Boundaries

This section states what each subsystem must never do, based strictly on the loaded specifications and explicit ownership statements.

### macOS Application Shell

The shell must never:

- assume responsibility for backend intelligence, consensus, generation, or GitHub operations
- execute generated code
- bypass biometric, session, or Keychain controls for secret handling
- infer trust implicitly where it can be asserted and verified explicitly

This follows from:
- two-process split in AGENTS/CLAUDE
- shell ownership limited to UI, auth, secrets, orchestration
- explicit product statement that neither process executes generated code
- architecture rules requiring explicit trust assertion and verification

### Python Backend

The backend must never:

- own native macOS UI
- own Keychain secret storage
- own biometric authentication
- collapse process boundaries by treating shell-owned identity/session state as its own
- execute generated code

This follows directly from the documented split of responsibilities and the explicit non-execution rule.

### Consensus Engine

The consensus engine must never:

- operate without the document/context injection contract where required
- replace the shell’s authentication or secret boundary
- blur provider roles beyond the documented consensus model

The loaded docs explicitly define:
- two-model consensus
- Claude + GPT-4o participation
- Claude arbitrates every result
- `auto_context()` is called per generation

### Document Store and Retrieval Engine

The document store must never:

- become the source of truth for shell identity, auth, or secrets
- define independent project schema outside the shell-defined layout/schema contracts it depends on
- bypass the context-consumer contracts of dependent systems

This follows from TRD-10 dependencies on TRD-1 and TRD-2 and its explicit scope as a retrieval subsystem.

### GitHub Operations Subsystem

GitHub operations must never:

- own local authentication UX or Keychain storage
- circumvent conflict/content-hash handling where GitHub state is involved
- operate as though repository state is authoritative without fetching current content and SHA when required by the workflow

This follows from the explicit headings for:
- current file fetch from GitHub
- content + SHA retrieval
- conflict detection
- content hash computation

### Authentication / Identity / Secret Storage

This subsystem must never:

- move secret custody into the Python backend
- rely on shell environment initialization behavior not guaranteed by launch context

The loaded headings explicitly note:
- LaunchAgent does not source `.zshrc` or `.bash_profile`

### IPC Layer

The IPC layer must never:

- accept unauthenticated process communication
- abandon line-delimited JSON framing
- hide transport or credential-path failures

This follows from:
- authenticated Unix socket requirement
- line-delimited JSON requirement
- explicit failure cases around credential delivery and connection establishment

### UI Subsystem

The UI must never:

- become the execution engine for generation or GitHub operations
- violate shell state ownership and module boundaries defined by TRD-1
- imply chat-product semantics contradicted by the README

The README explicitly says Crafted is **not a chat interface**.

### CI Integration

CI integration must never:

- replace local shell/backend responsibility for pipeline gating
- be treated as optional in the documented generation pipeline before draft PR creation

The README explicitly includes CI execution before opening a draft PR.

---

## Key Data Flows

### 1. Operator Intent to Pull Request Flow

Derived from README and repository identity docs.

1. Operator provides:
   - repository
   - TRDs/specifications
   - plain-language intent
2. System assesses confidence in scope.
3. Intent is decomposed into an ordered PRD plan.
4. Each PRD is decomposed into a sequence of typed pull requests.
5. Generation runs using two LLM providers in parallel.
6. Consensus/arbitration is applied, with Claude arbitrating every result.
7. Self-correction pass runs.
8. Lint gate runs.
9. Iterative fix loop runs.
10. CI executes.
11. A draft GitHub pull request is opened for operator review.

### 2. Shell-to-Backend Startup and Session Flow

Derived from TRD-1/CLAUDE/loaded headings.

1. Swift shell authenticates operator and manages session lifecycle.
2. Shell accesses secrets via Keychain.
3. Shell starts the Python backend process.
4. Backend communication is established over an authenticated Unix socket.
5. Messages are encoded as line-delimited JSON.
6. Progress and operational status are communicated back through the shell bridge.

Relevant explicit headings include:
- shell starts backend process with test socket path and nonce
- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`

### 3. Credential and Identity Flow

Derived from TRD-1 and loaded headings.

1. Operator identity/authentication is handled in the shell.
2. Biometric gate protects access to sensitive operations.
3. Secrets are stored in Keychain.
4. `display_name` is stored in `UserDefaults`.
5. `engineer_id` is stored in Keychain as `SecretKey.engineerId`.
6. `github_username` is fetched from GitHub `/user` endpoint on first auth.
7. Backend receives only what is needed through the authenticated process boundary.

### 4. Document Ingestion and Retrieval Flow

Derived from TRD-10.

1. A project is created.
2. An empty index is created at `cache/{project_id}/`.
3. Documents/specifications are ingested into the document store.
4. Retrieval produces context for backend consumers.
5. `auto_context()` is called per generation for Consensus Engine use.
6. Retrieval also supports:
   - `doc_filter` in TRD-3 Stage 1/5
   - review context in TRD-6
   - `PRODUCT_CONTEXT` auto-load in TRD-7

### 5. GitHub File Update / Conflict-Aware Flow

Derived from loaded headings.

1. Read current file from GitHub.
2. Retrieve file content and SHA.
3. Compute new content hash.
4. Detect conflicts.
5. Perform GitHub operations using current repository state expectations.

This flow is explicitly supported by headings for:
- read current file from GitHub → get content + SHA
- compute new content hash
- conflict detection

### 6. Review and Exclusion Flow

Derived from loaded headings.

1. Operator starts a review flow.
2. Operator may exclude directories or files before fixing/review processing.
3. Operator may select lenses by comma-separated lens IDs.
4. Review context is supplied by dependent retrieval functionality.

Explicit examples in loaded content include:
- exclude `src/legacy/`
- exclude `src/old_api.py`
- exclude security in `src/vendor/`

### 7. Validation and CI Flow

Derived from README and CI headings.

1. Backend pipeline prepares generated changes.
2. Self-correction and lint gates run.
3. Iterative fix loop runs.
4. CI jobs execute:
   - Python test job
   - macOS unit-test job
   - macOS XPC integration test job
5. Successful validation precedes draft PR creation.

---

## Critical Invariants

These are hard architectural invariants directly supported by the loaded documents.

### 1. Two-process separation is mandatory

Crafted is architected as:

- Swift shell
- Python backend

This boundary is not optional and defines ownership of UI/auth/secrets versus intelligence/generation/GitHub operations.

### 2. The shell owns trust-sensitive local responsibilities

The shell is the owner of:

- UI
- authentication
- biometric gate
- Keychain secret storage
- session lifecycle
- process orchestration

These responsibilities must not migrate into the Python backend.

### 3. The backend owns intelligence and repository automation

The backend is the owner of:

- consensus
- generation
- pipeline execution
- GitHub operations
- retrieval consumers

These responsibilities must not migrate into the shell UI/auth layer.

### 4. IPC must be authenticated and framed as line-delimited JSON

All shell/backend communication must use:

- authenticated Unix socket transport
- line-delimited JSON message framing

No alternative transport is defined in the loaded documents.

### 5. Neither process executes generated code

This is an explicit product constraint in CLAUDE.md and therefore a core architecture invariant.

### 6. Document retrieval is a required upstream dependency for multiple backend flows

The Document Store and Retrieval Engine is not optional support infrastructure. It is explicitly required by:

- Consensus Engine generation context via `auto_context()`
- TRD-3 `doc_filter`
- TRD-6 review context
- TRD-7 `PRODUCT_CONTEXT` auto-load

### 7. CI occurs before draft PR creation

The documented pipeline sequence in the README places CI execution before opening a draft pull request.

### 8. Crafted is not a chat product

Architectural choices must preserve the README-defined product shape:

- not a chat interface
- not code autocomplete
- not a copilot

The system is a directed build agent with plan/decompose/generate/validate/review behavior.

### 9. Trust and enforcement must be explicit

From the loaded architecture rules:

- trust must never be inferred implicitly when it can be asserted and verified explicitly
- identity, policy, telemetry, and enforcement must remain separable but tightly linked
- control decisions must be explainable, observable, and reproducible
- components must default to policy enforcement, not policy suggestion

These rules apply to all subsystem interactions and control points.

### 10. Shell-defined project/file layout contracts constrain dependent subsystems

TRD-10 explicitly depends on TRD-1 for:

- file layout
- project schema
- XPC progress messages

Therefore downstream backend subsystems must conform to shell-owned structural contracts rather than redefining them.

### 11. Secret handling is anchored in platform storage, not process environment assumptions

The loaded docs explicitly tie secrets to Keychain and note that LaunchAgent does not source shell startup files such as `.zshrc` or `.bash_profile`. Architectural decisions must therefore not depend on interactive shell environment initialization for secure operation.

### 12. Provider consensus has fixed documented roles

The README explicitly defines:

- two-model consensus engine
- Claude + GPT-4o
- Claude arbitrates every result

Changes that collapse this into single-provider behavior or alter arbitration semantics would violate the documented architecture.

### 13. Review and fix workflows must support explicit exclusion controls

Loaded review command examples explicitly support file/directory/lens exclusions. Review-related architecture must preserve this operator-controlled filtering capability.

### 14. Distribution and update are shell responsibilities

Application packaging, installation, and Sparkle auto-update belong to the macOS shell and are not backend concerns.

---