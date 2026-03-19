# Architecture — Forge Platform

## System Overview

Forge is a two-process, native macOS autonomous software build platform that transforms repository specifications and operator intent into reviewed GitHub pull requests. The platform is explicitly split into:

- a **Swift macOS shell** responsible for local trust, UI, secrets, operator gating, packaging, lifecycle, and interprocess orchestration
- a **Python backend** responsible for intelligence, planning, consensus generation, retrieval, review, CI orchestration, and GitHub mutation

The system is designed around one core architectural constraint:

- **generated code is never executed by the agent runtime**

Instead, Forge generates artifacts, writes them into a working tree, runs predeclared tooling and CI, and submits draft pull requests for operator review. Trust boundaries are enforced through explicit interfaces, authenticated local IPC, Keychain-backed credential custody, and policy-first workflow sequencing.

At the highest level, Forge executes the following loop:

1. operator selects a repository and loads specifications
2. shell authenticates the user and unlocks secrets
3. shell launches and supervises the Python backend
4. backend ingests repository and documents
5. backend decomposes intent into PRDs and PRs
6. backend performs generation using multiple model providers in parallel
7. backend arbitrates outputs through Claude-led consensus
8. backend runs staged review and CI checks
9. backend creates a draft GitHub pull request
10. shell presents progress, gates user actions, and sequences the next unit of work

The full platform is governed by the following system rules inferred from the loaded specifications:

- local trust is anchored in the Swift shell, not the Python process
- the shell owns authentication and secret storage
- the backend owns planning and code generation
- communication occurs over an authenticated Unix domain socket using line-delimited JSON
- no subsystem may infer trust implicitly when it can be asserted explicitly
- control decisions must remain explainable, observable, and reproducible
- generated outputs are reviewed, tested, and opened as PRs; they are not autonomously merged
- the operator remains the final approval authority for progression across gated workflow boundaries

## Subsystem Map

### 1. macOS Application Shell

**Primary source:** TRD-1  
**Implementation domain:** Swift 5.9+, SwiftUI, AppKit integration where needed

#### What it does

The macOS Application Shell is the native container for the entire product. It owns:

- app packaging and installation
- application lifecycle
- native windowing and SwiftUI presentation
- biometric gate integration
- Keychain interactions
- session lifecycle
- backend process launch and supervision
- authenticated IPC/XPC bridging
- project selection and local filesystem coordination
- progress/event projection into UI state
- update distribution via Sparkle
- crash-safe orchestration boundaries between trusted local components

#### What it enforces

- only the shell can access and release sensitive secrets into runtime workflows
- local sessions are gated by biometric or equivalent system authentication
- backend processes are supervised and restarted according to shell policy
- UI state reflects backend state through explicit event messages, not direct mutation
- local trust decisions are anchored in native APIs and OS trust stores
- backend actions requiring identity or secret material are mediated by shell-owned flows

---

### 2. SwiftUI Interface Layer

**Primary sources:** TRD-1, TRD-8  
**Implementation domain:** SwiftUI

#### What it does

The UI layer presents the operator-facing application surface, including:

- project onboarding
- repository and document selection
- progress views
- cards, panels, and stateful workflow surfaces
- approval/review controls
- gate prompts
- transcript and execution status visualization
- error presentation and retry affordances

#### What it enforces

- the product is not exposed as an unconstrained chat interface
- the operator interacts through directed workflow controls
- human approvals are explicit and stateful
- sensitive operations are surfaced with clear control boundaries
- workflow progression must remain understandable in plain language

---

### 3. Local Authentication and Session Gate

**Primary source:** TRD-1  
**Implementation domain:** Swift + LocalAuthentication + Keychain

#### What it does

This subsystem manages:

- biometric unlocking
- session open/close lifecycle
- gate-on-foreground and relock behavior
- authentication timing and timeout handling
- operator-presence verification before releasing secret-dependent capabilities

#### What it enforces

- secrets are unavailable until a valid local session is opened
- gates are never auto-answered
- foreground return, long-running unlock edge cases, and stale sessions are handled explicitly
- unusual authentication latency and credential-path deadlocks are treated as fault conditions

---

### 4. Secret Custody and Keychain Store

