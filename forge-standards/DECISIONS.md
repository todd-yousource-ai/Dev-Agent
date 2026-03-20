# DECISIONS.md

## Native macOS shell with bundled Python backend
**Status:** Accepted  
**Context:** The platform is specified as a native macOS product, not a web app or editor plugin. It must provide a desktop UI, local secret handling, repository access, autonomous orchestration, and local execution of controlled workflows while preserving strong separation between trusted platform code and model-driven logic.  
**Decision:** Forge is implemented as a two-process desktop system: a native Swift/SwiftUI macOS shell and a bundled Python 3.12 backend. The Swift shell owns UI, application lifecycle, auth, Keychain, local permissions, update flow, and trusted orchestration boundaries. The Python backend owns planning, consensus generation, review pipeline, documentation handling, and GitHub/repository automation.  
**Consequences:** Clear trust boundaries are established. UI and secrets remain in the native process. Intelligence and pipeline logic can evolve faster in Python. Packaging, IPC, lifecycle, and compatibility management become first-class concerns. The product is constrained to macOS 13+ and native distribution.  
**Rejected alternatives:**  
- Single-process Swift-only app — rejected because model/pipeline logic and ecosystem integrations are faster to develop and maintain in Python.  
- Electron or web-based shell — rejected because native macOS integration, Keychain access, local trust boundaries, and system UX are core requirements.  
- Remote SaaS orchestration — rejected because the platform is designed for local repository control and local secret custody.

## Authenticated local IPC over Unix domain socket with line-delimited JSON
**Status:** Accepted  
**Context:** The shell and backend must communicate across a process boundary with a protocol that is observable, debuggable, structured, and secure against unintended local access.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket and line-delimited JSON messages. The shell is the authority for process launch and session establishment. Message contracts are explicit and versioned by implementation control rather than ad hoc serialization.  
**Consequences:** Communication is simple to inspect and test. Process isolation is preserved without requiring network exposure. Both sides must implement robust framing, validation, timeout, and error handling. Protocol changes require coordinated updates.  
**Rejected alternatives:**  
- XPC for all communication — rejected because the Python backend is a first-class process and JSON IPC is more portable and easier to debug across language boundaries.  
- HTTP on localhost — rejected because it expands attack surface and introduces unnecessary server semantics.  
- STDIN/STDOUT pipes — rejected because socket lifecycle, authentication, and bidirectional structured exchange are cleaner for long-running sessions.

## Swift shell owns secrets, identity, and security-sensitive OS integrations
**Status:** Accepted  
**Context:** The system handles provider credentials, GitHub tokens, biometric access, local repository access, and privileged operating-system integrations. These functions require a strongly trusted boundary.  
**Decision:** All secrets, credential storage, biometric gates, session unlock behavior, and sensitive OS integration points are owned by the Swift shell. Secrets are stored in Keychain and not delegated to the Python backend except as narrowly scoped runtime access required by defined interfaces.  
**Consequences:** The backend cannot become the system of record for credentials. Security review is concentrated in the shell. Backend features must be designed around least-privilege access patterns. Some integration work is more complex because data must cross an explicit trust boundary only when necessary.  
**Rejected alternatives:**  
- Letting Python manage secrets directly — rejected due to weaker platform-native secret handling and larger trusted surface.  
- Environment-variable credential model — rejected because it is brittle, leaks easily, and does not meet the platform security posture.  
- Browser/session-only auth without local secure storage — rejected because the product requires persistent, local, user-controlled credentials.

## Backend owns intelligence, generation, and repository automation
**Status:** Accepted  
**Context:** The platform’s differentiator is autonomous planning, multi-model generation, review, and pull-request production. These capabilities require rapid iteration, rich library support, and isolation from UI concerns.  
**Decision:** The Python backend owns decomposition, consensus orchestration, prompt pipelines, review passes, CI coordination logic, documentation regeneration logic, and GitHub operations. The shell invokes capabilities and renders state but does not implement core intelligence logic.  
**Consequences:** Core agent behavior can evolve without UI redesign. Pipeline testing can be concentrated in Python. The shell remains a thin trusted controller rather than an AI runtime. Interface discipline is required to prevent leakage of business logic into Swift.  
**Rejected alternatives:**  
- Splitting planning across shell and backend — rejected because it creates duplicated state and unclear authority.  
- Keeping GitHub logic in Swift — rejected because repository automation belongs with generation and review workflow ownership.  
- Moving all intelligence to remote services — rejected because the product is specified as a local application with local orchestration boundaries.

