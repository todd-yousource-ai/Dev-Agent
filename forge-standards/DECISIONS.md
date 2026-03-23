# DECISIONS.md

## Native macOS shell with bundled Python backend
**Status:** Accepted  
**Context:** Crafted is specified as a native macOS AI coding agent, not a web app or editor plugin. The product must provide macOS-native installation, UI, auth, Keychain integration, and local orchestration while also running a sophisticated generation and GitHub automation backend. The repository guidance and TRDs define a two-process architecture with Swift owning UI and secrets, and Python owning intelligence and repository automation.  
**Decision:** Forge adopts a two-process local architecture: a native Swift/SwiftUI macOS shell and a bundled Python 3.12 backend. The Swift shell owns installation, updates, UI, authentication, Keychain, lifecycle, and privileged local integrations. The Python backend owns planning, consensus, generation, validation loops, and GitHub operations.  
**Consequences:** The platform is macOS-specific by design. UI and security-sensitive logic must remain in Swift. AI orchestration and repository automation must remain in Python. Packaging, upgrades, process supervision, and cross-process contracts become first-class engineering concerns.  
**Rejected alternatives:**  
- Single-process Swift-only application — rejected because the intelligence pipeline, provider integrations, and repository automation are better served by Python ecosystem capabilities.  
- Electron or web container — rejected because the shell must provide native macOS security, Keychain, biometrics, and system integration.  
- Pure Python desktop app — rejected because secrets, auth UX, and native system behavior belong in a native shell.

## Strict TRD-driven architecture
**Status:** Accepted  
**Context:** The product is fully specified by 16 TRDs and agent guidance explicitly states that the TRDs are the source of truth. Multiple subsystems interact across security, UI, orchestration, and GitHub automation; uncontrolled local conventions would cause drift and unsafe behavior.  
**Decision:** All significant subsystem behavior, interfaces, error contracts, and testing expectations are derived from the TRDs. Implementation decisions that are not spelled out in code comments or local docs must align with the applicable TRD owner document.  
**Consequences:** Engineers must trace changes to the owning TRD before implementation. Cross-cutting changes require checking dependent TRDs, especially security requirements in TRD-11. Local convenience behavior cannot override documented contracts.  
**Rejected alternatives:**  
- Team conventions as primary authority — rejected because they create ambiguity and drift.  
- Code-as-spec only — rejected because the platform spans two languages and many boundaries requiring explicit contracts.  
- Ad hoc feature interpretation — rejected because safety and consistency depend on deterministic requirements.

## Authenticated local IPC over Unix domain socket with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend must communicate locally, reliably, and with a clear boundary between trusted secret-handling code and untrusted external-content-processing code. The repository guidance explicitly defines an authenticated Unix socket and line-delimited JSON transport.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket and line-delimited JSON messages. The shell supervises connection establishment and message framing. The protocol is explicit, typed by message kind, and treated as a stable internal contract.  
**Consequences:** Both processes must implement schema validation, framing discipline, and authentication for every session. IPC messages must remain compact, explicit, and version-tolerant. Debugging and observability can rely on structured message flows.  
**Rejected alternatives:**  
- In-process FFI bridge — rejected because it weakens isolation between secret-owning shell code and AI/backend logic.  
- HTTP localhost API — rejected because it introduces unnecessary network semantics and attack surface for a local-only boundary.  
- XPC for everything — rejected because Python interoperability and backend portability are simpler with a Unix socket contract.

## Swift shell is the sole owner of secrets and identity
**Status:** Accepted  
**Context:** The platform handles provider credentials, GitHub credentials, and user authentication. Security guidance states that the Swift process owns authentication and secrets. The backend processes external content and generated code artifacts, so secret exposure must be minimized.  
**Decision:** All credentials, tokens, and secret persistence are owned by the Swift shell using macOS Keychain and native authentication controls. The Python backend never stores long-lived secrets and receives only the minimum scoped material required for a task, when permitted by the security model.  
**Consequences:** Any feature requiring credentials must be brokered through shell-managed flows. Backend code must be designed to function with delegated capability tokens or ephemeral inputs instead of direct secret ownership. Security review is mandatory for any exception.  
**Rejected alternatives:**  
- Duplicate secret storage in Python — rejected because it expands exposure and bypasses native security controls.  
- Environment variable based long-lived secret handling — rejected because it is brittle and less secure on end-user systems.  
- Shared config-file secret storage — rejected because Keychain is the correct macOS-native control plane.

