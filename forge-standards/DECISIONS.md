# DECISIONS.md

## Native macOS shell with Python intelligence backend
**Status:** Accepted  
**Context:** Forge must provide a native macOS user experience while also supporting rapid iteration in AI orchestration, provider integration, and repository automation. The source materials define a two-process architecture: Swift for user-facing and security-sensitive platform duties, Python for intelligence and workflow execution.  
**Decision:** Forge is built as a two-process system:
- A native Swift/SwiftUI macOS shell owns UI, app lifecycle, auth gates, Keychain access, local orchestration, update flow, and process supervision.
- A bundled Python 3.12 backend owns planning, consensus generation, review pipeline, documentation generation, and GitHub automation.
- The two processes communicate only through a local authenticated IPC channel using line-delimited JSON.  
**Consequences:**  
- Platform-sensitive responsibilities remain in Swift where macOS APIs and security primitives are strongest.
- AI and orchestration logic can evolve faster without destabilizing the shell.
- All cross-process contracts must be explicit, versioned, and testable.
- Debugging complexity increases because failures may originate in either process or in their boundary.
**Rejected alternatives:**  
- **Single-process all-Swift implementation:** rejected because provider integration and AI pipeline iteration would be slower and less flexible.
- **Single-process all-Python desktop app:** rejected because native macOS UX, security integration, and system trust surfaces would be weaker.
- **Remote-only orchestration service:** rejected because local trust boundaries and repository control are core to the product.

## Swift shell owns all secrets and user identity
**Status:** Accepted  
**Context:** The platform handles API credentials, GitHub authentication state, and user session gating. Security requirements place the strongest trust boundary around native macOS facilities.  
**Decision:** All durable secrets and identity-sensitive operations are owned by the Swift shell:
- Secrets are stored in Keychain.
- Biometric or equivalent local authentication is enforced by the shell.
- The Python backend never becomes the source of truth for secrets.
- The backend receives only scoped, minimal credentials or tokens required for current work.  
**Consequences:**  
- Secret exposure risk is reduced in the more dynamic backend runtime.
- Shell/backend message design must support capability passing rather than unrestricted secret sharing.
- Backend features that require new credentials must be mediated through shell APIs.
**Rejected alternatives:**  
- **Store secrets directly in Python config files or env vars:** rejected due to weak local security posture.
- **Let both processes read secrets independently:** rejected because it expands the trusted computing base unnecessarily.

## Authenticated local IPC over Unix domain socket with line-delimited JSON
**Status:** Accepted  
**Context:** The two processes require a robust, inspectable, low-overhead local protocol for commands, events, and streaming status. The architecture docs specify authenticated Unix socket communication with line-delimited JSON.  
**Decision:** Forge uses an authenticated Unix domain socket as the sole shell/backend IPC mechanism, with one JSON object per line as the wire format.  
**Consequences:**  
- Protocol traffic is easy to log, test, replay, and fuzz.
- Streaming progress and event notifications are naturally supported.
- Schema discipline is required to prevent drift and incompatible assumptions.
- Binary payloads must be passed indirectly or encoded explicitly when unavoidable.
**Rejected alternatives:**  
- **XPC for all communication:** rejected because the backend is Python and needs a language-neutral boundary.
- **HTTP localhost server:** rejected because it adds unnecessary surface area and server semantics.
- **StdIO pipes only:** rejected because supervision, reconnection, and authentication are less robust.

## No generated code is ever executed by the agent
**Status:** Accepted  
**Context:** The product generates code, tests, and repo changes autonomously. Security requirements explicitly prohibit the system from executing generated code. This is a foundational control against prompt-injection-to-execution chains.  
**Decision:** Forge never directly executes generated application code. It may inspect, diff, lint, type-check, or run pre-approved repository CI flows within controlled policy, but it does not execute arbitrary generated artifacts as runnable programs outside those controls.  
**Consequences:**  
- The platform is constrained to static analysis, test/CI pipelines, and repository-native validation steps.
- Prompt injection risks from generated scripts, binaries, or command suggestions are substantially reduced.
- Some classes of dynamic verification are intentionally unavailable.
**Rejected alternatives:**  
- **Run generated code in a local sandbox:** rejected because it still creates a high-risk execution path.
- **Allow opt-in execution from the UI:** rejected because it weakens the core security invariant.

