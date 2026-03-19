# DECISIONS.md

## Native macOS shell with Python intelligence backend
**Status:** Accepted  
**Context:** Forge is a native macOS AI coding agent that must provide a polished desktop experience, secure local secret handling, strong OS integration, and flexible AI orchestration across model providers and GitHub workflows. A single-runtime design would force poor tradeoffs between macOS-native UX/security and rapid backend evolution.  
**Decision:** The platform is split into two processes: a native Swift/SwiftUI macOS shell and a Python backend. The Swift shell owns UI, onboarding, authentication, Keychain access, app lifecycle, settings, updates, and process supervision. The Python backend owns planning, consensus generation, review pipeline, repository operations, CI orchestration, and GitHub integration.  
**Consequences:** Clear ownership boundaries are mandatory. Cross-process APIs must be explicit and versioned. Security-sensitive capabilities remain in Swift. AI and automation logic can evolve independently in Python. Operational complexity increases because process startup, health, restart, and IPC must be managed carefully.  
**Rejected alternatives:** A pure Swift app was rejected because LLM orchestration, repository automation, and backend iteration speed are better served in Python. A pure Python desktop app was rejected because it weakens native macOS UX, security integration, and distribution. A monolithic single-process hybrid was rejected because it blurs trust boundaries and complicates isolation.

## Swift shell is the system-of-record for identity and secrets
**Status:** Accepted  
**Context:** The platform handles API credentials, GitHub authentication, user session state, and local trust decisions. TRD authority requires the strongest trust boundary around secrets and user identity.  
**Decision:** All secret storage and user authentication are owned by the Swift shell. Secrets are stored in Keychain. Biometric or equivalent platform gating is enforced by the shell. The Python backend never persists or directly manages long-lived credentials and only receives scoped material when required for an active operation.  
**Consequences:** The backend must be designed to operate with delegated, ephemeral credential access. Any feature needing credentials must flow through shell-controlled authorization. Security review is simplified because secret handling is centralized. Some backend flows are more complex due to indirection and reauthorization requirements.  
**Rejected alternatives:** Storing secrets in Python-managed config files or environment variables was rejected for weaker security. Shared credential ownership across both processes was rejected because it enlarges the attack surface and obscures accountability.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend require low-latency bidirectional communication for commands, streaming progress, state updates, and error propagation. The channel must be inspectable, simple to debug, and secured against unauthorized local access.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket and line-delimited JSON messages. Message schemas are explicit and contract-driven. The shell launches and supervises the backend and establishes the authenticated session.  
**Consequences:** The API must remain stable and schema-disciplined. Streaming is straightforward. Local transport remains fast and implementation-friendly across Swift and Python. Message framing is simple but requires careful handling of partial writes, schema evolution, and backpressure.  
**Rejected alternatives:** XPC-only integration was rejected because the backend is Python and cross-language friction is unnecessary. HTTP localhost APIs were rejected because they add unnecessary network semantics and larger exposure. Binary custom protocols were rejected because they reduce debuggability without sufficient benefit.

## No generated code is ever executed by the platform
**Status:** Accepted  
**Context:** The system generates code, tests, plans, and documentation from model outputs and repository context. Executing generated artifacts directly would create an unacceptable security boundary violation and undermine user trust.  
**Decision:** Neither the shell nor the backend executes generated code as code. The platform may write files, run repository-defined tooling, invoke CI, and prepare pull requests, but it does not interpret model output as executable instructions beyond structured pipeline data. Any command execution must come from explicit platform logic or repository tooling under controlled workflow rules.  
**Consequences:** Pipeline stages must distinguish between generated content and platform actions. Tooling integrations must be declarative and controlled. Some autonomous behaviors are intentionally limited, but the security model is substantially stronger.  
**Rejected alternatives:** Agent-directed shell execution from model text was rejected as unsafe. Sandboxed execution of arbitrary generated code was rejected because it still expands the attack surface and complicates guarantees.

## TRDs are the source of truth for implementation
**Status:** Accepted  
**Context:** Forge is fully specified through a set of Technical Requirements Documents. Multiple subsystems, agents, and contributors must align on exact contracts and behavior.  
**Decision:** The 12 TRDs in `forge-docs/` are authoritative for architecture, interfaces, state machines, security controls, testing requirements, and error contracts. Code and operational decisions must conform to the owning TRD.  
**Consequences:** Product and engineering changes must update TRDs before or alongside implementation. Local convenience must not override spec authority. Documentation discipline is required, but ambiguity and drift are reduced.  
**Rejected alternatives:** Allowing code to become the de facto spec was rejected because it encourages undocumented behavior. Lightweight README-driven requirements were rejected because they are insufficient for this system’s complexity.

