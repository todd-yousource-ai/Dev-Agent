# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform built as a **two-process system**:

- **Swift macOS shell**
  - Owns UI, authentication, biometric gating, Keychain access, project lifecycle, local orchestration, update/install integration, and the authenticated bridge to the backend.
- **Python backend**
  - Owns planning, consensus generation, repository analysis, document ingestion/retrieval, PR decomposition, code/test generation, review, self-correction, lint/fix loops, CI orchestration, and GitHub operations.

The system is intentionally split so that:

- **Secrets and user identity remain in the Swift trust boundary**
- **Model execution and repository mutation logic remain in the Python execution boundary**
- **Neither process executes generated code**
- **All cross-process communication is explicit, authenticated, and message-based**

The platform consumes repository state, operator intent, and technical requirements documents (TRDs), then transforms them into an ordered implementation pipeline that emits typed pull requests against GitHub. Every stage is constrained by explicit contracts, security controls, and deterministic state transitions defined across the TRDs.

At a high level, Forge operates as:

1. Operator opens the macOS app.
2. Swift shell authenticates the user and unlocks required secrets.
3. Shell launches Python backend with a per-session authenticated Unix socket.
4. Operator selects a repository/project and loads specifications.
5. Backend ingests repository/docs, builds document retrieval context, and assesses intent scope/confidence.
6. Backend produces a PRD/PR plan.
7. For each unit of work, backend runs a multi-model generation pipeline:
   - dual-provider generation
   - Claude arbitration / consensus
   - self-review
   - lint gate
   - iterative fix loop
   - CI execution
8. Backend opens a draft PR through GitHub.
9. Operator reviews/approves/merges.
10. System advances to the next planned PR.

This is **not a chat product** and **not an autocomplete system**. It is a directed, review-gated, policy-constrained build agent.

---

## Subsystem Map (one entry per subsystem: what it does, what it enforces)

### 1. macOS Application Shell
**Primary spec:** TRD-1  
**What it does:**
- Packages the product as a native `.app`
- Owns app startup, lifecycle, session bootstrap, and module wiring
- Hosts SwiftUI root navigation and screens
- Manages project selection and app-level state
- Launches and supervises the Python backend
- Owns XPC / socket bridge bootstrap and operator-visible error handling
- Integrates installation/update flow including Sparkle

**What it enforces:**
- Process separation between shell and backend
- Swift-side ownership of identity and secrets
- Session-scoped startup sequencing
- UI state consistency and main-thread-safe rendering
- Fail-closed behavior when backend/auth/bootstrap invariants are not satisfied

---

### 2. Authentication and Identity
**Primary spec:** TRD-1, TRD-11  
**What it does:**
- Authenticates the operator
- Performs biometric gate / local auth
- Tracks session lifecycle
- Resolves stored identity attributes such as display name, engineer ID, and GitHub-derived user profile
- Gates backend startup and sensitive operations on authenticated state

**What it enforces:**
- No privileged backend session without successful local authentication
- Identity must be established explicitly, never inferred
- Session state must be revocable and time-bounded
- Security-sensitive actions require an authenticated local session

---

### 3. Secret Storage / Keychain
**Primary spec:** TRD-1, TRD-11  
**What it does:**
- Stores secrets in macOS Keychain
- Holds credentials such as engineer ID and GitHub App/private-key-related material
- Supplies secrets only to the Swift trust boundary
- Delivers required credentials to backend over the authenticated bridge when allowed

**What it enforces:**
- Secrets are never persisted in backend-owned plaintext storage
- Secret access is explicit and auditable
- Secret delivery is gated by active authenticated session
- Backend receives only the minimum secret material required for current operation

---

### 4. SwiftUI Interface Layer
**Primary spec:** TRD-1, TRD-8  
**What it does:**
- Presents root app navigation, cards, panels, status, progress, review surfaces, and control affordances
- Displays pipeline progress, errors, PR status, review controls, and repo/project state
- Captures operator intent, exclusions, lens selections, and review commands

