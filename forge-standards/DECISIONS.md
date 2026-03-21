# DECISIONS.md

## Two-process native architecture
**Status:** Accepted  
**Context:** Forge is a native macOS AI coding agent with distinct trust boundaries and responsibilities. The product requires a native shell for installation, auth, UI, Keychain, and OS integration, while the intelligence layer needs rapid iteration, model/provider integrations, and repository automation. The TRDs define a split between Swift and Python.  
**Decision:** Forge is implemented as a two-process system: a native Swift/SwiftUI macOS shell and a separate Python backend. The Swift shell owns UI, authentication, session lifecycle, Keychain access, app packaging, updates, and local orchestration. The Python backend owns planning, consensus generation, review pipeline, documentation regeneration, CI/GitHub orchestration, and repository operations.  
**Consequences:** Clear separation of concerns, stronger secret isolation, and simpler enforcement of trust boundaries. Cross-process interfaces must be explicit, versioned, and failure-tolerant. Some features become more complex due to IPC and lifecycle management.  
**Rejected alternatives:**  
- **Single-process app:** Rejected because it weakens isolation between secrets/UI and untrusted external content/model output.  
- **All-native implementation:** Rejected because model/provider and repository automation evolve faster and are better suited to Python’s ecosystem.  
- **Backend-only/headless product:** Rejected because the product requires a native macOS user experience, auth gating, and local secret handling.

## Swift shell owns secrets and identity
**Status:** Accepted  
**Context:** The platform handles provider credentials, GitHub credentials/tokens, and session state. The security model requires that sensitive material be controlled by the most trusted component with native OS facilities.  
**Decision:** All secrets, authentication state, biometric gates, and session lifecycle controls are owned by the Swift shell. Secrets are stored in Keychain and never delegated as durable authority to the Python backend beyond the minimum needed for a scoped operation.  
**Consequences:** The shell becomes the root of local trust. Backend APIs must be designed around capability passing rather than broad secret ownership. Some backend operations require mediated access through the shell.  
**Rejected alternatives:**  
- **Store secrets in backend config files or env vars:** Rejected for weaker local security and poorer macOS integration.  
- **Let Python own auth/session state:** Rejected because it blurs the trust boundary and complicates biometric/keychain enforcement.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two-process architecture requires a local communication mechanism that is simple, inspectable, reliable, and easy to validate across Swift and Python.  
**Decision:** The shell and backend communicate over an authenticated Unix domain socket using line-delimited JSON messages. Message schemas are explicit and bounded to defined interfaces.  
**Consequences:** IPC is human-decodable and implementation-friendly across languages. Message framing is simple. The platform must handle schema evolution, malformed input, backpressure, and reconnection behavior carefully.  
**Rejected alternatives:**  
- **gRPC/Protocol Buffers:** Rejected due to added complexity and packaging overhead relative to the needs of a local-only boundary.  
- **XPC for all communication:** Rejected because the backend is Python, and native XPC interop would be more complex than a local socket protocol.  
- **STDIN/STDOUT subprocess protocol:** Rejected because long-lived orchestration and authenticated reconnect semantics are cleaner with a socket.

## Never execute generated code
**Status:** Accepted  
**Context:** Forge generates code and tests from model output and manipulates repositories, but the security model explicitly disallows executing generated code due to supply-chain and prompt-injection risk.  
**Decision:** Neither the Swift shell nor the Python backend may directly execute generated code as part of agent operation. Validation is performed through controlled repository workflows and CI defined by the target project, not by arbitrary local execution of generated artifacts.  
**Consequences:** Local autonomy is intentionally constrained. The system must rely on static validation where available and on repository CI for dynamic verification. Feature design must avoid “just run it locally” shortcuts.  
**Rejected alternatives:**  
- **Execute generated code in a sandbox:** Rejected because sandbox escape and trust-model complexity remain inconsistent with the platform’s security posture.  
- **Run only generated tests locally:** Rejected because tests themselves are generated content and therefore untrusted.

