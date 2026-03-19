# Architecture — Forge Platform

## System Overview

Forge is a policy-enforcing autonomous software delivery platform centered on a native macOS operator application and a Python intelligence backend. The platform ingests technical specifications, plans implementation work, generates code and tests using multiple LLM providers, reviews outputs through a consensus workflow, validates changes in CI, and opens gated GitHub pull requests for human approval.

The architecture is explicitly split into two trust domains:

1. **Swift macOS Shell**
   - Native UI and operator experience
   - Local authentication and biometric gating
   - Secret custody via Keychain
   - Process lifecycle management
   - Authenticated IPC/XPC bridge to backend
   - Settings, onboarding, install/update, and local state

2. **Python Backend**
   - Planning and orchestration
   - Consensus generation pipeline
   - Document ingestion and retrieval
   - Git and GitHub operations
   - Review and validation pipeline
   - CI integration
   - TRD/PRD decomposition and execution state

This separation is fundamental to the security model: the Swift process owns local trust, credentials, and user presence; the Python process owns intelligence and automation. Generated code is never executed by either process as part of generation or review.

The system is specification-driven. The authoritative product behavior is defined in the repository TRDs. The runtime uses those documents not only as design artifacts but also as active retrieval context for planning, generation, review, and iterative implementation.

The platform’s behavior is governed by the following architectural rules:

- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Forge components must default to policy enforcement, not policy suggestion.
- Local agents must minimize user friction while preserving strong enforcement guarantees.
- Administrative workflows must be simple, explicit, and understandable in plain language.
- Protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments.

---

## Subsystem Map

### 1. macOS Application Shell
**What it does**
- Packages the application as a native `.app`
- Supports install/distribution and Sparkle-based auto-update
- Hosts SwiftUI operator interface
- Manages onboarding, settings, and session state
- Owns authentication UX and biometric gate
- Manages backend process launch, monitoring, restart, and credential delivery
- Provides authenticated XPC/Unix-socket communication to Python backend

**What it enforces**
- Local user presence before sensitive actions
- Secret isolation in Keychain
- No plaintext secret persistence
- Strict state ownership between UI and backend
- Authenticated IPC only
- Controlled backend lifecycle

---

### 2. Swift Module Architecture and State Layer
**What it does**
- Defines module boundaries in the macOS shell
- Encapsulates view models, app state, navigation, and concurrency
- Coordinates shell-owned state transitions and UI updates

**What it enforces**
- Main-thread UI mutation discipline
- Separation between presentation, state, and integration logic
- No direct secret access from arbitrary UI components
- No bypass of authenticated shell services

---

### 3. SwiftUI View Hierarchy
**What it does**
- Presents root views, panels, cards, onboarding, settings, and operational status
- Surfaces planning progress, PR lifecycle, review artifacts, and operator decisions
- Provides explicit approval, correction, expansion, stop, and exclusion controls

**What it enforces**
- Human-in-the-loop review
- Explicit operator approvals for merges and progression gates
- Visibility into stage/state before destructive or privileged actions
- No silent action on ambiguous model output

---

### 4. Authentication and Session Subsystem
**What it does**
- Performs biometric/local authentication
- Establishes and expires operator sessions
- Re-gates privileged actions when required
- Tracks foreground/background transitions and unlock state

**What it enforces**
- Never auto-answer a gate
- Gate state must not remain open incorrectly on foreground return
- Sensitive actions require valid, unexpired local session
- Biometric anomalies are observable and actionable

---

### 5. Keychain and Secret Custody
**What it does**
- Stores provider/API/GitHub credentials in macOS Keychain
- Supplies credentials to shell-owned services and backend bootstrap paths
- Supports secure retrieval for authenticated sessions only

**What it enforces**
- No plaintext secrets on disk — ever
- Secret material remains shell-owned
- Credential delivery to backend is controlled and minimal
- Secret access requires shell mediation

---

### 6. XPC / Authenticated IPC Bridge
**What it does**
- Connects Swift shell and Python backend
- Uses authenticated local IPC with line-delimited JSON messaging
- Carries commands, state updates, progress, and controlled credential material

