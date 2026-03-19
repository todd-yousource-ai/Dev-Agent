# DECISIONS.md

## ADR-001: Build Forge as a native macOS two-process system
**Status:** Accepted  
**Context:** The platform must provide a native desktop experience, secure local secret handling, strong process isolation, and autonomous software delivery against user-supplied repositories and specifications. The product definition requires a shell responsible for UI, auth, and local trust boundaries, and a backend responsible for planning, generation, review, and GitHub operations.  
**Decision:** Forge is implemented as a two-process architecture: a native Swift/SwiftUI macOS shell and a Python backend. The Swift shell owns UI, authentication, Keychain access, process orchestration, and the local control plane. The Python backend owns consensus inference, planning, code generation, review, CI orchestration, and GitHub interactions.  
**Consequences:** Security-critical OS integrations remain in Swift. Model orchestration and automation logic remain in Python. Cross-process protocols become first-class interfaces and must be versioned, authenticated, and testable. Some complexity is introduced in lifecycle management, IPC, and debugging.  
**Rejected alternatives:** A single monolithic app was rejected because it weakens isolation and mixes OS-trust concerns with untrusted content processing. A web app was rejected because it does not satisfy native macOS security and UX requirements. A pure Python desktop shell was rejected because it is weaker for native auth, Keychain, and platform integration.

## ADR-002: Make the TRDs the source of truth for all subsystems
**Status:** Accepted  
**Context:** The platform spans UI, orchestration, security, GitHub automation, CI, and consensus model behavior. A single authoritative specification is needed to prevent drift and ad hoc implementation.  
**Decision:** The 12 TRDs in `forge-docs/` are the normative source of truth. Code, tests, interfaces, state machines, and error contracts must conform to them. Significant design decisions are recorded in this file as implementation-level ADRs aligned to the TRDs, not as replacements for them.  
**Consequences:** Engineers and agents must consult the owning TRD before changing a subsystem. Ambiguity is resolved by reading TRDs first, not by inferring from code. This improves consistency but raises the bar for making undocumented changes.  
**Rejected alternatives:** Code-as-spec was rejected because the system is too cross-cutting and security-sensitive. Informal docs were rejected because they cannot reliably govern interfaces and constraints across subsystems.

## ADR-003: Treat Forge as a directed build agent, not a chat product
**Status:** Accepted  
**Context:** Product behavior, UI, and orchestration depend on whether the system is interactive conversation software or a specification-driven delivery engine. The README defines Forge as a build agent that turns intent and TRDs into sequenced pull requests.  
**Decision:** Forge is designed as a directed autonomous build agent. The primary workflow is: ingest repository and TRDs, accept user intent, generate a PRD/plan, decompose into ordered pull requests, implement and review each PR via consensus, run CI, and open draft PRs for human review. Chat-style freeform interaction is secondary or excluded from core architecture.  
**Consequences:** UX, state machines, telemetry, and backend APIs optimize for task pipelines, approvals, progress visibility, and artifact traceability rather than conversational continuity. This narrows scope and improves reliability.  
**Rejected alternatives:** A general chat assistant was rejected because it diffuses the product focus. IDE autocomplete was rejected because it does not satisfy the autonomous PR-based delivery model.

## ADR-004: Keep Swift responsible for trust-boundary functions
**Status:** Accepted  
**Context:** The shell must own local secrets, user identity, biometrics, app lifecycle, and process supervision. These responsibilities sit within the OS trust boundary and require native platform APIs.  
**Decision:** Swift owns authentication, session lifecycle, Keychain storage, biometric gating, app installation/update integration, socket bootstrap, backend process creation, monitoring, and restart policy. Python never directly manages system secrets or native auth prompts.  
**Consequences:** Secret exposure surface is reduced. Backend portability is preserved while local trust remains centralized. Some operations require explicit request/response handoffs from backend to shell.  
**Rejected alternatives:** Allowing Python direct access to secrets was rejected for security and platform-integration reasons. Sharing trust-boundary responsibilities evenly across both processes was rejected because it creates ambiguous ownership.

