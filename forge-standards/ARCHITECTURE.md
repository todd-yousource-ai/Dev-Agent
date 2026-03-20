# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software-building platform composed of a **trusted local shell** and an **untrusted-but-constrained intelligence backend**.

At the highest level, the platform:

1. Loads a target repository and technical specifications (TRDs).
2. Builds a structured implementation plan (PRD graph and ordered PR sequence).
3. Generates implementation and tests using multiple LLM providers in parallel.
4. Applies consensus, arbitration, review, and policy checks.
5. Runs validation and CI without executing generated application code as part of the agent itself.
6. Opens GitHub draft pull requests for operator review.
7. Advances incrementally, one logical PR at a time.
8. Optionally regenerates documentation from the completed implementation.

The architecture is explicitly split into **two processes**:

- **Swift macOS Shell**
  - UI, application lifecycle, onboarding, local state, authentication gates, Keychain, update/install, project/session orchestration, XPC/socket supervision, progress rendering.
- **Python Backend**
  - Planning, consensus generation, document ingestion/retrieval, review pipeline, Git/GitHub operations, CI orchestration, state checkpoints, and structured outputs.

The two processes communicate over an **authenticated local Unix socket** using **line-delimited JSON**. The shell is the trust anchor for user presence and local secret custody. The backend is the execution engine for content synthesis and repository automation, but remains bounded by strict security and process-isolation rules.

Core product behavior is governed by the repository TRDs, with the shell and backend acting as concrete implementations of those technical contracts.

---

## Subsystem Map (one entry per subsystem: what it does, what it enforces)

### 1. macOS Application Shell
**Primary source:** TRD-1

**What it does**
- Packages Forge as a native macOS app bundle.
- Owns app lifecycle, SwiftUI navigation, local settings, and user-visible orchestration.
- Installs and updates via standard macOS application distribution patterns and Sparkle.
- Supervises backend launch and local IPC.
- Manages project/session state visible to the operator.
- Bridges progress/events from backend to UI.

**What it enforces**
- The shell is the only component allowed to own platform-native identity and secret workflows.
- User presence and gated actions must pass through native authentication paths.
- The shell must never delegate secret custody to the Python backend.
- The shell must preserve process separation and authenticated IPC boundaries.

---

### 2. SwiftUI Interface Layer
**Primary source:** TRD-8

**What it does**
- Renders the app’s panes, cards, progress views, plan/review surfaces, gating prompts, and status indicators.
- Presents pipeline state, PRD/PR progression, generated artifacts, and review decisions.
- Provides explicit operator controls for approvals, exclusions, lens selections, and scope corrections.
- Displays long-running pipeline progress and failure states.

**What it enforces**
- Human approval boundaries are explicit and visible.
- The UI must not silently auto-advance gated decisions.
- The UI must not infer approvals from ambiguous operator input.
- Operator actions are serialized into structured commands, not free-form hidden control flow.

---

### 3. Authentication, Session, and Biometric Gate
**Primary source:** TRD-1; security rules from TRD-11

**What it does**
- Performs local authentication and user presence checks.
- Uses biometric/system auth before protected actions.
- Controls session lifecycle and gate-open/gate-closed state.
- Manages foreground/background relock behavior.

**What it enforces**
- Sensitive actions require fresh local authorization.
- Gate state must not remain open incorrectly after app lifecycle transitions.
- The platform must never auto-answer a gate.
- Authentication latency/failure paths are observable and handled explicitly.

---

### 4. Keychain and Secret Custody
**Primary source:** TRD-1; security rules from TRD-11

**What it does**
- Stores provider/API credentials and other local secrets.
- Supplies secrets to backend only through narrow, controlled delivery paths.
- Keeps long-lived secret material in macOS-native secure storage.

**What it enforces**
- Secret persistence is native-only; Python does not become the system of record for secrets.
- Secret retrieval requires the shell’s policy checks and authentication controls.
- Secret access paths are designed to avoid deadlock and unauthorized replay.
- Secrets must not be exposed in logs, transcripts, or generated artifacts.

---

### 5. Local IPC / XPC / Unix Socket Bridge
**Primary source:** TRD-1; implementation touchpoint includes `ForgeAgent/XPCBridge.swift`

**What it does**
- Establishes and supervises local interprocess communication between Swift and Python.
- Encodes requests/responses/events as line-delimited JSON.
- Carries progress messages, state updates, command invocations, and credential delivery.
- Supports backend health monitoring and failure recovery.

