# DECISIONS.md

## Two-process local architecture
**Status:** Accepted  
**Context:** Forge is specified as a native macOS AI coding agent with sharply separated responsibilities: native OS integration, user interface, authentication, and secret handling on one side; planning, generation, consensus, review, and repository automation on the other. The TRDs require strong isolation around credentials and generated content, while preserving a responsive native shell and a flexible intelligence layer.  
**Decision:** Forge uses a two-process architecture: a Swift/SwiftUI macOS shell and a bundled Python backend. The Swift shell owns UI, lifecycle, auth, Keychain access, update flow, and local orchestration. The Python backend owns planning, consensus, generation, review pipeline, CI orchestration, and GitHub operations. Communication occurs only over an authenticated local IPC channel using line-delimited JSON.  
**Consequences:** This creates a hard trust and responsibility boundary, reduces secret exposure to the backend, enables native macOS UX without embedding the intelligence stack in Swift, and allows the backend to evolve independently. It also introduces IPC contracts, process supervision, version compatibility requirements, and recovery paths for partial failure.  
**Rejected alternatives:** A single monolithic app was rejected because it weakens isolation and couples native shell concerns to model orchestration. A fully remote backend was rejected because it increases trust surface, complicates local repo access, and conflicts with the local-first security model. Embedding Python logic directly in-process was rejected because it reduces fault isolation and complicates least-privilege boundaries.

## Swift shell as owner of trust, identity, and secrets
**Status:** Accepted  
**Context:** The platform handles highly sensitive material including GitHub credentials, provider API keys, repository paths, and generated code. TRD-11 places special constraints on credentials and external content. A single component must own privileged interactions with the operating system.  
**Decision:** The Swift shell is the only component permitted to interact directly with Keychain, biometric APIs, user identity/session state, app entitlements, and privileged macOS services. The Python backend never reads secrets from storage directly and only receives scoped tokens or session material required for a specific operation.  
**Consequences:** Secret storage and trust decisions remain centralized in the most constrained process. Backend compromise has reduced blast radius. This also means the shell must provide broker APIs for secret retrieval, session renewal, and provider credential injection, and those APIs become security-critical.  
**Rejected alternatives:** Allowing both processes direct Keychain access was rejected because it broadens the trusted computing base. Putting all auth inside Python was rejected because it weakens platform integration and violates the native-shell ownership defined in the TRDs.

## Python backend as owner of intelligence and repository automation
**Status:** Accepted  
**Context:** The platform’s core product value lies in planning work from TRDs, generating code with multiple providers, reviewing outputs, managing PR sequencing, and interacting with GitHub. These workflows are model- and pipeline-heavy, change faster than shell concerns, and align better with Python ecosystem tooling.  
**Decision:** The Python backend owns the consensus engine, provider adapters, prompt assembly, planning pipeline, code generation, review loops, documentation regeneration, CI orchestration, repository analysis, Git operations, and GitHub API interactions.  
**Consequences:** Core product logic is concentrated in the backend where model and automation libraries are strongest. The shell remains thinner and more stable. The cost is that cross-boundary contracts must be explicit, versioned, and robust to backend crashes or upgrade mismatch.  
**Rejected alternatives:** Implementing orchestration in Swift was rejected due to reduced ecosystem fit and slower iteration. Splitting intelligence across shell and backend was rejected because it creates blurred ownership and inconsistent state.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two-process design requires structured, low-latency, local communication. The protocol must be inspectable, debuggable, and strict enough for typed contracts while remaining simple to implement in Swift and Python. The trust model also requires peer authentication and replay-resistant session establishment.  
**Decision:** The shell and backend communicate over an authenticated Unix domain socket using line-delimited JSON messages. The protocol is request/response plus event streaming where needed, with schema-defined message types, correlation IDs, version negotiation, and authenticated session startup.  
**Consequences:** Local IPC remains simple and operationally transparent. Logs and tests can validate protocol boundaries easily. This constrains payload formats, requires careful framing and backpressure handling, and makes protocol compatibility a first-class engineering concern.  
**Rejected alternatives:** XPC end-to-end was rejected because the backend is Python-based and cross-language ergonomics are poor. HTTP on localhost was rejected because it adds unnecessary network semantics and attack surface. Binary custom protocols were rejected because they reduce debuggability and increase implementation complexity.