**What it enforces**
- Mutual message framing and schema discipline
- Authenticated local channel only
- No trust in unauthenticated local senders
- Clear interface boundary between shell and backend

---

### 7. Backend Process Manager
**What it does**
- Launches Python backend
- Monitors liveness and restarts on failure
- Injects runtime configuration and authorized credentials
- Manages startup/shutdown sequencing

**What it enforces**
- Backend cannot self-elevate into shell responsibilities
- Launch environment is explicit and reproducible
- Credential delivery path must not deadlock
- LaunchAgent assumptions are explicit; no sourcing of shell profiles such as `.zshrc` or `.bash_profile`

---

### 8. Consensus Engine
**What it does**
- Runs parallel multi-provider generation
- Uses two model providers for implementation/test generation
- Uses Claude as arbiter over generated results
- Produces consolidated outputs for downstream review and execution

**What it enforces**
- No single model is sole authority for generated implementation
- Arbitration is explicit, not implied
- Provider outputs remain attributable and reviewable
- Generated output is treated as untrusted until validated

---

### 9. Provider Adapter Layer
**What it does**
- Normalizes requests/responses across LLM providers
- Encapsulates provider-specific auth, APIs, retries, and serialization
- Supports parallel generation and arbitration workflows

**What it enforces**
- Stable internal interface independent of external vendor API shape
- Provider isolation and fault containment
- Explicit token/credential routing
- Consistent error contracts to orchestration layers

---

### 10. Planning and Decomposition Engine
**What it does**
- Converts operator intent plus loaded specs into build plans
- Decomposes work into PRDs and then into ordered PR units
- Supports boundary operations such as split, merge, move, remove, add
- Maintains plan progression across operator checkpoints

**What it enforces**
- Build work follows specification boundaries
- Operator review before committing to plan transitions
- Logical unit isolation per PR
- State checkpointing after phase transitions and operator responses

---

### 11. TRD/PRD Authoring and Refinement Workflow
**What it does**
- Assists in generating new TRDs/PRDs from operator intent
- Iteratively proposes sections and boundaries
- Supports expand/correct/approve/stop interactions
- Updates generated documents and execution state as phases complete

**What it enforces**
- Human approval before advancing drafted specifications
- Explicit boundary ownership changes
- Transcript-backed reproducibility
- Controlled handling of document-level prompt injection patterns

---

### 12. Document Store and Retrieval Engine
**What it does**
- Ingests TRDs, PRDs, architecture specs, and related documents
- Chunks documents and computes embeddings
- Stores searchable vector representations
- Retrieves relevant context for planning, generation, review, and development sessions

**What it enforces**
- Retrieval quality as a first-order system requirement
- Stable chunking/embedding versioning
- Re-embedding required when embedding model changes
- Retrieval is scoped and attributable to source documents

---

### 13. Ingestion and Chunking Pipeline
**What it does**
- Parses source documents
- Extracts structure, headings, sections, and textual content
- Builds retrieval chunks with metadata for provenance and targeting

**What it enforces**
- Structural fidelity to source specifications
- Prompt-injection pattern detection in ingested text
- Source traceability for every retrieval unit
- Controlled chunk sizing and overlap

---

### 14. Review and Validation Pipeline
**What it does**
- Performs structured multi-pass review over generated diffs
- Evaluates implementation, test coverage, and specification conformance
- Produces approval/correction/exclusion loops
- Prevents progression of low-confidence or policy-violating outputs

**What it enforces**
- Three-pass review cycle
- Generated work must be reviewed before PR creation
- Exclusion controls are explicit and operator-driven
- No silent acceptance of unresolved issues

---

### 15. Git Workspace Orchestrator
**What it does**
- Applies generated changes in repository worktrees
- Creates branches and commit messages
- Maintains clean workspace boundaries between PR units
- Prepares artifacts for CI and PR submission

**What it enforces**
- One PR per logical unit
- Reproducible branch naming and commit conventions
- No uncontrolled workspace mutation
- Clear separation between plan state and repository state

---

### 16. GitHub Integration
**What it does**
- Creates draft pull requests
- Updates PR metadata, descriptions, and labels
- Integrates with GitHub workflows and status checks
- Supports approval-gated progression to subsequent PR units

