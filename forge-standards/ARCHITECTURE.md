# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software build platform implemented as a **two-process system**:

- A **Swift macOS shell** responsible for:
  - application lifecycle
  - UI and operator interaction
  - authentication and biometric gating
  - Keychain-backed secret custody
  - local orchestration
  - XPC / Unix-socket bridge ownership
  - packaging, updates, logging, and system integration

- A **Python backend** responsible for:
  - planning and decomposition
  - document ingestion and retrieval
  - multi-provider code generation
  - consensus and arbitration
  - review and repair loops
  - CI orchestration
  - git and GitHub operations
  - PR sequencing and stateful autonomous execution

The system is explicitly **not** a chat product and **not** a code execution runtime. It is a directed build agent that transforms:
1. repository + specifications + operator intent
2. into ordered planning artifacts and implementation units
3. then into tested draft pull requests
4. under operator approval gates.

The architecture is governed by the repository TRDs, with the loaded source material establishing these top-level principles:

- Swift and Python are **strictly separated by responsibility**
- generated code is **never executed by the product itself**
- secrets are owned by Swift and must not persist in plaintext on disk
- all merge actions require explicit operator approval
- trust must be explicit, verifiable, observable, and reproducible
- enforcement defaults to deny / block rather than suggest / allow

Core platform shape:

```text
Operator
  ↓
Swift macOS Shell
  ├─ UI / State / Auth / Keychain / Update / Telemetry
  ├─ XPC + authenticated local transport
  └─ Backend Process Supervisor
        ↓
     Python Backend
      ├─ Planning / PRD pipeline
      ├─ Document Store + Retrieval
      ├─ Consensus Engine
      ├─ Review / Repair pipeline
      ├─ CI orchestration
      ├─ Git / GitHub integration
      └─ Progress + result streaming
```

---

## Subsystem Map

Below, each subsystem lists:
- what it does
- what it enforces

### 1. macOS Application Shell

**Primary source:** TRD-1

**What it does**
- Packages Forge as a signed native `.app`
- Provides drag-to-Applications installation model
- Integrates Sparkle auto-update
- Owns top-level app lifecycle, windows, navigation, and shell state
- Hosts the SwiftUI operator interface
- Supervises backend startup, liveness, and shutdown
- Owns the authenticated local communication boundary with Python
- Defines Swift module boundaries and shell concurrency patterns

**What it enforces**
- Native-only shell ownership for secrets, identity, and operator presence
- No direct backend access to macOS credential stores
- Strict process boundary between UI/auth and intelligence/generation
- Stable shell-owned state model for project/session/backend status
- Local transport authentication before message exchange

---

### 2. SwiftUI Interface Layer

**Primary source:** TRD-8, referenced by TRD-1

**What it does**
- Renders project selection, intent entry, pipeline progress, PR cards, review states, approvals, and errors
- Presents cards, panels, and shell-native operator workflows
- Surfaces generated artifacts, checkpoints, stage outcomes, and corrective prompts
- Mediates explicit approval actions

**What it enforces**
- Operator-visible state for all consequential actions
- No hidden merge, approve, or trust decisions
- Review-first interaction model rather than conversational free-form execution
- Gated action surfaces for sensitive operations

---

### 3. Identity, Authentication, and Session Gate

**Primary source:** TRD-1; security requirements constrained by TRD-11

**What it does**
- Authenticates operator presence using biometrics / native authentication gates
- Manages session lifecycle and unlock duration
- Re-prompts when the app foregrounds or session conditions require it
- Controls access to secret-releasing operations and high-trust actions

**What it enforces**
- Secret access only after successful operator authentication
- Gate must never auto-answer
- Foreground return must not leave an expired or invalid gate open
- Session validity is explicit, time-bounded, and auditable

---

### 4. Keychain Secret Custody

**Primary source:** TRD-1; security model governed by TRD-11

**What it does**
- Stores provider API keys, GitHub credentials/tokens, and other sensitive material in Keychain
- Releases secrets only to authorized shell-controlled flows
- Supplies secrets to backend operations over the authenticated local channel when policy allows

**What it enforces**
- No plaintext secrets on disk, ever
- Python backend does not own persistent secret custody
- Secret release is contextual, explicit, and operator-gated where required
- Secret lifecycle is managed independently of backend generation state