## Consensus generation uses multiple model providers with deterministic orchestration
**Status:** Accepted  
**Context:** The platform is explicitly built around a consensus development model rather than a single-provider coding agent. Quality and robustness depend on obtaining multiple candidate outputs and adjudicating among them.  
**Decision:** Forge uses a multi-provider consensus engine. Distinct providers generate outputs in parallel, and arbitration is performed through a defined orchestration flow rather than informal fallback. Provider adapters implement a common contract so models are interchangeable at the integration layer.  
**Consequences:** The system gains resilience to provider variance and improved output quality at the cost of higher latency, higher token spend, and more complex orchestration. Adapter boundaries become critical. Testing must include disagreement and partial-failure scenarios.  
**Rejected alternatives:**  
- Single best model strategy — rejected because the product’s core value proposition is consensus-based development.  
- Manual user choice of model per step — rejected because the platform is intended to be autonomous and directed, not an interactive prompt workbench.  
- Hard-coded provider-specific logic throughout pipeline — rejected because it would make evolution and substitution costly.

## Claude acts as the final arbiter in consensus and review flows
**Status:** Accepted  
**Context:** The product definition specifies a two-model workflow where outputs are compared and one model is used as the final arbiter. A stable arbitration policy is required to make behavior predictable.  
**Decision:** Claude is the final arbiter for consensus resolution and review outcomes where arbitration is required by the pipeline design. Other providers participate as peers in generation, but final selection and adjudication are routed through the arbitration role.  
**Consequences:** The platform behavior is consistent with the product promise and easier to reason about operationally. Arbitration quality depends on Claude availability and output quality. Arbitration failure modes require explicit handling so the pipeline can stop safely or degrade predictably.  
**Rejected alternatives:**  
- Dynamic arbiter selection — rejected because it reduces predictability and complicates validation.  
- Human-required arbitration for every disagreement — rejected because it undermines autonomous throughput.  
- Simple majority vote without designated arbiter — rejected because two-provider workflows need a deterministic tie-breaking mechanism.

## Intent-to-PRD-to-PR pipeline is the core execution model
**Status:** Accepted  
**Context:** The platform is not a chat assistant. It is a directed build system that turns user intent and technical specifications into sequenced implementation work. The workflow must be structured enough to support autonomy, review, and traceability.  
**Decision:** User input is transformed into an ordered PRD plan, and each PRD is decomposed into a sequence of pull requests. Each PR is an independently reviewable unit that flows through generation, review, CI, and draft PR creation before the next PR proceeds.  
**Consequences:** Work is incremental, inspectable, and resumable. The system must maintain plan state and PR sequencing. Throughput is bounded by the granularity of PR decomposition and review gates. The platform is not optimized for free-form conversational exploration.  
**Rejected alternatives:**  
- Generating one giant branch for the entire intent — rejected because it harms reviewability, rollback, and CI isolation.  
- Pure chat-loop tasking — rejected because it does not provide the directed autonomy required by the product.  
- Direct file-edit mode without PR planning — rejected because it weakens traceability and governance.

## One pull request per logical unit of change
**Status:** Accepted  
**Context:** The product promise emphasizes reviewable, sequenced development. PR size strongly affects CI signal, human review burden, and rollback safety.  
**Decision:** Forge creates one pull request per logical unit of change, with decomposition designed to preserve coherent review scope and dependency order.  
**Consequences:** PRs remain comprehensible and easier to validate. The system must invest in decomposition quality and dependency management. Some intents will require many PRs, increasing orchestration overhead.  
**Rejected alternatives:**  
- Batch many unrelated changes into a single PR — rejected because it degrades review quality and recovery.  
- One file per PR — rejected because it creates excessive operational noise and loses semantic grouping.  
- User-manual PR splitting — rejected because the platform is intended to perform this planning autonomously.

