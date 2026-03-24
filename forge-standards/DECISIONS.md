# DECISIONS.md

## Native macOS shell with Python backend two-process architecture
**Status:** Accepted  
**Context:** The product is specified as a native macOS AI coding agent with clear separation of responsibilities between user-facing system integration and AI/code-generation orchestration. The repository guidance and product description both define a two-process architecture, and TRD-1 establishes the macOS Application Shell as foundational.  
**Decision:** The system is split into two cooperating processes: a native Swift/SwiftUI macOS shell and a bundled Python 3.12 backend. The Swift shell owns UI, installation, authentication, Keychain access, session lifecycle, and local orchestration concerns. The Python backend owns intelligence, generation, consensus, pipeline execution, and GitHub operations.  
**Consequences:** This constrains subsystem boundaries, ownership of secrets, packaging, and runtime behavior. Features must be assigned to the correct process rather than implemented opportunistically. Cross-process integration becomes a first-class interface concern.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because the product definition explicitly separates native shell responsibilities from backend intelligence responsibilities.  
- **All-Swift implementation:** Rejected because the backend is specified as Python 3.12 bundled with the app.  
- **Web or Electron shell:** Rejected because the shell is specified as a native macOS Swift/SwiftUI application.

## Swift shell is the sole owner of authentication and secrets
**Status:** Accepted  
**Context:** The architecture description in repository guidance assigns authentication and secrets to the Swift process, and TRD-1 defines identity, authentication, biometric gating, Keychain storage, and session lifecycle as shell responsibilities.  
**Decision:** All user authentication, biometric gating, session lifecycle, and secret storage are handled exclusively by the Swift shell, using native macOS facilities such as Keychain. The Python backend does not own or persist primary user secrets.  
**Consequences:** Secret-handling code must remain in the shell. Backend interfaces must consume only the minimum authenticated context required. This reduces secret exposure in the intelligence pipeline and constrains implementation of provider and GitHub access flows.  
**Rejected alternatives:**  
- **Backend-managed credentials:** Rejected because shell ownership of auth and Keychain is explicitly specified.  
- **Shared secret management between Swift and Python:** Rejected because it weakens the clear trust boundary established by the architecture.

## Inter-process communication uses an authenticated Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** Repository instructions explicitly define process communication as an authenticated Unix socket using line-delimited JSON. The two-process design requires a stable, constrained, implementation-independent contract between Swift and Python subsystems.  
**Decision:** The Swift shell and Python backend communicate only over an authenticated Unix domain socket, and message framing is line-delimited JSON.  
**Consequences:** All cross-process interfaces must be serialized through this protocol. Message design, authentication, error contracts, and observability must fit this transport. Alternate direct embedding or ad hoc IPC patterns are out of scope.  
**Rejected alternatives:**  
- **XPC as the only runtime transport:** Rejected because the repository-level architecture explicitly specifies authenticated Unix socket communication for the two processes.  
- **HTTP/REST localhost API:** Rejected because it adds unnecessary surface area and does not match the specified transport.  
- **Binary custom protocol:** Rejected because line-delimited JSON is the specified message format.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** Repository guidance states that neither process ever executes generated code. This is reinforced by the security posture referenced in the agent instructions, especially for generated code handling.  
**Decision:** The product may generate, analyze, lint, test, patch, and prepare code changes within the defined pipeline, but neither the Swift shell nor the Python backend executes generated code directly as an untrusted runtime payload.  
**Consequences:** System design must preserve a strict boundary between generation/orchestration and code execution. Any validation or CI activity must occur through controlled repository and pipeline mechanisms rather than arbitrary direct execution of generated artifacts by the agent itself.  
**Rejected alternatives:**  
- **Execute generated code locally for rapid validation:** Rejected due to explicit prohibition.  
- **Sandboxed execution of generated code:** Rejected because the governing requirement is categorical: generated code is not executed by either process.