## TRDs are the source of truth
**Status:** Accepted  
**Context:** The platform spans shell, backend, planning, UI, GitHub automation, and security. To prevent undocumented behavior and drift, engineering needs a single authoritative specification set.  
**Decision:** The 12 TRDs in `forge-docs/` are the authoritative product specification. Implementation, interfaces, state machines, errors, tests, and security controls must conform to them. ADRs in this file record cross-cutting design decisions but do not supersede TRDs.  
**Consequences:** Engineering changes require TRD alignment. Code review and agent behavior must reference the owning TRD. “Convenient” undocumented behavior is treated as non-authoritative.  
**Rejected alternatives:**  
- **Code is the spec:** Rejected because it encourages drift and makes validation across subsystems difficult.  
- **This decisions file as the primary spec:** Rejected because this file is intentionally concise and not a replacement for detailed technical requirements.

## macOS-native distribution and lifecycle management
**Status:** Accepted  
**Context:** The product is explicitly a native macOS application with installation, updates, secure local state, and OS-integrated UX requirements.  
**Decision:** Forge is packaged and delivered as a native macOS `.app`, supports drag-to-Applications installation, and uses native lifecycle management with Sparkle-based auto-update as specified by the shell TRD.  
**Consequences:** Release engineering must support signed macOS application distribution and update feeds. Platform scope is intentionally narrowed to macOS rather than cross-platform parity.  
**Rejected alternatives:**  
- **Electron or cross-platform desktop shell:** Rejected because native macOS integration, security posture, and product scope favor Swift/SwiftUI.  
- **CLI-only distribution:** Rejected because the product requires a guided native experience and secure UI-mediated controls.

## Native SwiftUI interface rather than chat-centric UX
**Status:** Accepted  
**Context:** The product is a directed build agent, not a conversational assistant. Users provide repository context, specifications, and intent, then review staged outputs and pull requests.  
**Decision:** The UX is built as a native SwiftUI application focused on workflow state, plans, PR units, review surfaces, approvals, and progress visualization rather than a generic chat interface.  
**Consequences:** Interaction design centers on structured tasks and artifacts, not open-ended conversation. UI components must represent pipeline state and gated approvals clearly.  
**Rejected alternatives:**  
- **Chat-first interface:** Rejected because it mismatches the product’s operating model and encourages ambiguous commands and hidden state.  
- **Web UI wrapped in native shell:** Rejected because native performance, integration, and trust cues are core product goals.

## Python backend as orchestration and intelligence layer
**Status:** Accepted  
**Context:** The backend must integrate multiple model providers, perform planning and consensus, manage repository changes, and evolve rapidly with provider APIs and automation tooling.  
**Decision:** The backend is implemented in Python 3.12 and owns orchestration, planning, generation, consensus, review, documentation regeneration, and GitHub interactions.  
**Consequences:** Backend development benefits from Python’s ecosystem and velocity. Strong contracts are required at the Swift/Python boundary. Runtime packaging and embedded interpreter management must be handled by the shell.  
**Rejected alternatives:**  
- **Swift backend logic:** Rejected due to slower iteration for model/provider tooling and repository automation.  
- **Remote hosted backend:** Rejected because the platform is designed around local control and local trust boundaries.

## Two-model consensus with arbitration
**Status:** Accepted  
**Context:** The product’s core differentiation is higher-confidence code generation through multi-model agreement rather than single-model output. The README and TRDs describe parallel generation with arbitration.  
**Decision:** Forge uses a two-model consensus approach, with multiple providers generating in parallel and Claude arbitrating final results where specified. Consensus is a first-class backend primitive, not an optional plugin.  
**Consequences:** Provider adapters, prompt contracts, and arbitration logic must be explicit. Performance and cost budgeting must account for parallel inference. Failures must degrade predictably when one provider is unavailable.  
**Rejected alternatives:**  
- **Single-model generation:** Rejected because it reduces confidence and weakens the core product thesis.  
- **N-model open-ended voting:** Rejected because it adds cost/latency and complicates arbitration without being part of the defined product design.