**What it enforces**
- Communication is authenticated and local-only.
- Messages are structured, versioned by contract, and not arbitrary code execution channels.
- IPC must not bypass shell-owned auth/secret boundaries.
- Transport errors are surfaced, recoverable, and do not silently corrupt workflow state.

---

### 6. Python Backend Runtime
**Primary source:** TRD-1 and dependent backend TRDs

**What it does**
- Hosts the autonomous build engine.
- Coordinates planning, generation, review, retrieval, git operations, and CI execution.
- Maintains deterministic state progression through pipeline stages.
- Emits structured progress and result events to the shell.

**What it enforces**
- The backend never becomes a UI or secret-custody authority.
- Generated code is treated as data unless explicitly validated by external build/test tooling.
- The backend must respect security policy and stage contracts from all owning TRDs.
- Recovery is checkpoint-based rather than ad hoc hidden state mutation.

---

### 7. Consensus Engine
**Primary source:** TRD-2

**What it does**
- Executes multi-model generation using at least two providers in parallel.
- Uses Claude + GPT-4o style dual-provider generation with Claude as final arbitrator per product description.
- Produces implementation candidates, compares outputs, arbitrates disagreements, and emits structured selected results.
- Injects retrieval context per generation through `auto_context()`.

**What it enforces**
- No single model output is treated as authoritative without the defined consensus/arbitration flow.
- Consensus inputs and outputs are structured and attributable.
- Arbitration is bounded by the selected prompt/spec context rather than ungrounded free generation.
- Provider outputs are reviewed before becoming PR content.

---

### 8. Provider Adapter Layer
**Primary source:** TRD-2

**What it does**
- Normalizes interaction with external model providers.
- Encapsulates provider-specific request formats, retries, timeouts, metadata, and response normalization.
- Allows the consensus engine to invoke multiple providers through a common contract.

**What it enforces**
- Provider-specific quirks do not leak upward into planning/review logic.
- Authentication/configuration per provider is explicit.
- Failures are normalized into shared error contracts.
- Providers remain pluggable and independently testable.

---

### 9. Planning Engine / PRD Decomposition
**Primary source:** PRD/TRD planning flows referenced across README and loaded prompts

**What it does**
- Converts repository specs and operator intent into an ordered PRD plan.
- Splits work into logical pull requests.
- Supports plan refinement via explicit operator feedback:
  - approve
  - correct
  - expand
  - split
  - merge
  - move
  - remove
  - stop

**What it enforces**
- Planning is specification-driven, not chat-driven.
- Scope changes are explicit and operator-auditable.
- Boundary ownership can be revised only through structured correction workflows.
- Ordered execution is maintained so downstream PRs build atop reviewed prior work.

---

### 10. Build Thread / Orchestration State Machine
**Primary source:** stage semantics from source excerpts

**What it does**
- Materializes a running workstream from an approved plan.
- Tracks current phase, PRD, PR, and transcript.
- Advances through phases and resumes from checkpoints.
- Applies restart rules:
  - If mid-PR: retry current PR from scratch
  - If between PRs: start next PR
  - If PRD complete: start next PRD

**What it enforces**
- Progress is checkpointed after important state transitions.
- Operator interactions are durable and replayable.
- Recovery behavior is deterministic.
- The agent does not skip required intermediate states after failure.

---

### 11. Review Pipeline
**Primary source:** README, TRD-6 references, stage notes

**What it does**
- Applies multi-pass review to generated changes before PR creation.
- Performs review using repository context, retrieved spec context, and policy checks.
- Supports issue exclusion and scope filters from the operator.
- Produces structured review outcomes and corrected iterations.

**What it enforces**
- Generated output must pass review before becoming a PR.
- Review uses explicit context and exclusions rather than hidden heuristics.
- Security- and spec-relevant issues cannot be silently ignored.
- Review stages are traceable and reproducible.

---

### 12. Document Store and Retrieval Engine
**Primary source:** TRD-10

**What it does**
- Ingests documents, TRDs, repository context, and related technical materials.
- Chunks, embeds, indexes, stores, and retrieves relevant context for generation and review.
- Stores project-scoped cache under:

```text
~/Library/Application Support/ForgeAgent/cache/{project_id}/
```

- Supplies contextual retrieval to:
  - TRD-2 consensus generation via `auto_context()`
  - TRD-3 stage filters
  - TRD-6 review context
  - TRD-7 product context auto-load

