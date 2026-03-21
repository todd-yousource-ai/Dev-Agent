# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the repository build for the `ConsensusDevAgent` target. It owns:

- persistent thread state for the build,
- startup/restart recovery,
- PRD-to-PR planning progression,
- reconstruction of local execution state from GitHub-backed artifacts,
- operator-facing resume selection for incomplete builds.

This subsystem is designed so that a normal application restart does **not** require a manual resume command. On startup, Forge scans for incomplete build threads and presents them for operator selection. If the operator selects the incomplete `ConsensusDevAgent` thread, control passes to `director.resume()` and execution continues from saved state.

Normal restart sequence:

1. Launch `ForgeAgent.app`
2. Bootstrap completes (~45s; transient installer pauses are expected)
3. Incomplete build threads are discovered automatically
4. Operator selects the `ConsensusDevAgent` thread by number
5. Resume is initiated via `director.resume()`

The subsystem also supports disaster recovery when local thread state is missing or stale. In that case, it reconstructs PR planning state from machine-readable PR plan JSON artifacts stored on the GitHub PRDs branch.

## Component Boundaries

### In Scope

ConsensusDevAgent includes responsibility for:

- managing the local thread state file for the `ConsensusDevAgent` build thread,
- tracking build lifecycle state such as PRD generation vs PR pipeline execution,
- persisting and resuming PR plan progress,
- detecting incomplete threads at startup,
- resuming from previously saved local state,
- reconstructing state from GitHub-backed PR plan JSON when local state is absent or incomplete,
- presenting build status summary during resume selection.

Representative local state path:

- `workspace/.../state/threads/consensusdevagent.json`

Representative GitHub recovery artifacts:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

### Out of Scope

This subsystem does **not** own:

- application bootstrap itself,
- generic branch lifecycle management outside its branch namespace,
- direct GitHub API access,
- gate auto-resolution,
- operator approval persistence across backend restarts,
- arbitrary code execution,
- repository-global CI policy.

GitHub operations must go through `GitHubTool`; the subsystem must not call the GitHub API directly.

### Branch Boundary

This subsystem operates within the `forge-agent/build/consensusdevagent-*` branch namespace for generated build branches. Operational guidance explicitly treats old branches in this namespace as disposable, except:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery files

Old build branches should be deletable because the agent recreates branches automatically. The PRDs branch is special because it may contain the authoritative recovery artifacts.

## Data Flow

### 1. Startup and Incomplete Thread Detection

At normal startup:

1. Forge bootstraps.
2. Thread state storage is scanned for incomplete build threads.
3. If a `ConsensusDevAgent` thread is incomplete, it is presented in the resume menu with summary metadata:
   - agent name,
   - PRD progress,
   - PR completion count,
   - recency,
   - human-readable task description.
4. Operator selects the thread.
5. Resume transfers to `director.resume()`.

There is no `/resume`, `/continue`, or `/ledger resume` requirement for standard restart behavior.

### 2. Local State Persistence

The subsystem persists execution state in a local JSON thread file. Important observable fields include:

- `state`
- `prd_count`
- `pr_plans` / `pr_plans_by_prd`

Operationally relevant interpretation:

- `state: "pr_pipeline"` indicates PR plans should already exist and execution is in PR pipeline processing.
- `state: "prd_gen"` with empty `pr_plans_by_prd` indicates PR planning was not durably captured in local state before restart.

### 3. PR Plan Artifact Persistence to GitHub

After each PR plan is generated, the subsystem writes two artifacts to the PRDs branch:

- markdown summary for human inspection,
- JSON specification for machine recovery.

The JSON file is the disaster-recovery source of truth for plan reconstruction if local state is wiped or stale.

### 4. Recovery from GitHub Artifacts

If local state is missing, corrupted, or reflects a pre-plan-save snapshot, the subsystem must recover by reading PR plan JSON files from the PRDs branch and reconstructing the full plan set.

This path is required to resolve the observed failure mode where the system restarts at `0 PRs done` and begins regenerating PRs from the beginning despite prior progress.

### 5. Manual Reset / Operational Repair

Operators may intentionally wipe local thread state by deleting the thread JSON file. After that, recovery depends on GitHub-backed PR plan JSON existing on the PRDs branch.

This means local state is a cache/checkpoint; GitHub PR plan JSON is the durable recovery substrate for planning state.

## Key Invariants

1. **Normal restart is automatic at startup**
   - No explicit resume command is required for ordinary restart.
   - Incomplete build discovery must happen during startup flow.

2. **Resume is thread-based**
   - Recovery targets an incomplete build thread, not a free-form command invocation.