**What it enforces:**
- UI reflects authoritative state from orchestrators, not inferred state
- Unsafe or invalid operator actions are disabled when prerequisites are unmet
- Progress/error surfaces must map to real backend states/events
- Review commands are explicit operator actions, not implicit automation

---

### 5. Backend Process Host
**Primary spec:** TRD-1  
**What it does:**
- Runs bundled Python 3.12 backend
- Accepts session bootstrap parameters from Swift
- Initializes service graph for planning, generation, review, GitHub, retrieval, and telemetry
- Maintains backend-local job state and pipeline execution context

**What it enforces:**
- Startup only through shell-mediated authenticated launch
- No unauthenticated standalone backend control plane
- Per-session isolation using socket path + nonce/bootstrap contract
- Deterministic shutdown and surfaced startup failure reasons

---

### 6. Authenticated IPC / XPC Bridge
**Primary spec:** TRD-1; implementation hints include `Crafted/XPCBridge.swift` and `src/xpc_server.py`  
**What it does:**
- Connects Swift shell and Python backend over an authenticated Unix socket with line-delimited JSON messages
- Transports requests, responses, progress updates, status changes, and error events
- Delivers credentials/bootstrap data from shell to backend
- Carries operator commands and backend pipeline events

**What it enforces:**
- Every session is bound to explicit bootstrap secrets/nonces
- Message framing and schemas are strict
- Backend cannot assume trust solely from process locality
- Connection failures, deadlocks, or early shell crashes fail closed with surfaced error states

---

### 7. Intent Assessment and Scope Control
**Primary spec:** README behavior, planning TRDs, security references in TRD-11  
**What it does:**
- Accepts plain-language operator intent
- Assesses confidence and scope before committing implementation
- Supports operator adjustments such as file/directory exclusions
- Prevents over-broad changes by constraining candidate work areas

**What it enforces:**
- Generation does not begin until intent is sufficiently scoped
- Operator-visible scope controls remain authoritative
- Exclusions are respected through planning, review, and fix loops
- Scope expansion must be explicit, not automatic

---

### 8. PRD Planner / Work Decomposition Engine
**Primary spec:** planning-related TRDs referenced in README  
**What it does:**
- Converts intent + repository + spec corpus into an ordered PRD plan
- Decomposes plan into a sequence of typed pull requests
- Establishes dependency order between PRs
- Produces machine-consumable implementation units for downstream pipeline stages

**What it enforces:**
- Work must be decomposed into reviewable, logical units
- PR order must respect dependency graph
- Planning artifacts must remain consistent with repository state and loaded specs
- No direct monolithic repo rewrite path

---

### 9. Consensus Engine
**Primary spec:** TRD-2  
**What it does:**
- Runs two-model generation in parallel
- Uses Claude and GPT-4o as providers
- Uses Claude as final arbitrator on every result
- Produces merged or selected implementation output from competing generations
- Supplies rationale, confidence, and decision traces to later stages

**What it enforces:**
- No single-provider output is accepted as final without arbitration
- Arbitration is mandatory for result acceptance
- Provider disagreement must be resolved explicitly
- Retry/fallback rules are deterministic; provider substitution is controlled

---

### 10. Provider Adapters
**Primary spec:** TRD-2  
**What it does:**
- Encapsulates API-specific logic for each model provider
- Normalizes prompts, responses, errors, token accounting, and capability differences
- Supports consensus engine fan-out and result collection

**What it enforces:**
- Provider-specific quirks do not leak into core orchestration contracts
- Errors are normalized into backend-standard categories
- Token/session limits are enforced before or during calls
- Unsupported provider behavior fails explicitly

---

### 11. Prompt / Context Assembly Layer
**Primary spec:** TRD-2, TRD-10, TRD-7  
**What it does:**
- Builds prompts from operator intent, repository state, retrieved documents, product context, and stage-specific instructions
- Calls retrieval functions such as `auto_context()`
- Injects spec/document context into generation, review, and repair stages

