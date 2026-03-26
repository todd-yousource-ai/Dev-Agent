# DECISIONS.md

## Native macOS product with a two-process architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent. The repository guidance and product description consistently describe two distinct responsibilities: a Swift process for UI, authentication, secrets, and local system integration, and a Python process for intelligence, generation, consensus, and GitHub operations.  
**Decision:** The system is architected as two cooperating processes: a Swift shell and a Python backend. The Swift process owns the native macOS surface area, while the Python process owns planning, model orchestration, code generation, validation pipeline, and repository automation.  
**Consequences:** This enforces a hard boundary between platform/security concerns and intelligence/orchestration concerns. Features must be assigned to the owning process rather than duplicated. Cross-process contracts become a primary design surface.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because the documented product architecture explicitly separates native shell responsibilities from backend intelligence responsibilities.  
- **Python-first desktop shell:** Rejected because the shell is specified as Swift-native on macOS.  
- **More than two runtime processes:** Rejected because the documented architecture defines a two-process system.

## Swift shell owns UI, authentication, secrets, and local IPC endpoints
**Status:** Accepted  
**Context:** Repository instructions state that the Swift process owns UI, auth, Keychain, and XPC. The system description also assigns authentication and secrets handling to Swift rather than Python.  
**Decision:** All user interface, native macOS integration, authentication flows, credential custody, Keychain access, and local process-bridging responsibilities are implemented in the Swift shell.  
**Consequences:** Sensitive credentials are not handled as a primary concern by the Python backend. Native UI and local secret storage decisions must be implemented in Swift. Backend features requiring credentials must request them through controlled interfaces rather than directly sourcing or persisting them.  
**Rejected alternatives:**  
- **Backend-managed credentials:** Rejected because secrets ownership is explicitly assigned to the Swift side.  
- **Shared credential storage across both processes:** Rejected because custody is intentionally centralized in the shell.

## Python backend owns intelligence, consensus, generation, and GitHub operations
**Status:** Accepted  
**Context:** The product description and repository guidance assign consensus, pipeline, code generation, and GitHub integration to the Python backend. The README also frames the backend as the engine that plans, generates, validates, and opens pull requests.  
**Decision:** The Python backend is the sole owner of planning logic, provider orchestration, two-model consensus, self-correction, lint/fix loops, and GitHub repository automation.  
**Consequences:** Intelligence features are concentrated in one subsystem, simplifying model orchestration and pipeline control. GitHub automation is not split across runtimes. Backend changes must preserve the documented ownership boundary.  
**Rejected alternatives:**  
- **Swift performing model orchestration:** Rejected because intelligence responsibilities are explicitly assigned to Python.  
- **GitHub automation split between Swift and Python:** Rejected because GitHub operations are documented as backend-owned.

## Inter-process communication uses an authenticated Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The system description explicitly states that the Swift and Python processes communicate over an authenticated Unix socket using line-delimited JSON. This is a concrete protocol and transport choice, not an implementation suggestion.  
**Decision:** Cross-process communication is implemented via an authenticated local Unix socket, and messages are encoded as line-delimited JSON records.  
**Consequences:** Message framing, parsing, and error handling must conform to newline-delimited JSON semantics. Both processes must implement authentication and validation of the local channel. Alternative IPC methods may exist internally in the shell, but the shell-backend boundary must honor this transport contract.  
**Rejected alternatives:**  
- **HTTP or gRPC over localhost:** Rejected because the documented transport is an authenticated Unix socket with line-delimited JSON.  
- **Direct XPC between Swift and Python:** Rejected because the product description names Unix socket IPC for the inter-process protocol.  
- **Binary protocol:** Rejected because line-delimited JSON is explicitly specified.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** The system guidance explicitly states that neither process ever executes generated code. This is a core safety and security invariant.  
**Decision:** The product forbids runtime execution of model-generated code by both the Swift shell and the Python backend. Validation and automation must rely on non-execution mechanisms defined by the documented pipeline and repository tooling rather than arbitrary execution of generated outputs.  
**Consequences:** Any feature proposal that requires running generated code inside the agent is incompatible with the system design. Pipeline stages must be designed around static generation, repository modification, checks, and controlled external CI rather than in-process code execution.  
**Rejected alternatives:**  
- **Sandboxed local execution of generated code:** Rejected because the invariant is absolute: neither process executes generated code.  
- **Optional execution in developer mode:** Rejected because no exception is described in the provided documents.