**What it enforces**
- Operator must approve all merges — never auto-merge
- Draft PR creation only after validation gates pass
- PR traceability to PRD/PR unit and engineer identity where applicable
- Stable naming/message conventions such as `forge-agent[{engineer_id}]: {message}`

---

### 17. CI Orchestration
**What it does**
- Triggers and monitors test/validation workflows
- Integrates with repository-defined workflows such as:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
- Uses CI results as acceptance signals for PR readiness

**What it enforces**
- No progression past failed required checks
- CI status is visible and attributable
- Changes should avoid accidental full rebuild triggers when unnecessary
- Build/test execution remains externalized to CI or controlled local test harnesses, not arbitrary generated execution

---

### 18. Bootstrap / Repository Scaffolding
**What it does**
- Initializes Forge automation into target repositories
- Adds baseline CI workflow and required repository structures
- Establishes naming and identity conventions for initial PRs

**What it enforces**
- Deterministic bootstrap behavior
- Minimal initial permissions footprint
- Clear bootstrap commit identity, e.g. `forge-agent: add CI workflow`

---

### 19. Operator Interaction Protocol
**What it does**
- Defines finite response vocabulary and freeform correction channels
- Supports commands such as approve, correct, expand, select lenses, exclude files, split, merge, remove, stop
- Drives progression through planning and refinement phases

**What it enforces**
- Explicit human decisions at control points
- Machine actions remain bounded by operator intent
- Transcript capture after every operator response
- Stop/abort semantics are immediate and well-defined

---

### 20. Policy / Security Control Plane
**What it does**
- Applies repository-wide security and trust rules
- Governs credential handling, generated content, CI safety, IPC trust, and review requirements
- Serves as the cross-cutting control framework referenced by all subsystems

**What it enforces**
- No execution of generated code by agent components
- Explicit trust assertion and verification
- Strong separation of identity, policy, telemetry, and enforcement
- Secure defaults across local and remote operations

---

### 21. Telemetry, Logging, and Audit Trail
**What it does**
- Records pipeline stages, operator decisions, backend events, CI state, and fault conditions
- Supports reproducibility and debugging of plan and execution history

**What it enforces**
- Decisions are explainable, observable, and reproducible
- Sensitive data is excluded or redacted from logs
- Checkpointing after phase updates, transcript updates, and generated document updates
- Auditability of privileged and state-changing actions

---

### 22. Update and Distribution Subsystem
**What it does**
- Packages releases for native macOS distribution
- Supports Developer ID signing/notarization workflows
- Handles auto-update via Sparkle

**What it enforces**
- Signed, trusted application distribution
- Controlled update provenance
- Shell integrity across upgrades
- Update channel remains outside backend trust boundary

---

## Enforcement Order

The platform is designed so enforcement precedes automation. The typical sequence for a privileged autonomous build operation is:

1. **App launch**
   - Signed macOS shell starts
   - Local state and settings load
   - Backend process manager prepares runtime

2. **Operator authentication**
   - Biometric/local auth gate is presented
   - Session is established only on success
   - Keychain access becomes available only through shell-controlled session

3. **Backend bootstrap**
   - Shell launches Python backend
   - Authenticated IPC channel is established
   - Minimal required credentials/config are delivered

4. **Repository/spec intake**
   - Operator selects repository and source specs
   - Document ingestion pipeline parses and chunks content
   - Document Store embeds and indexes chunks
   - Injection patterns and malformed inputs are flagged

5. **Intent capture and planning**
   - Operator states build intent
   - Planning engine retrieves relevant spec context
   - PRD and PR-unit decomposition is proposed
   - Operator approves/corrects/splits/merges/excludes as needed

6. **Generation**
   - Consensus engine dispatches implementation requests to multiple providers
   - Provider adapter layer normalizes responses
   - Arbiter model consolidates outputs into candidate changes

7. **Review**
   - Multi-pass review pipeline checks conformance, quality, and risk
   - Retrieval engine supplies targeted spec context
   - Corrections or exclusions are applied if required

8. **Workspace application**
   - Git workspace orchestrator stages validated changes in isolated branch context
   - Commit messages and branch metadata are generated according to convention