**What it enforces:**
- Context assembly is stage-aware and bounded
- Retrieved documents are filtered and relevance-ranked
- Product context injection is automatic where required
- External/untrusted content is handled under prompt-injection controls

---

### 12. Document Store and Retrieval Engine
**Primary spec:** TRD-10  
**What it does:**
- Ingests repository documents and technical specs
- Chunks content and stores embeddings/indexes under  
  `~/Library/Application Support/Crafted/cache/{project_id}/`
- Maintains retrieval indexes per project
- Supplies relevant context for generation, planning, filtering, and review

**What it enforces:**
- Retrieval state is project-scoped
- Index lifecycle is deterministic from project creation onward
- Re-embedding is required when embedding model changes
- Document retrieval must never silently cross project boundaries

---

### 13. Repository Analyzer / File Selection
**Primary spec:** planning and review TRDs; TRD-10 for document filtering  
**What it does:**
- Examines repository structure and candidate files
- Applies include/exclude patterns
- Identifies likely implementation/test targets
- Feeds file subsets into planning, generation, and review

**What it enforces:**
- Excluded paths are never mutated
- Candidate selection remains bounded to scoped work
- Repository metadata, CI files, Swift files, Python files, tests, etc. are routed to correct workflows
- Full-rebuild or repo-wide edits are treated as anomalies when not justified

---

### 14. Code Generation Pipeline
**Primary spec:** README pipeline; TRD-2 and dependent backend TRDs  
**What it does:**
- Generates implementation artifacts for each PR unit
- Produces tests alongside code
- Writes candidate patches without executing generated code
- Hands output to review and correction stages

**What it enforces:**
- Generated code is data until committed; it is never directly executed
- Generation must remain within scoped files and accepted plan
- Tests are first-class outputs, not optional add-ons
- Stage transitions require structured outputs, not free-form text only

---

### 15. Self-Review / Critique Engine
**Primary spec:** review-related TRDs, TRD-6 references from TRD-10  
**What it does:**
- Reviews generated code against specs, context, and repository constraints
- Identifies gaps, risks, missing tests, contract violations, and quality issues
- Produces findings consumed by fix loops and operator review

**What it enforces:**
- Generation cannot proceed directly to PR without quality inspection
- Review is contextualized with retrieved documents and product rules
- Findings are structured and actionable
- Known exclusions/lenses constrain review scope

---

### 16. Lint Gate and Static Validation
**Primary spec:** backend pipeline TRDs  
**What it does:**
- Runs linting/static checks appropriate to repository language/components
- Blocks promotion of changes that fail syntactic or style gates
- Produces machine-readable diagnostics for repair

**What it enforces:**
- Lint failure blocks PR advancement
- Diagnostics must map to fixable file/rule locations
- Validation commands must not violate no-execute-generated-code policy beyond allowed project checks
- Gate outcomes are deterministic and surfaced

---

### 17. Iterative Fix Loop
**Primary spec:** backend pipeline TRDs  
**What it does:**
- Consumes compiler/lint/test/CI failures
- Generates targeted repair attempts
- Prioritizes fixes using failure evidence such as assertion identifiers and test names
- Respects operator exclusions during repair

**What it enforces:**
- Fixes are evidence-driven, not unconstrained rewrites
- Repair scope remains narrower than or equal to original PR scope
- The system does not switch providers arbitrarily when retry rules forbid it
- Repair terminates on configured limits or successful gate passage

---

### 18. Test Execution and CI Orchestration
**Primary spec:** README, CI workflow references  
**What it does:**
- Runs project tests locally or via CI pipeline as configured
- Interprets GitHub Actions results
- Distinguishes Python, Swift, and XPC integration jobs, including:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
- Uses CI status to decide PR readiness

**What it enforces:**
- PRs are opened only after required gates succeed or are explicitly categorized
- Platform-specific jobs run only when relevant files change
- CI results become authoritative status signals
- Accidental broad rebuild/test triggers are detectable anomalies

---

