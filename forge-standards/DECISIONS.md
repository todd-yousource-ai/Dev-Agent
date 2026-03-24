# DECISIONS.md

## Adopt a native macOS two-process architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent, not a web app or editor plugin. The repository guidance and product description state that Crafted consists of a Swift shell and a Python backend, with strict separation of responsibilities. TRD-1 defines the macOS Application Shell as foundational, and the repository-level docs establish that the Swift process owns UI, authentication, Keychain, and orchestration while the Python process owns intelligence, generation, and GitHub operations.  
**Decision:** Crafted is implemented as a two-process system: a native Swift/SwiftUI macOS shell and a separate bundled Python 3.12 backend. The shell owns installation, distribution, identity, authentication, secret handling, session lifecycle, and native macOS integration. The backend owns consensus, planning, generation, self-correction, lint/fix loops, CI-related workflow orchestration, and GitHub operations.  
**Consequences:** This enforces strict subsystem boundaries, process isolation, and clear ownership of security-sensitive responsibilities. Features must be placed in the correct process, and cross-process interactions must be explicit. Packaging, startup, monitoring, and IPC become first-class design concerns.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because the source documents explicitly define a two-process architecture and separate shell/backend responsibilities.  
- **Web or Electron shell:** Rejected because TRD-1 specifies a native macOS application shell in Swift/SwiftUI.  
- **Backend-only CLI architecture:** Rejected because the product requires a native shell for UI, auth, Keychain, and macOS lifecycle integration.

## Use Swift/SwiftUI for the application shell
**Status:** Accepted  
**Context:** TRD-1 defines the application shell as a native macOS container implemented with Swift 5.9+ and SwiftUI, targeting macOS 13.0+. Repository instructions further map Swift files and SwiftUI views to shell-related TRDs.  
**Decision:** All shell functionality is implemented in Swift 5.9+ using SwiftUI for the native macOS interface, with minimum supported macOS version 13.0 Ventura.  
**Consequences:** The product aligns with native macOS conventions, security APIs, and lifecycle behaviors. UI components, shell orchestration, and platform integration must use Apple-native frameworks and patterns. Support for older macOS versions is excluded.  
**Rejected alternatives:**  
- **AppKit-first shell:** Rejected because the shell is specified in SwiftUI.  
- **Cross-platform UI framework:** Rejected because the product is explicitly a native macOS app.  
- **Older macOS compatibility target:** Rejected because TRD-1 sets the minimum macOS version at 13.0.

## Bundle Python 3.12 as the backend runtime
**Status:** Accepted  
**Context:** TRD-1 lists Python 3.12 as bundled, and repository guidance assigns intelligence and automation responsibilities to the Python backend. A bundled runtime is necessary for a controlled, predictable execution environment.  
**Decision:** The backend is implemented in Python 3.12 and shipped as part of the macOS application bundle rather than depending on a user-managed system Python.  
**Consequences:** Runtime behavior is controlled and reproducible across installations. Packaging complexity increases, but environmental drift and dependency issues are reduced. Backend code must be compatible with the bundled interpreter version.  
**Rejected alternatives:**  
- **Use system Python:** Rejected because it would introduce dependency and compatibility variability inconsistent with a packaged native product.  
- **Implement backend in Swift:** Rejected because the source documents explicitly define a Python backend.  
- **Require external Python installation:** Rejected because the shell is responsible for packaging and installation as a native app.

## Communicate between shell and backend over an authenticated Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** Repository guidance explicitly states that the two processes communicate through an authenticated Unix socket using line-delimited JSON. Because the processes are separated and security-relevant boundaries exist between them, IPC format and authentication must be standardized.  
**Decision:** Inter-process communication between the Swift shell and Python backend uses an authenticated Unix domain socket protocol with line-delimited JSON messages.  
**Consequences:** The IPC boundary is stable, inspectable, and language-agnostic across Swift and Python. Message framing is simple and operationally predictable. Both sides must implement protocol authentication, schema discipline, and robust error handling at the socket boundary.  
**Rejected alternatives:**  
- **XPC-only communication:** Rejected because the repository-level architecture specifies an authenticated Unix socket with line-delimited JSON.  
- **HTTP localhost API:** Rejected because it expands attack surface and diverges from the specified local authenticated IPC model.  
- **Binary custom protocol:** Rejected because line-delimited JSON is the specified interchange format.