## ADR-005: Keep Python responsible for intelligence and delivery automation
**Status:** Accepted  
**Context:** Planning, consensus, code generation, review, and GitHub automation benefit from Python’s ecosystem and the need to integrate multiple model providers, repo tooling, and CI workflows.  
**Decision:** Python owns the consensus engine, provider adapters, planning pipeline, code generation pipeline, review cycle, GitHub API interactions, branch/PR automation, and documentation regeneration workflows.  
**Consequences:** Backend logic can evolve rapidly and leverage mature SDKs. The shell remains thin and stable. The backend becomes the main locus for deterministic orchestration testing and failure handling.  
**Rejected alternatives:** Implementing orchestration in Swift was rejected due to ecosystem friction and slower iteration. Splitting consensus logic across both processes was rejected because it complicates correctness and observability.

## ADR-006: Use an authenticated Unix domain socket with line-delimited JSON for IPC
**Status:** Accepted  
**Context:** The shell and backend require a local IPC mechanism that is simple, inspectable, stream-friendly, and compatible with both Swift and Python. The architecture docs specify an authenticated Unix socket using line-delimited JSON.  
**Decision:** Cross-process communication uses a local authenticated Unix domain socket with one JSON message per line. Messages are structured, typed by envelope fields, and validated on both sides. Authentication and connection bootstrap are controlled by the shell.  
**Consequences:** The protocol is easy to debug and language-agnostic. Streaming progress and events are straightforward. Message framing is simple. This requires careful schema discipline and robust handling of partial writes, reconnects, and version mismatch.  
**Rejected alternatives:** XPC-only transport was rejected because the backend is Python and portability of protocol handling is simpler with sockets. HTTP/gRPC was rejected as heavier than needed for local IPC. StdIO pipes were rejected because lifecycle, authentication, and reconnection are less robust.

## ADR-007: Version all cross-process protocol messages
**Status:** Accepted  
**Context:** The shell and backend will evolve independently across updates, restarts, and failure recovery. A stable contract is required to avoid silent incompatibilities.  
**Decision:** Every IPC message schema includes explicit protocol versioning and typed payloads. Compatibility checks occur during handshake, and incompatible versions fail closed with user-visible remediation.  
**Consequences:** Releases can evolve safely with explicit migration behavior. Additional engineering is required to maintain schema compatibility and tests.  
**Rejected alternatives:** Implicit version compatibility was rejected because it leads to fragile runtime failures. Shared internal structs without wire versioning were rejected because they do not survive independent evolution.

## ADR-008: Fail closed on authentication, protocol, and trust-boundary errors
**Status:** Accepted  
**Context:** The platform handles credentials, repositories, generated code, and external provider responses. Security-sensitive failures must not degrade into permissive behavior. TRD-11 governs this security posture.  
**Decision:** Authentication failures, session validation failures, IPC authentication failures, secret access failures, and unsafe-content gate failures terminate or block the relevant workflow by default. The system does not silently continue in a reduced-security mode.  
**Consequences:** Some user-visible interruptions increase, but trust guarantees are preserved. Error handling and remediation UX become critical.  
**Rejected alternatives:** Best-effort continuation was rejected because it creates hidden security regressions. Silent retries without user awareness were rejected for high-risk trust operations.

## ADR-009: Never execute generated code inside Forge
**Status:** Accepted  
**Context:** The repository guidance explicitly states that neither process executes generated code. This is foundational to the security model for untrusted model output.  
**Decision:** Forge does not run generated application code as part of local execution. Validation is limited to static processing, repository operations, and CI workflows in controlled environments defined by the platform. Any test execution is delegated to the repository’s CI or explicit non-generated tooling paths governed by security controls.  
**Consequences:** Local compromise risk from model output is reduced. Some classes of validation are deferred to CI, increasing dependency on pipeline feedback loops. Product messaging and UX must set expectations appropriately.  
**Rejected alternatives:** Running generated code locally for faster validation was rejected because it materially expands the attack surface. Sandboxed local execution was rejected as out of scope for the initial security model.

