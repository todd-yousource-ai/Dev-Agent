# DECISIONS.md

## Two-process architecture with strict responsibility split
**Status:** Accepted  
**Context:** The platform is specified as a native macOS product with materially different trust and runtime requirements between user-facing OS integration and AI/code-generation workflows. The shell must own native UI, authentication, Keychain access, installation, updates, and local orchestration, while the backend must own planning, consensus, code generation, validation, and GitHub operations. This separation is repeatedly reinforced across the repository guidance and TRDs.  
**Decision:** Forge uses a two-process architecture: a native Swift/SwiftUI macOS shell and a bundled Python backend. The Swift process owns UI, auth, session control, secrets, packaging, and OS integrations. The Python process owns intelligence, planning, consensus, generation, fix loops, and repository/GitHub automation.  
**Consequences:** Clear trust boundaries are enforced. Secrets remain under shell control. Native UX can evolve independently from backend intelligence. Inter-process contracts become critical and versioned. Operational complexity increases due to process lifecycle, IPC, and packaging of two runtimes.  
**Rejected alternatives:**  
- **Single-process app:** Rejected because it weakens isolation between secrets/native privileges and untrusted model-driven workflows.  
- **All-backend Electron/web shell:** Rejected because the platform requires native macOS auth, Keychain, biometrics, and shell-grade UX.  
- **Backend-only CLI:** Rejected because the product is specified as a native application, not a terminal-first tool.

## Native macOS shell as the user-facing product container
**Status:** Accepted  
**Context:** The product is defined as a native macOS application with installation, onboarding, biometrics, Keychain, update flow, and SwiftUI interfaces. The shell is foundational and required by multiple downstream subsystems.  
**Decision:** The Forge platform is packaged and delivered as a native macOS `.app` using Swift 5.9+ and SwiftUI, targeting macOS 13.0+ as the minimum supported version. The shell is the canonical entrypoint for all user interaction and lifecycle orchestration.  
**Consequences:** The platform can rely on native APIs for security and UX. Distribution, notarization, update, and app lifecycle requirements become first-class concerns. The implementation is constrained to Apple platform conventions and release tooling.  
**Rejected alternatives:**  
- **Cross-platform desktop framework:** Rejected because TRDs require native macOS security primitives and UX fidelity.  
- **Browser-based product:** Rejected because local repo access, Keychain, biometrics, and app-bundled runtime requirements are core.  
- **CLI-first shell with optional GUI:** Rejected because the shell is not optional in the specified architecture.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two-process design requires a narrow, explicit, local communication mechanism between Swift and Python. The contract must be inspectable, deterministic, and suitable for streaming state transitions and commands while remaining local-only and authenticated.  
**Decision:** Inter-process communication is implemented via an authenticated Unix domain socket using line-delimited JSON messages. Message schemas are explicit and treated as a stable contract between shell and backend.  
**Consequences:** IPC remains local, efficient, and debuggable. Both processes can evolve independently so long as they preserve the contract. Authentication and framing rules must be enforced consistently. Binary protocol efficiency is traded for operational clarity and ease of inspection.  
**Rejected alternatives:**  
- **HTTP localhost API:** Rejected because it broadens attack surface and introduces unnecessary server semantics.  
- **XPC for all communication:** Rejected because the backend is Python and the cross-language contract is better served by a portable socket protocol.  
- **gRPC/Protobuf:** Rejected because the added complexity was unnecessary for a local, bounded interface.

## Swift owns secrets, identity, and session authority
**Status:** Accepted  
**Context:** Repository guidance states that the Swift process owns authentication and secrets. The macOS shell TRD assigns biometric gate, Keychain secret storage, and session lifecycle to the shell. Security controls depend on preventing the backend from becoming the root of trust.  
**Decision:** All long-lived secrets, authentication material, and session authority are owned by the Swift shell. Secrets are stored in Keychain and exposed to the Python backend only through scoped, explicit, minimal interfaces when required. The backend is never the system of record for credentials.  
**Consequences:** Security-sensitive operations remain anchored in native OS protections. Backend compromise has reduced blast radius. Additional interface design is required for token brokerage and session-scoped access. Some backend operations may be slightly more complex due to mediation through the shell.  
**Rejected alternatives:**  
- **Store secrets in Python config/state:** Rejected due to weaker platform protections and broader exposure.  
- **Share unrestricted credentials with backend:** Rejected because it breaks least privilege.  
- **Use environment variables as primary secret transport:** Rejected because they are easier to leak and harder to govern.

