# DECISIONS.md

## Two-process platform architecture
**Status:** Accepted  
**Context:** Forge is specified as a native macOS AI coding agent with strict separation between user-facing trust boundaries and model-driven code generation. The shell must own UI, authentication, Keychain, app lifecycle, and local OS integrations. The backend must own planning, consensus, generation, review, and GitHub automation.  
**Decision:** The platform is implemented as two cooperating processes: a native Swift/SwiftUI macOS shell and a Python backend. The Swift shell owns presentation, secrets, authentication, process control, and local system integration. The Python backend owns intelligence, orchestration, generation, validation, and repository automation.  
**Consequences:** This creates a clear trust boundary, allows native macOS UX and security primitives, and isolates model-driven behavior from credentials and UI state. It also adds IPC complexity, process lifecycle management, and cross-language contract maintenance.  
**Rejected alternatives:** A single-process app was rejected because it weakens isolation between secrets/UI and generated content. A fully web-based client was rejected because it does not satisfy native macOS security and UX requirements. A full Swift implementation was rejected because the backend requires a faster-evolving AI/tooling ecosystem.

## Swift shell owns all secrets and authentication
**Status:** Accepted  
**Context:** Credentials, tokens, biometric gates, and user trust are security-critical. The product requires strong local protection and minimal exposure of secrets to model-handling components.  
**Decision:** All long-lived credentials and sensitive secrets are stored and managed by the Swift shell using macOS security primitives, including Keychain and biometric/session gates. The Python backend never becomes the source of truth for stored secrets.  
**Consequences:** Secret handling remains aligned with platform-native controls and reduces backend compromise impact. Backend features requiring credentials depend on shell-mediated delivery and session state.  
**Rejected alternatives:** Storing credentials directly in Python configuration or environment variables was rejected due to weaker local security controls. Cloud-only secret storage was rejected because the app must support local-first secure operation.

## Python backend owns intelligence and automation
**Status:** Accepted  
**Context:** Consensus orchestration, provider integration, planning, code generation, GitHub operations, and review pipelines change rapidly and depend on Python-native ecosystems.  
**Decision:** The Python backend is the execution environment for consensus logic, provider adapters, planning pipelines, review passes, CI coordination, and GitHub interactions.  
**Consequences:** AI and orchestration logic can evolve independently of the macOS shell and use mature Python libraries. This requires careful IPC design and schema versioning between shell and backend.  
**Rejected alternatives:** Implementing orchestration in Swift was rejected because it would slow iteration and reduce access to model and automation tooling. Splitting orchestration across both processes was rejected because it would blur ownership and complicate debugging.

## TRDs are the source of truth
**Status:** Accepted  
**Context:** The repository is governed by 12 TRDs that define architecture, interfaces, security controls, state machines, and testing expectations. Platform coherence depends on a single authoritative specification set.  
**Decision:** All subsystems must conform to the TRDs in `forge-docs/`, and implementation decisions must be traced back to those specifications. When ambiguity exists, the owning TRD governs.  
**Consequences:** Requirements remain centralized and auditable. Implementation flexibility is reduced where TRDs are explicit, and changes require spec updates rather than ad hoc divergence.  
**Rejected alternatives:** Allowing code to become the de facto spec was rejected because it causes drift. Informal README-level guidance was rejected because it is insufficiently precise for security and interface contracts.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend require a local communication channel that is explicit, inspectable, and language-neutral. The protocol must support request/response and event flows while preserving local authentication guarantees.  
**Decision:** The shell and backend communicate over an authenticated local Unix socket using line-delimited JSON messages. Message schemas define commands, responses, errors, and events.  
**Consequences:** IPC remains simple to debug, portable across the chosen languages, and suitable for streaming structured events. The platform must maintain strict framing, authentication, and schema compatibility rules.  
**Rejected alternatives:** XPC-only communication was rejected because the backend is Python-based. Binary custom protocols were rejected because they reduce inspectability and increase integration complexity. HTTP localhost APIs were rejected because they expand the local attack surface unnecessarily.

## No execution of generated code by either process
**Status:** Accepted  
**Context:** The platform generates and modifies source code from model output. Executing generated artifacts would create a severe supply-chain and local compromise risk.  
**Decision:** Neither the Swift shell nor the Python backend executes generated code. Validation is performed through static checks, repository operations, and external CI workflows rather than local execution of generated artifacts.  
**Consequences:** The local runtime attack surface is significantly reduced. Some classes of validation must be deferred to sandboxed or external CI systems, which can slow feedback on runtime defects.  
**Rejected alternatives:** Local execution of generated tests or app code was rejected due to security risk. Selective execution behind prompts was rejected because it weakens a core invariant and is prone to policy erosion.