## Centralize UI, authentication, and secret ownership in the Swift shell
**Status:** Accepted  
**Context:** Both AGENTS.md and CLAUDE.md assign UI, authentication, Keychain, and shell orchestration to the Swift process. TRD-1 defines the shell as owner of identity and authentication, including biometric gate, Keychain storage, and session lifecycle.  
**Decision:** The Swift shell is the sole owner of all user interface, identity, authentication, biometric gating, Keychain interactions, and session state. The backend does not directly manage these concerns.  
**Consequences:** Secret material and user authentication remain in the native macOS trust boundary. The backend must obtain any required capability only through shell-mediated interfaces. Feature work that touches credentials or session state must be implemented in the shell or via explicit shell-controlled handoff.  
**Rejected alternatives:**  
- **Backend-managed auth or secret storage:** Rejected because ownership is explicitly assigned to the shell.  
- **Shared responsibility across processes:** Rejected because it weakens the trust boundary and contradicts the documented architecture.  
- **UI in the backend:** Rejected because the shell is defined as the native UI container.

## Centralize intelligence, generation, and GitHub operations in the Python backend
**Status:** Accepted  
**Context:** Repository guidance defines the Python backend as owner of consensus, pipeline, generation, and GitHub operations. The product description describes a directed build agent that plans, generates, validates, and opens PRs autonomously.  
**Decision:** The Python backend owns task intelligence: scope assessment, PRD planning, typed pull-request decomposition, multi-model generation, self-correction, lint gate, iterative fix loop, CI workflow orchestration, and GitHub interactions.  
**Consequences:** The shell remains thin with respect to model orchestration and repository automation. GitHub and generation-related behavior must be implemented in backend services rather than embedded in the UI layer.  
**Rejected alternatives:**  
- **Shell-driven generation pipeline:** Rejected because generation and GitHub operations belong to the Python backend.  
- **External hosted orchestration service:** Rejected because the source material specifies a local two-process application.  
- **Manual PR workflow only:** Rejected because the product is defined to autonomously create and sequence PRs.

## Treat the TRDs as the sole source of truth for implementation
**Status:** Accepted  
**Context:** AGENTS.md and CLAUDE.md state that the 16 TRDs in `forge-docs/` completely specify the product and that code must match them. They explicitly instruct implementers not to invent requirements.  
**Decision:** Architectural, interface, security, state machine, error contract, and testing decisions are derived from the TRDs, and implementation must conform to them. Where ambiguity exists, the controlling TRD for the subsystem must be consulted before changes are made.  
**Consequences:** Ad hoc feature interpretation is constrained. Engineering work must trace back to a documented TRD. This improves consistency but requires discipline in documentation-first development.  
**Rejected alternatives:**  
- **Code as primary source of truth:** Rejected because the repository instructions explicitly designate the TRDs as authoritative.  
- **Developer interpretation filling gaps freely:** Rejected because the docs explicitly prohibit inventing requirements.  
- **README-only governance:** Rejected because the README is descriptive, while the TRDs are normative.

## Make TRD-1 the foundational dependency for shell-adjacent subsystems
**Status:** Accepted  
**Context:** TRD-1 is marked as foundational and is required by TRD-2, TRD-3, TRD-4, TRD-5, and TRD-8. It defines the shell’s purpose, packaging, authentication, architecture, and orchestration responsibilities.  
**Decision:** Shell-adjacent subsystem design inherits its base constraints from TRD-1, and dependent subsystem work must conform to its platform, packaging, lifecycle, and security boundaries.  
**Consequences:** Changes in dependent shell-related subsystems must be evaluated against TRD-1 first. Foundational shell decisions become architectural constraints for all downstream components.  
**Rejected alternatives:**  
- **Subsystem-specific divergence from shell foundations:** Rejected because TRD-1 is explicitly foundational and referenced by dependent TRDs.  
- **Independent platform contracts per subsystem:** Rejected because the shell establishes shared platform and orchestration behavior.

## Enforce the global security model from TRD-11 across all components
**Status:** Accepted  
**Context:** AGENTS.md states that TRD-11 governs all components and must be read before touching credentials, external content, generated code, or CI. The repository identity describes a security-sensitive system operating across credentials, source code, generated code, and GitHub automation.  
**Decision:** Security-relevant behavior across shell, backend, external content handling, credential use, generated artifacts, and CI interaction is governed by TRD-11 as a cross-cutting authority. No subsystem may define contradictory local security behavior.  
**Consequences:** Security reviews and changes must be checked against a single controlling specification. Cross-cutting controls may limit implementation choices in every subsystem. Teams cannot optimize locally at the expense of the global security model.  
**Rejected alternatives:**  
- **Per-subsystem independent security models:** Rejected because TRD-11 is explicitly global.  
- **Best-effort security without mandatory review of TRD-11:** Rejected because repository instructions require TRD-11 consultation for security-relevant changes.

