# DECISIONS.md

## Two-process native architecture
**Status:** Accepted  
**Context:** Forge is a native macOS AI coding agent with strong separation between user-trust concerns and model-driven generation. The platform must provide a native UX, own authentication and secrets locally, and isolate intelligence and repository mutation logic from the UI container.  
**Decision:** Forge is built as a two-process system: a Swift/SwiftUI macOS shell and a Python backend. The Swift shell owns UI, authentication, Keychain access, app lifecycle, updates, and local orchestration. The Python backend owns planning, consensus generation, review pipeline, documentation regeneration, CI coordination, and GitHub operations.  
**Consequences:** Security boundaries are explicit. Secret ownership remains in the shell. Backend evolution is faster due to Python flexibility. Inter-process communication becomes a first-class contract that must be authenticated, versioned, and failure-tolerant.  
**Rejected alternatives:**  
- **Single-process app:** Rejected because it weakens isolation between secrets/UI and model-driven code generation.  
- **All-backend web app:** Rejected because the product requires native macOS trust surfaces, local secrets, and desktop workflow integration.  
- **All-Swift implementation:** Rejected because backend orchestration and provider integrations are better suited to Python iteration speed and ecosystem support.

## Swift shell owns trust-sensitive responsibilities
**Status:** Accepted  
**Context:** The platform handles authentication state, API credentials, local repository access, and user approvals. These functions require the highest-trust execution environment and alignment with macOS security primitives.  
**Decision:** The Swift shell is the sole owner of biometric gating, Keychain storage, session unlock state, native UI, app distribution concerns, and secure initiation of backend work. Secrets are never persisted by the Python backend.  
**Consequences:** Security-critical logic is centralized in one trusted boundary. Backend services must request capabilities through explicit shell-mediated interfaces. Some implementation complexity shifts into IPC and token-passing.  
**Rejected alternatives:**  
- **Backend direct secret access:** Rejected because it expands the attack surface and violates the platform trust model.  
- **Environment-variable secret injection as primary model:** Rejected because it is harder to audit and easier to leak.

## Python backend owns intelligence and repository automation
**Status:** Accepted  
**Context:** Forge’s core value is autonomous planning, code generation, review, CI handling, and GitHub PR production. These capabilities require rapid iteration across provider APIs, workflow orchestration, and content processing.  
**Decision:** The Python backend exclusively owns the consensus engine, provider adapters, planning pipeline, PR generation, review passes, CI interpretation, documentation regeneration, and GitHub interactions.  
**Consequences:** Backend behavior can evolve without destabilizing the shell. Repository mutation logic is isolated from user trust surfaces. The shell remains a container and controller rather than an intelligence runtime.  
**Rejected alternatives:**  
- **Split intelligence across shell and backend:** Rejected because it complicates state ownership and observability.  
- **GitHub operations from the shell:** Rejected because repository automation belongs with planning and execution logic.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two processes require a local communication protocol that is inspectable, debuggable, low-latency, and suitable for structured request/response and event streaming.  
**Decision:** The shell and backend communicate over an authenticated local Unix domain socket using line-delimited JSON messages. The protocol is explicit, machine-readable, and stable across subsystem evolution.  
**Consequences:** IPC is easy to test and observe. Messages can be streamed incrementally. Strict schema validation and framing are required. Authentication and message origin controls are mandatory.  
**Rejected alternatives:**  
- **XPC-only architecture:** Rejected as a sole mechanism because the backend is Python and portability of the backend process contract is simpler with socket JSON.  
- **HTTP localhost server:** Rejected because it introduces unnecessary networking semantics and larger attack surface.  
- **Binary custom protocol:** Rejected because it reduces debuggability without meaningful product benefit.

