# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform built as a **two-process local system** with strict separation of duties:

- **Swift macOS Shell**
  - Owns UI, installation, updates, authentication, biometric gating, Keychain access, operator interactions, project/workspace state, and local process orchestration.
  - Hosts the native app experience and all user-trust boundaries.
- **Python Backend**
  - Owns planning, consensus generation, document ingestion/retrieval, review/fix loops, GitHub API operations, CI orchestration, PR lifecycle handling, and repository automation.
  - Performs intelligence and repository mutation planning, but does **not** execute generated code.

Inter-process communication is over an **authenticated Unix domain socket** using **line-delimited JSON**. The Swift shell launches and supervises the Python backend, provisions a per-session authenticated channel, and supplies secrets only through controlled delivery paths.

The platform’s behavior is governed by the loaded TRDs/PRDs, with subsystem ownership distributed across the 12 TRDs referenced in repository guidance. From the provided source material, the principal implemented/spec’d platform subsystems are:

1. macOS Application Shell
2. SwiftUI Interface Layer
3. Auth, Identity, and Secret Storage
4. XPC / Socket Bridge and Process Supervision
5. Consensus Engine
6. Provider Adapter Layer
7. Planning / PRD-to-PR decomposition pipeline
8. Review and remediation pipeline
9. GitHub integration and PR operations
10. Document Store and Retrieval Engine
11. CI orchestration and workflow integration
12. Ledger / operator command plane
13. Security controls spanning all subsystems

Forge architecture follows the stated platform rules:

- Trust is asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement stay separable but linked.
- Control decisions are explainable and observable.
- Components default to enforcement, not suggestion.
- User friction is minimized without weakening guarantees.
- Admin workflows are explicit and understandable.
- Protocols are designed for future scaling across endpoint/network/cloud/AI runtime contexts.

---

## Subsystem Map

### 1. macOS Application Shell
**Primary source:** TRD-1

**What it does**
- Packages and distributes the app as a native `.app`.
- Supports drag-to-Applications install flow.
- Owns Sparkle-based auto-update integration.
- Creates and owns the top-level application lifecycle.
- Launches, monitors, and stops the Python backend.
- Manages session lifecycle and app-local state.
- Owns project/workspace selection and local filesystem anchoring.
- Publishes progress/state updates to UI.

**What it enforces**
- Native trust boundary: secrets never originate in Python.
- Process isolation between UI/auth concerns and AI/backend concerns.
- Session gating before backend operations requiring operator authority.
- Correct startup and teardown ordering.
- Stable module boundaries and concurrency ownership within Swift.

---

### 2. SwiftUI Interface Layer
**Primary source:** TRD-8, referenced by TRD-1

**What it does**
- Renders project views, cards, panels, review surfaces, and operator controls.
- Displays planning state, generation progress, PR status, CI outcomes, and review findings.
- Hosts operator affordances such as:
  - selecting lenses
  - adjusting scope
  - excluding files/directories
  - approving/pausing work
  - triggering review ingestion
  - entering REPL-style commands such as `/ledger note` and `/review`

**What it enforces**
- Human-in-the-loop gating at explicit approval points.
- Clear presentation of exclusions and scope reductions before remediation/generation.
- No hidden autonomous escalation beyond specified approval transitions.

---

### 3. Auth, Identity, and Secret Storage
**Primary source:** TRD-1, security constraints from TRD-11 per repo instructions

**What it does**
- Performs biometric authentication.
- Stores and retrieves secrets from Keychain.
- Maintains session identity and local operator profile values.
- Manages app identity records, including:
  - `display_name` in `UserDefaults`
  - `engineer_id` in Keychain (`SecretKey.engineerId`)
  - `github_username` fetched from GitHub `/user` endpoint on first auth
- Stores GitHub App/private key material and other tokens needed by backend operations.

**What it enforces**
- Swift-only access to credentials at rest.
- Session authentication before privileged actions.
- Controlled, ephemeral credential delivery to backend.
- Protection against deadlock/crash in credential handoff path.
- Strong separation between user profile metadata and secret material.

---

### 4. XPC / Socket Bridge and Process Supervision
**Primary source:** TRD-1; explicit file references include `ForgeAgent/XPCBridge.swift` and `src/xpc_server.py`

