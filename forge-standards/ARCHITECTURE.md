# Architecture

## System Overview

**Product:** Crafted Dev Agent / Crafted

Crafted is a **native macOS AI coding agent** that autonomously builds software from specifications. The product is explicitly **not** a chat interface, code autocomplete tool, or copilot. The operating model described in the source documents is:

1. The operator provides:
   - a repository,
   - a set of technical specifications (**TRDs**),
   - a plain-language intent.
2. The agent:
   - assesses confidence in scope,
   - decomposes intent into an ordered **PRD plan**,
   - decomposes each PRD into a sequence of **typed pull requests**,
   - generates implementation and tests using **two LLM providers in parallel**,
   - applies a **self-correction pass**,
   - runs a **lint gate** and **iterative fix loop**,
   - executes **CI**,
   - opens a **draft GitHub pull request** for review.
3. The operator gates, reviews, and merges.
4. The agent proceeds to the next pull request while the previous one is under review.

The architecture is a strict **two-process system**:

- **Swift shell**
  - owns UI,
  - authentication,
  - secrets / Keychain,
  - process orchestration,
  - XPC / local IPC-facing shell responsibilities.
- **Python backend**
  - owns intelligence,
  - consensus,
  - generation pipeline,
  - document retrieval,
  - GitHub operations.

The two processes communicate over an **authenticated Unix socket** using **line-delimited JSON**. The documents are explicit that **neither process ever executes generated code**.

The loaded TRDs establish the following architecture anchors:

- **TRD-1** defines the **macOS Application Shell** as the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems.
- **TRD-10** defines the **Document Store and Retrieval Engine** as a Python subsystem that ingests and retrieves project documents, with storage under `~/Library/Application Support/Crafted/cache/{project_id}/`.
- Repository-level docs define the existence of:
  - a **two-model consensus engine** using **Claude + GPT-4o**, with **Claude arbitrating every result**,
  - a **GitHub PR production flow**,
  - a **security model governed by TRD-11**,
  - CI jobs spanning Python and macOS/Swift validation.

Per the repository guidance, the **16 TRDs in `forge-docs/` are the source of truth**. This architecture summary is therefore limited to what is explicitly present in the provided documents.

---

## Subsystem Map

### 1. macOS Application Shell
**Source:** TRD-1

The macOS Application Shell is the foundational native container for Crafted.

**Declared responsibilities:**
- installation and distribution:
  - `.app` bundle,
  - drag-to-Applications,
  - Sparkle auto-update;
- identity and authentication:
  - biometric gate,
  - Keychain secret storage,
  - session lifecycle;
- Swift module architecture:
  - module boundaries,
  - concurrency model,
  - state ownership;
- SwiftUI view hierarchy;
- orchestration of all subsystems.

**Implementation domain:**
- Swift 5.9+
- SwiftUI
- native macOS 13.0+ (Ventura)

**Architectural role:**
- root host process,
- user-facing shell,
- trust boundary for secrets and local operator interaction,
- launcher/orchestrator for the Python backend.

---

### 2. Swift UI Layer
**Source:** TRD-1, CLAUDE.md TRD map

The documents distinguish SwiftUI views/cards/panels as a specifically owned area.

**Declared responsibilities from provided docs:**
- SwiftUI view hierarchy is owned by the shell.
- SwiftUI views, cards, and panels are associated with a dedicated TRD reference path.

**Architectural role:**
- renders native operator interface,
- surfaces shell-owned state,
- presents progress and control surfaces for the directed build workflow.

Because the loaded content is partial, no additional view taxonomy should be inferred beyond SwiftUI hierarchy ownership.

---

### 3. Authentication and Identity Subsystem
**Source:** TRD-1, extracted headings/content

A shell-owned subsystem for identity, authentication, and session handling.

**Declared responsibilities:**
- biometric gate,
- Keychain secret storage,
- session lifecycle.

**Observed related stored identities/secrets from extracted content:**
- `display_name` stored in `UserDefaults`,
- `engineer_id` stored in Keychain as `SecretKey.engineerId`,
- `github_username` fetched from GitHub `/user` endpoint on first auth.

