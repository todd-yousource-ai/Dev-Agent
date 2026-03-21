# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform built as a **two-process system**:

- a **Swift macOS shell** responsible for native application concerns, trust anchors, local identity, secrets, UI, update/install mechanics, operator interaction, and process orchestration
- a **Python backend** responsible for planning, consensus generation, document retrieval, code transformation, review, CI orchestration, GitHub operations, and repository automation

The platform is not a chat product. It is a **directed build agent** that converts technical requirements and operator intent into an ordered implementation pipeline that emits pull requests, one logical unit at a time.

At runtime, Forge ingests repository state and loaded TRDs/PRDs, derives a plan, generates and reviews candidate changes using multiple model providers, validates via CI and policy checks, and then opens draft pull requests for human review. The operator remains the merge authority.

The core architectural pattern is:

1. **Swift establishes trust and local control**
2. **Swift launches and authenticates Python**
3. **Python executes deterministic pipeline stages**
4. **Python reports progress and requests privileged actions through a narrow bridge**
5. **Swift owns user-facing state, secret material, and any privileged OS integration**
6. **Neither process executes generated code**

This separation is foundational to the security model and appears throughout the subsystem contracts.

---

## Subsystem Map (one entry per subsystem: what it does, what it enforces)

### 1. macOS Application Shell
**Primary spec:** TRD-1

**What it does**
- Packages Forge as a native `.app`
- Owns app lifecycle, installation, launch, and auto-update integration
- Hosts SwiftUI interface and native operator workflows
- Starts, supervises, and stops the Python backend
- Manages local application state and project/session state presentation
- Bridges all privileged local capabilities to Python via authenticated IPC

**What it enforces**
- Process separation between shell and backend
- No direct backend access to Keychain, biometrics, or privileged OS APIs
- Backend launch authentication using socket path and nonce
- Session lifecycle gating before sensitive actions proceed
- Shell-owned state model as the source of truth for UI-visible state

---

### 2. Native Authentication and Identity Subsystem
**Primary spec:** TRD-1, security requirements referenced by TRD-11

**What it does**
- Authenticates the operator with biometric or equivalent local gate
- Establishes the local trusted session
- Stores and retrieves operator identity material:
  - `display_name` in `UserDefaults`
  - `engineer_id` in Keychain
  - GitHub user identity fetched from `/user` on first auth
- Delivers credentials to backend only through controlled pathways

**What it enforces**
- Secrets remain shell-owned
- Biometric/session gates precede sensitive operations
- Identity assertions are explicit and auditable
- Session token/credential use is bounded and revocable
- Deadlock/crash conditions in credential delivery are surfaced as hard failures, not ignored

---

### 3. Secret Storage and Keychain Layer
**Primary spec:** TRD-1, TRD-11

**What it does**
- Stores GitHub App private key material, engineer identifiers, tokens, and other sensitive credentials in Keychain
- Supports secret retrieval only under approved shell execution paths
- Provides trust root for GitHub authentication and operator-scoped actions

**What it enforces**
- Python cannot read Keychain directly
- Secret retrieval is mediated, minimal, and purpose-bound
- Sensitive material is not persisted into backend cache, logs, prompts, or repository output
- Secret use is attributable to a specific shell-controlled flow

---

### 4. XPC / Authenticated IPC Bridge
**Primary spec:** TRD-1
**Relevant implementation references:** `ForgeAgent/XPCBridge.swift`, `src/xpc_server.py`

**What it does**
- Connects the Swift shell and Python backend
- Uses authenticated Unix socket communication with line-delimited JSON messages
- Carries:
  - progress events
  - operator action requests
  - credential handoff requests
  - errors
  - pipeline state updates
  - telemetry signals

**What it enforces**
- Backend messages must match explicit schemas/contracts
- Backend is authenticated at startup using test/launch socket path plus nonce
- Shell only exposes a limited command surface to backend
- Failure to establish the connection is fatal to orchestrated backend work
- Errors propagate over IPC if possible; process supervision handles the rest

---

### 5. SwiftUI Operator Interface
**Primary spec:** TRD-8, depends on TRD-1

**What it does**
- Presents project, plan, run, PR, review, and status surfaces
- Renders cards, panels, and state transitions for the operator
- Captures operator intent, exclusions, review commands, and approvals
- Displays pipeline progress and subsystem health

