# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform implemented as a **two-process system**:

- a **Swift macOS shell** responsible for UI, local identity, authentication, secure secret custody, lifecycle control, and operator interaction
- a **Python backend** responsible for planning, consensus generation, document retrieval, review, repair loops, GitHub operations, and CI-driven progression

The platform is intentionally **non-executing with respect to generated code**: neither the Swift shell nor the Python backend may execute generated application code. Forge produces changes, validates them through controlled tooling and CI, and submits them as reviewable GitHub pull requests.

The architecture is specification-driven. Product behavior is defined by the loaded TRDs/PRDs, with subsystem ownership split across 16 technical requirements documents. The shell and backend communicate over an **authenticated Unix domain socket** using **line-delimited JSON**. Security-critical controls are centralized in the platform security model and are enforced across authentication, transport, storage, retrieval, generation, review, and GitHub publication.

At a high level, Forge operates as a directed build pipeline:

1. Operator selects a repository and loads technical documents.
2. Shell authenticates the engineer and releases required secrets from Keychain.
3. Shell launches backend with an authenticated socket path and nonce.
4. Backend ingests project documents into a local retrieval index.
5. Backend assesses operator intent and estimates confidence/scope.
6. Backend decomposes work into PRD plan and typed pull-request units.
7. For each unit, backend retrieves relevant context, runs multi-provider generation in parallel, arbitrates with Claude, performs self-correction and lint/test repair loops, and opens a draft PR.
8. Operator reviews and approves/merges; backend advances to the next logical PR.

The platform is designed around the following architectural rules:

- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Forge components must default to policy enforcement, not policy suggestion.
- Local agents must minimize user friction while preserving strong enforcement guarantees.
- Administrative workflows must be simple, explicit, and understandable in plain language.
- Protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments.

---

## Subsystem Map

Below is the complete subsystem map implied by the loaded product docs and TRD references.

### 1. macOS Application Shell
**Primary implementation:** Swift 5.9+, SwiftUI  
**Owns:** local app runtime, top-level state, app distribution, update flow, process orchestration

**Responsibilities**
- Package and distribute the `.app` bundle
- Support drag-to-Applications installation
- Manage auto-update via Sparkle
- Own app lifecycle and root SwiftUI scene hierarchy
- Launch and supervise the Python backend process
- Manage socket path/nonce bootstrapping
- Present system state, progress, errors, and review surfaces

**Enforces**
- Only the shell may access platform-local authentication APIs directly
- Only the shell may read/write Keychain secrets
- Backend startup must be explicit and authenticated
- UI state and secure secret state remain separate
- Shell never performs generation, planning, or GitHub mutation logic

---

### 2. Authentication and Identity
**Primary implementation:** Swift shell + macOS biometric APIs + Keychain  
**Owns:** engineer authentication, session gating, local identity material

**Responsibilities**
- Biometric gate before privileged operations
- Session lifecycle management
- Identity persistence for:
  - `display_name` in `UserDefaults`
  - `engineer_id` in Keychain
  - `github_username` fetched from GitHub `/user` on first auth
- Secret release to backend only after successful auth

**Enforces**
- Credentials are not available to backend prior to successful shell-controlled auth
- Session unlock is time-bounded and auditable
- Long biometric delays are treated as unusual and observable
- Authentication failures do not downgrade to weaker implicit trust

---

### 3. Secret Storage and Credential Custody
**Primary implementation:** Swift shell, Keychain  
**Owns:** all persistent secret material

**Responsibilities**
- Store GitHub App private key and other platform secrets in Keychain
- Store `engineer_id` in Keychain
- Release secrets only to in-process shell code or to backend through authenticated startup/session transfer
- Ensure secrets are never persisted in backend-owned storage

**Enforces**
- Python backend does not own durable secret custody
- Secrets are never sourced from shell environment profiles
- Launch paths cannot depend on `.zshrc` or `.bash_profile`
- Credential delivery path must not deadlock or silently fail