## Python backend owns intelligence, planning, and repository automation
**Status:** Accepted  
**Context:** The product’s core value is autonomous software delivery from specifications through planning, generation, validation, and pull request creation. These behaviors are model-driven, iterative, and better suited to the backend runtime defined in the architecture.  
**Decision:** The Python backend is the sole owner of intent assessment, PRD planning, PR decomposition, multi-model generation, arbitration, self-correction, fix loops, CI handling, and GitHub pull request orchestration.  
**Consequences:** All AI and automation logic is centralized in one runtime, reducing duplication and ambiguity. Shell/backend contracts stay clean. Backend reliability, observability, and testability become crucial because the highest-complexity workflows live there.  
**Rejected alternatives:**  
- **Split planning between shell and backend:** Rejected because it creates inconsistent authority and duplicated state.  
- **Put GitHub automation in Swift:** Rejected because it belongs with generation and workflow control.  
- **Use shell for lightweight generation tasks:** Rejected because all model-driven behavior should remain in the backend trust domain.

## Specifications in TRDs are the source of truth
**Status:** Accepted  
**Context:** Repository instructions repeatedly state that the 16 TRDs define all interfaces, error contracts, state machines, security controls, and performance requirements, and that implementation must match them. A platform-wide decision record must therefore preserve that governance model.  
**Decision:** The Forge platform is specification-driven. TRDs are authoritative over implementation, and engineering decisions must align to the owning TRD rather than ad hoc convention. Where code and TRDs diverge, the divergence is treated as a defect or an explicit specification change.  
**Consequences:** Design drift is reduced and subsystem ownership is clear. Engineering work requires disciplined TRD lookup before changes. Delivery speed may be slower when specifications must be updated before implementation.  
**Rejected alternatives:**  
- **Code is the source of truth:** Rejected because the platform is intentionally specified up front across subsystem boundaries.  
- **Wiki or issue-driven requirements:** Rejected because they are too informal for a safety- and workflow-sensitive agent.  
- **Per-team interpretation without document authority:** Rejected due to high risk of interface drift.

## Security-first design governed centrally by the security TRD
**Status:** Accepted  
**Context:** Repository instructions explicitly direct engineers to consult the security TRD before touching credentials, external content, generated code, or CI. The platform handles untrusted inputs, generated code, and repository automation, making a centralized security model necessary.  
**Decision:** Cross-cutting security requirements are governed centrally and apply to every subsystem. Security-sensitive behavior must defer to the platform security TRD, and no subsystem may weaken those requirements through local convenience choices.  
**Consequences:** Security controls remain consistent across shell, backend, CI interaction, and GitHub automation. Teams must evaluate changes against centralized controls. Some local optimizations may be disallowed if they violate platform security posture.  
**Rejected alternatives:**  
- **Subsystem-specific security policies only:** Rejected because threats span process boundaries and workflow stages.  
- **Best-effort security guidance:** Rejected because generated code and credential handling require enforceable controls.  
- **Security deferred to deployment environment:** Rejected because security is intrinsic to product behavior.

## Generated code is never executed by the product itself
**Status:** Accepted  
**Context:** Repository guidance states that neither process ever executes generated code. This is a core safety boundary for an autonomous coding agent that can propose changes but must not directly run arbitrary generated artifacts within the product runtime.  
**Decision:** Forge never directly executes generated application code as part of its own process runtime. Validation occurs through controlled tooling, repository checks, linting, test orchestration, and CI workflows rather than in-process execution of generated artifacts.  
**Consequences:** The attack surface from model output is materially reduced. The platform is constrained to static analysis, repository tooling, and externalized validation mechanisms. Some categories of rapid local verification are intentionally unavailable within the app runtime.  
**Rejected alternatives:**  
- **Run generated code in-process for speed:** Rejected due to severe safety risks.  
- **Execute generated code in the backend with guards:** Rejected because the policy is categorical.  
- **Allow opt-in local execution:** Rejected because it weakens a simple and auditable security invariant.