**Primary sources:** TRD-1, security rules referenced in AGENTS/CLAUDE  
**Implementation domain:** Swift

#### What it does

This subsystem persists and manages:

- GitHub credentials
- model provider credentials
- any operator-scoped integration secrets
- secure retrieval and release of secrets to authorized runtime consumers
- secret invalidation and rotation coupling with session state

#### What it enforces

- Python never becomes the root custodian of long-lived secrets
- secret release is explicit, bounded, and session-dependent
- local storage of credentials uses Keychain rather than ad hoc files
- credential delivery is mediated and auditable

---

### 5. Backend Process Host and IPC Bridge

**Primary sources:** TRD-1, repository notes referencing `ForgeAgent/XPCBridge.swift`  
**Implementation domains:** Swift shell + Python backend

#### What it does

This subsystem provides the two-process communication fabric:

- backend process launch
- process supervision
- authenticated Unix socket setup
- line-delimited JSON message transport
- request/response and event streaming semantics
- translation of backend progress into shell-observable state
- credential handoff only through controlled interfaces

#### What it enforces

- shell and backend remain isolated processes with explicit contracts
- no shared mutable in-process trust state exists across the language boundary
- messages are typed, structured, and authenticated
- backend cannot silently access shell-owned trust functions
- IPC is the only supported control plane between native shell and intelligence engine

---

### 6. Consensus Engine

**Primary source:** TRD-2  
**Implementation domain:** Python 3.12

#### What it does

The Consensus Engine is the core intelligence runtime. It:

- constructs prompts and execution context
- dispatches work to multiple model providers in parallel
- compares and reconciles candidate outputs
- uses Claude as the required arbitrating authority for final result selection
- structures generation into deterministic stages
- returns code, plans, reviews, and corrective actions to downstream pipeline stages

#### What it enforces

- multi-model generation is mandatory for target workflows
- arbitration is explicit, not implicit majority voting
- context injection is controlled and sourced from retrieval/document subsystems
- output quality is checked through staged review rather than single-pass generation
- no provider output is treated as trusted solely because it was returned successfully

---

### 7. Provider Adapter Layer

**Primary source:** TRD-2  
**Implementation domain:** Python

#### What it does

This layer abstracts external model providers behind a uniform interface:

- request normalization
- provider-specific authentication handling
- prompt formatting
- timeout/retry policy
- response normalization
- provider metadata capture
- model-specific capability routing

Providers explicitly include the dual-provider generation path described in product documents:

- Claude
- GPT-4o

#### What it enforces

- backend logic is provider-agnostic above the adapter boundary
- per-provider errors are normalized into common engine contracts
- provider identity remains visible for traceability and arbitration
- model outputs remain data artifacts, not executable actions

---

### 8. Planning and Decomposition Engine

**Primary sources:** README, loaded phase/workflow content, TRD references across planning docs  
**Implementation domain:** Python

#### What it does

This subsystem converts operator intent and project specifications into executable work units:

- derive PRDs from loaded TRDs/specifications or bootstrap cases
- sequence PRDs in dependency-aware order
- decompose each PRD into a sequence of implementation PRs
- checkpoint after each phase, operator response, and TRD generation
- support operator commands such as approve, correct, expand, split, merge, remove, adjust scope, and stop
- resume builds across interruptions at phase, PRD, or PR boundaries

#### What it enforces

- work is partitioned into logical, reviewable units
- operator intent is converted into explicit plan state
- planning changes are transcripted and checkpointed
- no hidden reprioritization occurs outside plan state transitions
- operator corrections modify plan topology explicitly

---

### 9. PRD/TRD Boundary Management

**Primary sources:** loaded interaction patterns around split/merge/move/remove/approve  
**Implementation domain:** Python

#### What it does

This subsystem governs specification boundary evolution during document-driven planning:

- infer candidate technical boundaries
- let operator split TRDs into narrower scopes
- merge overlapping boundaries
- move ownership of concerns between TRDs
- remove out-of-scope boundaries
- track completion and generated document state

#### What it enforces

- document scope remains explicit
- ownership of technical concerns is not duplicated silently
- structural changes to the specification graph are operator-visible
- generated planning artifacts stay aligned with approved boundaries