## Local-first execution with no execution of generated code by the agent
**Status:** Accepted  
**Context:** The product manipulates untrusted inputs from TRDs, repositories, model outputs, and remote APIs. The specification explicitly forbids executing generated code. Security depends on limiting the consequences of prompt injection, malicious repo contents, and unsafe generations.  
**Decision:** Forge operates locally on the user’s machine and never executes generated application code. It may perform static analysis, file edits, tests and CI only through explicitly defined safe workflows, but generated code itself is not run by the agent as part of autonomous decision-making. Validation is delegated to repository CI and user review gates.  
**Consequences:** The platform significantly reduces risk from arbitrary code execution and prompt-to-execution escalation. It also constrains local validation strategies and requires stronger static checks, review passes, and CI reliance before PR creation.  
**Rejected alternatives:** Running generated code in-process or in ad hoc local sandboxes was rejected because it violates the security model and materially increases risk. A fully autonomous “execute and iterate” loop was rejected for the same reason.

## TRDs as the authoritative source of build intent
**Status:** Accepted  
**Context:** Forge is not a general chatbot; it is a directed build system driven by technical specifications. To keep planning deterministic and auditable, the system must privilege repository-provided requirements over conversational drift.  
**Decision:** Technical Requirements Documents in the repository are the canonical source of truth for planning, decomposition, implementation, validation expectations, and documentation regeneration. User intent is interpreted through the TRDs, not as an override to them. When intent conflicts with TRDs, the system must surface the conflict rather than invent requirements.  
**Consequences:** Planning remains grounded, reproducible, and reviewable. This constrains UX by requiring document ingestion and indexing, and it may block ambiguous requests until specifications are clarified.  
**Rejected alternatives:** Treating chat intent as primary was rejected because it encourages requirement drift. Allowing the agent to infer missing requirements freely was rejected because it undermines auditability and traceability.

## Directed build workflow rather than chat-centric interaction
**Status:** Accepted  
**Context:** The product promise is autonomous software delivery through planned PR sequences, not open-ended conversation. The UX and backend both need a clear operational model aligned with backlog decomposition and review gates.  
**Decision:** Forge is designed as a directed build agent. The primary user flow is: ingest repository and TRDs, state intent, derive a PRD/plan, decompose into ordered pull requests, generate and review each unit, run CI, open draft PRs, and proceed only after user approval gates. Conversational interaction is secondary and operational, not the product center.  
**Consequences:** The platform can optimize for throughput, traceability, and artifact production rather than conversational richness. This constrains UI design, model prompting, and telemetry toward pipeline state over chat history.  
**Rejected alternatives:** A chat-first copilot-style interface was rejected because it does not align with the specification or the review-gated PR workflow. Freeform coding assistance as the main mode was rejected for the same reason.

## Sequential pull-request pipeline with explicit user gating
**Status:** Accepted  
**Context:** Large implementation efforts must be broken into logical, reviewable units. The README specifies one PR per logical unit and that the next PR is built while the user reviews the previous one, but advancement still requires approval.  
**Decision:** Forge decomposes work into an ordered sequence of pull requests. Each PR must remain logically coherent and scoped for review. Draft PRs are opened for human inspection, and progression to subsequent integration stages is gated by explicit user approval or merge state as defined by the workflow.  
**Consequences:** Users receive manageable review units and stronger control over repository changes. This increases planning overhead and requires dependency tracking between PRs, branch management, and queue control.  
**Rejected alternatives:** One giant PR per intent was rejected because it is harder to review and riskier to merge. Fully autonomous direct-to-main delivery was rejected because it removes required human control.

