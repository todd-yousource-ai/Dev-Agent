# DECISIONS.md

## Two-process native macOS architecture
**Status:** Accepted  
**Context:** The product is specified as a native macOS AI coding agent with distinct responsibilities spanning UI, authentication, secret handling, orchestration, model consensus, and GitHub automation. The repository guidance states the architecture is split into a Swift shell and a Python backend, and the README defines the agent as a directed build system rather than a general chat tool.  
**Decision:** The system is implemented as a two-process architecture: a native Swift macOS shell for UI, authentication, Keychain, and local system integration; and a Python backend for intelligence, generation, consensus, pipeline execution, and GitHub operations.  
**Consequences:** Clear trust and responsibility boundaries are enforced between user/system-facing operations and AI/pipeline operations. Changes must respect subsystem ownership and interfaces rather than collapsing functionality into a single runtime. Cross-process communication becomes a first-class design concern.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because repository guidance explicitly defines a two-process architecture.  
- **Python-only desktop agent:** Rejected because native macOS UI, Keychain, and auth are assigned to the Swift shell.  
- **Swift-only implementation:** Rejected because consensus, generation, and GitHub automation are assigned to the Python backend.

## Swift shell owns UI, authentication, and secrets
**Status:** Accepted  
**Context:** The repository instructions assign UI, auth, Keychain, and XPC/system integration to the Swift process. Security-sensitive handling is explicitly separated from model execution and generation concerns.  
**Decision:** All user interface behavior, authentication flows, and secret storage/access are owned by the Swift shell. Secrets are not delegated to the Python backend as a source of record.  
**Consequences:** The shell becomes the security and UX boundary for the application. Backend features that require credentials must receive only the minimum necessary access through defined interfaces. Secret persistence and retrieval must stay aligned with the native macOS security model.  
**Rejected alternatives:**  
- **Store credentials in the Python backend:** Rejected because secret ownership is assigned to Swift/Keychain.  
- **Duplicate auth handling in both processes:** Rejected because it weakens trust boundaries and contradicts subsystem ownership.  
- **Web-based auth and UI layer:** Rejected because the product is explicitly a native macOS agent.

## Python backend owns intelligence, generation, and GitHub operations
**Status:** Accepted  
**Context:** Repository guidance assigns consensus, provider integration, generation pipeline, and GitHub interactions to the Python process. The README further describes autonomous plan decomposition, typed PR generation, self-correction, and iterative fix loops as backend behaviors.  
**Decision:** The Python backend is the sole owner of model orchestration, consensus evaluation, code/test generation, correction loops, lint gating, and GitHub repository/PR automation.  
**Consequences:** Backend components must expose stable interfaces for orchestration and integration. Shell code must not embed generation logic or GitHub workflow logic. Performance, error handling, and correctness of autonomous build execution are concentrated in backend subsystems.  
**Rejected alternatives:**  
- **Implement GitHub automation in the Swift shell:** Rejected because backend ownership is explicitly defined.  
- **Split generation responsibilities between shell and backend:** Rejected because it blurs subsystem boundaries and complicates consistency.  
- **Use external hosted orchestration instead of a local backend:** Rejected because the product is defined as a local two-process application.

## Inter-process communication uses an authenticated Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The architecture guidance states that the two processes communicate through an authenticated Unix socket using line-delimited JSON. This is a core contract between the shell and backend.  
**Decision:** All shell-backend communication uses an authenticated local Unix socket transport and a line-delimited JSON message protocol.  
**Consequences:** Message framing, authentication, compatibility, and error contracts must be designed around JSON line messages. Any subsystem crossing the process boundary must serialize into this protocol. Transport changes require explicit architectural revision because they affect every subsystem interface.  
**Rejected alternatives:**  
- **REST over localhost:** Rejected because the prescribed IPC mechanism is an authenticated Unix socket.  
- **Raw XPC for all communication:** Rejected because the cross-process contract is specified as socket-based LDJSON.  
- **Binary custom protocol:** Rejected because line-delimited JSON is the documented wire format.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** The repository instructions explicitly state that neither process ever executes generated code. This is a foundational security boundary for an autonomous coding agent that produces code changes and tests.  
**Decision:** The system must not execute generated code directly in either the Swift shell or the Python backend. Build, validation, and review workflows must be designed to avoid runtime execution of model-produced artifacts by the agent itself.  
**Consequences:** Validation relies on static checks, repository-integrated tooling, gated CI, and human review rather than local execution of generated artifacts by the agent runtime. Features that would require sandboxed execution are out of scope unless separately specified. Security review must treat any attempt to run generated outputs as a violation of the architecture.  
**Rejected alternatives:**  
- **Local sandbox execution of generated code:** Rejected because the architecture explicitly forbids executing generated code.  
- **Selective execution for tests only:** Rejected for the same reason; no exception is stated.  
- **Provider-side code execution services:** Rejected because the agent’s security posture is built around non-execution.

