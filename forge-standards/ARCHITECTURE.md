# Architecture — Forge Platform

## System Overview

Forge is a two-process, policy-first autonomous software delivery platform for macOS that turns repository context, technical specifications, and operator intent into gated GitHub pull requests. The platform is structured around a strict separation of concerns:

- **Swift macOS Shell** owns local trust, UX, secrets, installation, session lifecycle, and operator control.
- **Python Backend** owns planning, retrieval, consensus generation, review, CI orchestration, GitHub interactions, and document synthesis.
- **Document Store** supplies retrieval-augmented context for all planning, generation, review, and documentation tasks.
- **Security and policy controls** apply across both processes and all external inputs, governed centrally by the platform security model.

The architecture is intentionally non-chat and non-executing:

- The system does **not** execute generated code locally.
- The system does **not** grant LLMs direct access to credentials.
- The system does **not** permit hidden trust transitions between UI, backend, document inputs, generated code, or remote systems.
- All progression from intent to pull request is staged, reviewed, observable, and operator-gated.

At runtime, the normal flow is:

1. Operator launches the macOS app.
2. Shell performs onboarding, biometric/session gate, settings validation, and secure backend startup.
3. Shell establishes an authenticated local IPC channel to the backend.
4. Operator imports documents and scopes a project/repository.
5. Backend parses and indexes documents into the Document Store.
6. Operator provides intent.
7. Backend creates a PRD plan, decomposes it into ordered pull requests, and processes each PR through generation, review, CI, and GitHub draft PR creation.
8. Operator reviews and approves each PR before the next PR proceeds.
9. On completion, backend may generate or refresh repository documentation artifacts such as `PRODUCT_CONTEXT.md` and TRDs.

This architecture follows the Forge rules:

- Trust is explicit, asserted, and verified.
- Identity, policy, telemetry, and enforcement are separate but linked.
- Control decisions are explainable and reproducible.
- Components default to enforcement.
- Operator friction is minimized without weakening guarantees.
- Local and remote workflows are explicit.
- Protocols and controls are designed to scale beyond this initial macOS-local form factor.

---

## Subsystem Map

### 1. macOS Application Shell
**Primary TRD:** TRD-1  
**What it does:** Native Swift/SwiftUI application container for packaging, onboarding, authentication, settings, process orchestration, secure secret handling, and presentation of pipeline state.  
**What it enforces:**
- Native app lifecycle and distribution model
- Session and biometric gating
- Keychain ownership for secrets
- Local process launch and restart policy
- Authenticated IPC boundary to backend
- UI state ownership and concurrency boundaries
- Observability via `os_log` and crash/reporting integration

### 2. SwiftUI Presentation Layer
**Primary TRD:** TRD-8  
**What it does:** Implements root views, navigation, cards, panels, settings, onboarding, notifications, menu bar behavior, dock integration, and operator review surfaces.  
**What it enforces:**
- Explicit operator review gates
- Stable state presentation of pipeline phases
- No direct business logic mutation outside view-model contracts
- No direct secret handling in views
- No direct backend bypass around shell-owned session/auth rules

### 3. Authentication and Session Lifecycle
**Primary TRD:** TRD-1, security requirements from TRD-11  
**What it does:** First-launch auth setup, biometric unlock, session creation, timeout, lock/unlock transitions, and secret access preconditions.  
**What it enforces:**
- Local user-presence requirement before sensitive operations
- Session-scoped access to credentials and backend launch
- Re-authentication on configured security boundaries
- No unauthenticated access to high-risk settings or operations

### 4. Secrets and Keychain Management
**Primary TRD:** TRD-1, TRD-11  
**What it does:** Stores and retrieves provider API keys, GitHub credentials/tokens, and other sensitive local configuration via macOS Keychain.  
**What it enforces:**
- Secrets remain owned by the Swift process
- Secrets are never persisted in plaintext app configuration
- Controlled credential delivery to backend
- Secret access only after local trust gates succeed

### 5. XPC / Local IPC Transport
**Primary TRD:** TRD-1  
**What it does:** Authenticated local communication between Swift shell and Python backend using a local Unix socket and line-delimited JSON protocol.  
**What it enforces:**
- Single explicit transport boundary between local control plane and intelligence plane
- Peer authentication and startup handshake
- Typed message framing and stateful command/response flow
- Prevention of unauthorized local process impersonation