## Biometric and session-gated access to privileged actions
**Status:** Accepted  
**Context:** The shell owns user identity and session lifecycle. The application performs sensitive operations such as revealing account state, using credentials, and authorizing repository actions. Native desktop UX should leverage OS-level authentication where appropriate.  
**Decision:** Privileged actions are gated by shell-managed session controls, with biometric or equivalent OS-backed authentication used where required by policy. Session state is explicit and expires according to shell lifecycle rules.  
**Consequences:** Sensitive features must be invocable only through session-aware shell pathways. UX flows must account for unlock, re-authentication, failure, and timeout states. The backend cannot silently escalate access.  
**Rejected alternatives:**  
- Always-unlocked local app model — rejected because it is incompatible with local secret custody.  
- Backend-managed auth state — rejected because auth ownership belongs in the shell.  
- Custom credential prompts in place of OS facilities — rejected because native security UX is safer and more consistent.

## No execution of generated code by the platform
**Status:** Accepted  
**Context:** The repository guidance explicitly states that neither process ever executes generated code. The product produces implementation, tests, and pull requests, but generated code is external content until validated through repository tooling and CI boundaries. This is a core safety property.  
**Decision:** Forge never directly executes generated application code as part of agent operation. Validation is limited to approved repository tooling, static analysis, linting, tests, and CI invocation under the defined security model rather than arbitrary runtime execution of generated artifacts.  
**Consequences:** Product features must avoid “run this generated app locally” or autonomous runtime probing of generated binaries. Validation design favors deterministic toolchain invocations and CI-mediated checks. Some classes of dynamic verification are intentionally out of scope.  
**Rejected alternatives:**  
- Sandboxed execution of generated code — rejected because it still meaningfully expands risk and violates stated platform constraints.  
- Local autonomous app launching for QA — rejected for the same safety reason.  
- Unrestricted tool use by the backend — rejected because the platform is a directed build agent, not a general-purpose autonomous executor.

## Directed build agent, not chat or autocomplete
**Status:** Accepted  
**Context:** README explicitly defines the product as neither a chat interface nor code autocomplete. The user supplies repository context, TRDs, and intent; the system plans, generates, validates, and opens pull requests. Product design must stay optimized for deterministic delivery rather than conversational breadth.  
**Decision:** Forge is designed as a directed software build agent with intent intake, confidence assessment, plan decomposition, PR sequencing, implementation generation, validation, and PR creation. Conversational UX is subordinate to workflow execution and review gating.  
**Consequences:** UI, state models, telemetry, and testing focus on task progression, artifacts, and approvals rather than open-ended dialogue. Feature requests that turn the product into a chatbot or IDE copilot should be rejected unless they directly support the build workflow.  
**Rejected alternatives:**  
- General chat assistant UX — rejected because it dilutes the core workflow.  
- Inline code completion product — rejected because it is a different product category.  
- Fully autonomous merge-and-deploy agent — rejected because human review gates are central to trust and control.

## Consensus generation using multiple providers with arbitration
**Status:** Accepted  
**Context:** The product description specifies a two-model consensus engine using Claude and GPT-4o in parallel with Claude arbitrating every result. The platform must increase quality and confidence for repository changes while reducing single-model failure modes.  
**Decision:** Implementation generation uses multiple LLM providers in parallel for substantive coding tasks, with an explicit arbitration stage producing the accepted result. Consensus and arbitration are treated as first-class pipeline stages, not incidental prompt patterns.  
**Consequences:** Provider abstractions, prompt contracts, latency budgets, and result comparison become core backend design elements. Failures must be attributable by provider and stage. The pipeline must tolerate provider degradation and partial availability.  
**Rejected alternatives:**  
- Single-model generation — rejected because it increases correlated failure risk and weakens confidence.  
- Majority voting without arbitration — rejected because code synthesis requires qualitative reconciliation, not just counting outputs.  
- Provider-specific bespoke flows everywhere — rejected because it would fragment the orchestration model.

## Confidence assessment before committing to work
**Status:** Accepted  
**Context:** The product description states that the agent assesses confidence in the scope before committing to it. This protects users from low-confidence, poorly bounded automation and improves planning quality.  
**Decision:** Before a build begins, the backend must evaluate scope clarity, repository readiness, and specification sufficiency, and surface a confidence determination that influences whether planning proceeds, blocks, or requests clarification.  
**Consequences:** Intake is not a blind “always start” action. UX and APIs must support clarification loops and blocked states. Confidence logic becomes part of acceptance criteria for orchestration changes.  
**Rejected alternatives:**  
- Immediate execution on every request — rejected because it leads to unsafe or low-value work.  
- Purely user-declared confidence — rejected because the system must independently assess readiness.  
- Hidden internal confidence only — rejected because users need actionable gating feedback.