## Specification-driven development with TRDs as source of truth
**Status:** Accepted  
**Context:** Forge is intended to build software from technical specifications and is itself governed by a set of subsystem TRDs. Consistency across shell, backend, pipeline, and UI requires a single authoritative requirement source.  
**Decision:** Technical Requirements Documents are the authoritative source for system behavior, interfaces, state machines, error contracts, and testing expectations. Implementation and operational decisions must trace back to TRD-defined requirements.  
**Consequences:**  
- Design drift is reduced.
- Engineering changes require corresponding spec updates when they alter externally meaningful behavior.
- Agent and human contributors must consult the relevant TRD before modifying a subsystem.
**Rejected alternatives:**  
- **Code-first evolution with docs updated later:** rejected because it creates ambiguity and weakens cross-subsystem contracts.
- **Use informal README guidance as primary authority:** rejected because it lacks sufficient precision.

## Directed build agent, not a conversational assistant
**Status:** Accepted  
**Context:** Product identity is central to architecture. Forge is designed to translate user intent plus specifications into planned repository changes and pull requests, not to maximize open-ended chat interaction.  
**Decision:** The platform is optimized around an execution pipeline:
- ingest specifications and repository context,
- derive a structured plan,
- decompose into logical PR units,
- implement and review changes,
- run CI,
- open draft PRs,
- continue iteratively after user approval.  
Chat may exist only as a support surface, not as the primary product mode.  
**Consequences:**  
- UX, telemetry, and backend architecture prioritize task progression and artifact generation over conversational breadth.
- State machines focus on jobs, PRs, reviews, and approvals rather than dialog turns.
- Provider prompting and memory design are constrained to execution outcomes.
**Rejected alternatives:**  
- **General-purpose coding chat app:** rejected because it dilutes product focus.
- **Inline autocomplete tool:** rejected because it does not match the autonomous PR-based workflow.

## Plan decomposition into PRD and ordered pull requests
**Status:** Accepted  
**Context:** Large user intents must be translated into reviewable, mergeable work units. The README specifies decomposition from intent to PRD plan to a sequence of pull requests.  
**Decision:** Forge first produces a structured plan, then decomposes execution into an ordered series of small, logical pull requests with explicit dependencies and completion criteria.  
**Consequences:**  
- Users can review progress incrementally.
- CI failures and regressions are localized.
- Merge sequencing becomes part of system state and orchestration logic.
- Planning quality directly affects execution throughput.
**Rejected alternatives:**  
- **Single giant PR per user intent:** rejected because reviewability and recovery are poor.
- **Unordered micro-commits without PR semantics:** rejected because human governance is weaker.

## Parallel multi-model generation with consensus and Claude arbitration
**Status:** Accepted  
**Context:** The product promise is based on two-model generation with arbitration. The architecture references a consensus engine and provider adapters, and product copy specifies Claude plus GPT-4o with Claude arbitrating outcomes.  
**Decision:** Forge generates proposed implementations using multiple providers in parallel and resolves output through a consensus process in which Claude serves as final arbiter for acceptance and consolidation.  
**Consequences:**  
- Quality and robustness are improved through diversity of model outputs.
- Provider adapter abstraction becomes mandatory.
- Latency and cost increase relative to single-model generation.
- Arbitration logic becomes a critical correctness path.
**Rejected alternatives:**  
- **Single-provider generation:** rejected because it reduces resilience and comparative review quality.
- **Majority voting only:** rejected because it lacks a designated quality arbiter.
- **Human-only arbitration at every step:** rejected because it breaks autonomous throughput.