## Human-gated autonomous delivery via pull requests
**Status:** Accepted  
**Context:** Forge is intended to build software autonomously from specifications while preserving human approval at meaningful boundaries. Users review work at the PR level rather than interact through a chat loop.  
**Decision:** The platform delivers changes as one pull request per logical unit of work. PRs are opened as draft or reviewable units, and user approval gates progression to subsequent PRs.  
**Consequences:** Work is segmented into auditable, reviewable changesets and aligns with existing team workflows. Throughput depends on review latency, and decomposition quality directly affects usability.  
**Rejected alternatives:** Direct pushes to the default branch were rejected because they remove human approval and review boundaries. A chat-centric patch application workflow was rejected because the product is not designed as an interactive chat assistant.

## Intent-to-PRD-to-PR decomposition pipeline
**Status:** Accepted  
**Context:** User intent is broad and underspecified relative to implementation work. The platform needs deterministic staging from goal to executable units.  
**Decision:** Forge transforms user intent into an ordered PRD-style plan, then decomposes that plan into a sequence of pull requests representing logical implementation units.  
**Consequences:** Planning becomes explicit and reviewable, enabling progress tracking and incremental delivery. The system must maintain decomposition quality and avoid overlarge or tightly coupled PRs.  
**Rejected alternatives:** Generating one monolithic implementation for the entire intent was rejected because it reduces reviewability and increases failure blast radius. Purely reactive file-by-file editing was rejected because it lacks architectural sequencing.

## Two-model consensus generation with provider parallelism
**Status:** Accepted  
**Context:** The product promise includes higher reliability than single-model generation. Independent model outputs can expose inconsistencies and improve implementation quality when reconciled.  
**Decision:** Each implementation unit is generated using two model providers in parallel, with outputs compared and reconciled through a consensus workflow.  
**Consequences:** Generation quality and defect detection improve relative to single-model output, but latency, cost, and orchestration complexity increase. Provider adapters and normalization layers become critical infrastructure.  
**Rejected alternatives:** Single-model generation was rejected because it does not meet the reliability target. N-model majority voting beyond two providers was rejected because it raises cost and latency without proportional product value.

## Claude arbitrates final consensus outcomes
**Status:** Accepted  
**Context:** The platform specification states that consensus results are arbitrated by Claude. A deterministic tie-breaking and synthesis authority is required to avoid oscillation between providers.  
**Decision:** Claude serves as the final arbiter in the consensus workflow, synthesizing or selecting the final result after parallel generation and comparison.  
**Consequences:** The system has a clear resolution path for disagreements and avoids deadlock in consensus. This creates dependency on one provider for final arbitration behavior and associated availability/performance characteristics.  
**Rejected alternatives:** User arbitration on every disagreement was rejected because it would collapse autonomy. Symmetric reconciliation with no final arbiter was rejected because it risks nontermination or unstable output selection.

## Three-pass review cycle before PR creation
**Status:** Accepted  
**Context:** Generated changes require structured self-critique before being proposed to users. A single pass is insufficient for correctness, completeness, and standards alignment.  
**Decision:** Each PR candidate passes through a three-pass review cycle before finalization and PR creation. Review covers implementation quality, test completeness, and conformance to specifications and constraints.  
**Consequences:** Output quality improves before human review, reducing avoidable defects. Pipeline duration increases, and the review framework must be consistently structured across repositories.  
**Rejected alternatives:** No automated review was rejected because it provides poor quality control. Unlimited iterative review was rejected because it risks runaway cost and latency.

## CI validates changes; local unsafe validation is prohibited
**Status:** Accepted  
**Context:** The platform must validate generated work without violating the no-execution security model locally. Repository-native CI offers a safer place for runtime checks.  
**Decision:** Validation requiring execution occurs in CI or equivalent external controlled environments, not by locally executing generated code in the app or backend process.  
**Consequences:** Validation is safer and aligns with standard repository workflows. CI reliability and configuration quality become prerequisites for strong assurance.  
**Rejected alternatives:** Running tests locally from the backend was rejected because it violates the non-execution boundary. Blindly opening PRs with no validation was rejected because it weakens output quality.

## Draft PRs are the primary delivery artifact
**Status:** Accepted  
**Context:** Users need a stable review surface with diffs, comments, CI status, and merge controls. The product is oriented around repository-native collaboration, not proprietary review UI.  
**Decision:** Forge delivers work primarily by opening GitHub pull requests, typically as drafts until validation and user review are complete.  
**Consequences:** The platform leverages existing developer workflows and auditability. GitHub becomes a core external dependency, and the backend must robustly manage branch and PR lifecycle states.  
**Rejected alternatives:** Delivering patches only as local diffs was rejected because it does not support team workflows. A custom in-app review system was rejected because it duplicates mature repository features.