## Hierarchical decomposition from intent to PRD plan to typed pull requests
**Status:** Accepted  
**Context:** The README specifies a decomposition path from intent to ordered PRD plan to a sequence of typed pull requests. Large software changes require structure, dependency ordering, and reviewable units.  
**Decision:** Forge decomposes work hierarchically: user intent becomes a PRD-level execution plan, and each PRD is further decomposed into ordered, typed PRs representing logical implementation units. PRs are the principal delivery artifact.  
**Consequences:** Planning data models must represent hierarchy, dependencies, ordering, and PR typing. Review UX must display progression across plan and PR levels. Pipeline execution must optimize for small, coherent, independently reviewable changes.  
**Rejected alternatives:**  
- One large PR per request — rejected because it reduces reviewability and increases failure blast radius.  
- Flat task list without hierarchy — rejected because it weakens planning discipline.  
- File-by-file autonomous commits — rejected because PRs should map to logical units, not incidental edit batches.

## Draft pull request as the default unit of delivery
**Status:** Accepted  
**Context:** The product creates pull requests for review, and the user gates, reviews, and merges. Trust in autonomous coding depends on preserving human control before merge.  
**Decision:** The default output of a completed implementation cycle is a draft pull request containing code, tests, and machine-generated rationale/metadata as defined by subsystem specs. Human approval remains the release gate for merge.  
**Consequences:** Backend logic must integrate tightly with GitHub branch and PR workflows. UI must support review status visibility and next-step guidance. Merge authority remains outside autonomous completion.  
**Rejected alternatives:**  
- Direct commit to main — rejected because it violates review and safety expectations.  
- Local patch export only — rejected because the product is intended to open GitHub PRs autonomously.  
- Automatic merge after CI — rejected because the user remains the gate.

## GitHub-centered repository workflow
**Status:** Accepted  
**Context:** The README and architecture describe opening GitHub pull requests and advancing work after approval. Repository automation, CI checks, branches, and PR metadata revolve around GitHub.  
**Decision:** Forge standardizes on GitHub as the initial source-control and PR orchestration platform. Branch creation, push, PR creation, status tracking, and merge-adjacent workflows are implemented against GitHub contracts first.  
**Consequences:** Backend abstractions should isolate provider-specific Git operations, but GitHub is the normative implementation target. Future SCM support must not compromise GitHub quality or expand scope prematurely.  
**Rejected alternatives:**  
- Multi-SCM support from day one — rejected because it increases complexity without matching the product spec.  
- Local Git-only workflow with no hosted provider integration — rejected because draft PRs are central to the product value.  
- GitHub Actions-only tight coupling with no abstraction — rejected because some portability is still desirable at the adapter boundary.

## Iterative validation pipeline with self-correction and fix loops
**Status:** Accepted  
**Context:** The README specifies generation followed by self-correction, lint gate, iterative fix loop, CI execution, and PR creation. Generated code quality requires explicit repair cycles, not a single-shot output model.  
**Decision:** The backend pipeline is multi-stage: generate, review/self-correct, run lint/static checks, apply iterative fixes, execute CI-oriented validation, and only then create or update a draft PR. Each stage produces structured outcomes that can trigger retries or blocking failure.  
**Consequences:** Orchestration must model stage state, retries, and stop conditions. Logs and telemetry must preserve stage-level evidence. UX must communicate whether the system is generating, correcting, blocked on validation, or ready for review.  
**Rejected alternatives:**  
- One-pass generation with no feedback loop — rejected because code quality would be too inconsistent.  
- Human-only repair after generation — rejected because the product’s value includes autonomous correction.  
- Unlimited retry loops — rejected because bounded iteration and explicit failure states are necessary.

## Typed subsystem boundaries and modular ownership
**Status:** Accepted  
**Context:** The shell and backend have distinct responsibilities, and the TRDs define subsystem ownership across shell, provider adapters, consensus engine, UI, and security. Clear boundaries reduce accidental coupling and security regressions.  
**Decision:** Forge uses explicit subsystem boundaries with strong ownership rules: shell modules own UI/platform concerns; backend modules own planning, provider integration, consensus, and repository automation; shared contracts are limited to versioned schemas and narrow service interfaces.  
**Consequences:** Cross-cutting shortcuts are discouraged. New features must be placed in the owning subsystem rather than whichever layer is easiest to modify. Testing and code review should align with subsystem responsibility.  
**Rejected alternatives:**  
- Broad utility layers shared across everything — rejected because they blur ownership.  
- Feature duplication in both processes — rejected because it creates drift and inconsistent behavior.  
- Informal message payloads without schemas — rejected because cross-process contracts need rigor.

## Native SwiftUI interface for workflow visualization and control
**Status:** Accepted  
**Context:** TRD-1 establishes a Swift/SwiftUI shell, and repository guidance references SwiftUI views, cards, and panels. The product needs rich stateful views for authentication, plans, PRs, validation progress, and review handoff.  
**Decision:** The user interface is implemented natively in SwiftUI with a view architecture aligned to shell-owned state and workflow models. UI components present structured build progress rather than free-form conversational windows.  
**Consequences:** UI state must be synchronized with backend pipeline state through typed shell models. macOS-native patterns and accessibility expectations apply. Web-rendered UI surfaces should remain exceptional, not primary.  
**Rejected alternatives:**  
- Web UI embedded in a native wrapper — rejected because a native app is part of the product definition.  
- CLI-first product with optional UI — rejected because the shell is foundational, not ancillary.  
- Chat transcript as primary UX — rejected because it does not fit the workflow-centered product.

