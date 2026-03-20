# DECISIONS.md

## ADR-001: Adopt a two-process native macOS architecture
**Status:** Accepted  
**Context:** The platform must provide a native macOS experience while enforcing strong separation between privileged host responsibilities and untrusted AI-driven generation/orchestration logic. The TRDs define a Swift shell responsible for UI, auth, Keychain, packaging, and local orchestration, and a Python backend responsible for consensus, planning, generation, review, and GitHub operations. Security requirements prohibit generated code from gaining privileged access to host secrets or app capabilities.  
**Decision:** Forge uses a two-process architecture: a native Swift/SwiftUI macOS shell and a separate bundled Python 3.12 backend. The Swift shell owns user-facing workflows, application lifecycle, credential custody, secure storage, update integration, and process supervision. The Python backend owns planning, consensus, code generation, review pipelines, CI interaction, repository manipulation, and GitHub automation. Communication occurs only through a constrained authenticated IPC channel.  
**Consequences:** Stronger fault isolation, clearer trust boundaries, and easier enforcement of least privilege. The architecture adds IPC complexity, version coordination, process supervision requirements, and explicit contracts between subsystems. Cross-process features must be intentionally designed rather than sharing memory or in-process state.  
**Rejected alternatives:**  
- **Single-process app embedding all logic in Swift:** Rejected because it weakens isolation, complicates AI/tooling integration, and increases blast radius for failures.  
- **Electron/web shell with backend service:** Rejected because the product is explicitly a native macOS application and needs platform-native security integrations.  
- **Remote-only backend service:** Rejected because the TRDs require a local agent model with local secrets handling and local repo operations.

## ADR-002: Make the TRDs the source of truth for all implementation decisions
**Status:** Accepted  
**Context:** The platform spans 12 technical requirement documents and multiple subsystems with strict interface, security, and testing requirements. Without a single source of truth, implementation drift would be likely across shell, backend, UI, and automation layers.  
**Decision:** All significant implementation decisions in Forge are subordinate to the TRDs in `forge-docs/`. Code, interfaces, state machines, error contracts, and tests must conform to the owning TRD. When ambiguity exists, the relevant TRD is consulted before extending behavior. This document records architectural decisions made in service of those TRDs, not independent product requirements.  
**Consequences:** Architectural consistency is improved, review is simplified, and future changes can be traced back to documented requirements. Teams must identify the owning TRD before modifying a subsystem. Expedient undocumented behavior is intentionally discouraged.  
**Rejected alternatives:**  
- **Code-as-truth with informal docs:** Rejected because it invites drift and weakens cross-subsystem coordination.  
- **This ADR file as primary authority:** Rejected because it is derivative and cross-cutting; the TRDs remain normative.

## ADR-003: Use authenticated Unix domain socket IPC with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend require structured local IPC with clear framing, low overhead, and explicit authentication. The protocol must work well with Swift and Python, support streaming-style events, and remain inspectable for debugging.  
**Decision:** Forge uses an authenticated Unix domain socket as the IPC transport between the Swift shell and Python backend. Messages are line-delimited JSON, with explicit schemas per command/event type. The shell authenticates the backend connection and supervises session establishment.  
**Consequences:** The platform gains simple, local-only transport with operational visibility and easy incremental event delivery. The decision constrains message design to text-framed JSON and requires careful schema evolution and validation. Binary RPC systems and implicit method invocation are avoided.  
**Rejected alternatives:**  
- **XPC for all interprocess communication:** Rejected because the backend is Python-based and the TRDs define socket-based interoperability.  
- **gRPC/HTTP localhost service:** Rejected due to unnecessary network semantics, higher operational complexity, and a larger attack surface.  
- **StdIO pipes:** Rejected because long-lived authenticated bidirectional communication is better modeled with explicit sockets.