**What it enforces**
- Context injection is bounded, retrievable, and project-scoped.
- Embedding/indexing behavior is explicit; embedding model changes require re-embedding.
- Retrieval is a support subsystem, not a hidden source of authority.
- Index lifecycle remains predictable; per excerpt, explicit unload is unnecessary when index size permits always-loaded operation.

---

### 13. Repository Context / Product Context Loader
**Primary source:** TRD-10, TRD-7 references

**What it does**
- Loads repository content and document context needed for planning/generation/review.
- Auto-loads product context for the active build thread.
- Supports filtering based on operator-selected scope or lens selection.

**What it enforces**
- Only relevant context is promoted into model prompts.
- Exclusions are honored consistently across stages.
- Context assembly is deterministic and auditable.

---

### 14. Lens and Scope Filter System
**Primary source:** stage command excerpts

**What it does**
- Allows operator-directed inclusion/exclusion of analysis and remediation scopes.
- Supports:
  - selecting lenses
  - excluding security in specific directories
  - excluding entire directories
  - excluding specific files
- Applies scope controls to planning and review.

**What it enforces**
- The agent does not widen scope implicitly once operator filters are set.
- Excluded files/directories are not reintroduced by later stages.
- Lens-based analysis remains operator-driven and explainable.

---

### 15. Git Workspace Manager
**Primary source:** README and CI/workflow references

**What it does**
- Clones/opens the working repository.
- Creates branches, stages modifications, commits generated changes, and prepares pull request artifacts.
- Maintains one PR per logical unit of work.
- Coordinates generated file sets across source, tests, workflows, and app code.

**What it enforces**
- Repository mutations are organized into isolated logical branches.
- Commit messages and PR titles follow defined patterns, e.g.:
  - `forge-agent[{engineer_id}]: {message}`
  - `forge-agent[todd-gould]: PR007 implement idempotency key expiry`
  - `forge-agent[todd-gould]: PRD-003 — Transaction Idempotency Layer`
  - bootstrap form: `forge-agent: add CI workflow`
- Workspace operations remain reproducible and attributable.

---

### 16. GitHub Integration
**Primary source:** README and workflow strings

**What it does**
- Opens draft pull requests against the target repository.
- Associates generated branches, commits, PR metadata, and CI status.
- Supports iterative progression where the next PR is built while the operator reviews the previous one.
- May support ancillary repository automation such as issue references or PR claim semantics (e.g. `forge-ledger[sara-chen]: claim PR #8` if present in project workflows).

**What it enforces**
- External repository actions occur only after required local generation/review stages pass.
- Draft PR creation preserves human review before merge.
- GitHub interactions use explicit repository state, not inferred conversational state.

---