## Two-model parallel generation with Claude arbitration
**Status:** Accepted  
**Context:** The product specification defines a consensus engine using two model providers in parallel and requires a deterministic arbitration path. This design aims to improve output quality and robustness against single-model failure modes.  
**Decision:** Forge uses at least two model providers in parallel for core generation tasks, specifically Claude and GPT-4o as the baseline pairing, with Claude serving as the final arbiter for consensus decisions where the pipeline requires a single selected result.  
**Consequences:** Quality and resilience improve through comparison, divergence analysis, and arbitration. This increases latency, cost, and orchestration complexity, and requires normalized provider interfaces and deterministic arbitration rules.  
**Rejected alternatives:** A single-model pipeline was rejected because it weakens robustness and contradicts the product design. Majority voting among many models was rejected because it increases cost and complexity beyond the required architecture. Human arbitration at every step was rejected because it reduces autonomy and throughput.

## Provider abstraction layer for model interoperability
**Status:** Accepted  
**Context:** Forge depends on multiple LLM providers with differing APIs, token semantics, streaming behaviors, and error contracts. The consensus engine requires consistent behavior across providers.  
**Decision:** The backend implements a provider adapter abstraction that normalizes prompt submission, response collection, usage accounting, retries, safety handling, and provider-specific errors into a common interface consumed by the consensus engine and pipeline.  
**Consequences:** The core pipeline remains provider-agnostic and extensible. Adding providers becomes localized. This requires a carefully designed canonical schema, adapter tests, and explicit handling of provider capability mismatches.  
**Rejected alternatives:** Coding provider logic directly into the pipeline was rejected because it causes tight coupling. Standardizing on a single provider-specific API shape was rejected because it reduces extensibility.

## Three-pass review cycle before PR creation
**Status:** Accepted  
**Context:** Generated code quality must be improved prior to user review, especially since generated code is not executed autonomously and human attention is finite. The product description specifies a 3-pass review cycle.  
**Decision:** Every generated PR candidate goes through a structured three-pass review cycle in the backend before draft PR creation. The passes are designed to identify correctness gaps, specification mismatches, test omissions, and maintainability issues, with revisions applied between passes according to explicit stop conditions.  
**Consequences:** User-facing PR quality improves and obvious defects are filtered earlier. This increases compute cost and orchestration time, and demands durable intermediate artifacts and repeatable pass criteria.  
**Rejected alternatives:** No review pass beyond generation was rejected because it produces lower-quality PRs. Unlimited critique/rewrite loops were rejected because they create unpredictable cost and runtime. A single review pass was rejected as insufficient for the stated quality bar.

## CI as the primary execution-based validation boundary
**Status:** Accepted  
**Context:** The agent must not execute generated code autonomously, but changes still require evidence of validity. Repository CI already represents the project-defined execution environment and can serve as the controlled validation stage.  
**Decision:** Forge relies on repository CI and defined test workflows as the primary execution-based validation mechanism before or alongside draft PR readiness, according to repository configuration. The agent may prepare changes and trigger or observe CI, but execution authority resides in the project’s CI boundary rather than arbitrary local runs of generated code.  
**Consequences:** Validation aligns with project standards and remains auditable. This can increase turnaround time and requires strong CI integration, status polling, failure summarization, and recovery handling.  
**Rejected alternatives:** Heavy local execution of generated code was rejected due to security constraints. Skipping CI prior to PR creation was rejected because it lowers trust in generated changes.