## ADR-010: Use a two-model consensus engine with Claude arbitration
**Status:** Accepted  
**Context:** The product promise is based on parallel generation and review using two model providers, with Claude arbitrating outcomes. A single-model approach does not satisfy the intended reliability model.  
**Decision:** Forge uses at least two model providers in parallel for implementation and review stages, with Claude serving as the final arbiter in result selection and adjudication. Provider adapters normalize prompts, responses, errors, and capability differences.  
**Consequences:** Quality and resilience improve through disagreement detection and arbitration. Cost, latency, and orchestration complexity increase. Backend design must support provider heterogeneity and partial failure.  
**Rejected alternatives:** Single-model generation was rejected because it reduces robustness and does not match product requirements. Equal-weight voting without arbitration was rejected because deadlocks and low-quality convergence are harder to resolve.

## ADR-011: Normalize model providers behind adapter interfaces
**Status:** Accepted  
**Context:** Different LLM providers vary in API shape, latency, token accounting, streaming behavior, and failure modes. Consensus orchestration requires a stable abstraction.  
**Decision:** All model interactions are mediated through provider adapters with normalized request/response objects, timeout contracts, retry policies, streaming event semantics, and structured error categories. The consensus engine depends on the adapter interface, not provider-specific SDKs.  
**Consequences:** Providers can be swapped or extended with minimal impact on orchestration logic. Adapter maintenance becomes a dedicated concern.  
**Rejected alternatives:** Calling provider SDKs directly from business logic was rejected because it couples orchestration to vendor specifics. A lowest-common-denominator abstraction was rejected because it would discard capabilities needed for consensus behavior.

## ADR-012: Decompose user intent into PRD, then ordered PR units
**Status:** Accepted  
**Context:** The system must convert broad user intent into a build plan that is reviewable, incremental, and suitable for autonomous execution. The README describes a PRD-level plan followed by PR decomposition.  
**Decision:** Forge first derives a structured PRD/implementation plan from the repository, TRDs, and user intent. It then decomposes that plan into a sequence of logically scoped pull requests with explicit dependencies, acceptance criteria, and completion signals.  
**Consequences:** Execution becomes incremental and reviewable. Failure isolation improves. Planning becomes a first-class artifact requiring persistence and UX visibility.  
**Rejected alternatives:** Generating one large branch for the entire intent was rejected because it reduces reviewability and increases rollback cost. Ad hoc task-level generation without a planning artifact was rejected because sequencing quality degrades.

## ADR-013: Use pull requests as the primary delivery unit
**Status:** Accepted  
**Context:** Human oversight is a core product behavior. The natural boundary for review, CI, and merge control is the pull request.  
**Decision:** Every logical implementation unit is delivered as a Git branch plus a draft pull request. Forge advances to the next planned unit only according to the workflow state defined by approval and merge progression.  
**Consequences:** All output is traceable through normal GitHub review mechanics. Users retain control over merge gates. Throughput is bounded by PR lifecycle states rather than unrestricted branch mutation.  
**Rejected alternatives:** Direct commits to main were rejected because they remove review control. Patch file export was rejected because it weakens integration with repository workflows.

## ADR-014: Gate autonomous progress on human review milestones
**Status:** Accepted  
**Context:** Forge is autonomous but not fully self-authorizing. The product promise includes user review and merge gating between units of work.  
**Decision:** The system pauses or conditions subsequent work based on explicit workflow states such as draft PR opened, CI completed, user approval, and merge status. Automation may prepare the next unit while prior review is ongoing only where allowed by dependency rules.  
**Consequences:** Human control is preserved. Queueing and dependency management become important to maintain throughput. Some latency is accepted in exchange for governance.  
**Rejected alternatives:** Fully unattended merge-and-continue behavior was rejected because it undermines safety and trust. Requiring synchronous user approval for every internal substep was rejected as too interruptive.