### 17. CI Orchestration Layer
**Primary source:** workflow references including:
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`

**What it does**
- Executes validation workflows for generated changes.
- Coordinates local and/or GitHub-hosted CI checks.
- Collects pass/fail outputs for review and PR reporting.
- Detects changes that accidentally trigger broad rebuilds.

**What it enforces**
- PRs are validated before advancement.
- CI definitions are part of the controlled repository change set.
- Build/test feedback is explicit input into progression decisions.
- CI execution is separated from arbitrary agent-side execution of generated app code.

---

### 18. Checkpoint and Transcript Store
**Primary source:** stage persistence excerpts

**What it does**
- Persists orchestration state:
  - after each phase completes
  - after each TRD is generated
  - after every operator response
- Stores transcripts and progress markers needed for resume/recovery.

**What it enforces**
- Crash recovery and resume are deterministic.
- Human instructions remain part of the durable state model.
- The backend cannot “forget” prior operator constraints after restart.
- Checkpoints define legal restart points.

---

### 19. Documentation Regeneration Subsystem
**Primary source:** README

**What it does**
- Optionally regenerates project documentation after a build completes.
- Uses completed implementation state as source material for updated docs.

**What it enforces**
- Documentation updates are downstream of implementation, not substitutes for it.
- Regenerated docs remain tied to reviewed/validated repository state.
- Documentation generation remains within the same review/PR discipline when committed.

---

### 20. Installer / Updater
**Primary source:** TRD-1

**What it does**
- Packages Forge as a signed macOS application.
- Supports drag-to-Applications installation and Sparkle-based auto-update.
- Operates under Developer ID distribution constraints, including identity similar to:
  - `Developer ID Application: YouSource.ai ({TEAM_ID})`

**What it enforces**
- Distribution is signed and native to macOS trust mechanisms.
- Updates preserve application identity and integrity.
- Runtime components are delivered as part of a controlled app bundle.

---

### 21. Launch / Background Execution Environment
**Primary source:** loaded source excerpt `(LaunchAgent does not source .zshrc or .bash_profile)`

**What it does**
- Starts backend and auxiliary processes in a controlled launch context.
- Ensures runtime environment does not depend on interactive shell profiles.

**What it enforces**
- Execution assumptions are explicit and reproducible.
- Backend startup cannot rely on developer-local shell customization.
- Environment-sensitive behavior is configured by application policy, not incidental shell state.

---

### 22. Security Policy and Trust Boundary Layer
**Primary source:** TRD-11; reinforced by AGENTS/CLAUDE instructions and architecture rules

**What it does**
- Defines cross-cutting security requirements for credentials, external content, generated code, CI, and enforcement behavior.
- Constrains every other subsystem.
- Supplies rules for trust, verification, observability, and separation of enforcement concerns.

**What it enforces**
- Trust must be asserted and verified explicitly, never inferred when verification is possible.
- Identity, policy, telemetry, and enforcement remain separable but linked.
- All control decisions are explainable, observable, and reproducible.
- Components default to enforcement, not suggestion.
- User-friction minimization must not weaken enforcement guarantees.
- The platform is designed for future scaling across endpoint, network, cloud, and AI runtime environments.

---

## Enforcement Order (what calls what, in sequence)

The dominant end-to-end control flow is:

1. **Application Shell initializes**
   - Loads app state, project catalog, settings, and update status.
   - Restores last known session/checkpoint if applicable.

2. **Authentication gate validates user presence**
   - Shell performs native auth for protected operations.
   - Keychain access remains blocked until gate/policy allows it.

3. **Shell establishes backend process and authenticated IPC**
   - Python runtime is launched/supervised.
   - Unix socket/XPC bridge is established.
   - Capability/health handshake completes.

4. **Project and document context are loaded**
   - Repository path/project metadata are resolved.
   - Document Store ingests or reuses indexed context.
   - Product context and repository context are assembled.

5. **Planning engine builds or resumes work plan**
   - Operator intent + TRDs + repository state produce PRD decomposition.
   - Operator may approve/correct/split/merge/move/remove boundaries.

6. **Build thread is created or resumed**
   - Current phase, PRD, PR, transcript, exclusions, and lenses are checkpointed.
   - Ordered execution begins.

7. **For each PR unit**
   - Context retrieval selects relevant technical/document context.
   - Consensus Engine invokes multiple provider adapters in parallel.
   - Arbitration selects/combines acceptable implementation output.
   - Changes and tests are materialized into the workspace.

8. **Review pipeline executes**
   - Multi-pass review checks code, tests, spec alignment, and policy constraints.
   - Exclusions and operator-selected lenses are applied.
   - If review fails, generation/revision loops continue or PR is retried from scratch per recovery rules.

9. **Validation and CI execute**
   - Repository tests/workflows run.
   - CI status becomes gating input for PR readiness.

10. **Git/GitHub publication**
    - Branch is committed using controlled commit conventions.
    - Draft PR is opened.
    - Results are surfaced to the operator.

11. **Checkpoint and progression**
    - State is checkpointed.
    - If approved and work remains, next PR starts.
    - If PRD completes, next PRD begins.
    - If the plan completes, optional documentation regeneration may run.

This sequence is intentionally enforcement-heavy: every transition from planning to generation to publication passes through explicit review, validation, and state persistence.

---

## Component Boundaries (what each subsystem must never do)

### macOS Application Shell must never
- Execute backend planning/generation logic itself.
- Store secrets in unsecured app-local plaintext stores.
- Auto-approve gated actions.
- Collapse trust boundaries by passing unrestricted host authority to Python.

### SwiftUI Interface Layer must never
- Smuggle hidden control commands outside explicit operator actions.
- Infer approval from ambiguous input.
- Act as the system of record for backend state progression independent of checkpoints.

### Authentication / Session subsystem must never
- Leave the gate open incorrectly on foreground return or session expiry.
- Treat stale auth as perpetual authorization.
- Silently bypass biometric/system prompts.

### Keychain subsystem must never
- Expose secret material to logs, transcripts, generated files, or provider prompts unless explicitly required and policy-permitted.
- Delegate long-term secret storage to Python.
- Permit deadlock-prone credential delivery paths to remain unbounded.

### IPC / XPC bridge must never
- Function as an arbitrary code execution channel.
- Accept unauthenticated local peers.
- Allow message schemas to drift from contract without failure visibility.

### Python Backend must never
- Own final authority over user authentication or secret custody.
- Execute generated code directly as part of agent reasoning.
- Mutate workflow state outside checkpointed orchestration rules.

### Consensus Engine must never
- Treat a single raw model response as final implementation without arbitration/review.
- Bypass retrieval when required by stage contracts.
- Hide provider disagreement or synthesis provenance.

### Provider Adapter Layer must never
- Leak provider-specific assumptions into calling subsystems.
- Persist credentials outside approved secret-handling paths.
- Suppress provider failures in ways that fabricate successful outputs.

### Planning Engine must never
- Change scope silently.
- Invent TRD ownership or architectural boundaries without presenting them for operator confirmation when required.
- Skip ordered dependency handling between PRDs/PRs.

### Review Pipeline must never
- Mark output acceptable without running its defined passes.
- Ignore operator exclusions or selected lenses.
- Override security policy for convenience.

### Document Store must never
- Serve stale or cross-project context as though it were current project truth.
- Treat retrieval relevance as policy authority.
- Hide re-embedding requirements when embedding models change.

### Git Workspace Manager must never
- Mix unrelated logical units into one PR when the plan requires isolation.
- Rewrite operator-reviewed history invisibly.
- Commit artifacts outside the repository working model.

### GitHub Integration must never
- Open merge-ready changes without draft/review posture when draft review is required.
- Publish without prior local review/validation.
- Blur attribution of generated changes.

### CI Orchestration must never
- Be treated as optional for gated PR readiness.
- Execute with hidden environment assumptions from user shell startup files.
- Be used to run unrestricted generated code outside defined test/build workflows.

### Checkpoint/Transcript Store must never
- Lose operator corrections while continuing execution.
- Permit resume from undefined internal state.
- Persist sensitive secrets in transcript/state payloads.

### Documentation Regeneration must never
- Replace implementation review with doc-only success criteria.
- Publish docs that are detached from validated implementation state.

### Security Policy Layer must never
- Be embedded only as guidance.
- Depend on implicit trust relationships.
- Become non-observable or non-reproducible in enforcement decisions.

---

## Key Data Flows

### 1. Secret flow
1. Operator initiates a protected action.
2. Shell requires local authentication.
3. Shell retrieves secret from Keychain.
4. Secret is delivered over controlled IPC only to the component requiring it.
5. Backend uses the credential for provider or GitHub access.
6. Secret is never checkpointed, transcripted, or persisted as backend-owned state.

**Invariant:** secret custody begins and ends with the shell/Keychain boundary.

---

### 2. Intent-to-plan flow
1. Operator supplies plain-language intent.
2. Planner combines intent with TRDs and repository context.
3. Planner generates PRD boundaries and ordered PR sequence.
4. UI presents proposed plan.
5. Operator approves or corrects using structured commands.
6. Build thread is created from approved plan.

**Invariant:** no autonomous code-generation work begins from unapproved planning state.

---

### 3. Retrieval-augmented generation flow
1. Current PR unit requests generation.
2. Document Store retrieves relevant TRD/repository/product context.
3. Consensus Engine calls provider adapters in parallel.
4. Candidate outputs are compared and arbitrated.
5. Selected output becomes proposed code/test diff.
6. Review pipeline consumes the same or related context for verification.

**Invariant:** generation and review are both grounded in shared contextual inputs.

---

### 4. Review-and-repair flow
1. Generated diff enters review.
2. Multi-pass review flags defects, spec divergence, or security concerns.
3. Operator exclusions and scope filters are applied.
4. Backend regenerates or repairs as needed.
5. Revised diff re-enters review.
6. On repeated failure mid-PR, retry starts from scratch per orchestration rule.

**Invariant:** failed review cannot directly advance to PR publication.

---

### 5. Validation-to-PR flow
1. Candidate branch is assembled in workspace.
2. Tests and CI workflows run.
3. Results are summarized to backend and surfaced to UI.
4. If passing, branch is committed with controlled message format.
5. Draft PR is opened on GitHub.
6. Checkpoint persists PR completion state.

**Invariant:** publication follows validation, not the reverse.

---

### 6. Resume/recovery flow
1. App or backend restarts.
2. Shell restores latest checkpoint metadata.
3. Backend reloads phase/PRD/PR/transcript state.
4. Recovery rule is applied:
   - mid-PR → retry current PR from scratch
   - between PRs → start next PR
   - PRD complete → start next PRD
5. UI reflects resumed state.

**Invariant:** recovery is deterministic and based on explicit checkpoint semantics.

---

### 7. Documentation regeneration flow
1. Build completes successfully.
2. Optional doc-regeneration task runs against final repository state.
3. Generated docs are reviewed/committed through normal repository workflow.
4. Updated docs are surfaced as part of completion or follow-up PR(s).

**Invariant:** documentation generation is downstream of code truth.

---

## Critical Invariants

### Trust and security invariants
- Trust is never inferred where explicit verification is possible.
- Secrets are shell-owned and Keychain-backed.
- The Python backend is not a root-of-trust component.
- Generated code is never executed directly by the agent as part of reasoning/orchestration.
- The platform must never auto-answer a gate.
- Identity, policy, telemetry, and enforcement remain separable but linked.
- Security controls apply to credentials, external content, generated code, and CI.

### Workflow invariants
- The system is not a chat assistant; it is a directed build pipeline.
- Work is decomposed into ordered PRDs, then ordered PRs.
- One PR corresponds to one logical unit of work.
- Pull requests are draft-first and human-reviewed.
- The next PR may be built while the operator reviews the last one, but progression still respects gating rules.

### State invariants
- Every major stage transition is checkpointed.
- Operator responses are durable.
- Resume behavior is deterministic.
- Mid-PR failures restart from scratch rather than attempting unsafe partial continuation.
- Exclusions, selected lenses, and scope corrections persist across retries/resumes.

### Context invariants
- Retrieval context is project-scoped.
- Embedding model changes require re-embedding.
- Context loading is deterministic and auditable.
- Review and generation both rely on controlled context assembly.
- Cross-project contamination of context is forbidden.

### Interface invariants
- Swift owns UI/auth/secret custody.
- Python owns planning/intelligence/review/git operations.
- Communication occurs only through authenticated local IPC with structured messages.
- Provider-specific details remain behind adapter boundaries.
- GitHub and CI operations happen only after internal review/validation sequence.

### Operational invariants
- Launch environments cannot depend on shell profile files such as `.zshrc` or `.bash_profile`.
- CI workflows are part of the controlled system surface, including Python tests, macOS unit tests, and XPC integration tests.
- Update/install mechanisms preserve code identity and platform trust expectations.
- All control decisions must be explainable, observable, and reproducible.

---

## Additional Architectural Notes

### Process model
Forge’s most important architectural property is its **strict process split**:

- **Trusted native shell**
  - Platform integration
  - human-presence verification
  - secret custody
  - user-visible orchestration

- **Constrained backend engine**
  - planning
  - retrieval
  - generation
  - review
  - repository automation

This split is not an implementation detail; it is the primary trust boundary.

### Storage model
Persistent data is divided by sensitivity and ownership:

- **Keychain**
  - credentials and secrets
- **Application Support / project-scoped cache**
  - retrieval indexes and document-store artifacts
- **Checkpoint/transcript state**
  - resumable orchestration metadata
- **Repository workspace**
  - generated source/test/workflow changes under review

### Failure model
Failures are expected and first-class:
- provider failures
- IPC interruptions
- auth timeout/failure
- review rejection
- CI failure
- restart/crash recovery
- scope correction from operator
- retrieval/index invalidation after embedding changes

The architecture handles these through explicit stage transitions, normalized errors, and checkpoint-based recovery rather than hidden mutable session state.

### Repository surface
The loaded source references indicate Forge may manage changes across:
- `src/**`
- `tests/**`
- `requirements.txt`
- `.github/workflows/forge-ci.yml`
- app/Xcode project surfaces such as:
  - `ForgeAgent/**`
  - `ForgeAgentTests/**`
  - `*.xcodeproj/**`

This reinforces that the platform spans both the native shell and Python backend codebases and must maintain clean boundaries while allowing coordinated repository evolution.

---

## Summary

Forge is a **spec-driven autonomous software delivery platform** with:

- a **native macOS shell** as trust anchor,
- a **Python backend** as constrained intelligence engine,
- a **retrieval-grounded consensus generation pipeline**,
- a **multi-pass review and CI gate**,
- and a **draft-PR-based human oversight model**.

Its architecture is defined by:
- explicit trust boundaries,
- deterministic orchestration,
- structured recovery,
- project-scoped retrieval,
- and strict separation between authentication/secret custody and autonomous code generation.

The platform succeeds only if these boundaries remain intact across every subsystem.