## Never execute generated code
**Status:** Accepted  
**Context:** Forge produces and modifies source code from model outputs. Executing generated code would create a major safety and supply-chain risk.  
**Decision:** Neither the shell nor the backend may execute generated application code. Forge may run controlled repository tooling and CI-defined commands only within the platform’s approved pipeline boundaries, but generated code itself is not directly executed as an agent action.  
**Consequences:** Safety posture is stronger and easier to reason about. Validation relies on static analysis, tests, diffs, and CI rather than autonomous runtime execution of generated artifacts. Some classes of dynamic verification are intentionally out of scope.  
**Rejected alternatives:**  
- **Sandboxed execution of generated code:** Rejected because it still increases complexity and risk materially.  
- **Autonomous local run-and-fix loops:** Rejected because they normalize unsafe execution behavior.

## TRDs are the source of truth
**Status:** Accepted  
**Context:** The product spans UI, backend orchestration, GitHub automation, consensus generation, security, and testing. Informal requirements would lead to drift and unsafe implementation.  
**Decision:** The 12 technical requirements documents in `forge-docs/` are the authoritative product specification. Implementation, tests, interfaces, and error contracts must conform to the owning TRD.  
**Consequences:** Design changes require spec updates or explicit divergence decisions. Teams and agents must read the relevant TRD before modifying code. Architectural consistency improves at the cost of heavier upfront discipline.  
**Rejected alternatives:**  
- **Code-as-spec only:** Rejected because cross-subsystem contracts and security controls need explicit written authority.  
- **Wiki-style informal documentation:** Rejected because it is too easy to drift and too weak for enforcement.

## Security controls are centralized under the security TRD
**Status:** Accepted  
**Context:** Credentials, external content ingestion, generated artifacts, GitHub operations, and CI interactions all carry elevated risk and must follow one coherent security model.  
**Decision:** All security-relevant design and implementation decisions are governed by the platform security requirements, with security review required whenever a change touches credentials, external content, generated code, CI, or trust boundaries.  
**Consequences:** Security reasoning stays uniform across subsystems. Teams must consult the security specification before changing sensitive code paths. Delivery speed may be slower for security-touching work, but risk is lower.  
**Rejected alternatives:**  
- **Per-team ad hoc security decisions:** Rejected because it leads to inconsistent controls and weak auditing.  
- **Backend-only security ownership:** Rejected because shell trust surfaces are equally critical.

## Native macOS shell, not a web wrapper
**Status:** Accepted  
**Context:** The product must feel like a trusted desktop tool, integrate with biometrics and Keychain, and support local repository workflows naturally on macOS.  
**Decision:** Forge is implemented as a native macOS application using Swift 5.9+ and SwiftUI, targeting macOS 13.0 or later. The shell is the primary user-facing application container.  
**Consequences:** UX aligns with macOS conventions and security features. Platform scope is intentionally narrowed. Cross-platform delivery is deferred.  
**Rejected alternatives:**  
- **Electron or web wrapper:** Rejected because it weakens native trust integration and increases runtime overhead.  
- **Cross-platform first strategy:** Rejected because it dilutes the macOS-specific product requirements.

## Bundled Python runtime for backend consistency
**Status:** Accepted  
**Context:** The backend depends on Python 3.12 behavior and predictable local execution. Requiring users to manage their own interpreter would create support and reproducibility issues.  
**Decision:** Forge ships with a bundled Python 3.12 runtime used by the backend. The shell is responsible for packaging and launching the backend with the supported runtime.  
**Consequences:** Backend behavior is reproducible across installations. Packaging and update complexity increase. Dependency and notarization workflows must account for the embedded runtime.  
**Rejected alternatives:**  
- **Use system Python:** Rejected because versions and availability are not reliable on target machines.  
- **Ask users to install Python manually:** Rejected because it harms onboarding and supportability.

## Drag-to-Applications distribution with auto-update
**Status:** Accepted  
**Context:** The shell is a consumer-grade native macOS app and must support straightforward installation and lifecycle management.  
**Decision:** Forge is distributed as a standard `.app` bundle with drag-to-Applications installation and uses Sparkle for auto-update.  
**Consequences:** Installation is simple and familiar for macOS users. Release engineering must support signed and updateable app artifacts. Update trust and signing become operationally critical.  
**Rejected alternatives:**  
- **Command-line installation only:** Rejected because it does not match the product’s desktop UX goals.  
- **Custom updater:** Rejected because Sparkle is a mature solution with established macOS patterns.