## Three-pass review pipeline before PR creation
**Status:** Accepted  
**Context:** Generated changes require structured quality control before they are surfaced to the user. The product description specifies a three-pass review cycle.  
**Decision:** Every implementation unit passes through a fixed multi-pass review pipeline before draft PR creation, including code quality, spec conformance, and likely correctness/risk checks.  
**Consequences:**  
- Review behavior becomes a first-class pipeline stage rather than an ad hoc prompt.
- The system can reject or revise low-confidence changes before consuming user attention.
- End-to-end latency increases, but reviewable quality improves.
**Rejected alternatives:**  
- **Single-pass generation and immediate PR:** rejected because quality variance is too high.
- **Unlimited review recursion:** rejected because runtime becomes unbounded and harder to supervise.

## Human-gated progression between pull requests
**Status:** Accepted  
**Context:** The system is autonomous but not fully self-authorizing. The product flow states that the user reviews and approves each PR, after which the next unit proceeds.  
**Decision:** Forge requires explicit human approval before advancing from one draft PR to the next dependent PR in a plan. The system may prepare subsequent work opportunistically, but merge/progression authority remains user-gated.  
**Consequences:**  
- Users retain control over repository evolution.
- Errors are less likely to cascade across a long plan.
- Throughput is slower than fully autonomous branching and merging.
**Rejected alternatives:**  
- **Automatic merge and continue:** rejected because governance and trust are insufficient.
- **Require approval for every internal pipeline stage:** rejected because it would make the product too manual.

## GitHub pull requests are the primary output artifact
**Status:** Accepted  
**Context:** The platform’s job is to create reviewable repository changes in standard developer workflows. GitHub is explicitly named as the target collaboration surface.  
**Decision:** The canonical unit of delivered work is a GitHub draft pull request containing code changes, tests, CI status, and machine-generated rationale. Local diffs or chat summaries are secondary.  
**Consequences:**  
- Backend must deeply integrate with GitHub repository, branch, commit, and PR APIs.
- UI must expose PR-centric status and review context.
- Alternative SCM platforms are not first-class in the initial architecture.
**Rejected alternatives:**  
- **Patch file export only:** rejected because it does not fit team review workflows.
- **Direct branch pushes without PRs:** rejected because review and governance are weakened.

## Repository-native validation through CI rather than bespoke execution framework
**Status:** Accepted  
**Context:** Forge must validate changes while maintaining the no-generated-code-execution security posture. Repository CI is the natural controlled validation mechanism already accepted by teams.  
**Decision:** Validation is performed primarily through existing repository test, lint, and CI workflows, executed under explicit policy and surfaced as part of PR readiness. Forge does not invent a parallel generalized runtime for generated code.  
**Consequences:**  
- The system aligns with existing engineering workflows.
- Validation quality depends on the repository’s own test maturity.
- CI integration becomes essential to pipeline correctness.
**Rejected alternatives:**  
- **Custom universal local execution harness:** rejected because it increases risk and complexity.
- **No automated validation before PR:** rejected because review quality would be too low.

## Native SwiftUI interface for core user experience
**Status:** Accepted  
**Context:** The shell TRD defines a native macOS shell and SwiftUI view system. A native interface is required for trust, responsiveness, and platform integration.  
**Decision:** The user interface is implemented in SwiftUI within the native macOS shell, including workflow views, cards, panels, auth surfaces, and operational status.  
**Consequences:**  
- UI architecture follows macOS conventions and lifecycle models.
- Platform-specific polish and accessibility are improved.
- Cross-platform UI reuse is intentionally deprioritized.
**Rejected alternatives:**  
- **Web UI in an embedded browser shell:** rejected because it weakens native integration and trust.
- **Cross-platform UI toolkit:** rejected because macOS-first quality is more important than portability.

## Bundled Python runtime instead of system Python dependency
**Status:** Accepted  
**Context:** The shell TRD references Python 3.12 bundled with the app. Relying on a user-installed interpreter would create setup drift and support issues.  
**Decision:** Forge ships with a bundled Python runtime and backend dependencies managed as part of the application distribution. The product does not depend on system Python availability or configuration.  
**Consequences:**  
- Install and runtime behavior are predictable.
- Packaging and update complexity increase.
- Security patching of Python dependencies becomes part of product operations.
**Rejected alternatives:**  
- **Use system Python:** rejected because environment inconsistency is unacceptable.
- **Download runtime on first launch:** rejected because offline and trust characteristics are worse.