3. **Local thread state is not the only source of truth**
   - PR plan JSON stored in GitHub must be sufficient to reconstruct planning state after local loss.

4. **PR plan JSON is durable recovery data**
   - For every generated PR plan, the machine-readable JSON artifact must be written to the PRDs branch.

5. **State must reflect execution phase accurately**
   - If PR plans exist, local state should indicate the PR pipeline phase rather than PRD generation.

6. **Old build branches are disposable**
   - Build branches under `forge-agent/build/consensusdevagent-*` should not be relied on for durable recovery.
   - The PRDs branch is the exception if it contains JSON files.

7. **GitHub writes must be safe and mediated**
   - All GitHub operations go through `GitHubTool`.
   - Paths must be validated before any write.
   - No blind write without SHA.
   - No direct GitHub API usage.

8. **Gates never auto-resolve**
   - If this subsystem encounters a gated condition, it must wait.
   - If backend restarts during a gate, gate state is lost and must be re-approved by the operator.

9. **Retries are bounded**
   - Never retry indefinitely.
   - Maximum 3 attempts total.
   - Provider/tool-specific backoff rules apply.

10. **Security restrictions are mandatory**
    - No shell injection
    - No credential leakage to logs or prompts
    - No direct execution of generated code
    - No path traversal
    - No blind GitHub write
    - No ignoring `SECURITY_REFUSAL`

## Failure Modes

### 1. Restart Causes PR Regeneration from Zero

**Symptom**
- Resume shows `0 PRs done`
- System begins generating `PR #1` again

**Typical diagnosis**
- Local thread JSON shows:
  - `state: "prd_gen"`
  - empty `pr_plans_by_prd`

**Cause**
- Local state was saved before PR plans were durably captured there.

**Required behavior**
- Recover PR plans from GitHub PRD JSON artifacts instead of regenerating from scratch.

### 2. Local Thread State Deleted

**Symptom**
- No local thread checkpoint for `ConsensusDevAgent`

**Cause**
- Manual wipe or corruption of `consensusdevagent.json`

**Required behavior**
- Reconstruct from GitHub PR plan JSON if present.
- If PRD JSON is absent, planning state is unrecoverable from this subsystem alone.

### 3. PRDs Branch Missing or Cleaned Incorrectly

**Symptom**
- Local state lost and no recovery artifacts available

**Cause**
- `forge-agent/build/consensusdevagent/prds` branch deleted or retained without required JSON files

**Impact**
- Disaster recovery for PR planning is broken.

**Operational implication**
- The PRDs branch must be preserved when it contains JSON files.

### 4. GitHub Write/Read Failures

**Cause examples**
- rate limits,
- permission failures,
- SHA mismatch,
- path validation failure,
- transient provider/tool errors.

**Required behavior**
- Apply bounded retries only.
- Respect:
  - 403 primary rate-limit backoff starting at 60s with exponential backoff,
  - 429 secondary limit `Retry-After` exactly,
  - ETag caching on polling endpoints.
- Emit an error card and gate when failure is non-retriable or policy-blocked.

### 5. Backend Restart During Gate

**Symptom**
- previously pending approval is no longer active after restart

**Cause**
- gate state is not durable across backend restarts

**Required behavior**
- Do not auto-resolve or infer prior approval.
- Require explicit operator re-approval.

### 6. Unsafe or Forbidden Operation Attempted

**Examples**
- direct GitHub API usage,
- path traversal,
- shell injection,
- generated code execution,
- credential exposure,
- write without SHA.

**Required behavior**
- Stop immediately.
- Do not retry or rephrase around the policy.
- Emit error card, gate, and log full prompt context as required by system policy.

## Dependencies

### Runtime/Platform Dependencies

- Forge application startup flow
- thread-state persistence under workspace state storage
- `director.resume()` for continuation of incomplete work

### Storage Dependencies

- local thread JSON file for checkpointed execution state
- GitHub PRDs branch for durable PR plan recovery artifacts

### Tooling Dependencies

- `GitHubTool` for all GitHub reads/writes
- consensus/provider infrastructure subject to bounded retry rules
- document/context loading facilities for repository instructions and generation inputs

### Repository Contract Dependencies

This subsystem must conform to repository-wide operating rules reflected in the documented headings, including:

- read critical files before modifying behavior,
- validate paths before writes,
- use consensus engine and document store according to repo contract,
- route GitHub operations only through approved tooling,
- honor CI routing and version management conventions,
- apply the security checklist before every PR.

### Operational Dependencies

- operators must select the incomplete build thread on startup to resume work,
- operators may inspect local state fields to diagnose restart problems,
- operators may preserve or remove branches according to runbook rules,
- operators must re-approve gated actions after backend restarts.