## Draft pull requests as the unit of user review
**Status:** Accepted  
**Context:** The system’s deliverable is not merely changed files but reviewable GitHub artifacts with context, branch lineage, CI status, and narrative. Draft PRs provide a standard collaboration surface.  
**Decision:** Forge opens draft pull requests for each logical unit of work, including generated implementation, tests, and machine-authored summary/context needed for review. Draft status is preserved until user-controlled promotion or merge workflow criteria are met.  
**Consequences:** Review happens in a familiar collaboration environment and supports normal GitHub controls. This requires reliable GitHub auth, branch publishing, PR templating, and idempotent retry behavior.  
**Rejected alternatives:** Delivering patches only locally was rejected because it weakens collaboration and traceability. Opening ready-for-review PRs immediately was rejected because the product requires explicit human gating.

## Documentation regeneration as an optional post-build stage
**Status:** Accepted  
**Context:** The README states that after the build completes, the system may optionally regenerate documentation. Documentation changes are valuable but can also create noise if forced into every implementation step.  
**Decision:** Documentation regeneration is supported as an explicit optional workflow stage, typically after implementation sequences complete or at controlled checkpoints, rather than being mandatory in every PR.  
**Consequences:** Teams can keep docs current without inflating every PR with generated documentation churn. This requires separate triggers, scope rules, and review presentation for doc-only updates.  
**Rejected alternatives:** Always regenerating docs in every PR was rejected because it adds noise and merge friction. Never regenerating docs was rejected because it underdelivers on the product promise.

## Native macOS application distribution
**Status:** Accepted  
**Context:** The shell is explicitly a native macOS application with installation, upgrade, authentication, and UI responsibilities. Distribution must align with expected macOS user experience and trust expectations.  
**Decision:** Forge is distributed as a native `.app` bundle for macOS 13+ with standard drag-to-Applications installation semantics and integrated auto-update support via Sparkle, as specified by the shell TRD.  
**Consequences:** Users get a conventional macOS installation and update path. This constrains packaging, signing, notarization, update feed integrity, and version migration behavior.  
**Rejected alternatives:** Web-only delivery was rejected because it cannot own local repo access, Keychain, and native auth flows. CLI-only distribution was rejected because it conflicts with the native shell and UI requirements.

## SwiftUI-first shell user interface
**Status:** Accepted  
**Context:** The shell must provide a native macOS experience and coordinate complex workflow state, review status, authentication, and progress surfaces. SwiftUI is the specified UI technology in the shell TRD.  
**Decision:** The Forge shell UI is built primarily with SwiftUI, with AppKit interop used only where required for native macOS capabilities not adequately covered by SwiftUI.  
**Consequences:** UI development aligns with the specified platform stack and modern state-driven patterns. This constrains component design toward declarative state models and requires careful interoperability handling for lower-level macOS behaviors.  
**Rejected alternatives:** AppKit-first UI was rejected because it departs from the specified stack and increases implementation complexity. A webview-based interface was rejected because it weakens native integration.

## Minimum platform baseline of macOS 13 and modern language runtimes
**Status:** Accepted  
**Context:** The shell TRD establishes supported platform and language baselines. A consistent baseline is required for APIs, security controls, and packaging.  
**Decision:** Forge targets macOS 13.0 or later, with Swift 5.9+ for the shell and bundled Python 3.12 for the backend.  
**Consequences:** Engineering can rely on contemporary platform APIs and avoid excessive compatibility shims. This narrows the install base and requires version management for the bundled runtime.  
**Rejected alternatives:** Supporting older macOS releases was rejected due to increased maintenance and weaker API guarantees. Requiring a system Python was rejected because it harms reproducibility and install reliability.

## Bundled Python runtime for reproducible backend behavior
**Status:** Accepted  
**Context:** The backend is integral to product function and cannot depend on host Python configuration, package availability, or user environment quality.  
**Decision:** Forge ships with a bundled Python 3.12 runtime and controlled dependency set as part of the application distribution so the backend runs in a reproducible environment independent of user-installed interpreters.  
**Consequences:** Installation becomes more reliable and supportability improves. This increases app size and requires runtime patching, update, and code-signing considerations.  
**Rejected alternatives:** Using the system Python or Homebrew-installed Python was rejected because it creates environmental drift. Downloading the backend runtime on first launch was rejected because it weakens offline reliability and complicates trust.

