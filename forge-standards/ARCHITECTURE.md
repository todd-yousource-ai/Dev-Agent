# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and driving completion of the `ConsensusDevAgent` repository build across PRDs and PRs, while preserving resumable execution state across application restarts.

Its core responsibilities are:

- detect previously incomplete `ConsensusDevAgent` build threads at Forge startup
- present resumable thread choices to the operator without requiring a command such as `/resume`, `/continue`, or `/ledger resume`
- resume the selected thread through `director.resume()`
- persist local thread state for in-progress execution
- persist disaster-recovery build artifacts to GitHub on the PRDs branch
- reconstruct PR planning state from GitHub backups if local thread state is missing or stale
- continue PR pipeline execution from recovered state rather than regenerating completed planning work

Operationally, normal recovery is automatic at startup:

1. Operator launches `ForgeAgent.app`
2. Forge bootstraps
3. Incomplete build threads are detected automatically
4. Operator selects the numbered thread to resume
5. Resume proceeds via `director.resume()`

This subsystem therefore owns resumability and continuity of the `ConsensusDevAgent` build thread, not generic command-driven session restoration.

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- build-thread identity for `ConsensusDevAgent`
- local persisted thread state under the Forge workspace thread-state store
- startup-time detection of incomplete build threads
- operator-facing resume selection for incomplete builds
- transition into resumed execution
- PRD-to-PR-plan persistence for this build
- recovery of PR plans from GitHub-hosted JSON backups
- interpretation of thread progress fields such as:
  - `state`
  - `prd_count`
  - `pr_plans`
  - `pr_plans_by_prd`

### Out of Scope

This subsystem does **not** own:

- application bootstrap itself
- generic Forge shell command parsing
- ad hoc resume commands for normal restart
- direct GitHub API usage
- CI policy execution
- gate auto-resolution after backend restart
- undo semantics for operator gate decisions
- arbitrary branch lifecycle outside branches created for this build family

### External Operational Boundary

The subsystem assumes the existence of repository/agent operational controls documented elsewhere, including:

- branch hygiene for `forge-agent/build/consensusdevagent-*`
- preservation of:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files
- optional manual deletion of local thread state file when forcing a reset:
  - `.../state/threads/consensusdevagent.json`

## Data Flow

### 1. Startup Detection

On normal Forge startup, the system scans persisted thread state for incomplete builds. If an incomplete `ConsensusDevAgent` thread exists, it is surfaced in the startup UI with summary metadata such as:

- agent name
- PRD completion count
- PR completion count
- recency
- build description

No explicit resume command is required in the normal path.

### 2. Operator Selection

The operator chooses:

- a numbered incomplete thread to resume, or
- Enter for a fresh build

Selection of the existing `ConsensusDevAgent` thread transfers control to resume flow.

### 3. Local State Resume

Resume reads local thread state from the thread-state store, e.g.:

- `state/threads/consensusdevagent.json`

This state is the primary source of truth for in-progress execution when present and current.

Important state interpretation includes:

- `state` indicates pipeline stage
  - expected recovery-ready value when PR plans exist: `pr_pipeline`
- PR plan presence/count must align with expected PR count per PRD
- if PR plan structures are absent while execution should already have planned PRs, local state is considered stale or incomplete

### 4. GitHub Backup Persistence

After each PR plan is generated, the subsystem persists two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Roles:

- `.md`: human-readable planning table
- `.json`: machine-readable disaster-recovery backup

The JSON artifact is the authoritative recovery backup when local thread state is unavailable or predates PR plan generation.

### 5. Recovery Reconstruction

If local state has been lost or saved too early, resume logic reconstructs the full PR planning state by reading the PR-plan JSON files from the GitHub PRDs branch.

This recovery path is required in the failure mode where, after restart:

- thread reports `0 PRs done`
- execution re-enters PR generation from PR #1
- local JSON shows:
  - `"state": "prd_gen"`
  - empty `pr_plans_by_prd`

In that case, GitHub-backed PR-plan JSON files are used to rebuild the missing in-memory/local planning structures before resuming the pipeline.

## Key Invariants

### Restart and Resume

- Normal restart recovery is automatic at startup.
- No explicit resume command is required for normal operation.
- Incomplete `ConsensusDevAgent` threads must be discoverable from persisted state.
- Resume must be operator-selected; fresh start and resume are distinct actions.

### State Correctness

- If PR plans exist, local thread `state` should reflect pipeline progression, specifically `pr_pipeline`.
- PR plan counts in state must match expected PR counts per PRD.
- Local state must not silently override more complete GitHub-backed PR-plan data.
- Recovery must prefer reconstructing from GitHub PR-plan JSON over regenerating already planned work.