### 6. Backend Process Manager
**Primary TRD:** TRD-1  
**What it does:** Launches, monitors, restarts, and tears down the Python backend; injects runtime configuration and credentials through approved mechanisms.  
**What it enforces:**
- Backend startup ordering
- Crash/restart policy
- Environment and working-directory constraints
- No backend execution before shell trust gates pass
- No backend self-escalation into shell-owned privileges

### 7. Planning Engine
**Primary TRD:** planning PRD/TRD set  
**What it does:** Converts repository context, technical documents, and operator intent into an ordered implementation plan, including PRD generation and PR sequencing.  
**What it enforces:**
- Work decomposition into logical, reviewable units
- Dependency-aware PR ordering
- Scope explicitness before code generation
- Alignment to imported specifications rather than freeform generation

### 8. Consensus Engine
**Primary TRD:** TRD-2  
**What it does:** Runs multi-provider generation using at least two models in parallel, compares outputs, and uses Claude as the arbiter on every result path.  
**What it enforces:**
- No single-model unilateral code authority
- Structured disagreement handling
- Arbitration before downstream acceptance
- Provider abstraction through stable interfaces

### 9. Provider Adapter Layer
**Primary TRD:** TRD-2  
**What it does:** Normalizes interactions with Claude, GPT-4o, and future providers under a shared contract for prompting, generation, and result capture.  
**What it enforces:**
- Provider-independent consensus semantics
- Prompt isolation and output normalization
- Error categorization per provider
- No provider-specific trust exceptions

### 10. Retrieval and Document Store
**Primary TRD:** TRD-10  
**What it does:** Imports technical documents, parses multiple file types, extracts metadata, chunks content, embeds chunks, stores vectors and metadata, and retrieves relevant context for all downstream LLM calls.  
**What it enforces:**
- Structured ingestion pipeline
- Stable chunking and embedding rules
- Metadata-preserving retrieval
- Context relevance for generation/review
- Document-origin traceability

### 11. Document Import Pipeline
**Primary TRD:** TRD-10  
**What it does:** Handles document import UX and backend parsing for TRDs, PRDs, architecture specifications, and related knowledge sources.  
**What it enforces:**
- Supported format validation
- Parse-failure error handling
- Metadata extraction standards
- Rejection or quarantine of invalid inputs where required

### 12. Prompt Construction Layer
**Primary TRD:** generation/review/security TRDs  
**What it does:** Builds generation, review, arbitration, improvement, and documentation prompts from intent, repo state, retrieved context, and pipeline stage.  
**What it enforces:**
- Stage-specific prompt templates
- Separation between system instructions, retrieved context, and user intent
- Injection-resistant treatment of external content
- Reproducible prompt assembly

### 13. Code Generation Stage
**Primary TRD:** generation pipeline TRD, “Stage 5: CodeGenerationStage”  
**What it does:** Generates implementation and tests for a scoped PR unit using consensus outputs and retrieved context.  
**What it enforces:**
- Generation only after planning/scoping gates pass
- Patch production scoped to intended files and tasks
- Requirement alignment against imported specs
- No code execution as part of generation

### 14. Three-Pass Review Stage
**Primary TRD:** “Stage 6: ThreePassReviewStage”  
**What it does:** Applies a structured multi-pass review cycle to generated changes before CI and PR creation.  
**What it enforces:**
- Independent review passes
- Defect discovery before remote submission
- Improvement loop bounded by explicit prompts and conditions
- No unreviewed generated output enters PR flow

### 15. Improvement / Fix Pass
**Primary TRD:** “10. Improvement Pass”, “11. Fix Execution”  
**What it does:** Runs targeted remediation when review or CI identifies defects; may create fix branches or correction iterations.  
**What it enforces:**
- Explicit trigger conditions
- Controlled remediation prompt lens selection
- Bounded retries and corrective scope
- Preservation of auditability across fix iterations