## Biometric gate for session unlock
**Status:** Accepted  
**Context:** The shell owns authentication and must secure access to sensitive repository operations and stored secrets while keeping user friction manageable. macOS provides strong local authentication mechanisms suitable for session gating.  
**Decision:** Forge uses a biometric gate, when available, for unlocking or authorizing privileged sessions in the shell, with secure fallback mechanisms compliant with platform capabilities and the security TRD.  
**Consequences:** User sessions are protected by native local authentication and integrate with user expectations. This requires session timeout rules, fallback flows, and clear UX around locked/unlocked states.  
**Rejected alternatives:** No local gate was rejected because it leaves secrets and actions insufficiently protected. A custom password-only scheme was rejected because Keychain and native auth provide stronger platform alignment.

## Keychain-backed secret storage
**Status:** Accepted  
**Context:** The system handles provider API keys, GitHub credentials, and session-related material. Secret storage must use platform-native secure storage rather than application-managed files.  
**Decision:** All long-lived secrets under shell control are stored in the macOS Keychain, with access mediated by the shell and scoped to the minimum required operation.  
**Consequences:** Secret persistence uses audited OS facilities, reducing exposure and storage complexity. This constrains migration behavior, access group design, and testing strategies for credential flows.  
**Rejected alternatives:** Storing secrets in configuration files, app preferences, or backend-managed stores was rejected because it weakens security and violates shell ownership of secrets.

## Session-scoped credential brokering to the backend
**Status:** Accepted  
**Context:** The backend must call external APIs and GitHub, but direct long-lived secret access is disallowed. A secure pattern is needed for delegated operations.  
**Decision:** The shell brokers credentials to the backend only as session-scoped, least-privilege material required for specific operations. Secrets are not persisted by the backend, and credential refresh or reauthorization is mediated by the shell.  
**Consequences:** The backend can perform required work without becoming a second secret vault. This imposes token lifecycle management, secure in-memory handling, and clear expiry/error semantics.  
**Rejected alternatives:** Persisting credentials in the backend was rejected because it duplicates trust responsibilities. Requiring the user to paste credentials into the backend directly was rejected because it bypasses shell security controls.

## Security-first treatment of all external and model-generated content
**Status:** Accepted  
**Context:** Forge ingests untrusted content from repositories, TRDs, model outputs, dependency manifests, GitHub metadata, and CI logs. Prompt injection and malicious file content are realistic threats.  
**Decision:** All external content and all model-generated content are treated as untrusted input. Parsing, prompting, rendering, and action selection must follow explicit trust boundaries and sanitization/containment rules defined by the security TRD.  
**Consequences:** The platform resists prompt injection, content-based privilege escalation, and unsafe action chaining. This constrains prompt assembly, markdown rendering, logging, and any automation triggered by repository content.  
**Rejected alternatives:** Trusting repository or model content by default was rejected because it is incompatible with the threat model. Selective ad hoc sanitization was rejected because it is inconsistent and brittle.

## Human-in-the-loop as a hard control boundary
**Status:** Accepted  
**Context:** The product autonomously plans and generates changes, but it operates on valuable codebases and external services. The specification emphasizes user review and gating.  
**Decision:** Human approval is a mandatory control boundary for consequential transitions such as accepting plans, progressing PR sequences where required, and final merge/release actions. Automation prepares and proposes; the user authorizes.  
**Consequences:** Risk is reduced and accountability remains clear. This limits maximum autonomy and requires well-designed approval UX, resumable state, and unambiguous pending-action presentation.  
**Rejected alternatives:** Fully autonomous end-to-end repository modification and merge was rejected because it exceeds the intended trust model. Manual approval for every sub-step was rejected because it would destroy throughput.

