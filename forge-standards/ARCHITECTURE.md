# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning, tracking, and resuming generation of the `ConsensusDevAgent` workstream across PRDs and PRs.

Its primary responsibilities are:

- maintain per-thread build state for the `ConsensusDevAgent` thread
- detect incomplete work automatically on agent startup
- offer restart-time recovery without requiring a resume command
- persist generated PR-plan artifacts to both local thread state and GitHub-backed recovery files
- reconstruct execution state from GitHub PR-plan JSON artifacts if local state is missing or stale
- support operator-directed continuation of an incomplete build thread via startup selection

Normal recovery is automatic at startup. The operator does **not** issue `/resume`, `/continue`, or `/ledger resume` for standard restarts. Instead, on boot, ForgeAgent scans thread state, detects incomplete builds, and presents resumable threads. Selecting the `ConsensusDevAgent` entry invokes `director.resume()` for that thread.

This subsystem is therefore a **restart-safe execution state manager** for the `ConsensusDevAgent` build pipeline, with GitHub-backed disaster recovery for PR-plan state.

## Component Boundaries

### In Scope

This subsystem owns:

- thread-local persisted state for the `ConsensusDevAgent` build
- startup-time detection of incomplete `ConsensusDevAgent` build threads
- resume selection UX integration at startup
- mapping persisted thread state into the runtime pipeline state
- storage of PR plan progress indicators such as:
  - thread `state`
  - `prd_count`
  - `pr_plans`
  - `pr_plans_by_prd`
- reconstruction of PR plans from GitHub PRD-plan JSON backups
- operational cleanup expectations for stale `forge-agent/build/consensusdevagent-*` branches
- preservation of the PRDs branch when it contains recovery JSON files

### Out of Scope

This subsystem does **not** own:

- the general ForgeAgent bootstrap process
- the implementation of `director.resume()` itself
- PR generation semantics beyond the state required to resume them
- CI execution or branch monitoring logic
- manual operator gate persistence across backend restarts
- direct GitHub API access outside approved tool boundaries

### External Boundary Rules

The subsystem operates within repository-wide agent constraints:

- all GitHub operations must go through `GitHubTool`
- never use the GitHub API directly
- validate paths before any write
- never perform blind GitHub writes without SHA protection
- never retry indefinitely; max 3 attempts total
- gates never auto-resolve
- if backend restarts mid-gate, gate state is lost and requires operator re-approval
- no undo exists for gate decisions

These are not optional behaviors; they constrain how recovery state may be persisted, restored, and advanced.

## Data Flow

### 1. Normal Startup Detection

On application launch:

1. operator starts `ForgeAgent.app`
2. bootstrap completes in approximately 45 seconds
3. startup scans for incomplete build threads
4. if `ConsensusDevAgent` thread state is incomplete, the operator is shown a resumable entry such as:
   - thread name
   - PRD progress, e.g. `2/26 PRDs`
   - completed PR count, e.g. `14 PRs done`
   - recency, e.g. `(0h ago)`
5. operator selects the thread by numeric index
6. runtime calls `director.resume()`

No explicit resume command is part of the normal path.

### 2. Local State Persistence

The canonical local thread state is stored as a thread JSON file, operationally exemplified by:

`/Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

This file carries enough information to identify:

- current pipeline phase via `"state"`
- PRD progress via `"prd_count"`
- generated PR plans via `pr_plans` and/or `pr_plans_by_prd`

Operationally, a healthy resumed PR-planning thread should show:

- `"state": "pr_pipeline"` when PR plans already exist
- PR plan counts matching expected PR count per PRD

### 3. GitHub Recovery Persistence

After each PR plan is generated, the subsystem writes two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The markdown file is human-readable.
The JSON file is the machine-readable disaster recovery source of truth for PR-plan reconstruction.

This means recovery durability is split across:

- **local thread state** for fast resume
- **GitHub PR-plan JSON files** for disaster recovery

### 4. Resume Reconstruction

If local state is present and internally consistent, the subsystem resumes directly from the thread JSON.

If local state is missing, wiped, or stale, the subsystem reconstructs from GitHub PR-plan JSON artifacts in the PRDs branch. This is specifically intended to recover from cases where local thread state was lost or saved before PR plans were recorded.

### 5. Operator Maintenance Paths

Operational runbook actions affecting this subsystem include:

- deleting stale build branches matching `forge-agent/build/consensusdevagent-*`
- preserving:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery files
- manually inspecting thread state JSON
- wiping local thread state when required

The subsystem depends on the PRDs branch backup artifacts surviving cleanup when they contain recovery JSON.

## Key Invariants

1. **Normal restart requires no explicit resume command.**  
   Recovery is startup-driven and selection-driven, not command-driven.

2. **Incomplete `ConsensusDevAgent` work must be discoverable at startup.**  
   If a thread is incomplete, it must appear in the startup resume list.

3. **Local thread state must encode phase accurately.**  
   In particular:
   - if PR plans exist, thread `"state"` must not remain at an earlier phase such as `"prd_gen"`
   - resume behavior depends on this phase marker being correct

4. **Each generated PR plan must produce GitHub recovery artifacts.**  
   For every generated PR plan, both markdown and JSON artifacts must be written to the PRDs branch.

5. **GitHub PR-plan JSON is the disaster recovery backup.**  
   Loss of local thread state must not imply loss of PR-plan reconstruction capability, provided the JSON artifacts exist.

6. **The PRDs recovery branch must not be deleted if it contains JSON files.**  
   Branch cleanup may remove stale build branches, but the recovery-bearing PRDs branch is retained.

7. **GitHub writes must respect repository safety rules.**  
   This includes:
   - use `GitHubTool` only
   - path validation before writes
   - SHA-aware writes
   - no direct GitHub API usage

8. **Retries are bounded.**  
   Recovery persistence and polling behavior may retry, but never indefinitely; maximum 3 attempts total.

9. **Gate state is not durable across backend restart.**  
   This subsystem may resume build-thread state, but it must not assume gate approvals survive restart.

10. **Branch-monitor noise from stale build branches is an operational hazard.**  
    Cleanup of old `forge-agent/build/consensusdevagent-*` branches is part of maintaining correct subsystem behavior.

## Failure Modes

### Stale or Incomplete Local State

Symptom:
- after restart, the system reports `0 PRs done`
- PR generation restarts from PR #1

Likely cause:
- local thread state was saved before PR plans were generated
- `"state"` remains `"prd_gen"`
- `pr_plans_by_prd` is empty `{}`

Effect:
- resume logic believes PR planning has not yet occurred

Expected recovery path:
- inspect GitHub PRDs branch for `*-pr-plan.json` files
- reconstruct PR-plan state from those JSON artifacts

### Local Thread State Deleted

Symptom:
- no usable local `consensusdevagent.json`

Effect:
- local fast-resume state is unavailable

Expected recovery path:
- rebuild state from GitHub PR-plan JSON files in the PRDs branch

### Recovery Branch Accidentally Deleted

Symptom:
- local state is missing and GitHub PR-plan JSON artifacts are absent

Effect:
- disaster recovery source is lost
- full PR-plan reconstruction may be impossible

Operational prevention:
- keep `forge-agent/build/consensusdevagent/prds` if it contains JSON files

### Stale Build Branch Accumulation

Symptom:
- CI failures accumulate on old branches
- branch monitor becomes noisy or confused

Effect:
- operational signal degradation
- increased likelihood of incorrect branch interpretation during active builds

Operational mitigation:
- delete all branches matching `forge-agent/build/consensusdevagent-*`
- except preserve the PRDs branch if it contains recovery JSON

### Backend Restart During Gate

Symptom:
- backend restarts while awaiting operator approval

Effect:
- gate state is lost
- approval does not auto-resume

Constraint:
- operator must explicitly re-approve
- subsystem must not auto-resolve or infer prior approval state

### GitHub Rate Limit or Access Errors

Relevant repository-wide handling constraints:

- `403` primary rate limiting: exponential backoff starting at 60s
- `429` secondary rate limiting: respect `Retry-After` exactly
- ETag caching on polling endpoints
- retry after failover patterns are bounded to 3 attempts total

Effect on this subsystem:
- delayed or failed persistence of recovery artifacts
- delayed recovery-state polling or branch inspection

### Safety Rule Violations

Forbidden behaviors that would compromise this subsystem include:

- direct GitHub API usage
- blind GitHub writes without SHA
- path traversal
- shell injection
- logging or prompting credentials
- direct execution of generated code
- ignoring `SECURITY_REFUSAL`

These are architecture-level violations, not just implementation bugs.

## Dependencies

### Runtime Dependencies

- ForgeAgent application bootstrap and startup prompt flow
- thread-state storage under the workspace state directory
- `director.resume()` for runtime continuation after thread selection

### Persistence Dependencies

- local JSON thread state file for `ConsensusDevAgent`
- GitHub PRDs branch as off-host recovery storage
- PR-plan markdown and JSON artifact generation

### Platform/Tooling Dependencies

- `GitHubTool` for all GitHub operations
- path validation before any file write
- SHA-aware write semantics for GitHub content updates
- branch management tooling for cleanup of stale build branches

### Cross-Cutting Repository Policies

This subsystem is constrained by repository-wide operational and safety policies, including:

- bounded retries only
- provider failover behavior in consensus/error paths
- no automatic gate resolution
- explicit operator override on hard-stop error cards
- security checklist compliance before every PR

### Critical Operational Files and Artifacts

- local thread state:
  - `state/threads/consensusdevagent.json`
- GitHub recovery artifacts:
  - `prds/consensusdevagent/prd-###-pr-plan.md`
  - `prds/consensusdevagent/prd-###-pr-plan.json`

Together, these files define the resumability contract for the `ConsensusDevAgent` subsystem.