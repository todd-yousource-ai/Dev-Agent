# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the multi-PRD / multi-PR workflow for the `ConsensusDevAgent` build target.

Its core responsibilities are:

- maintain thread-local progress for an in-flight build
- detect incomplete work on startup and offer resume automatically
- persist planning artifacts so work can be reconstructed after local state loss
- drive continuation from prior state via `director.resume()`
- prevent accidental duplicate fresh starts when resumable work exists

Normal recovery is automatic. No explicit `/resume`, `/continue`, or `/ledger resume` command is required for standard restarts. On application startup, after bootstrap, the subsystem scans persisted thread state for incomplete build threads and presents a resume selector to the operator. Selecting the thread resumes execution from saved state.

This subsystem specifically supports recovery of PR planning and PR execution progress for the `ConsensusDevAgent` thread. It also relies on GitHub-hosted PRD plan JSON as a disaster-recovery source of truth when local thread state is missing or stale.

## Component Boundaries

### In Scope

- detection of incomplete `ConsensusDevAgent` build threads at startup
- presentation of resumable thread metadata to the operator
- resumption of the selected thread via `director.resume()`
- persistence of local thread state under the thread-state store
- reconstruction of PR plan state from GitHub `prds` branch JSON files when local state is lost
- interpretation of thread progress fields such as:
  - thread `state`
  - PRD count
  - PR plan inventory / completed PR count
- operational compatibility with branch hygiene rules for `forge-agent/build/consensusdevagent-*`

### Out of Scope

- application bootstrap itself
- general-purpose command parsing for manual resume commands
- direct GitHub API usage outside the platform GitHubTool boundary
- CI execution semantics
- approval gate persistence across backend restarts
- undo/rollback of gate decisions
- arbitrary branch recovery outside the documented ConsensusDevAgent branch namespace

### External Interfaces

- **Startup / bootstrap flow**
  - detects incomplete threads after app launch
- **Director**
  - resumes selected work through `director.resume()`
- **Local thread state store**
  - canonical runtime checkpoint for in-progress work
- **GitHub `prds` branch**
  - disaster-recovery source for generated PR plan JSON/Markdown
- **GitHubTool**
  - all GitHub operations must route through this tool; direct GitHub API access is forbidden

## Data Flow

### 1. Startup Detection

On normal startup:

1. operator launches `ForgeAgent.app`
2. agent bootstraps
3. subsystem scans persisted thread state for incomplete build threads
4. if an incomplete `ConsensusDevAgent` thread exists, UI presents resumable thread metadata:
   - agent name
   - PRD progress
   - completed PR count
   - recency
   - thread summary
5. operator selects the thread number to resume, or presses Enter for a fresh start

This is the primary recovery entrypoint. No command-based resume is required for standard restarts.

### 2. Resume Execution

After the operator selects the thread:

1. thread state is loaded from local persisted state
2. `director.resume()` is invoked
3. execution continues from the saved thread `state`

Expected state inspection fields include:

- `"state"`
- `"prd_count"`
- `"pr_plans"` / `pr_plans_by_prd`

Operationally, a valid resumed planning pipeline should show `state = "pr_pipeline"` when PR plans already exist.

### 3. Local State Persistence

The subsystem stores thread-local state in a JSON file for the `ConsensusDevAgent` thread. This file is the primary fast-recovery checkpoint used on restart.

Operationally relevant behavior:

- the thread-state JSON is consulted during startup detection
- it is used to determine whether the thread is incomplete
- it is used to determine whether PR planning already occurred
- it can be manually removed to wipe local thread state

Wiping this file is a destructive local reset and forces the subsystem to rely on remote recovery artifacts if resume is later attempted.

### 4. GitHub-Backed Recovery

After each PR plan is generated, two artifacts are written to the GitHub `prds` branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The Markdown file is human-readable. The JSON file is the machine-readable disaster-recovery backup.

If local thread state is missing or was saved before PR plans were materialized, the subsystem reconstructs the plan from these JSON files on resume. This is the recovery path for cases where local state shows planning as absent even though planning artifacts were already generated.

### 5. Branch Hygiene Interaction

Operational runbook constraints define branch cleanup rules:

- delete branches matching `forge-agent/build/consensusdevagent-*`
- keep:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files

This boundary matters because the `prds` branch may contain the only surviving machine-readable recovery artifacts needed to reconstruct PR plans after local thread-state loss.

## Key Invariants

### Automatic Resume Discovery

- normal restart recovery must be discoverable automatically at startup
- no manual resume command is required for standard restart scenarios
- incomplete `ConsensusDevAgent` work must surface as a resumable thread option

### Single Source of Runtime Continuation

- local thread state is the primary runtime checkpoint for resuming execution
- `director.resume()` is the continuation mechanism after thread selection

### Remote Recovery Durability

