# DECISIONS.md

## Native macOS two-process architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent with clear separation between user-facing platform responsibilities and AI/backend responsibilities. The repository identity and implementation guidance state that the Swift process owns UI, authentication, Keychain, and XPC-adjacent shell duties, while the Python process owns consensus, generation, pipeline, and GitHub operations.  
**Decision:** The system is split into two cooperating processes: a Swift macOS shell and a Python backend. The Swift shell is responsible for native UX, authentication, and secret storage. The Python backend is responsible for planning, model orchestration, code generation, validation pipeline, and GitHub integration.  
**Consequences:** This enforces strict subsystem boundaries, language separation by responsibility, and explicit inter-process contracts. Platform-sensitive concerns remain in Swift; AI and automation concerns remain in Python. Cross-cutting changes must respect process ownership.  
**Rejected alternatives:** A single-process monolith was rejected because it would blur security and responsibility boundaries. A fully Swift or fully Python implementation was rejected because it would weaken either native macOS integration or backend orchestration flexibility.

## Authenticated local IPC over Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The Swift and Python processes must communicate reliably and securely. The implementation guidance explicitly defines authenticated Unix-socket communication using line-delimited JSON.  
**Decision:** Inter-process communication uses an authenticated Unix domain socket protocol with line-delimited JSON messages.  
**Consequences:** All cross-process interfaces must be serializable into line-delimited JSON and designed for local authenticated exchange. This constrains message framing, schema evolution, and testing of IPC boundaries. It also reinforces the local-only trust model between shell and backend.  
**Rejected alternatives:** Ad hoc stdin/stdout piping was rejected due to weaker session structure and scalability. HTTP-based localhost APIs were rejected as unnecessarily broad for a local two-process architecture. Binary custom protocols were rejected because the documented contract specifies JSON.

## Swift shell owns UI, authentication, and secrets
**Status:** Accepted  
**Context:** The repository guidance assigns native user interaction and secret-handling responsibilities to the Swift shell. The architecture depends on keeping platform-integrated functions in the native process.  
**Decision:** The Swift process is the sole owner of the UI, user authentication flows, and secure secret storage through macOS facilities such as Keychain.  
**Consequences:** Python services cannot directly own user credentials or present native authentication UI. Any feature requiring secrets or user interaction must route through the shell. This reduces secret sprawl and centralizes platform trust decisions.  
**Rejected alternatives:** Allowing the Python backend to store or manage secrets directly was rejected because it violates the documented ownership model. Duplicating auth logic across both processes was rejected due to inconsistency and increased attack surface.

## Python backend owns intelligence, generation, pipeline, and GitHub operations
**Status:** Accepted  
**Context:** The backend is described as the intelligence layer of the product, including consensus, implementation generation, validation, and repository automation.  
**Decision:** The Python process owns intent assessment, PRD and PR decomposition, model orchestration, self-correction, lint and fix loops, and GitHub API interactions.  
**Consequences:** Planning and code-production logic must remain backend-centric. GitHub automation is not implemented in the shell. Backend contracts must be rich enough to accept operator intent and return status, plans, and PR outcomes.  
**Rejected alternatives:** Performing GitHub operations from the Swift shell was rejected because repository automation is explicitly assigned to the backend. Splitting planning logic across both processes was rejected because it would complicate authority and state management.

## TRDs are the sole source of truth for system behavior
**Status:** Accepted  
**Context:** Multiple repository documents state that the 16 TRDs in `forge-docs/` completely specify the product and that code must match them. The user request also requires deriving decisions entirely from provided TRD-related materials.  
**Decision:** All significant architecture, interface, state machine, error contract, security, testing, and performance decisions are governed by the TRDs, and implementation must conform to them rather than inventing requirements.  
**Consequences:** Engineers and agents must consult the relevant TRD before changing a subsystem. Unspecified behavior should not be assumed. Documentation and implementation drift is treated as a defect.  
**Rejected alternatives:** Deriving requirements from implementation convenience or agent inference was rejected because the repository explicitly forbids inventing requirements. Treating README-level summaries as authoritative over TRDs was also rejected.