## TRDs are the sole source of truth for implementation
**Status:** Accepted  
**Context:** Multiple repository documents state that 16 TRDs in `forge-docs/` completely specify the system, and that code must match them. They define interfaces, error contracts, state machines, security controls, performance requirements, and testing obligations.  
**Decision:** Significant design and implementation choices are derived from the TRDs, not invented ad hoc from code convenience or unstated assumptions. Repository-level guidance documents are secondary and point back to the TRDs as authoritative specifications.  
**Consequences:** Any subsystem change must begin by identifying and reading the owning TRD. Drift between implementation and TRDs is treated as a defect. Design work requires explicit traceability back to documented requirements.  
**Rejected alternatives:**  
- **Code-first design with documentation updated later:** Rejected because the TRDs are defined as source of truth.  
- **Agent discretion to invent missing requirements:** Rejected because repository guidance explicitly prohibits inventing requirements.  
- **README as primary product specification:** Rejected because the README is descriptive, while the TRDs are normative.

## Security controls are centralized under the security TRD and apply across all subsystems
**Status:** Accepted  
**Context:** Repository guidance states that TRD-11 governs all components and must be read before making security-relevant changes, especially where credentials, external content, generated code, or CI are involved.  
**Decision:** Security is treated as a cross-cutting architecture concern with a single governing specification that constrains shell, backend, provider integration, content handling, and pipeline behavior.  
**Consequences:** No subsystem may define conflicting local security behavior. Changes involving credentials, external inputs, generated outputs, or automation pipelines must be evaluated against the common security model first. Security-sensitive shortcuts are not allowed for subsystem convenience.  
**Rejected alternatives:**  
- **Per-subsystem independent security rules:** Rejected because a single governing security specification is mandated.  
- **Security only at process boundaries:** Rejected because the guidance explicitly covers credentials, content, generated code, and CI across the system.  
- **Defer security to implementation review:** Rejected because the security model is specified up front.

## The product is a directed build agent, not a chat assistant or autocomplete tool
**Status:** Accepted  
**Context:** The README explicitly distinguishes the product from a chat interface, code autocomplete, or copilot. It describes an intent-driven workflow that plans work from TRDs, produces typed PRs, and runs an autonomous build pipeline.  
**Decision:** Product and subsystem design optimize for directed specification-to-PR execution rather than conversational assistance or inline coding support.  
**Consequences:** UX, orchestration, model prompting, and output structures must center on intent intake, scoped planning, PR decomposition, and reviewable GitHub outputs. Features that primarily support open-ended chat or editor autocomplete are out of scope unless separately specified.  
**Rejected alternatives:**  
- **General-purpose chat UI:** Rejected because the product is explicitly not a chat interface.  
- **IDE autocomplete assistant:** Rejected because the product is explicitly not a copilot.  
- **Free-form code generation without planning/PR structure:** Rejected because the documented workflow is structured and gated.

## Work is decomposed from intent to ordered PRD plan to typed pull requests
**Status:** Accepted  
**Context:** The README describes a staged autonomous workflow: user intent is assessed for confidence, decomposed into an ordered PRD plan, and then decomposed into a sequence of typed pull requests. This establishes the unit of planning and delivery.  
**Decision:** The planning subsystem uses a hierarchical decomposition model: intent → scoped plan/PRD sequence → typed PRs as delivery units.  
**Consequences:** Backend orchestration, UI state, and GitHub integration all assume PRs are the canonical execution artifacts. Planning must preserve order and logical unit boundaries rather than generating a monolithic change set. Review and merge workflows depend on this decomposition.  
**Rejected alternatives:**  
- **Single large branch/change per intent:** Rejected because delivery is explicitly one PR per logical unit.  
- **Task execution without explicit planning hierarchy:** Rejected because ordered PRD and PR decomposition is part of the documented workflow.  
- **Unstructured patch generation:** Rejected because typed PR sequencing is a core product behavior.

