# DECISIONS.md

## Native macOS shell with bundled Python backend
**Status:** Accepted  
**Context:** Forge is specified as a native macOS AI coding agent with strict separation between platform-native responsibilities and intelligence/runtime responsibilities. The product requirements call for native installation, macOS auth and secret handling, and a Python-based implementation pipeline.  
**Decision:** Forge is implemented as a two-process architecture: a native Swift/SwiftUI macOS shell and a bundled Python 3.12 backend. The Swift shell owns UI, app lifecycle, installation/update integration, authentication, Keychain access, and local orchestration. The Python backend owns planning, consensus, code generation, validation pipeline orchestration, and GitHub operations.  
**Consequences:** Clear ownership boundaries are enforced across the codebase. Platform-native capabilities remain in Swift, while AI workflow logic remains in Python. Cross-language integration becomes a first-class concern and requires a stable IPC contract. Packaging must include a bundled Python runtime.  
**Rejected alternatives:**  
- **Single-process Swift-only application:** Rejected because the intelligence stack, ecosystem libraries, and backend orchestration are specified in Python.  
- **Single-process Python desktop app:** Rejected because native macOS UX, security integration, and system APIs are core requirements.  
- **Remote-only backend service:** Rejected because the product is designed as a local native agent with local orchestration and secret isolation.

## Authenticated local IPC over Unix domain socket with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend must communicate reliably across processes while preserving local security, simplicity, and debuggability. The interface must support structured requests, responses, progress events, and failure contracts.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket with line-delimited JSON messages. The shell establishes and owns the connection lifecycle; both sides validate message schema and authentication state.  
**Consequences:** The platform gains a simple, inspectable transport with explicit framing and strong local-only semantics. The protocol must remain versioned and backward compatible during upgrades. Message schemas, correlation IDs, and error contracts become part of the platform surface area.  
**Rejected alternatives:**  
- **XPC for all cross-process communication:** Rejected because the backend is Python, and the product specification centers on a language-agnostic JSON protocol.  
- **HTTP on localhost:** Rejected because it expands network exposure unnecessarily and introduces avoidable complexity.  
- **StdIO pipes:** Rejected because lifecycle management and service-style reconnection are weaker than a socket-based model.

## Swift shell owns authentication, biometrics, session lifecycle, and secrets
**Status:** Accepted  
**Context:** Forge requires strong local security controls, macOS-native auth flows, and strict handling of credentials. The platform must prevent the backend from directly handling platform secrets.  
**Decision:** All user authentication, biometric gating, session establishment, and secret storage are owned by the Swift shell. Secrets are stored in the macOS Keychain and only capability-scoped material needed for backend operations is passed across the process boundary.  
**Consequences:** Sensitive operations remain under macOS-native control. The Python backend is intentionally constrained and cannot become the source of truth for user identity or credential storage. IPC interfaces must be designed around least-privilege token handoff rather than raw secret ownership.  
**Rejected alternatives:**  
- **Backend-managed credentials:** Rejected because it violates the platform trust boundary and weakens OS-integrated protections.  
- **Flat-file secret storage:** Rejected because Keychain is the required secure store.  
- **No biometric/session gate:** Rejected because local access control is part of the product security model.

## Python backend owns planning, consensus, generation, validation, and GitHub operations
**Status:** Accepted  
**Context:** The product’s core value is autonomous software delivery from specifications, including scope assessment, decomposition, generation, correction, and GitHub PR creation. These workflows are defined as backend intelligence responsibilities.  
**Decision:** The backend is the sole owner of intent analysis, confidence assessment, PRD and PR decomposition, model-provider orchestration, consensus and arbitration, self-correction, lint/fix loops, CI-facing logic, and GitHub branch/PR operations.  
**Consequences:** Business logic for autonomous delivery is centralized in Python, improving testability and reducing duplication. The shell acts as orchestrator and presenter rather than an intelligence layer. Any feature that changes planning or generation behavior must land in the backend and conform to backend contracts.  
**Rejected alternatives:**  
- **Split workflow logic across shell and backend:** Rejected because it creates duplicated state machines and brittle ownership boundaries.  
- **Put Git operations in the shell:** Rejected because GitHub automation is part of the generation pipeline, not UI orchestration.