**What it does**
- Starts Python backend process with session-specific socket path and nonce.
- Establishes authenticated Unix socket connection.
- Exchanges line-delimited JSON messages.
- Forwards status, progress, requests, and errors across process boundary.
- Supports integration testing with test socket paths/nonces.

**What it enforces**
- Mutual channel authentication using launch-time shared secret/nonce.
- Rejection of unauthenticated or malformed messages.
- Structured message contracts between Swift and Python.
- Safe error propagation when one side crashes or disconnects.
- Process supervision and failure visibility for:
  - shell crash before credential send
  - connection establishment failure
  - backend startup issues

---

### 5. Consensus Engine
**Primary source:** TRD-2

**What it does**
- Runs two-model generation using parallel providers.
- Uses Claude and GPT-4o in a consensus/arbitration pattern.
- Produces implementation proposals, tests, and revisions for each PR unit.
- Invokes context loading, including document retrieval (`auto_context()` from TRD-10).
- Arbitrates outputs and determines final candidate result.

**What it enforces**
- Consensus is a first-class control, not a best-effort enhancement.
- Claude arbitrates every result.
- Provider disagreement is surfaced and resolved through deterministic pipeline logic.
- Failed provider calls follow explicit retry/error policy.

---

### 6. Provider Adapter Layer
**Primary source:** TRD-2

**What it does**
- Encapsulates model-provider-specific APIs, prompt formatting, request/response normalization, and error handling.
- Supports multiple LLM providers in parallel.
- Maps provider-specific failure modes into shared engine error contracts.

**What it enforces**
- Provider isolation behind stable interfaces.
- No provider-specific logic leaking upward into planning/review orchestration.
- Explicit handling of provider failure cases; for certain classes of failure:
  - **Do not retry with the other provider** unless the owning TRD explicitly permits it.

---

### 7. Planning Pipeline
**Primary source:** README product flow; likely covered by planning TRDs not fully included

**What it does**
- Converts operator intent plus loaded TRDs into an ordered PRD plan.
- Decomposes PRDs into a sequence of logically isolated pull requests.
- Establishes branch/commit intent and work unit ordering.
- Applies repository-aware decomposition.

**What it enforces**
- Work is broken into reviewable PR-sized units.
- Planning stays grounded in repository specs rather than freeform generation.
- Generated work tracks explicit intent and decomposition lineage.

---

### 8. Review and Remediation Pipeline
**Primary source:** README, TRD-6 references in TRD-10, operator commands from loaded docs

**What it does**
- Executes a three-pass review cycle on generated changes.
- Ingests open PRs via `/review` command and `PRReviewIngester.scan_open_prs()`.
- Supports remediation scope control:
  - directory exclusions
  - file exclusions
  - lens selection
- Runs issue-specific fix passes while respecting operator exclusions.

**What it enforces**
- Review is mandatory before draft PR publication.
- Remediation scope is explicit and operator-visible.
- Security or domain-specific “lenses” can be selected or excluded.
- Exclusion rules such as:
  - `exclude src/legacy/`
  - `exclude src/old_api.py`
  - `exclude security in src/vendor/`
  are applied before fix generation.

---

### 9. GitHub Integration and PR Operations
**Primary source:** README flow; source snippets mention GitHub `/user`, App auth JWT, REST/GraphQL fallback, commit/branch naming

**What it does**
- Authenticates to GitHub using GitHub App credentials.
- Generates JWT using App private key from Keychain.
- Interacts with GitHub APIs for:
  - repository reads
  - branch operations
  - file content fetches
  - pull request creation/update
  - user identity retrieval
  - review ingestion
- Uses deterministic commit and PR naming schemes, e.g.:
  - `forge-agent[{engineer_id}]: {message}`
  - `forge-agent[todd-gould]: PR007 implement idempotency key expiry`
  - `forge-agent[todd-gould]: PRD-003 — Transaction Idempotency Layer`
  - `forge-ledger[sara-chen]: claim PR #8`
- Reads file content + SHA before mutation.
- Computes content hashes and reconciles GitHub SHA-based updates.
- Falls back from GraphQL to REST when GraphQL returns HTTP 200 with `"errors"`.

**What it enforces**
- Repository mutation is API-mediated and state-aware.
- Writes use current GitHub file SHA to prevent blind overwrites.
- Naming conventions preserve operator/engineer attribution.
- Transport fallback preserves operation continuity without silent corruption.
- No local generated code execution as part of mutation flow.

