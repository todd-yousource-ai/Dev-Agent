# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and executing the end-to-end build of the `ConsensusDevAgent` deliverable across multiple PRDs and PRs.

Its primary responsibilities are:

- maintain per-thread execution state for the `ConsensusDevAgent` build
- detect and resume incomplete work automatically on application startup
- persist recoverable planning artifacts locally and to GitHub
- reconstruct lost local planning state from GitHub-backed PR plan JSON artifacts
- manage progression from PRD generation into PR pipeline execution
- present resumable build threads to the operator at startup

This subsystem is explicitly designed for **automatic recovery on normal restart**. No operator command such as `/resume`, `/continue`, or `/ledger resume` is required to make recovery possible. On boot, the system discovers incomplete build threads and offers them for selection. Selecting the thread invokes resume behavior.

Operationally, a normal restart flow is:

1. operator launches `ForgeAgent.app`
2. bootstrap completes
3. incomplete build threads are detected automatically
4. operator selects `ConsensusDevAgent`
5. `director.resume()` continues execution from saved state

The subsystem also supports disaster recovery when local thread state is missing or stale by using machine-readable PR plan JSON files stored in the GitHub PRDs branch.

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- thread-local persisted state for the `ConsensusDevAgent` build
- startup-time detection of incomplete `ConsensusDevAgent` build threads
- resume eligibility and resume handoff into director orchestration
- PRD-to-PR planning state tracking
- reconstruction of `pr_plans` from GitHub-backed JSON artifacts
- representation of build progress such as:
  - PRD count completed
  - PR count planned or completed
  - current state marker such as `prd_gen` or `pr_pipeline`

### Out of Scope

ConsensusDevAgent does **not** own:

- app bootstrap itself
- the top-level startup prompt renderer
- direct GitHub API access
- CI execution or CI monitoring policy
- gate approval persistence across backend restarts
- branch lifecycle outside the branch conventions used by this build
- direct execution of generated code
- recovery semantics for unrelated subsystems

### External Operational Boundary

The subsystem depends on operator-driven selection at startup. Recovery discovery is automatic, but continuation is not silent: the operator chooses a listed incomplete thread or starts fresh.

If local thread state becomes corrupted or undesirable, operational recovery may include:

- deleting old build branches matching `forge-agent/build/consensusdevagent-*`
- preserving `main`
- preserving `forge-agent/build/consensusdevagent/prds` if it contains JSON files
- deleting the local thread state file:
  - `.../state/threads/consensusdevagent.json`

Those actions are operational controls, not subsystem-internal behavior.

## Data Flow

### 1. Startup Discovery

On normal startup:

- ForgeAgent bootstraps
- subsystem scans persisted thread state for incomplete builds
- if `consensusdevagent.json` exists and represents unfinished work, the build appears in the resume list
- operator selects the thread
- control passes to `director.resume()`

### 2. Local State Persistence

The canonical local thread state for this subsystem is stored in:

- `state/threads/consensusdevagent.json`

This file contains key fields used to determine resumability and progress, including:

- `state`
- `prd_count`
- `pr_plans` or `pr_plans_by_prd`

State inspection guidance indicates:

- `state` should be `pr_pipeline` if PR plans already exist
- the number of planned PRs should match expected PR count per PRD

### 3. GitHub Recovery Persistence

After each PR plan is generated, the subsystem writes two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Roles of these artifacts:

- `.md`: human-readable summary/table
- `.json`: machine-readable disaster recovery source of truth for PR plan reconstruction

If local state is lost, the subsystem is expected to read the JSON files on resume and reconstruct the full plan.

### 4. Resume Decision Logic

Resume behavior depends on the saved state:

- if local thread state indicates PR planning has been completed, resume should continue in PR pipeline execution
- if local state is stale and shows `prd_gen` with empty `pr_plans_by_prd`, the system must not treat that local absence as authoritative if GitHub PR plan JSON files exist
- GitHub-backed PR plan JSON is the recovery source for reconstructing missing plan state

### 5. Failure/Repair Path

A known failure mode is repeated PR regeneration on every restart:

- symptom: startup shows `0 PRs done`, then planning restarts from PR #1
- diagnosis: local state is stuck in `prd_gen` and `pr_plans_by_prd` is empty
- repair path:
  - inspect local thread state
  - verify whether PR plan JSON exists in the GitHub PRDs branch
  - reconstruct from JSON-backed plans rather than regenerating

## Key Invariants

1. **Normal restart recovery requires no resume command**
   - Recovery discovery is automatic at startup.
   - No `/resume`, `/continue`, or `/ledger resume` is required for normal restart handling.

2. **Incomplete builds must be discoverable at startup**
   - If `ConsensusDevAgent` has unfinished work and persisted state exists, it must be surfaced in the incomplete-thread list.

3. **Local thread state is resumable state, not the only recovery source**
   - `state/threads/consensusdevagent.json` is the primary local state file.
   - Its absence or staleness must not imply total loss if GitHub PR plan JSON artifacts exist.