## Native macOS application shell, not cross-platform first
**Status:** Accepted  
**Context:** The product identity is explicitly a native macOS AI coding agent. It relies on macOS-native UX, Keychain, biometrics, distribution, and app lifecycle behavior.  
**Decision:** The initial shell is a native macOS application built with Swift and SwiftUI, using platform-native capabilities for auth, storage, updates, and UX.  
**Consequences:** The product can provide a higher-trust macOS experience and integrate deeply with the platform. Portability to other desktop platforms is deferred and may require a different shell implementation later.  
**Rejected alternatives:** Electron or other cross-platform shells were rejected because they weaken native security/UX goals. A web app was rejected because it cannot provide the required local integration model.

## SwiftUI-based interface with shell-owned state
**Status:** Accepted  
**Context:** The shell must provide onboarding, settings, navigation, authentication state, and operational visibility in a native macOS form. Clear state ownership is necessary to avoid UI/backend entanglement.  
**Decision:** The shell UI is implemented in SwiftUI, with shell-owned application state and view models responsible for presentation, navigation, and session-aware interactions with the backend.  
**Consequences:** UI development aligns with modern Apple platform patterns and integrates with Swift concurrency. Care is required to prevent duplicated state between shell and backend.  
**Rejected alternatives:** AppKit-first UI was rejected because SwiftUI is the intended modern architecture. Backend-driven UI state was rejected because UI trust and local session state belong to the shell.

## Shell-managed backend lifecycle
**Status:** Accepted  
**Context:** The backend is subordinate to the desktop application and must start, stop, restart, and reconnect in ways that preserve user trust and session semantics.  
**Decision:** The Swift shell launches, monitors, and restarts the Python backend, manages its authenticated connection, and controls credential delivery according to session state.  
**Consequences:** Process supervision remains in the trusted local shell, enabling resilient UX and predictable recovery behavior. The shell must handle crash loops, stale sockets, and restart backoff.  
**Rejected alternatives:** Letting the backend self-daemonize independently was rejected because it weakens shell control and user expectations. Manual user management of the backend process was rejected as operationally unacceptable.

## Session-gated credential delivery to backend
**Status:** Accepted  
**Context:** The backend needs access to provider and GitHub credentials to perform work, but permanent unrestricted access would violate the trust boundary.  
**Decision:** Credentials are delivered to the backend only through shell-mediated, session-aware mechanisms after authentication and policy checks. Credential access is scoped to active operations and governed by shell state.  
**Consequences:** Backend capability is limited by explicit shell-approved sessions, reducing persistence of sensitive access. This adds reauthentication and session-expiry handling complexity.  
**Rejected alternatives:** Persisting usable credentials directly in backend storage was rejected because it bypasses the shell trust boundary. Requiring users to manually paste credentials into backend flows was rejected due to poor UX and higher leakage risk.

## First-launch onboarding and settings are explicit product flows
**Status:** Accepted  
**Context:** Forge depends on repository access, provider configuration, security posture, and user preferences that must be configured safely and predictably.  
**Decision:** The shell provides explicit first-launch onboarding and settings flows for authentication, provider setup, repository-related configuration, and app preferences, backed by a defined local settings schema and migrations.  
**Consequences:** Configuration becomes structured and supportable across app versions. The platform must maintain migration logic and avoid silent behavior changes.  
**Rejected alternatives:** Implicit configuration through scattered prompts was rejected because it creates unreliable state. Flat config-file-only setup was rejected because it is inconsistent with the native product model.

## Sparkle-based auto-update for the macOS shell
**Status:** Accepted  
**Context:** The shell is a distributed macOS application that requires safe, user-friendly updates outside the App Store.  
**Decision:** The application shell uses Sparkle for auto-update distribution and installation.  
**Consequences:** Update delivery follows a proven macOS-native path with signing and user-facing update UX. Release engineering must maintain update feeds, signing, and compatibility discipline.  
**Rejected alternatives:** Manual download-only upgrades were rejected because they degrade maintainability and security posture. App Store distribution was rejected because it conflicts with product distribution and capability assumptions.