## Planning is hierarchical: intent to PRD to ordered PR sequence
**Status:** Accepted  
**Context:** The product accepts high-level user intent and technical specs, then autonomously delivers implementation through manageable review units. This requires decomposition across multiple levels.  
**Decision:** Forge decomposes user intent into an implementation plan, decomposes that plan into PRDs/tasks as required by the backend pipeline, and then into an ordered sequence of pull requests representing logical reviewable units.  
**Consequences:** Planning data structures and UI must preserve lineage from intent to implementation unit. Progress tracking, retries, and approvals operate at PR granularity while remaining traceable to the higher-level plan.  
**Rejected alternatives:**  
- **Generate one giant PR:** Rejected because it harms reviewability, increases failure blast radius, and breaks the staged workflow.  
- **Only task-level planning with no intermediate structure:** Rejected because it weakens traceability and sequencing.

## Pull request is the unit of delivery
**Status:** Accepted  
**Context:** The system is intended to integrate with GitHub-centered engineering workflows where review, CI, and merge controls occur at the PR boundary.  
**Decision:** The primary delivery artifact is a GitHub pull request. Forge creates one draft PR per logical unit of work, waits for user approval/merge gating, and advances to the next planned unit accordingly.  
**Consequences:** State machines, UI, and automation are organized around PR lifecycle. Local changes must remain attributable to a single PR unit. The product optimizes for reviewability over maximum local throughput.  
**Rejected alternatives:**  
- **Direct pushes to main:** Rejected due to safety and review concerns.  
- **Patch-file export as primary artifact:** Rejected because it does not align with the intended GitHub workflow.

## Human-gated progression between PR units
**Status:** Accepted  
**Context:** The agent is autonomous in generation but not sovereign in deployment. The product promise is “you gate, review, and merge; the agent builds the next PR while you read the last one.”  
**Decision:** Forge requires human review and gating at defined approval points, especially around pull request progression and merge-related advancement. The system may prepare subsequent work, but workflow advancement respects explicit user controls.  
**Consequences:** The platform remains assistive rather than fully autonomous. UI must make pending approvals and blocked states obvious. Throughput is bounded by human review checkpoints by design.  
**Rejected alternatives:**  
- **Fully autonomous merge and deploy loop:** Rejected as inconsistent with product trust and risk posture.  
- **Manual-only step execution with no autonomous preparation:** Rejected because it undermines the product’s core value.

## Three-pass review cycle before PR creation
**Status:** Accepted  
**Context:** Generated implementation quality must be improved before surfacing a PR to the user. The product specification references a structured multi-pass review cycle.  
**Decision:** Forge performs a three-pass review cycle on generated changes before opening a draft pull request. Review is part of the standard pipeline, not a best-effort add-on.  
**Consequences:** Pipeline duration includes review iterations, and internal review artifacts must be tracked. Provider prompts and review criteria must be stable and testable.  
**Rejected alternatives:**  
- **Single-pass generation only:** Rejected because quality and consistency are lower.  
- **Unlimited review loops until convergence:** Rejected because it risks unbounded latency and cost.

## CI is the execution boundary for dynamic validation
**Status:** Accepted  
**Context:** Because generated code is never executed locally by the agent, the system still needs a place for dynamic verification within the target repository’s normal controls.  
**Decision:** Continuous integration associated with the target repository is the primary execution boundary for dynamic validation of generated changes. Forge triggers and monitors CI as part of the PR workflow rather than executing generated artifacts locally.  
**Consequences:** Repository integration and CI status handling are critical. The platform must tolerate diverse CI systems through GitHub-centric abstractions. Validation latency depends on remote CI.  
**Rejected alternatives:**  
- **Local agent-run test execution:** Rejected by the no-execution rule.  
- **No automated validation before PR:** Rejected because it would materially reduce confidence.