## Sparkle-based application update strategy
**Status:** Accepted  
**Context:** TRD-1 lists Sparkle auto-update as part of shell responsibilities. Desktop distribution requires secure update delivery and a standard user experience for native macOS software.  
**Decision:** The macOS shell uses Sparkle for application update distribution and installation. Update behavior is implemented as a shell concern and integrated with app lifecycle and release signing requirements.  
**Consequences:** Release engineering must support Sparkle-compatible packaging and signing. Update UX and rollback expectations must fit Sparkle’s operating model. Backend version compatibility with shell releases must be managed carefully.  
**Rejected alternatives:**  
- App Store distribution only — rejected because the specified installation model is direct app distribution.  
- Custom updater — rejected because Sparkle is mature and already specified.  
- Manual-only updates — rejected because it degrades security and user experience.

## Local-first orchestration with remote providers as dependencies
**Status:** Accepted  
**Context:** Crafted is a native app that operates on a local repository while calling external model providers and GitHub. User trust and security depend on local control over orchestration state and artifact handling.  
**Decision:** Core workflow state, orchestration control, session state, and local repository interactions are managed on-device. External services are used for model inference and hosted repository workflows, but control flow remains local to the app.  
**Consequences:** The app must handle degraded connectivity and remote service failures gracefully. Local persistence, resumability, and recovery matter. The architecture avoids turning the product into a thin client for a hosted agent service.  
**Rejected alternatives:**  
- Cloud-orchestrated agent with local UI client — rejected because it would centralize secrets and reduce local control.  
- Browser-only SaaS implementation — rejected because it conflicts with the native shell and security model.  
- Purely offline system with no provider dependency — rejected because model and GitHub integrations are essential.

## Structured error contracts across subsystems
**Status:** Accepted  
**Context:** The TRDs emphasize interfaces and error contracts. In a two-process architecture with security-sensitive operations and multi-stage orchestration, ambiguous failures create unsafe retries and poor UX.  
**Decision:** Errors are modeled as structured contracts at subsystem boundaries, especially across IPC, provider adapters, auth flows, repository operations, and validation stages. Error classes must distinguish user-actionable issues, transient failures, security denials, and internal faults.  
**Consequences:** Logs, telemetry, and UI can present deterministic recovery paths. Retry logic can be policy-driven. New APIs must define explicit failure modes rather than rely on opaque strings or generic exceptions.  
**Rejected alternatives:**  
- Stringly-typed errors — rejected because they are hard to reason about across process boundaries.  
- Catch-all internal failures surfaced to users — rejected because they do not support recovery.  
- Silent fallback behavior — rejected because it obscures risk and system state.

## Security requirements are centralized and mandatory across all components
**Status:** Accepted  
**Context:** Repository guidance states that TRD-11 governs all components and must be consulted for any change touching credentials, external content, generated code, or CI. Security is not a feature slice; it is a cross-cutting control framework.  
**Decision:** Security policy is treated as a platform-wide controlling concern. Any subsystem decision involving secrets, content ingestion, code generation, CI, or external integrations must conform to the centralized security requirements before implementation.  
**Consequences:** Security review is required for many ordinary-seeming changes. Performance or convenience optimizations cannot bypass central controls. Documentation and tests must trace relevant security requirements where applicable.  
**Rejected alternatives:**  
- Per-team security interpretation — rejected because it causes inconsistent controls.  
- Security as a later hardening pass — rejected because the architecture itself encodes trust boundaries.  
- Best-effort security guidance — rejected because the product handles code, credentials, and repository automation.

## Human-in-the-loop progression between pull requests
**Status:** Accepted  
**Context:** The product description states that the agent builds the next PR while the user reads the last one, and that user approval is the gate for progression. This creates a supervised conveyor rather than uncontrolled autonomy.  
**Decision:** Forge supports sequential or overlapping PR production within a user-supervised plan, but progression through the plan remains subject to review and approval semantics. The system may prepare subsequent work, yet merge and acceptance remain human-controlled checkpoints.  
**Consequences:** Planning and execution state must represent approved, in-review, blocked, and ready-next statuses. The agent should optimize for reviewer throughput without assuming merge authority. Dependency handling between PRs must remain explicit.  
**Rejected alternatives:**  
- Fully serialized workflow with no lookahead — rejected because it wastes time and reduces throughput.  
- Fully autonomous multi-PR merge train — rejected because it weakens human oversight.  
- Single long-running branch instead of staged PRs — rejected because it harms reviewability and control.