# DECISIONS.md

## [Use the documented monorepo layout as a hard architectural boundary]
**Status:** Accepted  
**Context:** The repository structure is explicitly defined in the TRDs and README. The Crafted subsystem exists alongside Python backend code, shared standards, tests, and source documentation. Drift from this structure would break discoverability, cross-team coordination, and implementation assumptions referenced throughout the documented system.  
**Decision:** Keep Crafted implementation inside `Crafted/` and Crafted-specific XCTest coverage inside `CraftedTests/`. Treat `forge-docs/` as the source of truth for requirements, `forge-standards/` as the source of implementation constraints, `src/` as Python backend only, and `tests/` as Python pytest only. Do not relocate subsystem responsibilities across these boundaries.  
**Consequences:** Crafted code must not be introduced into `src/` or `tests/`. Swift UI shell work must remain isolated from backend runtime code. Documentation and standards must continue to be referenced from their existing locations rather than duplicated into the app target. Build and review tooling can rely on stable paths.  
**Rejected alternatives:**  
- **Flatten the repository into a single app-centric structure:** Rejected because it conflicts with the documented layout and obscures subsystem ownership.  
- **Move Swift tests into the generic `tests/` directory:** Rejected because XCTest and pytest have different tooling and execution assumptions.  
- **Duplicate TRD content into Crafted-local docs:** Rejected because `forge-docs/` is already designated as the source of truth and duplication would create version skew.

## [Implement Crafted as the macOS application shell, not as a standalone full-stack runtime]
**Status:** Accepted  
**Context:** TRD-1 defines Crafted as the macOS application shell, while backend orchestration and repository automation responsibilities are assigned elsewhere in the system. Clear subsystem boundaries are necessary to prevent the app shell from absorbing backend concerns.  
**Decision:** Build Crafted as the Swift/SwiftUI macOS application shell responsible for user-facing flow, state presentation, and client-side interaction. Do not embed backend pipeline orchestration, GitHub write logic, consensus execution, or path security enforcement directly into the Crafted subsystem.  
**Consequences:** Crafted must consume or present backend-driven state rather than reimplement backend behavior. UI code should remain focused on shell concerns such as onboarding, navigation, authentication handoff, and status display. Any need for generation, orchestration, or repository mutation must integrate with the designated backend subsystem rather than bypass it.  
**Rejected alternatives:**  
- **Implement business orchestration directly in the app:** Rejected because it duplicates backend responsibilities and weakens separation of concerns.  
- **Make Crafted a thin wrapper around embedded Python internals:** Rejected because it couples the app shell to backend implementation details and complicates maintainability.  
- **Expand Crafted into a cross-platform client immediately:** Rejected because the documented subsystem is specifically a macOS application shell.

## [Enforce the RootView onboarding decision tree exactly]
**Status:** Accepted  
**Context:** TRD-1 defines a root decision tree in which the app routes based on onboarding state. This flow is foundational to first-run behavior and determines the shell’s top-level composition.  
**Decision:** Implement `RootView` so that `OnboardingState != .complete` routes to `OnboardingContainerView`, and onboarding substate determines the presented screen according to the documented decision tree. Only when onboarding is complete may the application transition to its post-onboarding shell experience.  
**Consequences:** Root routing must be state-driven rather than ad hoc. Screens such as welcome, API key entry, GitHub authentication, and subsequent onboarding steps must remain subordinate to the onboarding container until completion criteria are satisfied. Top-level navigation must not bypass required setup stages.  
**Rejected alternatives:**  
- **Use freeform navigation without a single root decision authority:** Rejected because it would allow inconsistent entry states and bypass required setup.  
- **Present onboarding modally over the main app:** Rejected because the TRD specifies onboarding as the root routing path, not as an optional overlay.  
- **Mark onboarding complete opportunistically after partial setup:** Rejected because it would undermine the explicit state machine defined in the decision tree.

## [Model onboarding as an explicit state machine]
**Status:** Accepted  
**Context:** The documented root flow references distinct onboarding states such as `.notStarted`, `.apiKeys`, and `.githubAuth`. These named states imply a formal progression rather than implicit UI heuristics.  
**Decision:** Represent onboarding with an explicit typed state machine and drive screen transitions from that state. Persist and restore onboarding progress through the state model rather than inferring it from scattered UI flags.  
**Consequences:** View logic must consume a canonical onboarding state. Adding or changing onboarding steps requires updating the state model and root routing intentionally. Restoration after restart becomes deterministic. Testing can validate transitions independently of view rendering.  
**Rejected alternatives:**  
- **Derive onboarding progress from whether individual fields are filled:** Rejected because it creates ambiguous state and brittle transition logic.  
- **Use multiple independent booleans for each step:** Rejected because booleans do not encode ordering, exclusivity, or legal transitions clearly.  
- **Hardcode onboarding progression only inside views:** Rejected because it hides application flow inside presentation code and makes restoration difficult.