## ADR-004: Keep trust and secret ownership in the Swift shell
**Status:** Accepted  
**Context:** The product handles credentials, biometric gates, session control, and system integration. The backend must orchestrate AI and repository work but should not directly own long-lived secrets or OS-level trust anchors. TRD-11 makes security controls central across all components.  
**Decision:** The Swift shell is the root of trust on the client. It owns authentication state, Keychain integration, biometric gating, secure secret storage, session lifecycle, and permission to release scoped credentials or tokens to the backend when required. The backend never becomes the authoritative store for user secrets.  
**Consequences:** Sensitive operations remain within the native platform security boundary. Backend features requiring credentials must request them through defined contracts. This creates some friction in backend implementation but materially improves compartmentalization and auditability.  
**Rejected alternatives:**  
- **Store secrets directly in the Python backend:** Rejected because it weakens platform security guarantees and bypasses native secret-handling controls.  
- **Let both processes share secret custody:** Rejected because shared ownership makes revocation, auditing, and threat modeling harder.

## ADR-005: Store secrets in Keychain and gate access with biometrics/session policy
**Status:** Accepted  
**Context:** The application must securely manage provider credentials, GitHub tokens, and other sensitive material on macOS while providing a user-appropriate access model. Native secret storage and local user presence checks are required by the shell responsibilities.  
**Decision:** Forge stores secrets in macOS Keychain and uses shell-managed biometric and session-gate controls for access according to policy. Secrets are persisted only through approved platform mechanisms; access is mediated by the shell and exposed to the backend only in narrowly scoped, time-bounded ways when needed.  
**Consequences:** The platform aligns with native macOS security expectations and avoids creating a parallel credential store. Some automation flows must account for user-presence gates and session unlock state. Key rotation, deletion, and migration must respect Keychain semantics.  
**Rejected alternatives:**  
- **Flat-file encrypted secret store:** Rejected because it duplicates OS facilities and increases implementation risk.  
- **Environment-variable-based secret management:** Rejected because it is too porous for a desktop app and unsuitable for durable session management.

## ADR-006: Never execute generated code inside the application runtime
**Status:** Accepted  
**Context:** The platform generates and edits code autonomously. Executing generated code within the shell or backend would create a direct path from model output to arbitrary code execution. Repository changes and CI validation are required, but the host application itself must not become an execution surface for model-generated artifacts.  
**Decision:** Neither the Swift shell nor the Python backend executes generated code as part of application logic. Validation occurs through controlled repository operations and CI/test workflows external to the app runtime, following the security controls defined in the TRDs. Generated content is treated as untrusted input at all times.  
**Consequences:** The design substantially reduces RCE risk and simplifies trust boundaries. Validation mechanisms must be explicit and sandbox-aware, and some otherwise convenient local execution patterns are disallowed. Features that imply “run this code in-process” are out of scope.  
**Rejected alternatives:**  
- **In-process execution for faster feedback:** Rejected due to unacceptable security risk.  
- **Dynamic plugin execution model:** Rejected because generated outputs are not trusted extensions of the app.

## ADR-007: Bundle Python 3.12 with the application
**Status:** Accepted  
**Context:** The backend is Python-based and must run reliably on supported macOS systems without assuming a user-managed Python installation. Deterministic packaging and compatibility are required for a desktop application.  
**Decision:** Forge ships a bundled Python 3.12 runtime as part of the macOS application package. The shell launches and supervises this known backend environment rather than depending on system Python or user-installed interpreters.  
**Consequences:** Runtime behavior becomes more deterministic and supportability improves. Application packaging size increases and release engineering must account for Python runtime updates and dependency management. The platform avoids environmental drift from user machines.  
**Rejected alternatives:**  
- **Use system Python:** Rejected because macOS Python availability and configuration are inconsistent.  
- **Require Homebrew/pyenv setup:** Rejected because it degrades installation and violates desktop-app expectations.  
- **Rewrite backend fully in Swift:** Rejected because the specified backend architecture and model/tooling ecosystem are Python-based.

## ADR-008: Target macOS 13.0+ and build the shell with Swift 5.9+ and SwiftUI
**Status:** Accepted  
**Context:** The shell is specified as a native macOS application and must align with documented minimum platform and language versions. UI and app lifecycle responsibilities live in the shell.  
**Decision:** Forge targets macOS 13.0 Ventura and later. The native shell is implemented in Swift 5.9+ using SwiftUI for application UI and shell-layer architecture. Platform integrations use native Apple frameworks where appropriate.  
**Consequences:** The product can rely on modern macOS APIs and SwiftUI patterns while excluding older macOS versions. UI design and shell abstractions must fit SwiftUI’s data-flow model. Backporting to older operating systems is not planned.  
**Rejected alternatives:**  
- **AppKit-first implementation:** Rejected as the primary architecture because the TRDs specify SwiftUI shell ownership.  
- **Cross-platform UI toolkit:** Rejected because the product is intentionally native macOS.