### 16. Conflict Detection and Dependency Safety
**Primary TRD:** “10. Conflict Detection”, “10.1 Pre-Start File Overlap Check”, “10.4 Unmet Dependency Warning”  
**What it does:** Detects file overlap, dependency conflicts, issue exclusions, and sequence hazards before and during PR execution.  
**What it enforces:**
- No overlapping concurrent modifications where prohibited
- No progression with unmet prerequisite work
- File/path exclusion rules
- Early conflict surfacing to operator and logs

### 17. CI Orchestration
**Primary TRD:** CI pipeline TRD, “10. Python Bundling in CI”, “11. Notarization Job”  
**What it does:** Validates generated changes through repository CI and platform packaging CI, including Python bundling and notarization for the macOS application where applicable.  
**What it enforces:**
- No PR promotion without CI status
- Artifact reproducibility checks
- Packaging correctness for app distribution
- Notarization/signing job boundaries for releaseable builds

### 18. GitHub Integration
**Primary TRD:** GitHub integration TRD, “10. GraphQL API”, “11. Webhook Receiver”, “11. Live Sync”  
**What it does:** Creates branches, commits changes, opens draft PRs, queries PR status, receives webhooks, and synchronizes local state with GitHub.  
**What it enforces:**
- Remote state as an external, validated source
- GraphQL/API error handling
- Draft-first PR creation
- Branch/PR lifecycle consistency
- No hidden merge behavior

### 19. Operator Review Gate
**Primary TRD:** “10. Operator Review Gate”  
**What it does:** Presents generated PRs, review findings, and CI outcomes to the operator for explicit approve/reject/proceed decisions.  
**What it enforces:**
- Human approval before next PR progression
- Visibility into scope and quality signals
- Pause semantics between autonomous units
- No fully silent end-to-end autonomous merge path

### 20. Repository Scoping and Project Context
**Primary TRD:** “11. Project Scoping”, “10.1 Gate 1 — Scope Confirmation”  
**What it does:** Establishes the target repository, allowed scope, task boundaries, and context material before generation begins.  
**What it enforces:**
- Repository-level target explicitness
- Scope confirmation before mutation planning
- Exclusion/inclusion constraints
- Prevention of accidental out-of-scope modification

### 21. PRODUCT_CONTEXT.md Generation
**Primary TRD:** “10. Phase 7: PRODUCT_CONTEXT.md Generation”  
**What it does:** Synthesizes repository/product context documentation from accumulated understanding after build completion or designated phases.  
**What it enforces:**
- Documentation generation as a post-build artifact, not a hidden side effect
- Traceability back to imported sources and observed repo state
- Separation from implementation generation stage

### 22. TRD Generation
**Primary TRD:** “11. Phase 8: TRD Generation”  
**What it does:** Produces technical requirements documents from repository state, product context, and observed architecture, when invoked by workflow.  
**What it enforces:**
- Structured technical specification output
- Explicit phase ordering after implementation/document context accumulation
- No substitution of generated TRDs for imported source-of-truth docs unless operator-directed

### 23. Logging, Telemetry, and Observability
**Primary TRD:** TRD-1, TRD-11  
**What it does:** Emits structured local logs, pipeline events, diagnostics, crash metadata, and security-relevant audit events.  
**What it enforces:**
- Privacy annotations for sensitive fields
- Reproducible event trails
- Explainability of control decisions
- Separation between operational telemetry and secret material

### 24. Security and Threat Defense Layer
**Primary TRD:** TRD-11  
**What it does:** Defines global controls for prompt injection defense, path security, generated-code risk handling, context poisoning resistance, dependency code injection mitigation, and adversarial LLM output handling.  
**What it enforces:**
- Untrusted-content classification
- Multi-layer prompt injection defense
- Path and file access constraints
- No execution of generated code
- Suspicion and containment of model outputs and imported context
- Security review requirements for external and generated artifacts

### 25. Update, Packaging, and Distribution
**Primary TRD:** TRD-1, release/build TRD  
**What it does:** Builds the `.app` bundle, supports drag-to-Applications installation, Sparkle auto-update, bundling of Python runtime, and notarized distribution.  
**What it enforces:**
- Signed, notarized app distribution
- Controlled update path
- Bundle integrity
- Versioned installation and migration behavior