---

### 4. XPC / Authenticated Local Transport Bridge
**Primary implementation:** Swift `Crafted/XPCBridge.swift`, Python `src/xpc_server.py`  
**Owns:** shell↔backend command and event transport

**Responsibilities**
- Establish authenticated local IPC over Unix socket
- Use line-delimited JSON protocol
- Carry progress events, errors, state transitions, prompts, and operator actions
- Carry startup nonce and session-authenticated capability context

**Enforces**
- Backend must prove possession of launch-time nonce/session context
- Socket endpoint is local-only and per-session
- Message framing is deterministic and parseable
- If shell crashes before sending credentials, backend must fail closed
- Connection establishment failures are surfaced explicitly

---

### 5. SwiftUI Presentation Layer
**Primary implementation:** SwiftUI  
**Owns:** all operator-visible interaction surfaces

**Responsibilities**
- Root views, panels, cards, progress displays, review controls
- Display plan, PR sequence, generation progress, review findings, CI status
- Surface commands such as review exclusions and lens selection
- Show actionable errors and recovery steps

**Enforces**
- UI does not mutate repository or secrets directly
- UI dispatches intent to shell/application state; execution remains in backend or shell service layers
- Security-sensitive state is not rendered from unverified backend claims without shell validation

---

### 6. Python Backend Runtime
**Primary implementation:** Python 3.12  
**Owns:** orchestration of all autonomous build intelligence

**Responsibilities**
- Receive authenticated startup context from shell
- Manage planning, decomposition, generation, repair, review, retrieval, and publication workflows
- Own backend state machine for active project/session/job execution
- Emit progress and typed errors to shell

**Enforces**
- Backend never directly invokes local OS credential stores
- Backend never executes generated application code
- Backend treats shell as authority for identity and local auth
- Backend persists only allowed cache/state in app support paths

---

### 7. Intent Analysis and Scope Confidence
**Owns:** interpretation of operator intent before commitment

**Responsibilities**
- Parse operator’s natural-language request
- Assess confidence in requested scope
- Detect ambiguity, underspecification, and excessive breadth
- Request scope adjustment or exclusions where needed

**Enforces**
- Low-confidence scopes do not proceed directly into implementation
- Scope must be bounded before PRD planning
- Operator exclusions such as file or directory exclusions are explicit inputs, not heuristics

---

### 8. PRD Planning Engine
**Owns:** decomposition of user intent into ordered implementation plan

**Responsibilities**
- Convert accepted intent into structured PRD plan
- Order work according to dependency and risk
- Produce logical pull-request units rather than one monolithic change
- Preserve spec alignment with loaded TRDs/PRDs

**Enforces**
- Plans must be explainable and ordered
- Plan units must map to reviewable scopes
- No implementation begins without a bounded plan
- Plan cannot silently exceed approved scope

---

### 9. Pull Request Decomposition and Typed Change Units
**Owns:** conversion of plan into concrete branch/PR work packets

**Responsibilities**
- Break plan into typed PRs
- Define each PR’s target files, expected tests, and acceptance shape
- Sequence PRs so later units build on approved prior work

**Enforces**
- One draft PR per logical unit
- PR boundaries should minimize cross-cutting, unreviewable changes
- Full rebuilds caused by accidental broad changes are treated as regressions

---

### 10. Consensus Generation Engine
**Primary implementation:** Python backend  
**Depends on:** provider adapters, retrieval, review/self-correction

**Responsibilities**
- Run two LLM providers in parallel for implementation generation
- Use Claude as required arbitrator over parallel outputs
- Merge/adapt the selected or synthesized result
- Drive iterative improvement passes

**Enforces**
- Two-model consensus is the generation baseline
- Claude arbitrates every result
- Provider failures are handled explicitly
- On certain provider-specific errors: do **not** automatically retry with the other provider
- Generated output remains text/code artifacts only; no execution

---