## ADR-015: Enforce a three-pass review cycle before PR publication
**Status:** Accepted  
**Context:** Generated code requires structured scrutiny before reaching human review. The product definition includes a three-pass review cycle.  
**Decision:** Each PR candidate undergoes a defined multi-pass review process in the backend before publication. Passes are separately reasoned and recorded, and unresolved review failures block PR creation or trigger regeneration/escalation.  
**Consequences:** Code quality and consistency improve. Runtime and token cost increase. Review artifacts become part of the audit trail.  
**Rejected alternatives:** Single-pass review was rejected as insufficient for autonomous delivery quality. Human-only review before any machine review was rejected because it shifts too much filtering burden to users.

## ADR-016: Run repository validation through CI as the authoritative execution environment
**Status:** Accepted  
**Context:** Forge must verify changes without executing generated code locally. CI provides a controlled, repository-native validation path.  
**Decision:** Continuous integration is the authoritative environment for building, testing, and validating repository changes. Forge prepares changes and invokes or monitors CI workflows, using results as gating signals for PR readiness.  
**Consequences:** Validation remains close to real repository conditions and existing team workflows. CI availability and quality become dependencies. Feedback loops may be slower than local execution.  
**Rejected alternatives:** Local execution as the primary validator was rejected for security reasons. No automated validation was rejected because it would undermine confidence in generated PRs.

## ADR-017: Centralize GitHub operations in the backend
**Status:** Accepted  
**Context:** Branching, commits, PR creation, comment updates, and CI integration are tightly coupled to planning and review logic.  
**Decision:** The Python backend owns all GitHub and repository automation, including branch management, commit creation, draft PR opening, status polling, and related workflow artifacts. The shell displays state and requests user confirmations where required.  
**Consequences:** Delivery logic stays cohesive. Backend needs robust credential mediation and error handling. Shell remains simpler and does not duplicate repo state logic.  
**Rejected alternatives:** Splitting GitHub operations across shell and backend was rejected because ownership becomes unclear. Performing GitHub actions primarily in the shell was rejected because it couples UI to automation internals.

## ADR-018: Keep credentials in macOS Keychain under shell control
**Status:** Accepted  
**Context:** The platform requires secure storage for provider credentials and user tokens. Native macOS facilities are the correct trust anchor.  
**Decision:** Secrets are stored in the macOS Keychain and accessed only by the Swift shell. The backend receives only the minimum scoped material or delegated operation needed for a task, according to the security contract.  
**Consequences:** Secret management aligns with platform security. Additional IPC flows are needed when backend operations require authenticated access.  
**Rejected alternatives:** Storing secrets in environment variables, local config files, or backend-managed stores was rejected because they weaken local security and secret governance.

## ADR-019: Require biometric or equivalent local user gate for sensitive sessions
**Status:** Accepted  
**Context:** High-impact actions such as unlocking secrets, authorizing sessions, or re-entering a privileged workflow need local user confirmation under the macOS trust model.  
**Decision:** The shell uses biometric authentication or an OS-equivalent secure local gate to unlock sensitive capabilities and manage session lifecycle. Session state is explicit, time-bounded, and revocable.  
**Consequences:** Unauthorized local use is harder. UX must handle lock, unlock, timeout, and reauthentication flows gracefully.  
**Rejected alternatives:** Password-only app-local auth was rejected because native secure auth is stronger and more consistent with the platform. Permanent unlocked sessions were rejected because they increase exposure.

## ADR-020: Manage backend lifecycle under shell supervision
**Status:** Accepted  
**Context:** The backend is a worker process whose correctness and trust depend on supervised startup, health monitoring, and restart behavior.  
**Decision:** The shell launches, monitors, and restarts the Python backend according to explicit lifecycle rules. Crash detection, stale-session invalidation, and reconnection behavior are defined by the shell-owned state machine.  
**Consequences:** A single authority owns process health. Recovery UX and telemetry become essential. The backend cannot assume persistence across shell state transitions.  
**Rejected alternatives:** Letting the backend daemonize independently was rejected because it weakens user control and session coupling. Manual user restarts were rejected because they reduce resilience.

