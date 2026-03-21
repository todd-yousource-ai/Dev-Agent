# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the complete ConsensusDevAgent build across PRDs and PRs, with resumable progress across process restarts.

Its primary responsibilities are:

- Maintain per-thread build state for the `ConsensusDevAgent` workflow.
- Detect incomplete build threads automatically at application startup.
- Present resumable thread choices to the operator without requiring any explicit resume command.
- Resume execution via `director.resume()` when the operator selects an incomplete thread.
- Generate and track PRD-level and PR-level plans.
- Persist recovery-critical planning artifacts both locally and to GitHub.
- Reconstruct lost local planning state from GitHub-backed PR plan JSON artifacts.

Normal restart behavior is automatic:

1. ForgeAgent boots.
2. The subsystem scans persisted thread state.
3. If an incomplete `ConsensusDevAgent` thread exists, it is surfaced in the startup menu.
4. The operator selects the thread number.
5. The director resumes the thread.

No `/resume`, `/continue`, or `/ledger resume` command is part of the normal recovery path.

This subsystem is specifically concerned with build-thread continuity and PR/PRD planning state. It is not the general shell, not direct GitHub API orchestration, and not a generic workflow engine for unrelated agents.

## Component Boundaries

### In Scope

- Persistence of `ConsensusDevAgent` thread state in local thread-state storage.
- Startup-time discovery of incomplete `ConsensusDevAgent` build threads.
- Operator-visible resume selection for incomplete threads.
- State-machine progression for build phases such as:
  - PRD generation state
  - PR pipeline state
- Tracking of counts such as:
  - PRD completion count
  - PR plans generated
  - PRs completed
- Recovery from local-state loss using GitHub-stored PR plan JSON files.
- Branch hygiene expectations for this subsystem's generated branches.

### Out of Scope

- Direct use of the GitHub API. All GitHub operations must go through `GitHubTool`.
- Arbitrary command-driven resume semantics for normal restarts.
- Gate auto-resolution. Gates wait for explicit operator action.
- Recovery of gate approvals after backend restart; that state is explicitly not durable.
- Infinite retry behavior.
- Execution of generated code directly.
- Security policy exceptions such as path traversal, shell injection, or blind writes.

### Explicit Operational Boundary

The subsystem owns thread-level recovery state for `ConsensusDevAgent`, but does not own persistent operator approvals for gates. If the backend restarts mid-gate, gate state is lost and the operator must re-approve.

## Data Flow

### 1. Startup Detection

On normal startup, ForgeAgent bootstraps and then inspects local thread-state storage for incomplete build threads.

Expected operator experience:

- Application launch
- Bootstrap delay of approximately 45 seconds
- Discovery of incomplete thread(s)
- Prompt to select a thread number to resume or press Enter for a fresh build

The local thread state for this subsystem is stored at a path of the form:

