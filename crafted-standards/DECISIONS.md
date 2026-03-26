# DECISIONS.md

## Native macOS agent with a two-process architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent. The repository guidance states the architecture is split into a Swift shell and a Python backend, with clear ownership boundaries between UI/auth/secrets and intelligence/generation/GitHub operations.  
**Decision:** Implement the system as two cooperating local processes:
- A Swift native macOS shell responsible for UI, authentication, Keychain access, and local IPC orchestration.
- A Python backend responsible for consensus, generation pipeline, and GitHub operations.  
**Consequences:** This constrains component boundaries, ownership of secrets, and implementation language choices. Swift-facing concerns must remain in the shell; generation and orchestration logic must remain in the backend. Cross-process contracts become a primary system interface and must be treated as stable.  
**Rejected alternatives:**  
- **Single-process application:** Rejected because the TRD-derived architecture explicitly separates UI/secrets from model orchestration and automation logic.  
- **All-Swift or all-Python implementation:** Rejected because subsystem ownership is explicitly divided by responsibility and platform fit.

## Swift shell owns UI, authentication, Keychain, and local IPC
**Status:** Accepted  
**Context:** Repository instructions assign UI, authentication, Keychain, and XPC/socket-related shell responsibilities to the Swift process. The shell is the trusted local host for operator interaction and secret custody.  
**Decision:** Place all user interface, user-facing session/auth flows, and secure local secret access in the Swift shell. The shell is the authority for secret retrieval and user-mediated control surfaces.  
**Consequences:** The Python backend must not independently own macOS-native secret storage or UI responsibilities. Any backend operation requiring credentials depends on shell-mediated access or provisioning. This narrows the trusted surface for sensitive data handling.  
**Rejected alternatives:**  
- **Backend-owned secrets:** Rejected because secret custody is explicitly assigned to the Swift shell.  
- **Cross-platform UI hosted in Python:** Rejected because the product is specified as native macOS with Swift-owned UI.

## Python backend owns intelligence, generation pipeline, and GitHub operations
**Status:** Accepted  
**Context:** Repository guidance explicitly assigns consensus, generation, and GitHub tasks to the Python backend. The product behavior described in the README depends on backend orchestration across multiple generation and validation stages.  
**Decision:** Centralize planning execution, model orchestration, typed PR generation workflow, self-correction, lint/fix loops, and GitHub API operations in the Python backend.  
**Consequences:** GitHub logic, generation workflows, and model-provider abstractions must be implemented in Python. The shell must remain a controller/presenter rather than duplicating backend behavior.  
**Rejected alternatives:**  
- **Split GitHub behavior across Swift and Python:** Rejected because ownership is explicitly assigned to the backend.  
- **Move model orchestration into the shell:** Rejected because intelligence and pipeline responsibilities are specified for the backend.

## Inter-process communication uses an authenticated Unix socket with line-delimited JSON
**Status:** Accepted  
**Context:** The product definition states that the Swift shell and Python backend communicate through an authenticated Unix socket using line-delimited JSON messages. This is a core integration contract between the two processes.  
**Decision:** Use an authenticated local Unix socket as the transport and encode messages as line-delimited JSON records.  
**Consequences:** All cross-process requests and events must fit a JSON message protocol and stream framing model. Authentication of the local channel is mandatory. Any alternative IPC mechanism must not replace this without changing the governing specification.  
**Rejected alternatives:**  
- **XPC as the sole transport:** Rejected because the product definition specifically names an authenticated Unix socket with line-delimited JSON as the communication mechanism.  
- **HTTP/gRPC loopback server:** Rejected because it introduces an unneeded protocol surface not specified by the TRD-derived system description.  
- **Binary custom protocol:** Rejected because line-delimited JSON is the specified wire format.

## Never execute generated code
**Status:** Accepted  
**Context:** The repository guidance explicitly states that neither the Swift process nor the Python process ever executes generated code. This is a foundational security constraint for the agent.  
**Decision:** Prohibit execution of generated code by any system component. Generated artifacts may be analyzed, linted, tested through repository-controlled tooling where applicable, and proposed in pull requests, but the agent itself does not execute arbitrary generated output as code.  
**Consequences:** Design choices for validation, testing, and correction must avoid runtime execution of generated code as an agent action. Tooling and pipeline stages must respect this non-execution boundary.  
**Rejected alternatives:**  
- **Sandboxed execution of generated code:** Rejected because the governing product guidance says generated code is never executed.  
- **Optional operator-enabled execution mode:** Rejected because the prohibition is stated as universal, not configurable.

