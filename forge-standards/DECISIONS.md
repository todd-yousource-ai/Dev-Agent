# DECISIONS.md

## Native macOS shell with bundled Python backend
**Status:** Accepted  
**Context:** The product is specified as a native macOS AI coding agent, not a web or cross-platform application. The TRDs define a two-process architecture with Swift responsible for UI, authentication, secure storage, packaging, and orchestration, and Python responsible for intelligence, generation, consensus, and GitHub operations. TRD-1 is foundational and all other major subsystems depend on it.  
**Decision:** Build Crafted as a native macOS application shell in Swift 5.9+ and SwiftUI, bundling a Python 3.12 backend as a separate process. The shell owns installation, distribution, authentication, Keychain access, session lifecycle, and process orchestration. The backend owns model orchestration, planning, code generation, validation, and repository automation.  
**Consequences:** The product is intentionally macOS-specific with a minimum version of macOS 13.0. UI and system integrations must be implemented in Swift/SwiftUI. Backend intelligence must be isolated in Python. Interfaces between the two processes become critical contracts and must be stable, authenticated, and versioned by TRD-defined behavior.  
**Rejected alternatives:** A single-process architecture was rejected because the TRDs separate system-trusted responsibilities from intelligence and generation responsibilities. A web app or Electron-style shell was rejected because the TRDs require a native macOS shell with platform security integrations. A pure Python app was rejected because authentication, Keychain, UI, and native app lifecycle are assigned to the Swift shell.

## Two-process trust boundary
**Status:** Accepted  
**Context:** Both AGENTS.md and CLAUDE.md define the architecture as two processes with explicit ownership boundaries. The shell is trusted for identity and secrets; the backend is responsible for intelligence and GitHub workflows. The TRDs make this split foundational to security and subsystem ownership.  
**Decision:** Enforce a strict two-process architecture with the Swift shell and Python backend as separate runtime processes with a clear trust boundary. Secrets, auth state, and OS-integrated capabilities remain in the shell. Model execution, planning, and code-generation workflows remain in the backend.  
**Consequences:** Cross-process communication must be explicit and authenticated. Backend code cannot directly access Keychain or shell-owned state. Shell code must not absorb generation logic. The architecture favors least privilege and containment but increases integration complexity and IPC contract management.  
**Rejected alternatives:** Sharing all responsibilities in one process was rejected because it would collapse the security boundary defined by the TRDs. Allowing the backend direct access to secrets was rejected because secret handling belongs to the shell. Moving intelligence into Swift was rejected because the TRDs assign that responsibility to Python.

## Authenticated Unix socket with line-delimited JSON for IPC
**Status:** Accepted  
**Context:** CLAUDE.md explicitly states that the two processes communicate via an authenticated Unix socket with line-delimited JSON. This is a core interface decision implied by the architecture and needed for process isolation while preserving structured communication.  
**Decision:** Use an authenticated Unix domain socket as the sole shell-backend IPC mechanism, with line-delimited JSON messages as the framing and payload format.  
**Consequences:** All inter-process interfaces must be representable as JSON message contracts. Transport security and peer authentication are mandatory. Message framing, schema evolution, error reporting, and request/response semantics must be designed around newline-delimited JSON. This limits transport choices but simplifies debugging, logging, and deterministic parsing.  
**Rejected alternatives:** XPC-only integration was rejected because the TRDs and agent guidance explicitly define authenticated Unix sockets for shell-backend communication. HTTP or gRPC was rejected as unnecessary complexity and a poorer fit for local private IPC. Binary custom protocols were rejected in favor of line-delimited JSON for transparency and simpler contract handling.

## Swift shell owns UI, authentication, Keychain, and orchestration
**Status:** Accepted  
**Context:** TRD-1 assigns the shell ownership of installation, updates, identity, biometric gate, Keychain secret storage, session lifecycle, module architecture, and orchestration. Repository guidance repeats that the Swift process owns UI, authentication, and secrets.  
**Decision:** Centralize all user interface, app lifecycle, authentication flow, Keychain access, and backend orchestration in the Swift shell. The shell is the only component allowed to present native UI and interact with Apple security primitives.  
**Consequences:** Swift modules become the authoritative implementation point for user-facing state and protected credentials. Backend features must request shell mediation for any secret- or identity-related operation. This preserves native UX and security guarantees but requires careful shell APIs for backend-triggered flows.  
**Rejected alternatives:** Putting authentication into the backend was rejected because backend code is outside the trusted shell domain. Duplicating UI or session logic across both processes was rejected because it would fragment ownership and create inconsistent lifecycle behavior.