**Architectural role:**
- gates access to privileged product operations,
- persists identity and secret material in shell-owned stores,
- mediates authenticated use of downstream services.

---

### 4. Secret Storage / Keychain Subsystem
**Source:** TRD-1, AGENTS.md, CLAUDE.md

While part of the shell’s auth responsibilities, Keychain ownership is explicit enough to call out as a security-relevant subsystem boundary.

**Declared responsibilities:**
- secret storage in Keychain,
- shell ownership of secrets,
- credential handling and delivery to the backend as part of orchestration.

**Architectural role:**
- sole local persistence authority for secrets,
- participates in backend startup/authentication,
- must comply with the repository-wide security model governed by TRD-11.

---

### 5. Swift–Python IPC / XPC Bridge
**Source:** AGENTS.md, CLAUDE.md, TRD-1 dependency references, extracted file references

The provided docs describe authenticated communication between the two processes and reference XPC-related implementation artifacts.

**Declared/provided facts:**
- communication is over an **authenticated Unix socket**,
- protocol is **line-delimited JSON**,
- Swift shell owns XPC-related responsibilities,
- `Crafted/XPCBridge.swift` and `src/xpc_server.py` are named artifacts,
- TRD-10 depends on TRD-1 for **XPC progress messages**.

**Architectural role:**
- transports commands, progress, and results between shell and backend,
- forms the local process trust link,
- must authenticate the backend connection rather than assuming trust.

---

### 6. Python Backend
**Source:** AGENTS.md, CLAUDE.md, README, TRD-10

The Python backend is the non-UI execution process for all intelligence and automation logic.

**Declared responsibilities:**
- consensus,
- pipeline,
- GitHub,
- generation,
- document retrieval/retrieval-context injection,
- backend server functionality (`src/xpc_server.py` is referenced).

**Implementation domain:**
- Python 3.12
- bundled with the app per TRD-1 metadata.

**Architectural role:**
- executes the autonomous build workflow,
- consumes shell-delivered authentication/material as needed,
- performs no direct UI ownership,
- must never execute generated code.

---

### 7. Consensus Engine
**Source:** README, AGENTS.md, CLAUDE.md, TRD-10 dependencies

The repository description explicitly identifies a two-model consensus architecture.

**Declared responsibilities/facts:**
- uses **two LLM providers in parallel**,
- specifically **Claude + GPT-4o**,
- **Claude arbitrates every result**,
- consensus is a Python backend responsibility,
- TRD-10 says its retrieval engine is required by **TRD-2** and that `auto_context()` is called per generation.

**Architectural role:**
- coordinates multi-provider generation,
- arbitrates outputs,
- consumes retrieval context,
- feeds downstream correction, lint, and fix stages.

---

### 8. Generation / Build Pipeline
**Source:** README, AGENTS.md

The core product flow is a structured generation pipeline, not an ad hoc interaction loop.

**Declared stages/behaviors from README:**
- confidence assessment,
- intent decomposition into PRD plan,
- PR decomposition into typed pull requests,
- implementation and test generation,
- self-correction pass,
- lint gate,
- iterative fix loop,
- CI execution,
- draft PR creation.

**Architectural role:**
- deterministic orchestration framework for converting operator intent and project specs into reviewable pull requests.

---

### 9. Document Store and Retrieval Engine
**Source:** TRD-10

A Python subsystem that ingests project documents and serves context into generation/review flows.

**Declared responsibilities:**
- ingest documents,
- retrieval for context injection,
- support `auto_context()` per generation,
- support `doc_filter` integration in Stage 1/5,
- support review context,
- support `PRODUCT_CONTEXT` auto-load.

**Declared storage location:**
- `~/Library/Application Support/Crafted/cache/{project_id}/`

**Declared lifecycle/storage facts from extracted content:**
- project creation initializes an empty index in `cache/{project_id}/`,
- no explicit unload because the FAISS index is small enough to keep loaded,
- 10 projects ≈ ~3MB total.

**Architectural role:**
- local project knowledge base,
- retrieval provider for generation and review stages,
- backend-owned persistent cache.

---

### 10. GitHub Operations Subsystem
**Source:** AGENTS.md, CLAUDE.md, README, extracted content