## Directed build agent, not a chat product
**Status:** Accepted  
**Context:** The platform’s user promise is autonomous software delivery from specifications into reviewable GitHub pull requests. General-purpose chat metaphors would distort the interaction model and requirements.  
**Decision:** Forge is designed as a directed build agent. Users provide a repository, TRDs, and intent. The system decomposes work into plans and pull requests, generates implementation and tests, performs review and CI, and opens draft PRs for human gating. Conversational UX is secondary to task progression, artifact production, and reviewable state transitions.  
**Consequences:** Product design emphasizes pipeline visibility, approvals, plan state, diffs, CI results, and recoverability over freeform dialogue. Metrics and error handling are centered on throughput and correctness, not chat satisfaction.  
**Rejected alternatives:** A chat-first assistant was rejected because it dilutes the execution pipeline. A code-completion product was rejected because it does not satisfy the autonomous PR-based workflow.

## Consensus generation using two model providers with Claude arbitration
**Status:** Accepted  
**Context:** Single-model generation is vulnerable to provider-specific failures, blind spots, and quality variance. The product explicitly promises consensus-based implementation quality.  
**Decision:** Forge uses at least two model providers in parallel for generation, specifically Claude and GPT-4o, with Claude acting as final arbiter on outputs and reviews. The backend’s consensus engine compares, synthesizes, or selects across provider outputs according to pipeline stage rules.  
**Consequences:** Provider abstraction is required. Latency and cost increase relative to single-model generation. Quality, resilience, and adversarial disagreement detection improve. Arbitration logic becomes a critical subsystem and must be deterministic enough for auditability.  
**Rejected alternatives:** Single-provider generation was rejected for lower robustness. Equal-vote arbitration without a designated final arbiter was rejected because it leaves unresolved conflicts. Human-only arbitration at every step was rejected because it destroys autonomy.

## Work decomposition proceeds from intent to PRD plan to ordered pull requests
**Status:** Accepted  
**Context:** Large engineering intents must be transformed into manageable, reviewable units that preserve sequencing and reduce merge risk.  
**Decision:** The platform decomposes user intent into an ordered PRD-level plan and then into a sequence of pull requests, one per logical implementation unit. Each PR is independently generated, reviewed, tested, and opened as a draft for human approval before the next proceeds.  
**Consequences:** Planning quality is foundational. Dependencies between PRs must be explicit. The system can pipeline work while preserving reviewability. Some tasks may require re-planning when sequencing assumptions change.  
**Rejected alternatives:** Generating one giant branch for the full intent was rejected due to review and merge risk. Pure issue-by-issue ad hoc execution was rejected because it loses plan coherence.

## One logical unit per pull request
**Status:** Accepted  
**Context:** Review quality, merge safety, and user trust depend on PRs being scoped and understandable.  
**Decision:** Each generated PR must represent a single logical unit of work with coherent purpose, bounded diff size, associated tests, and review context. The system should split broad implementation into multiple sequential PRs rather than aggregating unrelated changes.  
**Consequences:** Planning and splitting heuristics must optimize for reviewer comprehension. Some overhead increases because more branches and PRs are created. Merge conflicts and rollback complexity are reduced.  
**Rejected alternatives:** Bundling many loosely related changes into fewer PRs was rejected because it harms reviewability. File-count-only splitting was rejected because logical coherence matters more than mechanical size.

## Human gating is mandatory before merge progression
**Status:** Accepted  
**Context:** The product is autonomous in production of code changes but must preserve user control and accountability over repository changes.  
**Decision:** Forge opens draft pull requests for human review and approval. The user gates progression by approving and merging or otherwise resolving the PR. The agent may prepare subsequent work, but repository advancement depends on human-controlled checkpoints.  
**Consequences:** Full lights-out merge autonomy is intentionally excluded. UX must make gate state explicit. The platform remains compatible with teams requiring auditable human approval. Throughput is lower than fully autonomous merge bots but trust and governance are improved.  
**Rejected alternatives:** Auto-merge on green CI was rejected because it removes necessary control. Manual patch export without PR creation was rejected because it weakens workflow integration.