## ADR-021: Structure the shell with clear module boundaries and owned state
**Status:** Accepted  
**Context:** The macOS shell spans installation, auth, process control, IPC, and UI. Without clear module ownership, Swift code becomes tightly coupled and hard to verify.  
**Decision:** The shell is organized into explicit modules with well-defined responsibilities, concurrency rules, and state ownership. UI state, session state, process state, and transport state are separated and exposed through stable interfaces.  
**Consequences:** The shell remains testable and maintainable. Additional upfront design discipline is required.  
**Rejected alternatives:** A single shared app state object for all concerns was rejected because it causes coupling and race-prone behavior. Feature code with implicit cross-module access was rejected for maintainability reasons.

## ADR-022: Use SwiftUI for the shell UI with view-model-driven state projection
**Status:** Accepted  
**Context:** The product requires a native macOS interface with rich progress, workflow state, and review artifacts. SwiftUI is the required shell technology.  
**Decision:** The shell UI is implemented in SwiftUI, with views driven by explicit view models or equivalent presentation-state abstractions derived from owned application state. UI components are projections of system state, not direct owners of orchestration logic.  
**Consequences:** Native UI behavior and reactive updates are supported. Architecture must guard against state duplication and side effects in views.  
**Rejected alternatives:** AppKit-first UI was rejected for the primary architecture because the product is specified around SwiftUI. Embedding orchestration logic directly in views was rejected because it harms testability.

## ADR-023: Design the UI around pipeline visibility rather than conversational history
**Status:** Accepted  
**Context:** Because Forge is a build agent, users need to understand plans, PR queues, CI results, blockers, and approvals, not a chat log.  
**Decision:** Primary UI surfaces emphasize repository context, current plan, active PR unit, review/CI status, security/session state, and actionable approvals. Conversational metaphors are not the organizing principle of the product.  
**Consequences:** Users can reason about progress and control points more effectively. Some users may expect chat-like flexibility and need onboarding.  
**Rejected alternatives:** Chat-first UI was rejected because it obscures the staged delivery model. A minimal background-only agent was rejected because it weakens trust and reviewability.

## ADR-024: Represent workflow progression as explicit state machines
**Status:** Accepted  
**Context:** Planning, generation, review, CI, PR publication, approval, and process lifecycle all involve multi-step transitions with failure and retry branches.  
**Decision:** Core workflows are modeled as explicit state machines with named states, legal transitions, and terminal/error conditions. This applies to sessions, backend connectivity, plan execution, and PR unit lifecycle.  
**Consequences:** Behavior is easier to test, reason about, and recover. Implementation must resist ad hoc side-channel transitions.  
**Rejected alternatives:** Implicit state derived from scattered flags was rejected because it creates inconsistent behavior. Freeform event handling without state models was rejected for reliability reasons.

## ADR-025: Preserve complete artifact traceability across plan, generation, review, and PR output
**Status:** Accepted  
**Context:** Autonomous delivery requires auditability: what intent produced which plan, which model outputs, which review findings, and which PR.  
**Decision:** Forge records durable links between user intent, repository snapshot, TRD inputs, generated plan artifacts, review artifacts, CI outcomes, and resulting branches/PRs.  
**Consequences:** Users can inspect provenance and debug failures. Storage, privacy, and retention policies must be managed carefully.  
**Rejected alternatives:** Keeping only final PR artifacts was rejected because it loses explainability. Storing no intermediate artifacts was rejected because it impairs debugging and trust.

## ADR-026: Treat external content and model output as untrusted input
**Status:** Accepted  
**Context:** Repositories, specifications, prompts, provider responses, and generated code can all carry malicious or malformed content. TRD-11 requires a strict security posture.  
**Decision:** All external content, including model output and repository content, is treated as untrusted. Parsing, rendering, storage, and downstream use are constrained by validation, encoding, and allowlist-based handling where applicable.  
**Consequences:** Security improves, but implementation complexity increases in prompt construction, rendering, and artifact processing.  
**Rejected alternatives:** Trusting repository-local content or model output by default was rejected because it creates multiple injection and compromise paths.

