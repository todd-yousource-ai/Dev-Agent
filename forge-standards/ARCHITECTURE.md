# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform built as a **two-process system**:

- a **Swift macOS shell** responsible for UI, local trust boundaries, authentication, secret custody, lifecycle management, and operator-facing controls
- a **Python backend** responsible for planning, retrieval, consensus generation, review, Git/GitHub automation, and execution orchestration

The platform converts operator intent plus repository specifications into an ordered implementation pipeline that produces typed pull requests, runs validation and repair loops, and opens GitHub draft PRs for review. It is explicitly **not** a chat product and **never executes generated application code**.

Core architectural properties:

- **Native trust boundary on macOS**
  - Swift owns biometrics, Keychain, session state, and backend launch/orchestration.
- **Intelligence isolated in Python**
  - Python owns planning, context retrieval, multi-model generation, review, patching, CI interaction, and GitHub operations.
- **Authenticated local IPC**
  - Swift and Python communicate over an authenticated Unix domain socket using **line-delimited JSON**.
- **Spec-driven operation**
  - TRDs are authoritative inputs. System behavior must match documented interfaces, state machines, error contracts, and security controls.
- **Human-gated autonomy**
  - The platform proposes and implements changes, but operator review remains the approval boundary.
- **No execution of generated code**
  - Generated outputs are treated as untrusted content; validation is performed through repository tooling and CI, not by arbitrary execution of model output outside defined gates.

The platform is composed of the following major subsystems:

1. macOS Application Shell
2. Authentication and Identity
3. Secret Storage and Session Management
4. XPC/IPC Bridge and Backend Process Control
5. Project/Workspace Management
6. Planning Engine
7. Consensus Generation Engine
8. Provider Adapters
9. Prompt/Pipeline Orchestrator
10. Document Store and Retrieval Engine
11. Review and Static Analysis Engine
12. Fix Loop and Validation Gates
13. Git and Branching Orchestrator
14. GitHub Integration Layer
15. CI Observation and PR Lifecycle Management
16. SwiftUI Operator Interface
17. Telemetry, Logging, and Audit Surfaces
18. Security Enforcement Layer
19. Update/Distribution/Packaging subsystem
20. Background and system integration services

These subsystems are tightly ordered, but each has a distinct trust and authority boundary.

---

## Subsystem Map (one entry per subsystem: what it does, what it enforces)

### 1. macOS Application Shell
**What it does**
- Packages and launches Forge as a native `.app`
- Owns app lifecycle, process supervision, windowing, local state, and system integration
- Hosts the SwiftUI application and local controller graph
- Starts the Python backend with authenticated startup parameters
- Coordinates install/update behavior, including Sparkle auto-update

**What it enforces**
- The backend may only run under shell-controlled launch conditions
- UI and local trust actions must originate in the shell
- Sensitive local operations must stay outside the Python process
- All backend communication must pass through authenticated IPC

---

### 2. Authentication and Identity
**What it does**
- Performs operator authentication
- Supports biometric gate and session unlock flow
- Acquires and validates operator-linked credentials
- Maintains the authenticated local user/session state

**What it enforces**
- Authentication is explicit; trust is never inferred from app presence or prior activity alone
- Biometric/auth session gating must complete before sensitive actions
- Long-lived credential material is never delegated to the Python backend for storage
- Identity attributes are split across secure and non-secure stores according to sensitivity

Known identity storage boundaries from source material:
- `display_name` → `UserDefaults`
- `engineer_id` → Keychain secret
- `github_username` → fetched from GitHub `/user` on first auth

---

### 3. Secret Storage and Session Management
**What it does**
- Stores secrets in Keychain
- Controls session lifecycle
- Delivers required credential material to the backend only after local authorization
- Tracks session expiry and session-scoped access

**What it enforces**
- Swift is the sole custodian of durable secrets
- Python may consume secrets transiently for approved tasks but is not the system of record
- Session expiration and token limits block generation when limits are exceeded
- Credential delivery paths must be explicit and failure-recoverable