`/Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

### 2. Resume Selection

If the operator selects the incomplete `ConsensusDevAgent` thread, control passes to resume logic via `director.resume()`.

Resume uses the persisted thread state to determine the correct continuation point rather than restarting from the beginning.

### 3. Local State Progression

The local thread JSON tracks workflow state and planning progress. Operationally important fields include:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

Expected interpretation:

- `state: "pr_pipeline"` indicates PR plans already exist and the thread should continue in PR execution/planning flow.
- `state: "prd_gen"` with empty `pr_plans_by_prd` indicates planning state was persisted before PR plans were generated.

### 4. GitHub-Backed Recovery Artifacts

After each PR plan is generated, the subsystem writes two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Semantics:

- `.md` file: human-readable summary/table
- `.json` file: machine-readable recovery artifact

The JSON artifact is the disaster-recovery source of truth for reconstructing PR planning if local thread state is lost or stale.

### 5. Reconstruction Path

If local thread state is wiped, corrupted, or persisted before PR plans were materialized, the subsystem must reconstruct PR planning state from the GitHub PR plan JSON files on resume.

This is the intended disaster-recovery path described by the runbook.

### 6. Branch Lifecycle

This subsystem creates build branches automatically. Operational guidance requires deletion of stale branches matching:

- `forge-agent/build/consensusdevagent-*`

Keep only:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it still contains JSON files

This prevents stale CI failures and branch-monitor confusion from contaminating the active build thread.

## Key Invariants

1. **Normal restart recovery is automatic**
   - No explicit resume command is required for normal restart.
   - Incomplete threads must be discoverable at startup.

2. **Resume is operator-selected, not implicit**
   - The subsystem may detect incomplete threads automatically.
   - Actual continuation occurs only after operator selection of the thread entry.

3. **Thread state must reflect the true phase**
   - If PR plans exist, thread state should not remain at pre-plan generation semantics.
   - In particular, `state` should be `pr_pipeline` when PR plans exist.

4. **GitHub JSON PR plans are the durable recovery backup**
   - Local thread state is not the only recovery source.
   - PR plan JSON files in the PRDs branch must be sufficient to reconstruct planning state.

5. **GitHub writes must be mediated**
   - All GitHub operations go through `GitHubTool`.
   - Never use the GitHub API directly.

6. **Writes must be validated**
   - Validate paths before any write.
   - Blind GitHub writes without SHA are forbidden.

7. **Retries are bounded**
   - Never retry indefinitely.
   - Maximum 3 attempts total.

8. **Rate-limit handling is policy-driven**
   - `403` primary rate limit: exponential backoff starting at 60 seconds.
   - `429` secondary rate limit: respect `Retry-After` exactly.
   - Polling endpoints use ETag caching.

9. **Gates do not auto-resolve**
   - They wait for explicit operator action.
   - On backend restart, gate state is lost.
   - No undo exists for gate decisions.

10. **Security constraints are non-negotiable**
    - No shell injection
    - No credential in logs
    - No credential in prompts
    - No direct execution of generated code
    - No path traversal
    - No blind GitHub write
    - No context in system prompt
    - No ignoring `SECURITY_REFUSAL`

## Failure Modes

### Local Thread State Missing

Example:
- `consensusdevagent.json` has been deleted or wiped.

Effect:
- Startup may not show expected progress from local storage.

Recovery:
- Reconstruct from GitHub PR plan JSON files in the PRDs branch.

### Local Thread State Stale or Prematurely Saved

Symptom:
- After restart, the agent shows `0 PRs done` and begins regenerating PR plans from the start.

Diagnosis:
- Local state shows:
  - `state: "prd_gen"`
  - empty `pr_plans_by_prd`

Cause:
- State was persisted before PR plans were generated.

Recovery:
- Inspect GitHub PRDs branch for `prd-*-pr-plan.json`.
- Rehydrate planning state from those JSON files.

### Stale Branch Accumulation

Symptom:
- Old CI failures persist.
- Branch monitor becomes confused by outdated build branches.

Cause:
- Old `forge-agent/build/consensusdevagent-*` branches were not cleaned up.

Recovery:
- Delete old branches.
- Retain only `main` and the PRDs branch if it contains JSON recovery files.

### Mid-Gate Backend Restart

Symptom:
- Build cannot continue through a previously pending approval point automatically.

Cause:
- Gate state is not durable across backend restart.

Recovery:
- Operator must explicitly re-approve.
- The system must not auto-resolve or infer approval.

### GitHub Operation Failures

Causes:
- Provider/API failures
- Rate limiting
- SHA mismatch or write conflict

Handling requirements:
- Route through `GitHubTool`
- Use bounded retries only
- Apply backoff policy for `403`
- Respect `Retry-After` for `429`
- Stop and surface an error rather than looping indefinitely

### Provider Failure During Generation

Handling requirements from repository policy:

- In `_claude_json`: retry after 10 seconds, then fall back to OpenAI
- In `consensus.py`: retry with the other provider
- Max 3 attempts total
- On hard refusal or security refusal:
  - Stop
  - Do not retry
  - Do not rephrase
  - Emit error card
  - Gate
  - Log full prompt context
  - Require explicit operator override

## Dependencies

### Local State Store

Used for thread-progress persistence and startup discovery of incomplete builds.

Primary artifact:
- `state/threads/consensusdevagent.json`

### Director Resume Mechanism

`director.resume()` is the execution handoff for continuing an incomplete thread after operator selection.

### GitHubTool

Mandatory abstraction for all GitHub operations.

Used for:
- Reading PRD/PR-plan artifacts
- Writing `.md` and `.json` plan files
- Branch operations consistent with repository policy

Direct GitHub API usage is forbidden.

### Git Branch Topology

The subsystem depends on repository branches for both active work and recovery artifacts, especially:

- `main`
- `forge-agent/build/consensusdevagent/prds`

The PRDs branch is recovery-critical when it contains PR plan JSON files.

### Consensus / Generation Providers

The subsystem depends on the repository’s consensus and LLM generation infrastructure for PRD and PR plan generation, including provider failover behavior defined in repository policy.

### Repository-Wide Operational and Security Policies

This subsystem must comply with repository-level rules covering:

- path validation before writes
- bounded retries
- rate-limit handling
- ETag caching on polling endpoints
- gate semantics
- security refusals
- forbidden patterns

These are architectural constraints, not optional implementation details.