### 26. Settings and Configuration Management
**Primary TRD:** TRD-1  
**What it does:** Persists non-secret settings in `UserDefaults`, handles migrations, exposes provider/API configuration, and drives security-sensitive option validation.  
**What it enforces:**
- Separation of secret vs non-secret configuration
- Schema/version migration behavior
- Validation before persistence where required
- No settings path that bypasses trust or review controls

---

## Enforcement Order

The platform is designed as a strict enforcement pipeline. Each subsystem calls the next only after its own invariants have been satisfied.

### 1. Application startup
1. **macOS Application Shell** launches.
2. **Settings and Configuration Management** loads persisted non-secret configuration and runs migrations.
3. **Authentication and Session Lifecycle** checks whether first-launch onboarding or unlock is required.
4. **Secrets and Keychain Management** becomes accessible only after successful local auth conditions.
5. **Backend Process Manager** starts the Python backend with approved configuration.
6. **XPC / Local IPC Transport** performs authenticated handshake and establishes command channel.
7. **Logging and Observability** records startup state, versions, and failures.

### 2. Onboarding and environment preparation
1. Operator completes **First-Launch Onboarding**.
2. Operator configures repository, provider credentials, and preferences through **Settings and Configuration Management**.
3. Shell validates credentials presence and required configuration.
4. **Repository Scoping and Project Context** establishes target repo and work scope.
5. **Document Import Pipeline** accepts TRDs/PRDs/spec documents.
6. **Retrieval and Document Store** parses, chunks, embeds, and indexes imported materials.

### 3. Intent-to-plan path
1. Operator submits intent.
2. **Repository Scoping and Project Context** confirms scope boundaries.
3. **Prompt Construction Layer** builds planning prompts from intent, repo metadata, and retrieved spec context.
4. **Planning Engine** generates ordered PRD/work plan.
5. **Conflict Detection and Dependency Safety** checks overlap, dependency ordering, exclusions, and unmet prerequisites.
6. **Operator Review Gate** may confirm plan or scope before execution proceeds.

### 4. Per-PR execution path
1. Select next planned PR unit.
2. **Conflict Detection and Dependency Safety** performs pre-start file overlap and dependency checks.
3. **Prompt Construction Layer** assembles generation prompt with retrieved context.
4. **Consensus Engine** dispatches to **Provider Adapter Layer** for parallel model generation.
5. **Consensus Engine** arbitrates outputs with Claude as required.
6. **Code Generation Stage** materializes proposed implementation and tests.
7. **Three-Pass Review Stage** performs structured review.
8. If issues are found, **Improvement / Fix Pass** runs targeted remediation and returns to review as allowed.
9. **CI Orchestration** validates resulting branch/build state.
10. **GitHub Integration** creates or updates branch, commit set, and draft PR.
11. **Operator Review Gate** blocks progression until operator decision.
12. On approval, planner advances to the next PR unit.

### 5. Post-build documentation path
1. After implementation sequence completion, **PRODUCT_CONTEXT.md Generation** may run.
2. **TRD Generation** may run as a later phase.
3. Outputs are surfaced through the shell for operator review and repository inclusion as configured.

### 6. Live sync and external feedback path
1. **GitHub Integration** receives webhooks or polls GraphQL status.
2. **Live Sync** updates local pipeline/PR state.
3. **SwiftUI Presentation Layer** refreshes operator-visible status.
4. **Logging and Observability** records state transitions and API errors.

### 7. Security enforcement path
Security checks are not a separate phase; they wrap every phase:
1. External content is classified as untrusted.
2. **Prompt injection defenses** sanitize and isolate imported content.
3. **Path security gates** validate file operations before patch application or branch preparation.
4. Generated output is treated as adversarial until review and CI clear it.
5. No generated artifact is executed locally.
6. Operator gate remains mandatory before workflow continuation where specified.

---

## Component Boundaries

This section defines what each subsystem must never do.

### macOS Application Shell must never
- Implement LLM planning, generation, arbitration, or retrieval logic.
- Store secrets in `UserDefaults`, logs, or plaintext files.
- Allow UI code to bypass auth/session gates.
- Execute generated code or repository code as part of agent workflow.
- Trust backend state without authenticated IPC and explicit message contracts.