### 11. Provider Adapter Layer
**Owns:** isolation of model-provider-specific APIs and data contracts

**Responsibilities**
- Normalize requests/responses across providers
- Handle auth, request formatting, token budgets, timeouts, and structured outputs
- Return provider-specific diagnostics for arbitration and observability

**Enforces**
- Consensus engine never speaks raw provider APIs directly
- Provider identity, error classes, and retry semantics remain explicit
- Session/token limits such as OI-13 constraints are checked before generation

---

### 12. Document Store and Retrieval Engine
**Primary implementation:** Python  
**Storage root:** `~/Library/Application Support/Crafted/cache/{project_id}/`

**Responsibilities**
- Ingest TRDs, PRDs, repository context, and supporting docs
- Chunk, embed, index, and cache retrieval corpus
- Serve `auto_context()` per generation
- Support context filtering for generation and review
- Maintain project-local retrieval state

**Enforces**
- Retrieval context is local to a project
- Changing embedding model requires re-embedding all indexed content
- Project creation creates an empty index in `cache/{project_id}/`
- Small FAISS index remains memory-resident; explicit unload is not required
- Context injection is filtered for prompt injection and unsafe content markers
- Retrieval is an input to generation/review, never an authority over security policy

---

### 13. Context Filtering and Injection Defense
**Owns:** filtering of retrieved and external text before model use

**Responsibilities**
- Detect prompt injection patterns in documentation or repository text
- Remove or annotate suspicious chunks
- Limit context scope to relevant and allowed documents
- Support review-time exclusions and lens-based scoping

**Enforces**
- External content is untrusted by default
- Retrieval chunks may be flagged, quarantined, or omitted
- Security review can exclude directories/files such as:
  - `src/vendor/`
  - `src/legacy/`
  - specific files like `src/old_api.py`
- Selection of lenses is explicit and operator-controlled

---

### 14. Self-Correction Pass
**Owns:** first corrective refinement after generation

**Responsibilities**
- Re-read generated change against task, context, and specs
- Correct obvious structural/spec mismatches
- Improve test coverage and conformance before lint/test stage

**Enforces**
- Raw first-pass generation is not directly committed
- Corrective pass occurs before publication pipeline advances
- Spec mismatches are repaired early rather than deferred to PR review

---

### 15. Lint Gate
**Owns:** static quality gate before iterative fix loop

**Responsibilities**
- Run project-appropriate linting/format/static checks
- Detect syntax and obvious style issues
- Block advancement if gating failures remain

**Enforces**
- Lint failures prevent PR publication
- Gate is deterministic and repeatable
- Tooling scope is constrained to repository-approved commands

---

### 16. Iterative Fix Loop
**Owns:** repair of failing validation signals

**Responsibilities**
- Parse lint/test/CI failures
- Feed failures back into repair prompts
- Prioritize targeted fixes using identifiers, failed test names, and diagnostics
- Re-run validations until pass or stop condition

**Enforces**
- Repair is evidence-driven, not freeform regeneration
- Failure parsing weights concrete evidence, e.g. assertion identifiers and failed test names
- Operator can exclude files/issues before fixing
- Loop terminates on bounded attempts or blocking conditions

---

### 17. Review Engine
**Owns:** structured code/document/security review before publication or approval

**Responsibilities**
- Run review passes with selectable lenses
- Accept operator commands such as `/review start`, `/review exclude`, `/ledger note`
- Produce structured outputs including `technical_note` and `gaps`
- Focus review on changed files and retrieved product context

**Enforces**
- Review scope can be explicitly narrowed or expanded
- Exclusions are operator-visible and auditable
- Review is advisory to operator but blocking where policy requires
- Findings remain attached to the relevant PR/unit of work

---

### 18. Security Review Lenses
**Owns:** specialized focused analysis dimensions

**Responsibilities**
- Evaluate code against security, architecture, correctness, and other lenses
- Permit explicit lens selection by comma-separated lens IDs
- Support exclusion examples and targeted directory/file suppression