## ADR-009: Ship as a standard macOS app bundle with drag-install and Sparkle updates
**Status:** Accepted  
**Context:** The shell owns installation, distribution, and update behavior. A desktop product needs predictable packaging and update delivery while preserving native macOS expectations.  
**Decision:** Forge is distributed as a `.app` bundle designed for drag-to-Applications installation and uses Sparkle for auto-update capability. Update behavior is owned by the shell and integrated with the application lifecycle and trust model.  
**Consequences:** Users get familiar installation and upgrade workflows. Release signing, notarization, Sparkle feed management, and update validation become required operational capabilities. Update policy must be coordinated with backend/runtime compatibility.  
**Rejected alternatives:**  
- **Homebrew-only distribution:** Rejected because it does not satisfy mainstream desktop installation expectations.  
- **Custom updater:** Rejected because Sparkle is the specified native solution with a mature update model.  
- **Mac App Store distribution as primary path:** Rejected because the TRDs specify direct app distribution with Sparkle.

## ADR-010: Use provider-based multi-model consensus with parallel generation and arbitration
**Status:** Accepted  
**Context:** The product’s core differentiator is autonomous software delivery using multiple LLM providers rather than a single-model pipeline. README and TRD content describe a two-model consensus engine where Claude arbitrates outcomes.  
**Decision:** Forge generates and reviews work through a consensus engine that invokes multiple model providers in parallel for implementation tasks, then resolves outcomes through defined arbitration rules, with Claude serving as arbiter for final result selection where specified. Provider access is abstracted behind backend adapters rather than embedded directly into orchestration logic.  
**Consequences:** Output quality and robustness are improved through diversity and structured comparison, but latency, cost, and orchestration complexity increase. Prompting, schema normalization, and arbitration rules become first-class system design concerns.  
**Rejected alternatives:**  
- **Single-provider generation pipeline:** Rejected because it reduces resilience and departs from the product’s defining architecture.  
- **Simple majority voting across many models:** Rejected because the specified system uses explicit arbitration rather than undifferentiated voting.  
- **Hard-code provider APIs into pipeline stages:** Rejected because adapters are needed for maintainability and substitution.

## ADR-011: Represent AI providers behind explicit adapter interfaces
**Status:** Accepted  
**Context:** The backend must work across multiple model providers with differing APIs, formats, limits, and failure modes. Consensus and arbitration logic should not be tightly coupled to any single vendor.  
**Decision:** Forge uses provider adapter abstractions in the backend. Each provider implementation is responsible for request/response translation, capability handling, retry semantics within policy, and normalization into backend-native contracts consumed by the consensus engine and pipeline.  
**Consequences:** Provider-specific complexity is isolated and new providers can be added with bounded impact. Adapter contracts must be carefully versioned and tested. Some provider-specific features may be intentionally unavailable if they cannot be normalized safely.  
**Rejected alternatives:**  
- **Direct provider SDK calls throughout the codebase:** Rejected due to coupling and maintenance cost.  
- **Lowest-common-denominator provider wrapper only:** Rejected because adapters need enough fidelity to support arbitration and backend policies.

## ADR-012: Build from intent through PRD plan to ordered pull requests
**Status:** Accepted  
**Context:** Forge is not a chat tool; it is a directed build agent. The product decomposes user intent into implementation work that is staged, reviewed, and delivered as pull requests.  
**Decision:** The platform transforms plain-language user intent plus repository/TRD context into an internal PRD-style plan, then decomposes that plan into an ordered sequence of logical pull requests. Each PR is treated as the primary unit of generation, review, CI, and user approval before subsequent work advances.  
**Consequences:** Delivery is incremental, reviewable, and auditable. Planning quality becomes critical, and dependencies across PRs must be managed explicitly. The system is intentionally optimized for repository change workflows rather than free-form conversational assistance.  
**Rejected alternatives:**  
- **Single large branch for entire intent:** Rejected because it harms reviewability and increases failure risk.  
- **Task list without PR-centric decomposition:** Rejected because GitHub PRs are the intended operational boundary.