## Human-gated autonomous delivery via pull requests
**Status:** Accepted  
**Context:** The product is described as a directed build agent that plans work, implements changes, runs validation, and opens draft pull requests for review, while the user gates approval and merge. This defines the operating model of the platform.  
**Decision:** Forge delivers work as human-reviewed pull requests, one logical unit at a time. The system may autonomously plan, implement, validate, and open draft PRs, but merge authority remains with the user’s existing review and repository governance processes.  
**Consequences:** Automation accelerates delivery without removing human oversight. Repository history remains legible through discrete PR units. The system must model work decomposition carefully and integrate tightly with GitHub review workflows.  
**Rejected alternatives:**  
- **Direct commits to default branch:** Rejected because it bypasses review and governance.  
- **Large monolithic PRs for complete intents:** Rejected because the product explicitly decomposes work into logical units.  
- **Chat-only recommendations without PR creation:** Rejected because the product is an execution agent, not advisory tooling.

## Intent assessment precedes commitment to work
**Status:** Accepted  
**Context:** The product description specifies that the agent assesses its confidence in user intent and scope before committing to implementation. This up-front qualification is necessary to avoid low-confidence autonomous changes.  
**Decision:** Forge performs an explicit intent and scope assessment before beginning planning and implementation. If confidence or clarity is insufficient, the system must defer, request clarification, or decline rather than proceed with ambiguous execution.  
**Consequences:** The platform reduces erroneous automation and mis-scoped PRs. Additional front-end UX and backend evaluation logic are required before planning begins. Some tasks will intentionally stop early rather than produce weak output.  
**Rejected alternatives:**  
- **Always plan immediately from user input:** Rejected because ambiguous intent leads to poor autonomous behavior.  
- **Rely only on downstream validation to catch mistakes:** Rejected because validation is not a substitute for scoping correctness.  
- **Human manually decomposes all work first:** Rejected because automated scoping is part of product value.

## Work decomposition proceeds from intent to PRD to typed PR sequence
**Status:** Accepted  
**Context:** The platform description defines a structured pipeline: user intent becomes an ordered PRD plan, and each PRD becomes a sequence of typed pull requests. This decomposition underpins reviewability, automation, and progress tracking.  
**Decision:** Forge uses hierarchical planning. User intent is transformed into an ordered implementation plan, then into typed PR units that correspond to logical increments of work and review.  
**Consequences:** Execution becomes staged, inspectable, and resumable. Review burden is reduced through smaller changesets. Planning artifacts and PR typing become part of the platform’s contract and UI.  
**Rejected alternatives:**  
- **Flat task list only:** Rejected because it lacks the structure needed for reviewable autonomous delivery.  
- **Single end-to-end plan with one PR output:** Rejected because it undermines incremental validation and review.  
- **Unstructured agent loop:** Rejected because deterministic decomposition is core to product behavior.

## Multi-model consensus is the default generation strategy
**Status:** Accepted  
**Context:** The README states that implementation and tests are generated using two LLM providers in parallel with a consensus/arbitration model. This is central to the product’s differentiation and quality strategy.  
**Decision:** Forge uses a two-model consensus engine as the default generation architecture. Multiple provider outputs are produced in parallel and compared, with downstream arbitration selecting or synthesizing the result used in the workflow.  
**Consequences:** Output quality and robustness are expected to improve through comparative generation. Provider abstraction and arbitration logic become core backend concerns. Cost, latency, and failure handling are more complex than single-model generation.  
**Rejected alternatives:**  
- **Single-model generation:** Rejected because it reduces cross-checking and is contrary to the specified product behavior.  
- **N-model ensemble beyond two by default:** Rejected because it adds cost and latency without being the stated baseline.  
- **Sequential fallback instead of parallel consensus:** Rejected because the design calls for active comparison, not passive backup.

## Claude is the arbitration authority in consensus workflows
**Status:** Accepted  
**Context:** Repository content specifies a two-model setup in which Claude arbitrates every result. A consensus architecture requires a clear tie-break and final output authority to avoid ambiguous completion semantics.  
**Decision:** In multi-model generation flows, Claude serves as the arbitration authority responsible for adjudicating candidate outputs and determining the accepted result for subsequent validation and PR preparation.  
**Consequences:** Arbitration behavior is deterministic at the architectural level. Provider roles are asymmetric by design. Changes to provider lineup must preserve or explicitly revisit the arbitration contract.  
**Rejected alternatives:**  
- **Symmetric voting without a final arbiter:** Rejected because it leaves deadlock and output selection underdefined.  
- **GPT as arbiter:** Rejected because the specified product behavior assigns arbitration to Claude.  
- **Human arbitration for every generation step:** Rejected because it would break autonomous throughput.