---

### 5. Local IPC / XPC Bridge / Authenticated Unix Socket Transport

**Primary source:** TRD-1; referenced by TRD-10 for progress messages

**What it does**
- Connects Swift shell and Python backend
- Uses authenticated local transport with line-delimited JSON messages
- Carries commands, events, progress updates, stage transitions, errors, and result payloads
- Bridges shell UI state with backend execution state

**What it enforces**
- Message framing and typed command/result boundaries
- Local endpoint authentication before accepting backend traffic
- No implicit trust of local process identity without handshake/assertion
- Serializable, inspectable, replayable control events

---

### 6. Backend Process Supervisor

**Primary source:** TRD-1

**What it does**
- Launches bundled Python 3.12 backend
- Monitors process liveness and restart behavior
- Manages startup readiness and clean shutdown
- Coordinates environment setup for backend execution inside app constraints

**What it enforces**
- Shell-owned process creation and termination
- Controlled startup sequencing before operator actions reach backend
- Failure isolation between UI shell and backend runtime
- No dependence on shell login rc files or interactive shell behavior

---

### 7. Planning and Intent Decomposition Engine

**Primary sources:** README product behavior; TRD-3 references indicate stage pipeline ownership

**What it does**
- Accepts repository + loaded TRDs + operator intent
- Decomposes intent into an ordered PRD plan
- Decomposes each PRD into a sequence of implementation PRs
- Maintains plan progression, checkpointing, and operator-visible advancement

**What it enforces**
- Work must be spec-driven
- Decomposition must remain scoped to declared intent and approved specifications
- Logical unit boundaries map to discrete pull requests
- Progression is ordered; next PR follows prior review/approval state

---

### 8. PRD / TRD Boundary Management and Specification Workflow

**Primary sources:** loaded workflow content and operator command grammar

**What it does**
- Supports generation, correction, approval, split, merge, move, remove, and expansion of requirement boundaries
- Tracks generated TRDs, phase completion, transcript, and operator interventions
- Maintains estimated sections and spec ownership transitions

**What it enforces**
- Specification boundaries are explicit and operator-correctable
- Boundary changes are recorded through structured actions
- No silent reshaping of subsystem ownership
- Source-of-truth documents remain authoritative over implementation

Supported operator actions evidenced in source material include:
- approve / yes / ok
- correct
- expand
- split TRD-X into ...
- merge TRD-X and TRD-Y
- move ownership from one TRD to another
- remove TRD-X
- select lenses
- exclude files / directories / concerns
- stop / no

---

### 9. Consensus Engine

**Primary source:** TRD-2

**What it does**
- Runs two model providers in parallel for generation
- Uses Claude + GPT-4o as the paired providers
- Has Claude arbitrate final outcomes
- Produces implementation proposals, comparisons, and reconciled outputs
- Drives generation under context assembled from specs, repo state, and retrieval output

**What it enforces**
- No single-provider unilateral generation path for final autonomous output
- Arbitration is explicit, not inferred
- Provider responses remain bounded by retrieval and planning context
- Final output is attributable to a consensus/arbitration step

---

### 10. Provider Adapter Layer

**Primary source:** TRD-2

**What it does**
- Normalizes calls to multiple LLM vendors
- Handles provider-specific request formatting, retries, limits, and response parsing
- Provides a common interface to the consensus engine

**What it enforces**
- Provider isolation behind stable interfaces
- No provider-specific assumptions leaking into planning/review logic
- Comparable outputs for arbitration
- Centralized handling of provider errors and transient failures

---

### 11. Build / Stage Pipeline Orchestrator

**Primary sources:** README product flow; TRD-3 references; TRD-10 references to Stage 1/5 doc filtering

**What it does**
- Executes the end-to-end autonomous workflow in stages
- Coordinates planning, context retrieval, generation, review, repair, CI, and PR publication
- Emits stage progress and checkpoints
- Supports stop/continue semantics based on operator responses and failures

**What it enforces**
- Ordered stage transitions
- Stage-specific contracts for inputs, outputs, and failure handling
- Checkpointing after major transitions and operator responses
- Repeatable progression through the same control flow for reproducibility