## Python backend owns intelligence, generation, consensus, and GitHub operations
**Status:** Accepted  
**Context:** The repository identity and product description assign consensus, generation pipeline, and GitHub operations to the Python backend. The README describes a workflow where the agent plans work, generates code using multiple models, validates outputs, runs CI, and opens draft PRs.  
**Decision:** Place all non-UI agent intelligence in the Python backend, including intent assessment, PRD planning, typed pull-request decomposition, provider orchestration, consensus, self-correction, lint/fix loops, CI workflow coordination, and GitHub pull-request operations.  
**Consequences:** The backend becomes the implementation center for agent behavior and repository automation. Python interfaces must expose deterministic contracts to the shell for status, errors, progress, review gates, and results. Operational failures in provider calls, repository state, and CI must be normalized in backend error contracts rather than leaking ad hoc provider details into the shell.  
**Rejected alternatives:** Implementing generation logic in the shell was rejected because the TRDs place intelligence in Python. Delegating GitHub operations to the shell was rejected because repository automation is part of the backend pipeline responsibility.

## Neither process executes generated code
**Status:** Accepted  
**Context:** CLAUDE.md explicitly states that neither process ever executes generated code. The security model in the repository also directs all components to comply with TRD-11 for generated code and external content handling.  
**Decision:** Prohibit execution of generated code by both the Swift shell and the Python backend. Generated artifacts may be written, linted, tested, and validated only through TRD-governed controlled workflows, but not executed as arbitrary code by the application itself outside those defined gates.  
**Consequences:** The system must treat generated output as untrusted content. Features that would run scripts, evaluate generated snippets, or dynamically load generated modules are out of scope. Validation pipelines must rely on repository tooling and controlled CI/test mechanisms rather than in-process execution of arbitrary generated output.  
**Rejected alternatives:** Running generated code locally for faster iteration was rejected because it violates the explicit repository rule and weakens the security model. Dynamic plugin-style loading of generated artifacts was rejected for the same reason.

## TRDs are the sole source of truth for implementation
**Status:** Accepted  
**Context:** AGENTS.md and CLAUDE.md state that the 16 TRDs in `forge-docs/` fully specify the product and that code must match them. Contributors are instructed not to invent requirements and to read the owning TRD before making changes.  
**Decision:** Treat the TRDs as the authoritative specification for architecture, interfaces, state machines, security controls, error contracts, testing requirements, and performance expectations across all subsystems. Implementation decisions must be derived from the relevant TRD rather than inferred from convenience or undocumented precedent.  
**Consequences:** Engineering changes require mapping work to the owning TRD. Local optimizations that contradict the TRDs are not allowed. Documentation, tests, and code must stay aligned with TRD-defined contracts. Ambiguity resolution requires consulting the relevant TRD hierarchy rather than inventing behavior.  
**Rejected alternatives:** Using code as the primary source of truth was rejected because the repository explicitly states the TRDs govern implementation. Ad hoc feature interpretation by individual contributors was rejected because it would undermine consistency across subsystems.

## Security governance centralized under TRD-11
**Status:** Accepted  
**Context:** AGENTS.md explicitly states that TRD-11 governs all components for security-relevant work and must be read before touching credentials, external content, generated code, or CI. This establishes a cross-cutting security authority over subsystem-specific TRDs.  
**Decision:** Apply TRD-11 as the mandatory security overlay for every subsystem, with special precedence for credentials, external content ingestion, generated artifacts, and CI-related behavior. Component TRDs define local behavior, but security-sensitive implementation must conform to TRD-11.  
**Consequences:** Security decisions cannot be made solely inside subsystem boundaries. Changes touching secrets, content trust, code generation, or automation pipelines require review against the security TRD. This may constrain implementation freedom in otherwise unrelated modules, but it enforces a single consistent security model across the product.  
**Rejected alternatives:** Letting each subsystem define its own independent security rules was rejected because the repository explicitly centralizes security governance in TRD-11. Deferring security decisions to implementation time was rejected because the TRDs require predefined controls.

