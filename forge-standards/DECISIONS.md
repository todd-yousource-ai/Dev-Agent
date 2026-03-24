## Two-process native macOS architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent with distinct responsibilities across UI/platform concerns and AI/generation concerns. The repository guidance and product description state that Swift owns UI, authentication, secrets, and local orchestration, while Python owns intelligence, generation, consensus, and GitHub operations.  
**Decision:** The system is split into two processes: a native Swift/SwiftUI macOS shell and a Python 3.12 backend. The Swift shell is the platform host for packaging, installation, authentication, Keychain access, and orchestration. The Python backend implements consensus, generation pipelines, self-correction, lint/fix loops, CI coordination, and GitHub pull request operations.  
**Consequences:** Clear trust and responsibility boundaries are enforced between platform/security functions and model/backend functions. Cross-process interfaces must be explicitly specified and authenticated. Features must be assigned to one side of the boundary rather than duplicated.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because the product specification explicitly separates platform/security ownership from intelligence/backend ownership.  
- **Web or Electron-style shell:** Rejected because the product is specified as a native macOS application shell in Swift/SwiftUI.

## Swift shell owns UI, identity, and secrets
**Status:** Accepted  
**Context:** TRD and repository guidance assign platform-native concerns to the Swift shell, especially user interface, authentication, session handling, and secret storage.  
**Decision:** All UI rendering, SwiftUI views, local authentication, biometric gating, Keychain secret storage, and shell-side orchestration are implemented in the Swift process. The shell is the only component that directly manages end-user identity and platform secrets.  
**Consequences:** Sensitive material remains under native macOS security primitives. Backend features requiring credentials must obtain them through defined shell-mediated interfaces rather than direct secret storage.  
**Rejected alternatives:**  
- **Python backend managing credentials directly:** Rejected because shell ownership of authentication and Keychain is explicitly specified.  
- **Shared responsibility for secrets between processes:** Rejected because it weakens trust boundaries and conflicts with the documented ownership model.

## Python backend owns intelligence, consensus, and GitHub operations
**Status:** Accepted  
**Context:** Product and repository documents consistently assign AI reasoning, implementation generation, model coordination, and repository automation to Python.  
**Decision:** The Python backend is the sole owner of consensus logic, provider coordination, planning/generation pipelines, self-correction, lint/fix loops, CI-related backend logic, and GitHub pull request creation/update behavior.  
**Consequences:** Backend code is the implementation locus for autonomous development workflows. Shell code should not duplicate planning or generation logic. Cross-process communication must be sufficient to expose backend state to the shell UI.  
**Rejected alternatives:**  
- **Embedding model orchestration in Swift:** Rejected because backend intelligence is explicitly assigned to Python.  
- **Moving GitHub operations into the shell:** Rejected because repository automation belongs to the backend in the documented architecture.

## Authenticated Unix socket with line-delimited JSON IPC
**Status:** Accepted  
**Context:** The system requires a defined communication mechanism between the Swift shell and Python backend. Repository guidance specifies both the transport and message framing.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket with line-delimited JSON messages. All cross-process requests and responses must conform to this IPC model.  
**Consequences:** Interface contracts must be serializable as JSON and framed one message per line. Authentication of the local channel is mandatory. Alternative transport layers are out of scope unless the TRDs are updated.  
**Rejected alternatives:**  
- **XPC-only communication:** Rejected because the repository guidance explicitly specifies an authenticated Unix socket with line-delimited JSON.  
- **HTTP/gRPC over localhost:** Rejected because it is not the documented IPC mechanism.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** Security guidance in the repository instructions explicitly states that neither process ever executes generated code. This is a foundational safety boundary for the product.  
**Decision:** The shell and backend must not execute generated code as part of generation, validation, or review workflows. The agent may generate code, tests, patches, PRs, and CI-triggering changes, but neither local process directly runs generated artifacts.  
**Consequences:** Validation strategies must rely on permitted mechanisms documented in the TRDs rather than direct execution of generated outputs by the agent processes. Any feature proposal requiring execution of generated code is non-compliant unless the TRDs change.  
**Rejected alternatives:**  
- **Sandboxed local execution of generated code:** Rejected because the repository guidance states neither process ever executes generated code.  
- **Selective execution for tests only:** Rejected for the same reason; no exception is specified in the provided documents.