The source material indicates explicit stage awareness including:
- stage result success/failure
- action-based continuation or stop
- stage-specific document filters
- progress emission to shell

---

### 12. Document Store and Retrieval Engine

**Primary source:** TRD-10

**What it does**
- Ingests technical documents and repository-relevant text
- Stores chunked content under per-project cache directories
- Embeds and indexes retrieved content
- Supplies contextual snippets to generation and review stages
- Auto-loads product context for generation

Storage root specified in TRD-10:

```text
~/Library/Application Support/ForgeAgent/cache/{project_id}/
```

**What it enforces**
- Per-project retrieval isolation
- Deterministic context assembly from ingested sources
- Retrieval-scoped relevance rather than whole-corpus dumping
- Re-embedding requirement when embedding model changes
- Small local index footprint acceptable for always-loaded index behavior

---

### 13. Review and Repair Cycle

**Primary sources:** README; TRD-6 references in TRD-10

**What it does**
- Executes a 3-pass review cycle on generated changes
- Injects document retrieval context into review
- Identifies defects, policy violations, regressions, or specification mismatches
- Produces targeted fixes before CI and PR creation

**What it enforces**
- Generated code is not accepted without review
- Review is structured and iterative
- Spec compliance is checked before PR publication
- Repair remains scoped to discovered issues and exclusions

---

### 14. CI Orchestration

**Primary sources:** workflow headings from loaded content

**What it does**
- Runs repository CI as part of autonomous validation
- Integrates with named workflows including:
  - `Forge CI — Python / test`
  - `Forge CI — macOS / unit-test`
  - `Forge CI — macOS / xpc-integration-test`
- Collects pass/fail outcomes and surfaces them to the operator and pipeline

**What it enforces**
- Changes are validated before PR publication
- Platform-specific and integration-specific test lanes remain distinct
- CI outcomes are part of build state, not optional metadata
- Failures feed back into review/repair rather than being ignored

---

### 15. Git Workspace Manager

**Primary sources:** README behavior; bootstrap / commit naming examples

**What it does**
- Creates branches for implementation units
- Applies generated changes into the repository workspace
- Tracks diffs, branch names, commit metadata, and PR unit boundaries
- Prepares local state for CI and publication

**What it enforces**
- One pull request per logical implementation unit
- Controlled mutation of repository contents
- Clear correspondence between plan item, branch, commit, and PR
- No silent workspace sprawl outside tracked build units

---

### 16. GitHub Integration

**Primary sources:** README behavior; naming conventions in loaded content

**What it does**
- Opens draft pull requests
- Posts structured commit messages and PR titles
- Coordinates claim/build/publish semantics
- Surfaces PR URLs and progression through the shell UI

Observed naming patterns include:
- `forge-agent[todd-gould]: PR007 implement idempotency key expiry`
- `forge-agent[todd-gould]: PRD-003 — Transaction Idempotency Layer`
- `forge-agent[{engineer_id}]: {message}`
- `forge-ledger[sara-chen]: claim PR #8`
- bootstrap form: `forge-agent: add CI workflow`

**What it enforces**
- Draft PR publication instead of silent direct merge
- Strong identity labeling in git/GitHub messages
- Sequential PR workflow controlled by approval state
- Operator review point before merge

---

### 17. Documentation Regeneration

**Primary source:** README

**What it does**
- Optionally regenerates documentation after build completion
- Aligns implementation outputs with specification/doc updates as a terminal workflow step

**What it enforces**
- Documentation refresh is post-build and optional
- Documentation generation follows implementation, not vice versa
- Generated docs remain downstream of approved implementation changes

---

### 18. Checkpointing and Transcript Persistence

**Primary sources:** loaded state update bullets

**What it does**
- Updates checkpoints:
  - after each TRD is generated
  - after each phase completes
  - after every operator response
- Persists transcript and workflow progression
- Enables recovery and continuity of long-running autonomous sessions

**What it enforces**
- Durable workflow state across interruptions
- Explicit recovery points
- Reconstructable operator decision history
- Phase/state transitions that are externally observable

---

### 19. Exclusion / Scope Control System

**Primary sources:** operator command grammar

**What it does**
- Lets operators exclude files, directories, and concern lenses from fixes or analysis
- Applies targeted scope reduction to planning, review, or repair steps