## Validation pipeline includes self-correction, lint gating, iterative fix loop, and CI
**Status:** Accepted  
**Context:** The product description defines a layered post-generation validation process: self-correction pass, lint gate, iterative fix loop, CI execution, and PR creation. This pipeline is necessary because code generation is probabilistic and must be constrained before review.  
**Decision:** All generated changes flow through a mandatory validation pipeline consisting of automated self-correction, static quality gates, iterative fixes, and CI-backed verification before draft PR creation.  
**Consequences:** Generated output is filtered through multiple safeguards before user review. Backend orchestration must support retries, failure classification, and stateful remediation. End-to-end latency increases, but review quality improves.  
**Rejected alternatives:**  
- **Open PRs immediately after first generation:** Rejected because raw model output is too unreliable.  
- **CI-only validation:** Rejected because earlier gates catch issues more cheaply and deterministically.  
- **Manual remediation only:** Rejected because autonomous correction is part of platform value.

## GitHub pull requests are the system output contract
**Status:** Accepted  
**Context:** The product is defined around opening GitHub draft pull requests as its primary artifact. The system is not merely advisory; it acts on repositories through branch and PR workflows.  
**Decision:** Forge’s primary externally visible unit of delivery is the GitHub pull request. Internal planning, generation, and validation exist to produce reviewable PRs that fit repository governance and CI practices.  
**Consequences:** GitHub integration is mission-critical. Branching, commit hygiene, PR metadata, and review-state synchronization must be first-class features. Support for other SCM targets is not assumed by default.  
**Rejected alternatives:**  
- **Patch files or local diffs as primary output:** Rejected because they do not match the intended review workflow.  
- **Direct issue updates without code artifacts:** Rejected because the product must produce implementation.  
- **Generalized SCM abstraction first:** Rejected because GitHub is the specified operational target.

## App-bundled Python runtime
**Status:** Accepted  
**Context:** The shell TRD identifies Python 3.12 as bundled, and the shell is responsible for packaging and installation. A bundled runtime is necessary to deliver a consistent backend environment inside a native macOS app.  
**Decision:** Forge ships with a bundled Python runtime as part of the application distribution, and the shell is responsible for installing and launching the backend in a controlled, version-compatible environment.  
**Consequences:** Runtime consistency improves and host-machine dependency drift is reduced. Packaging and update complexity increase. Security and notarization considerations must include the embedded interpreter and its dependencies.  
**Rejected alternatives:**  
- **Require user-installed Python:** Rejected because it creates fragility and undermines product-grade packaging.  
- **Compile backend to a native binary only:** Rejected because the architecture explicitly specifies Python.  
- **Containerize backend locally:** Rejected because it adds unnecessary operational weight for a bundled desktop app.

## Sparkle-based auto-update for application distribution
**Status:** Accepted  
**Context:** The shell TRD explicitly includes Sparkle auto-update as part of installation and distribution responsibilities. Desktop application lifecycle management requires a defined update mechanism.  
**Decision:** Forge uses Sparkle for macOS application auto-update within the native shell distribution model. Updates are managed as part of the app lifecycle rather than relying solely on manual replacement installs.  
**Consequences:** The platform gains a standard macOS update experience and can ship runtime/backend changes together. Release signing, notarization, and update feed management become operational requirements.  
**Rejected alternatives:**  
- **Manual download-only updates:** Rejected because it produces poor UX and weaker release hygiene.  
- **App Store distribution:** Rejected because the specified distribution model centers on direct app packaging and Sparkle.  
- **Custom updater:** Rejected because Sparkle is an established fit for the shell requirements.