**What it enforces**
- Operator controls are explicit rather than inferred
- Approval, exclusion, and scope adjustments are intentional and inspectable
- UI state reflects shell-authoritative state, not speculative backend assumptions
- Security-sensitive actions remain gated by session/auth state

---

### 6. Python Backend Runtime
**Primary spec:** TRD-1, repository/runtime guidance from AGENTS/CLAUDE

**What it does**
- Hosts the intelligence and automation engine
- Runs planning, consensus generation, retrieval, code edit, review, GitHub, and CI logic
- Maintains per-project cache and work products under application support
- Serves IPC endpoint to shell

**What it enforces**
- No direct access to macOS trust primitives
- No execution of generated code
- All privileged actions must round-trip through shell or approved external APIs
- Pipeline stages are explicit and observable
- Work remains reproducible from repository state, documents, and logged operator inputs

---

### 7. Consensus Engine
**Primary spec:** TRD-2

**What it does**
- Executes two-model generation workflows in parallel
- Uses provider adapters for model-specific interactions
- Applies Claude arbitration across results
- Produces implementation artifacts, tests, and candidate edits for each pull-request unit

**What it enforces**
- Multi-provider generation is structured, not ad hoc
- Arbitration is required; results are not accepted on a single unreviewed provider response
- Context injection uses document retrieval rather than unconstrained repository dumping
- Provider failures follow defined error contracts
- Backend must not “retry with the other provider” as an implicit fail-open path where TRD forbids it

---

### 8. Provider Adapter Layer
**Primary spec:** TRD-2

**What it does**
- Abstracts individual LLM provider APIs and request/response normalization
- Encapsulates provider-specific prompt packaging, model selection, token accounting, and error mapping
- Feeds the consensus engine with standardized outputs

**What it enforces**
- Provider-specific behavior does not leak into higher-level orchestration contracts
- Token/session limits are checked explicitly
- Errors are classified and routed predictably
- Provider selection remains deterministic from pipeline configuration, not improvised at runtime

---

### 9. Planning and Work Decomposition Engine
**Primary specs:** README product flow, TRD set governing orchestration

**What it does**
- Converts operator intent plus loaded specifications into an ordered PRD plan
- Decomposes each PRD into a sequence of pull requests
- Maintains logical-unit granularity for implementation sequencing
- Supports bootstrap flows and agent-authored commit/PR metadata

**What it enforces**
- Pull requests are emitted one logical unit at a time
- Build order is explicit and reviewable
- Work decomposition is derived from specifications, not free-form generation
- Operator approval gates progression to the next PR

---

### 10. Document Store and Retrieval Engine
**Primary spec:** TRD-10

**What it does**
- Ingests project documents, technical requirements, and repository-adjacent documentation
- Chunks, embeds, indexes, and retrieves relevant context for generation and review
- Stores retrieval cache under:
  - `~/Library/Application Support/ForgeAgent/cache/{project_id}/`
- Provides `auto_context()` for generation and review consumers
- Supports doc filtering for pipeline stages and `PRODUCT_CONTEXT` auto-load behavior

**What it enforces**
- Context is targeted and query-driven
- Retrieval state is persisted per project
- Project creation initializes an empty index in `cache/{project_id}/`
- Embedding/index operations are isolated from source repository contents
- Re-embedding is required when embedding model changes
- Document retrieval supports explainable, bounded context injection

---

### 11. Repository Workspace and File Layout Manager
**Primary specs:** TRD-1, TRD-10, CI/bootstrap references

**What it does**
- Establishes repository directory structure
- Tracks source, tests, workflows, app code, and generated work surfaces
- Applies project schema assumptions needed by pipeline stages
- Differentiates mutable source files from generated artifacts and cache

**What it enforces**
- Cache lives outside the repository under application support
- CI-relevant paths are known and scoped
- Project structure is predictable for planning, diffing, and review
- Changes do not silently spill into unmanaged directories

---

### 12. Code Generation and Edit Pipeline
**Primary specs:** TRD-2 and downstream pipeline TRDs

**What it does**
- Produces proposed code changes and tests for the current PR unit
- Uses retrieval context plus repository state
- Emits concrete file edits rather than executable actions
- Coordinates stage-by-stage generation flow