## Biometric gate for protected session unlock
**Status:** Accepted  
**Context:** The application handles high-value capabilities such as credential-backed GitHub operations and repository mutation. Access should be protected by native user presence verification.  
**Decision:** Forge uses a biometric gate for unlocking protected application sessions where supported by macOS, with session lifecycle managed by the shell.  
**Consequences:** Trust in local user actions is improved. Session state becomes part of the shell’s core state machine. Fallback and failure states must be handled explicitly.  
**Rejected alternatives:**  
- **Always-unlocked local session:** Rejected because it provides inadequate protection for sensitive operations.  
- **Application-specific password only:** Rejected because native biometric flows provide better UX and stronger platform integration.

## Keychain is the only persistent secret store
**Status:** Accepted  
**Context:** The platform stores provider credentials and other sensitive material needed for automation. Secret persistence must align with platform security primitives.  
**Decision:** Persistent secrets are stored only in the macOS Keychain under shell control. Secrets are not stored in plaintext files, app preferences, repository config, or backend-managed stores.  
**Consequences:** Secret handling is auditable and aligned with user expectations on macOS. The backend must operate via delegated access rather than direct storage. Recovery and migration logic must work with Keychain constraints.  
**Rejected alternatives:**  
- **Dotfile or JSON config storage:** Rejected because it is insecure for persistent secrets.  
- **Backend-owned encrypted file store:** Rejected because secret governance belongs to the shell and Keychain already solves the platform problem.

## UI built in SwiftUI with subsystem-specific ownership
**Status:** Accepted  
**Context:** The shell requires a coherent native UI that can represent pipeline progress, review states, authentication state, and generated outputs.  
**Decision:** The user interface is implemented in SwiftUI, with shell-owned presentation of cards, panels, workflow status, approvals, and system state while backend logic remains headless.  
**Consequences:** UI development follows Apple-native patterns. Backend remains decoupled from presentation concerns. Some advanced UI state mapping is required to translate backend events into user-friendly views.  
**Rejected alternatives:**  
- **Backend-rendered UI content:** Rejected because presentation belongs to the shell.  
- **AppKit-first architecture:** Rejected because SwiftUI is the specified primary framework and better fits the target UX model.

## Directed build agent, not a chat product
**Status:** Accepted  
**Context:** The platform is designed to autonomously build software from specifications and user intent, not to serve as a general conversational assistant.  
**Decision:** Forge’s primary operating model is directed execution: ingest specs, accept intent, derive a plan, generate implementation PRs, run review and CI, and present outputs for user gating. Chat is not the primary interaction paradigm.  
**Consequences:** Product design centers on workflows, artifacts, and approvals instead of freeform conversation. Scope stays aligned to software delivery outcomes. General assistant features are deprioritized.  
**Rejected alternatives:**  
- **Chat-first copilot interface:** Rejected because it does not match the intended autonomous build workflow.  
- **Inline autocomplete product:** Rejected because it solves a different problem.

## Specification-driven planning before implementation
**Status:** Accepted  
**Context:** User intent alone is too ambiguous for safe autonomous implementation across a full repository. The system needs an explicit planning stage grounded in technical documents.  
**Decision:** Forge first loads repository specifications and user intent, produces an ordered plan, and decomposes work into logical units before code generation begins.  
**Consequences:** Output quality and coherence improve. Planning becomes a mandatory stage that may block generation when inputs are insufficient. Users must provide or confirm enough specification context.  
**Rejected alternatives:**  
- **Immediate code generation from prompt only:** Rejected because it is too error-prone and weakly grounded.  
- **Single monolithic implementation pass:** Rejected because it reduces reviewability and control.