## GitHub-centered repository automation
**Status:** Accepted  
**Context:** The product promise explicitly includes opening pull requests and managing staged delivery in a GitHub workflow.  
**Decision:** Forge treats GitHub as the primary repository hosting and workflow integration target for planning execution, branch management, draft PR creation, review metadata, and CI observation.  
**Consequences:** GitHub concepts shape the data model and pipeline. Additional SCM providers, if ever added, must be adapters rather than changes to the core workflow semantics.  
**Rejected alternatives:**  
- **Provider-agnostic SCM core from day one:** Rejected because it would over-generalize the initial product and slow delivery.  
- **Local Git only with no hosted workflow integration:** Rejected because PR-based review is central to the product.

## Documentation regeneration is an explicit optional stage
**Status:** Accepted  
**Context:** The product may regenerate documentation after implementation completes, but documentation changes should not be forced in every workflow.  
**Decision:** Documentation regeneration is supported as an explicit optional pipeline stage after implementation progress, rather than an unconditional behavior on every change.  
**Consequences:** Users and plans can choose whether docs updates are included. The pipeline must model docs generation independently from code generation.  
**Rejected alternatives:**  
- **Always regenerate docs:** Rejected because it adds noise, latency, and unnecessary churn.  
- **Never generate docs:** Rejected because keeping specs/docs aligned is a valuable product capability.

## Security controls are centralized and cross-cutting
**Status:** Accepted  
**Context:** The platform spans untrusted model output, external repository content, credentials, local IPC, and remote automation. The security model must apply uniformly across subsystems.  
**Decision:** Security requirements defined in the security TRD govern all components. Changes involving credentials, generated code, external content, CI, or repository automation must be evaluated against centralized security controls rather than subsystem-local conventions.  
**Consequences:** Security review is required across feature boundaries. Subsystems cannot independently relax controls. Some implementation choices are intentionally constrained to preserve consistent risk posture.  
**Rejected alternatives:**  
- **Per-team or per-module security practices:** Rejected because cross-boundary gaps are too likely in this architecture.  
- **Best-effort security guidance only:** Rejected because the product’s threat model requires enforceable controls.

## Treat model output and repository content as untrusted input
**Status:** Accepted  
**Context:** The backend consumes external repository state, remote provider responses, specs, issue text, and generated artifacts. These are all potential injection and integrity risks.  
**Decision:** Model output, repository content, PR text, docs, and other external inputs are treated as untrusted data. They must be parsed, validated, bounded, and never implicitly granted execution or authority.  
**Consequences:** Prompt construction, diff application, UI rendering, and IPC handling require defensive design. Convenience features that assume “friendly input” are disallowed.  
**Rejected alternatives:**  
- **Trust internal model output after generation:** Rejected because the source remains probabilistic and potentially adversarially influenced.  
- **Trust repository-local scripts/config by default:** Rejected because repositories are part of the threat surface.

## Structured error contracts across subsystem boundaries
**Status:** Accepted  
**Context:** Forge coordinates multiple processes, providers, network calls, repository operations, and user actions. Failure handling must be predictable across UI and backend.  
**Decision:** Errors crossing subsystem boundaries are represented as structured contracts with stable categories and machine-readable payloads rather than ad hoc strings. The shell presents user-facing recovery states based on these contracts.  
**Consequences:** Interface definitions must include error semantics. Logging, telemetry, retries, and UI states become more consistent. Implementers must maintain backward compatibility when evolving error schemas.  
**Rejected alternatives:**  
- **Stringly typed exceptions over IPC:** Rejected because they are brittle and hard to reason about.  
- **Expose raw provider/library errors directly to users:** Rejected because they are unstable and often unsafe or confusing.