## Three-pass review cycle before CI and PR creation
**Status:** Accepted  
**Context:** Generated code quality cannot rely on first-pass synthesis alone. The platform requires internal validation before exposing changes as candidate work.  
**Decision:** Every PR candidate goes through a defined three-pass review cycle prior to final CI evaluation and draft pull request creation. Review is a required stage of the pipeline, not an optional enhancement.  
**Consequences:** Quality improves and obvious defects are filtered earlier. Latency and token cost increase. Review artifacts and outcomes must be modeled in state and logs. Pipelines must halt safely when review does not converge.  
**Rejected alternatives:**  
- Single-pass generation only — rejected because it does not meet the quality bar for autonomous PR production.  
- Unlimited iterative review loop — rejected because it risks non-termination and unpredictable costs.  
- Human-only review before CI — rejected because it shifts too much validation burden to users.

## CI is mandatory before opening a draft pull request
**Status:** Accepted  
**Context:** Autonomous code generation must be bounded by executable validation. Opening PRs without CI would overload users with low-signal output and weaken trust in the agent.  
**Decision:** Forge runs the defined CI workflow for each candidate PR and only opens a draft PR after required checks pass according to repository and pipeline policy.  
**Consequences:** Users receive higher-signal PRs. Build time increases and CI integration becomes a required subsystem. Repositories without stable tests or build scripts may need onboarding remediation before the platform performs well.  
**Rejected alternatives:**  
- Open PRs before CI and let users inspect failures — rejected because it lowers trust and review efficiency.  
- Skip CI for documentation or “small” changes — rejected because exceptions are brittle and misclassification risk is high.  
- Execute arbitrary generated code outside controlled CI/test flows — rejected by the security model.

## Generated code is never executed arbitrarily by the agent
**Status:** Accepted  
**Context:** The security model requires strict handling of untrusted generated content. Generated code can contain harmful side effects, persistence attempts, exfiltration logic, or destructive actions.  
**Decision:** Forge never executes generated code as an ad hoc action. Code may only be validated through bounded, repository-defined test/build/CI mechanisms allowed by policy. No free-form “run this generated script” capability exists in the agent.  
**Consequences:** The attack surface is reduced and behavior is auditable. Some classes of autonomous experimentation are intentionally unsupported. Repositories must expose safe, structured validation commands for effective operation.  
**Rejected alternatives:**  
- Allowing the model to run arbitrary generated commands locally — rejected for security reasons.  
- Sandboxing arbitrary execution as a general feature — rejected because it adds major complexity and still expands risk.  
- Trusting provider safety filters alone — rejected because local execution risk must be controlled by platform design.

## Repository-defined tests are the validation boundary
**Status:** Accepted  
**Context:** The platform needs a principled way to validate changes without inventing bespoke runtime behavior per task. Existing repository workflows are the most authoritative executable definition of correctness.  
**Decision:** Forge validates generated changes through repository-defined tests, build scripts, and CI workflows configured during onboarding and governed by policy. The platform does not invent hidden validation semantics outside those declared mechanisms.  
**Consequences:** Validation stays aligned with the repository’s real quality gates. Weak repositories will produce weak validation unless improved. Onboarding must identify and normalize project-specific commands and requirements.  
**Rejected alternatives:**  
- Universal built-in test harness independent of repository conventions — rejected because it cannot cover heterogeneous codebases.  
- Model-judged correctness without execution — rejected because it is insufficiently reliable.  
- Task-specific custom execution assembled on the fly — rejected because it is unpredictable and hard to secure.

## GitHub pull requests are the primary integration artifact
**Status:** Accepted  
**Context:** The product promise centers on autonomous development that produces reviewable units in standard engineering workflows. The artifact must fit existing team processes.  
**Decision:** Forge outputs work primarily as GitHub draft pull requests, one per logical unit, with associated branches, CI results, and review context. GitHub is the canonical remote collaboration target for the platform.  
**Consequences:** The platform fits standard repository review processes and branch-based governance. GitHub integration depth is required. Other SCM platforms are not first-class in the initial architecture.  
**Rejected alternatives:**  
- Direct commits to the main branch — rejected because it removes review and governance controls.  
- Email or patch-file output — rejected because it does not integrate with modern team workflows.  
- Equal first-class support for all git hosting providers at launch — rejected to maintain focus and product coherence.