## Technical Requirement Documents are the source of truth
**Status:** Accepted  
**Context:** Repository guidance states that the 16 TRDs in `forge-docs/` completely specify the product and that code must match them. Agents are instructed not to invent requirements.  
**Decision:** Treat the TRDs as authoritative for interfaces, error contracts, state machines, security controls, testing requirements, and performance requirements. Implementation decisions must be derived from those documents rather than ad hoc interpretation.  
**Consequences:** Engineering changes require tracing to the relevant TRD. Unspecified behavior should not be invented. Documentation and code reviews must validate conformance to TRD-owned subsystem requirements.  
**Rejected alternatives:**  
- **README or agent guidance as primary spec:** Rejected because those documents point back to the TRDs as authoritative.  
- **Implementation-defined behavior filling gaps freely:** Rejected because the explicit instruction is to avoid inventing requirements.

## Security requirements are governed centrally by TRD-11
**Status:** Accepted  
**Context:** Repository instructions state that TRD-11 governs all components and must be consulted for any work involving credentials, external content, generated code, or CI.  
**Decision:** Apply a centralized security model defined by TRD-11 across all subsystems, regardless of implementation language or ownership. Security-relevant changes must be evaluated against that governing document first.  
**Consequences:** Security controls cannot be decided independently per subsystem. Changes involving secrets, remote APIs, generated content, or automation pipelines must satisfy the same shared security constraints.  
**Rejected alternatives:**  
- **Per-subsystem security policies:** Rejected because security is specified as governed centrally across all components.  
- **Security review only for backend changes:** Rejected because the guidance explicitly applies across the system.

## The product is a directed build agent, not a chat interface or code autocomplete tool
**Status:** Accepted  
**Context:** The README explicitly distinguishes the product from chat interfaces, autocomplete tools, and copilots. It is described as a directed build agent that takes repository specifications and intent, then produces pull requests autonomously.  
**Decision:** Design user flows, system behavior, and subsystem interfaces around directed repository transformation and PR production rather than open-ended conversational interaction or inline completion.  
**Consequences:** UX, workflow, and backend orchestration must optimize for scoped intent intake, planning, execution, PR generation, and operator gating. Conversational features or editor-autocomplete behaviors are out of scope unless explicitly specified elsewhere.  
**Rejected alternatives:**  
- **Chat-first agent UX:** Rejected because the product definition explicitly says it is not a chat interface.  
- **Autocomplete/copilot behavior:** Rejected because the product is defined around repository-level build execution and pull-request output.

## Operator provides repository, TRDs, and plain-language intent as the primary input model
**Status:** Accepted  
**Context:** The README describes the operator supplying a repository, a set of TRDs, and a plain-language intent, after which the agent proceeds through confidence assessment, planning, generation, and PR creation.  
**Decision:** Use repository context, loaded technical specifications, and operator intent as the canonical inputs to the build workflow.  
**Consequences:** Input handling, planning, and execution subsystems must be optimized for spec-grounded repository work rather than generic prompt-only tasking. The system must maintain traceability from intent and TRDs into generated PRs.  
**Rejected alternatives:**  
- **Prompt-only task execution without repository/spec grounding:** Rejected because the product workflow is explicitly anchored in repository state and technical specifications.  
- **Fully autonomous goal discovery:** Rejected because the operator-supplied intent is the stated starting point.

## Assess confidence in scope before committing to execution
**Status:** Accepted  
**Context:** The README states that the agent assesses its confidence in the requested scope before committing to it. This indicates a gate before execution begins.  
**Decision:** Insert a pre-execution confidence assessment stage that evaluates whether the requested intent is sufficiently understood and bounded before the agent commits to building.  
**Consequences:** The system must support refusal, deferral, or decomposition behavior when scope confidence is inadequate. Downstream planning depends on this gate.  
**Rejected alternatives:**  
- **Immediate execution on every user request:** Rejected because the documented workflow includes a confidence assessment before commitment.  
- **Manual-only operator triage with no model-based confidence stage:** Rejected because confidence assessment is part of the product behavior.

## Decompose intent into an ordered PRD plan before generating pull requests
**Status:** Accepted  
**Context:** The README states that the system decomposes operator intent into an ordered PRD plan, then further decomposes each PRD into a sequence of typed pull requests. This establishes a staged planning hierarchy.  
**Decision:** Use a two-level planning structure:
1. Convert intent into an ordered PRD plan.
2. Convert each PRD into one or more typed pull requests for implementation.  
**Consequences:** Planning is explicit, hierarchical, and ordered. Subsystems must preserve plan sequencing and traceability from intent to PRD to PR.  
**Rejected alternatives:**  
- **Direct generation of code changes from intent:** Rejected because the documented workflow requires intermediate PRD planning.  
- **Single undifferentiated task list:** Rejected because the product specifies typed, ordered decomposition.

## Open one pull request per logical unit of work
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests “one per logical unit.” This implies a granularity rule for change packaging.  
**Decision:** Package implementation output into pull requests aligned with logical work units rather than batching unrelated changes together.  
**Consequences:** Planning and generation must identify logical boundaries and maintain them through PR creation. This improves reviewability and sequencing but constrains batching optimization.  
**Rejected alternatives:**  
- **Single large PR for all requested work:** Rejected because the documented behavior is one PR per logical unit.  
- **File-by-file PR fragmentation:** Rejected because the unit is logical work, not arbitrary technical slicing.

