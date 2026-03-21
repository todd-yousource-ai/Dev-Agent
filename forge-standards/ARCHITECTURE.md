# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and executing the end-to-end construction of the `ConsensusDevAgent` target across PRDs and PRs, with restart-safe recovery.

Its primary responsibilities are:

- maintain thread-local build state for the `ConsensusDevAgent` workstream
- detect incomplete work automatically on application startup
- allow operator selection of an incomplete build thread for continuation
- resume execution via `director.resume()` without requiring an explicit resume command
- persist PR planning artifacts to GitHub for disaster recovery
- reconstruct lost local state from persisted PR plan JSON artifacts when available
- track progression through phases such as PRD generation and PR pipeline execution
- expose enough state for operator inspection and operational repair

Normal recovery is automatic. On startup, the system scans for incomplete build threads and presents them to the operator. If the operator selects the `ConsensusDevAgent` thread, execution resumes from saved state. No `/resume`, `/continue`, or `/ledger resume` command is part of the normal restart path.

This subsystem is therefore both:

- a stateful execution thread for building `ConsensusDevAgent`
- a recovery domain with dual persistence:
  - local thread state
  - GitHub-backed PR plan artifacts

## Component Boundaries

### In Scope

This subsystem includes:

- the `ConsensusDevAgent` thread identity and its persisted thread state
- startup-time incomplete-thread detection for this thread
- resume selection and handoff into `director.resume()`
- state transitions relevant to build continuation
- PRD-to-PR planning state, including `pr_plans` / `pr_plans_by_prd`
- persistence of PR plan outputs into the GitHub `prds` branch
- recovery from local state loss using GitHub JSON artifacts
- operator-facing inspection and cleanup procedures specific to this thread

### Out of Scope

This subsystem does not define:

- ForgeAgent.app bootstrap behavior beyond the fact that restart recovery happens after startup
- generic UI command parsing for arbitrary commands
- implementation details of the consensus engine itself
- direct GitHub API usage
- CI execution semantics
- gate persistence across backend restarts
- undo semantics for operator gate decisions

### External System Boundaries

#### Startup / App Shell

The app shell launches the agent and reaches the `forge>` prompt. ConsensusDevAgent depends on startup completing, but does not own bootstrap.

#### Director

The director owns actual resumption entry via `director.resume()`. ConsensusDevAgent supplies recoverable thread state and resumable execution context.

#### GitHub Persistence Layer

All GitHub operations must flow through `GitHubTool`. The subsystem may rely on GitHub-stored PR plan files as recovery artifacts, but must not bypass the platform GitHub abstraction or write blindly without SHA validation.

#### Local State Store

The subsystem stores thread-local state in a JSON file under the workspace thread-state directory. This local file is the primary live state for restart continuation.

## Data Flow

### 1. Normal Startup Recovery

1. Operator launches `ForgeAgent.app`.
2. Agent bootstraps.
3. The system scans thread state for incomplete builds.
4. If `ConsensusDevAgent` is incomplete, it is shown in the recovery picker with summary metadata such as:
   - PRD progress
   - PR completion count
   - last activity time
   - thread description
5. Operator enters the selection number.
6. Resume is handed to `director.resume()`.

Key property: recovery discovery is automatic; command-based resume is not required for normal restarts.

### 2. Local State Persistence

The subsystem persists thread-local execution state to:

- `.../state/threads/consensusdevagent.json`

This file contains operational recovery state such as:

- `"state"` phase marker
- PRD count
- PR plan structures
- PR pipeline progress

Operationally important interpretations include:

- `"state": "pr_pipeline"` indicates PR planning has completed and the pipeline should continue from PR execution state
- `"state": "prd_gen"` with empty `pr_plans_by_prd` indicates planning state was not persisted before restart and recovery may need GitHub-backed reconstruction

### 3. GitHub-Backed PR Plan Persistence

After each PR plan is generated, the subsystem writes two artifacts to the GitHub `prds` branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The markdown artifact is human-readable.  
The JSON artifact is the machine-readable disaster recovery source of truth for PR planning.

This creates a secondary persistence channel independent of local thread state.

### 4. Recovery From Local State Loss

If local thread state is wiped or stale, the subsystem can recover PR planning state from GitHub PR plan JSON files.

Expected reconstruction behavior:

1. detect missing or insufficient local planning state
2. inspect GitHub `prds` branch for persisted `*-pr-plan.json` artifacts
3. rebuild in-memory/local PR planning structures from those JSON files
4. continue execution from reconstructed planning state rather than regenerating already-planned PRs

This recovery path is specifically intended to prevent unnecessary regeneration after crashes or state loss.

## Key Invariants

### Restart and Resume

- Normal restart requires no explicit resume command.
- Incomplete `ConsensusDevAgent` threads must be discoverable at startup.
- Resume must occur from persisted thread state after operator selection.
- Recovery must not depend on chat commands such as `/resume` or `/continue`.