9. **Validation**
   - Tests are run through defined validation paths, primarily CI-backed workflows
   - GitHub status checks are monitored
   - Failed checks block progression

10. **PR creation**
    - Draft PR is opened in GitHub with traceable metadata
    - Operator reviews and approves externally/in-app as supported

11. **Human gate**
    - Merge remains operator-controlled
    - On approval, the next planned PR unit may begin
    - Documentation regeneration may be triggered if configured

At every stage, policy, telemetry, and audit capture are cross-cutting and must not be bypassed.

---

## Component Boundaries

### macOS Shell must never
- Execute generated code
- Delegate Keychain ownership to Python
- Trust backend-originated requests without authenticated IPC validation
- Leave privileged session state implicitly open across unsafe lifecycle transitions
- Auto-approve gates, reviews, or merges

### SwiftUI/UI layer must never
- Directly store secrets
- Directly manipulate backend process internals
- Bypass shell session/auth state
- Perform hidden destructive actions

### Keychain subsystem must never
- Persist plaintext credentials to disk
- Expose raw secrets to logs or telemetry
- Allow unsessioned or unauthenticated retrieval

### IPC/XPC bridge must never
- Accept unauthenticated local traffic as trusted
- Carry ambiguous or schema-less commands for privileged operations
- Become a general execution tunnel

### Python backend must never
- Assume shell responsibilities for auth or local trust
- Persist shell-owned secrets beyond authorized runtime use
- Auto-merge PRs
- Execute generated code

### Consensus engine must never
- Treat a single provider output as inherently trusted
- Skip arbitration/review requirements for convenience
- Conceal source/provider attribution when needed for debugging or governance

### Provider adapters must never
- Leak provider credentials into application logs
- Expose vendor-specific semantics upward without normalization
- Expand trust boundary through arbitrary plugin execution

### Planning engine must never
- Advance irreversible plan transitions without operator approval where required
- Collapse multiple logical units into opaque, unreviewable changesets
- Invent specification authority not present in source docs or operator instruction

### Document Store must never
- Lose provenance for embedded chunks
- Silently mix embeddings from incompatible model/index configurations
- Treat ingested text as trusted instructions to the control plane

### Review pipeline must never
- Mark unreviewed generation as accepted
- Ignore exclusion lists or operator corrections
- Convert advisory findings into hidden auto-fixes without traceability

### Git/GitHub integration must never
- Push uncontrolled changes outside intended branch/PR scope
- Auto-merge on green CI
- Destroy attribution between plan item and repository artifact

### CI integration must never
- Treat missing status as success
- Hide failed checks from operator visibility
- Execute arbitrary generated code outside controlled repository test workflows

### Telemetry/audit subsystem must never
- Capture plaintext secrets
- Omit critical decision points
- Mutate operational state as a side effect of logging

---

## Key Data Flows

### 1. Authentication and Secret Access Flow
1. Operator opens app.
2. Shell presents biometric/local auth gate.
3. On success, shell creates active session.
4. Shell accesses Keychain entries needed for configured services.
5. Secrets remain shell-custodied and are only delivered over authenticated IPC as needed.
6. Backend uses delivered credentials for bounded operations.

**Key properties**
- Session-gated
- Shell-mediated
- No plaintext disk persistence
- Auditable secret access

---

### 2. Document Ingestion and Retrieval Flow
1. Operator loads TRDs/PRDs/spec documents.
2. Ingestion pipeline parses files and extracts structured text.
3. Chunker creates retrieval units with metadata.
4. Embedding subsystem computes vectors.
5. Index/store persists searchable representation.
6. Retrieval engine serves relevant chunks for planning/generation/review.

**Key properties**
- Provenance retained per chunk
- Embedding model/version compatibility required
- Re-embedding required after embedding model change
- Injection patterns are detected and surfaced

---

### 3. Intent-to-Plan Flow
1. Operator provides plain-language intent.
2. Planning engine retrieves relevant spec context.
3. Engine drafts PRD and PR decomposition.
4. Operator approves or issues corrections:
   - split
   - merge
   - move
   - remove
   - expand
   - correct
   - stop
5. Approved plan is checkpointed.