## User approval gates progression between pull requests
**Status:** Accepted  
**Context:** The product is autonomous but user-governed. Users must be able to inspect and approve each completed unit before the system proceeds to the next dependent unit.  
**Decision:** After Forge creates a PR, progression to the next PR in the plan requires user approval according to the platform’s gating model. The agent can prepare work, but human governance controls release of sequential implementation.  
**Consequences:** Users retain control over repository evolution. End-to-end throughput depends on review responsiveness. The system must model paused, awaiting-approval, approved, and resumed states cleanly.  
**Rejected alternatives:**  
- Fully automatic merge-and-continue — rejected because it exceeds the intended human governance level.  
- Manual triggering of every internal pipeline stage — rejected because it sacrifices autonomy.  
- Approval only at the end of the entire plan — rejected because it removes incremental control.

## Documentation regeneration is optional and explicit
**Status:** Accepted  
**Context:** The product may update documentation after implementation, but code and reviewable PR delivery are the primary mission. Documentation work should not destabilize the main build pipeline.  
**Decision:** Documentation regeneration is supported as an optional, explicit capability that can run after implementation completion or as configured by plan/policy. It is not a hidden side effect of every code change.  
**Consequences:** Users can choose whether to incur extra generation and review overhead. Documentation updates remain traceable. The platform avoids silently mutating product docs beyond agreed scope.  
**Rejected alternatives:**  
- Always regenerate all documentation after every PR — rejected because it is noisy, expensive, and often unnecessary.  
- Never support docs regeneration — rejected because maintaining technical documents is part of the product value.  
- Silent in-place docs edits outside PR flow — rejected because they bypass reviewability.

## SwiftUI-based native interface for orchestration, status, and review
**Status:** Accepted  
**Context:** The shell must provide a native macOS user experience for onboarding, status visibility, gating, and review workflows. Platform consistency and trust are important to adoption.  
**Decision:** The user interface is built with SwiftUI in the native shell. It presents plans, PR progression, provider status, authentication state, review controls, and security-relevant prompts as first-class application surfaces.  
**Consequences:** The app aligns with macOS UX conventions and system capabilities. UI state must be synchronized carefully with backend process state. Some complex desktop UI patterns may require additional architecture discipline in SwiftUI.  
**Rejected alternatives:**  
- Embedded web UI — rejected because it weakens native integration and trust posture.  
- CLI-first product — rejected because the specification defines a desktop application shell.  
- Heavy AppKit-only implementation — rejected because SwiftUI is the specified primary framework.

## Sparkle-based application updates with standard macOS distribution
**Status:** Accepted  
**Context:** The shell must support desktop distribution and updates appropriate for a native macOS application outside the App Store model.  
**Decision:** Forge is distributed as a standard macOS application bundle with drag-to-Applications installation and Sparkle-based auto-update support.  
**Consequences:** The app can update independently while preserving native installation expectations. Update signing and release discipline are required. App Store-specific constraints do not drive the architecture.  
**Rejected alternatives:**  
- Mac App Store distribution as the primary channel — rejected because platform behavior and bundled backend requirements are better served by direct distribution.  
- Manual update-only model — rejected because it degrades security and operability.  
- Self-updating custom updater — rejected because Sparkle is the established solution for this class of macOS application.

## Provider integrations use adapter interfaces, not provider-specific pipeline logic
**Status:** Accepted  
**Context:** The consensus engine depends on multiple LLM providers whose APIs, capabilities, and failure modes differ. The core pipeline should not be tightly coupled to any one provider.  
**Decision:** Model providers are integrated through adapter interfaces with normalized request/response, error, timeout, and metadata contracts. The consensus and review pipeline consumes provider abstractions rather than raw provider APIs.  
**Consequences:** Providers can be added, swapped, or versioned with limited blast radius. Adapter design becomes a critical abstraction layer. Some provider-specific features may be inaccessible unless promoted intentionally into shared contracts.  
**Rejected alternatives:**  
- Hard-coding Anthropic and OpenAI logic directly into pipeline stages — rejected because it would entangle orchestration and integration concerns.  
- Lowest-common-denominator text-only interface with no metadata — rejected because the pipeline needs richer semantics.  
- Separate pipeline per provider — rejected because it duplicates orchestration logic.