## Three-pass review cycle before PR creation
**Status:** Accepted  
**Context:** Raw model output is insufficiently reliable for direct submission. The system needs internal quality control before surfacing artifacts to users.  
**Decision:** Every PR candidate goes through a multi-pass review cycle, specified as three passes, before finalization. Review includes correctness, spec compliance, test sufficiency, and likely regressions, with model-based critique and revision loop(s) prior to opening the draft PR.  
**Consequences:** Pipeline complexity and latency increase. Quality and consistency improve. Review artifacts and rationale should be observable for debugging and trust.  
**Rejected alternatives:** Single-pass generation with no structured review was rejected for quality risk. Unlimited iterative review was rejected because it harms predictability and cost control.

## CI execution is a required validation stage
**Status:** Accepted  
**Context:** Generated changes need objective validation beyond model review. Repository-defined checks are the strongest available correctness signal in the workflow.  
**Decision:** The platform executes CI or equivalent repository validation as part of PR preparation and status reporting. CI results are attached to the PR workflow and contribute to user review decisions.  
**Consequences:** Forge must integrate with repository tooling and surface failures clearly. Some repos will require environment-specific adaptation. Autonomy is bounded by available deterministic test signals.  
**Rejected alternatives:** Skipping CI and relying only on model confidence was rejected as unsafe. Replacing repository CI with Forge-specific checks only was rejected because repository truth must dominate.

## Provider access is abstracted behind explicit adapter interfaces
**Status:** Accepted  
**Context:** Multi-provider consensus requires swappable implementations, isolated provider quirks, and policy control over prompts, retries, and result normalization.  
**Decision:** Model providers are integrated through backend adapter interfaces. The consensus engine depends on normalized provider contracts rather than provider-specific APIs. Prompting, response parsing, error mapping, and retry logic are encapsulated in adapters.  
**Consequences:** Adding providers becomes tractable. Cross-provider comparison becomes possible. Adapter maintenance is required as APIs change. Lowest-common-denominator design pressure must be managed carefully.  
**Rejected alternatives:** Embedding provider-specific logic directly in the consensus engine was rejected because it creates coupling. A generic one-size-fits-all SDK abstraction was rejected if it hides necessary provider differences.

## SwiftUI-first desktop application architecture
**Status:** Accepted  
**Context:** The shell must deliver a native macOS user experience with clear state presentation, onboarding, settings, and workflow navigation.  
**Decision:** The macOS shell is implemented using Swift and SwiftUI, with module boundaries and view models defined by shell requirements. State ownership remains explicit, and concurrency follows Swift’s structured concurrency model.  
**Consequences:** The app aligns with Apple platform conventions and long-term maintainability. State modeling must be disciplined. Some lower-level AppKit interop may still be needed, but SwiftUI is the primary UI technology.  
**Rejected alternatives:** AppKit-first UI was rejected for higher complexity and slower development for the required interface. Cross-platform UI frameworks were rejected because the product is intentionally native macOS-first.

## Shell owns process lifecycle management for backend execution
**Status:** Accepted  
**Context:** The backend is a subordinate local service whose availability, restart behavior, and credential access must be managed in a user-trustworthy way.  
**Decision:** The shell launches, monitors, and restarts the Python backend. It controls startup configuration, authenticated channel establishment, health observation, and failure presentation to the user.  
**Consequences:** Backend lifecycle semantics must be explicit. Crash recovery and exponential backoff policies are needed. User-facing status must distinguish shell health from backend health.  
**Rejected alternatives:** Running the backend as an independently managed daemon was rejected because it complicates trust and lifecycle control. Letting the backend self-spawn was rejected because it inverts authority.

## Secure local session lifecycle with biometric gate
**Status:** Accepted  
**Context:** The platform exposes repository access, model credentials, and automation capabilities that should not remain continuously available without user presence and intent.  
**Decision:** The shell enforces a secure session lifecycle, including biometric or platform-equivalent re-entry gates, unlock state, timeout behavior, and controlled secret release to active operations.  
**Consequences:** Users gain stronger local access control. Some friction is added to resumed sessions and long-running workflows. The UI must communicate locked vs unlocked state clearly.  
**Rejected alternatives:** Persistent unlocked sessions were rejected as too risky. Password-only app-managed auth was rejected because native platform security is preferred.

## Keychain is the canonical persistent secret store
**Status:** Accepted  
**Context:** The shell requires durable local secret storage for provider credentials and integration tokens while maintaining OS-level security properties.  
**Decision:** Long-lived local secrets are stored in macOS Keychain, with access mediated by the shell. UserDefaults, plaintext config files, and ad hoc encrypted blobs are not used as the primary secret store.  
**Consequences:** Secret management inherits OS protections and user expectations. Development and testing require Keychain-aware workflows. Secret portability is intentionally limited.  
**Rejected alternatives:** UserDefaults was rejected as insecure for secrets. Custom encrypted files were rejected because they duplicate platform primitives and increase key management risk.