## Technical Requirement Documents are the sole source of truth
**Status:** Accepted  
**Context:** Multiple repository documents state that the 16 TRDs in `forge-docs/` completely specify the system and that code must match them. Agents are instructed not to invent requirements.  
**Decision:** All significant implementation decisions, interfaces, error contracts, state machines, security controls, and testing expectations derive from the TRDs. Repository guidance and lessons learned inform interpretation, but they do not supersede TRD authority.  
**Consequences:** Changes require locating and following the owning TRD. Unspecified behavior should not be invented. Architectural drift from the TRDs is treated as invalid. Documentation and implementation must remain aligned to the TRD corpus.  
**Rejected alternatives:**  
- **Code-first evolution with docs updated later:** Rejected because the TRDs are declared authoritative in advance.  
- **README as equal authority:** Rejected because the documents explicitly identify the TRDs as the source of truth.

## Security controls are centralized under a dedicated security specification
**Status:** Accepted  
**Context:** Repository guidance states that TRD-11 governs all components and must be consulted for credentials, external content, generated code, and CI-related work. This implies a centralized, cross-cutting security authority.  
**Decision:** Security-sensitive behavior across every subsystem is constrained by a single governing security specification, and all subsystems must defer to it for credentials handling, external content processing, generated artifacts, and CI interactions.  
**Consequences:** Security decisions are not made independently per subsystem. Components that touch sensitive data or untrusted content must align to shared controls. Architectural convenience cannot override the centralized security model.  
**Rejected alternatives:**  
- **Per-component ad hoc security rules:** Rejected because security is explicitly governed centrally across all components.  
- **Backend-only security ownership:** Rejected because the security model applies to the entire system.

## The product is a directed build agent, not a chat or autocomplete tool
**Status:** Accepted  
**Context:** The product description explicitly distinguishes the system from chat interfaces, code autocomplete, and copilot-style workflows. It is framed instead as an autonomous build agent operating from specifications and intent.  
**Decision:** The user experience and system architecture are optimized for specification-driven software delivery rather than conversational assistance or inline suggestion UX.  
**Consequences:** Planning, decomposition, repository automation, review gating, and PR production are primary capabilities. Chat-centric interaction patterns or editor-completion paradigms are out of scope unless explicitly required by the TRDs.  
**Rejected alternatives:**  
- **General-purpose chat assistant:** Rejected because the product explicitly says it is not a chat interface.  
- **Autocomplete/copilot workflow:** Rejected because the product explicitly says it is not code autocomplete.

## Work begins from repository TRDs plus plain-language user intent
**Status:** Accepted  
**Context:** The README states that the user loads TRDs, states an intent, and the agent autonomously builds software from those specifications. This establishes the product’s input model.  
**Decision:** The system takes formal technical specifications and a natural-language intent as the governing inputs for planning and execution. Intent is interpreted within the boundaries set by the loaded specifications.  
**Consequences:** The agent is specification-constrained rather than open-ended. Planning and generation must remain anchored to repository documentation and user-declared scope. Unsupported behavior should not be inferred beyond the provided specifications.  
**Rejected alternatives:**  
- **Prompt-only coding workflow without specifications:** Rejected because the product is explicitly specification-driven.  
- **Freeform autonomous repo modification:** Rejected because work is bounded by TRDs and stated intent.