## TRDs are the sole source of truth for design and implementation
**Status:** Accepted  
**Context:** Multiple repository documents state that the 16 TRDs in `forge-docs/` completely specify the system and that code must match them.  
**Decision:** All significant behavior, interfaces, state machines, error contracts, security controls, testing expectations, and subsystem boundaries are derived from the TRDs. In implementation and design disputes, the relevant TRD governs.  
**Consequences:** Engineers and agents must consult the owning TRD before changing a subsystem. Unspecified behavior should not be invented. Design changes require TRD updates, not ad hoc implementation drift.  
**Rejected alternatives:**  
- **README or agent instruction files as primary specs:** Rejected because they direct implementers back to the TRDs rather than replacing them.  
- **Code-as-specification:** Rejected because the repository explicitly requires code to match the TRDs.

## TRD-11 is the governing security authority across all components
**Status:** Accepted  
**Context:** Repository guidance identifies TRD-11 as governing all security-relevant work, especially credentials, external content, generated code, and CI.  
**Decision:** Security-sensitive design and implementation decisions across shell, backend, CI-related workflows, and content handling must conform to TRD-11. Any component touching credentials, untrusted/external content, generated artifacts, or CI must be reviewed against TRD-11 requirements.  
**Consequences:** Security review is centralized under a single governing TRD. Subsystem-specific documents do not override TRD-11 on security matters. Security-impacting changes require explicit alignment with that document.  
**Rejected alternatives:**  
- **Per-subsystem security models only:** Rejected because the repository defines a cross-cutting governing security TRD.  
- **Best-effort security interpretation without TRD-11 reference:** Rejected because the guidance explicitly mandates consulting TRD-11.

## Native macOS application shell as the primary product container
**Status:** Accepted  
**Context:** TRD-1 defines the shell as the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems, with macOS 13.0+ as the minimum supported platform.  
**Decision:** The product is delivered as a native macOS `.app` built with Swift 5.9+ and SwiftUI, targeting macOS 13.0 Ventura or newer, and bundling Python 3.12 for the backend.  
**Consequences:** Platform support, packaging, and UI technology choices are fixed. Cross-platform desktop targets are out of scope. Backend runtime distribution must work within the app-bundled macOS application model.  
**Rejected alternatives:**  
- **Cross-platform desktop distribution:** Rejected because the product is specified as a native macOS application shell.  
- **System-installed Python dependency:** Rejected in favor of bundled Python 3.12 as stated in TRD-1.

## The shell is responsible for installation, distribution, and auto-update
**Status:** Accepted  
**Context:** TRD-1 explicitly assigns installation and distribution responsibilities to the shell, including `.app` bundling, drag-to-Applications installation, and Sparkle auto-update.  
**Decision:** Distribution is implemented through a macOS application bundle with standard drag-to-Applications installation semantics, and the shell integrates Sparkle for automatic updates.  
**Consequences:** Release engineering and update behavior must align with the macOS app bundle model and Sparkle integration. Alternative installers and update frameworks are not the default path.  
**Rejected alternatives:**  
- **Custom installer package as primary distribution method:** Rejected because TRD-1 specifies `.app` bundle distribution and drag-to-Applications install.  
- **Manual update-only workflow:** Rejected because Sparkle auto-update is part of shell ownership in TRD-1.

## Biometric gate and Keychain-backed secret storage
**Status:** Accepted  
**Context:** TRD-1 assigns identity and authentication responsibilities to the shell, specifically including biometric gating, Keychain secret storage, and session lifecycle management.  
**Decision:** User authentication and secret persistence are implemented using macOS-native biometric access controls and Keychain storage, managed by the Swift shell as part of session lifecycle handling.  
**Consequences:** Secret handling is coupled to platform-native security APIs. Credentials and session state must flow through shell-controlled mechanisms. Backend access to secrets must remain mediated.  
**Rejected alternatives:**  
- **Filesystem-based encrypted secret storage:** Rejected because Keychain ownership is explicitly specified.  
- **Password-only local gate without biometrics:** Rejected because the shell’s identity model explicitly includes a biometric gate.