## ADR-013: Make pull requests the unit of autonomy, review, and user gating
**Status:** Accepted  
**Context:** The product is designed to open one draft PR per logical unit, allow the user to review and approve, and then continue with the next PR while the previous one is under review. This requires a clear operational state machine.  
**Decision:** Forge treats each logical pull request as the atomic unit for implementation lifecycle management. For each PR, the backend plans changes, generates code and tests, runs review passes, executes CI, and opens a draft PR for user review. Advancement to dependent PRs is gated by user approval and workflow policy.  
**Consequences:** Progress is measurable and recoverable at PR boundaries. The system can parallelize some preparatory work but must preserve merge/order constraints. Users interact primarily through PR approval, not token-by-token conversation.  
**Rejected alternatives:**  
- **Commit-level autonomy without PR boundaries:** Rejected because user governance and CI integration become weaker.  
- **Fully autonomous merge without approval:** Rejected because the product is explicitly user-gated.

## ADR-014: Require a structured multi-pass review cycle before PR creation
**Status:** Accepted  
**Context:** The README specifies a 3-pass review cycle before a draft PR is opened. Autonomous code generation alone is insufficient for the quality bar expected of a directed build agent.  
**Decision:** Every generated PR passes through a structured multi-pass review workflow before publication. Review stages are backend-controlled, use defined prompts/contracts, and are part of the normal pipeline rather than optional post-processing. The review pipeline checks implementation completeness, consistency with specifications, and likely defect patterns before CI and PR publication.  
**Consequences:** Quality improves and the system has explicit checkpoints for self-correction. Latency and token usage increase, and failures may require regeneration or escalation. Review is a required pipeline stage, not an enhancement.  
**Rejected alternatives:**  
- **Single-pass generation with only CI validation:** Rejected because CI alone does not enforce specification alignment or code quality.  
- **Manual review only after PR open:** Rejected because the platform promises meaningful autonomous pre-review.

## ADR-015: Require tests to be generated and maintained with implementation changes
**Status:** Accepted  
**Context:** The repository instructions require consulting TRD testing requirements and running the existing test suite before changes. The product itself is expected to generate both implementation and tests for each PR.  
**Decision:** Forge treats tests as part of the deliverable for each PR whenever the affected subsystem warrants automated coverage. Generated code changes are accompanied by corresponding test changes, and review/CI stages evaluate both implementation and tests as part of completion.  
**Consequences:** Regression protection improves and generated work is held to a higher bar. Some PRs will be larger due to necessary test additions. Test contracts must be understood from the relevant TRD rather than guessed.  
**Rejected alternatives:**  
- **Implementation-first with deferred tests:** Rejected because it weakens delivery quality and contradicts the intended workflow.  
- **Only update tests when CI fails:** Rejected because tests are a design artifact, not just a repair mechanism.

## ADR-016: Integrate tightly with GitHub as the primary remote workflow system
**Status:** Accepted  
**Context:** The product opens draft pull requests, sequences work through repository branches, and relies on CI and PR review. The README and architecture place GitHub operations in the Python backend.  
**Decision:** Forge uses GitHub as the primary remote collaboration and delivery system. The backend owns repository automation including branch management, PR creation/update, and interaction with CI status in support of the PR pipeline. The shell provides user-facing status and approvals while backend workflows remain GitHub-centric.  
**Consequences:** The platform can offer a coherent end-to-end workflow around repositories and PRs. GitHub concepts shape internal state models and error handling. Portability to other forges is not a near-term architectural goal.  
**Rejected alternatives:**  
- **SCM-agnostic abstraction from day one:** Rejected because it adds complexity without matching the specified product workflow.  
- **Local-only patch generation:** Rejected because the product promise centers on opening GitHub pull requests.