## Scope is assessed for confidence before implementation commitment
**Status:** Accepted  
**Context:** The product description states that the agent assesses its confidence in the requested scope before committing to it. This indicates an explicit gating phase before planning and generation proceed.  
**Decision:** The execution pipeline includes an upfront confidence assessment stage that evaluates whether the requested intent can be responsibly decomposed and implemented from the available specifications.  
**Consequences:** Not every user intent proceeds directly to implementation. The system requires a pre-commitment validation of scope clarity and feasibility, which constrains downstream planning and reduces speculative implementation.  
**Rejected alternatives:**  
- **Always generate immediately after receiving intent:** Rejected because the documented workflow includes an explicit confidence assessment first.  
- **Human-only scoping with no system assessment:** Rejected because the agent itself is specified to assess confidence.

## Planning is decomposed from intent into an ordered PRD plan
**Status:** Accepted  
**Context:** The README describes a pipeline in which the agent decomposes the user intent into an ordered PRD plan before decomposing further into pull requests. This implies a structured planning layer between request and code generation.  
**Decision:** The system uses a hierarchical planning model in which plain-language intent is first translated into an ordered product/requirements-level plan before implementation units are created.  
**Consequences:** Planning is explicit and staged rather than implicit inside generation. Ordering matters, and dependencies between implementation goals are represented before PR production begins.  
**Rejected alternatives:**  
- **Direct generation from intent to code changes:** Rejected because the documented workflow includes an intermediate ordered PRD plan.  
- **Unordered task list planning:** Rejected because the plan is explicitly ordered.

## Implementation work is decomposed into typed pull requests, one per logical unit
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests one per logical unit and decomposes each PRD into a sequence of typed pull requests. This defines both granularity and structure of delivery.  
**Decision:** Delivery occurs through a sequence of typed pull requests, each corresponding to a logical unit of work derived from the higher-level plan.  
**Consequences:** Large requests must be broken into reviewable units rather than landed as monolithic changes. Workflow, UI, and backend planning must preserve PR typing and sequencing.  
**Rejected alternatives:**  
- **Single large PR per user intent:** Rejected because the documented product behavior is one PR per logical unit.  
- **Unstructured commit stream without PR typing:** Rejected because PRs are explicitly typed.

## Pull requests are opened as drafts first and promoted later
**Status:** Accepted  
**Context:** The GitHub integration lessons learned document states that the agent opens every PR as a draft so CI can run before the operator sees it. It also documents the draft-to-ready lifecycle behavior required by GitHub.  
**Decision:** All agent-created pull requests begin in draft state and are only later marked ready for review when the workflow determines they should be operator-visible for review.  
**Consequences:** The PR lifecycle must account for draft-specific GitHub behavior. Automation and UI should assume draft-first semantics, including separate handling for readiness transitions.  
**Rejected alternatives:**  
- **Open PRs directly as ready for review:** Rejected because the documented pipeline intentionally uses draft PRs to allow CI to run first.  
- **Use local branches without opening PRs until finalization:** Rejected because the system is described as opening PRs during execution.

## Draft-to-ready transition uses GitHub GraphQL, not REST patching
**Status:** Accepted  
**Context:** The GitHub integration lessons learned document records a production failure showing that REST `PATCH /pulls/{number}` with `{"draft": false}` is silently ignored. The documented supported path is the GraphQL `markPullRequestReadyForReview` mutation.  
**Decision:** Promotion of a pull request from draft to ready-for-review is implemented exclusively through the GitHub GraphQL mutation `markPullRequestReadyForReview`. REST patching is not used for this state transition.  
**Consequences:** GitHub integration must include GraphQL support even if most other operations use REST. State transition logic must not rely on apparently successful REST responses for draft conversion.  
**Rejected alternatives:**  
- **REST PATCH with `draft: false`:** Rejected because GitHub ignores the field while returning success.  
- **Manual operator conversion as the normal path:** Rejected because the system is an automation pipeline and the documented fix is GraphQL-based automation.