## [Preserve stage and gate authority outside Crafted]
**Status:** Accepted  
**Context:** The build pipeline documentation defines multiple stages, explicit gates, checkpointed state transitions, and operator approval before merge. These controls are system-wide governance mechanisms, not UI-local policy.  
**Decision:** Treat pipeline stages, gate decisions, checkpoints, and merge approval as authoritative backend-managed state that Crafted displays and helps the operator act upon, but does not independently redefine or bypass.  
**Consequences:** Crafted must not invent alternate stage names, synthesize completion states without backend confirmation, or expose UI actions that circumvent operator approval or checkpoint requirements. UI wording and state displays should map directly to the documented pipeline model.  
**Rejected alternatives:**  
- **Let the UI maintain its own simplified stage model:** Rejected because it would drift from the documented backend pipeline and create operator confusion.  
- **Auto-approve gates from the client when local conditions look good:** Rejected because gate authority is explicitly part of system governance.  
- **Hide intermediate checkpoint states from the UI model entirely:** Rejected because checkpointed transitions are a required part of the system behavior.

## [Treat checkpointed workflow state as durable and externally sourced]
**Status:** Accepted  
**Context:** The README states that every state transition is checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Crafted must interact safely with this durable process state.  
**Decision:** Design Crafted to read, present, and resume from durable workflow state rather than assuming ephemeral in-memory progress. On app launch or refresh, reconstruct visible workflow status from persisted or backend-provided checkpoints.  
**Consequences:** The UI must support interrupted sessions, restarts, and resumed work without losing process fidelity. Progress indicators and action availability must be derived from authoritative checkpoint state. Local transient state may improve UX but cannot be the source of truth for workflow progression.  
**Rejected alternatives:**  
- **Track workflow progress only in memory during a session:** Rejected because it conflicts with the documented checkpointing requirement.  
- **Use UI navigation stack as the workflow source of truth:** Rejected because navigation state is not durable process state.  
- **Collapse multiple checkpoint states into a single generic “in progress” UI state:** Rejected because it discards required operational detail.

## [Do not bypass backend security and repository boundaries from the Crafted client]
**Status:** Accepted  
**Context:** Critical backend files include `src/github_tools.py` for GitHub I/O and `src/path_security.py` for write-path enforcement. These are designated security boundaries. The Crafted subsystem must not undermine them by introducing alternate mutation paths.  
**Decision:** Route repository writes, GitHub mutations, and path-sensitive operations through the designated backend mechanisms. Crafted may initiate or request operations, but must not implement direct alternate write paths that bypass backend validation, SHA protocol, rate limiting, or path security checks.  
**Consequences:** Client features that affect repositories or remote state require integration contracts with the backend rather than direct filesystem or GitHub-side mutation logic in the app shell. Security and audit assumptions remain centralized. UI actions may need to wait on validated backend responses.  
**Rejected alternatives:**  
- **Perform direct GitHub API writes from Crafted for responsiveness:** Rejected because it bypasses documented backend controls.  
- **Write directly into working directories from the app shell:** Rejected because all write paths must pass through the path security boundary.  
- **Replicate security validation in Swift and allow either path:** Rejected because duplicated security logic creates inconsistency and weakens enforcement.

## [Keep Crafted complexity low and composition-oriented]
**Status:** Accepted  
**Context:** The documented system enforces a maximum cyclomatic complexity of 15 per stage in the build pipeline, reflecting a broader architectural preference for bounded complexity. Although this limit is explicitly stated for pipeline stages, the same discipline is necessary in Crafted to keep flow logic auditable and maintainable.  
**Decision:** Structure Crafted using small, composable views and state coordinators. Keep routing, onboarding progression, and status presentation logic simple enough to remain inspectable, and refactor branching logic before it becomes deeply nested or multi-responsibility.  
**Consequences:** Root and onboarding flow implementation should prefer decomposition over large controller-style objects. Feature additions may require new coordinators or subviews rather than extending a single central object. Testability improves because logic is isolated into narrower units.  
**Rejected alternatives:**  
- **Use one large app coordinator containing all flow logic:** Rejected because it encourages excessive branching and opaque behavior.  
- **Embed state transition logic directly across many views without structure:** Rejected because it creates distributed complexity that is hard to audit.  
- **Ignore complexity discipline because the explicit limit only names backend stages:** Rejected because the same maintainability concerns apply to the app shell’s orchestration code.