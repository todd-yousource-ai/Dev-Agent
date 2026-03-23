# DECISIONS.md

## Two-process native architecture
**Status:** Accepted  
**Context:** Forge is a native macOS AI coding agent with distinct responsibilities: UI, OS integration, auth, and secret handling on one side; planning, consensus generation, review, CI orchestration, and GitHub automation on the other. The TRDs define a split between a trusted native shell and an intelligence backend.  
**Decision:** Forge is implemented as a two-process system: a Swift/SwiftUI macOS shell and a bundled Python 3.12 backend. The Swift shell owns UI, authentication, Keychain access, session lifecycle, app packaging, updates, and local orchestration. The Python backend owns consensus, planning, code generation, review pipeline, repository operations, and GitHub interactions.  
**Consequences:** Clear trust boundaries, simpler subsystem ownership, and better isolation of secrets from model/runtime code. Cross-process contracts must remain stable and explicit. Operational complexity increases because startup, supervision, IPC, and version compatibility must be managed.  
**Rejected alternatives:** Single-process app embedding all logic in Swift was rejected due to slower iteration for AI pipeline development and weaker separation of concerns. A fully remote backend was rejected because it weakens local control, increases data exposure, and conflicts with the product’s native-first security model.

## Swift shell is the system-of-record for trust-sensitive functions
**Status:** Accepted  
**Context:** Authentication, biometric gating, OS integration, and secret storage are macOS-specific trust domains. The TRDs place security ownership in the native shell rather than in the AI backend.  
**Decision:** The Swift shell is the authority for identity, session unlock, Keychain storage, provider credential mediation, app state gating, and local policy enforcement. The Python backend never directly reads from Keychain or independently establishes user identity.  
**Consequences:** Sensitive capabilities remain in the highest-trust local component. Backend code must request privileged actions through explicit shell-mediated interfaces. Some workflows become more indirect due to policy checks and brokered access.  
**Rejected alternatives:** Allowing Python direct access to secrets or auth state was rejected because it expands the attack surface and weakens macOS-native security controls.

## Python backend owns intelligence and repository automation
**Status:** Accepted  
**Context:** The generation pipeline requires rapid iteration across planning, consensus orchestration, code transformation, review loops, and GitHub operations. The TRDs assign these concerns to Python.  
**Decision:** The backend is the sole owner of PRD planning, PR sequencing, provider orchestration, consensus arbitration flow, code/test generation, review passes, CI result ingestion, and GitHub draft PR creation.  
**Consequences:** AI workflow logic remains centralized and easier to evolve. Shell code stays focused on native concerns. The backend becomes a critical subsystem whose interfaces and error contracts must be rigorously versioned and tested.  
**Rejected alternatives:** Splitting pipeline logic across Swift and Python was rejected because it would blur ownership and complicate debugging, testing, and protocol design.

## Authenticated local IPC over Unix domain socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two-process architecture requires local interprocess communication that is simple, inspectable, and suitable for streaming structured events. The TRDs specify authenticated Unix socket communication with line-delimited JSON.  
**Decision:** The shell and backend communicate over an authenticated local Unix domain socket using line-delimited JSON messages. Message schemas are explicit, typed by operation/event kind, and designed for incremental streaming of status and results.  
**Consequences:** IPC remains local, low-latency, and easy to debug. Contracts are language-agnostic and testable. Message framing and schema evolution must be handled carefully. Authentication and socket lifecycle management are mandatory.  
**Rejected alternatives:** XPC-only transport was rejected because the backend is Python-based and portability of protocol tooling is important. HTTP-on-localhost was rejected due to unnecessary network semantics and larger attack surface. Binary custom protocols were rejected because they reduce debuggability.

## IPC contracts are explicit, versioned, and fail-closed
**Status:** Accepted  
**Context:** A split-process platform can drift unless interfaces are tightly controlled. The TRDs emphasize documented interfaces and error contracts.  
**Decision:** All shell↔backend messages use explicit schemas with protocol versioning, strict validation, and fail-closed handling for unknown or malformed messages. Compatibility is intentional rather than implicit.  
**Consequences:** Safer upgrades and more predictable failures. Development requires schema maintenance and compatibility tests. Rapid ad hoc message additions are discouraged.  
**Rejected alternatives:** Loosely structured JSON and best-effort parsing were rejected because they cause hidden coupling and unpredictable runtime behavior.