---

### 10. Document Store and Retrieval Engine
**Primary source:** TRD-10

**What it does**
- Ingests project documents, TRDs, PRDs, repository files, and supporting context.
- Builds an embedding-backed retrieval index under:
  - `~/Library/Application Support/ForgeAgent/cache/{project_id}/`
- Creates an empty index when a project is created.
- Supplies contextual retrieval to generation and review stages.
- Supports `doc_filter` integration in pipeline stages.
- Keeps FAISS index loaded in memory; explicit unload is not required.

**What it enforces**
- Per-project document isolation in cache layout.
- Context injection is controlled and query-driven, not arbitrary.
- Retrieval is upstream of generation/review, not an afterthought.
- Embedding model changes trigger full re-embedding requirements.

---

### 11. CI Orchestration and Workflow Integration
**Primary source:** README and loaded workflow names

**What it does**
- Runs CI for generated PRs.
- Integrates with repository workflows including:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
- Distinguishes targeted changes from accidental broad rebuilds.
- Supports optional live smoke test prompts.

**What it enforces**
- PRs are not just generated; they are validated through CI.
- Platform-specific and backend-specific tests are both part of release quality.
- Detection of accidental rebuild/regression breadth is part of validation.

---

### 12. Ledger / Operator Command Plane
**Primary source:** loaded operator commands and examples

**What it does**
- Tracks operator-visible actions and annotations.
- Supports notes and claims through command/repl flows.
- Accepts commands like:
  - `/ledger note <text>`
  - `/review ...`
- Maintains operational history associated with work items/PRs.

**What it enforces**
- Human actions are attributable and recorded.
- Review/remediation actions are invocable explicitly, not hidden behind opaque automation.
- Auditability of operator interventions.

---

### 13. Security Control Plane
**Primary source:** TRD-11 referenced as governing all components; additional explicit constraints in repo docs

**What it does**
- Defines repository-wide security posture.
- Governs credential handling, external content handling, generated code policies, CI exposure, and trust boundaries.
- Applies to Swift shell, Python backend, GitHub integration, and document ingestion.

**What it enforces**
- Neither process executes generated code.
- Secrets stay in Swift/Keychain boundary except controlled delivery.
- External content is treated as untrusted input.
- CI and generated artifacts are bounded by policy.
- Security-relevant changes must obey explicit contracts, not inferred behavior.

---

## Enforcement Order

This is the normative high-level control sequence for a typical Forge work cycle.

1. **Application launch**
   - Swift shell starts.
   - Native state stores initialize.
   - Update, installation, and environment prerequisites are checked.

2. **Identity and session establishment**
   - Operator authenticates via biometrics or approved session flow.
   - Swift resolves local profile data.
   - Required secrets remain in Keychain until needed.

3. **Project selection / creation**
   - Operator selects repository/project.
   - Shell establishes project state.
   - Document Store creates empty index if project is new.

4. **Backend startup**
   - Swift starts Python backend process with:
     - test or production socket path
     - per-session nonce/auth material
   - Backend binds/authenticates socket listener.
   - Swift and Python complete authenticated handshake.

5. **Credential delivery**
   - Swift delivers only required credentials after channel authentication.
   - Backend confirms receipt/readiness.
   - Error is surfaced if:
     - Swift crashes before send
     - connection fails
     - credential path deadlocks

6. **Intent capture and planning**
   - Operator provides intent.
   - Planning pipeline translates intent + loaded TRDs into ordered PRDs/PR units.
   - Scope/exclusions are captured if present.

7. **Context ingestion / retrieval**
   - Document Store ingests or refreshes project context.
   - Retrieval executes `auto_context()` per generation.
   - Stage-specific `doc_filter` constraints are applied.

8. **Consensus generation**
   - Consensus Engine invokes provider adapters in parallel.
   - Claude arbitrates final result.
   - Provider failures are mapped to pipeline control outcomes.

9. **Review cycle**
   - Generated changes go through multi-pass review.
   - Review lenses, exclusions, and fix scopes are applied.
   - Additional retrieval context may be injected.

10. **Repository mutation preparation**
    - Backend fetches current file content and SHA from GitHub.
    - Computes content hashes.
    - Determines branch/commit/PR metadata.