## TRDs are the source of truth for all subsystem behavior
**Status:** Accepted  
**Context:** Forge is fully specified by a set of technical requirements documents covering interfaces, state machines, security controls, and performance requirements. A single authority is required to prevent implementation drift.  
**Decision:** The TRDs in `forge-docs/` are the normative design authority for the platform. Code, tests, interfaces, and operator behavior must conform to the owning TRD for each subsystem.  
**Consequences:** Design decisions are not inferred ad hoc from implementation. Contributors must trace changes back to the relevant TRD. Cross-cutting decisions, especially around security and interfaces, require explicit reconciliation with the relevant specifications.  
**Rejected alternatives:**  
- **Code-as-documentation only:** Rejected because the platform has multiple subsystems and formal cross-process contracts that need specification-level governance.  
- **Wiki-driven design:** Rejected because it is too informal for a system with strict security and orchestration requirements.

## Security controls are centralized under the platform security model
**Status:** Accepted  
**Context:** The platform handles credentials, external model outputs, generated code, repository access, and CI interactions. Security requirements must be consistent across shell, backend, and pipeline.  
**Decision:** Security-sensitive implementation decisions are governed by the platform security model and applied uniformly across all subsystems. Generated code is treated as untrusted until validated; external content is constrained by explicit policy; secrets never cross boundaries unnecessarily; and no component may execute generated code directly.  
**Consequences:** Convenience shortcuts that bypass validation or trust boundaries are prohibited. Pipeline stages, UI actions, and integration behavior must all preserve the same security assumptions. Security review is required for changes touching credentials, execution, external content, or CI interactions.  
**Rejected alternatives:**  
- **Subsystem-specific security policies:** Rejected because inconsistent rules create exploitable gaps.  
- **Trust generated code by default:** Rejected because the product explicitly treats model output as untrusted.

## Generated code is never executed directly by the agent
**Status:** Accepted  
**Context:** Forge produces code autonomously but must maintain a safe operating posture. Direct execution of generated output creates avoidable security and stability risks.  
**Decision:** Neither the Swift shell nor the Python backend may directly execute generated code as part of normal operation. Validation is performed through controlled repository tooling, linting, tests, and CI gates rather than arbitrary execution of model-produced artifacts.  
**Consequences:** The platform must rely on bounded validation workflows. Features that would require free-form execution of generated code are out of scope unless explicitly specified under controlled mechanisms. This reduces risk but may limit certain dynamic evaluation strategies.  
**Rejected alternatives:**  
- **Run generated code locally for faster verification:** Rejected due to security and containment concerns.  
- **Allow optional execution in developer mode:** Rejected because it weakens the safety model and complicates guarantees.

## Repository-driven autonomous workflow centered on typed pull requests
**Status:** Accepted  
**Context:** Forge is not a chat assistant; it is a directed build agent that transforms specifications and intent into reviewable code changes. The workflow must create auditable, incrementally reviewable outputs.  
**Decision:** The core unit of delivery is the typed pull request. The backend decomposes intent into an ordered plan, then into a sequence of logically scoped PRs, each with explicit type and bounded purpose. Forge opens draft PRs for review rather than applying changes silently to mainline branches.  
**Consequences:** Planning and execution logic must preserve reviewability and logical isolation. The platform is optimized for incremental delivery over monolithic changesets. UI and backend state models must expose PR sequence, status, and dependencies clearly.  
**Rejected alternatives:**  
- **Single large branch per intent:** Rejected because it reduces reviewability and increases integration risk.  
- **Direct commits to main:** Rejected because the platform is designed around human-gated review and merge.  
- **Chat-response-only output:** Rejected because the product’s value is repository change delivery, not conversational assistance.