## Explicit state machines for long-running workflows
**Status:** Accepted  
**Context:** Planning and PR generation are multi-step, asynchronous, and failure-prone. The UI needs deterministic status presentation and resumability.  
**Decision:** Major Forge workflows are modeled as explicit state machines with defined transitions, terminal states, and recovery paths rather than implicit “current status” flags.  
**Consequences:** The implementation must maintain durable workflow state and transition logic. UI components can reliably render progress and blocked/error conditions. Some development overhead is added to preserve correctness.  
**Rejected alternatives:**  
- **Boolean/status-string driven workflow logic:** Rejected because it becomes inconsistent and fragile at scale.  
- **Fire-and-forget task orchestration:** Rejected because the product requires visibility and user gating.

## Backend provider integrations use adapter interfaces
**Status:** Accepted  
**Context:** Consensus generation and review depend on multiple model providers with different APIs, rate limits, and response shapes.  
**Decision:** Provider-specific behavior is isolated behind adapter interfaces in the backend. Consensus and pipeline logic depend on provider abstractions, not vendor SDK details.  
**Consequences:** Adding or replacing providers is localized. Testability improves through mock adapters. The adapter surface must be rich enough to express provider capabilities without leaking vendor-specific complexity upward.  
**Rejected alternatives:**  
- **Hardcode provider logic into consensus engine:** Rejected because it couples core logic to vendors and impedes testing.  
- **Use only one provider SDK everywhere:** Rejected because the product requires multi-provider consensus.

## Shell-mediated backend lifecycle management
**Status:** Accepted  
**Context:** The backend is a subordinate local service whose trust and availability are controlled by the app shell. The product needs deterministic startup, shutdown, upgrade, and recovery behavior.  
**Decision:** The Swift shell launches, authenticates, monitors, and terminates the Python backend as part of app lifecycle management. The backend is not treated as an independently user-managed daemon.  
**Consequences:** Lifecycle responsibility is centralized in the shell. Upgrade and restart flows can be coordinated. Backend resilience must support supervised restarts and reconnection.  
**Rejected alternatives:**  
- **Standalone backend daemon:** Rejected because it complicates trust, supportability, and UX.  
- **Backend spawned per request:** Rejected because long-running orchestration and stateful workflows need a managed service lifecycle.

## Local-first trust model, remote services by necessity
**Status:** Accepted  
**Context:** Forge depends on remote LLM providers and GitHub, but the user-facing application and trust anchor are local.  
**Decision:** The product follows a local-first trust model: the app shell is the local control plane; remote services are used for model inference, repository hosting, and CI because required by function, not as the primary control surface.  
**Consequences:** User control, auth gating, and sensitive local interactions remain on-device. Network dependency remains unavoidable for core features, so degraded/offline behavior must fail clearly rather than pretending to be local-complete.  
**Rejected alternatives:**  
- **Fully cloud-hosted agent with thin client:** Rejected because it weakens local trust and contradicts the product architecture.  
- **Completely offline product:** Rejected because model providers and GitHub workflows are integral.

## Tests must align to subsystem contracts and security requirements
**Status:** Accepted  
**Context:** The TRDs define interfaces, error contracts, and security controls that must be preserved over time. Testing must reinforce those boundaries, not only implementation details.  
**Decision:** Testing strategy prioritizes subsystem contract validation, state machine behavior, security invariants, and provider/backend adapter behavior in addition to ordinary unit testing. Changes touching protected areas must validate the relevant TRD-defined behaviors.  
**Consequences:** Test suites must be organized around contract fidelity and regression prevention. Mocking and fixture design need to reflect real interface semantics.  
**Rejected alternatives:**  
- **Primarily snapshot/manual testing:** Rejected because it is insufficient for cross-process and security-sensitive behavior.  
- **Only low-level unit tests:** Rejected because many risks occur at subsystem boundaries.