11. **CI validation**
    - Generated PR branch runs CI workflows.
    - Test and integration outcomes are collected.
    - Broad unintended changes are detected.

12. **Draft PR publication**
    - Backend opens or updates draft PR.
    - Operator reviews.
    - Ledger events and status are recorded.

13. **Approval and continuation**
    - On operator approval/merge, next PR unit begins.
    - Documentation regeneration may run if configured.

This order reflects Forge’s core principle: **authenticate first, retrieve context second, generate third, validate fourth, publish last**.

---

## Component Boundaries

### Swift Shell must never
- Execute generated code.
- Delegate secret-at-rest ownership to Python.
- Allow unauthenticated backend access to privileged operations.
- Collapse UI/auth/session logic into backend orchestration code.
- Trust backend claims about user identity without shell-owned verification.

### Python Backend must never
- Access Keychain directly.
- Bypass shell-mediated authentication/session policy.
- Execute generated code or repository code.
- Mutate repositories without GitHub state reconciliation.
- Invent authority outside TRD-defined workflows.

### XPC / Socket Bridge must never
- Accept unauthenticated peers.
- Carry unstructured ad hoc messages outside schema.
- Implicitly trust socket path locality as authentication.
- Hide transport failures from supervising components.

### Consensus Engine must never
- Operate without document/context grounding where required.
- Treat provider output as authoritative without arbitration.
- Smuggle provider-specific behavior into domain logic.
- Turn retry/failover into silent speculative behavior.

### Provider Adapters must never
- Own planning policy.
- Make repository mutation decisions.
- Store long-term credentials outside approved mechanism.
- Normalize away materially important provider failures.

### Planning Pipeline must never
- Skip PR/PRD decomposition for convenience.
- Generate work disconnected from loaded specs.
- Merge unrelated changes into a single PR unit without explicit plan rationale.

### Review Pipeline must never
- Ignore operator exclusions.
- Auto-fix excluded directories/files.
- Publish unreviewed generated output as final.
- Collapse security findings into generic lint output.

### GitHub Integration must never
- Blind-write file contents without SHA checks.
- Assume GraphQL success solely from HTTP 200.
- Lose actor attribution in branch/commit/PR metadata.
- Depend on shell environment files like `.zshrc` or `.bash_profile` in LaunchAgent contexts.

### Document Store must never
- Mix documents across project IDs.
- Inject arbitrary context without retrieval/query constraints.
- Assume embedding model compatibility after model changes.
- Depend on unload semantics for correctness.

### CI Integration must never
- Treat generation as complete before validation.
- Ignore platform-specific workflows.
- Hide failed smoke/unit/integration test outcomes.

### Ledger / Operator Command Plane must never
- Mutate protected state without explicit command semantics.
- Record ambiguous actorless events.
- Override review/approval gates implicitly.

---

## Key Data Flows

### 1. Session and Secret Flow
1. App launches in Swift.
2. Operator authenticates.
3. Swift resolves identity metadata.
4. Secrets remain in Keychain.
5. Swift launches backend and authenticates socket.
6. Swift transmits only required credentials/session material.
7. Backend stores only runtime-necessary values in memory.

**Security property:** secret origin and trust root remain in Swift.

---

### 2. Project Context and Retrieval Flow
1. Operator opens/creates a project.
2. Document Store creates/loads `cache/{project_id}/`.
3. Source docs/repository docs are ingested.
4. Embeddings/index are built or refreshed.
5. Generation/review calls `auto_context()`.
6. Retrieval returns filtered relevant chunks to consensus/review stages.

**Security property:** contextual grounding is explicit, scoped, and project-isolated.

---

### 3. Intent-to-PR Flow
1. Operator submits intent.
2. Planning decomposes into PRD plan.
3. PRD decomposes into ordered PR units.
4. Unit metadata is assigned.
5. Consensus Engine generates implementation/test candidates.
6. Review pipeline validates and remediates.
7. GitHub branch/commit/PR artifacts are created.
8. Draft PR is opened for operator review.

**Control property:** autonomous execution is bounded by reviewable units.

---

### 4. GitHub Mutation Flow
1. Backend requests GitHub auth material.
2. JWT is generated using App private key from Keychain-derived material.
3. Backend reads current file content from GitHub.
4. Backend obtains file SHA.
5. Backend computes content hash/new payload.
6. Backend performs update/create operation against GitHub API.
7. If GraphQL returns HTTP 200 with `"errors"`, backend logs and falls back to REST.
8. Branch/commit/PR are updated with attribution naming.