## TRDs are the authoritative source of product behavior
**Status:** Accepted  
**Context:** Multiple repository documents state that the 16 TRDs in `forge-docs/` fully specify interfaces, error contracts, state machines, security controls, and performance requirements, and that code must match them.  
**Decision:** Architectural, behavioral, interface, testing, and security decisions are derived from the TRDs, which serve as the source of truth across all subsystems. Implementation must not invent requirements outside the TRDs.  
**Consequences:** All significant design work must trace back to a TRD. Changes require consultation of the owning TRD and relevant cross-cutting TRDs, especially security. This limits undocumented feature drift and ad hoc API design.  
**Rejected alternatives:**  
- **Code-first evolution with documentation catch-up:** Rejected because TRDs are declared authoritative.  
- **README or agent instruction files as primary specification:** Rejected because those files direct implementers back to the TRDs rather than replacing them.

## Security requirements are governed centrally by TRD-11 across all components
**Status:** Accepted  
**Context:** Repository guidance states that TRD-11 governs all components for security-relevant work and must be consulted when changes touch credentials, external content, generated code, or CI.  
**Decision:** Security is treated as a cross-cutting architectural authority under TRD-11, and every subsystem must conform to its requirements when handling credentials, external inputs, generated artifacts, or continuous integration interactions.  
**Consequences:** Security-sensitive implementation cannot be designed in isolation within subsystem TRDs alone. Reviews and changes must include TRD-11 alignment. This centralizes security posture and constrains local subsystem optimizations that would violate shared controls.  
**Rejected alternatives:**  
- **Independent per-subsystem security rules:** Rejected because security governance is explicitly centralized.  
- **Best-effort security interpretation by developers:** Rejected because the repository requires direct consultation of TRD-11.

## The product is a directed build agent, not a chat or autocomplete interface
**Status:** Accepted  
**Context:** The product README explicitly states what the product is not and defines it as a directed build agent that transforms specifications and user intent into sequenced GitHub pull requests.  
**Decision:** The system is designed around autonomous, specification-driven software delivery workflows rather than conversational chat interaction or inline code completion. Its primary unit of output is structured pull requests derived from TRDs, intent, planning, generation, validation, and review gates.  
**Consequences:** UX, orchestration, and backend behaviors must optimize for planning, decomposition, confidence assessment, PR generation, and review loops rather than open-ended conversational experiences. Feature requests that shift the product toward a copilot/chat paradigm are outside the intended architecture.  
**Rejected alternatives:**  
- **General chat assistant UX:** Rejected because the README explicitly says the product is not a chat interface.  
- **IDE autocomplete/copilot behavior:** Rejected because the README explicitly says it is not code autocomplete or a copilot.

## Work is decomposed into ordered PRD plans and typed pull requests
**Status:** Accepted  
**Context:** The product flow in the README defines a staged process: assess confidence, decompose intent into an ordered PRD plan, decompose each PRD into a sequence of typed pull requests, then generate and validate implementation.  
**Decision:** The core orchestration model breaks user intent into an ordered planning hierarchy: intent → PRD plan → typed pull requests. Implementation proceeds one logical unit per pull request.  
**Consequences:** Planning artifacts and execution must preserve ordering and typing of work units. Pipeline, UI, and GitHub automation must all support sequential, reviewable PR-based delivery rather than monolithic code drops.  
**Rejected alternatives:**  
- **Single large pull request per intent:** Rejected because the product explicitly opens one PR per logical unit.  
- **Unstructured task execution without PRD planning:** Rejected because ordered PRD decomposition is part of the defined workflow.

## Two-model consensus generation with Claude arbitration is the generation strategy
**Status:** Accepted  
**Context:** The product README specifies that pull requests are produced using a two-model consensus engine involving Claude and GPT-4o, with Claude arbitrating every result. AGENTS and CLAUDE guidance also reference consensus ownership in the Python backend.  
**Decision:** Code generation and related intelligence tasks use two LLM providers in parallel with a consensus/arbitration stage, and Claude serves as the final arbiter of results.  
**Consequences:** Provider abstraction, backend orchestration, error handling, and output evaluation must support parallel multi-model generation and arbitration. Single-provider generation does not satisfy the intended architecture.  
**Rejected alternatives:**  
- **Single-model generation pipeline:** Rejected because the product is explicitly described as using two-model consensus.  
- **Human-only arbitration:** Rejected because arbitration is assigned to Claude in the product definition.