**What it enforces**
- Generated code is never executed by Forge
- Generation is constrained by current task/PR scope
- File mutations are inspectable and diff-based
- Unsafe or out-of-scope edits can be excluded before fix/review cycles continue

---

### 13. Review Engine
**Primary spec:** TRD-6

**What it does**
- Performs multi-pass review over generated changes
- Consumes repository diffs, retrieval context, and review lenses
- Scans open PRs via `PRReviewIngester.scan_open_prs()`
- Supports operator-triggered review via `/review`
- Applies exclusions and lens selection before review runs

**What it enforces**
- All generated output passes through review before PR creation
- Review context is informed by the same retrieval substrate as generation
- Operator can explicitly exclude files, directories, or issues from review/fix scope
- Review findings are structured and actionable
- Review is a first-class stage, not optional best effort

---

### 14. Review Lens and Scope-Exclusion System
**Primary specs:** TRD-6 and operator command surfaces

**What it does**
- Allows selective review by lens ID
- Supports directory/file exclusions such as:
  - `exclude src/legacy/`
  - `exclude src/old_api.py`
  - `exclude security in src/vendor/`
- Supports scope adjustment before fixing or rerunning review

**What it enforces**
- Exclusions are operator-specified and explicit
- Lens application is scoped and inspectable
- Suppression is granular rather than silent global disablement
- Review/fix behavior remains reproducible from declared exclusions

---

### 15. CI Orchestration Layer
**Primary specs:** CI workflow references in source content

**What it does**
- Runs or triggers validation workflows for generated changes
- Integrates with repository workflows such as:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
- Collects CI results as part of PR readiness
- Detects accidental full rebuild triggers and related workflow regressions

**What it enforces**
- PRs are not advanced as ready artifacts without validation
- CI behavior is part of the deterministic pipeline
- Workflow file changes are visible and reviewable
- Validation scope includes both Python backend and macOS shell integration paths

---

### 16. GitHub Integration Layer
**Primary specs:** GitHub operations referenced across README and loaded requirements

**What it does**
- Authenticates as a GitHub App or approved identity
- Generates JWT from App private key in Keychain
- Calls GitHub REST/GraphQL APIs
- Reads current file content and SHA
- Creates branches, commits, draft PRs, comments, notes, and metadata
- Resolves GitHub username from `/user` endpoint on first auth

**What it enforces**
- GitHub auth material remains shell-rooted
- API fallbacks are controlled, e.g. GraphQL to REST on defined response conditions
- Commit/PR identity follows product naming conventions
- Repository mutations occur through GitHub API contracts, not uncontrolled local execution
- PR creation remains downstream of review and CI gates

---

### 17. Pull Request Lifecycle Manager
**Primary specs:** README execution model

**What it does**
- Opens one PR per logical implementation unit
- Keeps next work item blocked until operator review/approval of current work
- Tracks draft/open/reviewed/approved progression
- Supports claim/note/review command workflows in agent-led processes

**What it enforces**
- Sequential PR progression
- Human gate before merge progression
- PR metadata is tied to planned work decomposition
- Repository state changes remain attributable to a pipeline stage and operator state

---

### 18. Ledger / Operational Log Subsystem
**Primary specs:** command references and operational metadata requirements

**What it does**
- Records claims, notes, operator actions, and PR workflow events
- Supports commands such as:
  - `/ledger note <text>`
  - PR claim messaging like `forge-ledger[sara-chen]: claim PR #8`
- Stores auditable context for work coordination and later inspection

**What it enforces**
- Operator and agent actions are attributable
- Coordination state is explicit
- Informal coordination is converted into structured operational records
- Auditability is preserved across multi-step autonomous flows

---

### 19. Session Limit / Usage Governance
**Primary specs:** operational limits in loaded source content

**What it does**
- Tracks model/session token usage and budget conditions
- Blocks generation when session token totals exceed allowed limits
- Surfaces usage exhaustion as an explicit pipeline condition

**What it enforces**
- Hard limits fail closed
- Token exhaustion cannot silently degrade into unrestricted execution
- Provider/session budgets are checked before expensive generation continues

---

### 20. Security Policy and Enforcement Plane
**Primary spec:** TRD-11
**Cross-cutting authority:** all components

**What it does**
- Defines security requirements for credentials, external content, generated code, CI, and repository operations
- Constrains how each subsystem handles trust, identity, content ingestion, and privileged actions
- Provides the global security baseline for shell, backend, retrieval, generation, and GitHub mutation