## Generated code is never executed by the agent
**Status:** Accepted  
**Context:** The product creates code autonomously, which creates obvious supply-chain and prompt-injection risks. The security TRD explicitly constrains execution behavior.  
**Decision:** Neither the Swift shell nor the Python backend ever executes generated code as part of its autonomous operation. Validation is limited to static processing, repository mutation, and CI orchestration through controlled external systems.  
**Consequences:** Strong reduction in local code-execution risk from model output. Some classes of dynamic verification are deferred to repository CI or user-controlled environments. Product scope excludes autonomous local execution loops.  
**Rejected alternatives:** Running generated code in-process or in a local sandbox was rejected because it materially increases exploitability and violates the security posture defined by the TRDs.

## CI is the execution boundary for generated artifacts
**Status:** Accepted  
**Context:** Forge must validate changes while preserving the prohibition on local execution of generated code. CI provides an auditable, repository-owned execution environment.  
**Decision:** Execution-based validation of generated code occurs only through the target repository’s CI workflows or other user-controlled external systems, not on the local Forge host. Forge may trigger, observe, and ingest CI results, but not run the generated implementation locally.  
**Consequences:** Validation depends on repository CI quality and availability. CI feedback becomes a first-class input to the review and PR flow. Local turnaround can be slower than direct execution.  
**Rejected alternatives:** Local Docker/sandbox execution was rejected because it still constitutes executing generated code on the user machine and broadens the local attack surface.

## Consensus generation uses two providers in parallel with arbitration
**Status:** Accepted  
**Context:** The product is built around higher reliability than a single-model coding assistant. README and TRD materials describe a two-model consensus approach with arbitration.  
**Decision:** Forge generates candidate implementation output using two LLM providers in parallel and resolves disagreement through a structured arbitration step. Claude is the designated arbiter for final result selection where the TRDs specify that role.  
**Consequences:** Improved robustness against single-model failure modes and better comparative reasoning. Cost, latency, and orchestration complexity increase. Provider abstraction must support heterogeneity in APIs, rate limits, and output formats.  
**Rejected alternatives:** Single-provider generation was rejected because it weakens reliability. Majority voting across many models was rejected as too costly and operationally complex for the product’s design point.

## Provider integrations are abstracted behind adapters
**Status:** Accepted  
**Context:** Multiple model providers are central to the platform, but each has different APIs, quotas, auth mechanisms, and response shapes.  
**Decision:** Forge uses a provider adapter layer in the backend so consensus and pipeline logic depend on a normalized provider interface rather than vendor-specific APIs.  
**Consequences:** Provider logic is swappable and testable. New providers can be added with bounded impact. Adapter maintenance is required as vendors evolve. Lowest-common-denominator design pressure must be managed.  
**Rejected alternatives:** Hard-coding provider calls directly inside consensus logic was rejected because it creates brittle coupling and slows provider evolution.

## Claude is the final arbitration authority in consensus disputes
**Status:** Accepted  
**Context:** Product positioning and repository guidance explicitly state that two-model consensus uses Claude as the arbitrator. This must be made deterministic in system behavior.  
**Decision:** When primary model outputs materially diverge and consensus logic requires a final arbiter, Claude is the authoritative arbitration step used to determine the accepted result, subject to policy and validation gates.  
**Consequences:** The platform has a clear tie-break rule and deterministic control flow. Dependence on one provider for arbitration becomes a critical operational dependency. Outage and degradation handling must account for that role.  
**Rejected alternatives:** Human-only arbitration for all disagreements was rejected because it breaks automation. Symmetric tie-breaking without a fixed arbiter was rejected because it produces unstable behavior.