## Work is decomposed into sequential pull requests
**Status:** Accepted  
**Context:** Large autonomous changes are hard to review, risky to merge, and difficult to recover from when CI fails.  
**Decision:** Forge decomposes planned work into a sequence of pull requests, one per logical unit, and advances to the next PR only after the previous unit reaches the required gate.  
**Consequences:** Review is tractable and failures are isolated. Throughput is balanced against control. Planning must produce coherent dependency ordering across PR units.  
**Rejected alternatives:**  
- **Single giant branch for all changes:** Rejected because it creates review and merge risk.  
- **Unbounded parallel PR generation:** Rejected because dependency conflicts and user review burden increase substantially.

## Draft PRs are the main handoff artifact
**Status:** Accepted  
**Context:** The user needs a durable, inspectable artifact for reviewing generated work inside standard engineering workflows.  
**Decision:** Forge opens draft GitHub pull requests as the primary output of each completed logical unit. User review, approval, and merge occur in GitHub-centered workflows.  
**Consequences:** The system fits existing team practices and audit trails. GitHub integration is a core dependency. Non-PR delivery modes are secondary or unsupported.  
**Rejected alternatives:**  
- **Local patch files as primary output:** Rejected because they are weaker for collaboration and auditability.  
- **Direct push to protected branches:** Rejected because it bypasses human review and standard controls.

## Two-model generation with consensus
**Status:** Accepted  
**Context:** Single-model output quality can be inconsistent, especially for nontrivial repository changes. The product explicitly aims to improve reliability through model diversity and arbitration.  
**Decision:** For implementation generation, Forge uses two LLM providers in parallel and evaluates their outputs through a consensus process rather than trusting either provider alone.  
**Consequences:** Reliability and comparative signal improve. Cost, latency, and orchestration complexity increase. Provider abstraction and normalized evaluation become mandatory backend capabilities.  
**Rejected alternatives:**  
- **Single-model generation:** Rejected because it offers weaker fault detection and lower confidence.  
- **N-model voting across many providers:** Rejected because complexity and cost outweigh current product needs.

## Claude arbitrates final outcomes
**Status:** Accepted  
**Context:** The product specification defines an asymmetric consensus process rather than simple majority or random tie-breaking.  
**Decision:** Forge uses Claude as the arbitrating model for final consensus decisions and result selection across competing generated outputs.  
**Consequences:** Arbitration behavior is consistent and predictable. Provider independence is reduced at the final decision layer. Arbitration prompts and contracts become especially important.  
**Rejected alternatives:**  
- **Symmetric voting with no arbiter:** Rejected because two-model disagreement needs a deterministic resolution path.  
- **Human arbitration for every disagreement:** Rejected because it would undermine autonomy and throughput.  
- **GPT-4o as arbiter:** Rejected because the product specification explicitly assigns arbitration to Claude.

## Provider integrations are abstracted behind adapters
**Status:** Accepted  
**Context:** Forge depends on multiple model providers and must normalize request/response behavior, errors, and capability differences.  
**Decision:** All model providers are integrated through adapter interfaces owned by the backend. The consensus engine consumes normalized provider abstractions rather than provider-specific code paths.  
**Consequences:** Providers can evolve independently and be swapped with less disruption. Adapter contracts must capture retries, errors, token usage, and output normalization.  
**Rejected alternatives:**  
- **Provider-specific calls throughout backend code:** Rejected because it creates brittle coupling and duplicate logic.  
- **Single generic SDK without explicit adapters:** Rejected because provider-specific behavior still needs disciplined normalization.

## Mandatory multi-pass review cycle before PR publication
**Status:** Accepted  
**Context:** Raw model output is not reliable enough to publish directly as a pull request candidate. The platform’s value includes structured self-review before user review.  
**Decision:** Every PR unit passes through a three-pass review cycle before final publication. Review is a first-class pipeline stage, not an optional enhancement.  
**Consequences:** Quality and consistency improve. Latency and token cost increase. Pipeline state management must represent pass-level outcomes and retry conditions.  
**Rejected alternatives:**  
- **Single review pass:** Rejected because it provides weaker defect detection.  
- **No automated review stage:** Rejected because it undermines the product’s quality claims.