### SwiftUI Presentation Layer must never
- Contain secret material directly.
- Own durable business state outside approved view models/store objects.
- Call external providers or GitHub directly.
- Make hidden workflow progression decisions without operator visibility.

### Authentication and Session Lifecycle must never
- Infer trust from app foreground state alone.
- Grant indefinite secret access without session policy.
- Expose biometric results directly to backend as a substitute for shell-controlled authorization.

### Secrets and Keychain Management must never
- Hand raw secrets to LLM providers.
- Serialize secrets into prompts, logs, crash reports, or documents.
- Permit backend self-service secret retrieval without shell mediation.

### XPC / Local IPC Transport must never
- Accept unauthenticated peer messages.
- Permit ambiguous framing or mixed message schemas.
- Act as a general-purpose plugin bus.

### Backend Process Manager must never
- Launch arbitrary child tools outside approved backend/runtime strategy.
- Escalate privileges or inherit unconstrained environment state.
- Continue silently after repeated backend integrity failures.

### Planning Engine must never
- Modify the repository directly.
- Skip explicit scope decomposition.
- Treat undocumented assumptions as requirements when imported specs exist.

### Consensus Engine must never
- Accept a single-provider result as equivalent to consensus when consensus is required.
- Bypass arbitration on disagreement or low-confidence paths.
- Mutate files or Git state directly.

### Provider Adapter Layer must never
- Leak provider-specific credentials into other provider contexts.
- Embed policy logic that changes consensus semantics per provider.
- Normalize away safety-relevant error conditions.

### Retrieval and Document Store must never
- Treat imported documents as trusted instructions.
- Lose document provenance during chunking or retrieval.
- Return context without metadata sufficient for traceability.
- Mutate source documents during ingestion.

### Document Import Pipeline must never
- Silently coerce unsupported formats into partial/truncated context.
- Ignore parse errors that would degrade retrieval correctness.
- Treat file names alone as trustworthy metadata.

### Prompt Construction Layer must never
- Merge user intent, system rules, and retrieved text without role separation.
- Permit external content to override platform instructions.
- Omit source boundaries in contexts that need them for reviewability.

### Code Generation Stage must never
- Execute generated or target-repo code locally.
- Write outside scoped repository/file boundaries.
- Advance changes directly to GitHub without review and CI stages.

### Three-Pass Review Stage must never
- Be skipped for generated code.
- Collapse all review objectives into a single undifferentiated pass.
- Hide review findings from later audit/telemetry.

### Improvement / Fix Pass must never
- Loop indefinitely.
- Expand fix scope beyond triggering defects without explicit approval.
- Overwrite prior review history.

### Conflict Detection and Dependency Safety must never
- Ignore file overlap or unmet dependency conditions.
- Permit hidden concurrent mutation of the same scoped areas.
- Resolve conflicts by silently dropping work.

### CI Orchestration must never
- Be treated as optional for PR-ready changes.
- Execute arbitrary generated payloads outside the repository’s defined CI process.
- Report success without capturing actual remote/local CI outcomes.

### GitHub Integration must never
- Merge PRs autonomously unless explicitly specified by future requirements.
- Treat webhook payloads as implicitly trusted without validation.
- Drift local state from remote state without surfacing sync errors.

### Operator Review Gate must never
- Auto-approve on behalf of the user.
- Conceal scope, review findings, or CI status required for decision-making.
- Permit automatic progression when a human decision is required.

### Repository Scoping and Project Context must never
- Allow ambiguous target repository selection.
- Permit out-of-scope file mutation.
- Ignore explicit exclusions or dependency order constraints.

### PRODUCT_CONTEXT.md Generation must never
- Rewrite source-of-truth imported specifications silently.
- Masquerade inferred behavior as verified fact without basis.
- Run as an invisible side effect of unrelated phases.

### TRD Generation must never
- Replace imported TRDs as authoritative source without operator intent.
- Present generated requirements as enforced platform behavior unless adopted.
- Omit traceability to observed context.