---

### 10. Build Pipeline Orchestrator

**Primary sources:** README, TRD references spanning backend workflow  
**Implementation domain:** Python

#### What it does

The orchestrator is the runtime coordinator for end-to-end work execution:

- consume approved plan state
- create build threads/checkpoints
- select current PRD and PR
- invoke generation stages
- coordinate review passes
- trigger CI
- open draft PRs
- advance to next unit after approval
- retry current unit from scratch when required

#### What it enforces

- only one well-defined workflow stage is active per unit
- progression follows the required sequence
- failure recovery is deterministic
- completed PRs gate entry to subsequent PRs
- draft PR creation occurs only after generation/review/CI sequence completion

---

### 11. Document Store and Retrieval Engine

**Primary source:** TRD-10  
**Implementation domain:** Python  
**Storage root:** `~/Library/Application Support/ForgeAgent/cache/{project_id}/`

#### What it does

This subsystem ingests, indexes, stores, and retrieves project documents for automatic context injection. It manages:

- repository and specification document ingestion
- chunking and indexing
- embeddings generation
- retrieval over project-local corpus
- auto-context resolution for generation calls
- document filtering during staged workflows
- persistence of retrieval artifacts in project-scoped cache

It is consumed by:

- Consensus Engine via `auto_context()`
- staged generation and review filters
- product context auto-loading paths

#### What it enforces

- generation context is drawn from approved, indexed project material
- retrieval is project-scoped
- cache layout is deterministic and local
- embedding model changes require explicit re-embedding
- retrieval is a data-source dependency, not a hidden side channel

---

### 12. Review Engine

**Primary sources:** README, TRD references for review context, staged workflow mentions  
**Implementation domain:** Python

#### What it does

The review engine performs a structured, multi-pass quality process over generated changes:

- review generated code and tests
- compare implementation against requirements
- inject retrieval-backed context into review
- identify defects, omissions, and contract mismatches
- feed corrections back into regeneration loops
- enforce pass sequencing before CI and PR creation

The product description specifies a **3-pass review cycle**.

#### What it enforces

- no generated change proceeds directly from first draft to PR
- review is staged and repeatable
- specification conformance is verified before GitHub mutation
- review context is grounded in the document store and current repo state

---

### 13. Repository Mutation and Working Tree Manager

**Primary sources:** README, CI/test references, bootstrap path examples  
**Implementation domain:** Python

#### What it does

This subsystem applies generated outputs into a local repository workspace:

- write or patch files in the checked-out repo
- honor inclusion/exclusion scope controls
- track changed files for review and CI
- preserve repository structure assumptions
- prepare branch state for PR submission

#### What it enforces

- file mutation is scope-limited
- excluded paths and files are never modified
- generated changes are materialized as repository diffs, not arbitrary commands
- repository operations stay tied to the active PR unit

---

### 14. Scope Filter and Exclusion Engine

**Primary sources:** loaded commands such as `exclude src/legacy/`, `exclude src/old_api.py`, `exclude security in src/vendor/`, `select lenses`  
**Implementation domain:** Python

#### What it does

This subsystem interprets operator scoping instructions and applies them to planning, review, and mutation:

- exclude directories
- exclude files
- exclude issue lenses in selected locations
- select subsets of analysis lenses
- constrain generation and remediation targets

#### What it enforces

- operator-directed exclusions are first-class constraints
- planning and review only target allowed regions
- scoped lens execution prevents accidental broad rewrites
- excluded domains remain outside automated enforcement and mutation

---

### 15. GitHub Integration Layer

**Primary sources:** README, commit/branch naming conventions in loaded content  
**Implementation domain:** Python

#### What it does

This subsystem performs GitHub-facing operations:

- branch creation and naming
- commit message construction
- push/pull remote operations
- draft PR creation
- PR metadata population from PRD/PR state
- claim or coordination conventions for engineer-scoped workflows

Observed naming patterns include:

- branch/message forms such as `forge-agent[{engineer_id}]: {message}`
- bootstrap commit style such as `forge-agent: add CI workflow`
- PRD-referenced commit forms such as `forge-agent[todd-gould]: PR007 implement idempotency key expiry`