## ADR-017: Treat CI as a mandatory quality gate in the PR pipeline
**Status:** Accepted  
**Context:** The product generates code, runs a review cycle, executes CI, and only then opens a draft PR. CI provides an external validation stage distinct from in-app generation and review.  
**Decision:** Continuous integration is a required gate in the Forge pipeline for any PR where CI is configured and applicable. The backend triggers or observes CI status as part of PR readiness and uses results to determine whether a PR is fit to publish or needs remediation.  
**Consequences:** The system gains stronger validation and aligns with normal repository governance. Pipeline duration depends partly on external CI latency and availability. CI failures become first-class workflow states requiring retry, fixup, or escalation.  
**Rejected alternatives:**  
- **Open PR before CI completes:** Rejected because the product flow states CI precedes draft PR publication.  
- **Make CI optional by default:** Rejected because it weakens the autonomous quality bar.

## ADR-018: Design the user experience as a directed workflow, not a chat interface
**Status:** Accepted  
**Context:** The README explicitly states the product is not a chat interface, not code autocomplete, and not a copilot. The shell UI must therefore represent pipeline state, approvals, plans, and PR progression rather than generic conversation.  
**Decision:** Forge’s product UX is centered on intent submission, plan visibility, PR progression, review state, approvals, and outcome tracking. Conversational interactions may exist only insofar as they support these directed workflows; they are not the primary product model.  
**Consequences:** UI and backend APIs prioritize job orchestration, artifacts, and lifecycle state over arbitrary dialogue. This sharpens product identity but constrains features that would pull the platform toward a general assistant.  
**Rejected alternatives:**  
- **General-purpose chat-first IDE assistant:** Rejected because it is explicitly outside product scope.  
- **Inline autocomplete workflow:** Rejected because the platform is oriented around autonomous PR delivery.

## ADR-019: Model the shell as the orchestrator of backend process lifecycle and health
**Status:** Accepted  
**Context:** The shell owns packaging, launching, authentication context, and IPC setup. The backend is a supervised worker process whose availability and compatibility are essential to the product experience.  
**Decision:** The Swift shell is responsible for launching, monitoring, authenticating, and terminating the Python backend process. It manages startup sequencing, compatibility checks, reconnect behavior, and user-visible degraded-state handling when the backend is unavailable or unhealthy.  
**Consequences:** Process control is centralized in the trusted native layer and user experience remains coherent during backend faults. The shell must implement health/state management rather than assuming the backend is always present.  
**Rejected alternatives:**  
- **Backend self-daemonization outside shell control:** Rejected because it weakens lifecycle coordination and trust establishment.  
- **Independent processes started ad hoc:** Rejected because it complicates update, auth, and state management.

## ADR-020: Use explicit schema-based contracts for commands, events, and errors
**Status:** Accepted  
**Context:** Cross-process communication and multi-stage pipelines create many integration points. The repository instructions emphasize interface and error-contract compliance from the relevant TRD.  
**Decision:** Forge defines explicit structured contracts for IPC commands, backend events, pipeline statuses, and error payloads. Messages are validated at subsystem boundaries and versioned intentionally as interfaces evolve. Error handling is contract-driven rather than inferred from free-form strings.  
**Consequences:** Integration becomes more robust and debuggable. Schema evolution requires discipline and compatibility planning. Ad hoc payloads are discouraged even when they seem faster during implementation.  
**Rejected alternatives:**  
- **Stringly typed message passing:** Rejected because it is brittle and hard to evolve safely.  
- **Opaque exception tunneling across process boundaries:** Rejected because it does not provide stable user- or system-level behavior.

## ADR-021: Treat generated, repository, and external content as untrusted input
**Status:** Accepted  
**Context:** The platform ingests TRDs, repository files, model outputs, CI results, and remote GitHub content. TRD-11 imposes strong security controls around external content and generated artifacts.  
**Decision:** Forge classifies all generated code, model output, repository content, remote API payloads, and external documents as untrusted unless explicitly validated within a defined trust boundary. Parsing, rendering, storage, and display paths must avoid implicit execution and must apply validation and sanitization appropriate to the subsystem.  
**Consequences:** Security posture improves and prompt/content injection risks are reduced. Some integrations require extra normalization and defensive coding. Convenience features that assume trusted content are restricted.  
**Rejected alternatives:**  
- **Trust repository-local content by default:** Rejected because repositories and generated outputs can be adversarial or malformed.  
- **Trust model outputs once consensus is reached:** Rejected because consensus does not imply safety.