## ADR-027: Minimize credential and privilege exposure to the least required scope and duration
**Status:** Accepted  
**Context:** The backend needs to perform authenticated tasks, but unrestricted token access would enlarge blast radius.  
**Decision:** Forge grants only the minimum scope and lifetime of credentials necessary for each operation. Sessions are bounded, secrets are not broadly cached, and privileged operations require explicit policy-compliant pathways through the shell.  
**Consequences:** Compromise impact is reduced. Token refresh, delegation, and session UX become more complex.  
**Rejected alternatives:** Long-lived globally available backend credentials were rejected because they violate least privilege. Requiring repeated full re-auth for every operation was rejected as impractical.

## ADR-028: Prefer deterministic orchestration around nondeterministic model behavior
**Status:** Accepted  
**Context:** LLM outputs are probabilistic. A reliable build agent must constrain that variability with explicit orchestration and acceptance logic.  
**Decision:** Forge wraps model calls in deterministic pipeline steps, structured prompts, validation rules, review gates, and explicit retry/escalation policies. Business logic does not rely on unconstrained freeform model behavior.  
**Consequences:** Repeatability and debuggability improve. Some flexibility and creativity are sacrificed in favor of operational predictability.  
**Rejected alternatives:** Agentic freeform loops with minimal structure were rejected because they are too hard to validate. Manual operator adjudication of every model variation was rejected as non-scalable.

## ADR-029: Model partial provider failure as a first-class operational case
**Status:** Accepted  
**Context:** Consensus depends on multiple providers, each of which can timeout, rate limit, or degrade independently.  
**Decision:** The backend explicitly handles partial provider failure with categorized errors, retries where permitted, degraded-path decisions where safe, and user-visible status when consensus cannot be completed to policy.  
**Consequences:** The system is more resilient and transparent. Consensus rules and failure semantics become more complex.  
**Rejected alternatives:** Assuming both providers are always available was rejected as unrealistic. Silently substituting one provider for all roles was rejected because it undermines the consensus quality model.

## ADR-030: Use structured error contracts across subsystem boundaries
**Status:** Accepted  
**Context:** The shell, backend, provider adapters, and GitHub integrations all emit failures that must be actionable and displayable.  
**Decision:** Errors crossing boundaries are categorized, structured, and stable enough for programmatic handling, telemetry, and user messaging. Internal exceptions are translated into boundary-safe error forms.  
**Consequences:** Recovery logic and UX become more consistent. Error taxonomy maintenance is required.  
**Rejected alternatives:** Passing through raw provider, Python, or Swift errors directly was rejected because it leaks implementation detail and hinders reliable handling.

## ADR-031: Favor asynchronous, event-driven progress reporting
**Status:** Accepted  
**Context:** Long-running operations such as planning, generation, review, and CI polling need responsive UI updates and cancel-safe behavior.  
**Decision:** The backend emits structured progress and lifecycle events over IPC. The shell subscribes to and renders these events into user-facing state rather than blocking on synchronous RPC-style interactions alone.  
**Consequences:** UX remains responsive and transparent during long tasks. Event ordering, deduplication, and replay semantics require care.  
**Rejected alternatives:** Pure request/response blocking APIs were rejected because they are poor fits for long workflows. Polling internal state from the shell was rejected because it is less efficient and less precise.

## ADR-032: Make cancellation and recovery explicit parts of workflow design
**Status:** Accepted  
**Context:** Users may cancel runs, sessions may expire, providers may fail, and the backend may restart. These are normal, not exceptional, conditions.  
**Decision:** Core workflows support explicit cancellation, retry, resume, or restart behavior according to defined state-machine rules. Partial artifacts are either preserved with status or cleaned up deterministically.  
**Consequences:** User trust improves because behavior is predictable under interruption. Implementation complexity rises significantly.  
**Rejected alternatives:** Treating cancellation as a generic crash path was rejected because it makes recovery opaque. Always discarding all partial state was rejected because it wastes work and impairs traceability.