**Enforces**
- Review findings are lens-scoped and explainable
- Security analysis does not silently ignore excluded paths
- Exclusions are explicit operator inputs, not hidden defaults

---

### 19. GitHub Integration
**Owns:** repository read/write operations and PR publication

**Responsibilities**
- Authenticate as GitHub App
- Generate JWT using app private key from Keychain-backed flow
- Fetch current file contents and SHA before updates
- Create branches, commits, draft PRs, comments, and status updates
- Fetch `/user` on first auth for username mapping

**Enforces**
- File mutation uses current GitHub content + SHA to avoid blind overwrites
- Branch/PR publication occurs only after pipeline gates pass
- Draft PRs are created per logical unit
- Main branch pushes and PR events are observable and CI-driven

---

### 20. Conflict Detection
**Owns:** detection of repository drift and write conflicts

**Responsibilities**
- Compute content hashes
- Fetch current file content from GitHub
- Compare SHAs and detect concurrent modifications
- Prevent stale writes and accidental overwrite of remote changes

**Enforces**
- Remote state is revalidated prior to write
- Content hash mismatch blocks unsafe mutation
- Conflicts are surfaced explicitly for operator/backend resolution

---

### 21. CI Orchestration
**Owns:** post-commit validation in GitHub Actions and related build/test workflows

**Responsibilities**
- Trigger and observe CI for Python and macOS paths
- Distinguish workflow classes:
  - Forge CI — Python / test
  - Forge CI — macOS / unit-test
  - Forge CI — macOS / xpc-integration-test
- Route failures back into iterative fix loop or operator review

**Enforces**
- CI is authoritative for merge-readiness
- Workflow triggering may be path-sensitive
- Swift/macOS jobs should run only when Swift-relevant files change
- CI coverage must catch accidental full rebuild triggers

---

### 22. macOS Test and Integration Validation
**Owns:** shell/XPC-specific correctness validation

**Responsibilities**
- Validate Swift unit behavior
- Validate XPC/integration path with test socket path and nonce
- Ensure shell-backend launch/credential path works under CI and local tests

**Enforces**
- Socket authentication is testable
- Credential handoff failures are detectable
- XPC bridge contract is stable and versionable

---

### 23. Auto-Update and Release Distribution
**Owns:** packaged application lifecycle after installation

**Responsibilities**
- Ship signed `.app`
- Update via Sparkle
- Support Developer ID notarized distribution
- Validate app identity and release provenance

**Enforces**
- Release artifacts must be signed as Developer ID Application
- Update channel must preserve code-signing trust
- Certificate expiry/revocation procedures are operationally defined

---

### 24. Packaging, Signing, and Certificate Operations
**Owns:** release signing material and operational renewal

**Responsibilities**
- Build release app artifacts
- Sign with Apple Developer ID Application identity
- Handle certificate rotation/expiry checks
- Support revocation and replacement procedures

**Enforces**
- Signing identity must match approved team identity
- Expiring or revoked certs must not be ignored
- Operational checks may run on scheduled basis

---

### 25. Telemetry, Progress, and Error Reporting
**Owns:** explainability and observability across shell and backend

**Responsibilities**
- Emit structured progress events over XPC
- Surface typed errors and recovery instructions
- Report unusual conditions such as long biometric auth or connection failure
- Maintain traceability from operator action to backend stage

**Enforces**
- Control decisions are observable and reproducible
- Errors are never silently swallowed
- Telemetry must not leak secrets
- Progress semantics are stable enough for UI rendering and test assertions

---

### 26. Local Project Cache and State Storage
**Owns:** non-secret per-project local persistence

**Responsibilities**
- Store retrieval indices and cache artifacts under app support
- Persist lightweight metadata for active/known projects
- Maintain negligible disk footprint expectations

**Enforces**
- Secret material is excluded from cache
- Project-local state remains isolated by `project_id`
- Cache invalidation occurs when embedding/version changes require it