## Strict subsystem ownership and contract-driven integration
**Status:** Accepted  
**Context:** The platform spans shell, backend, providers, GitHub integration, and UI surfaces. Without explicit ownership boundaries, changes would create drift and hidden coupling.  
**Decision:** Every significant subsystem has a primary owning layer and integrates through explicit contracts, schemas, and state models rather than shared implicit behavior. The TRDs define these contracts and are authoritative over implementation.  
**Consequences:** Integration remains testable and maintainable, and subsystem evolution becomes safer. This adds upfront schema/versioning work and may slow ad hoc changes.  
**Rejected alternatives:** Cross-cutting shared logic without clear ownership was rejected because it leads to boundary erosion. “Code first, document later” integration was rejected because the platform is specification-driven.

## Versioned interfaces and compatibility checks between shell and backend
**Status:** Accepted  
**Context:** The application ships two cooperating processes that may fail independently and may be upgraded together. Interface drift would break startup or corrupt workflow state.  
**Decision:** IPC schemas and capability contracts between shell and backend are explicitly versioned, with compatibility checks during session establishment and graceful failure when versions are incompatible.  
**Consequences:** Releases are safer and issues are surfaced early. This requires protocol negotiation logic, migration policy, and test coverage for mixed-version behaviors.  
**Rejected alternatives:** Assuming in-lockstep compatibility without negotiation was rejected because it makes failures opaque. Fully dynamic unversioned payloads were rejected because they are fragile.

## Durable pipeline state for resumability
**Status:** Accepted  
**Context:** Long-running planning, generation, review, and CI workflows can span process restarts, app updates, auth expiry, and network interruptions. The user experience depends on recovering state without silent duplication or loss.  
**Decision:** Forge persists durable pipeline state sufficient to resume or safely restart work units, preserving plan structure, PR sequencing, review artifacts, and external operation correlation where appropriate.  
**Consequences:** Users can recover from interruptions and the system can avoid duplicate PRs or branch corruption. This requires a defined state model, idempotency keys, migration handling, and careful storage of sensitive versus non-sensitive state.  
**Rejected alternatives:** In-memory-only workflow state was rejected because it is too fragile. Recomputing state from external systems alone was rejected because it is incomplete and error-prone.

## Structured error contracts over best-effort failure handling
**Status:** Accepted  
**Context:** Multiple providers, local process boundaries, Git operations, auth flows, and CI systems introduce diverse failure modes. The TRDs emphasize explicit interfaces and error contracts.  
**Decision:** Forge represents failures through structured, typed error contracts across subsystem boundaries, including user-actionable categories, retryability, and correlation metadata, rather than opaque strings or silent fallback.  
**Consequences:** Failures become diagnosable, testable, and presentable in the UI. This requires schema design, mapping from provider-specific errors, and discipline in propagation.  
**Rejected alternatives:** Stringly typed errors were rejected because they are not robust across boundaries. Silent retries and hidden fallback behavior were rejected because they reduce predictability and trust.

## Observability focused on pipeline state, auditability, and safety
**Status:** Accepted  
**Context:** An autonomous build agent must explain what it is doing, why it is blocked, and what artifacts it produced, without exposing secrets or unsafe content.  
**Decision:** Forge implements structured observability around pipeline state transitions, provider operations, review outcomes, GitHub actions, and security-relevant events, with redaction rules for secrets and sensitive content. User-facing status surfaces derive from this structured telemetry.  
**Consequences:** Debugging, auditability, and user trust improve. This imposes logging schemas, retention decisions, redaction controls, and test coverage for sensitive event handling.  
**Rejected alternatives:** Minimal ad hoc logs were rejected because they do not support an autonomous pipeline. Verbose raw payload logging was rejected because it risks secret leakage and unsafe content exposure.