## Distribution as a macOS app bundle with drag-to-Applications install and Sparkle updates
**Status:** Accepted  
**Context:** TRD-1 assigns installation and distribution responsibilities to the shell and explicitly lists `.app` bundle packaging, drag-to-Applications installation, and Sparkle auto-update.  
**Decision:** Ship Crafted as a native `.app` bundle for macOS, installed via standard drag-to-Applications flow and updated using Sparkle.  
**Consequences:** Release engineering must produce signed, distributable macOS bundles compatible with Sparkle update mechanics. The shell must support app lifecycle requirements associated with native installation and update behavior. Packaging and update infrastructure are constrained to macOS-native distribution patterns rather than browser delivery or package-manager-first distribution.  
**Rejected alternatives:** Browser-hosted delivery was rejected because the shell is a native macOS application. Homebrew-only or Python-package distribution was rejected because TRD-1 specifies an app bundle and Sparkle-based updates.

## Biometric gate and Keychain-backed secret storage
**Status:** Accepted  
**Context:** TRD-1 explicitly assigns biometric gate, Keychain secret storage, and session lifecycle to the shell under identity and authentication responsibilities.  
**Decision:** Use macOS biometric authentication and Keychain-backed secure storage for identity gating and secret persistence, with the shell owning the session lifecycle.  
**Consequences:** Secret management must use platform-native secure storage rather than custom encryption stores managed by the backend. Session restoration, unlock flows, and authentication prompts must be integrated into shell state management. Backend operations that require credentials must obtain them indirectly through shell-approved mechanisms.  
**Rejected alternatives:** Storing secrets in files or environment variables was rejected because secure storage is explicitly assigned to Keychain. Backend-managed credential stores were rejected because secret ownership belongs to the shell. Password-only gating without native biometric support was rejected because the TRD specifies a biometric gate.

## Directed build agent, not chat or autocomplete
**Status:** Accepted  
**Context:** The README explicitly states that Crafted is not a chat interface, not code autocomplete, and not a copilot. It is a directed build agent that consumes specifications and intent, plans work, produces PRs, and advances iteratively through user-gated review.  
**Decision:** Design the product around goal-directed software delivery workflows rather than open-ended conversation or inline suggestion UX. The primary user flow is repository + TRD loading, intent submission, confidence assessment, structured planning, PR generation, review gating, and iterative continuation.  
**Consequences:** UI, APIs, and system behavior must optimize for planning, status visibility, review, and PR lifecycle management instead of chat transcript management or editor-inline interactions. Feature proposals that reframe the product as a conversational assistant are misaligned unless explicitly specified by a TRD.  
**Rejected alternatives:** Building a generic chatbot interface was rejected because the README explicitly says the product is not a chat interface. Building editor autocomplete was rejected because the product is not a copilot and the TRDs define a PR-oriented autonomous workflow.

## Two-model consensus with Claude and GPT-4o, with Claude arbitration
**Status:** Accepted  
**Context:** The README defines the generation model as a two-model consensus engine using Claude and GPT-4o in parallel, with Claude arbitrating every result. The architecture also identifies consensus as a backend responsibility.  
**Decision:** Implement code generation and related intelligence tasks using parallel outputs from Claude and GPT-4o, with Claude serving as the arbitration authority for final result selection or judgment within the consensus engine.  
**Consequences:** Provider abstraction, prompt routing, result normalization, and arbitration logic must support at least these two providers and preserve the arbitration role of Claude. The backend must handle disagreement, failure, and comparison workflows as first-class concerns. Single-provider shortcuts are inconsistent with the defined product behavior unless specifically permitted by a TRD.  
**Rejected alternatives:** Single-model generation was rejected because the product description explicitly defines a two-model consensus engine. Non-Claude arbitration was rejected because the README states Claude arbitrates every result.