The Python backend explicitly owns GitHub operations.

**Declared responsibilities/facts:**
- opens draft pull requests,
- fetches user identity from GitHub `/user` on first auth,
- performs repository operations as part of the build workflow.

**Observed extracted operation details:**
- fetch file content from GitHub,
- get content + SHA,
- generate JWT using App private key from Keychain.

Because the source set is partial, these are recorded only as explicit observed responsibilities and interaction patterns.

**Architectural role:**
- repository read/write integration,
- PR publication mechanism,
- external system boundary to GitHub.

---

### 11. CI Integration Subsystem
**Source:** extracted workflow headings, README

The product pipeline includes CI execution prior to PR readiness, and repository workflows are explicitly named.

**Declared/observed CI jobs:**
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`

**README-declared role:**
- CI is executed as part of the automated flow before opening/reviewing PRs.

**Architectural role:**
- validation gate across Python and Swift/macOS surfaces,
- enforces quality before PR handoff.

---

### 12. Distribution and Update Subsystem
**Source:** TRD-1, extracted content

A shell-owned subsystem for installation and update.

**Declared responsibilities:**
- `.app` bundling,
- drag-to-Applications installation,
- Sparkle auto-update.

**Observed distribution identity detail:**
- Developer ID Application: `YouSource.ai ({TEAM_ID})`

**Architectural role:**
- packages and distributes the native app,
- updates the shell according to macOS application conventions.

---

### 13. Session and Operator Control Surface
**Source:** TRD-1, README, extracted command examples

The shell owns session lifecycle, while the overall product exposes operator-controlled review/gating flows.

**Declared/observed facts:**
- session lifecycle is shell-owned,
- operator gates, reviews, and merges,
- review commands and exclusions exist in the product surface:
  - `/ledger note <text>`
  - `/review start`
  - `/review exclude`
  - file/directory/lens exclusions.

**Architectural role:**
- operator-facing control boundary,
- enables explicit human gating and scope control,
- constrains autonomous actions within reviewed workflow stages.

---

### 14. Security Governance
**Source:** AGENTS.md, CLAUDE.md, architecture rules excerpt

Security is defined as a cross-cutting subsystem/governance layer rather than an isolated implementation component.

**Declared facts:**
- **TRD-11 governs all components** for security-relevant changes.
- It must be consulted for credentials, external content, generated code, or CI.
- Trust must be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- Components default to policy enforcement, not suggestion.

**Architectural role:**
- cross-cutting control plane for all sensitive operations,
- defines admissible behavior around secrets, content, generated artifacts, and automation.

---

## Component Boundaries

This section captures what each subsystem is explicitly responsible for and, critically, what it must **never** do based on the provided documents.

### macOS Application Shell
**Must do:**
- own UI, authentication, Keychain secrets, installation/update, and orchestration.

**Must never do:**
- own backend intelligence, consensus, generation, or GitHub operations;
- implicitly delegate shell-owned trust decisions without authenticated handoff;
- execute generated code.

---

### Swift UI Layer
**Must do:**
- render the shell-owned native interface and state.

**Must never do:**
- store secrets directly outside shell-defined secret management;
- perform backend intelligence functions;
- execute generated code.

---

### Authentication and Identity Subsystem
**Must do:**
- enforce biometric gate,
- manage session lifecycle,
- persist identity/secrets through approved stores.

**Must never do:**
- allow unauthenticated elevation into backend operations by assumption;
- bypass Keychain for secret-class data where Keychain ownership is defined;
- execute generated code.

---

### Secret Storage / Keychain
**Must do:**
- remain the shell-owned persistence location for secret material.

**Must never do:**
- leak secrets into non-secret storage by convenience;
- transfer credentials without authenticated process linkage;
- execute generated code.

---

### Swift–Python IPC / XPC Bridge
**Must do:**
- use authenticated local communication,
- exchange line-delimited JSON messages,
- carry progress and orchestration traffic.

**Must never do:**
- assume process trust without authentication;
- become the owner of business logic that belongs to shell or backend;
- execute generated code.

---

### Python Backend
**Must do:**
- own intelligence, consensus, generation pipeline, document retrieval, and GitHub operations.

**Must never do:**
- own native UI, biometric auth, or Keychain secret persistence;
- violate shell ownership of secrets and identity;
- execute generated code.

---

### Consensus Engine
**Must do:**
- run two-provider generation in parallel,
- use Claude + GPT-4o,
- apply Claude arbitration,
- consume retrieval context.

**Must never do:**
- replace the shell as security/secret owner;
- bypass documented context or pipeline stages when they are required;
- execute generated code.

---

### Generation / Build Pipeline
**Must do:**
- transform intent into PRD plan, then typed pull requests,
- run correction, lint, iterative fix loop, CI, and PR creation.

**Must never do:**
- collapse into unrestricted chat behavior;
- skip operator review/gating as described in the product model;
- execute generated code.

---

### Document Store and Retrieval Engine
**Must do:**
- ingest documents,
- persist project-local retrieval data in the declared cache path,
- provide context to generation/review consumers.

**Must never do:**
- redefine generation policy or consensus behavior;
- escape its project-scoped storage boundary;
- execute generated code.

---

### GitHub Operations Subsystem
**Must do:**
- interact with GitHub for identity and repository/PR actions.

**Must never do:**
- become the primary owner of local identity/secrets;
- bypass review-oriented workflow expectations in the product definition;
- execute generated code.

---

### CI Integration Subsystem
**Must do:**
- validate Python and macOS/Swift behavior via named CI jobs.

**Must never do:**
- substitute for local policy/security controls;
- execute generated code beyond normal test/validation scope as defined by the repository;
- bypass the broader pipeline ordering defined in product flow.

---

### Distribution and Update Subsystem
**Must do:**
- package and update the app as a native macOS application.

**Must never do:**
- own runtime intelligence logic,
- bypass platform signing/distribution expectations implied by Developer ID and Sparkle usage,
- execute generated code.

---

### Session and Operator Control Surface
**Must do:**
- preserve operator gating, review, merge, and exclusion controls.

**Must never do:**
- remove explicit operator control from reviewed workflow stages;
- infer approval from silence;
- execute generated code.

---

### Security Governance
**Must do:**
- apply TRD-11 across credentials, external content, generated code, and CI-touching behavior,
- require explicit trust assertion and verification.

**Must never do:**
- allow implicit trust where explicit verification is possible;
- collapse identity, policy, telemetry, and enforcement into an unobservable control path.

---

## Key Data Flows

## 1. App startup and subsystem orchestration
1. The native macOS shell launches as the `.app` bundle.
2. The shell owns installation/runtime environment concerns.
3. The shell starts and orchestrates the Python backend.
4. Communication is established over an **authenticated Unix socket** using **line-delimited JSON**.
5. The shell and backend exchange orchestration and progress messages.

**Boundary owners:**
- shell owns process lifecycle and local trust establishment,
- backend owns automation logic after successful authenticated connection.

---

## 2. Authentication and session establishment
1. The operator interacts with the native shell.
2. The shell performs biometric gate and manages session lifecycle.
3. Secret material is stored in Keychain.
4. Identity attributes are persisted/fetched through the documented stores and external GitHub identity lookup where applicable.
5. Authenticated state enables access to downstream automation flows.

**Boundary owners:**
- shell owns auth/session/secrets,
- GitHub may provide identity data,
- backend consumes but does not own these primitives.

---

## 3. Intent-to-PR automation flow
1. The operator supplies repository, TRDs, and intent.
2. The backend assesses confidence in scope.
3. The backend decomposes intent into an ordered PRD plan.
4. The backend decomposes each PRD into typed pull requests.
5. The backend generates implementation and tests using two providers in parallel.
6. Claude arbitrates every result.
7. The pipeline applies self-correction, lint, iterative fix loop, and CI.
8. The system opens a draft PR for review.
9. The operator gates, reviews, and merges.
10. The agent proceeds to the next PR.

**Boundary owners:**
- shell owns operator interaction and gating surface,
- backend owns decomposition/generation/pipeline/GitHub execution.

---

## 4. Retrieval-augmented generation flow
1. Project documents are ingested into the Document Store.
2. The store persists retrieval artifacts under `~/Library/Application Support/Crafted/cache/{project_id}/`.
3. On generation, `auto_context()` is invoked per TRD-10.
4. Retrieval context is supplied to consensus/generation consumers.
5. Review and product-context consumers also use retrieval outputs where specified.

**Boundary owners:**
- document store owns ingestion/index/cache,
- consensus/pipeline own use of retrieved context.

---

## 5. GitHub content and PR flow
1. The backend interacts with GitHub for repository/user operations.
2. On first auth, GitHub `/user` can provide `github_username`.
3. Repository content may be fetched with content and SHA metadata.
4. PR artifacts are pushed as draft pull requests for operator review.

**Boundary owners:**
- shell owns local secret material,
- backend owns GitHub API workflow,
- operator remains approval authority.

---

## 6. CI validation flow
1. Generated or updated code enters the validation phase.
2. CI jobs run across Python and macOS/Swift surfaces.
3. CI results gate progress toward PR readiness.

**Observed CI surfaces:**
- Python test job,
- macOS unit test job,
- macOS XPC integration test job.

**Boundary owners:**
- pipeline owns invocation/order,
- CI owns validation outcome,
- operator owns final merge decision.

---

## Critical Invariants

## 1. Two-process separation is mandatory
The architecture is explicitly two-process:
- **Swift shell**
- **Python backend**

Responsibilities are partitioned accordingly and must not be merged implicitly.

---

## 2. Secret ownership remains in the Swift shell
The shell owns:
- authentication,
- Keychain,
- secret storage,
- session lifecycle.

The backend may consume authenticated capabilities but does not become the system of record for secrets.

---

## 3. Local inter-process trust must be authenticated
Communication between shell and backend is not a raw convenience channel. It is explicitly:
- over an **authenticated Unix socket**,
- using **line-delimited JSON**.

Trust must be asserted and verified explicitly.

---

## 4. Generated code is never executed by the product
The repository docs are explicit: **neither process ever executes generated code**.

This is a system-wide invariant applying to shell, backend, and all supporting subsystems.

---

## 5. Crafted is a directed build agent, not a chat product
The product’s architectural purpose is constrained:
- repository + TRDs + intent in,
- reviewed pull requests out.

The system must preserve the staged planning/build/review pipeline and not degrade into unrestricted conversational tooling behavior.

---

## 6. Consensus is multi-provider and Claude-arbitrated
The generation architecture uses:
- **Claude**
- **GPT-4o**
in parallel, with
- **Claude arbitrating every result**.

Any implementation of consensus must preserve that explicit control structure.

---

## 7. Retrieval is project-scoped and cache-backed
Document retrieval state is stored under:

`~/Library/Application Support/Crafted/cache/{project_id}/`

This establishes a project-scoped persistence boundary for document indexing and retrieval artifacts.

---

## 8. Operator review and merge remain explicit
The product flow requires:
- draft PR creation,
- operator review,
- operator gating,
- operator merge.

Autonomous production of changes does not remove human approval from the described workflow.

---

## 9. TRDs are the source of truth
The documents state that the codebase is specified completely in **16 TRDs** and that code must match them.

Architecture, interfaces, error contracts, state machines, security controls, and performance behavior must therefore remain subordinate to TRD definitions.

---

## 10. TRD-11 governs all security-relevant behavior
Any change involving:
- credentials,
- external content,
- generated code,
- CI

must remain consistent with **TRD-11**. Security is not optional or advisory in this system.

---

## 11. Identity, policy, telemetry, and enforcement must remain separable but linked
From the provided architecture rules:
- trust must not be inferred implicitly where it can be verified,
- identity, policy, telemetry, and enforcement remain separable but tightly linked,
- decisions must be explainable, observable, and reproducible,
- enforcement defaults over suggestion.

These rules function as architecture-wide invariants across all subsystems.

---

## 12. Native macOS packaging and runtime are first-class architecture constraints
Crafted is specified as a **native macOS** application with:
- Swift/SwiftUI shell,
- macOS 13.0+ minimum,
- bundled Python 3.12,
- `.app` distribution,
- Sparkle auto-update.

These are not incidental implementation choices; they are part of the architectural contract.