**Integrity property:** writes are state-aware and attributable.

---

### 5. Review / Fix Flow
1. `/review` command or automated review stage begins.
2. Open PRs are scanned by review ingester.
3. Operator may:
   - select lenses
   - adjust scope
   - exclude files/directories
4. Review findings are classified.
5. Remediation generation runs only on allowed scope.
6. Updated PR artifacts are pushed and revalidated.

**Safety property:** operator exclusions are binding.

---

### 6. CI Validation Flow
1. PR branch is pushed.
2. GitHub workflows run:
   - Python tests
   - macOS unit tests
   - XPC integration tests
3. Results are ingested.
4. Optional live smoke tests may be requested.
5. PR status is updated for operator review.

**Quality property:** generated changes must pass explicit validation gates.

---

### 7. Error Propagation Flow
1. Transport, auth, provider, GitHub, review, or CI errors occur.
2. Backend emits structured error over socket if channel is open.
3. Shell updates UI state and operator-visible diagnostics.
4. Supervising layer decides whether to retry, pause, or fail terminally.

**Observability property:** failures are surfaced, not hidden.

---

## Critical Invariants

1. **Generated code is never executed by Forge.**
   - Applies to Swift shell, Python backend, and validation flows.
   - CI may test repository code in controlled workflow contexts, but the agent itself does not execute generated output locally as a decision mechanism.

2. **Secrets originate and persist in Swift/Keychain trust boundary.**
   - Python receives only scoped runtime credentials.
   - Python never owns secret-at-rest storage.

3. **All privileged backend activity is session-gated.**
   - No authenticated session, no sensitive operations.

4. **Inter-process communication is authenticated, structured, and explicit.**
   - Socket locality is insufficient.
   - Messages are schema-bound JSON lines.

5. **Consensus requires arbitration.**
   - Two-provider generation is not complete until arbitration occurs.
   - Claude is the required arbiter per product definition.

6. **Planning precedes mutation.**
   - Repository changes must derive from explicit PRD/PR decomposition, not ad hoc file edits.

7. **Context injection is retrieval-based and project-scoped.**
   - Document Store isolates by `project_id`.
   - Retrieval inputs are constrained and stage-aware.

8. **Repository writes are state-aware.**
   - GitHub file SHA/content state must be read before write.
   - Blind overwrite is forbidden.

9. **Review is mandatory before publication.**
   - Multi-pass review is part of the generation pipeline, not optional post-processing.

10. **Operator exclusions are binding.**
    - Excluded files/directories/lenses are never remediated in that run.

11. **Transport and provider failures are explicit.**
    - HTTP 200 with GraphQL errors is still a failure condition.
    - Failover and retries follow contract, not intuition.

12. **CI is part of completion semantics.**
    - A generated PR is not considered complete merely because code was produced.

13. **Attribution is preserved end-to-end.**
    - Engineer/operator identity is reflected in commit, branch, PR, and ledger records.

14. **Launch context must not assume interactive shell configuration.**
    - LaunchAgent execution does not source `.zshrc`/`.bash_profile`.
    - All runtime environment dependencies must be explicit.

15. **Embedding model changes invalidate prior embedding compatibility.**
    - Re-embedding is required on model change.

16. **Security policy is globally applicable.**
    - Any subsystem touching credentials, external content, generated code, or CI must conform to TRD-11 controls.

17. **Trust must be explicit and explainable.**
    - No subsystem may infer authority or safety from convenience heuristics where direct verification is possible.

18. **Enforcement defaults to deny/restrict.**
    - Components should block or surface for approval when policy certainty is absent.

---

## Summary

Forge is architected as a **local, native, two-process autonomous coding platform** with strict trust partitioning:

- **Swift owns trust, identity, secrets, UI, and orchestration.**
- **Python owns planning, consensus, retrieval, review, GitHub operations, and CI coordination.**
- **The socket bridge is authenticated and explicit.**
- **Document retrieval grounds generation.**
- **Consensus and review constrain model output.**
- **GitHub state reconciliation and CI constrain repository mutation.**
- **Operator approval remains the final control point.**

The result is a system optimized for autonomous software delivery while preserving explicit trust boundaries, auditability, and non-execution safety.