Relevant failure cases explicitly called out:
- deadlock in credential delivery path
- Swift shell crash before sending credentials
- XPC connection failed to establish

---

### 4. XPC/IPC Bridge and Backend Process Control
**What it does**
- Launches and supervises the Python backend
- Establishes the Unix socket channel
- Exchanges line-delimited JSON messages between processes
- Propagates progress, events, errors, and control commands

**What it enforces**
- Only authenticated local peers may exchange commands
- Startup requires shell-provided socket path and nonce
- Message framing is strict and machine-parseable
- Process boundaries remain intact: Swift does not implement generation logic; Python does not own local trust primitives

Implementation evidence referenced in source material:
- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`

---

### 5. Project/Workspace Management
**What it does**
- Registers repositories/projects
- Maintains project identifiers, metadata, and cache paths
- Maps a project to local working directories and backend retrieval state
- Creates project-scoped cache/index directories

**What it enforces**
- All stateful derived artifacts are project-scoped
- Document indices and cached retrieval artifacts live under:
  `~/Library/Application Support/Crafted/cache/{project_id}/`
- Project creation initializes an empty retrieval index
- Workspace operations must not escape the declared repository root

---

### 6. Planning Engine
**What it does**
- Interprets operator intent against repository specs
- Assesses scope confidence before implementation
- Decomposes intent into an ordered plan/PRD sequence
- Further decomposes each plan unit into typed pull requests

**What it enforces**
- Work must be structured into reviewable logical units
- Scope must be assessed before code generation begins
- Planning artifacts derive from operator intent plus loaded specifications, not unconstrained model improvisation
- Plans are ordered and resumable

---

### 7. Consensus Generation Engine
**What it does**
- Runs the dual-provider implementation workflow
- Obtains outputs from two model providers in parallel
- Uses Claude as arbitrator over generation results
- Produces implementation candidates, tests, and corrections

**What it enforces**
- Multi-model agreement is used to increase implementation reliability
- Arbitration is explicit, not implicit majority voting
- Provider failure handling is constrained; one provider failure does not automatically trigger fallback to the other in disallowed paths
- Consensus operates on retrieved project context and typed task inputs

From source notes:
- “Do NOT retry with the other provider” is a defined control in at least one failure path.

---

### 8. Provider Adapters
**What it does**
- Encapsulates model-specific APIs, prompt formatting, request/response normalization, token accounting, and error mapping
- Shields the rest of the backend from provider-specific protocol differences

**What it enforces**
- Upstream logic interacts with a normalized provider contract
- Provider credentials remain isolated behind approved access paths
- Token/session limits are measurable and enforceable
- Provider-specific failures become stable internal error categories

---

### 9. Prompt/Pipeline Orchestrator
**What it does**
- Runs the staged implementation pipeline
- Injects system, project, and retrieval context
- Sequences generation, self-correction, lint gate, review, fix loop, CI check, and PR creation
- Owns command/reply routing inside the backend

**What it enforces**
- Generation proceeds through defined stages rather than arbitrary tool use
- Required context is injected per stage
- Downstream stages consume typed outputs from upstream stages
- Unsafe or malformed outputs are filtered before they can affect repository state

---

### 10. Document Store and Retrieval Engine
**What it does**
- Ingests technical documents and repository context
- Chunks, indexes, and stores retrievable context for generation and review
- Provides `auto_context()` and stage-specific retrieval
- Supports document filtering for pipeline stages

**What it enforces**
- Retrieval is project-scoped and deterministic from indexed content
- Context injection must come from the indexed corpus, not ad hoc memory
- Model context is bounded and explainable
- Re-indexing is required when embedding model changes

Documented characteristics from source material:
- Depends on app shell file layout/project schema and consumes/serves context to generation/review subsystems
- Stores under `cache/{project_id}/`
- Empty index created on project creation
- FAISS index is kept loaded; explicit unload is unnecessary due to small memory footprint
- Changing the embedding model requires full re-embedding

---

### 11. Review and Static Analysis Engine
**What it does**
- Reviews generated diffs before PR creation
- Applies security and correctness “lenses”
- Detects suspicious patterns, policy issues, and implementation gaps
- Accepts operator-specified exclusions and lens selection

**What it enforces**
- Generated changes are analyzed before promotion to PR
- Review scope can be narrowed explicitly, never implicitly
- Lens selection and exclusions are operator-visible and auditable
- Injection-like or unsafe content patterns are surfaced

Operator controls surfaced in source material:
- `adjust scope`
- `exclude files`
- `select lenses`
- `/review start`
- `/review exclude`

Examples:
- exclude `src/legacy/`
- exclude `src/old_api.py`
- exclude security lens in `src/vendor/`

Also indicated:
- detection note: `[NOTE: this chunk triggered injection pattern detection]`

---

### 12. Fix Loop and Validation Gates
**What it does**
- Executes post-generation validation steps
- Runs lint/test gates
- Iteratively fixes failing outputs using structured error signals
- Scores and prioritizes corrective actions from test failures

**What it enforces**
- No PR is opened directly from first-pass generation
- Validation failures drive bounded repair loops
- Failure parsing must be structured and reproducible
- Full rebuilds should not be triggered unnecessarily by narrow changes

Observed gate-related details from source content:
- scoring signals include:
  - `+2 per failing assertion identifier found`
  - `+1 per FAILED test name`
- catches accidental full rebuild triggering
- CI/test gates are first-class pipeline stages

---

### 13. Git and Branching Orchestrator
**What it does**
- Applies file modifications to the local repo
- Creates branches per logical unit of work
- Maintains clean commit structure
- Prepares changesets for GitHub push and PR creation

**What it enforces**
- One logical unit maps to one reviewable PR branch
- Repository mutations occur only through controlled backend paths
- Branching and commit operations are tied to plan units
- Workspace state must remain attributable to a plan step

---

### 14. GitHub Integration Layer
**What it does**
- Authenticates to GitHub
- Fetches repository metadata and current file state
- Pushes branches
- Opens and updates draft PRs
- May use GitHub App or token-backed flows depending on subsystem design

**What it enforces**
- Remote mutations require explicit authenticated GitHub identity
- File updates must use current remote SHA for conflict detection where API-based writes apply
- GitHub credentials are acquired via shell-controlled secure storage path
- Remote operations are resumable and error-classified

Explicit flow fragments from source material:
- fetch file content from GitHub
- generate JWT using App private key from Keychain
- read current file → get content + SHA
- conflict detection is part of update flow

---

### 15. CI Observation and PR Lifecycle Management
**What it does**
- Monitors CI status for opened PRs
- Surfaces pipeline state to the operator
- Decides whether a PR is ready for review progression or requires remediation
- Integrates repository-specific workflows

**What it enforces**
- PR readiness is based on actual CI state, not local optimism
- CI is externalized as an observable gate
- Platform-specific jobs are separated by concern

Referenced workflows/jobs include:
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- ubuntu Python main test job
- macOS Swift job only triggers for Swift-file changes

---

### 16. SwiftUI Operator Interface
**What it does**
- Presents root application UI, cards, panels, progress, review controls, and project views
- Shows plan state, generation status, PR progress, review results, and remediation prompts
- Accepts operator commands and adjustments

**What it enforces**
- The UI is the only supported operator control surface
- State transitions are visible and attributable
- Sensitive actions occur behind explicit interaction boundaries
- Review, scope adjustment, and approval are human-readable and actionable

---

### 17. Telemetry, Logging, and Audit Surfaces
**What it does**
- Records progress events, pipeline outcomes, error states, operator commands, and review decisions
- Provides observability across shell and backend
- Supports diagnosis of failures across IPC, auth, generation, and CI

**What it enforces**
- Decisions and failures must be explainable and reproducible
- Cross-process operations need correlation identifiers
- Security-sensitive data must not be emitted as raw secrets
- Operator-visible state must correspond to backend truth

---

### 18. Security Enforcement Layer
**What it does**
- Applies the product-wide security model
- Separates trust, identity, policy, telemetry, and enforcement concerns
- Governs content handling, credential handling, generated code treatment, and CI safety

**What it enforces**
- Trust is asserted and verified explicitly
- Local agents minimize friction without weakening enforcement
- Enforcement defaults to deny/block, not suggest
- Generated code and external content are always treated as untrusted until validated
- Policy decisions must be observable and reproducible

This subsystem is cross-cutting and informed by the explicit architecture rules:

- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Forge components must default to policy enforcement, not policy suggestion.
- Local agents must minimize user friction while preserving strong enforcement guarantees.
- Administrative workflows must be simple, explicit, and understandable in plain language.
- Protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments.

---

### 19. Update/Distribution/Packaging Subsystem
**What it does**
- Delivers the native app bundle
- Supports drag-to-Applications installation
- Handles signed distribution and Sparkle-based updates
- Integrates Apple Developer signing/notarization requirements

**What it enforces**
- Only signed and valid app artifacts are distributed
- Update channels are controlled and auditable
- Packaging must preserve the shell/backend trust boundary
- Release artifacts match the expected app path and signing identity

Referenced packaging detail:
- `$GITHUB_WORKSPACE/build/Release/Crafted.app`
- `Developer ID Application: YouSource.ai ({TEAM_ID})`

---

### 20. Background and System Integration Services
**What it does**
- Integrates with macOS background facilities where required
- Supports scheduled maintenance/health tasks
- Handles environment caveats of launched agents

**What it enforces**
- Background jobs must not rely on interactive shell startup files
- System services must operate deterministically under launchd-style environments
- Health checks should be explicit and low-risk

Referenced note:
- LaunchAgent does not source `.zshrc` or `.bash_profile`

---

## Enforcement Order (what calls what, in sequence)

The end-to-end enforcement chain is:

1. **Shell startup**
   - Swift app launches
   - local configuration, signing, and environment validation occur
   - UI state initializes in locked or unauthenticated mode as required

2. **Operator authentication**
   - user unlocks session
   - biometrics and/or credential checks complete
   - shell resolves identity attributes and secret availability

3. **Backend launch**
   - shell creates authenticated socket path and nonce
   - shell starts Python backend process with those launch parameters
   - backend binds/accepts only the expected local authenticated channel

4. **Session credential delivery**
   - shell sends only the session-approved credentials/config needed for backend operations
   - backend acknowledges readiness
   - failure here blocks all autonomous execution

5. **Project selection/open**
   - shell identifies repository/project
   - project metadata and cache directories are resolved
   - document store ensures project index exists

6. **Document ingestion / retrieval readiness**
   - backend ingests TRDs and selected repository context
   - embeddings/chunks/index are prepared or reused
   - retrieval layer becomes available for stage injection

7. **Intent capture**
   - operator specifies desired outcome
   - planning engine evaluates scope and confidence

8. **Plan decomposition**
   - intent becomes ordered PRD plan units
   - plan units become typed PR tasks/branches

9. **Context assembly**
   - retrieval engine executes `auto_context()`
   - pipeline stage-specific document filters run
   - prompt orchestrator assembles bounded context payloads

10. **Consensus generation**
    - provider adapters invoke both model providers
    - outputs are normalized
    - Claude arbitration selects/resolves implementation direction

11. **Self-correction and review preparation**
    - generated output is refined
    - review engine applies lenses and scope controls
    - suspicious/injection-like content is flagged

12. **Validation gates**
    - lint/tests/repository checks run
    - failure parser scores issues
    - fix loop iterates until success or bounded termination

13. **Git operations**
    - local changes are materialized on a task branch
    - commit(s) are created
    - branch is prepared for remote publication

14. **GitHub publication**
    - GitHub auth material is resolved
    - branch is pushed
    - draft PR is opened

15. **CI monitoring**
    - CI workflows execute
    - backend/shell surface real-time state
    - failures may trigger additional remediation

16. **Operator review**
    - user inspects PR, review lenses, CI results, and diffs
    - user approves/merges or requests changes
    - next planned unit proceeds only after gate conditions are met

This ordering is strict in the sense that later stages may not bypass earlier trust or validation stages.

---

## Component Boundaries (what each subsystem must never do)

### Shell must never
- generate code or own model reasoning logic
- persist secrets outside approved secure stores
- trust the backend without authenticated startup and message validation
- silently approve repository mutations on behalf of the operator

### Python backend must never
- become the durable source of truth for operator secrets
- bypass shell authentication/session gates
- execute generated application code arbitrarily
- mutate repositories outside declared workspace/project context
- invent trust decisions not grounded in explicit state or policy

### UI must never
- directly manipulate secrets
- call external providers or GitHub without going through controlled backend/shell paths
- represent speculative state as committed backend truth
- conceal validation failures or review exclusions

### Document store must never
- retrieve context across projects
- inject unindexed or unexplained content as authoritative context
- silently mix embedding/index versions
- operate without a project-scoped cache root

### Consensus engine must never
- treat a single provider response as consensus
- bypass arbitration
- ignore token/session policy limits
- silently switch providers in prohibited failure paths

### Review engine must never
- auto-waive security findings without explicit operator or policy basis
- expand exclusions beyond what the operator specified
- mutate code as part of passive review
- hide which lenses were or were not applied

### Fix loop must never
- run unbounded retries
- discard failing signals that should inform correction
- degrade scope discipline by rewriting unrelated repository areas
- mask persistent validation failures

### Git/GitHub layer must never
- push directly to protected main without the defined workflow
- write remote file content without conflict checks when API semantics require SHA matching
- operate with credentials not sourced from approved secret paths
- create PRs for unvalidated change bundles

### Security layer must never
- collapse identity, policy, telemetry, and enforcement into one opaque mechanism
- allow implicit trust inheritance where explicit assertions are possible
- convert enforcement to advisory-only behavior by default

### Background services must never
- assume interactive shell configuration
- depend on user shell dotfiles for required environment
- weaken local trust guarantees for convenience

---

## Key Data Flows

### 1. Authentication and session bootstrap
**Flow**
1. Operator opens Forge
2. Shell performs biometric/session unlock
3. Shell reads secure identity/secrets from Keychain and non-sensitive profile fields from local preferences
4. Shell launches backend with socket path + nonce
5. Shell delivers session-scoped auth material via authenticated IPC

**Properties**
- secrets originate and persist in Swift-owned secure storage
- backend receives only what is required to act
- all credential delivery is session-bounded

---

### 2. Project indexing and retrieval
**Flow**
1. Operator opens a project
2. Backend resolves `project_id`
3. Cache root `~/Library/Application Support/Crafted/cache/{project_id}/` is created if needed
4. TRDs/repository docs are chunked and embedded
5. Retrieval index is stored and kept loaded
6. Generation/review stages call retrieval APIs such as `auto_context()`

**Properties**
- retrieval is deterministic from project corpus
- indices are isolated per project
- embedding model changes invalidate prior embeddings and require re-embedding

---

### 3. Intent-to-plan decomposition
**Flow**
1. Operator provides a plain-language intent
2. Planning engine combines intent with loaded specs and repo context
3. Scope confidence is computed
4. Ordered plan units are generated
5. Each unit maps to one typed pull request

**Properties**
- planning precedes implementation
- units are intentionally review-sized
- plan structure is externally visible

---

### 4. Consensus generation
**Flow**
1. Pipeline orchestrator assembles stage prompt + retrieved context
2. Provider adapters call both models
3. Outputs are normalized
4. Claude arbitrates
5. Resulting patch/test proposal moves to review and validation stages

**Properties**
- parallel provider generation
- explicit arbitration
- normalized error handling
- no implicit trust in a single model output

---

### 5. Review and exclusion control
**Flow**
1. Generated diff enters review engine
2. Default or selected lenses execute
3. Operator may narrow scope via exclusions or lens selection
4. Findings are emitted with technical note / gaps / annotations
5. Pipeline either proceeds, pauses, or returns for correction

**Properties**
- exclusions are explicit and bounded
- review scope is operator-visible
- injection/security findings are preserved as auditable output

---

### 6. Validation and repair
**Flow**
1. Lint/test gates run
2. Failure signals are parsed
3. Scored repair targets are computed
4. Fix loop produces constrained modifications
5. Validation re-runs until pass or bounded failure

**Properties**
- failures are structured inputs, not free-form chaos
- retries are bounded
- validation gates are mandatory before PR publication

---

### 7. GitHub publication and PR lifecycle
**Flow**
1. Validated branch is prepared locally
2. GitHub auth is resolved
3. Branch is pushed
4. Draft PR is opened
5. CI workflows execute
6. CI states are surfaced in the UI
7. Operator reviews/approves/merges
8. Next plan unit begins

**Properties**
- CI is external confirmation, not optional metadata
- PRs are draft-first
- merge remains a human-governed boundary

---

### 8. Update and release delivery
**Flow**
1. CI produces signed app artifact
2. Build artifact path resolves to release app bundle
3. Signing/notarization/update metadata are applied
4. Sparkle or packaged distribution delivers update
5. Shell installs/updates under native macOS rules

**Properties**
- release artifacts remain signed
- native app trust chain is preserved
- update mechanism does not bypass shell security boundary

---

## Critical Invariants

1. **Two-process separation is mandatory**
   - Swift and Python have distinct responsibilities and trust levels.
   - No subsystem may collapse them into a single runtime.

2. **Swift owns local trust**
   - biometrics, Keychain, session state, and secure bootstrap stay in Swift.

3. **Python owns intelligence orchestration**
   - planning, retrieval, consensus, review, fix loops, and GitHub automation stay in Python.

4. **IPC must be authenticated**
   - backend launch requires shell-provided authenticated parameters.
   - unauthenticated local command channels are forbidden.

5. **Generated code is never inherently trusted**
   - it must pass review and validation gates before PR publication.
   - the system never executes generated code as an authority shortcut.

6. **Every repository mutation must be attributable**
   - to a project, a plan unit, a branch, a validation state, and an operator-visible workflow step.

7. **Retrieval is project-scoped**
   - no cross-project leakage of embeddings, context, or cached artifacts.

8. **Index/version coherence matters**
   - embedding model changes require re-embedding.
   - mixed-version semantic indices are invalid.

9. **Consensus requires explicit arbitration**
   - dual-provider generation without arbitration is insufficient.
   - single-provider success is not automatically equivalent to consensus.

10. **Validation gates are non-optional**
    - lint/test/review/fix-loop sequence cannot be skipped for convenience.

11. **PRs are the unit of autonomous delivery**
    - work is decomposed into logical, typed, reviewable pull requests.

12. **Human approval remains the governance boundary**
    - Forge automates implementation and PR creation, not unsupervised production deployment.

13. **Security enforcement defaults to block**
    - policy is enforced, not merely suggested.

14. **Decisions must be explainable**
    - planning, exclusions, findings, failures, and gates must be observable and reproducible.

15. **Background execution must be environment-stable**
    - no reliance on interactive shell dotfiles or unstated environment assumptions.

16. **Release artifacts must preserve platform trust**
    - signed, notarized, native macOS distribution is part of the security model, not a packaging afterthought.

17. **CI truth outranks local optimism**
    - a branch is not “done” until required CI and review conditions are satisfied.

18. **Failure handling must be explicit**
    - connection failures, credential delivery failures, provider failures, and GitHub conflicts must map to stable recoverable error paths.

19. **Scope control must remain explicit**
    - exclusions, selected lenses, and review narrowing are allowed only through visible operator actions.

20. **Forge architecture follows separable-but-linked control planes**
    - identity, policy, telemetry, and enforcement are distinct concerns and must remain so as the platform scales.