## Planning pipeline from intent to PRD to typed pull requests
**Status:** Accepted  
**Context:** The README describes a structured workflow: the user provides TRDs and plain-language intent; the agent assesses confidence in scope, decomposes the intent into an ordered PRD plan, then decomposes each PRD into a sequence of typed pull requests.  
**Decision:** Implement a staged planning pipeline in the backend: intent intake, scope-confidence assessment, ordered PRD planning, and typed pull-request decomposition before implementation generation begins.  
**Consequences:** Planning is a first-class subsystem rather than an informal precursor to generation. The system must preserve intermediate planning artifacts and expose them to the shell as meaningful states. Downstream generation depends on typed PR outputs, so ad hoc direct-to-code behavior is constrained.  
**Rejected alternatives:** Immediate code generation from user intent was rejected because the product workflow requires confidence assessment and structured decomposition. A single undifferentiated task queue was rejected because the README specifies ordered PRD and typed PR stages.

## Draft-PR-based delivery with human review gating
**Status:** Accepted  
**Context:** The README specifies that the agent executes CI, opens a draft PR for review, and that the user approves and merges while the agent prepares the next PR. This establishes a human-gated autonomous delivery model.  
**Decision:** Deliver implementation units as draft GitHub pull requests, one per logical unit, with human review and approval as the control point before merge and continuation.  
**Consequences:** GitHub PR creation, branch management, CI attachment, review state tracking, and sequencing across logical units are mandatory backend capabilities. The shell must expose review-oriented progress and status rather than only raw generation logs. Full autonomous merge without human gate is out of scope unless another TRD explicitly authorizes it.  
**Rejected alternatives:** Direct commits to main were rejected because the product is PR-driven and human-gated. Bundling all work into one monolithic PR was rejected because the README calls for one PR per logical unit.

## Validation pipeline includes self-correction, lint gate, iterative fix loop, and CI
**Status:** Accepted  
**Context:** The README describes a fixed downstream validation process after generation: self-correction pass, lint gate, iterative fix loop, CI execution, and then PR opening. This is part of the promised product behavior.  
**Decision:** Require generated work to pass through a backend validation pipeline consisting of self-correction, linting, iterative remediation, and CI execution before a draft PR is opened.  
**Consequences:** Generation completion does not imply deliverability. The backend must model and report validation stages, retry behavior, and failure modes. Tooling integration for lint/test/CI becomes part of the core system rather than optional enhancement. This may increase execution time but improves PR quality and aligns with the specified workflow.  
**Rejected alternatives:** Opening PRs immediately after first-pass generation was rejected because the product explicitly includes correction and validation stages. Manual-only validation was rejected because the README specifies automated gates before PR creation.

## One pull request per logical unit of work
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests “one per logical unit.” This is a delivery granularity decision that shapes planning and sequencing.  
**Decision:** Decompose implementation into logically scoped pull requests and deliver them individually rather than aggregating unrelated work into larger batches.  
**Consequences:** Planning logic must produce coherent units with bounded scope and dependency ordering. GitHub workflows, branch naming, review state, and progress tracking must all operate at the logical-unit level. This improves reviewability and incremental merge safety but requires more sophisticated decomposition logic.  
**Rejected alternatives:** A single all-encompassing PR per user intent was rejected because the product specifies one PR per logical unit. Extremely fine-grained commit-level PR fragmentation was also rejected implicitly because the unit is logical work, not arbitrary atomic changes.

## SwiftUI as the shell UI technology
**Status:** Accepted  
**Context:** TRD-1 specifies Swift 5.9+ and SwiftUI for the macOS application shell. The repository guidance also maps SwiftUI views, cards, and panels to a dedicated TRD, reinforcing the UI technology direction.  
**Decision:** Implement the shell user interface using SwiftUI within the native Swift macOS application.  
**Consequences:** UI architecture, state propagation, navigation, and component composition must align with SwiftUI patterns. AppKit may still be used only where necessary for macOS integration, but SwiftUI is the primary UI framework. This narrows UI implementation choices but aligns with the TRD-defined native architecture.  
**Rejected alternatives:** AppKit-first UI was rejected because TRD-1 specifies SwiftUI. Cross-platform UI frameworks were rejected because the product is a native macOS shell defined in Swift and SwiftUI.