Examples from source material:
- `exclude src/legacy/`
- `exclude src/old_api.py`
- `exclude security in src/vendor/`
- `select lenses`

**What it enforces**
- Scoped autonomy
- Respect for explicit operator boundaries
- Separation between available analysis and permitted mutation
- No repair outside stated exclusion rules

---

### 20. Security and Trust Enforcement Layer

**Primary source:** TRD-11, referenced as governing all security-relevant changes

**What it does**
- Defines product-wide controls for credentials, external content, generated code, CI, and trust boundaries
- Constrains both Swift and Python subsystems
- Supplies the normative security model for data handling and execution restrictions

**What it enforces**
- Generated code must never be executed by the product
- Credentials and secrets remain strongly isolated
- External content is treated as untrusted input
- Security-sensitive operations require explicit controls and auditability
- CI and automation cannot become a backdoor around operator review

---

### 21. Packaging, Signing, and Distribution

**Primary source:** TRD-1

**What it does**
- Produces signed macOS application bundles
- Supports Developer ID distribution
- Integrates auto-update delivery

Observed signing reference:
- `Developer ID Application: YouSource.ai ({TEAM_ID})`

Observed app path in workflows:
- `$GITHUB_WORKSPACE/build/Release/ForgeAgent.app`

**What it enforces**
- Native distribution integrity
- Signed application provenance
- Controlled update path
- Stable bundle layout required by shell/backend co-packaging

---

### 22. Telemetry, Logging, and Observability

**Primary sources:** Forge architecture rules; TRD-1 references to logging; stage progress references

**What it does**
- Records state transitions, progress updates, failures, and operator-visible issues
- Supports explanation of control decisions and pipeline behavior
- Emits enough structured data for reproducibility and troubleshooting

**What it enforces**
- Decisions must be explainable, observable, and reproducible
- Policy and enforcement outcomes must be inspectable
- Failure conditions are surfaced rather than silently absorbed
- Telemetry is separated from policy itself, while linked to it

---

### 23. Policy / Lens Selection Layer

**Primary sources:** architecture rules and operator command grammar

**What it does**
- Applies domain-specific evaluation lenses to generation/review workflows
- Allows operator-selected or excluded concern categories
- Scopes analysis such as security or other review dimensions

**What it enforces**
- Enforcement dimensions remain explicit
- Policy scopes can be narrowed or expanded transparently
- Analysis categories are selectable, not hidden heuristics
- Concern-specific review can be suppressed only by explicit operator input

---

## Enforcement Order

This section describes the dominant runtime call order and control precedence.

### A. Application startup

1. macOS launches the signed Swift application shell
2. Shell initializes app state, logging, update subsystem, and UI
3. Shell starts backend supervisor
4. Supervisor launches bundled Python backend
5. Shell and backend establish authenticated local transport
6. Backend readiness is reported to shell
7. Operator gains access to project workflows only after shell-ready and backend-ready states are satisfied

### B. Authenticated operator action path

1. Operator initiates a sensitive action
2. Shell checks session/gate validity
3. If required, biometric/native auth prompt is presented
4. On success, shell unlocks the action window/session
5. If secrets are needed, shell retrieves them from Keychain
6. Shell sends scoped command payload to backend over authenticated transport
7. Backend executes only the requested non-secret business logic

### C. End-to-end build flow

1. Operator selects repository and loaded specifications
2. Operator enters plain-language intent
3. Planning engine decomposes intent into PRD plan
4. PRD/TRD boundary workflow may refine scope
5. Pipeline orchestrator creates the next logical PR work unit
6. Document store retrieves relevant context for the current stage
7. Consensus engine invokes both model providers in parallel
8. Claude arbitrates/reconciles provider outputs
9. Workspace manager applies candidate changes
10. Review subsystem runs structured 3-pass review
11. Repair loop fixes review findings within current scope/exclusions
12. CI orchestration runs configured workflows
13. If CI fails, control returns to repair/review as permitted by pipeline policy
14. If CI passes, GitHub integration opens a draft PR
15. Shell presents result to operator
16. Operator reviews and approves or rejects progression
17. Only after approval does the system proceed to the next PR
18. Merge remains operator-controlled and is never automatic

### D. Retrieval-enabled generation path