### GitHub Persistence

- Every generated PR plan produces both markdown and JSON artifacts in the PRDs branch.
- The JSON artifact is mandatory for disaster recovery.
- GitHub operations must go through `GitHubTool`; direct GitHub API use is forbidden.
- Any GitHub write must validate paths and must not be blind; writes require correct SHA-based safety semantics.

### Security and Execution Controls

The subsystem must obey repository-wide restrictions, including:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt
- no ignoring `SECURITY_REFUSAL`

### Retry and Gating Behavior

- retries are bounded: maximum 3 attempts total
- `_claude_json`: retry after 10s, then fall back to OpenAI
- `consensus.py`: retry with the other provider
- 403 primary rate limit: exponential backoff starting at 60s
- 429 secondary rate limit: respect `Retry-After` exactly
- polling endpoints use ETag caching
- gates never auto-resolve
- if backend restarts mid-gate, gate state is lost and operator must re-approve
- gate decisions have no undo path

## Failure Modes

### 1. Local Thread State Missing

**Symptom**
- thread state file is absent or manually wiped

**Effect**
- local resume context is unavailable

**Expected handling**
- discover incomplete build via other persisted metadata if available
- reconstruct PR planning state from GitHub PR-plan JSON files
- continue from recovered pipeline state rather than restarting planning blindly

### 2. Local Thread State Stale or Saved Too Early

**Symptom**
- restart shows `0 PRs done`
- agent starts regenerating PRs from the beginning
- local state contains `"state": "prd_gen"` and empty `pr_plans_by_prd`

**Effect**
- completed planning work is at risk of duplication

**Expected handling**
- inspect GitHub PRDs branch for `*-pr-plan.json`
- rebuild `pr_plans_by_prd` and related progress state from JSON backups
- transition execution back into `pr_pipeline`

### 3. Branch Accumulation / Monitor Confusion

**Symptom**
- many old `forge-agent/build/consensusdevagent-*` branches exist
- CI failures and branch monitor noise accumulate

**Effect**
- operational confusion and incorrect build monitoring

**Expected handling**
- delete old build branches in this family
- preserve `main`
- preserve `forge-agent/build/consensusdevagent/prds` if it contains JSON backups

### 4. Mid-Gate Backend Restart

**Symptom**
- backend restarts while awaiting operator approval

**Effect**
- gate state is lost

**Expected handling**
- do not auto-resolve or infer approval
- require explicit operator re-approval
- document no-undo semantics

### 5. Provider / API Failure

**Symptom**
- model/provider call fails or is rate-limited

**Effect**
- planning or resume operations may stall

**Expected handling**
- bounded retry only
- provider fallback per repository policy
- respect 403/429 handling requirements exactly
- if hard failure persists, emit error card, gate, and log full prompt context
- do not retry indefinitely
- do not rephrase around a refusal condition

### 6. Security Refusal or Forbidden Operation

**Symptom**
- requested action violates security checklist or forbidden patterns

**Effect**
- unsafe state mutation or execution risk

**Expected handling**
- stop immediately
- do not retry
- do not rephrase
- emit error card
- gate for explicit operator override where policy permits

## Dependencies

### Persistent State Storage

- local Forge thread-state storage
- thread file for this subsystem:
  - `state/threads/consensusdevagent.json`

Used for:
- incomplete-thread discovery
- resume metadata
- current pipeline stage
- PR plan progress tracking

### GitHub Storage

- PRDs branch for `ConsensusDevAgent`
- required recovery artifacts:
  - `prds/consensusdevagent/*.md`
  - `prds/consensusdevagent/*.json`

Used for:
- durable backup of PR plans
- disaster recovery reconstruction
- cross-restart continuity beyond local machine state

### GitHubTool

All GitHub operations for this subsystem must go through `GitHubTool`.

Constraints:
- never use the GitHub API directly
- validate paths before any write
- use safe write semantics
- honor repository write protections and retry policies

### Director Resume Path

- `director.resume()` is the control transfer used after operator selection of an incomplete thread

This is the execution boundary between startup detection/UI and resumed build orchestration.

### Consensus / Model Infrastructure

The subsystem depends on the repository’s consensus/model execution layer for generation and recovery-related reasoning, subject to:

- provider fallback behavior
- bounded retries
- refusal handling
- logging and gating rules

### Repository Operational Policy

ConsensusDevAgent is constrained by repository-wide architecture guidance including:

- critical file review before modification
- GitHub operations discipline
- error handling patterns
- CI routing expectations
- version management
- security checklist enforcement