---

### 27. Operator Command Surface
**Owns:** non-chat command verbs for review and annotation

**Responsibilities**
- Support commands like:
  - `/ledger note <text>`
  - `/review start`
  - `/review exclude ...`
- Accept exclusion parameters, file scope narrowing, and lens selection
- Route commands into review/ledger subsystems

**Enforces**
- Commands map to typed backend actions
- Freeform operator text is not treated as privileged command unless parsed as such
- Command effects are explicit and logged

---

### 28. Session Limit and Budget Controls
**Owns:** usage and token guardrails

**Responsibilities**
- Track provider/session token totals
- Block generation when platform-defined thresholds are exceeded
- Surface budget exhaustion before starting expensive work

**Enforces**
- Generation halts when session limits are exceeded
- Budget decisions are explicit, not hidden provider-side failures
- Limits are checked before provider invocation

---

## Enforcement Order

The Forge platform is designed as a strict ordered control chain. The order below reflects the effective runtime sequence and the enforcement dependencies between subsystems.

### 1. App launch and shell initialization
1. macOS Application Shell starts.
2. Shell initializes root SwiftUI state and local services.
3. Packaging/update trust is assumed only after code-signing/notarization validation at install/update time.

### 2. Operator authentication and session unlock
1. Operator initiates privileged session.
2. Authentication subsystem performs biometric gate.
3. Shell loads identity metadata and authorizes session.
4. Secret storage subsystem unlocks only the minimum required credentials.

### 3. Backend launch and authenticated transport establishment
1. Shell creates test or runtime socket path.
2. Shell generates startup nonce.
3. Shell launches Python backend with socket path and nonce.
4. Backend connects to local transport bridge.
5. Shell validates authenticated handshake.
6. Only after successful handshake does shell release session-scoped credentials/capabilities.

### 4. Project load and document ingestion
1. Operator selects repository/TRDs.
2. Backend creates or opens project cache under `cache/{project_id}/`.
3. Document Store ingests docs/code context.
4. Embedding/index build or reuse occurs.
5. Context filtering scans for injection or unsafe chunks.

### 5. Intent qualification
1. Operator submits plain-language intent.
2. Intent analysis computes scope confidence.
3. If ambiguous/broad, backend requests adjustment/exclusions.
4. Only bounded scope proceeds to planning.

### 6. Planning and PR decomposition
1. PRD Planning Engine constructs ordered plan.
2. PR decomposition creates typed logical PR units.
3. Shell/UI displays proposed execution structure.

### 7. Per-PR implementation cycle
For each PR unit:

1. Retrieval engine computes `auto_context()`.
2. Context filtering applies scope and injection defenses.
3. Consensus engine invokes provider adapters in parallel.
4. Claude arbitrates outputs.
5. Self-correction pass refines result.
6. Lint gate runs.
7. Iterative fix loop repairs failures as needed.
8. Review engine runs lenses and produces findings.
9. GitHub integration fetches remote state and SHAs.
10. Conflict detection validates no stale write.
11. Branch/commit/draft PR is created.

### 8. CI validation and post-publication progression
1. GitHub Actions workflows run.
2. CI orchestration collects status.
3. Failing jobs route back to fix loop or operator attention.
4. Passing PR remains for operator review/approval.
5. On approval/merge, next queued PR unit begins.

### 9. Update and release maintenance
1. Auto-update subsystem checks for signed updates.
2. Signing/certificate operations maintain release trust chain.
3. Expiry/revocation checks preserve distribution integrity.

---

## Component Boundaries

This section defines what each subsystem must **never** do.

### macOS Application Shell must never
- Execute generation/planning logic that belongs in Python backend
- Execute generated application code
- Persist secrets outside approved Keychain storage
- Trust backend-reported identity without shell-managed auth state

### Authentication subsystem must never
- Expose long-lived credentials before successful local auth
- Fall back from biometric/session policy to silent weaker modes
- Store secret identity tokens in `UserDefaults`