1. Stage begins
2. Stage-specific doc filter is computed
3. Document store retrieves relevant chunks for project and phase
4. Retrieved context is injected into generation/review request payloads
5. Providers produce outputs bounded by the assembled context
6. Arbitration and review validate against source specs and retrieved evidence

### E. Checkpoint and recovery path

1. Operator response received or phase completes
2. Transcript is updated
3. Phase/checkpoint state is persisted
4. If interrupted, shell/backend reload current state
5. Workflow resumes from the last durable checkpoint rather than recomputing entire history

---

## Component Boundaries

This section defines what each subsystem must never do.

### macOS Application Shell must never
- perform autonomous code generation logic that belongs to the Python backend
- store secrets in plaintext files
- permit backend access to Keychain APIs directly
- auto-approve operator gates
- auto-merge pull requests

### SwiftUI Interface must never
- make hidden policy decisions not represented in state/actions
- imply approval from passive viewing
- conceal CI, review, or arbitration failures

### Authentication / Session subsystem must never
- leave a stale gate open after session invalidation
- bypass biometric/native auth for protected actions
- silently extend trust windows without policy basis

### Keychain custody subsystem must never
- export secrets to persistent backend storage
- release secrets without shell-side authorization checks
- rely on environment file plaintext persistence

### IPC / local transport layer must never
- trust unauthenticated local peers
- accept malformed or unframed message payloads as valid commands
- collapse typed control and data events into opaque blobs

### Backend supervisor must never
- assume interactive shell environment initialization
- source `.zshrc` or `.bash_profile`
- let backend startup failure masquerade as ready state

### Planning engine must never
- invent scope that contradicts loaded TRDs/PRDs
- skip decomposition directly to arbitrary code mutation
- reorder approved execution flow without explicit state transition

### PRD/TRD boundary manager must never
- change document ownership silently
- merge/split/remove boundaries without recording operator-visible actions
- treat generated drafts as authoritative without approval

### Consensus engine must never
- allow a final autonomous output without arbitration
- collapse to implicit single-model trust for final result
- exceed provider abstraction boundaries

### Provider adapter layer must never
- leak provider-specific semantics into higher orchestration layers
- persist provider secrets outside approved secret channels
- bypass centralized error handling

### Pipeline orchestrator must never
- skip mandatory review or CI stages for normal PR production
- continue after a stop action
- hide stage failures from checkpoint state

### Document store must never
- mix contexts across project IDs
- inject unbounded corpus content without retrieval selection
- ignore embedding-version invalidation requirements

### Review subsystem must never
- treat generated code as accepted without review passes
- modify excluded files or excluded concern areas
- suppress spec violations for convenience

### CI subsystem must never
- stand in for local execution of generated code by the product
- mark failing validations as passing
- bypass required workflow categories when configured

### Git workspace manager must never
- mutate outside the intended repository workspace
- blur boundaries between distinct PR work units
- hide generated diffs from later review/publication

### GitHub integration must never
- auto-merge changes
- publish directly to mainline without PR workflow
- erase engineer identity labeling from messages

### Documentation regeneration must never
- precede implementation validation as a source of truth replacement
- overwrite authoritative requirement documents silently

### Checkpointing subsystem must never
- lose operator transcript updates after acknowledged responses
- resume from non-durable transient state when a durable checkpoint exists

### Security / trust layer must never
- permit execution of generated code
- infer trust where explicit verification is possible
- entangle policy, telemetry, identity, and enforcement beyond their defined interfaces

---

## Key Data Flows

### 1. Secret delivery flow

```text
Operator action
  → Shell auth gate
  → Keychain lookup in Swift
  → scoped in-memory secret release
  → authenticated local transport
  → Python backend uses secret for outbound provider/GitHub API call
  → secret not persisted by backend
```

Properties:
- shell-originated
- ephemeral in memory
- no plaintext disk persistence
- backend consumption only

---

### 2. Intent-to-PR flow

```text
Intent
  → planning decomposition
  → PRD sequence
  → current PR work unit
  → retrieval context assembly
  → dual-provider generation
  → arbitration
  → review passes
  → CI
  → draft PR publication
  → operator approval
  → next PR
```

Properties:
- ordered
- checkpointed
- review-validated
- approval-gated