## Work is decomposed from intent to PRD plan to ordered pull requests
**Status:** Accepted  
**Context:** Forge is not a chat system; it is a directed build agent. The README describes decomposition from user intent into a PRD plan and then into a sequence of logical PRs.  
**Decision:** User intent and repository specifications are transformed into an ordered plan of implementation units. Each unit is realized as a separate pull request representing a logical, reviewable change boundary.  
**Consequences:** Work becomes auditable, reviewable, resumable, and less risky than monolithic generation. Planning quality is critical. More pipeline machinery is required to preserve sequencing and dependencies.  
**Rejected alternatives:** Generating one large branch for an entire feature was rejected because it harms reviewability and rollback. Pure conversational iteration was rejected because it does not satisfy the product’s directed-build purpose.

## Pull requests are the primary delivery unit
**Status:** Accepted  
**Context:** The platform’s operating model is centered on draft PR creation and human review. A stable unit of delivery is required for gating and repository integration.  
**Decision:** Forge delivers autonomous implementation as Git branches and draft pull requests, one per logical unit of work, rather than direct pushes to protected branches or opaque patches outside repository workflows.  
**Consequences:** Repository-native review, CI, auditability, and rollback are preserved. GitHub integration becomes essential. Users must work within PR-based repository practices.  
**Rejected alternatives:** Direct commits to main were rejected because they bypass review and increase risk. Patch-file export as the main mode was rejected because it weakens orchestration and lifecycle tracking.

## Every generated PR includes implementation and tests
**Status:** Accepted  
**Context:** The product claims to generate implementation and tests for each PR. This is necessary for quality and CI usefulness.  
**Decision:** Forge treats tests as part of the required output for each generated pull request whenever the change is testable within the repository’s conventions. Test generation is not an optional afterthought.  
**Consequences:** Better confidence and CI signal. Pipeline complexity increases because test updates must remain aligned with implementation changes. Some repositories may require explicit handling where tests are infeasible or absent.  
**Rejected alternatives:** Implementation-only PRs by default were rejected because they create low-confidence changes and shift too much burden to reviewers.

## Three-pass review is mandatory before PR creation
**Status:** Accepted  
**Context:** Autonomous code generation needs structured self-critique before it reaches a repository PR. The README defines a 3-pass review cycle.  
**Decision:** Forge performs a mandatory three-pass review cycle on generated changes before opening a draft PR. The passes are distinct review stages rather than a single monolithic post-check.  
**Consequences:** Quality improves through iterative refinement and defect catching. Latency and token cost increase. Review stages require explicit state tracking and reproducibility.  
**Rejected alternatives:** Single-pass review was rejected because it provides weaker quality control. Unlimited review loops were rejected because they risk non-termination and cost blowups.

## Human approval gates progression between pull requests
**Status:** Accepted  
**Context:** The product builds the next PR while the user reviews the last one, but merge and progression remain user-governed.  
**Decision:** Forge may prepare subsequent work autonomously, but advancement of repository state remains gated by human review and approval at the PR level. The user remains the final decision-maker on merge and acceptance.  
**Consequences:** User control is preserved, reducing the risk of runaway automation. End-to-end throughput is bounded by review cadence. The system must track dependencies between prepared and approved work.  
**Rejected alternatives:** Fully autonomous merge to protected branches was rejected because it violates the product’s oversight model.

## GitHub is the canonical VCS and PR integration target
**Status:** Accepted  
**Context:** The backend is specified to own GitHub operations, and product behavior is PR-centric.  
**Decision:** Forge is designed around Git and GitHub as the canonical repository hosting and pull request platform for autonomous delivery flows.  
**Consequences:** Deep GitHub automation is supported and optimized. Non-GitHub forges are not first-class in the initial platform design. Product wording and UX can be concrete rather than generic.  
**Rejected alternatives:** Designing for every forge equally at launch was rejected because it dilutes scope and slows delivery of a cohesive workflow.

## Native macOS application as the primary client
**Status:** Accepted  
**Context:** TRD-1 defines a native macOS shell with packaging, install, auth, and UI. The product is explicitly a native macOS agent.  
**Decision:** Forge ships as a native macOS application built with Swift 5.9+ and SwiftUI, targeting macOS 13.0+ as the primary and required client environment.  
**Consequences:** Deep OS integration, native UX, biometric support, Keychain access, and app update mechanisms are available. Platform reach is intentionally narrower. Cross-platform support is deferred.  
**Rejected alternatives:** Electron/web-first client was rejected because it weakens native trust integration and conflicts with the TRD-defined shell architecture.