### Secret storage subsystem must never
- Hand raw durable secret ownership to Python
- Log secret values
- Depend on login shell configuration files for credential availability

### XPC / transport bridge must never
- Accept unauthenticated backend connections
- Treat malformed line-delimited JSON as valid partial commands
- Continue after nonce/session mismatch

### SwiftUI presentation layer must never
- Own business logic for generation, GitHub writes, or retrieval indexing
- Bypass shell state/control services
- Render unsafe rich content as trusted instructions

### Python backend must never
- Access Keychain directly
- Execute generated code or arbitrary repository code
- Assume provider output is trustworthy without arbitration/review
- Mutate GitHub without conflict checks

### Intent analysis must never
- Auto-expand scope beyond operator request
- Proceed on low confidence without explicit clarification path

### PRD planning/decomposition must never
- Produce unreviewable mega-PRs
- Break dependency order
- Ignore loaded specification boundaries

### Consensus engine must never
- Use a single-provider shortcut when two-provider consensus is required
- Skip Claude arbitration
- Hide provider failures or silently substitute altered outputs

### Provider adapters must never
- Leak provider-specific auth material outside their boundary
- Mask token/budget exhaustion as generic unknown failure
- Retry in ways forbidden by contract

### Document Store must never
- Store secrets in retrieval index
- Treat indexed text as executable instructions
- Reuse stale embeddings after embedding model changes

### Context filtering must never
- Allow flagged injection text to pass as trusted context without annotation/control
- Apply hidden exclusions

### Self-correction/fix loop must never
- Rewrite unrelated repository areas opportunistically
- Continue indefinitely without stop conditions
- Ignore explicit operator exclusions

### Review engine/lenses must never
- Conceal excluded scope
- Present findings without lens/source attribution
- Substitute for required hard policy gates where those exist

### GitHub integration must never
- Blind overwrite file contents
- Push directly to protected main outside defined workflow
- Create PRs before validation gates complete

### Conflict detection must never
- Assume local file state equals remote state
- Ignore SHA/content hash mismatches

### CI orchestration must never
- Mark merge-ready on missing/unknown workflow status
- Collapse distinct workflow failures into an untyped success/failure blob

### Packaging/update/signing must never
- Ship unsigned or unnotarized release artifacts
- Accept mismatched Developer ID identity
- Ignore cert expiry or revocation events

### Telemetry/progress must never
- Leak secrets, tokens, or private key material
- Replace typed errors with unstructured strings only
- Make enforcement decisions non-observable

---

## Key Data Flows

### 1. Authentication and credential release
1. Operator initiates sign-in/unlock.
2. Shell performs biometric auth.
3. Shell reads identity metadata:
   - `display_name` from `UserDefaults`
   - `engineer_id` from Keychain
4. Shell establishes session state.
5. Shell releases session-scoped credentials to backend only after handshake.

**Security property:** secret custody remains in shell/Keychain boundary until explicit authenticated release.

---

### 2. Shell-to-backend startup flow
1. Shell allocates socket path.
2. Shell generates nonce.
3. Shell starts backend process with startup parameters.
4. Backend connects to `src/xpc_server.py` server endpoint semantics.
5. Handshake validates nonce and session.
6. Progress/error streams begin.

**Failure cases explicitly called out**
- XPC connection failed to establish
- Shell crashed before sending credentials
- Deadlock in credential delivery path

---

### 3. Document ingestion and retrieval flow
1. Project is opened.
2. Cache directory is created at `~/Library/Application Support/Crafted/cache/{project_id}/`.
3. Documents are chunked and embedded.
4. FAISS or equivalent local index is built/loaded.
5. Retrieval results are filtered for relevance and injection risk.
6. `auto_context()` produces generation context per stage.

**Security property:** retrieved content is untrusted input until filtered.

---