## Biometric gate as part of local identity and access control
**Status:** Accepted  
**Context:** The shell owns identity and authentication, and the shell TRD includes a biometric gate. A local desktop product with secret handling requires a user-presence control before exposing sensitive capabilities.  
**Decision:** Forge integrates biometric authentication in the shell as part of local access control and session establishment for security-sensitive actions and state transitions.  
**Consequences:** User presence can be verified using native macOS capabilities. UX flows must account for biometric availability, failure, and fallback behavior as defined by the shell’s auth model. Security-sensitive backend actions depend on shell-mediated authorization state.  
**Rejected alternatives:**  
- **Password-only local gate:** Rejected because native biometrics are explicitly part of the shell contract.  
- **No local gate after app launch:** Rejected because secrets and repository actions require stronger session controls.  
- **Backend-managed auth prompts:** Rejected because auth authority belongs to the shell.

## Swift module architecture with subsystem boundaries
**Status:** Accepted  
**Context:** The shell TRD defines Swift module architecture as part of the shell’s responsibilities. With multiple concerns—UI, auth, XPC/socket orchestration, updates, state, and security—clear modularity is required to preserve maintainability.  
**Decision:** The Swift shell is organized into explicit modules or subsystem boundaries reflecting major concerns such as UI, authentication, secret management, backend orchestration, and distribution/update concerns.  
**Consequences:** The shell remains maintainable and testable as the product grows. Interface boundaries can align to TRD ownership. Initial implementation overhead is higher than a monolithic app target.  
**Rejected alternatives:**  
- **Single monolithic shell target with implicit boundaries:** Rejected due to long-term maintainability risk.  
- **Feature slicing without platform/service separation:** Rejected because cross-cutting security and lifecycle concerns need explicit ownership.  
- **Backend-driven UI state only:** Rejected because shell-side concerns require native modular control.

## UX is not chat-first; it is workflow- and artifact-first
**Status:** Accepted  
**Context:** The README explicitly states the product is not a chat interface, not autocomplete, and not a copilot. The user experience centers on specifications, intent, plans, PRs, and reviewable artifacts.  
**Decision:** Forge’s UX is designed around directed build workflows, status, plans, validation progress, and pull request artifacts rather than an open-ended conversational interface. Conversational affordances may support the workflow, but they are not the primary product model.  
**Consequences:** UI priorities favor dashboards, plans, cards, panels, and review states over chat transcripts. Interaction design must keep users oriented around execution and gating. Expectations are set clearly about what the product is and is not.  
**Rejected alternatives:**  
- **Chat-first assistant UX:** Rejected because it conflicts with the product definition.  
- **Inline code-completion UX:** Rejected because the platform is not an editor copilot.  
- **Pure background automation with no artifact-centric UI:** Rejected because user review and gating are central.

## Typed state machines and explicit error contracts across subsystems
**Status:** Accepted  
**Context:** Repository guidance emphasizes that TRDs define interfaces, error contracts, and state machines. In a cross-process autonomous workflow system, hidden states and ad hoc error handling create unsafe and irreproducible behavior.  
**Decision:** Subsystems communicate through explicit state models and documented error contracts. Workflow progression, backend orchestration, authentication, and PR execution states are treated as formal interfaces rather than implicit control flow.  
**Consequences:** Behavior becomes more testable, observable, and recoverable. Cross-process integration requires disciplined versioning and mapping of states/errors. Development may be slower than ad hoc exception-based flows, but reliability improves.  
**Rejected alternatives:**  
- **Implicit state through mutable flags:** Rejected because it is brittle across process boundaries.  
- **Undocumented exception propagation:** Rejected because it produces poor UX and unstable integrations.  
- **Best-effort status text only:** Rejected because orchestration requires machine-readable state.

## Test-first change discipline aligned to owning TRDs
**Status:** Accepted  
**Context:** Agent guidance instructs contributors to identify the owning TRD, read interfaces and testing requirements, and run existing tests before making changes. This indicates a platform-wide engineering policy rather than a local implementation detail.  
**Decision:** Changes to Forge must be made in the context of the owning TRD and validated by the relevant automated tests before and after modification. Test scope and expectations are derived from subsystem specifications, especially around interfaces, security, and workflow behavior.  
**Consequences:** Regression risk is lowered and subsystem contracts remain enforceable. Contributors must understand specification ownership before editing code. Development workflows require discipline and may slow opportunistic changes.  
**Rejected alternatives:**  
- **Code-first changes with tests added later if needed:** Rejected because interface drift and regressions are too costly.  
- **Manual verification as primary quality gate:** Rejected because autonomous workflow systems require repeatable validation.  
- **Global smoke tests only:** Rejected because subsystem contracts need targeted coverage.