## Structured logging and observability across both processes
**Status:** Accepted  
**Context:** Forge spans two processes and multiple external systems. Diagnosing failures requires correlated, structured telemetry rather than ad hoc logs.  
**Decision:** Both shell and backend emit structured logs and operational events suitable for correlation across process boundaries, while respecting security constraints around secrets and generated content.  
**Consequences:** Debugging, support, and reliability improve. Logging schemas, correlation IDs, and redaction rules must be maintained consistently.  
**Rejected alternatives:** Plain unstructured logs were rejected because they are insufficient for distributed troubleshooting. Full payload logging was rejected because it increases risk of sensitive data exposure.

## Security-first design governed by a dedicated security TRD
**Status:** Accepted  
**Context:** The platform handles credentials, generated code, external content, and repository operations. Security requirements cut across every subsystem and must remain consistent.  
**Decision:** Security controls are treated as first-class architectural constraints, with the dedicated security TRD governing credential handling, external content, execution boundaries, CI interactions, and related controls across the platform.  
**Consequences:** Feature implementation must satisfy explicit security review criteria and cannot bypass central constraints for convenience. Some capabilities are intentionally limited to preserve platform trustworthiness.  
**Rejected alternatives:** Subsystem-specific informal security decisions were rejected because they create inconsistent controls. Best-effort security without a governing specification was rejected as inadequate.

## Repository-native documentation regeneration is optional post-build behavior
**Status:** Accepted  
**Context:** The product may update documentation after implementation completes, but documentation changes should not block core code delivery in every case.  
**Decision:** Documentation regeneration is supported as an optional post-build behavior rather than a mandatory step for all work.  
**Consequences:** The platform can improve repository docs when appropriate without forcing unnecessary churn. Documentation freshness may vary unless explicitly requested or required by project policy.  
**Rejected alternatives:** Mandatory documentation regeneration on every PR was rejected because it adds noise and cost. No documentation support was rejected because it misses a useful automation capability.

## Product is a directed build agent, not a chat assistant
**Status:** Accepted  
**Context:** The product definition explicitly distinguishes Forge from chat interfaces, code autocomplete, and copilot-style tools. Architecture and UX must reflect a task-directed workflow.  
**Decision:** The platform is designed around structured intent capture, planning, PR generation, validation, and review handoff, rather than free-form conversational assistance as the primary interaction model.  
**Consequences:** UX and backend flows optimize for autonomous delivery and reviewability instead of conversational breadth. User expectations are narrowed, and some chat-like flexibility is intentionally deprioritized.  
**Rejected alternatives:** A general-purpose chat UX was rejected because it conflicts with the product identity. Inline autocomplete behavior was rejected because it does not align with the autonomous PR-based workflow.

## Logical unit boundaries are a core planning constraint
**Status:** Accepted  
**Context:** The platform promises one pull request per logical unit and continuous progress from one reviewed PR to the next. This requires decomposition to optimize for reviewability and independence.  
**Decision:** Planning and generation must produce PRs sized and scoped as logical units, with ordering chosen to minimize coupling and enable sequential autonomous progress.  
**Consequences:** Decomposition quality becomes central to user trust and throughput. The planner must avoid oversized, cross-cutting PRs and account for dependency sequencing explicitly.  
**Rejected alternatives:** Arbitrary fixed-size chunking was rejected because it ignores semantic boundaries. Large milestone PRs were rejected because they reduce reviewability and increase merge risk.

## External provider integration is adapter-based
**Status:** Accepted  
**Context:** The consensus engine depends on multiple model providers whose APIs, capabilities, and failure modes differ. The system needs stable internal contracts despite provider churn.  
**Decision:** Model and external AI integrations are abstracted behind provider adapters in the backend, with a normalized internal interface used by the consensus engine and review pipeline.  
**Consequences:** Providers can be swapped or upgraded with less impact on core orchestration. Adapter maintenance becomes a necessary cost, especially when provider semantics diverge.  
**Rejected alternatives:** Binding core orchestration directly to vendor SDKs was rejected because it creates lock-in and fragile code paths. A least-common-denominator abstraction with no provider-specific tuning was rejected because it sacrifices quality unnecessarily.

## Backend error contracts are explicit and cross-process safe
**Status:** Accepted  
**Context:** Two-process systems fail in more ways than single-process systems, and user-facing trust depends on predictable error handling across IPC, providers, GitHub, and process lifecycle events.  
**Decision:** Backend and shell interactions use explicit error contracts that can be serialized safely across the IPC boundary and surfaced clearly in the shell.  
**Consequences:** Failures become easier to classify, retry, and present to users. Teams must maintain versioned error schemas and avoid leaking internal-only exceptions across the boundary.  
**Rejected alternatives:** Passing raw exceptions or free-form error strings was rejected because it creates instability and poor UX. Silent retries without surfaced error states were rejected because they reduce trust and diagnosability.