## Sparkle-based application auto-update for macOS distribution
**Status:** Accepted  
**Context:** The shell owns installation and distribution, and the TRD names Sparkle for auto-update. A native update channel is needed for rapid security and feature delivery.  
**Decision:** Forge uses standard macOS app bundle distribution with Sparkle-managed application updates.  
**Consequences:**  
- Update UX is native and well understood.
- Release signing and update feed operations are required.
- Backend/runtime updates are coupled to app release packaging.
**Rejected alternatives:**  
- **Custom updater:** rejected because existing native mechanisms are safer and less costly.
- **Manual download-only updates:** rejected because security and operational responsiveness are worse.

## Capability-minimized backend access model
**Status:** Accepted  
**Context:** The backend performs high-risk operations over untrusted inputs including repository content, model outputs, and external service responses. Security requirements imply strict minimization of ambient authority.  
**Decision:** The Python backend operates with least privilege:
- receives only scoped capabilities required for current tasks,
- accesses files, tokens, and network operations through constrained interfaces where possible,
- is denied direct long-lived ownership of sensitive credentials.  
**Consequences:**  
- Interface design is more complex.
- Compromise impact is reduced.
- Some backend tasks require explicit shell mediation and token refresh flows.
**Rejected alternatives:**  
- **Give backend broad filesystem and credential access:** rejected due to excessive blast radius.
- **Run all logic in shell to avoid delegation:** rejected because it sacrifices flexibility and separation of concerns.

## Explicit subsystem ownership boundaries
**Status:** Accepted  
**Context:** The platform spans shell, UI, consensus engine, provider adapters, pipeline orchestration, GitHub integration, and security controls. Clear ownership prevents duplication and contradictory behavior.  
**Decision:** Forge assigns primary ownership by subsystem:
- shell: lifecycle, UX container, auth, secrets, supervision;
- backend: planning, consensus, generation, review, docs, GitHub automation;
- shared boundary: versioned IPC contracts only.  
**Consequences:**  
- Cross-cutting features must be designed through explicit contracts rather than hidden coupling.
- Teams can evolve subsystems independently within interface constraints.
- Some features may require more coordination upfront.
**Rejected alternatives:**  
- **Shared responsibility across both processes for convenience:** rejected because it causes ambiguity and drift.
- **Monolithic service layer spanning both languages:** rejected because boundaries become porous.

## Machine-readable contracts at process boundaries
**Status:** Accepted  
**Context:** IPC is central to operation, and the two implementations are in different languages. Reliability requires strict contract definitions rather than informal payload conventions.  
**Decision:** All shell/backend messages use explicit schemas, typed envelopes, version identifiers, and defined error contracts. Backward-incompatible changes require coordinated version updates.  
**Consequences:**  
- Integration testing and replay become practical.
- Rolling changes across the boundary require discipline.
- Ad hoc fields and undocumented events are disallowed.
**Rejected alternatives:**  
- **Loose JSON with best-effort parsing:** rejected because failures would become opaque and brittle.
- **Language-specific object serialization:** rejected because it harms interoperability and debuggability.

## Structured error contracts across all major interfaces
**Status:** Accepted  
**Context:** Multiple subsystems fail for different reasons: provider issues, auth failures, repository conflicts, CI errors, and security policy denials. The docs emphasize explicit error contracts.  
**Decision:** Forge standardizes errors as structured, machine-readable categories with user-displayable summaries, remediation hints, and correlation to pipeline stage or subsystem.  
**Consequences:**  
- UI can present clear recovery actions.
- Telemetry and support workflows improve.
- Every subsystem must classify errors rather than surfacing raw exceptions directly.
**Rejected alternatives:**  
- **Pass through raw provider and runtime errors:** rejected because UX and automation degrade.
- **Single generic failure state:** rejected because it prevents recovery.