## Security decisions are centrally governed by TRD-11
**Status:** Accepted  
**Context:** The repository guidance explicitly states that TRD-11 governs all components for security-relevant work, especially where credentials, external content, generated code, or CI are involved.  
**Decision:** Security-sensitive behavior across all subsystems must be reviewed and constrained under the security model defined by TRD-11.  
**Consequences:** Changes touching credentials, external inputs, code generation outputs, or CI integration require explicit alignment with the security TRD. Security is treated as a cross-cutting architectural authority, not a local implementation detail.  
**Rejected alternatives:** Allowing each subsystem to define independent security rules was rejected because the repository specifies a single governing security model. Treating security review as optional for non-auth code paths was rejected because generated code and CI are explicitly in scope.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** The architecture guidance explicitly states that neither the Swift process nor the Python process ever executes generated code. This is a foundational safety constraint for an AI coding agent.  
**Decision:** The system may generate, validate, lint, test, and prepare code changes, but neither process executes generated code as part of agent operation.  
**Consequences:** Pipeline design must avoid runtime execution of model-produced artifacts. Validation must rely on non-execution-based checks or controlled repository tooling consistent with the documented security model. Features that would require dynamic execution of generated code are out of scope unless the governing TRDs explicitly permit them.  
**Rejected alternatives:** Sandboxed execution of generated code was rejected because the provided architecture explicitly says generated code is never executed. Direct execution in either process was rejected for the same reason.

## Directed build agent, not chat or autocomplete product
**Status:** Accepted  
**Context:** The product description clearly distinguishes Crafted from chat interfaces, autocomplete tools, or copilots. It is described as a directed build agent driven by specifications and operator intent.  
**Decision:** Product behavior is optimized for specification-driven autonomous delivery rather than conversational assistance or inline code completion.  
**Consequences:** UX, orchestration, and backend logic should prioritize intake of repository context, TRDs, and intent; decomposition into implementation units; and production of pull requests. Features that primarily emulate chat or autocomplete behavior are not core architecture drivers.  
**Rejected alternatives:** Designing the system as a general chat assistant was rejected because the README explicitly says it is not a chat interface. Building around editor autocomplete workflows was rejected because it is not a copilot-style product.

## Specification-first workflow from intent to PRD plan to typed pull requests
**Status:** Accepted  
**Context:** The product flow is described as taking repository specifications and plain-language operator intent, assessing confidence, decomposing the work into an ordered PRD plan, then decomposing each PRD into a sequence of typed pull requests.  
**Decision:** Work orchestration follows a staged planning pipeline: ingest specifications and intent, assess scope confidence, create an ordered PRD plan, then derive typed PR units for implementation.  
**Consequences:** Planning is a first-class subsystem rather than an incidental prompt. State and interfaces must preserve planning artifacts and ordering. Pull requests are produced as logical units tied back to the decomposition plan.  
**Rejected alternatives:** Directly generating code from raw user intent without intermediate planning was rejected because the product explicitly performs confidence assessment and decomposition. A single monolithic PR per request was rejected because the product opens one PR per logical unit.

## One pull request per logical unit of work
**Status:** Accepted  
**Context:** The product description states that the agent opens GitHub pull requests one per logical unit, and that the operator gates, reviews, and merges them while the next PR is built.  
**Decision:** Changes are packaged into separate pull requests according to logical units derived from the planning process rather than bundled into a single large repository update.  
**Consequences:** The pipeline must support incremental planning, branch management, PR sequencing, and resumable progress. Reviewability is prioritized over maximal batching.  
**Rejected alternatives:** Creating a single umbrella PR for an entire intent was rejected because it conflicts with the documented one-PR-per-logical-unit workflow. Creating unstructured micro-commits without PR boundaries was rejected because the unit of operator review is the pull request.

## Two-model consensus generation with Claude arbitration
**Status:** Accepted  
**Context:** The README states that implementation and tests are produced using a two-model consensus engine with Claude and GPT-4o in parallel, with Claude arbitrating every result. The architecture notes also reference a ConsensusEngine and provider adapters.  
**Decision:** Model output generation uses parallel participation from two LLM providers, and final arbitration is performed by Claude.  
**Consequences:** Backend design must support multiple provider adapters, parallel generation, comparison or reconciliation logic, and explicit arbitration behavior. Final outputs are not accepted from a single provider without the consensus mechanism described by the product.  
**Rejected alternatives:** Single-model generation was rejected because the product is explicitly defined around two-model consensus. Symmetric voting without an arbitrator was rejected because Claude is specified as the arbitrator.