## A two-model consensus engine is used, with Claude as arbiter
**Status:** Accepted  
**Context:** The README states that pull requests are produced using a two-model consensus engine with Claude and GPT-4o in parallel, and Claude arbitrates every result. This is a defining product behavior.  
**Decision:** Model generation and evaluation are performed by a dual-provider consensus system, and final arbitration authority is assigned to Claude.  
**Consequences:** Provider orchestration must support parallel generation and an arbitration phase. The system is not provider-neutral at the arbitration layer. Output quality and conflict resolution are shaped by Claude’s final adjudication role.  
**Rejected alternatives:**  
- **Single-model generation pipeline:** Rejected because the product explicitly specifies two-model consensus.  
- **Equal voting between models with no arbiter:** Rejected because Claude is explicitly designated as the arbiter.  
- **GPT-4o as final arbiter:** Rejected because arbitration is explicitly assigned to Claude.

## Generation is followed by self-correction, lint gating, and iterative fix loops
**Status:** Accepted  
**Context:** The README describes a post-generation validation pipeline including a self-correction pass, a lint gate, and an iterative fix loop. This indicates that generation alone is not considered sufficient for delivery.  
**Decision:** The implementation pipeline includes explicit validation and remediation stages after initial code generation: self-correction, lint-based quality gating, and repeated fix iterations as needed.  
**Consequences:** The backend must support multi-stage refinement rather than one-shot output. Delivery time and orchestration complexity increase, but code quality and conformance are treated as first-class outcomes.  
**Rejected alternatives:**  
- **Single-pass generation only:** Rejected because the documented workflow includes multiple corrective stages.  
- **Human-only correction after PR creation:** Rejected because the system itself performs self-correction and fix loops.

## Review and merge remain operator-gated
**Status:** Accepted  
**Context:** The README states, “You gate, review, and merge.” This indicates that the human operator remains the authority for acceptance and merge decisions even while the agent continues building subsequent work.  
**Decision:** The agent automates planning, implementation, and PR creation, but final review and merge authority stays with the human operator.  
**Consequences:** The system must preserve a human approval boundary before integration. Full autonomous merge is out of scope unless separately specified. UX and workflow should support operator review rather than bypass it.  
**Rejected alternatives:**  
- **Fully autonomous merge pipeline:** Rejected because the documented workflow explicitly reserves gating, review, and merge for the operator.  
- **No human review step:** Rejected for the same reason.

## The agent pipelines work by building the next PR while the previous one is under review
**Status:** Accepted  
**Context:** The product description says the agent builds the next PR while the operator reads the last one. This indicates intentional overlap between human review and machine implementation.  
**Decision:** The workflow is designed as a pipelined sequence of logically ordered PRs, allowing the system to continue preparing subsequent units while earlier ones await operator review.  
**Consequences:** Planning must preserve PR dependencies and sequencing so concurrent preparation does not violate logical order. The system is optimized for throughput rather than strictly serial human-in-the-loop execution.  
**Rejected alternatives:**  
- **Strictly sequential stop-and-wait workflow:** Rejected because the documented behavior explicitly overlaps review and subsequent build work.  
- **Unbounded parallel PR generation without order:** Rejected because the product emphasizes ordered decomposition and logical units.

## Versioned operational behavior is tied to the documented v38.x product line
**Status:** Accepted  
**Context:** Repository guidance identifies a current version in the 38.x line, and the GitHub lessons learned document says the fixes are implemented in v38.x. This indicates that the documented architecture and operational lessons are anchored to that release family.  
**Decision:** Architectural and integration behaviors described in the provided documents are treated as current accepted decisions for the v38.x system line.  
**Consequences:** Implementations and future changes should assume these behaviors are not provisional. Any deviation should be treated as an intentional architecture change rather than an incidental refactor.  
**Rejected alternatives:**  
- **Treat documented behavior as historical only:** Rejected because the documents describe current product identity and implemented fixes.