## Use a two-model consensus engine with Claude and GPT-4o, with Claude arbitrating every result
**Status:** Accepted  
**Context:** The README defines the generation strategy as a two-model consensus engine using Claude and GPT-4o in parallel, with Claude arbitrating every result.  
**Decision:** Implement generation and evaluation around two providers operating in parallel, with Claude acting as the arbiter for final result selection or reconciliation.  
**Consequences:** Provider abstraction, consensus orchestration, and arbitration logic must support two distinct model outputs and a final adjudication step. Single-model operation would not satisfy the specified behavior.  
**Rejected alternatives:**  
- **Single-provider generation:** Rejected because the product explicitly uses two-model consensus.  
- **Symmetric voting with no designated arbiter:** Rejected because Claude is specifically assigned arbitration responsibility.  
- **GPT-4o as arbiter:** Rejected because the product description names Claude as the arbiter.

## Generate implementation and tests in parallel across providers
**Status:** Accepted  
**Context:** The README states that the system generates implementation and tests using two LLM providers in parallel. This indicates both concurrency and inclusion of tests as first-class generated artifacts.  
**Decision:** Run parallel provider generation for both implementation changes and corresponding tests as part of each typed pull request workflow.  
**Consequences:** The pipeline must support concurrent provider requests and handle reconciliation across code and test outputs. Test generation is required, not optional.  
**Rejected alternatives:**  
- **Implementation-first, tests-later manual addition:** Rejected because tests are part of the described generation workflow.  
- **Sequential provider execution:** Rejected because provider generation is explicitly parallelized.

## Apply a self-correction pass, lint gate, and iterative fix loop before PR output
**Status:** Accepted  
**Context:** The README describes the agent performing a self-correction pass, a lint gate, and an iterative fix loop as part of the build workflow. These are explicit quality-control stages.  
**Decision:** Insert mandatory post-generation quality stages consisting of:
- self-correction,
- lint validation,
- iterative issue-fixing loops before finalizing pull requests.  
**Consequences:** PRs are not emitted directly from first-pass generation. The backend pipeline must support repeated refinement and validation cycles.  
**Rejected alternatives:**  
- **First-pass output with no correction loop:** Rejected because the documented workflow includes correction and lint gating.  
- **Human-only review as the sole quality control:** Rejected because automated self-correction and iterative fixes are specified.

## Operator gates, reviews, and merges; the agent continues building sequentially
**Status:** Accepted  
**Context:** The README states that the operator gates, reviews, and merges each PR while the agent builds the next PR in parallel with review of the previous one.  
**Decision:** Keep merge authority and final review with the operator, while allowing the agent to continue preparing subsequent logical-unit PRs within the planned sequence.  
**Consequences:** Human oversight remains mandatory at the merge boundary. The system must support pipelined preparation of subsequent work without taking final merge actions autonomously.  
**Rejected alternatives:**  
- **Fully autonomous merge by the agent:** Rejected because review and merge are operator-controlled.  
- **Strictly serial build-review-build execution:** Rejected because the product explicitly overlaps next-PR building with operator review of the previous PR.

## GitHub pull requests are opened as drafts first
**Status:** Accepted  
**Context:** The GitHub integration lessons learned document states that the agent opens every PR as a draft so CI can run before the operator sees it.  
**Decision:** Create all GitHub pull requests initially in draft state.  
**Consequences:** PR lifecycle logic must include draft handling and later promotion to review-ready state. CI behavior and operator-facing review timing depend on this.  
**Rejected alternatives:**  
- **Open PRs as ready-for-review immediately:** Rejected because the documented operating model intentionally uses drafts to allow CI to run first.  
- **No PR creation until all checks are complete locally:** Rejected because the described lifecycle uses draft PRs as the vehicle for CI.

## Convert draft pull requests to ready-for-review using GraphQL, not REST PATCH
**Status:** Accepted  
**Context:** The GitHub integration lessons learned document records a production-discovered API behavior: REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}` silently fails to convert draft PRs, while the GraphQL `markPullRequestReadyForReview` mutation is the supported path.  
**Decision:** Use the GitHub GraphQL `markPullRequestReadyForReview` mutation to transition draft pull requests to ready-for-review status. Do not rely on REST PATCH with a `draft` field for this transition.  
**Consequences:** GitHub integration must include GraphQL support for PR lifecycle transitions even if other operations use REST. API client behavior must account for silent REST non-effect in this case.  
**Rejected alternatives:**  
- **REST PATCH with `draft: false`:** Rejected because it is documented to return 200 while leaving the PR in draft state.  
- **Manual operator conversion in GitHub UI:** Rejected because the pipeline requires reliable automated lifecycle progression.