## Provider integration via adapter abstraction
**Status:** Accepted  
**Context:** Consensus depends on multiple model providers, and the architecture references provider adapters. The system must isolate provider-specific APIs, limits, and prompt formatting differences.  
**Decision:** All model providers are integrated through a common adapter interface that normalizes request construction, streaming, retries, error mapping, token accounting, and response extraction.  
**Consequences:**  
- New providers can be added without rewriting the pipeline.
- Provider-specific capabilities must be abstracted carefully.
- The common interface may expose only the intersection of supported features unless explicitly extended.
**Rejected alternatives:**  
- **Embed provider-specific logic throughout the pipeline:** rejected because it creates tight coupling.
- **Use only one provider SDK permanently:** rejected because it undermines consensus architecture.

## Incremental, reviewable work over maximal autonomy
**Status:** Accepted  
**Context:** User trust is essential for an agent that changes codebases. Reviewable increments are safer than optimizing purely for speed or independence.  
**Decision:** The platform favors smaller, explainable, reviewable outputs with explicit checkpoints over large, opaque autonomous changesets.  
**Consequences:**  
- Plans are broken into units that are easy to inspect and revert.
- The UI must expose rationale and progress for each unit.
- Some efficiency is sacrificed for trust and governance.
**Rejected alternatives:**  
- **Optimize for end-to-end fully automatic completion:** rejected because failure cost and trust burden are too high.

## Documentation regeneration as an optional post-build phase
**Status:** Accepted  
**Context:** Product behavior includes optional documentation regeneration after builds complete. Documentation changes can be useful but noisy and are not always desired.  
**Decision:** Documentation regeneration is treated as an optional, explicit pipeline phase after implementation work reaches a suitable completion point.  
**Consequences:**  
- Users can avoid unnecessary documentation churn.
- Documentation tasks can be isolated from core implementation PRs when appropriate.
- The planner must understand when docs are required versus optional.
**Rejected alternatives:**  
- **Always regenerate docs:** rejected because it creates noise and larger diffs.
- **Never regenerate docs automatically:** rejected because specs and implementation can drift.

## Local-first repository operation
**Status:** Accepted  
**Context:** The product acts on user repositories under local control and only publishes changes through GitHub as PR artifacts. Trust and usability require local workspace awareness.  
**Decision:** Forge operates against a local checked-out repository as the execution workspace, using GitHub as the remote collaboration and publication target rather than as the sole source of repository state.  
**Consequences:**  
- The system can inspect and prepare changes before publication.
- Local repo state, branch hygiene, and workspace validation become necessary concerns.
- Remote-only repository operation is not the primary mode.
**Rejected alternatives:**  
- **Operate entirely against remote GitHub APIs without local checkout:** rejected because code synthesis, diffing, and validation are less reliable.
- **Cloud-hosted workspace only:** rejected because it weakens local control and trust.

## App-level supervision of backend lifecycle
**Status:** Accepted  
**Context:** Because the shell is the trusted container and UX surface, it must manage backend startup, health, shutdown, and recovery.  
**Decision:** The Swift shell supervises the Python backend process, including launch, handshake, readiness checks, crash detection, restart policy, and clean shutdown.  
**Consequences:**  
- The shell becomes responsible for operational resilience.
- The backend must expose health and protocol readiness semantics.
- Crash loops and degraded modes must be surfaced to users clearly.
**Rejected alternatives:**  
- **Let backend self-daemonize independently:** rejected because it weakens control and observability.
- **Manual backend startup by the user:** rejected because it harms product usability.

## Security policy is a cross-cutting architectural authority
**Status:** Accepted  
**Context:** The source materials explicitly identify a dedicated security TRD governing all components. Security constraints must override subsystem convenience.  
**Decision:** Security requirements are treated as binding architecture-wide constraints. Any feature involving credentials, external content, generated code, CI, repository writes, or network access must conform to platform security policy even when that complicates implementation.  
**Consequences:**  
- Security review is required for many changes.
- Some otherwise attractive shortcuts are unavailable.
- Cross-subsystem consistency is improved because one policy source governs all.  
**Rejected alternatives:**  
- **Local subsystem-specific security rules only:** rejected because gaps and contradictions are likely.
- **Defer security hardening until later:** rejected because core trust boundaries are foundational.