### Logging, Telemetry, and Observability must never
- Emit secrets or raw credential values.
- Collapse security events into generic log noise.
- Make control decisions unverifiable after the fact.

### Security and Threat Defense Layer must never
- Assume model output is safe because it passed generation.
- Allow imported documents to act as executable instruction authority.
- Trust paths, dependencies, or generated patches without validation.
- Allow “convenience” exceptions that bypass core controls.

### Update, Packaging, and Distribution must never
- Ship unsigned or unnotarized release artifacts where notarization is required.
- Update application code through uncontrolled channels.
- Bundle runtime components without version and integrity control.

### Settings and Configuration Management must never
- Persist secrets in non-secret stores.
- Accept invalid or incomplete critical settings silently.
- Perform migrations that alter security posture without explicit schema logic.

---

## Key Data Flows

## 1. Secret and credential flow
**Origin:** Operator enters provider/API credentials in settings.  
**Path:**
1. SwiftUI settings form captures secret input.
2. Shell validates format/basic constraints.
3. Secret is written to macOS Keychain.
4. Non-secret references/status may be persisted in `UserDefaults`.
5. On authenticated backend startup or provider call preparation, shell retrieves secret from Keychain.
6. Secret is delivered to backend only through approved shell-mediated runtime channels.

**Controls:**
- Keychain-only durable storage
- Session/biometric gate before retrieval
- No secret exposure in logs, prompts, documents, or telemetry

## 2. Document ingestion and retrieval flow
**Origin:** Operator imports TRDs/PRDs/specs.  
**Path:**
1. UI submits import request to backend.
2. Document Import Pipeline validates type and parses content.
3. Metadata is extracted.
4. Content is chunked according to Document Store strategy.
5. Chunks are embedded.
6. Embeddings + metadata are stored in retrieval index.
7. Later prompt assembly retrieves relevant chunks by query.
8. Retrieved chunks are attached to planning/generation/review prompts with source metadata.

**Controls:**
- Parse error handling
- Provenance retention
- Imported text treated as untrusted context, not executable instruction
- Injection-aware prompt assembly

## 3. Intent-to-plan flow
**Origin:** Operator provides plain-language intent.  
**Path:**
1. Intent is submitted through the shell.
2. Backend combines intent with repository scope and retrieved specification context.
3. Planning prompts are constructed.
4. Planning Engine generates PRD/work plan.
5. Conflict/dependency validation runs.
6. Plan is exposed to operator and execution scheduler.

**Controls:**
- Scope confirmation gate
- Dependency checks
- Traceable plan artifacts
- No direct code generation before planning completes

## 4. Per-PR generation flow
**Origin:** Next planned implementation unit.  
**Path:**
1. Scheduler selects PR unit.
2. Relevant repository context and document context are retrieved.
3. Prompt Construction Layer creates provider-ready prompts.
4. Provider Adapter Layer invokes multiple models.
5. Consensus Engine compares and arbitrates outputs.
6. Code Generation Stage materializes candidate patch and tests.
7. Review stage inspects candidate output.
8. Improvement loop runs if needed.
9. Final candidate enters CI.

**Controls:**
- Multi-model generation
- Claude arbitration
- No code execution
- Security checks on content, paths, and dependencies
- Review before CI/PR creation

## 5. Branch/PR publication flow
**Origin:** Reviewed, CI-eligible change set.  
**Path:**
1. Backend prepares branch state.
2. GitHub Integration creates or updates branch.
3. Commit(s) are pushed.
4. Draft PR is opened via API.
5. PR metadata and status are synchronized locally.
6. Operator reviews in app and/or GitHub.

**Controls:**
- Draft-first PR policy
- GraphQL/API error handling
- Sync status visible to operator
- No autonomous merge implied

## 6. Review and fix loop flow
**Origin:** Review findings or CI failure.  
**Path:**
1. Findings are classified by stage.
2. Improvement prompt is constructed with defect-specific lens.
3. Fix branch or corrective iteration is generated.
4. Changes re-enter review.
5. If CI-related, CI reruns after accepted fix.
6. On success, publication resumes.

**Controls:**
- Explicit fix triggers
- Bounded retries
- Scope-limited remediation
- Full event history retained