## One pull request is created per logical unit of work
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests one per logical unit and continues building the next while the operator reviews the previous one. This defines the granularity of output.  
**Decision:** The pipeline produces separate pull requests for logically distinct units of implementation rather than batching unrelated work into a single PR.  
**Consequences:** Planning, branch management, dependency tracking, and GitHub automation must support multiple sequential PRs. The system must preserve reviewability and isolation between work items. CI, status reporting, and merge progression operate at PR granularity.  
**Rejected alternatives:**  
- **Batch all generated changes into one PR:** Rejected because it conflicts with the specified logical-unit model.  
- **Commit directly to the main branch:** Rejected because the product is centered on PR-based gating.  
- **Create PRs per file or per commit:** Rejected because the unit is logical work, not arbitrary technical granularity.

## Two-model parallel generation with Claude arbitration is the default consensus strategy
**Status:** Accepted  
**Context:** The README specifies a two-model consensus engine using Claude and GPT-4o in parallel, with Claude arbitrating every result. Repository guidance also names backend components such as ConsensusEngine and ProviderAdapter, indicating explicit subsystem support for this pattern.  
**Decision:** The generation pipeline obtains parallel outputs from two model providers and resolves outcomes through a consensus/arbitration mechanism in which Claude is the arbitrator.  
**Consequences:** Provider abstraction, result normalization, comparison logic, and arbitration pathways are required backend capabilities. Pipeline latency and failure handling must account for multiple provider calls. Single-provider shortcuts cannot replace the prescribed consensus behavior where that behavior is required by specification.  
**Rejected alternatives:**  
- **Single-model generation:** Rejected because the product is defined around a two-model consensus engine.  
- **Majority voting across many models:** Rejected because the specified pattern is two providers with Claude arbitration.  
- **Non-deterministic provider selection per task:** Rejected because the documented architecture assumes parallel dual-provider operation.

## Autonomous generation is gated by self-correction, lint checks, and iterative fix loops
**Status:** Accepted  
**Context:** The README describes a build pipeline that generates implementation and tests, runs a self-correction pass, applies a lint gate, and performs an iterative fix loop. These are defined as standard stages of the agent’s operation.  
**Decision:** Generated changes pass through a staged quality pipeline including self-correction, lint gating, and repeated remediation loops before PR output is considered ready.  
**Consequences:** The backend pipeline must support multi-stage evaluation and mutation of generated work rather than one-shot generation. Error handling and status reporting need to represent intermediate correction states. Pipeline completion criteria depend on these gates.  
**Rejected alternatives:**  
- **One-pass generation directly to PR:** Rejected because quality gates are part of the documented workflow.  
- **Human-only correction after generation:** Rejected because the system includes autonomous self-correction and fix loops.  
- **Lint as advisory only:** Rejected because lint is described as a gate.

## Pull requests are opened as draft by default and only later marked ready for review
**Status:** Accepted  
**Context:** The GitHub integration lessons-learned document states that the agent opens every PR as a draft so CI can run before the operator sees it. It also documents the lifecycle implications of draft PRs.  
**Decision:** GitHub PR creation defaults to draft status, and promotion to reviewable state is a separate explicit workflow step.  
**Consequences:** CI and review state transitions are decoupled. GitHub integration must track PR draft status as part of its state machine. Operator-facing workflows and notifications must account for draft-first behavior.  
**Rejected alternatives:**  
- **Open PRs as ready for review immediately:** Rejected because the documented workflow explicitly opens every PR as a draft.  
- **Use issue comments instead of PR drafts for staging:** Rejected because the specified lifecycle is PR-centric.  
- **Local-only staging before PR creation:** Rejected because draft PRs are the chosen staging mechanism.

## Draft-to-ready transition uses GitHub GraphQL, not REST patch semantics
**Status:** Accepted  
**Context:** The lessons-learned document records a production-discovered GitHub behavior: REST `PATCH /pulls/{number}` with `{"draft": false}` returns 200 but does not convert a draft PR. The documented fix is to use the GraphQL `markPullRequestReadyForReview` mutation, identified as the supported path.  
**Decision:** The GitHub integration subsystem uses GraphQL to convert draft pull requests to ready-for-review state and does not rely on REST patching for this transition.  
**Consequences:** GitHub client abstractions must support both REST and GraphQL where API behavior demands it. PR lifecycle code must encode this specific transport choice. Testing and failure diagnosis must account for silent REST non-effect in this transition.  
**Rejected alternatives:**  
- **REST PATCH with `draft: false`:** Rejected because it is documented to silently fail to change state.  
- **Close and recreate PR as non-draft:** Rejected because a supported GraphQL mutation exists and preserves continuity.  
- **Manual operator conversion only:** Rejected because the pipeline automates PR lifecycle transitions.