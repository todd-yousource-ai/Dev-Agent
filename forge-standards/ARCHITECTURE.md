# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and driving the implementation of the `ConsensusDevAgent` repository workstream across PRDs and PRs, with restart-safe recovery semantics.

Its core responsibilities are:

- Maintain per-thread build state for the `ConsensusDevAgent` build.
- Detect incomplete work automatically at agent startup.
- Present resumable build threads to the operator without requiring any resume command.
- Resume execution from persisted thread state when the operator selects the incomplete build.
- Persist PR planning artifacts to both local thread state and GitHub-backed recovery files.
- Reconstruct PR pipeline state from GitHub PR plan JSON if local state is missing or stale.
- Continue execution through PRD generation / PR pipeline stages without duplicating completed planning work when valid recovery data exists.

Normal recovery is automatic:

1. `ForgeAgent.app` starts.
2. Bootstrap completes.
3. Incomplete build threads are detected automatically.
4. The operator selects the thread by number.
5. `director.resume()` is invoked for the selected thread.

No `/resume`, `/continue`, or `/ledger resume` command is part of the normal restart path.

Operationally, this subsystem exists to ensure that long-running multi-PRD, multi-PR workflows survive process restarts and local state loss, while preserving enough structure to continue planning and execution deterministically.

## Component Boundaries

### In Scope

The subsystem includes:

- Discovery of incomplete `ConsensusDevAgent` build threads at startup.
- Local persisted thread state for the build thread.
- Resume selection UX for incomplete builds.
- Transition into resumed execution via `director.resume()`.
- Tracking build state fields such as:
  - `state`
  - `prd_count`
  - `pr_plans`
  - `pr_plans_by_prd`
- Persistence of PR plan artifacts into GitHub on the PRDs branch:
  - `prds/consensusdevagent/prd-001-pr-plan.md`
  - `prds/consensusdevagent/prd-001-pr-plan.json`
- Disaster recovery reconstruction of PR plans from GitHub JSON artifacts.
- Operational branch hygiene for build branches under:
  - `forge-agent/build/consensusdevagent-*`
- Preservation of the PRDs branch when it contains recovery JSON files:
  - `forge-agent/build/consensusdevagent/prds`

### Out of Scope

The subsystem does not own:

- General Forge bootstrap behavior beyond relying on startup completion.
- Direct GitHub API usage. All GitHub operations must route through `GitHubTool`.
- Gate persistence across backend restarts.
- Automatic operator decision replay after restart.
- Direct execution of generated code.
- CI implementation details, other than being affected by branch accumulation and branch monitor behavior.
- Arbitrary repository-wide state management outside the `ConsensusDevAgent` thread and its PRD/PR artifacts.

### Explicit Boundary Rules

- Recovery is startup-driven, not command-driven.
- GitHub is the recovery backup for PR planning artifacts; local thread state is not the sole source of truth.
- Branch cleanup may remove old build branches, but must retain `main` and the PRDs branch if it contains JSON recovery files.
- Gate state is not durable across backend restarts. If a restart occurs mid-gate, operator approval must be re-issued.

## Data Flow

### 1. Startup Detection

On normal startup:

- The agent bootstraps.
- The system scans persisted thread state for incomplete build threads.
- If an incomplete `ConsensusDevAgent` build exists, the operator is shown a resumable entry such as:
  - thread name
  - PRD progress
  - PR progress
  - recency metadata
  - build description

This is a discovery/read path only; no explicit resume command is required.

### 2. Resume Selection

When the operator selects the listed build thread:

- The runtime invokes `director.resume()` for the selected thread.
- Resume proceeds from local persisted thread state if present and internally consistent.

Primary local thread state path:

- `/Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

Relevant inspected fields include:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

### 3. Planning Persistence

As PR plans are generated, the subsystem writes durable recovery artifacts to the GitHub PRDs branch.

Per PRD, two artifacts are produced:

- Human-readable plan:
  - `prds/consensusdevagent/prd-001-pr-plan.md`
- Machine-readable recovery/spec artifact:
  - `prds/consensusdevagent/prd-001-pr-plan.json`

The JSON artifact is the disaster recovery source used to reconstruct planning state.

### 4. Recovery Reconstruction

If local state is lost, deleted, or saved too early, the subsystem reconstructs PR planning state by reading the PR plan JSON artifacts from the GitHub PRDs branch.

This is specifically required when symptoms indicate stale local state, e.g.:

- local `state` remains `prd_gen`
- `pr_plans_by_prd` is empty
- restart causes PR generation to restart from PR #1 despite prior planning completion

In that case:

- GitHub JSON artifacts are treated as authoritative recovery inputs.
- The subsystem rebuilds the PR pipeline representation from those files.
- Resume continues from reconstructed state rather than regenerating already-planned PRs.

### 5. Operational Reset Paths

Operators may intentionally reset local state by deleting the thread state file:

- `rm /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

This removes local resume state only. Recovery remains possible if GitHub PR plan JSON files exist.

Operators may also clean old build branches:

- delete `forge-agent/build/consensusdevagent-*`
- keep:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files

This cleanup exists to prevent stale CI failures and branch-monitor confusion, while preserving recovery artifacts.

## Key Invariants

1. **Normal restart requires no resume command**
   - Recovery is initiated by startup detection plus operator selection.
   - `/resume`, `/continue`, and `/ledger resume` are not part of the normal flow.

2. **An incomplete build thread must be discoverable at startup if persisted state exists**
   - Incomplete `ConsensusDevAgent` work must appear in the startup resume list.