**Key properties**
- Human-directed planning
- Spec-scoped decomposition
- Transcript-backed changes
- Explicit phase/state updates

---

### 4. Multi-Provider Generation Flow
1. Backend packages task context plus retrieved specification material.
2. Provider adapters dispatch parallel requests to multiple models.
3. Candidate implementations and tests are returned.
4. Claude arbitration selects/merges/rewrites final candidate output.
5. Candidate diff passes to review pipeline.

**Key properties**
- Consensus-based generation
- Provider normalization
- Arbitration before acceptance
- No direct trust in raw model output

---

### 5. Review and Correction Flow
1. Candidate diff enters review pass 1.
2. Additional retrieval context is fetched as needed.
3. Passes 2 and 3 refine findings and verify corrections.
4. Operator may exclude files/areas or provide corrective direction.
5. Approved changes advance to workspace application.

**Key properties**
- Three-pass review required
- Correction loop is explicit
- Exclusions are operator-controlled
- Findings remain attributable

---

### 6. Git/CI/PR Flow
1. Validated changes are applied in isolated branch/worktree.
2. Commit metadata is generated according to Forge conventions.
3. Branch is pushed to remote.
4. Draft PR is opened.
5. CI workflows execute:
   - Python tests
   - macOS unit tests
   - XPC integration tests
6. Operator reviews results and decides merge.

**Key properties**
- Draft-first PR model
- CI as required gate
- No auto-merge
- One logical unit per PR

---

### 7. TRD Authoring / Spec Refinement Flow
1. Operator asks Forge to create or update technical requirements.
2. System proposes boundaries/sections.
3. Operator responds with approve/correct/expand/merge/split/remove.
4. Generated TRDs and transcript state are updated.
5. Output becomes part of the Document Store and future retrieval context.

**Key properties**
- Recursive specification-driven development
- Explicit operator governance
- Stateful checkpoints after each phase and response
- Newly authored docs feed future generation quality

---

## Critical Invariants

1. **Generated code is never executed by the agent runtime.**
   - Neither Swift shell nor Python backend may execute generated code as part of generation, review, or arbitration.

2. **Secrets are shell-owned and never stored in plaintext on disk.**
   - Keychain is the root of local secret custody.
   - Backend receives only controlled runtime access.

3. **All privileged actions require explicit trust establishment.**
   - Authentication, IPC, credential release, and merge progression are all gated by explicit checks.

4. **Human approval is mandatory at core control points.**
   - Plan approval, specification correction, exclusions, and merges remain operator-controlled.

5. **No auto-merge under any circumstance.**
   - CI success is necessary but never sufficient for merge.

6. **One pull request corresponds to one logical unit of work.**
   - Planning and workspace orchestration must preserve reviewable granularity.

7. **Retrieval provenance must be preserved end-to-end.**
   - Every retrieved chunk must remain traceable to source document and section.

8. **Embedding/index compatibility is strict.**
   - Changing embedding model requires re-embedding affected corpora.

9. **Policy, identity, telemetry, and enforcement are separable but linked.**
   - No subsystem may collapse these concerns into opaque behavior.

10. **All control decisions must be explainable and reproducible.**
    - Logs, transcripts, checkpoints, and state transitions must support reconstruction.

11. **The backend is untrusted for local identity and secret custody.**
    - It may orchestrate work, but it cannot become the root of trust.

12. **The UI must never silently advance ambiguous model outcomes.**
    - Ambiguity requires operator review, correction, or stop.

13. **CI status must be explicit.**
    - Missing or unknown status cannot be interpreted as success.

14. **Prompt-injection-like content in source documents is data, not authority.**
    - Ingested text can influence retrieval context but cannot override platform policy or control flow.

15. **Checkpointing is mandatory at state boundaries.**
    - After each phase, operator response, and generated TRD update, persistent execution state must reflect reality.

16. **Lifecycle transitions must not weaken authentication guarantees.**
    - Background/foreground changes, long biometric delays, and restart flows must preserve gate correctness.

17. **Trust is asserted and verified, never inferred implicitly.**
    - This is the governing rule behind shell/backend separation, IPC authentication, CI gating, and operator approval.

---