### 19. GitHub Integration Layer
**Primary spec:** GitHub/backend TRDs, TRD-11 for credential handling  
**What it does:**
- Authenticates as GitHub App / installation
- Calls GitHub APIs for repository reads, branch operations, commits, PR creation, and status polling
- Fetches current file content and SHA before writing updates
- Opens draft pull requests for operator review
- Fetches `/user` data on first auth where applicable

**What it enforces:**
- GitHub mutations require explicit, current repository state
- File updates use SHA-based optimistic concurrency
- Auth is based on signed GitHub App JWT and installation flow, not ad hoc PAT leakage
- PRs are draft-first and review-gated

---

### 20. Branching / PR Sequencer
**Primary spec:** README workflow  
**What it does:**
- Creates one branch/PR per logical unit
- Advances from approved PR to next planned PR
- Maintains dependency-aware ordering

**What it enforces:**
- Only one logical change unit per PR
- Later PRs must build on accepted earlier units where dependencies exist
- Sequencing is deterministic and operator-visible
- No implicit stacking outside planned dependency structure

---

### 21. Review Command and Lens System
**Primary spec:** review TRDs; examples include `/review start`, `/review exclude`, lens selection  
**What it does:**
- Allows operator to initiate focused reviews
- Supports path exclusions like:
  - `exclude src/legacy/`
  - `exclude src/old_api.py`
  - `exclude security in src/vendor/`
- Supports lens selection by IDs
- Records review notes and technical gaps

**What it enforces:**
- Review scope is operator-steerable and explicit
- Exclusion semantics are preserved through analysis and remediation
- Lens-based review remains bounded and explainable
- Review commands are parsed into structured backend actions, not interpreted loosely

---

### 22. Ledger / Audit Notes
**Primary spec:** command references such as `/ledger note <text>`  
**What it does:**
- Stores operator notes, decisions, or contextual annotations
- Associates notes with sessions/projects/reviews

**What it enforces:**
- Human decisions can be attached to machine workflow
- Audit context is explicit and durable enough for later review
- Notes do not mutate execution policy unless routed through proper control paths

---

### 23. Security Controls and Policy Enforcement
**Primary spec:** TRD-11  
**What it does:**
- Defines security rules for credentials, external content, generated code, CI, and trust boundaries
- Applies prompt-injection defenses, content handling policy, and fail-closed behavior
- Governs all security-relevant components across Swift and Python

**What it enforces:**
- Trust is asserted and verified explicitly
- Untrusted content cannot silently escalate authority
- Secrets stay in approved stores and channels
- Generated code is never executed as a shortcut
- CI, auth, and external content handling adhere to strict contracts

---

### 24. Telemetry / Progress / Error Reporting
**Primary spec:** TRD-1 and backend TRDs  
**What it does:**
- Emits progress messages over IPC
- Surfaces pipeline phase, failures, CI results, and operator-visible diagnostics
- Records performance anomalies and unusual conditions

**What it enforces:**
- Control decisions must be observable and explainable
- UI status must match backend state transitions
- Critical errors are surfaced with actionable category/reason
- Telemetry remains separate from control logic, though linked by identifiers

---

### 25. Update and Distribution Subsystem
**Primary spec:** TRD-1  
**What it does:**
- Ships as signed macOS app bundle
- Supports drag-to-Applications install
- Integrates Sparkle auto-update
- Operates under Developer ID distribution

**What it enforces:**
- Only signed, distributable builds are shipped
- Update path remains native and auditable
- App identity is preserved across releases
- Installed shell remains the only supported trust entrypoint

---

### 26. Build, Signing, and Certificate Operations
**Primary spec:** TRD-1 and operational docs  
**What it does:**
- Supports Developer ID signing
- Handles release artifact production
- Includes operational certificate rotation/revocation workflows

**What it enforces:**
- Release binaries must be signed with correct Developer ID identity
- Expired/revoked certs are operationally detectable
- Unsigned or mis-signed apps are not valid distribution artifacts

---

### 27. macOS Launch / Background Automation Constraints
**Primary spec:** operational notes in source docs  
**What it does:**
- Supports background or scheduled operational scripts where required
- Executes under macOS LaunchAgent/launchd semantics