## Validation pipeline includes self-correction, lint gating, and iterative fix loop
**Status:** Accepted  
**Context:** The product flow explicitly includes a self-correction pass, a lint gate, and an iterative fix loop after generation.  
**Decision:** Generated changes pass through a post-generation validation pipeline that performs self-correction, applies lint-based gating, and iterates fixes until the pipeline reaches an acceptable state or fails according to the governing contracts.  
**Consequences:** Generation is not treated as a one-shot action. Backend workflow orchestration must preserve intermediate validation states and retries. Quality gates are mandatory parts of delivery, not optional polish.  
**Rejected alternatives:** Accepting first-pass model output without structured validation was rejected because it conflicts with the documented pipeline. Manual-only postprocessing was rejected because the product is designed for autonomous build progression.

## Operator-gated review and merge model
**Status:** Accepted  
**Context:** The README states that the operator gates, reviews, and merges pull requests while the agent continues building subsequent work. This defines the human control point in the system.  
**Decision:** The system automates planning, implementation, and PR creation, but review and merge authority remains with the human operator.  
**Consequences:** The product must expose PRs in a reviewable state and cannot assume autonomous merge completion as the default model. Pipeline progress may be concurrent with human review, but merge control remains external to the agent.  
**Rejected alternatives:** Fully autonomous merge behavior was rejected because the documented workflow places gating and merge with the operator. Manual-only coding without automated PR generation was rejected because it does not match the product mission.

## Pull requests are opened as draft first
**Status:** Accepted  
**Context:** The GitHub integration lessons learned document states that the agent opens every PR as a draft so CI can run before the operator sees it. This is described as an established behavior in the v38.x pipeline.  
**Decision:** Newly created pull requests are opened in draft state by default to allow CI and pipeline checks to complete before human review.  
**Consequences:** GitHub automation must support draft PR creation and later state transition. Review workflows assume an initial non-reviewable draft lifecycle. CI timing and PR notifications should align with draft-first operation.  
**Rejected alternatives:** Opening PRs immediately as ready for review was rejected because the documented pipeline intentionally uses draft PRs to stage CI before operator review.

## Draft-to-ready transition uses GitHub GraphQL mutation
**Status:** Accepted  
**Context:** Production lessons learned document a specific GitHub API behavior: REST `PATCH /pulls/{number}` with `{"draft": false}` silently does not convert draft PRs, while the GraphQL `markPullRequestReadyForReview` mutation is the supported approach.  
**Decision:** The system converts draft pull requests to ready-for-review using GitHub GraphQL `markPullRequestReadyForReview`, not REST patching of the draft field.  
**Consequences:** GitHub integration must include GraphQL capability in addition to any REST usage. API client abstractions must account for endpoint-specific behavior and not rely on misleading successful REST responses for this transition.  
**Rejected alternatives:** Using REST `PATCH` to clear the draft state was rejected because the document reports it returns 200 while leaving the PR as draft. Manual UI conversion was rejected because the pipeline is automated.

## Subsystem ownership is organized by TRD domain
**Status:** Accepted  
**Context:** The repository guidance maps implementation concerns to specific TRDs, including Swift files, SwiftUI views, and backend components such as `ConsensusEngine` and `ProviderAdapter`. This implies domain-based subsystem governance.  
**Decision:** Each subsystem is owned by its corresponding TRD domain, and changes begin by identifying the controlling TRD for the relevant component area.  
**Consequences:** Architecture and maintenance are modularized by subsystem specification. Teams and agents must navigate by TRD ownership rather than by file location alone. Cross-subsystem changes require reading multiple authoritative specs.  
**Rejected alternatives:** Treating the codebase as governed by a single undifferentiated design document was rejected because the repository explicitly partitions authority across multiple TRDs. Relying only on source code conventions was rejected because TRDs are the source of truth.