## Two-model generation with consensus and Claude arbitration
**Status:** Accepted  
**Context:** The product requirement is to improve reliability and confidence of autonomous changes by using parallel model generation and structured adjudication. A deterministic governance model is needed for disagreement handling.  
**Decision:** Forge uses two model providers in parallel for generation and analysis, with consensus logic comparing outputs and Claude acting as the arbiter on final results where arbitration is required.  
**Consequences:** Provider abstraction, comparison logic, and arbitration prompts become core backend infrastructure. The system must tolerate provider latency, divergence, and partial failure. Results are expected to be higher confidence, but cost and orchestration complexity increase.  
**Rejected alternatives:**  
- **Single-model generation:** Rejected because it offers less robustness and lower confidence for autonomous code changes.  
- **Majority vote across many models:** Rejected because it increases cost and operational complexity beyond the specified architecture.  
- **Human arbitration for every disagreement:** Rejected because it breaks autonomous throughput goals.

## Provider integrations are abstracted behind stable adapter interfaces
**Status:** Accepted  
**Context:** Forge depends on multiple model providers and must preserve backend portability, testability, and future substitution without rewriting pipeline logic.  
**Decision:** All LLM providers are integrated through adapter interfaces that normalize prompt submission, response handling, error mapping, retry behavior, and metadata capture. Consensus and generation layers depend on the abstraction, not provider-specific APIs.  
**Consequences:** Adding or replacing providers becomes a bounded integration task. The abstraction layer must be expressive enough for common capabilities while preventing pipeline code from depending on provider quirks. Testing can use adapter mocks rather than live provider calls.  
**Rejected alternatives:**  
- **Inline provider-specific calls throughout the backend:** Rejected because it couples orchestration logic to vendor APIs.  
- **Overly generic plugin model:** Rejected because the current platform requirements are better served by explicit adapter contracts.

## Intent is gated by confidence assessment before execution
**Status:** Accepted  
**Context:** The agent must not begin repository modification when the requested scope is ambiguous, unsafe, or insufficiently grounded in the supplied specifications. An early qualification step reduces bad autonomous work.  
**Decision:** Forge assesses confidence in the user’s requested intent before committing to planning and implementation. If confidence is too low, the system blocks execution or requests clarification rather than proceeding optimistically.  
**Consequences:** The user experience includes explicit gating before work begins. The backend must maintain a confidence model and reasons for deferral. Throughput may decrease for ambiguous requests, but correctness and trust improve.  
**Rejected alternatives:**  
- **Always proceed and self-correct later:** Rejected because early misunderstandings produce cascaded bad PRs.  
- **Require manual decomposition for all work:** Rejected because it undermines autonomy.

## Planning hierarchy is Intent → PRD plan → ordered PR sequence
**Status:** Accepted  
**Context:** Complex repository changes require decomposition at more than one level to remain understandable and executable. The product description specifies a staged planning hierarchy.  
**Decision:** Forge first transforms user intent into a PRD-level plan, then decomposes that plan into an ordered sequence of typed pull requests for implementation. Each stage has explicit outputs and feeds the next stage deterministically.  
**Consequences:** Planning becomes inspectable and auditable. The UI and backend state model must preserve artifacts at each level. Changes to decomposition behavior must respect this hierarchy rather than collapsing directly from intent to code.  
**Rejected alternatives:**  
- **Direct code generation from intent:** Rejected because it is too opaque and brittle for complex work.  
- **Only a flat task list:** Rejected because it lacks the product-level structure needed for sustained autonomous delivery.