## Validation pipeline includes self-correction, lint gate, iterative fix loop, CI, and draft PR creation
**Status:** Accepted  
**Context:** The README defines the post-generation workflow as including self-correction, a lint gate, an iterative fix loop, CI execution, and opening a draft PR for review.  
**Decision:** Generated changes must pass through a structured validation and remediation pipeline before being surfaced as draft pull requests. The pipeline includes self-correction, linting, iterative fixing, and CI execution as standard stages.  
**Consequences:** The backend pipeline is not limited to raw generation; it must implement quality gates and remediation loops. GitHub integration and UI state must reflect draft PR lifecycle rather than direct merge-ready output.  
**Rejected alternatives:**  
- **Generate and immediately open PRs without validation:** Rejected because quality gates are explicitly part of the workflow.  
- **Manual-only correction after generation:** Rejected because self-correction and iterative fix loops are specified system behaviors.

## User review and approval are required gate points before progression
**Status:** Accepted  
**Context:** The README describes a review model in which the agent opens draft PRs, the user gates, reviews, and merges them, and the agent continues while the user reviews the previous output.  
**Decision:** The system uses a human-gated delivery model in which generated work is surfaced as draft pull requests for review and approval rather than being autonomously merged without user oversight.  
**Consequences:** Product flow, UI, and backend state management must model reviewable draft states and await explicit user decisions. Full autonomous merge behavior is outside the defined delivery model.  
**Rejected alternatives:**  
- **Auto-merge upon CI success:** Rejected because user review and gating are central to the product definition.  
- **No draft phase:** Rejected because the README explicitly calls for opening draft PRs.

## The macOS application shell is the foundational subsystem for dependent TRDs
**Status:** Accepted  
**Context:** TRD-1 identifies itself as a foundational TRD and lists TRD-2, TRD-3, TRD-4, TRD-5, and TRD-8 as depending on it. It also defines shell ownership over installation, distribution, authentication, module architecture, and orchestration concerns.  
**Decision:** The macOS Application Shell defined in TRD-1 is treated as the foundational platform layer upon which multiple higher-level subsystems depend. Its contracts and architectural boundaries govern downstream subsystem integration.  
**Consequences:** Dependent subsystem implementations must conform to shell-defined packaging, lifecycle, and integration contracts. Changes to shell architecture have broad downstream impact and require careful compatibility consideration.  
**Rejected alternatives:**  
- **Backend-first architecture with minimal shell:** Rejected because TRD-1 is explicitly foundational and assigns substantial responsibility to the shell.  
- **Independent subsystem shells:** Rejected because dependent TRDs reference a single macOS application shell foundation.

## Distribution is via native macOS app bundle with drag-to-Applications installation and Sparkle auto-update
**Status:** Accepted  
**Context:** TRD-1 explicitly lists installation and distribution responsibilities of the shell, including `.app` bundle packaging, drag-to-Applications installation, and Sparkle auto-update.  
**Decision:** The product is distributed as a native macOS `.app` bundle, installed through standard drag-to-Applications flow, and updated via Sparkle.  
**Consequences:** Packaging, signing, update delivery, and release engineering must align with native macOS application distribution patterns and Sparkle integration. Non-native or store-dependent distribution models are not the primary target defined here.  
**Rejected alternatives:**  
- **Mac App Store-only distribution:** Rejected because Sparkle-based auto-update and drag-to-Applications installation are explicitly specified.  
- **Command-line distribution only:** Rejected because the shell is a native macOS app bundle.

## Minimum supported platform is macOS 13.0 Ventura with Swift 5.9+ and bundled Python 3.12
**Status:** Accepted  
**Context:** TRD-1 specifies minimum macOS version and implementation languages/versions for the shell and backend runtime.  
**Decision:** The supported baseline platform is macOS 13.0 Ventura, implemented with Swift 5.9+ and SwiftUI in the shell and a bundled Python 3.12 runtime for the backend.  
**Consequences:** All implementation choices, dependencies, and runtime features must remain compatible with Ventura and the specified language/runtime versions. Backward compatibility below this version is not required by the current architecture.  
**Rejected alternatives:**  
- **Support older macOS releases by default:** Rejected because TRD-1 sets Ventura as the minimum.  
- **Use system Python instead of bundled Python:** Rejected because the backend runtime is specified as bundled Python 3.12.