## Sparkle-based auto-update for desktop distribution
**Status:** Accepted  
**Context:** The app must support standard macOS distribution with secure and user-friendly update behavior outside the Mac App Store model.  
**Decision:** The shell uses Sparkle for auto-update within the drag-to-Applications distribution model. Update flows remain under shell ownership and align with macOS application expectations.  
**Consequences:** Release engineering must support signed updates and feed management. Update UX becomes standardized. The platform accepts Sparkle operational and security maintenance responsibilities.  
**Rejected alternatives:** Manual update-only distribution was rejected for poor maintainability and user experience. Mac App Store-only distribution was rejected due to product constraints and operational flexibility requirements.

## Structured logging and observability across both processes
**Status:** Accepted  
**Context:** The multi-stage pipeline spans two runtimes and many failure modes. Diagnosing issues requires correlated telemetry and inspectable state transitions.  
**Decision:** Both shell and backend emit structured logs and observability events with consistent correlation identifiers across process boundaries and pipeline stages. Logging must respect security policies and avoid leaking secrets or sensitive content beyond allowed boundaries.  
**Consequences:** Message IDs, run IDs, PR IDs, and stage IDs must be propagated consistently. Debugging and support improve. Telemetry schema governance is required.  
**Rejected alternatives:** Unstructured process-local logging was rejected because it impedes debugging. Verbose raw transcript logging by default was rejected due to privacy and security concerns.

## UserDefaults is used for non-secret settings and migration-managed preferences
**Status:** Accepted  
**Context:** The shell needs durable local storage for onboarding completion, non-secret preferences, and application configuration state.  
**Decision:** Non-secret settings are stored in UserDefaults under an explicit schema with migration support. Secret or security-sensitive data is excluded from UserDefaults.  
**Consequences:** Settings evolution requires schema versioning and migrations. Local state remains simple and native. Data classification between secret and non-secret fields must be maintained.  
**Rejected alternatives:** Storing all settings in custom JSON files was rejected for unnecessary complexity. Using Keychain for routine preferences was rejected because it is inappropriate for non-secret app settings.

## Explicit module boundaries in the Swift shell
**Status:** Accepted  
**Context:** The shell covers UI, authentication, process supervision, settings, and IPC. Without disciplined boundaries, the app would quickly become tightly coupled and difficult to audit.  
**Decision:** The Swift codebase is organized into explicit modules or responsibility boundaries for UI, auth, secret handling, settings, process management, IPC, and observability. Ownership of state and side effects is localized to the responsible subsystem.  
**Consequences:** Architectural consistency improves and testing is easier. Cross-cutting features require intentional interfaces. Some duplication may be preferable to hidden coupling.  
**Rejected alternatives:** A flat application module with broad shared state was rejected because it impedes maintainability and security review.

## Structured concurrency is the concurrency model in Swift components
**Status:** Accepted  
**Context:** The shell performs asynchronous UI updates, IPC communication, process management, and secure operations. Concurrency correctness is critical for UX and security.  
**Decision:** Swift structured concurrency is the primary concurrency model for shell components. State mutations must respect actor isolation or equivalent ownership rules defined by shell architecture.  
**Consequences:** Async flows are easier to reason about and cancellation semantics are clearer. Legacy callback patterns should be minimized. Care is required when bridging to lower-level APIs.  
**Rejected alternatives:** Ad hoc GCD-heavy concurrency was rejected due to maintainability and correctness risks. Shared mutable state without isolation was rejected outright.

## Backend is responsible for planning, generation, review, and GitHub operations
**Status:** Accepted  
**Context:** The automation pipeline’s core intelligence requires cohesive ownership to avoid fragmented orchestration logic.  
**Decision:** The Python backend owns plan creation, task decomposition, provider invocation, consensus arbitration, review loops, file generation, branch and PR orchestration, and GitHub interaction. The shell requests operations and renders state but does not implement pipeline intelligence.  
**Consequences:** Backend APIs must expose enough state for rich UI. Shell/backend responsibility remains crisp. Backend correctness becomes central to overall platform reliability.  
**Rejected alternatives:** Splitting orchestration logic between shell and backend was rejected because it creates duplication and ambiguous control flow.