### 4. Intent-to-plan flow
1. Operator enters plain-language build intent.
2. Backend analyzes confidence and scope.
3. Clarification or exclusions may be requested.
4. Planning engine outputs PRD-aligned ordered plan.
5. PR decomposition yields reviewable PR units.

**Control property:** no implementation before scope bounding.

---

### 5. Generation and arbitration flow
1. For a PR unit, backend gathers retrieved context.
2. Provider adapters send parallel requests to multiple models.
3. Responses return with structured metadata.
4. Claude arbitrates result selection/synthesis.
5. Self-correction revises output.
6. Lint gate and fix loop validate/repair.

**Control property:** no single raw provider output is authoritative.

---

### 6. Review flow
1. Review engine loads changed files and relevant context.
2. Operator may start review, select lenses, or exclude paths/files.
3. Review outputs structured findings.
4. Findings attach to PR or current work unit.

**Control property:** review scope and exclusions are explicit and auditable.

---

### 7. GitHub mutation flow
1. Backend fetches current file content from GitHub.
2. Backend obtains current SHA.
3. Backend computes new content hash.
4. Conflict detection compares expected/current state.
5. Branch and commit are created.
6. Draft PR is opened.

**Control property:** all writes are read-before-write and conflict-checked.

---

### 8. CI feedback loop
1. Draft PR triggers workflows.
2. CI orchestration polls or receives statuses.
3. Failures are parsed into fix-loop evidence.
4. Backend proposes or applies targeted repairs.
5. Updated commit re-triggers validation.

**Control property:** CI is part of enforcement, not a post-hoc suggestion layer.

---

### 9. Update distribution flow
1. Signed release is produced.
2. Sparkle publishes or consumes update metadata.
3. Client validates signing/provenance.
4. Updated shell preserves same trust model and backend orchestration contract.

**Control property:** release trust chain is externalized via code signing and notarization.

---

## Critical Invariants

These invariants must hold across all implementations.

### Process and trust invariants
- Forge is always a **two-process architecture**: Swift shell + Python backend.
- The shell is the authority for local auth and secret custody.
- The backend is the authority for planning/generation/review/GitHub orchestration.
- Neither process executes generated application code.

### Transport invariants
- Shell/backend communication uses authenticated local Unix socket transport.
- Protocol framing is line-delimited JSON.
- Handshake authentication must complete before privileged operations.
- Transport failures fail closed.

### Secret and identity invariants
- Keychain is the only durable store for sensitive secret material.
- `engineer_id` is stored in Keychain.
- `display_name` may be stored in `UserDefaults`.
- Backend never becomes durable owner of GitHub App private key or equivalent root secrets.

### Planning and generation invariants
- Work begins only after intent scope is bounded.
- Implementation is decomposed into ordered logical PR units.
- Two-provider generation plus Claude arbitration is mandatory for consensus output.
- Provider/session limits must be checked before generation.

### Retrieval invariants
- Project retrieval state lives under `~/Library/Application Support/Crafted/cache/{project_id}/`.
- Retrieval context is project-scoped.
- Embedding model changes require full re-embedding.
- Retrieved content is untrusted until filtered.

### Validation invariants
- Self-correction occurs before publication.
- Lint/test/fix loops are mandatory gates, not optional enhancements.
- CI status is required for merge-readiness.
- Conflict checks precede GitHub writes.

### Review invariants
- Review exclusions and lens selection are explicit and operator-visible.
- Findings are attributable to lens and scope.
- Excluded paths are never silently treated as reviewed.

### Distribution invariants
- Release artifacts must be signed and notarized.
- Auto-update must preserve release trust.
- Certificate rotation/revocation is an operationally enforced part of the platform.

### Observability invariants
- Control decisions must be explainable, observable, and reproducible.
- Typed progress and error events must be emitted across the pipeline.
- Telemetry must never expose secrets.

### Safety invariants
- External docs, repository content, and retrieved chunks are untrusted inputs.
- The system defaults to enforcement, not suggestion.
- No subsystem may silently widen scope, lower trust, or skip required gates.