**What it enforces:**
- Automation cannot rely on shell startup files like `.zshrc` or `.bash_profile`
- Environment assumptions must be explicit
- Operational tasks must remain compatible with launchd behavior

---

### 28. Storage Layout and Local Cache Management
**Primary spec:** TRD-1, TRD-10  
**What it does:**
- Stores app support files, project caches, retrieval indexes, and session-local artifacts
- Maintains per-project cache directories and lightweight persistent state

**What it enforces:**
- Cache content is project-scoped
- Secret material is not downgraded into ordinary cache storage
- Local persistence layout is stable and predictable
- Small indexes may remain loaded when allowed by design

---

## Enforcement Order (what calls what, in sequence)

The authoritative runtime call order is:

1. **App Launch**
   - macOS starts the signed Swift app bundle.
   - Shell initializes root modules, state containers, and UI.

2. **Local Authentication**
   - Shell performs session auth / biometric gate.
   - On success, identity context is restored.
   - On failure, privileged workflows remain unavailable.

3. **Secret Unlock / Session Preparation**
   - Shell resolves required Keychain material.
   - Session identifiers/bootstrap nonce are created.
   - Backend launch parameters are prepared.

4. **Backend Launch**
   - Shell starts bundled Python backend process.
   - Shell passes authenticated socket path + nonce/session bootstrap.
   - Backend binds/accepts only the expected authenticated channel.

5. **IPC Handshake**
   - Swift and Python exchange initial capability/session messages.
   - Credential delivery occurs only after handshake validation.
   - Any deadlock, early crash, or connection failure aborts session.

6. **Project Open / Repository Binding**
   - Operator selects project/repo.
   - Shell/backend establish active project context.
   - Backend initializes or opens project cache/index.

7. **Document Ingestion and Context Prep**
   - Document Store ingests TRDs/repo docs.
   - Embeddings/indexes are built or reused.
   - Retrieval engine becomes available to pipeline stages.

8. **Intent Submission**
   - Operator provides plain-language intent and optional exclusions/lenses.
   - Backend assesses scope/confidence.
   - If under-scoped or too broad, system requests adjustment before proceeding.

9. **Planning**
   - Planner produces PRD plan.
   - Planner decomposes plan into ordered typed PR units.
   - Dependency graph and execution order are fixed.

10. **PR Unit Execution**
    - Repository analyzer selects candidate files.
    - Prompt/context assembly fetches retrieved context.
    - Consensus engine invokes provider adapters in parallel.
    - Claude arbitrates result.
    - Candidate implementation and tests are produced.

11. **Quality Gates**
    - Self-review runs.
    - Lint/static validation runs.
    - Iterative fix loop consumes findings/failures.
    - Required tests/CI execute.

12. **GitHub Mutation**
    - GitHub layer authenticates via App flow.
    - Branch is created/updated.
    - Draft PR is opened.

13. **Operator Review**
    - UI shows diff, status, review findings, and commands.
    - Operator approves, requests changes, or merges externally/integrated flow.

14. **Sequenced Continuation**
    - On approved/merged prerequisite PRs, next PR unit begins.
    - Plan continues until complete or operator stops session.

---

## Component Boundaries (what each subsystem must never do)

### macOS Shell must never
- Execute generated code
- Delegate Keychain authority directly to arbitrary backend logic
- Assume backend trust without authenticated handshake
- Invent backend pipeline states not emitted by backend
- Store long-lived secrets in UserDefaults or project cache

### Python Backend must never
- Read Keychain directly
- Bypass shell-mediated authentication
- Assume local process equals trusted process
- Execute generated code
- Mutate files outside scoped/allowed work areas
- Create final outputs without arbitration/review/gating stages where required

### IPC Bridge must never
- Accept unauthenticated cross-process messages
- Treat malformed JSON or schema-violating messages as partial success
- Leak secrets into logs or unaudited channels
- Remain ambiguous about message origin or session identity

### Authentication subsystem must never
- Treat cached UI state as valid authentication
- Keep privileged session active after explicit revocation/expiry
- Allow biometric/auth failures to degrade into silent access