## Validation pipeline includes self-correction, lint gate, iterative fixes, and CI
**Status:** Accepted  
**Context:** Autonomous code generation requires layered quality gates before opening a reviewable PR. The product description specifies a multi-stage validation pipeline.  
**Decision:** Every implementation flows through a defined backend pipeline: generate, self-correct, apply lint and static quality gates, run iterative fix loops as needed, then execute CI-facing validation before opening a draft pull request.  
**Consequences:** Pipeline stages are explicit and ordered. Failure handling and retry behavior must be designed per stage. The system favors higher-quality PRs at the cost of longer execution time and greater orchestration complexity.  
**Rejected alternatives:**  
- **Open PRs immediately after first-pass generation:** Rejected because quality would be too inconsistent.  
- **Rely on CI alone:** Rejected because earlier local gates reduce noise and wasted cycles.

## Human review and merge remain mandatory
**Status:** Accepted  
**Context:** Forge is autonomous in generation and PR creation, but the product positions the user as the final gate on repository changes. Human trust and governance require explicit approval points.  
**Decision:** Forge opens draft PRs for user review and does not self-merge autonomous changes into protected branches. The human operator remains responsible for approval and merge decisions.  
**Consequences:** The system is designed for supervised autonomy, not full unsupervised deployment. UI workflows prioritize reviewability, explanations, and staged delivery. Some end-to-end automation opportunities are intentionally constrained.  
**Rejected alternatives:**  
- **Automatic merge on green CI:** Rejected because the product promises user-gated review.  
- **Direct branch updates without PRs:** Rejected because they reduce visibility and control.

## Draft pull requests are the default publication mode
**Status:** Accepted  
**Context:** Generated changes may be logically complete but still require human inspection. The platform should communicate that outputs are proposed work pending review.  
**Decision:** Forge publishes generated work as draft pull requests by default. Promotion to ready-for-review or merge is a human decision outside autonomous generation.  
**Consequences:** The GitHub integration must support draft PR creation and status tracking. User expectations are set around review-first workflows. Downstream automations must account for draft-state semantics.  
**Rejected alternatives:**  
- **Open ready-for-review PRs immediately:** Rejected because it overstates confidence and readiness.  
- **Keep changes only local until manually pushed:** Rejected because the platform’s value includes managed GitHub publication.

## Local-first orchestration with remote integrations only where required
**Status:** Accepted  
**Context:** Forge runs as a desktop application and must preserve native responsiveness, local control, and minimal external exposure, while still depending on remote LLM and GitHub services.  
**Decision:** Core orchestration, state management, authentication mediation, and pipeline control run locally on the user’s machine. Remote dependencies are limited to model providers, GitHub, update infrastructure, and other explicitly required external services.  
**Consequences:** The platform remains usable as a local tool with strong operator control. Networked features must degrade gracefully and expose connectivity state. Architecture choices that assume always-on remote orchestration are out of bounds.  
**Rejected alternatives:**  
- **Cloud-orchestrated control plane:** Rejected because it conflicts with the native local-agent model.  
- **Fully offline operation:** Rejected because model and GitHub capabilities inherently require network access.

## Sparkle-based application updates for the macOS shell
**Status:** Accepted  
**Context:** The macOS shell requires native distribution and update behavior appropriate for a desktop application. The shell specification includes in-app update support.  
**Decision:** Forge uses Sparkle for macOS application update delivery for the shell application bundle. Installation remains standard native app distribution, including drag-to-Applications semantics.  
**Consequences:** Release engineering must produce signed update artifacts compatible with Sparkle. Update flows remain native to macOS expectations. Security and trust of update feeds become release concerns.  
**Rejected alternatives:**  
- **Custom updater implementation:** Rejected because it adds unnecessary security and maintenance burden.  
- **App Store-only distribution:** Rejected because the specified distribution/update model is direct app distribution with integrated updating.