**What it enforces**
- Trust is asserted and verified explicitly
- Identity, policy, telemetry, and enforcement remain separable but linked
- Components default to enforcement, not suggestion
- External content and generated artifacts are treated as untrusted unless explicitly validated
- Generated code is not executed
- Security controls are reproducible, observable, and explainable

---

### 21. Telemetry, Error Reporting, and Observability
**Primary specs:** TRD-1 plus cross-cutting contracts

**What it does**
- Emits progress updates over IPC
- Reports shell/backend failures
- Surfaces unusual runtime conditions such as:
  - biometric auth > 30 seconds
  - XPC connection failed
  - shell crashed before sending credentials
  - deadlock in credential delivery path
- Provides state required for diagnosis and reproducibility

**What it enforces**
- Errors are surfaced explicitly
- Telemetry remains linked to control decisions
- Observability does not imply hidden side effects
- Runtime failures do not silently convert into insecure fallback behavior

---

### 22. Distribution, Installation, and Update Subsystem
**Primary spec:** TRD-1

**What it does**
- Packages the app bundle
- Supports drag-to-Applications installation
- Integrates Sparkle auto-update
- Supports developer signing and certificate lifecycle procedures

**What it enforces**
- Native distribution path integrity
- Signed application identity
- Update path remains inside trusted application delivery channels
- Operational certificate handling is explicit and maintainable

---

### 23. Launch and Background Execution Integration
**Primary spec:** TRD-1 and operational notes

**What it does**
- Launches backend processes and supporting scripts under macOS constraints
- Supports launch-agent style execution environments where shell dotfiles are not sourced
- Supervises startup with explicit socket path and nonce values
- Coordinates test/runtime differences in backend startup

**What it enforces**
- Runtime does not depend on user shell profile initialization
- Launch environment assumptions are explicit
- Startup contract remains deterministic across app and test execution

---

## Enforcement Order (what calls what, in sequence)

The normal end-to-end enforcement sequence is:

1. **App launch**
   - macOS launches the signed Swift shell
   - shell initializes app state, UI state, local config, and update/status services

2. **Operator authentication**
   - shell performs biometric/session gate
   - shell loads operator identity from Keychain/UserDefaults
   - GitHub username is resolved if first-run auth requires it

3. **Backend bootstrap**
   - shell creates authenticated IPC endpoint parameters
   - shell starts Python backend with socket path and nonce
   - backend connects to shell bridge
   - shell verifies handshake and establishes authenticated session

4. **Project load**
   - shell selects/opens project
   - backend loads repository metadata and project schema
   - document store initializes or loads `cache/{project_id}/`
   - empty index is created for new projects

5. **Intent intake**
   - operator provides plain-language intent and any relevant spec set
   - planning engine derives PRD plan and PR sequence

6. **Context preparation**
   - document store ingests/updates source documents and retrieval index
   - retrieval engine computes relevant context slices for current task
   - doc filters and product-context loading rules are applied

7. **Generation**
   - consensus engine invokes provider adapters in parallel
   - candidate solutions are normalized
   - Claude arbitration selects or synthesizes approved result
   - session/token limits are checked before and during this stage

8. **Code edit staging**
   - backend emits concrete file changes and tests
   - no generated code is executed
   - diffs remain in inspectable repository form

9. **Review**
   - review engine runs multi-pass review
   - selected lenses apply
   - operator exclusions or scope adjustments are honored
   - findings feed targeted fix iterations

10. **Validation**
    - CI orchestration runs applicable workflows
    - backend collects pass/fail data
    - accidental workflow or rebuild regressions are detected

11. **GitHub mutation**
    - shell-mediated auth path provides required GitHub credentials
    - backend/GitHub layer creates branch, commit, and draft PR
    - PR metadata follows naming conventions and project plan mapping

12. **Operator gate**
    - shell UI presents draft PR and findings
    - operator reviews and approves or sends back
    - only after approval does the system proceed to the next PR unit

13. **Operational logging**
    - ledger records actions, notes, review events, claims, and state transitions

At every step, TRD-11 security controls constrain content handling, secret access, and trust boundaries.

---

## Component Boundaries (what each subsystem must never do)