## SwiftUI is the UI framework for application surfaces
**Status:** Accepted  
**Context:** The shell TRD specifies SwiftUI-based application surfaces. Consistency across cards, panels, and app state is important.  
**Decision:** User-facing application views are implemented in SwiftUI, with view models and state flow structured to align with shell module boundaries.  
**Consequences:** Faster native UI composition and consistency with modern macOS patterns. Some low-level UI customization may require bridging where SwiftUI is insufficient.  
**Rejected alternatives:** AppKit-first UI was rejected as the default because it increases complexity for the specified product surfaces without corresponding benefit.

## Secrets are stored in Keychain and never persisted in plaintext
**Status:** Accepted  
**Context:** The shell owns secret management, and the security model requires strong local credential handling.  
**Decision:** Provider credentials, GitHub tokens, and other persistent secrets are stored only in the macOS Keychain, mediated by the Swift shell. Plaintext persistence in files, logs, preferences, or backend-owned stores is prohibited.  
**Consequences:** Local credential handling aligns with macOS security controls. Development and diagnostics must account for limited visibility into secret values. Backend design must work with token brokering rather than direct storage.  
**Rejected alternatives:** File-based encrypted secret stores or backend-managed secrets were rejected because they weaken the native trust model and duplicate OS facilities.

## Biometric/session gating is required for privileged access
**Status:** Accepted  
**Context:** The shell is responsible for identity and session lifecycle. The platform needs a clear unlock model before exposing sensitive operations.  
**Decision:** Forge requires a session-unlock mechanism using native authentication controls, including biometric gating where available, before exposing privileged actions and secrets to active workflows.  
**Consequences:** Better local defense against casual unauthorized use. UX must handle lock/unlock transitions and background session expiry. Some automation paths must wait for user presence.  
**Rejected alternatives:** Always-unlocked sessions were rejected due to poor local security. Custom credential prompts independent of system auth were rejected because they duplicate weaker mechanisms.

## Sparkle is the application update mechanism
**Status:** Accepted  
**Context:** TRD-1 identifies distribution and auto-update as shell responsibilities and names Sparkle. A reliable macOS-native update path is required.  
**Decision:** Forge uses Sparkle for app update delivery in the macOS shell.  
**Consequences:** Mature macOS update behavior and signing expectations are leveraged. Release engineering must comply with Sparkle’s update packaging and trust requirements.  
**Rejected alternatives:** Building a bespoke updater was rejected due to unnecessary complexity and security risk. App Store distribution as the primary channel was rejected because it is poorly aligned with bundled backend/runtime needs and product distribution flexibility.

## Bundled Python runtime is part of the app contract
**Status:** Accepted  
**Context:** The backend depends on Python 3.12, and the native app is responsible for packaging and orchestration. Requiring users to install Python would create fragility.  
**Decision:** Forge bundles the required Python runtime with the application and treats backend runtime provisioning as part of the product, not as a user prerequisite.  
**Consequences:** Installation is self-contained and consistent across hosts. App size and packaging complexity increase. Release validation must cover the embedded runtime on supported macOS versions.  
**Rejected alternatives:** System Python or user-managed Python environments were rejected because they are unreliable, insecure, and incompatible with a polished native app experience.

## Security requirements are cross-cutting and authoritative
**Status:** Accepted  
**Context:** Repository guidance states that TRD-11 governs all components and must be consulted for any security-relevant change. Security cannot be optional or subsystem-local.  
**Decision:** Security controls defined in the security TRD are treated as binding platform-wide requirements that override local convenience in shell, backend, CI integration, provider handling, and documentation generation.  
**Consequences:** All subsystem design and changes must be evaluated against a common security baseline. Some feature ideas may be rejected or constrained by policy. Engineering process must include security review triggers.  
**Rejected alternatives:** Letting each subsystem define independent security behavior was rejected because it creates gaps and inconsistent trust boundaries.