## GitHub as the primary remote collaboration target
**Status:** Accepted  
**Context:** The product promise explicitly centers on opening GitHub pull requests and using repository CI and review workflows. The remote integration surface must therefore optimize for GitHub first.  
**Decision:** Forge treats GitHub as the primary and required remote collaboration target for pull request creation, branch publication, status observation, and review workflow integration in the initial platform scope.  
**Consequences:** The product can deeply integrate with one dominant workflow and avoid lowest-common-denominator abstractions. This constrains remote support and defers generalized VCS hosting abstractions.  
**Rejected alternatives:** Building equal first-class support for all Git hosting providers was rejected because it dilutes focus and increases complexity. Local-only Git workflows were rejected because they do not satisfy the product goal.

## PR-scoped tests generated alongside implementation
**Status:** Accepted  
**Context:** The platform promises implementation and tests for each PR. Since autonomous execution is constrained, tests must be treated as part of the generated deliverable and review artifact.  
**Decision:** Each generated pull request includes corresponding test changes where applicable, and test adequacy is evaluated during the review cycle against the TRDs and repository conventions.  
**Consequences:** Quality expectations are embedded in each unit of work rather than deferred. This can increase PR size and requires repository-aware test strategy selection.  
**Rejected alternatives:** Generating code without tests by default was rejected because it undermines confidence and contradicts the product description. Deferring all tests to a final hardening PR was rejected because it concentrates risk.

## Plan decomposition into PRD and ordered implementation units
**Status:** Accepted  
**Context:** User intent can be broad and ambiguous. To transform intent into reviewable engineering work, the platform needs intermediate planning artifacts.  
**Decision:** Forge first derives a PRD-like implementation plan from user intent and repository TRDs, then decomposes that plan into ordered, dependency-aware pull request units suitable for generation and review.  
**Consequences:** Work becomes more traceable and manageable, and users can inspect planning before code is produced. This adds planning stages and requires explicit artifact generation and revision handling.  
**Rejected alternatives:** Direct intent-to-code generation was rejected because it is too coarse and insufficiently auditable. Fully manual planning outside the tool was rejected because it weakens automation value.

## Native shell supervises backend lifecycle
**Status:** Accepted  
**Context:** The backend is subordinate to the shell in trust and application lifecycle terms. Process startup, shutdown, crashes, and updates must be controlled coherently.  
**Decision:** The Swift shell is responsible for launching, authenticating, monitoring, restarting when appropriate, and terminating the Python backend. Backend availability is reflected as explicit application state in the UI.  
**Consequences:** Lifecycle control remains centralized and consistent with OS integration. This requires health checks, crash policies, startup sequencing, and clear user feedback on degraded states.  
**Rejected alternatives:** Letting the backend daemonize independently was rejected because it complicates trust, lifecycle, and update behavior. Manual backend management by the user was rejected because it harms usability.

## Sparkle-based automatic updates for the shell distribution
**Status:** Accepted  
**Context:** The shell TRD explicitly includes Sparkle auto-update. A secure and standard update path is needed for timely fixes, especially in security-sensitive software.  
**Decision:** Forge uses Sparkle for application update distribution and installation, with signed update feeds and standard macOS update UX.  
**Consequences:** Users receive secure and familiar app updates. This requires signing discipline, update channel policy, rollback considerations, and compatibility checks with the bundled backend.  
**Rejected alternatives:** Custom updater infrastructure was rejected because it adds risk and maintenance burden. Manual update-only distribution was rejected because it slows security response and UX.

## App-level refusal to invent requirements beyond the TRDs
**Status:** Accepted  
**Context:** The repository guidance repeatedly states that implementers must not invent requirements and must consult the relevant TRDs. The same principle must govern the platform itself.  
**Decision:** When Forge encounters ambiguity, missing specifications, or conflicts between user intent and repository requirements, it must surface the gap explicitly instead of silently inferring product requirements beyond what the TRDs support.  
**Consequences:** Outputs stay closer to repository intent and are easier to trust. This may produce more clarifying prompts or blocked states when specs are incomplete.  
**Rejected alternatives:** Aggressive autonomous requirement synthesis was rejected because it creates drift. Quietly choosing plausible defaults was rejected because it reduces transparency.