## 7. Live sync flow
**Origin:** Remote GitHub state changes.  
**Path:**
1. Webhook receiver or GraphQL poll obtains remote update.
2. Payload/status is validated and mapped to local entities.
3. Backend updates pipeline state.
4. Shell receives state updates over IPC.
5. UI refreshes and notifications may be posted.

**Controls:**
- External payload validation
- Error-classified sync failures
- No hidden state mutation outside auditable event path

## 8. Documentation synthesis flow
**Origin:** Build completion or explicit documentation phase.  
**Path:**
1. Repository state, imported docs, and execution artifacts are gathered.
2. Retrieval/context assembly constructs documentation prompts.
3. PRODUCT_CONTEXT.md and/or TRDs are generated.
4. Outputs are surfaced for review and repository inclusion.

**Controls:**
- Separation from implementation path
- Traceability to source context
- Generated docs are reviewable artifacts, not implicit truth

---

## Critical Invariants

1. **Swift owns trust; Python owns intelligence.**  
   The shell controls secrets, local auth, session state, and backend lifecycle. The backend must not become the trust anchor.

2. **No generated code is executed locally by the agent.**  
   Generation, review, and packaging workflows must not run generated code as part of local agent behavior. Validation occurs through defined CI mechanisms, not arbitrary local execution.

3. **All external content is untrusted by default.**  
   Imported documents, repository content, dependencies, webhook payloads, provider responses, and generated code all enter through explicit validation and containment paths.

4. **Consensus is mandatory where specified.**  
   A single provider output cannot substitute for the required multi-model consensus + Claude arbitration path.

5. **Operator approval is a first-class enforcement point.**  
   The platform may automate planning, generation, review, and PR creation, but not silently erase the human decision boundary where required.

6. **Secrets never cross into durable insecure storage.**  
   Credentials must remain in Keychain or equally protected transient memory paths; they must never appear in `UserDefaults`, logs, prompt bodies, or generated artifacts.

7. **Prompt roles must remain separated.**  
   System rules, operator intent, retrieved context, repository evidence, and model outputs must not be collapsed into a single unstructured trust domain.

8. **Retrieval quality is architecture-critical.**  
   Chunking, embeddings, metadata retention, and retrieval relevance directly affect every downstream subsystem; ingestion correctness is not optional infrastructure.

9. **Planning precedes mutation.**  
   The system must define scope, dependencies, and PR ordering before code generation starts.

10. **Review precedes publication.**  
    Generated changes must pass structured review before CI/PR publication.

11. **CI precedes PR readiness.**  
    A change set is not considered ready for operator review as a valid implementation unit until required CI states are available.

12. **Path and scope constraints are mandatory.**  
    No subsystem may modify files outside the explicitly scoped repository and allowed path set.

13. **Every control decision must be observable.**  
    Security gates, scope blocks, conflict detections, review findings, CI outcomes, and sync failures must be surfaced through logs and/or operator-visible state.

14. **Remote state is authoritative for remote objects; local state is authoritative for local trust.**  
    GitHub owns PR/branch truth; the shell owns local auth/session/secrets truth. Neither side should be inferred from the other.

15. **Generated documentation is derivative unless adopted.**  
    Synthesized `PRODUCT_CONTEXT.md` or TRDs are outputs of the platform, not automatically the new source of truth.

16. **Security controls must compose across stages.**  
    Prompt injection defense, path security, dependency scrutiny, and adversarial-output handling are layered protections, not one-time checks.

17. **Failure must degrade safely.**  
    On parse failures, provider errors, IPC failures, auth issues, CI ambiguity, or sync uncertainty, the platform must stop or quarantine progression rather than guess.

18. **Explainability is part of correctness.**  
    If a reviewer cannot reconstruct why the system planned, generated, blocked, or published something, the architecture has failed an explicit requirement.

19. **Distribution integrity matters as much as runtime integrity.**  
    Bundling, signing, Sparkle updates, Python packaging, and notarization are architectural trust boundaries, not release afterthoughts.

20. **Subsystem boundaries are security boundaries.**  
    The separation between UI, secrets, backend intelligence, retrieval, review, CI, and GitHub is intentional and must not be collapsed for convenience.