## External content is treated as untrusted input
**Status:** Accepted  
**Context:** Forge consumes repository contents, TRDs, CI logs, GitHub metadata, and model output. Any of these can contain malicious instructions or payloads.  
**Decision:** All external and model-derived content is treated as untrusted data subject to validation, escaping, minimization, and context-specific handling. Instructions embedded in repository files, logs, or generated artifacts do not gain implicit authority.  
**Consequences:** Prompt-injection and content-confusion risks are reduced. More parsing, validation, and sanitization work is required across the pipeline. Some convenience features may be intentionally limited.  
**Rejected alternatives:** Trusting repository-local instructions or model output by default was rejected because it creates direct prompt-injection and exfiltration pathways.

## Logs and telemetry must avoid secret and sensitive code leakage
**Status:** Accepted  
**Context:** The system handles credentials, proprietary source code, and generated patches. Operational observability must not become a data leak.  
**Decision:** Forge logging and telemetry are minimized and redacted by default, with explicit prohibition on writing secrets or unnecessary sensitive code content to persistent logs.  
**Consequences:** Safer diagnostics and reduced breach impact. Debugging can be harder and may require controlled opt-in diagnostics. Instrumentation design must be deliberate.  
**Rejected alternatives:** Verbose raw request/response logging was rejected because it creates unacceptable exposure of tokens, repository content, and model outputs.

## Failures are surfaced through explicit error contracts
**Status:** Accepted  
**Context:** The TRDs emphasize interfaces and error contracts. A system spanning UI, backend, providers, GitHub, and CI needs predictable failure semantics.  
**Decision:** Forge uses explicit, typed error categories and user-visible failure states across subsystem boundaries rather than opaque generic failures. Errors are designed to preserve actionable context without leaking sensitive data.  
**Consequences:** Better UX, easier recovery, and more testable behavior. Engineers must maintain error taxonomies and mapping across layers.  
**Rejected alternatives:** Stringly-typed ad hoc errors were rejected because they undermine automation, retry policy, and user comprehension.

## Subsystem ownership follows TRD boundaries
**Status:** Accepted  
**Context:** The repository guidance instructs implementers to find the owning TRD before changing code. The platform spans 12 TRDs and needs stable responsibility boundaries.  
**Decision:** Architectural ownership is aligned to the TRD set. Components, interfaces, tests, and changes are expected to map back to the TRD that specifies them, with cross-TRD dependencies made explicit rather than implicit.  
**Consequences:** Specification traceability improves and design drift is reduced. Cross-cutting changes require more disciplined coordination.  
**Rejected alternatives:** Organizing architecture primarily around implementation convenience without spec traceability was rejected because it encourages divergence from the source-of-truth documents.

## Documentation regeneration is optional and post-build
**Status:** Accepted  
**Context:** The product may optionally regenerate documentation when the build completes, but documentation changes should not destabilize core delivery.  
**Decision:** Documentation regeneration is treated as an optional post-build step, not a prerequisite for code delivery, and is executed only within the same guarded repository workflow model as other changes.  
**Consequences:** Core implementation flow remains primary. Documentation can stay aligned when enabled without blocking engineering progress. Documentation-only noise is reduced.  
**Rejected alternatives:** Mandatory documentation regeneration for every change was rejected because it can create unnecessary churn and slow delivery. Excluding documentation support entirely was rejected because it reduces value for specification-driven development.

## Repository tests must be run before making changes in development workflow
**Status:** Accepted  
**Context:** Repository instructions to agents require running the existing test suite before modifying code. This supports safe evolution of a complex system.  
**Decision:** The standard development workflow for Forge includes running the current test suite before changes and maintaining subsystem-specific tests for interfaces, security behavior, and pipeline correctness.  
**Consequences:** Regressions are caught earlier and engineers get a known baseline. Local development is slower but safer. Test hygiene becomes part of normal change management.  
**Rejected alternatives:** Allowing speculative changes without baseline verification was rejected because it increases regression risk and obscures root cause when failures occur.