## GitHub is the primary VCS collaboration surface
**Status:** Accepted  
**Context:** The product promise is explicit about opening pull requests and integrating with standard code review workflows.  
**Decision:** Forge targets GitHub as the primary repository hosting and collaboration platform for branch management, draft PR creation, status updates, and review workflow integration.  
**Consequences:** Initial platform fit is strongest for GitHub-hosted repositories. Domain models may reflect GitHub concepts such as draft PRs and checks. Future SCM support requires adapterization.  
**Rejected alternatives:** Building abstraction for all VCS hosts from day one was rejected as premature. Patch-file-only workflows were rejected because they weaken the core review loop.

## Documentation regeneration is an optional downstream workflow
**Status:** Accepted  
**Context:** The product may update documentation as implementation evolves, but documentation generation should not block the main code-delivery loop by default.  
**Decision:** After build completion, the platform may optionally regenerate project documentation as a separate workflow stage or follow-up action. This is not the primary success criterion for implementation PRs unless explicitly required by the repository or intent.  
**Consequences:** Documentation remains supported without overloading every PR. Teams can opt in based on repo policy. Documentation drift is reduced when enabled, but not guaranteed otherwise.  
**Rejected alternatives:** Always regenerating documentation was rejected due to unnecessary cost and noise. Never supporting documentation updates was rejected because it misses a valuable automation opportunity.

## Error contracts and interfaces are treated as first-class design artifacts
**Status:** Accepted  
**Context:** This platform crosses process, language, provider, and network boundaries. Ambiguous errors would make failure recovery and user trust poor.  
**Decision:** Every subsystem follows explicit interface and error contracts from the TRDs. Errors are categorized, propagated across IPC in structured form, and rendered in user-meaningful language while preserving diagnostic detail for logs.  
**Consequences:** Schema design and versioning matter. Engineering effort increases up front, but supportability and recoverability improve substantially.  
**Rejected alternatives:** Freeform exception propagation was rejected because it fails across boundaries. Generic “something went wrong” UX without structured diagnostics was rejected because it is not operable.

## Security controls in TRD-11 apply platform-wide
**Status:** Accepted  
**Context:** Security-relevant behavior exists across credentials, generated content, external content ingestion, CI, and repository mutation. A fragmented security model would create gaps.  
**Decision:** TRD-11 governs all components and overrides local convenience decisions in any subsystem involving secrets, credentials, generated code, external content, CI, or repository operations. Security review must reference TRD-11 for any relevant change.  
**Consequences:** Security is centralized as policy, not left to subsystem interpretation. Contributors must explicitly check TRD-11 when modifying sensitive paths. Some implementation choices are constrained, intentionally.  
**Rejected alternatives:** Per-team or per-module security conventions were rejected because they create inconsistency. Best-effort security interpretation was rejected as insufficient.

## Repository-defined tooling is the only execution authority for validation steps
**Status:** Accepted  
**Context:** The platform must validate generated changes while preserving the no-generated-code-execution rule and respecting project-specific workflows.  
**Decision:** Validation steps execute through explicit platform-controlled invocation of repository-defined tooling and CI configuration. The agent does not create ad hoc executable workflows from model output.  
**Consequences:** Repositories need a reasonably deterministic toolchain to benefit fully. The platform can support many stacks without interpreting arbitrary generated commands.  
**Rejected alternatives:** Letting models synthesize and execute arbitrary local commands was rejected as unsafe. Building a Forge-proprietary test runner model was rejected because repository truth should dominate.

## Schema-disciplined state propagation between backend and UI
**Status:** Accepted  
**Context:** Users need visibility into planning, generation, review, CI, and PR state. Inconsistent or implicit state transfer would make the UI unreliable.  
**Decision:** Backend-to-shell communication uses explicit message schemas for commands, progress events, state snapshots, and terminal outcomes. The UI renders backend state rather than inferring hidden workflow state locally.  
**Consequences:** API design and evolution need care. Time-travel debugging and replay become more feasible. Frontend implementation is simpler because state authority is clearer.  
**Rejected alternatives:** UI-side reconstruction of backend progress from logs was rejected as brittle. Implicit state transfer through loosely structured text was rejected because it is not robust.

## The platform optimizes for reviewability over maximal autonomy
**Status:** Accepted  
**Context:** Users must trust autonomous code production in real repositories. Trust is earned through understandable changes and clear decision points, not by eliminating humans entirely.  
**Decision:** Across planning, PR scoping, review cycles, CI, and draft PR gating, Forge is designed to maximize artifact clarity and human reviewability rather than pursue end-to-end unsupervised autonomy.  
**Consequences:** Some tasks take longer and require human checkpoints. Adoption barriers for serious engineering teams are lower. Product direction remains aligned with governed automation.  
**Rejected alternatives:** Aggressive autonomous repo mutation with minimal review was rejected due to governance, security, and trust concerns.