## Prohibit execution of generated code by either process
**Status:** Accepted  
**Context:** CLAUDE.md explicitly states that neither process ever executes generated code. This is a core safety boundary for a system that produces code autonomously.  
**Decision:** Generated code is never executed by the Swift shell or Python backend as part of normal operation. The system may generate, write, validate through non-execution checks, and prepare repository changes, but it must not directly run generated code.  
**Consequences:** Validation strategies must rely on non-execution mechanisms, repository CI, linting, static analysis, and controlled fix loops rather than local execution of generated artifacts. Some implementation approaches that would accelerate feedback are disallowed.  
**Rejected alternatives:**  
- **Run generated code locally for validation:** Rejected because the repository instructions explicitly prohibit execution.  
- **Allow shell-only execution of generated code:** Rejected because the prohibition applies to both processes.  
- **Selective execution behind a feature flag:** Rejected because it would violate the stated invariant.

## Use a directed build-agent workflow rather than a chat-centric interaction model
**Status:** Accepted  
**Context:** The README explicitly states that Crafted is not a chat interface, not autocomplete, and not a copilot. It is defined as a directed build agent that takes repository context, TRDs, and user intent, then autonomously produces ordered PRs.  
**Decision:** Product behavior is optimized around autonomous directed delivery workflows: understanding user intent, assessing confidence, planning, decomposing work into typed pull requests, generating code and tests, validating changes, and opening draft PRs for review. Chat-style conversational interaction is not the primary product model.  
**Consequences:** UX, workflow orchestration, and backend design prioritize structured task progression and artifact production over open-ended dialogue. Features that imply a copilot or chat assistant model are out of scope unless explicitly specified by TRDs.  
**Rejected alternatives:**  
- **General chat assistant UX:** Rejected because the README explicitly says the product is not a chat interface.  
- **Inline autocomplete product:** Rejected because the README explicitly says it is not code autocomplete.  
- **IDE copilot workflow:** Rejected because the product is defined as a directed build agent with PR-based output.

## Use multi-model consensus with Claude and GPT-4o, with Claude as arbiter
**Status:** Accepted  
**Context:** The README defines the core generation model as a two-model consensus engine using Claude and GPT-4o in parallel, with Claude arbitrating every result. The backend is assigned ownership of consensus and provider adaptation in repository guidance.  
**Decision:** Code generation and related reasoning use a two-model consensus architecture in which Claude and GPT-4o operate in parallel and Claude serves as the arbitration authority for outcomes.  
**Consequences:** Provider abstraction, consensus orchestration, result comparison, and arbitration are required backend capabilities. Model-specific assumptions must be isolated behind adapters. Product behavior depends on coordinated multi-provider operation rather than a single-model pipeline.  
**Rejected alternatives:**  
- **Single-model generation pipeline:** Rejected because the product is explicitly defined around two-model consensus.  
- **Human-only arbitration:** Rejected because Claude is specified as the arbiter of every result.  
- **Symmetric voting without arbitration:** Rejected because the product description assigns arbitration specifically to Claude.

## Insert an explicit confidence assessment before committing to scope
**Status:** Accepted  
**Context:** The README states that the agent assesses its confidence in the scope before committing to it. This indicates an intentional gating step before planning and execution.  
**Decision:** Before the system commits to implementation scope, it performs an explicit confidence assessment on the user’s intent and the loaded specifications.  
**Consequences:** The workflow includes a pre-commit gate that can constrain or defer downstream planning when confidence is insufficient. Planning and PR generation are not purely immediate actions.  
**Rejected alternatives:**  
- **Always proceed directly to planning:** Rejected because the product explicitly assesses confidence before committing to scope.  
- **Human-only confidence judgment:** Rejected because the agent itself is described as performing the assessment.

## Plan work through hierarchical decomposition from intent to PRD to typed pull requests
**Status:** Accepted  
**Context:** The README specifies a workflow in which the agent takes plain-language intent, decomposes it into an ordered PRD plan, then decomposes each PRD into a sequence of typed pull requests.  
**Decision:** Work planning follows a hierarchical decomposition pipeline: user intent → ordered PRD plan → sequence of typed PRs → implementation artifacts.  
**Consequences:** Planning data structures, workflow stages, and UI/state representation must support hierarchical planning and ordered execution. Direct one-shot generation without structured decomposition is out of alignment with product requirements.  
**Rejected alternatives:**  
- **Single-pass implementation from intent to code:** Rejected because the product requires intermediate PRD and typed PR decomposition.  
- **Flat task list planning:** Rejected because the specified workflow is hierarchical and ordered.  
- **Unordered PR generation:** Rejected because PRs are produced as a sequence.