### State Model

- The local thread state file is the primary active checkpoint for this thread.
- `state` must accurately reflect the current lifecycle phase.
- If PR plans exist, the thread should not remain in an earlier generation phase inconsistent with those plans.
- `pr_plans` / `pr_plans_by_prd` counts must align with expected PR counts per PRD.

### Persistence and Recovery

- Every generated PR plan must be persisted to GitHub as both markdown and JSON.
- The JSON PR plan artifact is the disaster recovery backup.
- Loss of local thread state must not require total re-planning if GitHub JSON artifacts exist.
- Recovery must prefer reconstruction from machine-readable plan artifacts over speculative regeneration.

### GitHub Safety

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Validate paths before any write.
- Never perform blind GitHub writes without SHA protection.

### Operational Hygiene

- Old branches matching `forge-agent/build/consensusdevagent-*` should be deleted during cleanup.
- Preserve:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files
- The `prds` branch is recoverability-critical when it contains plan JSON artifacts.

### Platform Safety Rules Relevant Here

- gates never auto-resolve
- if backend restarts mid-gate, gate state is lost and operator must re-approve
- there is no undo on gate decisions
- retries are bounded; never retry indefinitely

These constraints apply to the subsystem’s execution environment and must be respected during recovery and continuation.

## Failure Modes

### 1. Local State Saved Too Early

**Symptom:** On restart, the agent shows `0 PRs done` and begins regenerating from PR #1.

**Likely diagnosis:**

- local thread state has `"state": "prd_gen"`
- `pr_plans_by_prd` is empty `{}`

This means the checkpoint was captured before PR plans were persisted into local state.

**Expected handling:**

- inspect GitHub `prds` branch for `*-pr-plan.json`
- reconstruct planning state from JSON artifacts
- avoid regenerating already-planned PRs if recovery artifacts exist

### 2. Local Thread State Deleted

**Symptom:** `consensusdevagent.json` is missing.

**Cause:** operator or maintenance workflow wiped local thread state.

**Expected handling:**

- recover from GitHub PR plan JSON artifacts if present
- otherwise, treat as fresh start with loss of in-progress local-only state

### 3. PRDS Recovery Branch Deleted Improperly

**Symptom:** local state is incomplete and no GitHub JSON artifacts are available.

**Cause:** accidental deletion of `forge-agent/build/consensusdevagent/prds` containing backup JSON files.

**Impact:** disaster recovery path for PR planning is lost.

**Mitigation:** operational runbook explicitly preserves the `prds` branch when it contains JSON files.

### 4. Branch Accumulation / Monitor Confusion

**Symptom:** stale branches accumulate CI failures and confuse branch monitoring.

**Cause:** old `forge-agent/build/consensusdevagent-*` branches not cleaned up.

**Expected handling:** remove obsolete branches while preserving `main` and the recovery-critical `prds` branch.

### 5. Backend Restart During Gate

**Symptom:** execution does not continue through a previously pending gate after restart.

**Cause:** gate state is not durable across backend restart.

**Expected handling:**

- do not auto-resolve
- require explicit operator re-approval
- document that no undo exists for gate decisions

### 6. GitHub Write or Polling Failures

The subsystem inherits platform-level GitHub error handling requirements:

- `403` primary rate limit: exponential backoff starting at 60s
- `429` secondary rate limit: respect `Retry-After` exactly
- polling endpoints use ETag caching
- maximum 3 attempts total; never retry indefinitely

Failure to follow these rules risks duplicate writes, rate-limit escalation, or inconsistent recovery metadata.

## Dependencies

### Required Platform Dependencies

- **Director**
  - owns `resume()` orchestration after thread selection

- **Local Thread State Store**
  - stores `consensusdevagent.json`
  - provides startup discovery inputs and resume checkpoints

- **GitHubTool**
  - mandatory path for all GitHub reads/writes
  - used for PR plan persistence and recovery artifact access

- **Startup Incomplete-Thread Scanner**
  - enumerates unfinished build threads and summary metadata

### Recovery-Critical Data Dependencies

- local thread JSON:
  - current phase
  - PRD progress
  - PR planning state
  - pipeline progress

- GitHub `prds` branch artifacts:
  - `prd-*-pr-plan.json` as machine-readable recovery source
  - `prd-*-pr-plan.md` as human-readable inspection output

### Operational Dependencies

- branch hygiene procedures from the operational runbook
- operator ability to inspect thread state JSON
- operator ability to preserve the PRDS branch during cleanup

### Repository-Wide Constraints This Subsystem Must Respect

- all GitHub ops through `GitHubTool`
- validate paths before any write
- no direct execution of generated code
- no path traversal
- no blind write without SHA
- no credential leakage in logs or prompts
- never ignore `SECURITY_REFUSAL`

These repository-wide constraints are not implemented by this subsystem alone, but they are mandatory architectural assumptions for its correct operation.