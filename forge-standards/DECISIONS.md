# DECISIONS.md

## Native macOS product with a two-process architecture
**Status:** Accepted  
**Context:** The product is defined as a native macOS AI coding agent. The repository guidance states the system is split into a Swift shell and a Python backend, with strict responsibility boundaries between them. This separation is central to the documented architecture and security model.  
**Decision:** The system is implemented as two cooperating processes:
- a Swift macOS shell responsible for UI, authentication, Keychain access, and XPC/platform concerns
- a Python backend responsible for consensus, planning/generation pipeline, and GitHub operations

The processes communicate through a defined IPC interface rather than sharing responsibilities directly.  
**Consequences:** Clear subsystem ownership is enforced. UI and secrets remain in the Swift process; intelligence and repository automation remain in Python. Cross-cutting features must be designed across a process boundary. Testing, interfaces, and error handling must account for inter-process communication.  
**Rejected alternatives:** A single-process application was rejected because it would blur security and responsibility boundaries. Moving secrets or platform-native concerns into Python was rejected because the shell is explicitly documented as the owner of auth and Keychain access.

## Authenticated Unix socket with line-delimited JSON for inter-process communication
**Status:** Accepted  
**Context:** The repository instructions specify that the Swift and Python processes communicate over an authenticated Unix socket using line-delimited JSON. This is treated as a defined interface contract, not an implementation detail.  
**Decision:** All Swift↔Python communication uses an authenticated Unix domain socket and newline-delimited JSON messages. The protocol is the canonical transport between the shell and backend.  
**Consequences:** Message framing, authentication, request/response semantics, and error reporting must fit a line-delimited JSON protocol. Both processes must maintain strict schema compatibility. Socket authentication becomes part of the security boundary.  
**Rejected alternatives:** XPC-only communication was rejected because the backend is specified as Python-based. Binary protocols and ad hoc serialization were rejected because the documented contract is line-delimited JSON over an authenticated Unix socket.

## Swift shell owns UI, authentication, Keychain, and platform integration
**Status:** Accepted  
**Context:** The shell’s responsibility boundaries are explicitly described in the repository guidance. Native macOS functionality, user interaction, and secret storage are assigned to Swift.  
**Decision:** The Swift process is the sole owner of:
- the native macOS UI
- user authentication flows
- Keychain access and secret custody
- shell-side platform integration such as XPC/macOS-specific behaviors

No other subsystem is permitted to duplicate these responsibilities.  
**Consequences:** Backend features requiring user credentials must request them through the shell boundary. UI state and secret storage cannot be implemented in Python. macOS-native interactions must be surfaced through shell-owned APIs.  
**Rejected alternatives:** Putting auth or secrets in the Python backend was rejected because it conflicts with the defined shell responsibilities. Cross-platform UI frameworks were not adopted because the product is specified as native macOS with Swift ownership of UI.

## Python backend owns intelligence, generation pipeline, and GitHub operations
**Status:** Accepted  
**Context:** The product description and repository instructions assign all model orchestration and automation logic to the Python backend. This includes repository planning, generation, correction, and GitHub interaction.  
**Decision:** The Python process is the sole owner of:
- intent assessment and confidence evaluation
- PRD and pull-request decomposition
- multi-model generation and arbitration pipeline
- lint/fix/self-correction loops
- GitHub API operations and pull-request lifecycle handling

The backend is the execution engine for build automation, excluding execution of generated code.  
**Consequences:** Pipeline logic remains centralized. GitHub integration is not split across processes. Shell features that need workflow state must consume backend-produced state rather than reimplement logic.  
**Rejected alternatives:** Splitting GitHub logic into Swift was rejected because GitHub operations are explicitly assigned to the Python backend. Embedding generation logic in the shell was rejected because it violates the documented process boundary.

## TRDs are the source of truth for all subsystem behavior
**Status:** Accepted  
**Context:** Multiple repository documents state that the 16 TRDs in `forge-docs/` completely specify interfaces, contracts, state machines, security controls, and performance requirements. Contributors are instructed not to invent requirements.  
**Decision:** All significant implementation decisions are derived from the TRDs, and code must conform to them. When ambiguity exists, the owning TRD governs the subsystem.  
**Consequences:** Local convenience, unstated assumptions, and speculative features are constrained by the TRDs. Change management requires updating the relevant TRD first or alongside implementation. Cross-subsystem decisions must trace back to documented ownership.  
**Rejected alternatives:** Deriving behavior from code alone was rejected because the docs explicitly define the TRDs as authoritative. Allowing developers or agents to infer missing product requirements was rejected because the guidance says not to invent requirements.