### Keychain subsystem must never
- Export secrets into project files, caches, or logs
- Deliver secrets before session/auth checks pass
- Expose more credential material than the active operation requires

### Consensus Engine must never
- Accept a single provider result as final without Claude arbitration
- Hide provider disagreement
- Substitute unsupported fallback behavior silently

### Provider Adapters must never
- Leak provider-specific exceptions unnormalized into orchestration
- Ignore token/session ceilings
- Drift from provider contract without explicit versioned handling

### Prompt / Context Assembly must never
- Inject untrusted external content as trusted instructions
- Cross-contaminate context between projects
- Ignore operator exclusions during context collection

### Document Store must never
- Retrieve content across project boundaries
- Continue using stale embeddings after embedding-model changes without re-embedding
- Persist secrets in retrieval indexes

### Planner must never
- Produce monolithic repo-wide plans when the task is decomposable
- Ignore dependency ordering
- Proceed when scope confidence is below required threshold

### Code Generation pipeline must never
- Execute its own output
- Bypass review/gating stages
- Expand scope opportunistically beyond approved plan

### Review subsystem must never
- Report findings without evidence/context
- Ignore configured exclusions or selected lenses
- Mutate code directly outside designated repair/orchestration paths

### Fix Loop must never
- Rewrite unrelated files to satisfy local failures
- Retry indefinitely
- Violate explicit “do not retry with the other provider” rules where specified

### Test/CI subsystem must never
- Treat missing required jobs as success
- Mask failing jobs behind partial pass states
- Trigger irrelevant platform jobs without change-based justification

### GitHub integration must never
- Write stale file content without SHA validation
- Use unauthorized credentials
- Open non-draft PRs where draft-first is required

### UI layer must never
- Present speculative security state as fact
- Allow unavailable actions to appear committed
- Misrepresent gate status or review status

### Telemetry subsystem must never
- Become the source of truth for authorization
- Omit critical failure categories needed for operator recovery
- Log sensitive content in violation of TRD-11

---

## Key Data Flows

### 1. Authentication and Session Bootstrap
**Flow:**
1. Operator unlocks app with local auth/biometric gate.
2. Swift shell reads required identity/secret material from Keychain.
3. Shell creates session nonce and socket path.
4. Shell launches Python backend.
5. Shell and backend complete authenticated handshake.
6. Shell transmits only necessary credential/session material.

**Guarantees:**
- Secrets originate only in Swift/Keychain boundary.
- Backend session is cryptographically/session-bound, not ambiently trusted.
- Failure at any step aborts privileged operation.

---

### 2. Project and Document Ingestion
**Flow:**
1. Operator selects project/repository.
2. Backend computes/open project ID and cache path.
3. Document Store ingests TRDs, repo docs, and indexed source context.
4. Chunks are embedded and stored.
5. Retrieval index is retained for later `auto_context()` and review use.

**Guarantees:**
- Data is namespaced under `cache/{project_id}/`.
- Re-ingest/re-embed behavior is deterministic.
- Retrieval remains local to active project.

---

### 3. Intent to Plan
**Flow:**
1. Operator enters intent.
2. Optional exclusions/lenses are attached.
3. Backend analyzes repository and retrieved specs.
4. Planner produces PRD plan and ordered PR units.

**Guarantees:**
- Human intent is translated into bounded, typed work units.
- Exclusions shape downstream execution.
- Plan order reflects dependencies.

---

### 4. Plan Unit to Generated Patch
**Flow:**
1. Current PR unit selected.
2. Repository analyzer identifies candidate files.
3. Context assembler retrieves relevant documents/spec chunks.
4. Consensus engine prompts Claude + GPT-4o in parallel.
5. Claude arbitrates and emits accepted result.
6. Candidate code and tests are written as patch set.

**Guarantees:**
- Generation is spec-aware and retrieval-augmented.
- Final result is arbitrated, not single-model raw output.
- Patch scope remains tied to unit boundaries.

---