- every generated PR plan must produce a machine-readable JSON artifact in the `prds` branch
- these JSON files are the disaster-recovery backup for PR planning state
- loss of local thread state must not imply loss of PR plan structure if GitHub JSON exists

### State / Plan Consistency

- if PR plans exist, thread state should reflect a post-planning phase such as `pr_pipeline`
- if thread state remains at `prd_gen` and `pr_plans_by_prd` is empty, local state is inconsistent with actual generated work and must be repaired from GitHub artifacts

### Branch Retention Safety

- the `forge-agent/build/consensusdevagent/prds` branch must be preserved when it contains JSON plan files
- old build branches may be deleted
- deletion of the `prds` branch with valid JSON artifacts destroys the documented recovery source

### GitHub Access Discipline

- all GitHub operations must go through GitHubTool
- direct GitHub API access is forbidden
- writes must validate paths before any write
- blind writes without SHA are forbidden

### Safety / Reliability Constraints

- never retry indefinitely; max 3 attempts total
- `403` primary-rate-limit handling uses exponential backoff starting at 60s
- `429` secondary-rate-limit handling must respect `Retry-After` exactly
- polling endpoints use ETag caching
- gates never auto-resolve; they wait
- if backend restarts mid-gate, gate state is lost and operator re-approval is required
- no undo on gate decisions

## Failure Modes

### Local State Missing

**Symptom**
- resumable local thread state file is absent
- startup may not show expected local progress

**Effect**
- runtime checkpoint is unavailable

**Recovery**
- reconstruct PR plans from GitHub `prds` JSON artifacts if they exist
- if neither local state nor remote plan artifacts exist, thread must be treated as unrecoverable and restarted fresh

### Local State Stale / Saved Too Early

**Symptom**
- on restart, subsystem shows `0 PRs done`
- agent starts regenerating PR specs from PR #1
- local state shows:
  - `"state": "prd_gen"`
  - empty `pr_plans_by_prd`

**Effect**
- local state does not reflect already-generated PR plans

**Recovery**
- inspect GitHub `prds` branch for `*-pr-plan.json`
- rebuild planning state from those JSON files
- continue from reconstructed plan state rather than regenerating

### `prds` Branch Deleted or Corrupted

**Symptom**
- no machine-readable PR plan JSON available remotely

**Effect**
- disaster-recovery path is lost
- local state loss becomes unrecoverable for planning reconstruction

**Mitigation**
- preserve `forge-agent/build/consensusdevagent/prds` whenever it contains JSON files
- delete only old non-PRD branches per runbook

### Resume Not Offered at Startup

**Symptom**
- no incomplete thread shown despite expected prior work

**Possible Causes**
- thread-state file removed
- thread marked complete incorrectly
- local state unreadable or invalid
- startup detection failed to classify the thread as incomplete

**Effect**
- operator may accidentally start fresh and duplicate work

**Mitigation**
- inspect local thread JSON
- verify expected fields (`state`, `prd_count`, PR plans)
- recover from GitHub `prds` artifacts if needed

### Mid-Gate Backend Restart

**Symptom**
- backend restarts while awaiting operator approval

**Effect**
- gate state is lost
- approval does not survive restart

**Recovery**
- operator must re-approve explicitly
- subsystem must not auto-resolve or infer approval state

### GitHub Rate Limiting / API Failure

**Effect**
- delayed or failed persistence / recovery reads

**Handling Requirements**
- retry policy bounded to 3 total attempts
- `403` uses exponential backoff starting at 60s
- `429` obeys `Retry-After`
- no infinite retry loops

### Forbidden Write / Path Errors

**Examples**
- invalid path write
- path traversal attempt
- blind GitHub write without SHA

**Effect**
- write must be rejected

**Required Behavior**
- validate paths before any write
- stop rather than attempting unsafe fallback behavior

## Dependencies

### Runtime Dependencies

- **ForgeAgent startup flow**
  - provides bootstrap and startup lifecycle
- **Director**
  - provides `resume()` continuation entrypoint
- **local thread-state storage**
  - stores per-thread JSON checkpoints
- **GitHubTool**
  - sole allowed interface for GitHub operations
- **GitHub repository branches**
  - especially `forge-agent/build/consensusdevagent/prds` for durable PR-plan backups

### Behavioral / Platform Dependencies

- repository-wide GitHub operation policy:
  - no direct GitHub API use
  - validate paths before writes
  - no blind writes without SHA
- repository-wide retry and error-handling policy:
  - bounded retries only
  - provider fallback where documented
  - rate-limit handling as specified
- repository-wide gate semantics:
  - gates wait
  - no auto-resolution
  - backend restart loses gate state
  - explicit operator re-approval required

### Security Constraints Inherited by This Subsystem

The subsystem must comply with repository forbidden patterns, including:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt where prohibited
- no ignoring `SECURITY_REFUSAL`

These are cross-cutting constraints on implementation and operational behavior, including recovery and persistence paths.