### macOS Shell must never
- Execute generated code
- Delegate Keychain ownership to Python
- Allow backend to access unrestricted native APIs
- Infer trust in backend messages without authentication
- Treat UI state as authoritative if it conflicts with explicit session/security state

### Python Backend must never
- Access Keychain directly
- Bypass shell authentication/session gate
- Execute generated code, tests, or arbitrary repository code as part of generation
- Mutate repository state outside explicit pipeline actions
- Invent privileged capability outside IPC/API contracts

### Consensus Engine must never
- Accept unreviewed single-provider output as equivalent to arbitrated consensus where arbitration is required
- Silently substitute provider behavior on forbidden retry paths
- Pull unconstrained repository context into prompts
- Conceal provider disagreement or failure semantics

### Provider Adapters must never
- Leak provider-specific failure ambiguity into higher layers
- Ignore session/token budgets
- Persist secrets in prompts, logs, or cache
- Change task semantics to fit provider quirks

### Document Store must never
- Act as a hidden source of truth for project state
- Write retrieval cache into the source repository
- Use stale embeddings after embedding model changes without re-embedding
- Inject unbounded context into generation/review

### Review Engine must never
- Modify source without explicit fix-stage invocation
- Treat excluded paths as reviewed
- Suppress findings without operator-visible reason
- Become optional for generated changes

### CI Orchestrator must never
- Mark work validated without actual workflow evidence
- Hide failing workflow results
- Execute generated code outside approved validation contexts
- Ignore workflow mutations that affect trust or coverage

### GitHub Layer must never
- Store app private keys or long-lived credentials outside approved secret storage
- Mutate repository state without attributable auth context
- Open final-ready artifacts when review/validation gates failed
- Infer user identity without explicit authenticated API resolution

### UI Layer must never
- Invent backend state
- Hide security-relevant failures
- Collapse approval, review, and merge semantics into a single ambiguous action
- Make exclusions implicit

### Ledger/Telemetry must never
- Become the enforcement authority
- Record sensitive secret material
- Omit identity linkage for control-relevant actions
- Provide unverifiable summaries in place of event data

### Security Plane must never
- Depend on hidden operator assumptions
- Allow trust by convention alone
- Be implemented only as advisory logging
- Collapse policy, identity, and telemetry into an inseparable monolith

---

## Key Data Flows

### 1. Shell-to-backend startup flow
1. Shell allocates socket path and startup nonce
2. Shell launches Python backend with those parameters
3. Backend starts IPC server/client path as required
4. Backend authenticates using nonce
5. Shell marks backend session active only after successful handshake

**Security property:** backend identity is asserted before orchestration begins.

---

### 2. Secret delivery flow
1. Backend requests a credentialed operation
2. Shell checks session/auth state
3. Shell retrieves secret from Keychain if permitted
4. Shell delivers only the minimum needed material through approved channel
5. Backend performs external API action
6. Errors are reported over IPC or process supervision if IPC is unavailable

**Security property:** secrets remain shell-controlled and purpose-limited.

---

### 3. Document ingestion and retrieval flow
1. Project documents are discovered/loaded
2. Content is chunked and embedded
3. Embeddings are stored in project cache under application support
4. Retrieval query is generated for current pipeline stage
5. Relevant chunks are returned to generation/review consumers

**Security property:** context delivery is bounded, project-scoped, and reproducible.

---

### 4. Intent-to-PR flow
1. Operator enters intent
2. Planning engine derives PRD plan
3. Plan is decomposed into ordered PR units
4. Current PR unit is selected
5. Generation and review execute for that unit
6. CI validates result
7. Draft PR is opened
8. Operator approves before next PR begins

**Security/product property:** autonomy is sequenced and human-gated.

---

### 5. Generation flow
1. Current task and retrieval context are assembled
2. Provider adapters call both configured models
3. Candidate outputs are normalized
4. Claude arbitrates
5. Selected result becomes proposed edit set
6. Proposed edits are applied as diffs only

**Security property:** model output is treated as untrusted until arbitrated, reviewed, and validated.

---

### 6. Review/fix loop flow
1. Review engine scans generated diff
2. Lenses are selected
3. Operator exclusions are applied
4. Findings are emitted
5. Fix stage addresses allowed findings
6. Review reruns until pass/stop condition
7. CI begins only after review requirements are satisfied

**Security/property:** remediation remains controlled, scoped, and auditable.

---