## Shell-centered orchestration of subsystems
**Status:** Accepted  
**Context:** TRD-1 describes the shell as the container that orchestrates all subsystems, while the product architecture separates subsystem implementation responsibilities.  
**Decision:** The Swift shell acts as the top-level orchestrator for application lifecycle, process startup, authentication gating, secure backend connectivity, and presentation of backend-driven workflow state to the user.  
**Consequences:** Application lifecycle control remains centralized in the shell. Backend services are subordinate to shell-managed startup and connection policies. UI-visible state transitions must be coordinated through shell orchestration.  
**Rejected alternatives:**  
- **Backend-led application lifecycle:** Rejected because orchestration ownership is assigned to the shell.  
- **Peer processes with no primary orchestrator:** Rejected because TRD-1 defines the shell as the native container coordinating subsystems.

## Autonomous workflow is PR-oriented rather than chat-oriented
**Status:** Accepted  
**Context:** The README explicitly states the product is not a chat interface or code autocomplete tool, but a directed build agent that turns specifications and intent into ordered pull requests.  
**Decision:** The product experience and backend workflow are centered on specification-driven planning and creation of typed GitHub pull requests, not conversational assistance or inline completion.  
**Consequences:** UX and system design should optimize for plan execution, confidence assessment, decomposition, review gating, and PR delivery. Chat-centric interaction models are out of scope unless separately specified.  
**Rejected alternatives:**  
- **General-purpose chat assistant UX:** Rejected because the README explicitly says the product is not a chat interface.  
- **IDE autocomplete/copilot workflow:** Rejected because the README explicitly says it is not code autocomplete.

## Intent is decomposed into ordered PRD plans and typed pull requests
**Status:** Accepted  
**Context:** The product description defines a staged autonomous workflow: assess confidence, decompose intent into an ordered PRD plan, then decompose each PRD into a sequence of typed pull requests.  
**Decision:** Work execution follows a hierarchical decomposition model from user intent to PRD plan to a sequence of typed pull requests representing logical units of implementation.  
**Consequences:** Planning and execution components must preserve ordering and logical-unit boundaries. Delivery is incremental and reviewable at PR granularity rather than monolithic changesets.  
**Rejected alternatives:**  
- **Single-shot repository-wide implementation:** Rejected because the documented workflow is staged and PR-oriented.  
- **Unstructured task list execution:** Rejected because the product specifies ordered PRD planning and typed PR decomposition.

## Two-model consensus generation with Claude arbitration
**Status:** Accepted  
**Context:** The README states that the system uses a two-model consensus engine with Claude and GPT-4o in parallel, and Claude arbitrates every result.  
**Decision:** Implementation generation is performed using two model providers in parallel, and final arbitration of results is performed by Claude within the consensus workflow.  
**Consequences:** Provider integration, consensus logic, and result selection must support parallel multi-model operation and an explicit arbitration stage. Single-model generation is not the primary architecture.  
**Rejected alternatives:**  
- **Single-provider generation pipeline:** Rejected because the product description specifies a two-model consensus engine.  
- **Symmetric voting without designated arbiter:** Rejected because Claude is explicitly defined as the arbitrator.

## Quality gates include self-correction, lint gate, iterative fix loop, CI, and draft PR output
**Status:** Accepted  
**Context:** The README defines the generation pipeline as including self-correction, lint gating, iterative fixing, CI execution, and opening a draft pull request for review.  
**Decision:** Generated work passes through a structured quality pipeline consisting of self-correction, lint validation, iterative remediation, CI-related validation, and creation of a draft GitHub pull request for human review.  
**Consequences:** The pipeline is multi-stage and quality-gated before delivery. PR creation is downstream of automated validation stages. Reviewability and correction are first-class design goals.  
**Rejected alternatives:**  
- **Direct PR creation immediately after generation:** Rejected because the product description includes multiple validation and correction gates before PR opening.  
- **One-pass generation without iterative fixing:** Rejected because an iterative fix loop is explicitly specified.

## Human review gates merge progression while the agent continues sequential work
**Status:** Accepted  
**Context:** The README describes a review-driven workflow where the user reviews and merges each PR while the agent builds the next one.  
**Decision:** The system operates with human-gated review and merge decisions for pull requests, while supporting continued preparation of subsequent logical units in sequence.  
**Consequences:** Workflow state management must account for in-review, approved, and merged transitions. The system is designed for incremental autonomous progress under human governance rather than fully unattended merge authority.  
**Rejected alternatives:**  
- **Fully autonomous merge without review:** Rejected because the README places review and merge in the user’s control.  
- **Strict stop-until-merge behavior with no subsequent work preparation:** Rejected because the product description says the agent builds the next PR while the user reads the last one.