## Security controls are centralized under the security TRD and apply to all components
**Status:** Accepted  
**Context:** Repository instructions explicitly identify a security TRD as governing all components and requiring review for any change involving credentials, external content, generated code, or CI. Security is treated as a system-wide concern, not a per-feature add-on.  
**Decision:** Security-relevant behavior across shell, backend, pipeline, generated artifacts, and CI must conform to the shared security specification. Security review is mandatory whenever a change touches protected domains such as credentials or generated code handling.  
**Consequences:** Security decisions cannot be localized or improvised by a subsystem. Features that involve external input, code generation, or automation must be designed against explicit controls. CI and runtime behaviors are both in scope.  
**Rejected alternatives:** Per-team or per-component security policy was rejected because the repository defines a single governing security model. Treating CI or generated code as outside the security boundary was rejected because those areas are explicitly called out.

## Generated code is never executed by either process
**Status:** Accepted  
**Context:** The repository guidance explicitly states that neither the Swift shell nor the Python backend ever executes generated code. This is a core product and security constraint.  
**Decision:** The system may generate, lint, analyze, patch, commit, and propose code changes, but it must not execute generated code in either process. Any validation workflow must avoid runtime execution of generated output by the agent itself.  
**Consequences:** Pipeline stages must be designed around static analysis, repository operations, and non-execution validation paths. Features that depend on running produced code are prohibited unless delegated outside the agent’s execution boundary under separately specified controls.  
**Rejected alternatives:** Executing generated code for verification was rejected because it directly violates the documented rule. Sandboxed execution inside either process was also rejected because the prohibition is categorical in the provided guidance.

## The product is a directed build agent, not a chat interface or code autocomplete tool
**Status:** Accepted  
**Context:** The README explicitly distinguishes the product from chat interfaces, autocomplete tools, and copilots. It describes a workflow driven by specifications, intent, planning, generation, and pull requests.  
**Decision:** The primary product experience is a directed software build workflow:
- user provides repository, TRDs, and intent
- system assesses confidence and scope
- system decomposes work into ordered plans and typed pull requests
- system opens GitHub pull requests for operator review and merge

Interactive chat and inline completion are not the core product mode.  
**Consequences:** UX, architecture, and prioritization focus on planning and PR production rather than conversational breadth or IDE-style completion. Features should be evaluated against whether they advance the directed build workflow.  
**Rejected alternatives:** Building a general-purpose AI chat experience was rejected because the README explicitly says it is not a chat interface. Building a copilot/autocomplete product was rejected for the same reason.

## Specification-driven workflow from intent to ordered PR plan to typed pull requests
**Status:** Accepted  
**Context:** The README describes a staged workflow in which the agent consumes specifications and intent, determines confidence, decomposes work into an ordered PRD plan, and then into a sequence of typed pull requests.  
**Decision:** Work orchestration follows a specification-driven decomposition pipeline:
1. ingest repository and TRDs
2. accept plain-language user intent
3. assess confidence in scope
4. decompose into an ordered PRD plan
5. decompose each PRD into typed pull requests
6. generate and refine implementation for each PR

This decomposition is a first-class product behavior.  
**Consequences:** Planning artifacts and stepwise decomposition are part of the system contract. The backend must preserve ordering and logical unit boundaries. Pull requests represent intentional work units, not arbitrary commits.  
**Rejected alternatives:** Generating a single monolithic change from intent was rejected because the product is described as producing one PR per logical unit. Skipping confidence assessment or planning was rejected because those steps are explicitly part of the workflow.

## One pull request per logical unit of work
**Status:** Accepted  
**Context:** The README states that the agent opens GitHub pull requests one per logical unit, and that the next PR is built while the operator reviews the previous one. This implies PR granularity is deliberate and workflow-defining.  
**Decision:** The backend decomposes implementation into discrete, logically scoped pull requests rather than aggregating all work into one branch or creating arbitrary micro-commits.  
**Consequences:** Planning must identify logical boundaries. GitHub automation, branch management, and review state all operate at PR granularity. The operator review loop depends on meaningful PR units.  
**Rejected alternatives:** A single large PR per user intent was rejected because it conflicts with the documented “one per logical unit” workflow. Unstructured commit streaming without PR boundaries was rejected because the product centers on reviewable pull requests.