#### What it enforces

- GitHub mutations occur only after local generation/review/CI gates
- naming and metadata remain machine-consumable
- PRs correspond to logical units, not unbounded change sets
- draft status preserves human review control

---

### 16. CI Orchestration and Validation Layer

**Primary sources:** README, workflow headings from loaded content  
**Implementation domains:** Python orchestration + GitHub Actions workflows

#### What it does

This subsystem validates generated changes using declared CI workflows, including at minimum:

- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`

It handles:

- selecting relevant CI checks
- monitoring results
- capturing failures into review/regeneration loops
- detecting accidental full rebuild triggers
- validating both backend and shell changes

#### What it enforces

- generated changes must survive declared validation workflows
- Swift/XPC integration paths are tested, not assumed
- Python and macOS subsystems are independently validated
- CI outcomes are incorporated into draft-PR gating

---

### 17. Documentation Regeneration Path

**Primary sources:** README mention of optional documentation regeneration  
**Implementation domain:** Python

#### What it does

After build completion, Forge can optionally regenerate documentation based on updated implementation state.

#### What it enforces

- documentation updates are sequenced after code generation workflows
- documentation regeneration remains optional and explicit
- document changes are derived from current repository state and approved work outputs

---

### 18. State Checkpointing and Transcript Store

**Primary sources:** loaded checkpoint rules:
- after each TRD generation
- after each phase completes
- after every operator response  
**Implementation domain:** Python with local persistence

#### What it does

This subsystem persists long-running workflow state:

- current phase
- generated TRDs/PRDs
- transcript of operator interactions
- active build thread
- current PRD and PR position
- restart/recovery markers

#### What it enforces

- interruption recovery is deterministic
- operator responses are durable state transitions
- no phase progression occurs without checkpoint persistence
- restart behavior is defined for mid-PR, between-PR, and post-PRD conditions

---

### 19. Update and Distribution Subsystem

**Primary source:** TRD-1  
**Implementation domain:** Swift + Sparkle

#### What it does

This subsystem packages and updates the macOS application:

- `.app` bundle distribution
- drag-to-Applications installation flow
- Developer ID signing/notarization assumptions
- Sparkle-based app updates

#### What it enforces

- trusted distribution path for the shell
- macOS-native update mechanics
- update delivery remains outside backend control
- app authenticity is rooted in Apple platform trust mechanisms

---

### 20. Security Control Plane

**Primary sources:** TRD-11 reference in AGENTS/CLAUDE, repository architecture rules  
**Implementation domains:** cross-cutting

#### What it does

This cross-cutting subsystem defines platform-wide security requirements for:

- credentials
- external content handling
- generated code handling
- CI interactions
- trust boundaries
- telemetry and observability coupling to enforcement
- explainability of control decisions

#### What it enforces

- trust is explicit and verifiable
- identity, policy, telemetry, and enforcement remain separable but linked
- defaults favor enforcement, not suggestion
- local agents minimize friction without weakening guarantees
- administrative and operator workflows remain explicit and legible
- architecture supports future scale across endpoint, network, cloud, and AI-runtime domains

---

### 21. Telemetry, Progress, and Observability Layer

**Primary sources:** TRD-1 progress message references, architecture rules requiring explainable and observable decisions  
**Implementation domains:** Swift + Python

#### What it does

This subsystem records and projects:

- workflow progress events
- stage transitions
- CI state
- backend health
- gate state
- operator decisions
- error and retry conditions
- reproducible control-path explanations

#### What it enforces

- control decisions are observable
- shell UI reflects backend progress from structured messages
- failures can be diagnosed from durable event/state streams
- policy enforcement remains inspectable after the fact

## Enforcement Order

The system operates through a strict call and trust sequence.

### A. Application startup and trust establishment

1. macOS launches the signed Forge shell
2. shell initializes native services, UI state, update hooks, and local configuration
3. shell verifies session state and presents local auth gate if required
4. local authentication subsystem validates operator presence
5. secret custody subsystem unlocks eligible credentials for the active session
6. shell launches Python backend under supervised process control
7. shell establishes authenticated Unix socket IPC
8. backend registers readiness and capability state
9. shell transitions UI into project/workflow-ready state

### B. Project ingestion and context preparation

1. operator selects repository and document/specification inputs
2. shell passes project configuration to backend over authenticated IPC
3. backend initializes checkpoint/transcript state for the project
4. document store ingests repository docs and specifications
5. document store chunks, embeds, indexes, and caches project corpus
6. planning subsystem loads operator intent and available specifications
7. retrieval subsystem becomes available for `auto_context()` and stage filters

### C. Planning and decomposition

1. planning engine analyzes intent, repo state, and specifications
2. PRD/TRD boundary manager proposes or updates technical boundaries
3. operator may approve, correct, split, merge, remove, move, expand, or stop
4. transcript and checkpoint state are persisted after each response
5. planner emits ordered PRD list
6. planner decomposes active PRD into ordered PR units
7. build orchestrator activates the first executable unit

### D. Generation, review, and arbitration

1. orchestrator requests retrieval-backed context for the active unit
2. consensus engine dispatches generation work to provider adapters in parallel
3. provider adapters call external models and normalize outputs
4. consensus engine performs arbitration with Claude as final arbiter
5. repository mutation manager writes candidate changes into workspace
6. review engine runs pass 1 with spec and repo context
7. if defects exist, orchestrator loops back into regeneration
8. review engine runs pass 2
9. if defects exist, orchestrator loops back into regeneration
10. review engine runs pass 3
11. if defects remain, unit fails or retries according to pipeline policy

### E. Validation and GitHub publication

1. CI orchestration layer selects required checks
2. tests/workflows run for Python, macOS, and XPC paths as applicable
3. failures are captured and returned to review/regeneration flow
4. on success, GitHub integration creates branch and commits changes
5. GitHub integration opens a draft pull request
6. shell presents result and awaits operator review/approval
7. if approved, orchestrator advances to next PR or PRD
8. if not approved, planner/review loop incorporates operator correction

### F. Recovery behavior

1. on interruption, startup loads checkpoint state
2. if mid-PR, retry current PR from scratch
3. if between PRs, start next PR
4. if PRD complete, start next PRD
5. transcript and progress are restored into shell UI

## Component Boundaries

This section defines what each subsystem must never do.

### macOS Application Shell must never

- perform autonomous code generation logic that belongs to the backend
- execute generated code
- permit Python direct Keychain access outside shell-mediated interfaces
- bypass session gating for secret release
- infer backend trust from process existence alone

### SwiftUI Interface Layer must never

- mutate backend state outside explicit commands
- expose unrestricted chat semantics as the primary product mode
- hide approval or gate consequences from the operator
- silently continue through blocked workflow states

### Local Authentication and Session Gate must never

- auto-answer a gate
- leave a foreground-return gate open indefinitely
- release secret-dependent capabilities without valid session state
- treat long biometric delays as normal success without explicit handling

### Secret Custody and Keychain Store must never

- store long-lived secrets in plaintext files
- release secrets directly to UI code without policy checks
- grant the backend unrestricted persistent secret possession
- couple secret lifetime to backend process lifetime instead of session policy

### Backend Process Host and IPC Bridge must never

- allow unauthenticated local message injection
- expose ad hoc shell internals to backend callers
- use unstructured or ambiguous IPC payloads
- collapse process isolation into shared-memory trust

### Consensus Engine must never

- execute generated code
- treat a single provider response as sufficient where consensus/arbitration is required
- bypass retrieval and review stages when the pipeline requires them
- conceal which provider produced a candidate output

### Provider Adapter Layer must never

- leak provider-specific failures without normalization
- obscure provider identity in arbitration logs
- execute provider-returned tool/code artifacts locally
- own workflow policy decisions above the adapter boundary

### Planning and Decomposition Engine must never

- mutate repository code directly
- skip checkpointing around operator-visible plan changes
- reorder approved work units silently
- advance after an operator stop command

### PRD/TRD Boundary Management must never

- duplicate ownership of the same concern across multiple boundaries without explicit operator approval
- persist structural changes without transcript/checkpoint updates
- collapse separate technical domains merely for implementation convenience

### Build Pipeline Orchestrator must never

- create GitHub PRs before review and CI completion
- continue across failed hard gates
- leave active workflow stage ambiguous
- treat partial unit completion as final success

### Document Store and Retrieval Engine must never

- read outside the approved project/document scope without configuration
- return opaque context without source traceability
- mix project caches across `project_id`
- silently ignore embedding model version changes that require re-embedding

### Review Engine must never

- approve changes based only on syntax or provider confidence
- skip required review passes
- ignore applicable spec context
- treat CI as a substitute for requirements review

### Repository Mutation and Working Tree Manager must never

- modify excluded files or directories
- execute arbitrary shell commands as a substitute for structured mutation
- blend unrelated PR changes into the active unit
- write outside the checked-out repository/workspace contract

### Scope Filter and Exclusion Engine must never

- treat exclusions as advisory only
- lose file/directory specificity
- allow lens execution to escape declared scope
- reinterpret operator exclusions without explicit confirmation

### GitHub Integration Layer must never

- merge pull requests autonomously
- create non-draft PRs when draft gating is required
- push changes that have not passed the required local pipeline
- generate opaque branch/commit metadata

### CI Orchestration and Validation Layer must never

- suppress failing checks
- conflate Python, Swift, and XPC validation results
- trigger broader rebuild/test scopes accidentally without surfacing that fact
- mark a unit valid before required workflows complete

### Documentation Regeneration Path must never

- overwrite source-of-truth specifications without explicit workflow intent
- run implicitly before code workflow completion
- fabricate documentation state disconnected from repository contents

### State Checkpointing and Transcript Store must never

- lose operator decisions between phases
- permit non-durable phase transitions
- recover into an ambiguous active unit
- overwrite transcript history without append semantics or equivalent auditability

### Update and Distribution Subsystem must never

- delegate update trust decisions to the Python backend
- install unsigned or untrusted shell binaries
- bypass macOS platform trust requirements
- mutate runtime application code outside controlled update channels

### Security Control Plane must never

- permit implicit trust where explicit verification is possible
- entangle policy with opaque execution behavior
- degrade enforcement into recommendation-only behavior
- lose explainability of control decisions

### Telemetry, Progress, and Observability Layer must never

- become the source of policy truth
- hide enforcement decisions from audit surfaces
- mutate workflow state without the orchestrator/control plane
- collect events without preserving causal sequence

## Key Data Flows

### 1. Secret release flow

1. operator opens Forge shell
2. shell requests biometric/session authentication
3. upon success, shell reads required credentials from Keychain
4. shell retains custody of long-lived secrets
5. shell supplies backend with only the credential material or derived access needed for current operations through controlled IPC
6. backend uses credentials for provider/GitHub calls within workflow scope
7. session close or relock revokes future secret-dependent operations

**Invariant:** long-lived credentials originate and remain rooted in shell-managed custody.

---

### 2. Project context ingestion flow

1. operator selects project and loads TRDs/specifications
2. shell sends configuration to backend
3. backend creates project-scoped cache and state directories
4. document store ingests files
5. chunker produces retrieval units
6. embedding pipeline encodes chunks
7. index persists under `~/Library/Application Support/ForgeAgent/cache/{project_id}/`
8. retrieval engine serves `auto_context()` and stage-specific document filters

**Invariant:** retrieval is project-local and reproducible from indexed source inputs.

---

### 3. Intent-to-plan flow

1. operator provides plain-language intent
2. planner combines intent with loaded specifications and repo state
3. planner proposes PRDs and PR sequence
4. operator may approve or modify boundaries/scope
5. transcript and checkpoint store persist every response
6. approved plan is handed to build orchestrator

**Invariant:** execution only proceeds from explicit, checkpointed plan state.

---

### 4. Consensus generation flow

1. orchestrator requests active-unit generation
2. retrieval engine provides context bundle
3. consensus engine formats prompts
4. provider adapters call Claude and GPT-4o in parallel
5. normalized results return to consensus engine
6. Claude arbitrates final accepted output
7. candidate implementation/test artifacts are emitted for mutation/review

**Invariant:** provider outputs are advisory candidates until arbitration completes.

---

### 5. Review correction loop

1. generated artifacts are written to workspace
2. review pass runs against requirements, repo state, and retrieval context
3. defects are recorded
4. orchestrator either regenerates or advances
5. cycle repeats for three review passes
6. successful review hands off to CI

**Invariant:** no first-pass output directly becomes a PR without staged review.

---

### 6. Validation-to-PR flow

1. CI layer selects workflows
2. Python tests run when backend changes are present
3. macOS unit tests run when shell/UI changes are present
4. XPC integration tests validate shell-backend bridge behavior
5. failures loop back into remediation
6. success triggers branch creation, commit, push, and draft PR creation
7. shell presents PR result for human review

**Invariant:** GitHub publication is downstream of successful validation.

---

### 7. Operator correction flow

1. shell displays question/proposal
2. operator answers with commands like approve, correct, expand, split, merge, move, remove, exclude, or stop
3. backend interprets command
4. plan/scope/boundary state is updated
5. transcript is appended
6. checkpoint is written
7. orchestrator resumes from newly approved state

**Invariant:** operator directives become durable control inputs, not transient chat text.

---

### 8. Recovery flow

1. interruption or restart occurs
2. shell relaunches backend and reestablishes session/IPC
3. backend loads transcript and checkpoint state
4. active project/unit is reconstructed
5. workflow resumes according to recovery rules:
   - mid-PR: retry current PR from scratch
   - between PRs: start next PR
   - completed PRD: start next PRD

**Invariant:** recovery semantics are deterministic and phase-aware.

## Critical Invariants

1. **Two-process separation is mandatory.**  
   Swift shell and Python backend are separate trust and execution domains.

2. **Shell owns trust anchors.**  
   Authentication, session state, Keychain access, and local secret custody belong to Swift.

3. **Backend owns intelligence, not authority.**  
   Planning, generation, review, retrieval, and GitHub logic are backend concerns, but authority to unlock secrets and local session trust remains with the shell.

4. **Generated code is never executed by Forge runtime.**  
   The platform may write code, test via declared tooling, and submit PRs, but it does not execute generated artifacts as agent logic.

5. **IPC is explicit and authenticated.**  
   Cross-process coordination occurs only through authenticated Unix socket communication with line-delimited JSON messages.

6. **Every control decision must be explainable and observable.**  
   State transitions, approvals, retries, and failures must be reconstructable from structured telemetry and checkpointed state.

7. **Operator approval is explicit.**  
   Gates are never auto-answered; approvals and corrections are durable workflow events.

8. **Planning state is checkpointed.**  
   After each phase, TRD generation event, and operator response, durable state must be written.

9. **Project context is retrieval-backed and scoped.**  
   Automatic context injection comes from the document store for the current `project_id`, not from hidden global memory.

10. **Consensus is multi-provider with explicit arbitration.**  
    Parallel provider outputs are normalized and arbitrated; Claude is the final arbiter per product definition.

11. **Review is staged.**  
    Generated outputs pass through a three-pass review process before publication.

12. **Validation is required before PR creation.**  
    CI workflows, including Python, macOS unit, and XPC integration checks where applicable, gate GitHub publication.

13. **GitHub publication is draft-first.**  
    Forge opens draft PRs for human review; it does not autonomously merge.

14. **Scope exclusions are hard constraints.**  
    Excluded directories, files, and lens scopes must never be mutated or analyzed outside declared bounds.

15. **Security controls are cross-cutting and policy-first.**  
    Trust must be explicit, enforcement must default on, and identity/policy/telemetry/enforcement remain separable but linked.

16. **Recovery behavior is deterministic.**  
    Resume behavior is defined by the last durable checkpoint and active workflow position.

17. **Distribution trust is native-platform rooted.**  
    The shell is packaged and updated through signed macOS-native channels, not backend-managed code delivery.

18. **Observability does not replace enforcement.**  
    Telemetry reports decisions; it does not authorize them.

19. **Repository mutations are unit-scoped.**  
    Each PR corresponds to one logical unit of work with controlled branch/commit metadata.

20. **The platform is workflow-directed, not chat-directed.**  
    Freeform text may supply intent or correction, but the architecture is built around typed stages, gates, plans, and enforceable transitions.