3. **`director.resume()` is the execution handoff for resumed threads**
   - Startup detection and operator choice culminate in a single resume entrypoint.

4. **PR plan JSON in GitHub is the durable recovery backup**
   - Local thread state is recoverable from GitHub-backed JSON artifacts.
   - Recovery cannot depend exclusively on local disk state.

5. **The PRDs branch may be retention-critical**
   - `forge-agent/build/consensusdevagent/prds` must be preserved if it contains JSON files.
   - Deleting this branch can destroy the disaster recovery source.

6. **State machine values must reflect completed planning**
   - If PR plans exist, thread state should reflect PR pipeline progression rather than remaining at an earlier generation phase.
   - Operational guidance indicates `state` should be `pr_pipeline` if PR plans exist.

7. **Branch cleanup must not remove authoritative recovery artifacts**
   - Old build branches are disposable.
   - Recovery-bearing PRDs branch is not disposable when populated.

8. **All GitHub operations must go through `GitHubTool`**
   - No direct GitHub API access is permitted.

9. **GitHub writes must be validated and SHA-aware**
   - No blind writes.
   - Paths must be validated before any write.

10. **Gates do not auto-resolve**
    - If a restart occurs during a gate, gate state is lost.
    - The operator must explicitly re-approve.
    - No implicit replay or undo exists.

11. **Retries are bounded**
    - Never retry indefinitely.
    - Maximum 3 attempts total.
    - Provider- and HTTP-specific retry behavior must follow repository standards.

12. **Security constraints apply to all generation and persistence paths**
    - No shell injection.
    - No path traversal.
    - No credential leakage to logs or prompts.
    - No direct execution of generated code.
    - No ignoring `SECURITY_REFUSAL`.

## Failure Modes

### Local Thread State Missing

**Symptom**
- No local thread JSON exists.

**Effect**
- Normal local resume state is unavailable.

**Expected behavior**
- If GitHub PR plan JSON artifacts exist, reconstruct the plan from GitHub and resume.
- If no recovery artifacts exist, the build may need to restart fresh.

### Local Thread State Stale / Saved Too Early

**Symptom**
- On restart, system shows `0 PRs done` and starts regenerating PR #1.
- `state` is `prd_gen`.
- `pr_plans_by_prd` is empty.

**Cause**
- Local state was persisted before PR plans were recorded.

**Effect**
- Resume would regress to an earlier phase and duplicate planning work.

**Expected behavior**
- Detect inconsistency.
- Load PR plan JSON from GitHub PRDs branch.
- Reconstruct PR pipeline state.
- Avoid unnecessary regeneration.

### Recovery Branch Deleted

**Symptom**
- Local state lost and PRDs branch JSON files absent.

**Effect**
- Disaster recovery source is unavailable.

**Expected behavior**
- Recovery falls back to whatever local state remains.
- If neither source exists, planning must restart from scratch.

### Old Build Branch Accumulation

**Symptom**
- Multiple stale `forge-agent/build/consensusdevagent-*` branches accumulate.
- CI failures and branch-monitor confusion increase.

**Effect**
- Operational noise and incorrect monitoring signals.

**Expected behavior**
- Delete old build branches.
- Retain `main`.
- Retain PRDs branch if it contains JSON recovery files.

### Backend Restart During Gate

**Symptom**
- Restart occurs while awaiting operator approval.

**Effect**
- Gate state is lost.

**Expected behavior**
- Gate does not auto-resolve.
- Operator must explicitly re-approve.
- No undo or implicit carry-forward of prior approval.

### GitHub Rate Limiting / Provider Errors

**Symptom**
- GitHub or model provider operations fail transiently.

**Effect**
- Recovery, persistence, or polling may stall.

**Expected behavior**
- Follow platform retry policy:
  - max 3 attempts total
  - `_claude_json`: retry after 10s, then fall back to OpenAI
  - `consensus.py`: retry with the other provider
  - `403 primary`: exponential backoff starting at 60s
  - `429 secondary`: respect `Retry-After`
  - use ETag caching on polling endpoints

### Unsafe Write or Path Handling

**Symptom**
- Attempted write without path validation or without blob SHA context.

**Effect**
- Risk of corruption, path traversal, or blind overwrite.

**Expected behavior**
- Reject the operation.
- Enforce validated paths and SHA-aware writes through `GitHubTool`.

## Dependencies

### Runtime / Platform Dependencies

- Forge application startup flow (`ForgeAgent.app`)
- Director resume orchestration (`director.resume()`)
- Local thread state storage under workspace state directory
- Startup thread discovery / incomplete-build listing

### Persistence Dependencies

- Local JSON thread state file for `ConsensusDevAgent`
- GitHub PRDs branch as durable backup store
- PR plan JSON artifacts as machine-readable recovery source
- PR plan markdown artifacts as human-readable operator/debug output

### Tooling Dependencies

- `GitHubTool` for all GitHub operations
- JSON inspection/debug tooling in operational workflows
- Branch monitor / CI systems indirectly affected by branch hygiene

### Policy / Repository Dependencies

The subsystem is constrained by repository-wide operational and security rules, including:

- validate paths before any write
- never use the GitHub API directly
- no blind GitHub write without SHA
- bounded retries only
- gate persistence is not guaranteed across restart
- stop on security refusal conditions
- never place sensitive context or credentials into logs or prompts

### Human/Operational Dependencies

- Operator selects the resumable thread at startup
- Operator may inspect local JSON state during diagnosis
- Operator may clean stale branches
- Operator may wipe local state intentionally
- Operator must re-approve gates after restart when gate state was lost