## Two-model consensus generation with Claude and GPT-4o, with Claude as arbiter
**Status:** Accepted  
**Context:** The README explicitly describes a two-model consensus engine using Claude and GPT-4o in parallel, with Claude arbitrating every result. This is a core intelligence architecture decision.  
**Decision:** Code generation and related intelligence tasks use two LLM providers in parallel, and final arbitration is performed by Claude. The consensus model is part of the required backend design.  
**Consequences:** Provider orchestration, prompt compatibility, reconciliation logic, and arbitration paths are required backend capabilities. The system must preserve deterministic ownership of final judgments through Claude arbitration.  
**Rejected alternatives:** Single-model generation was rejected because the product is explicitly described as using two-model consensus. Symmetric voting without a designated arbiter was rejected because Claude is specifically assigned to arbitrate every result.

## Pipeline includes self-correction, lint gating, and iterative fix loops before PR output
**Status:** Accepted  
**Context:** The README describes the generation pipeline as including a self-correction pass, a lint gate, and an iterative fix loop. These are named pipeline stages, not optional enhancements.  
**Decision:** Generated changes must pass through post-generation quality stages including:
- self-correction
- lint gating
- iterative fixing

These stages are required before producing final pull-request output.  
**Consequences:** The backend pipeline must support repeated refinement cycles and gate progression on quality criteria. PR output is constrained by automated quality checks rather than first-pass generation alone.  
**Rejected alternatives:** Emitting first-draft code directly as a PR was rejected because the documented workflow requires correction and gating stages. Manual-only quality review was rejected because automated self-correction and iterative fixes are built into the product definition.

## Operator-gated review and merge remains part of the control model
**Status:** Accepted  
**Context:** The README states, “You gate, review, and merge,” establishing the human operator as the approval authority while the agent continues preparing subsequent work.  
**Decision:** The system automates planning and PR creation, but merge authority remains with the human operator. The agent does not eliminate the review gate.  
**Consequences:** Product workflows, UI, and GitHub integration must preserve a human review step. Automation can prepare and update PRs, but operator oversight remains a required control point.  
**Rejected alternatives:** Fully autonomous merge without operator review was rejected because it conflicts with the explicitly described control model. Blocking all downstream work until review is complete was also rejected because the README states the next PR is built while the last one is being reviewed.

## Pull requests are opened as drafts first to allow CI before operator review
**Status:** Accepted  
**Context:** The GitHub integration lessons document states that the agent opens every PR as a draft so CI can run before the operator sees it. This behavior is presented as an established pipeline practice.  
**Decision:** Newly created pull requests are opened in draft state by default, and only later transitioned to ready-for-review when the workflow requires it.  
**Consequences:** GitHub lifecycle handling must support draft creation and later promotion. CI and review sequencing are intentionally separated. UI and backend state machines must account for draft status as the default initial PR state.  
**Rejected alternatives:** Opening PRs directly as ready-for-review was rejected because the documented pipeline intentionally uses drafts to let CI run first. Avoiding draft PRs entirely was rejected because that would remove the established lifecycle control.

## Draft pull requests are promoted to ready-for-review using GraphQL, not REST
**Status:** Accepted  
**Context:** The GitHub integration lessons document records a production-discovered behavior: REST `PATCH /pulls/{number}` with `{"draft": false}` returns 200 but does not convert a draft PR. The document states that GraphQL `markPullRequestReadyForReview` is the supported solution.  
**Decision:** The system uses the GraphQL `markPullRequestReadyForReview` mutation to transition draft pull requests to ready-for-review. REST patching of the `draft` field is not used for this transition.  
**Consequences:** GitHub integration must support GraphQL in addition to any REST usage. PR lifecycle code must not rely on misleading REST success responses for draft conversion. Tests should cover this behavior explicitly.  
**Rejected alternatives:** Using REST patch with `draft: false` was rejected because the documented behavior shows it is silently ineffective. Manual operator conversion was rejected because the automated pipeline requires a programmatic transition.

## GitHub integration behavior is driven by documented production lessons
**Status:** Accepted  
**Context:** The GitHub integration lessons document states that each lesson came from real production failures and that the fixes are implemented in the v38.x agent. These lessons describe behavior of GitHub APIs that automation must respect.  
**Decision:** GitHub API integration is implemented according to documented observed behaviors from production, especially where official-looking API shapes do not match actual behavior. The lessons-learned document is treated as operationally authoritative for GitHub lifecycle edge cases.  
**Consequences:** Integration logic prioritizes proven behavior over assumptions from nominal API symmetry. Edge-case handling is part of the design, not a future hardening task. Regression tests should encode discovered GitHub quirks.  
**Rejected alternatives:** Implementing GitHub interactions solely from naïve REST expectations was rejected because the document records production failures caused by that approach. Treating these behaviors as incidental rather than architectural was rejected because they affect core PR workflow correctness.