4. **PR plan JSON in GitHub is the disaster recovery backup**
   - For every generated PR plan, a machine-readable JSON artifact must exist in the PRDs branch.
   - These files are sufficient to reconstruct planning state after local loss.

5. **State and plan data must agree**
   - If PR plans exist, thread state should reflect progression into `pr_pipeline`.
   - A state marker of `prd_gen` with empty `pr_plans_by_prd` is inconsistent with already-generated PR plans and indicates stale or incomplete persistence.

6. **Old build branches are disposable; PRDs backup branch may be authoritative**
   - Branches matching `forge-agent/build/consensusdevagent-*` should be considered safe to prune operationally.
   - `forge-agent/build/consensusdevagent/prds` must be preserved if it contains JSON recovery artifacts.

7. **GitHub operations must go through GitHubTool**
   - This subsystem must not use the GitHub API directly.
   - All repository reads/writes for persisted recovery artifacts must flow through the platform GitHub abstraction.

8. **Blind writes are forbidden**
   - Any GitHub write must validate target paths and use SHA-aware update semantics.
   - Blind GitHub writes are explicitly forbidden.

9. **No unsafe execution paths**
   - Generated code must never be directly executed by this subsystem.
   - Shell injection, path traversal, and credential leakage in logs or prompts are forbidden.

## Failure Modes

### Stale Local State Causes PR Regeneration

**Symptom**
- restart shows no PR progress
- execution begins regenerating PR plans from the beginning

**Likely condition**
- local thread JSON shows:
  - `state: "prd_gen"`
  - empty `pr_plans_by_prd`

**Impact**
- duplicate planning work
- inconsistent progress display
- possible branch/CI noise

**Expected handling**
- inspect GitHub PRDs branch for `*-pr-plan.json`
- rebuild in-memory/local plan state from JSON artifacts
- continue from reconstructed PR pipeline state

### Local Thread State Deleted or Lost

**Symptom**
- no local resumable state file

**Impact**
- startup may fail to identify local progress from disk alone

**Expected handling**
- recover from GitHub PR plan JSON artifacts if they exist
- reconstruct the full plan on resume

### Recovery Artifacts Missing from GitHub

**Symptom**
- local thread state lost and no JSON files present in PRDs branch

**Impact**
- planning state cannot be reconstructed from backup artifacts

**Expected handling**
- operator may need to start fresh
- preserve failure transparency rather than silently inventing state

### Branch Accumulation Interferes with Monitoring

**Symptom**
- old branches create CI failures or confuse branch monitoring

**Impact**
- operational noise
- misleading build status

**Expected handling**
- delete stale branches matching `forge-agent/build/consensusdevagent-*`
- preserve `main`
- preserve `forge-agent/build/consensusdevagent/prds` when it contains JSON recovery files

### Backend Restart During Gate

Platform-wide gate behavior affects this subsystem:

- gates never auto-resolve
- if backend restarts mid-gate, gate state is lost
- operator must re-approve
- there is no undo on gate decisions

ConsensusDevAgent must therefore not assume gate continuity across restarts, even if thread build state is otherwise recoverable.

### Provider/Backend Failures During Generation

Applicable platform error-handling constraints include:

- `_claude_json`: retry after 10 seconds, then fall back to OpenAI
- `consensus.py`: retry with the other provider
- never retry indefinitely
- maximum 3 attempts total
- `403` primary rate/permission failures: exponential backoff starting at 60 seconds
- `429` secondary throttling: respect `Retry-After` exactly
- polling endpoints must use ETag caching

These policies constrain how ConsensusDevAgent performs generation or polling through shared platform services.

## Dependencies

ConsensusDevAgent depends on the following platform capabilities and policies:

### Director / Resume Orchestration

- startup discovery hands off to `director.resume()`
- director is responsible for resuming execution once the operator selects the thread

### Local Thread State Store

- persisted JSON thread state under `state/threads/consensusdevagent.json`
- required for fast local resume and startup display

### GitHubTool

- all GitHub operations must go through `GitHubTool`
- never use the GitHub API directly
- path validation is required before any write
- blind writes without SHA are forbidden

### GitHub PRDs Branch

- stores durable PR plan recovery artifacts
- especially the machine-readable `*-pr-plan.json` files used for disaster recovery

### Consensus / Model Invocation Layer

Subject to shared policies:

- provider retry/fallback behavior
- max-attempt limits
- refusal handling
- logging and operator gate behavior on hard failures

### Security and Repository Controls

This subsystem is constrained by repository-wide forbidden patterns:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt
- no ignoring `SECURITY_REFUSAL`

### CI / Branch Hygiene Policies

ConsensusDevAgent relies on branch hygiene to keep operational state understandable:

- old `forge-agent/build/consensusdevagent-*` branches should be pruned
- PRDs branch containing recovery JSON must be preserved when present

