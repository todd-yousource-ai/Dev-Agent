# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge build-thread subsystem responsible for executing and recovering a long-running repository build plan for the `ConsensusDevAgent` target. It manages durable thread state, detects incomplete work on startup, reconstructs execution state when necessary, and resumes the PR pipeline without requiring an explicit recovery command.

Its primary responsibilities are:

- Track progress of a multi-PRD, multi-PR build thread.
- Persist local execution state for restart safety.
- Persist generated PR-plan artifacts to GitHub as disaster-recovery backups.
- Detect incomplete builds automatically during Forge startup.
- Offer operator-driven selection of an incomplete thread to resume.
- Reconstruct PR pipeline state from GitHub-backed JSON artifacts if local state is missing or stale.
- Prevent stale branch accumulation from interfering with branch/CI monitoring.

Normal recovery is automatic at application startup. There is no explicit `/resume`, `/continue`, or `/ledger resume` command in the normal restart path. The operator launches Forge, waits for bootstrap, and, if an incomplete thread is detected, selects it from the startup prompt. Resume then proceeds via the director resume flow.

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- The build thread identity for `ConsensusDevAgent`.
- Local thread-state persistence under the Forge workspace state directory.
- Detection of incomplete thread state at startup.
- Resume handoff into the director/orchestrator.
- PR plan persistence artifacts for this agent under the GitHub `prds` branch.
- Reconstruction of PR plans from previously written JSON backups.
- Operational expectations for branch hygiene specific to `forge-agent/build/consensusdevagent-*`.

### Out of Scope

ConsensusDevAgent does not own:

- Application bootstrap itself.
- Global startup UX outside incomplete-thread discovery/prompting.
- GitHub transport implementation.
- CI execution or CI policy.
- Gate approval persistence across backend restarts.
- Undo semantics for operator gate decisions.
- Direct use of the GitHub API.

All GitHub operations must go through `GitHubTool`; this subsystem must not bypass that abstraction.

### External Interfaces

#### Startup/Resume Interface

On normal startup, Forge scans for incomplete thread state and presents resumable builds. Example semantics:

- Detect incomplete `ConsensusDevAgent` thread.
- Display progress summary such as PRD count and PR count completed.
- Prompt operator to select a thread number or press Enter for a fresh start.
- On selection, call into the director resume path.

#### Local State Interface

Local durable state is stored as a thread JSON file, e.g.:

- `.../state/threads/consensusdevagent.json`

This file is the primary local checkpoint for execution state.

#### GitHub Backup Interface

After each PR plan is generated, the subsystem writes two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The JSON file is the authoritative disaster-recovery backup for PR-plan reconstruction if local state is lost.

## Data Flow

### 1. Build Execution

During normal execution, the subsystem advances through PRD and PR planning stages and updates thread state locally. As PR plans are generated, it emits:

- Human-readable PR plan markdown.
- Machine-readable PR plan JSON.

The local state file tracks high-level progress fields such as:

- `state`
- `prd_count`
- `pr_plans` / `pr_plans_by_prd`

### 2. Local Checkpointing

The thread state file under `state/threads/consensusdevagent.json` is updated as the pipeline advances. This file is used first for startup recovery and incomplete-thread detection.

Expected operational interpretation:

- If PR plans exist, `state` should have progressed to `pr_pipeline`.
- PR plan count should match the expected number of PRs per PRD.

### 3. GitHub Backup Persistence

After each PR plan generation, backup artifacts are written to the PRDs branch. The JSON version is the recovery source of truth when local state is unavailable or was captured before PR-plan generation completed.

This establishes a two-tier recovery model:

1. Local thread JSON for fast restart.
2. GitHub PR-plan JSON artifacts for disaster recovery/reconstruction.

### 4. Automatic Startup Recovery

On Forge startup:

1. Application bootstraps.
2. Incomplete thread state is discovered automatically.
3. `ConsensusDevAgent` appears in the resumable-thread list if unfinished.
4. Operator selects the thread.
5. Director resume is invoked.

No explicit recovery command is required in the normal path.

### 5. Reconstruction Path

If local state is missing, stale, or inconsistent, the subsystem must reconstruct PR pipeline state from GitHub PR-plan JSON files in the PRDs branch.

This is specifically required when local state shows a pre-plan state such as:

- `state: "prd_gen"`
- `pr_plans_by_prd: {}`

while GitHub already contains generated PR-plan JSON artifacts.

In that case, GitHub-backed JSON is used to rebuild the full plan so the agent does not regenerate PRs from scratch.

## Key Invariants

### Recovery Invariants

- Normal restart recovery is automatic at startup.
- No explicit resume command is required for standard recovery.
- An incomplete `ConsensusDevAgent` thread must be discoverable from persisted state.
- Resume must be operator-selected from the startup prompt; it is not silently auto-entered.

### State Invariants

- Local thread state is the primary checkpoint for active execution.
- GitHub PR-plan JSON is the disaster-recovery backup.
- If PR plans exist, thread state should reflect pipeline advancement beyond raw PRD generation.
- Reconstruction must prefer existing persisted PR-plan artifacts over regenerating plans.