### 7. GitHub mutation flow
1. Backend requests GitHub auth path
2. Shell retrieves/signs credentials as required
3. GitHub layer fetches current content/SHA if patching existing file
4. Branch/commit/PR actions are executed
5. Draft PR is created with agent naming conventions
6. Metadata and links are returned to UI and ledger

**Security property:** remote repository mutation is authenticated, attributable, and ordered after checks.

---

### 8. PR review ingestion flow
1. Operator runs `/review` or system scans open PRs
2. `PRReviewIngester.scan_open_prs()` enumerates targets
3. Review context is loaded from repository state and document store
4. Lens/exclusion choices are applied
5. Findings are emitted into review surfaces and logs

**Security/property:** open PR inspection is structured and operator-directed.

---

## Critical Invariants

1. **Two-process separation is mandatory**
   - Swift owns native trust and secrets
   - Python owns intelligence and automation
   - This boundary must not erode

2. **Generated code is never executed by Forge**
   - not during generation
   - not during review
   - not as a convenience fallback

3. **All trust must be explicit**
   - backend startup is authenticated
   - operator identity is authenticated
   - external API actions are authenticated
   - trust is not inferred from proximity or convention

4. **Secrets remain shell-owned**
   - Keychain is not exposed to Python
   - secret material is purpose-bound and minimally disclosed

5. **Every repository mutation is attributable**
   - to an authenticated identity
   - to a pipeline stage
   - to a specific PR/work item

6. **One logical unit per PR**
   - decomposition granularity is part of product behavior
   - sequencing is not optional

7. **Human approval gates progression**
   - the next PR does not proceed simply because a prior PR was generated

8. **Retrieval context is bounded and project-scoped**
   - document store augments generation/review
   - it does not replace repository truth
   - embedding model changes require re-embedding

9. **Review is mandatory for generated changes**
   - multi-pass review is part of the architecture, not a tool add-on

10. **Validation evidence is required**
    - CI pass state must come from actual workflow results

11. **Policy and enforcement fail closed**
    - session/token exhaustion blocks generation
    - IPC/auth failures block backend work
    - security exceptions surface as errors, not warnings-only bypasses

12. **Observability must explain control decisions**
    - errors, progress, approvals, exclusions, and claims are all inspectable
    - telemetry supports reproducibility, not hidden automation

13. **Cache is outside the repository**
    - application support storage holds retrieval/index artifacts
    - source repository remains clean and reviewable

14. **Launch behavior must not depend on interactive shell state**
    - launch agents do not source `.zshrc` or `.bash_profile`
    - runtime environment requirements must be explicit

15. **Security is cross-cutting but not implicit**
    - identity, policy, telemetry, and enforcement are separable
    - each decision path must remain understandable and auditable

---

## Architectural Notes

### Trust model
Forge follows the repository’s stated architecture rules:

- trust must never be inferred implicitly when it can be asserted and verified explicitly
- identity, policy, telemetry, and enforcement must remain separable but tightly linked
- control decisions must be explainable, observable, and reproducible
- components default to policy enforcement, not policy suggestion
- local agents minimize user friction while preserving strong enforcement guarantees
- administrative workflows remain simple and explicit
- protocol and enforcement logic are designed for future scale

These are not stylistic principles; they are system-shaping constraints.

### Storage model
Persistent local state is split by sensitivity and function:

- **Keychain** for secrets and sensitive identity material
- **UserDefaults** for low-sensitivity UI/profile state such as `display_name`
- **Application Support cache** for retrieval/index data under `cache/{project_id}/`
- **Repository working tree** for source-controlled artifacts only

### Failure model
Forge is designed to surface discrete failures rather than blur them together. Important hard-failure examples include:

- XPC connection failed to establish
- shell crashed before sending credentials
- deadlock in credential delivery path
- backend auth/nonce mismatch
- token/session limit exceeded
- review failed
- CI failed
- GitHub API mutation failed

Fallbacks are allowed only where specified by contract, such as defined API fallback behavior. Unspecified fallback is prohibited.

### Scalability direction
Although currently implemented as a local macOS shell plus bundled Python backend, the architecture already separates:

- identity
- policy
- telemetry
- orchestration
- generation
- repository mutation

That separation is consistent with future extension across endpoint, network, cloud, and AI runtime enforcement domains without redesigning the core trust model.

---