## Minimum platform target is macOS 13.0 with SwiftUI-based shell UI
**Status:** Accepted  
**Context:** The shell TRD defines the supported OS baseline and technology stack for the native application. A clear baseline is required for APIs, testing, and UX consistency.  
**Decision:** The shell targets macOS 13.0 or later and is implemented in Swift 5.9+ using SwiftUI for the application UI.  
**Consequences:** Platform APIs may assume Ventura-era capabilities and later. Older macOS versions are out of scope. UI architecture is aligned with SwiftUI patterns rather than AppKit-first designs.  
**Rejected alternatives:**  
- **Support older macOS releases:** Rejected because it increases compatibility burden beyond the specified baseline.  
- **AppKit-first UI:** Rejected because the shell specification calls for SwiftUI-based architecture.

## UI is purpose-built for orchestration, not chat
**Status:** Accepted  
**Context:** The product explicitly differentiates itself from chat interfaces and copilots. The shell UI must reflect directed software delivery workflows rather than conversational interaction patterns.  
**Decision:** The Forge user experience is designed around repository selection, specification loading, intent submission, plan visibility, pipeline status, PR sequencing, and review handoff—not free-form chat as the primary abstraction.  
**Consequences:** UI components, terminology, and state transitions emphasize work execution and artifact tracking. Features that mimic generic chat products are deprioritized unless they directly support the orchestration workflow.  
**Rejected alternatives:**  
- **Chat-first interface with code actions:** Rejected because it conflicts with product identity and workflow goals.  
- **CLI-only primary interface:** Rejected because native macOS shell UX is part of the platform definition.

## Cross-subsystem contracts require explicit error and state models
**Status:** Accepted  
**Context:** Forge spans UI, auth, IPC, planning, generation, validation, and GitHub publication. Robust orchestration requires predictable behavior under success, partial failure, and interruption.  
**Decision:** All major subsystem boundaries use explicit contracts for states, transitions, and error categories rather than implicit exceptions or UI-driven inference. IPC messages, pipeline stages, and user-visible workflow steps must expose structured status and failure information.  
**Consequences:** Additional schema and testing work is required, but orchestration becomes more reliable and debuggable. Recovery logic can be implemented consistently across shell and backend.  
**Rejected alternatives:**  
- **Ad hoc exception propagation:** Rejected because it is too brittle across process and language boundaries.  
- **UI-only interpretation of backend events:** Rejected because contracts must be authoritative at the subsystem boundary.

## Test strategy follows subsystem ownership and contract boundaries
**Status:** Accepted  
**Context:** The platform includes native shell code, backend orchestration, and cross-process integration. A coherent testing approach is required to preserve correctness across multiple languages and subsystems.  
**Decision:** Tests are organized by subsystem ownership and contract surface: Swift-side tests for shell behavior, Python tests for backend logic, and integration tests for IPC, pipeline, and external-service boundary behavior. Changes must validate the owning subsystem and any affected contracts.  
**Consequences:** Teams must maintain both unit and integration coverage. Contract regressions are treated as platform regressions, not isolated implementation bugs. Test infrastructure must support multi-language validation.  
**Rejected alternatives:**  
- **Unit tests only within each language stack:** Rejected because cross-process contracts are central to platform behavior.  
- **Manual end-to-end verification as the primary strategy:** Rejected because it does not scale or provide sufficient confidence.

## GitHub is the canonical collaboration and review surface
**Status:** Accepted  
**Context:** The product’s output is a sequence of pull requests intended for human review and merge in a standard software-development workflow. A canonical external system is required for branches, PRs, CI association, and review state.  
**Decision:** Forge integrates directly with GitHub as the authoritative remote repository and pull request system for publishing autonomous work. Branch creation, draft PR opening, and progression of work are modeled around GitHub semantics.  
**Consequences:** GitHub integration is a platform-critical dependency. Terminology and workflow assumptions align with GitHub concepts. Supporting additional SCM/review systems would require new explicit decisions and abstractions.  
**Rejected alternatives:**  
- **SCM-agnostic first release:** Rejected because it would weaken workflow depth and slow implementation of the specified experience.  
- **Local patch generation only:** Rejected because the product is designed to open PRs, not just emit diffs.