### 5. Patch to Validated Change
**Flow:**
1. Self-review inspects patch.
2. Lint/static checks run.
3. Test execution and/or CI runs.
4. Failures feed fix loop.
5. Fix loop generates targeted corrections.
6. Repeat until pass or limit reached.

**Guarantees:**
- Validation is multi-stage.
- Repair uses evidence from failures.
- Exclusions and scope are preserved through repair.

---

### 6. Validated Change to Pull Request
**Flow:**
1. GitHub integration authenticates using GitHub App credentials.
2. Backend fetches current remote state / file SHA where needed.
3. Branch is updated.
4. Commits are pushed.
5. Draft PR is opened.

**Guarantees:**
- Remote writes use current repository state.
- Draft-first review posture is preserved.
- Operator receives reviewable, atomic units.

---

### 7. Review Control Flow
**Flow:**
1. Operator launches review or targeted lens review.
2. UI sends structured review command to backend.
3. Backend applies exclusions/lens filters.
4. Findings are returned with evidence and scope.
5. Operator may add ledger notes or request further action.

**Guarantees:**
- Review remains explicit and bounded.
- Human steering is first-class.
- Findings are explainable and reproducible.

---

### 8. CI Status Propagation
**Flow:**
1. Backend triggers or observes GitHub Actions.
2. Workflow/job results are normalized.
3. Progress/status events are sent over IPC.
4. UI updates job cards and gate status.
5. PR readiness is recalculated.

**Guarantees:**
- UI status derives from authoritative CI events.
- Platform-specific jobs are visible individually.
- Failure signals propagate back into repair or operator review.

---

## Critical Invariants

1. **Two-process separation is mandatory.**
   - Swift owns UI, auth, secrets.
   - Python owns intelligence, generation, and GitHub operations.

2. **Secrets never originate in the backend.**
   - Keychain is the source of sensitive material.
   - Backend receives only explicit, session-scoped deliveries.

3. **Every backend session is explicitly authenticated.**
   - Locality is not trust.
   - Socket path plus bootstrap nonce/handshake are required.

4. **Generated code is never executed by Forge as a shortcut.**
   - Validation may run repository-defined tooling/tests under controlled gates.
   - Direct execution of newly generated arbitrary code is forbidden.

5. **Single-model outputs are never final.**
   - Consensus requires dual-provider generation and Claude arbitration.

6. **Planning precedes implementation.**
   - Intent must be scoped and decomposed before code generation begins.

7. **One logical unit per PR.**
   - Work is emitted as sequenced, typed, reviewable draft PRs.

8. **Exclusions are hard constraints.**
   - Files/directories/security-review exclusions must survive all downstream stages.

9. **Project isolation applies to caches and retrieval.**
   - Document indexes, context stores, and project metadata cannot bleed across projects.

10. **Embedding model changes require re-embedding.**
    - Retrieval correctness depends on embedding/index compatibility.

11. **GitHub writes must be concurrency-safe.**
    - Current file state and SHA must be fetched before mutation where applicable.

12. **Draft-first is the default publication mode.**
    - Human review gates the progression of the plan.

13. **Telemetry is observable, not authoritative for trust.**
    - Auth and policy decisions come from control subsystems, not logs/status displays.

14. **Fail-closed behavior is required on trust boundary errors.**
    - Auth failure, handshake failure, secret delivery failure, CI ambiguity, and schema errors block progress.

15. **Prompt/context handling treats external content as untrusted.**
    - Retrieved docs and repository text cannot silently override system policy.

16. **Administrative and operational behavior must remain explicit.**
    - LaunchAgent environments, signing flows, update channels, and cert rotation must not depend on hidden machine state.

17. **Policy enforcement defaults to deny/block rather than suggest/warn.**
    - This follows the Forge architecture rules: enforcement over suggestion, explicit trust, explainable decisions, and separable-but-linked control planes.

18. **All control decisions must be explainable and reproducible.**
    - Inputs, exclusions, retrieved context, gate outcomes, and PR sequencing must be inspectable after the fact.

---