### Persistence Invariants

- For every generated PR plan, both `.md` and `.json` artifacts are written.
- The `.json` artifact is sufficient to reconstruct machine-readable PR-plan state.
- GitHub writes must go through `GitHubTool`.
- Any write path must be validated before writing.
- Blind GitHub writes without SHA are forbidden.

### Operational Invariants

- Old branches matching `forge-agent/build/consensusdevagent-*` should be deleted to avoid accumulated CI failures and branch-monitor confusion.
- `main` must be preserved.
- `forge-agent/build/consensusdevagent/prds` should be preserved if it contains JSON files, because those files may be required for recovery.
- Local thread-state wipe is a destructive operator action and removes the primary local checkpoint.

### Safety and Platform Invariants

The subsystem must comply with repository-wide operational rules:

- Never use the GitHub API directly.
- Never retry indefinitely; maximum 3 attempts total.
- 403 primary-rate-limit handling uses exponential backoff starting at 60s.
- 429 secondary-rate-limit handling must respect `Retry-After` exactly.
- ETag caching is required on polling endpoints.
- Gates never auto-resolve; they wait for explicit operator action.
- If the backend restarts mid-gate, gate state is lost and must be re-approved by the operator.
- There is no undo on gate decisions.
- On hard-stop/refusal conditions: stop, do not retry, do not rephrase, emit an error card, gate, and log full prompt context.
- Forbidden patterns include shell injection, credentials in logs or prompts, direct execution of generated code, path traversal, blind GitHub write, placing context in the system prompt, and ignoring `SECURITY_REFUSAL`.

## Failure Modes

### 1. Local State Missing

**Symptom**
- No local `consensusdevagent.json` exists.

**Impact**
- Fast local resume is unavailable.

**Expected behavior**
- Recover from GitHub PR-plan JSON artifacts if they exist.
- If neither local state nor GitHub recovery artifacts exist, the thread cannot be resumed and must be restarted fresh.

### 2. Local State Stale or Saved Too Early

**Symptom**
- On restart, agent shows `0 PRs done` and begins regenerating from PR #1.
- State file shows `state: "prd_gen"` and empty `pr_plans_by_prd`, despite prior PR-plan generation.

**Impact**
- Duplicate regeneration of existing plans.
- Potential divergence between intended and regenerated state.

**Expected behavior**
- Detect inconsistency.
- Inspect GitHub PRDs branch for existing `.json` plan files.
- Reconstruct plan state from GitHub JSON rather than regenerating.

### 3. GitHub Backup Missing

**Symptom**
- Local state lost and no PR-plan JSON files exist in the PRDs branch.

**Impact**
- Disaster recovery path is unavailable.

**Expected behavior**
- Thread cannot be faithfully reconstructed.
- Operator must restart planning/build flow.

### 4. Stale Branch Accumulation

**Symptom**
- Many old `forge-agent/build/consensusdevagent-*` branches remain.

**Impact**
- CI failures accumulate.
- Branch monitor becomes noisy or confused.
- Operational visibility degrades.

**Expected behavior**
- Delete stale build branches.
- Preserve `main`.
- Preserve `forge-agent/build/consensusdevagent/prds` when it contains JSON recovery artifacts.

### 5. Backend Restart During Gate

**Symptom**
- Process restarts while awaiting approval.

**Impact**
- In-memory gate state is lost.

**Expected behavior**
- Gate does not auto-resolve on restart.
- Operator must explicitly re-approve.
- No implicit replay or undo occurs.

### 6. GitHub Write/Read Throttling

**Symptom**
- 403 or 429 responses from GitHub-backed operations.

**Impact**
- Delayed persistence, polling, or reconstruction.

**Expected behavior**
- Apply bounded retry policy.
- Respect 403 and 429 handling rules exactly.
- Do not retry indefinitely.

### 7. Unsafe Write Target

**Symptom**
- Write path is invalid or could traverse outside intended location.

**Impact**
- Potential corruption or security boundary violation.

**Expected behavior**
- Validate path before any write.
- Refuse unsafe operations.

## Dependencies

### Runtime Dependencies

- Forge application startup/bootstrap flow.
- Director/orchestrator resume entrypoint.
- Local filesystem for thread-state persistence.
- GitHubTool for all GitHub reads/writes.
- PRDs branch content for durable backup artifacts.

### Data Dependencies

- Local thread file:
  - `state/threads/consensusdevagent.json`
- GitHub recovery artifacts:
  - `prds/consensusdevagent/*.md`
  - `prds/consensusdevagent/*.json`

### Operational Dependencies

- Branch hygiene procedures for `forge-agent/build/consensusdevagent-*`.
- Operator participation in startup resume selection.
- Operator participation in gate re-approval after restart.
- Repository-wide safety, retry, GitHub, and security rules documented in AGENTS and related core docs.

### Documentation Dependencies

This subsystem behavior is defined in the TRD operational and recovery requirements for:

- Normal automatic restart recovery.
- State inspection and interpretation.
- GitHub-backed PR-plan persistence.
- Recovery from stale local state.
- Build-branch cleanup policy.