## ADR-022: Preserve least privilege across credentials, tools, and repository operations
**Status:** Accepted  
**Context:** The system touches secrets, GitHub scopes, provider credentials, and local repositories. Its architecture separates shell trust from backend intelligence specifically to contain risk.  
**Decision:** Forge grants the minimum scopes and capabilities necessary for each subsystem and workflow step. Credentials are scoped, time-bounded where possible, and exposed only to the process that requires them for a specific operation. Repository and remote operations are constrained to defined workflow needs rather than broad ambient authority.  
**Consequences:** Compromise impact is reduced, but implementation requires more explicit permission handling and occasional user prompts or policy checks. Broad “just in case” scopes are disallowed.  
**Rejected alternatives:**  
- **Use a single all-powerful token everywhere:** Rejected because it conflicts with the security model and increases blast radius.  
- **Give backend long-lived unrestricted local and remote authority:** Rejected because it undermines process separation.

## ADR-023: Favor resumable, stateful pipeline execution over ephemeral stateless jobs
**Status:** Accepted  
**Context:** Building software from intent through multiple ordered PRs, review passes, CI cycles, and user approvals is inherently long-running. Users need continuity across app restarts, backend restarts, and approval delays.  
**Decision:** Forge models work as resumable stateful jobs with durable pipeline state rather than one-shot ephemeral tasks. The shell and backend cooperate to restore user-visible progress, pending approvals, and current PR stage after interruption according to subsystem contracts.  
**Consequences:** Reliability and user trust improve, especially for long-running builds. State management complexity increases, including persistence, reconciliation, and migration concerns. Pipeline stages must be idempotent or carefully guarded.  
**Rejected alternatives:**  
- **Purely in-memory job execution:** Rejected because long-running autonomy would be fragile across failures.  
- **Restart entire build from scratch after interruption:** Rejected because it wastes time, cost, and user context.

## ADR-024: Prefer native observability through structured status and artifact surfaces
**Status:** Accepted  
**Context:** A directed build agent must explain what it is doing across planning, generation, review, CI, and PR publication without becoming a chat transcript product. Users still need transparency and operators need diagnosable state.  
**Decision:** Forge exposes progress, decisions, artifacts, and failures through structured statuses, pipeline events, and reviewable outputs surfaced in the shell. Observability is based on explicit workflow state and artifacts rather than conversational logs as the primary mechanism.  
**Consequences:** The UI can present reliable stage-oriented feedback and debugging information. Engineering must maintain meaningful event semantics and artifact retention. Free-form logs may supplement but do not replace structured observability.  
**Rejected alternatives:**  
- **Opaque “working…” UX:** Rejected because autonomous systems need legibility.  
- **Chat transcript as the sole audit trail:** Rejected because it does not map well to PR-centric workflow state.

## ADR-025: Constrain subsystem boundaries to Shell, Backend, UI, Security, and GitHub workflow domains
**Status:** Accepted  
**Context:** The TRDs divide ownership across shell, backend intelligence, UI presentation, security controls, and repository automation. Without clear boundaries, responsibilities could blur and create coupling.  
**Decision:** Forge maintains explicit subsystem ownership boundaries: the shell owns native app/platform concerns; the backend owns intelligence and automation; UI components reflect shell-managed state and backend-reported workflow; security controls are enforced cross-cutting with shell trust ownership; GitHub workflow automation remains a backend domain. Cross-boundary dependencies are mediated through documented interfaces only.  
**Consequences:** The architecture remains modular and easier to reason about. Some feature work may require interface additions instead of direct calls across layers. Boundary violations are treated as design defects.  
**Rejected alternatives:**  
- **Allow feature teams to cut across layers opportunistically:** Rejected because it leads to drift and weakens security and maintainability.  
- **Collapse UI and backend concerns into one shared logic layer:** Rejected because it conflicts with the two-process model and ownership clarity.