## ADR-033: Integrate auto-update through the shell distribution model
**Status:** Accepted  
**Context:** The shell owns installation and packaging and is specified to support standard macOS app distribution with Sparkle auto-update.  
**Decision:** The macOS app bundle is the primary distribution artifact, installed via standard drag-to-Applications flow, with shell-managed auto-update using Sparkle or the TRD-specified equivalent.  
**Consequences:** Updates align with native macOS expectations. Release engineering must manage signing, update feeds, and compatibility with backend packaging.  
**Rejected alternatives:** A custom updater was rejected because it adds avoidable security and maintenance burden. Package-manager-only distribution was rejected because it does not match the primary product distribution model.

## ADR-034: Package the backend as a shell-managed application component
**Status:** Accepted  
**Context:** The backend must be present, version-compatible, and controllable by the shell. Independent backend installation would complicate trust and supportability.  
**Decision:** The Python backend is packaged and shipped as a component managed by the macOS shell, with compatibility tied to the shell release and validated at startup.  
**Consequences:** Deployment is simpler for users. Release coupling between shell and backend increases. Backend hot-swapping outside compatible versions is disallowed.  
**Rejected alternatives:** Separately installed backend runtimes were rejected because they complicate support, compatibility, and security. Download-on-first-run was rejected unless governed by the shell’s trusted update mechanism.

## ADR-035: Prefer repository-native workflows over Forge-specific conventions where possible
**Status:** Accepted  
**Context:** Forge operates on user repositories with existing GitHub, CI, and branch practices. Excessive tool-specific conventions would reduce adoption and correctness.  
**Decision:** Forge integrates with repository-native structures—Git branches, pull requests, CI workflows, tests, and documentation locations—while adding only the minimal metadata and artifacts needed for its operation.  
**Consequences:** Adoption friction is lower and outputs fit existing team processes. The system must tolerate repository variability.  
**Rejected alternatives:** Requiring a Forge-exclusive repository layout or workflow model was rejected because it would constrain users unnecessarily. Fully generic behavior with no assumptions at all was rejected because some stable operating contract is still required.

## ADR-036: Regenerate documentation as an optional post-build workflow, not a prerequisite
**Status:** Accepted  
**Context:** The product may optionally regenerate documentation after implementation completes, but the core value is autonomous code delivery through PRs.  
**Decision:** Documentation regeneration is supported as an optional downstream workflow triggered after or alongside code delivery according to plan and repository policy. It is not required for every PR unless the plan or repository standards demand it.  
**Consequences:** The core implementation pipeline remains focused and efficient. Documentation updates can still be automated when appropriate.  
**Rejected alternatives:** Mandatory documentation regeneration for every change was rejected as unnecessarily rigid. No documentation support was rejected because some repositories require automated doc upkeep.

## ADR-037: Optimize for reviewability and safety over maximum raw throughput
**Status:** Accepted  
**Context:** Autonomous generation could be accelerated by larger batch sizes and fewer gates, but the product promise centers on trustworthy, reviewable delivery.  
**Decision:** When tradeoffs arise, Forge prioritizes smaller logical PRs, stronger review gates, explicit approvals, and artifact traceability over the highest possible end-to-end speed.  
**Consequences:** User trust and merge quality improve. Absolute throughput may be lower than a less-governed system.  
**Rejected alternatives:** Aggressive batching with limited review was rejected because it undermines the pull-request-based governance model. Hyper-optimized silent automation was rejected because it weakens confidence and control.

## ADR-038: Test subsystems at their boundaries, especially protocol and security contracts
**Status:** Accepted  
**Context:** The architecture relies on strong contracts between shell, backend, providers, and external services. Boundary failures are the most expensive and security-relevant.  
**Decision:** Testing emphasizes protocol conformance, state-machine behavior, structured error contracts, security controls, and deterministic orchestration at subsystem boundaries, in addition to internal unit tests.  
**Consequences:** Contract regressions are caught earlier. Test harnesses for IPC, provider simulation, and lifecycle recovery are required.  
**Rejected alternatives:** UI-only end-to-end confidence was rejected because it misses many boundary failures. Pure unit-test focus was rejected because it does not verify subsystem integration contracts.