## Validate generated changes through self-correction, lint gating, iterative fix loops, and CI before draft PR creation
**Status:** Accepted  
**Context:** The README describes a fixed validation sequence: generation and tests using two providers in parallel, then self-correction, a lint gate, an iterative fix loop, CI execution, and finally opening a draft PR.  
**Decision:** Generated work must pass through a staged validation pipeline consisting of self-correction, lint gating, iterative fix loops, and CI workflow execution before a draft pull request is opened.  
**Consequences:** PR creation is downstream of validation rather than immediate after code generation. The backend must track stage outcomes and support retries/fix cycles. UX and status models must reflect a multi-stage pipeline.  
**Rejected alternatives:**  
- **Open PR immediately after first generation pass:** Rejected because the README specifies multiple validation stages before PR creation.  
- **Lint-only validation:** Rejected because the workflow includes self-correction, iterative fix loops, and CI in addition to lint.  
- **Manual validation only:** Rejected because these stages are automated parts of the product workflow.

## Use draft pull requests as the review artifact for each logical unit of work
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests, one per logical unit, and that each is opened as a draft PR for user review.  
**Decision:** The system packages work into draft GitHub pull requests, with one pull request per logical unit produced by the planning pipeline.  
**Consequences:** GitHub integration must support branch management, PR metadata, and draft PR creation. Work granularity must be structured around logical units rather than monolithic repository-wide changes.  
**Rejected alternatives:**  
- **Direct commit to main branch:** Rejected because the workflow is PR-based.  
- **Single PR for all work:** Rejected because the README specifies one PR per logical unit.  
- **Non-draft PRs by default:** Rejected because draft PRs are the specified review artifact.

## Pipeline next work while the user reviews the previous pull request
**Status:** Accepted  
**Context:** The README states that when the user approves a PR, the agent advances, and that the agent builds the next PR while the user reads the last one. This implies overlapping review and preparation stages.  
**Decision:** The workflow is designed to pipeline work so that preparation of the next PR can proceed concurrently with user review of the current PR, subject to the product’s sequencing rules.  
**Consequences:** State management must support concurrent review and preparation phases across adjacent work items. Queueing, ordering, and dependency handling are required to avoid overlap conflicts.  
**Rejected alternatives:**  
- **Strictly serial workflow with no overlap:** Rejected because the product explicitly states that the next PR is built while the last one is being reviewed.  
- **Fully parallel independent PR generation without sequencing:** Rejected because work is still described as ordered and approval-gated.

## Package and distribute the shell as a macOS .app with drag-to-Applications installation and Sparkle auto-update
**Status:** Accepted  
**Context:** TRD-1 states that the shell owns installation and distribution, specifically including a `.app` bundle, drag-to-Applications installation, and Sparkle auto-update.  
**Decision:** Crafted is distributed as a native macOS `.app` bundle installed via drag-to-Applications and updated using Sparkle.  
**Consequences:** Release engineering, signing, packaging, and update flows must align with native macOS application distribution and Sparkle integration. Alternative distribution channels are not the primary supported model unless separately specified.  
**Rejected alternatives:**  
- **Package manager-only installation:** Rejected because TRD-1 specifies `.app` bundle distribution and drag-to-Applications install.  
- **Custom updater:** Rejected because Sparkle is explicitly named.  
- **Web-delivered application model:** Rejected because the shell is a packaged native macOS app.

## Use biometric gating, Keychain storage, and explicit session lifecycle management for identity
**Status:** Accepted  
**Context:** TRD-1 assigns identity and authentication responsibilities to the shell and explicitly lists biometric gate, Keychain secret storage, and session lifecycle as shell-owned concerns.  
**Decision:** User identity and secret protection in the shell use biometric gating where required, macOS Keychain for secret storage, and explicit session lifecycle management in the shell.  
**Consequences:** Authentication UX and secret access flows must integrate with macOS biometric and Keychain capabilities. Secrets must not be stored in ad hoc formats when Keychain-backed storage is required. Session semantics are a defined architectural concern rather than incidental implementation detail.  
**Rejected alternatives:**  
- **Plain file-based secret storage:** Rejected because Keychain storage is explicitly specified.  
- **No biometric gate:** Rejected because biometric gating is a named shell responsibility.  
- **Backend-owned session management:** Rejected because session lifecycle is assigned to the shell.