## Fail closed on authentication, provider, and pipeline uncertainty
**Status:** Accepted  
**Context:** The platform performs high-impact actions in user repositories and remote systems. Ambiguous state or partial trust should not produce autonomous continuation.  
**Decision:** When authentication validity, provider outcomes, repository state, or pipeline invariants are uncertain, Forge stops or pauses in a safe state rather than continuing optimistically. This applies across session handling, provider arbitration, branch operations, and review/CI gates.  
**Consequences:** Safety and predictability improve, but some workflows will halt more often and require explicit recovery actions. Error handling and resumability must be designed carefully.  
**Rejected alternatives:**  
- Best-effort continuation through ambiguous state — rejected because it can create incorrect or unsafe repository changes.  
- Silent retries indefinitely — rejected because it obscures failure and risks runaway behavior.  
- Automatic override of failed gates — rejected because it violates governance and security principles.

## Explicit state machines govern sessions and pipeline progression
**Status:** Accepted  
**Context:** The application spans onboarding, authentication, planning, generation, review, CI, PR creation, approval, and resume flows across two processes. Implicit state would be fragile and difficult to recover.  
**Decision:** Major subsystems use explicit state machines and defined transitions for session lifecycle, backend connectivity, job execution, PR progression, and approval gates.  
**Consequences:** Recovery, testing, and UI rendering become more deterministic. Invalid transitions can be prevented systematically. Implementation requires disciplined event modeling and state synchronization.  
**Rejected alternatives:**  
- Ad hoc boolean flags and loosely coupled callbacks — rejected because they are difficult to reason about in a multi-stage autonomous system.  
- Entirely event-sourced architecture — rejected as unnecessary complexity for the current product scope.  
- Stateless task invocation — rejected because long-running autonomous workflows require durable progression state.

## Local-first repository operation with remote collaboration through GitHub
**Status:** Accepted  
**Context:** The product operates on user repositories in a desktop environment while collaborating through hosted pull requests. The architecture must balance local control and remote team workflows.  
**Decision:** Forge works against local repository checkouts for generation, validation, and branch preparation, and uses GitHub as the remote system for PR publication and collaboration.  
**Consequences:** Users retain local control and visibility into repository state. The app must handle local git state, branch hygiene, and sync issues robustly. Cloud-only repository manipulation is not the primary operating mode.  
**Rejected alternatives:**  
- Remote-only hosted workspace execution — rejected because the desktop product is designed around local repos and local trust boundaries.  
- PR generation without local checkout — rejected because meaningful validation and structured edits require repository context.  
- Direct editing inside GitHub via API only — rejected because it is insufficient for the platform’s workflow.

## Security requirements in TRD-11 override convenience in all subsystems
**Status:** Accepted  
**Context:** Multiple subsystems handle secrets, external content, generated code, CI actions, and repository mutations. A single cross-cutting security authority is necessary to avoid local optimizations that weaken the platform.  
**Decision:** TRD-11 is the governing security authority across all Forge subsystems. Where convenience, performance, or feature flexibility conflicts with TRD-11 controls, security requirements prevail.  
**Consequences:** Security review has architectural priority. Some user-desired shortcuts will be intentionally unsupported. Cross-subsystem designs must be checked against a common control set.  
**Rejected alternatives:**  
- Letting each subsystem define its own local security tradeoffs — rejected because it leads to inconsistency and control gaps.  
- Treating security guidance as non-binding best practice — rejected because the platform performs high-impact automation.  
- Prioritizing speed-to-feature over explicit controls — rejected because trust is fundamental to product viability.

## TRDs are the authoritative specification, not inferred behavior
**Status:** Accepted  
**Context:** The platform is fully specified across a set of TRDs, and multiple implementations and agents may work on the codebase over time. A stable source of truth is required.  
**Decision:** The TRDs in `forge-docs/` are the source of truth for platform behavior. Code, tests, and future changes must conform to documented interfaces, error contracts, security requirements, and ownership boundaries rather than inferred or accidental implementation behavior.  
**Consequences:** Design drift is reduced and change control is clearer. Contributors must consult the owning TRD before modifying subsystems. Unspecified behavior should be clarified in documentation rather than invented in code.  
**Rejected alternatives:**  
- Code-as-specification only — rejected because the platform spans many subsystems and requires explicit cross-cutting contracts.  
- Relying on README-level summaries — rejected because they are too high level to govern implementation.  
- Allowing AI agents to infer missing requirements ad hoc — rejected because it creates inconsistency and drift.