---

### 3. Retrieval flow

```text
Docs / repo-derived text
  → ingest / chunk
  → embed / index
  → per-project cache
  → stage-specific query
  → relevant chunk set
  → generation/review prompt context
```

Properties:
- project-isolated
- stage-aware
- embedding-version-sensitive

---

### 4. Progress and state flow

```text
Backend stage event
  → line-delimited JSON message
  → shell bridge
  → app state reducer
  → SwiftUI presentation
  → operator action
  → command message back to backend
```

Properties:
- typed
- observable
- recoverable via checkpointing

---

### 5. CI feedback flow

```text
Workspace changes
  → CI workflow invocation
  → pass/fail results
  → pipeline policy decision
      ↳ fail: repair/review loop
      ↳ pass: PR creation
```

Properties:
- validation-gated
- non-optional for standard PR flow
- visible to operator

---

### 6. Checkpoint flow

```text
Phase completion / operator response / TRD generation
  → transcript update
  → checkpoint persist
  → resumable state snapshot
```

Properties:
- durable
- incremental
- recovery-oriented

---

## Critical Invariants

These invariants are architectural and must hold across all implementations.

### Trust and enforcement
1. **Trust must never be inferred when it can be explicitly asserted and verified.**
2. **Identity, policy, telemetry, and enforcement remain separable but linked.**
3. **All control decisions must be explainable, observable, and reproducible.**
4. **Forge defaults to enforcement, not suggestion.**

### Process and responsibility separation
5. **Swift owns UI, auth, Keychain, and local process orchestration.**
6. **Python owns planning, generation, retrieval, review, CI orchestration, and GitHub operations.**
7. **Neither process may erase the boundary between shell-controlled trust and backend-controlled intelligence.**

### Secret handling
8. **No plaintext secrets are ever written to disk.**
9. **Backend secret access is mediated by Swift-controlled release paths only.**
10. **Secret custody and generation logic remain separate.**

### Execution safety
11. **Generated code is never executed by the Forge product.**
12. **CI validates repository changes; the product itself is not a code execution environment for generated artifacts.**
13. **External content and generated content are treated as untrusted until validated through review/policy/CI.**

### Human control
14. **Operator must approve all merges; auto-merge is forbidden.**
15. **Sensitive actions require explicit operator authentication and/or approval gates.**
16. **The next PR may proceed only according to pipeline approval state.**

### Pipeline correctness
17. **Every implementation unit maps to a discrete logical pull request.**
18. **Consensus output requires parallel provider generation plus Claude arbitration.**
19. **Review occurs before PR publication.**
20. **CI occurs before draft PR publication in the standard autonomous path.**
21. **Failures feed back into structured repair or stop states; they are never silently ignored.**

### Specification authority
22. **TRDs are the source of truth for subsystem behavior.**
23. **Boundary changes to TRDs/PRDs must be explicit, reviewable, and checkpointed.**
24. **Implementation may not invent requirements that contradict authoritative specs.**

### Retrieval integrity
25. **Document retrieval is per-project and stage-aware.**
26. **Embedding model changes require re-embedding affected corpora.**
27. **Context injection must be bounded and traceable to retrieved sources.**

### State and recoverability
28. **Operator transcript, phase state, and checkpoints are durable across interruptions.**
29. **Stage progression is explicit and resumable.**
30. **UI state must reflect backend truth through authenticated, typed transport messages.**

### Platform integrity
31. **The app is distributed as a signed macOS application bundle.**
32. **Backend startup environment is controlled and must not depend on interactive shell initialization.**
33. **Local transport peers must authenticate before exchanging trusted control messages.**

---

## Notes on Architectural Style

Forge uses a **policy-first orchestration architecture** with these defining traits:

- **native trust shell + isolated intelligence engine**
- **spec-driven decomposition before code generation**
- **retrieval-augmented, consensus-based generation**
- **review/repair/CI before publication**
- **operator approval before merge progression**
- **strong local security controls without collapsing usability**

This architecture is intentionally optimized for:
- autonomous but reviewable software production
- deterministic responsibility boundaries
- secure local secret handling
- explicit approval and reproducibility
- future extension across broader endpoint, network, cloud, and AI-runtime enforcement domains, as required by the Forge architecture rules.