## CI is a required gate in the PR pipeline
**Status:** Accepted  
**Context:** Generated changes must be validated by the repository’s own automated checks before being presented as ready for human consideration.  
**Decision:** Forge runs and interprets CI as a required gating stage for PR units. CI outcomes influence revision, retry, or publication decisions.  
**Consequences:** The system aligns with repository-defined quality bars. CI integration and log interpretation become core features. Pipeline throughput depends on external CI latency.  
**Rejected alternatives:**  
- **Open PR before CI:** Rejected because it shifts too much validation burden to humans.  
- **Ignore repository CI and rely on model review only:** Rejected because tests and build checks are necessary ground truth.

## User approval gates advancement to the next PR
**Status:** Accepted  
**Context:** The system is autonomous but not fully self-authorizing. Human oversight is required before compounding repository changes across a sequence of PRs.  
**Decision:** Forge waits for user approval of the current PR outcome before building the next PR in the sequence.  
**Consequences:** Human review remains in control of repository evolution. End-to-end delivery may take longer, but risk is reduced and trust is improved.  
**Rejected alternatives:**  
- **Fully autonomous chained PR creation and merge:** Rejected because it removes necessary oversight.  
- **Generate all PRs upfront regardless of approval:** Rejected because later work may depend on user feedback from earlier units.

## Documentation regeneration is an optional end-of-build phase
**Status:** Accepted  
**Context:** Completed implementation may require synchronized documentation updates, but not every workflow should incur that cost automatically.  
**Decision:** Forge may optionally regenerate project documentation after build completion as a distinct pipeline phase rather than an unconditional step on every PR unit.  
**Consequences:** Documentation can stay aligned without forcing unnecessary work into every change. The option must be explicit and bounded.  
**Rejected alternatives:**  
- **Always regenerate docs for every PR:** Rejected because it adds noise and cost.  
- **Never automate documentation updates:** Rejected because the platform explicitly supports documentation regeneration when useful.

## Strict ownership boundaries between UI state and execution state
**Status:** Accepted  
**Context:** The shell presents workflow progress while the backend executes complex, stateful pipelines. Confusion over state ownership would create race conditions and inconsistent UX.  
**Decision:** Execution truth lives in the backend, while the shell maintains presentation state derived from authenticated backend events and local session/auth state.  
**Consequences:** Backend remains the source of truth for pipeline progress. The shell must translate event streams into resilient UI models. Synchronization and reconnection behavior must be defined carefully.  
**Rejected alternatives:**  
- **Duplicate mutable pipeline state in both processes:** Rejected because divergence risk is high.  
- **Backend-driven UI rendering:** Rejected because it blurs process responsibilities.

## Error contracts are explicit across subsystem boundaries
**Status:** Accepted  
**Context:** Forge has multiple boundaries: shell/backend IPC, provider adapters, GitHub operations, CI integrations, and planning/review stages. Silent or ad hoc failures would be hard to recover from safely.  
**Decision:** Each subsystem exposes explicit error contracts, and cross-boundary failures must be communicated in structured form rather than implicit logs or generic exceptions only.  
**Consequences:** Recovery behavior is more deterministic and testable. Interface design effort increases. Logging and telemetry can be correlated with user-visible states more effectively.  
**Rejected alternatives:**  
- **Best-effort unstructured error handling:** Rejected because it weakens observability and resilience.  
- **Generic catch-all error payloads only:** Rejected because actionable recovery requires typed failure modes.

## Test-first validation against TRD-defined contracts
**Status:** Accepted  
**Context:** The repository instructions require reading the owning TRD and running the test suite before changes. The platform depends on contract fidelity across many subsystems.  
**Decision:** Changes are validated against tests aligned to TRD-defined interfaces, error contracts, and security requirements. Existing tests must be run before modification, and new behavior must be covered at the owning boundary.  
**Consequences:** Regression risk is reduced and architectural drift is easier to detect. Test maintenance cost increases, but correctness and confidence improve.  
**Rejected alternatives:**  
- **Implementation-driven testing only:** Rejected because it allows drift from the specification.  
- **Manual validation for agent changes:** Rejected because it is insufficient for a multi-subsystem autonomous platform.