# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread orchestration subsystem for the `ConsensusDevAgent` build target. It is responsible for:

- tracking build-thread progress across restarts
- detecting and resuming incomplete work automatically at Forge startup
- persisting execution state locally
- persisting PR-plan recovery artifacts to GitHub
- reconstructing local execution state from GitHub-backed PR plan JSON when local thread state is missing or stale
- continuing the PR pipeline after operator selection of an incomplete thread

This subsystem specifically supports **automatic recovery on normal restart**:

- no `/resume`
- no `/continue`
- no `/ledger resume`

On startup, the platform bootstraps, scans persisted thread state, identifies incomplete build threads, and offers them for operator selection. If the operator selects the incomplete `ConsensusDevAgent` thread, the runtime invokes `director.resume()` for that thread.

It also defines the recovery contract for PR planning state:

- after each PR plan is generated, a human-readable markdown file and a machine-readable JSON file are written to the GitHub PRDs branch
- the JSON file is the authoritative disaster-recovery backup for PR-plan reconstruction
- if local thread state is lost, the subsystem rebuilds PR planning state from those JSON artifacts on resume

## Component Boundaries

### In Scope

This subsystem owns:

- build-thread state for `ConsensusDevAgent`
- incomplete-thread detection at startup
- thread resume selection UX integration
- transition into resumed execution via `director.resume()`
- local persisted state file management for the `ConsensusDevAgent` thread
- use of GitHub-hosted PR plan JSON as backup state for recovery
- consistency between persisted thread phase and available PR plan artifacts

Primary local state artifact:

- `state/threads/consensusdevagent.json`

Primary remote recovery artifacts:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`
- corresponding files for each PRD in the PRDs branch

Operational branch lifecycle relevant to this subsystem:

- keep `main`
- keep `forge-agent/build/consensusdevagent/prds` if it contains JSON files
- delete stale branches matching `forge-agent/build/consensusdevagent-*`

### Out of Scope

This subsystem does **not** own:

- Forge bootstrap itself
- the general terminal UI framework beyond exposing resumable threads
- PR implementation logic
- CI execution or CI repair
- GitHub API calls outside the platform’s GitHubTool abstraction
- gate persistence across backend restarts
- undo/rollback semantics for operator gate decisions

### External Constraints It Must Respect

- All GitHub operations go through `GitHubTool`; direct GitHub API usage is forbidden.
- Blind GitHub writes are forbidden; writes must be SHA-aware.
- Gates never auto-resolve.
- If the backend restarts mid-gate, gate state is lost and the operator must re-approve.
- There is no undo for gate decisions.
- Retry behavior must be bounded; never retry indefinitely.

## Data Flow

### 1. Normal Startup and Incomplete Thread Discovery

On application launch:

1. Operator starts `ForgeAgent.app`
2. platform bootstrap completes
3. startup logic scans persisted thread state
4. incomplete build threads are rendered in the startup prompt
5. operator chooses a thread number to resume, or presses Enter for a fresh run

Expected behavior for `ConsensusDevAgent`:

- if an incomplete thread exists, it is shown with summary metadata such as PRD count, completed PRs, and recency
- selecting the thread resumes existing work rather than starting over

### 2. Resume Path

After thread selection:

1. `director.resume()` is invoked for the selected thread
2. local thread state is loaded from `state/threads/consensusdevagent.json`
3. the subsystem inspects the saved state machine phase and any persisted PR planning metadata
4. if local PR planning state is complete, execution continues from the saved phase
5. if local state is missing, stale, or incomplete, recovery falls back to GitHub PR plan JSON artifacts

### 3. PR Plan Persistence

After each PR plan generation:

1. a markdown PR plan is written to the PRDs branch
2. a JSON PR plan is written to the PRDs branch
3. the JSON file serves as machine-readable recovery input
4. local thread state should reflect that PR planning has occurred

Remote files follow the pattern:

- `prds/consensusdevagent/prd-XXX-pr-plan.md`
- `prds/consensusdevagent/prd-XXX-pr-plan.json`

### 4. Disaster Recovery Reconstruction

If local state is lost or was saved before PR plans were recorded:

1. resume logic checks local state
2. if the phase indicates pre-PR-planning or `pr_plans_by_prd` is empty unexpectedly, the subsystem checks the PRDs branch
3. PR plan JSON files are read from GitHub
4. the PR plan graph is reconstructed from JSON
5. execution resumes from the recovered PR pipeline state instead of regenerating PRs

### 5. Operational Reset Path

If local thread state is irreparably bad:

1. operator may delete `state/threads/consensusdevagent.json`
2. restart the app
3. select the incomplete build thread if available
4. subsystem reconstructs recoverable planning state from GitHub PR plan JSON

This reset path relies on the remote PRDs branch still containing the JSON backup artifacts.

## Key Invariants

### Recovery and Resume

- Normal restart recovery is automatic at startup; no explicit resume command is required.
- Incomplete `ConsensusDevAgent` threads must be discoverable from persisted state.
- Resume must only occur after operator selection of the discovered incomplete thread.
- `director.resume()` is the entry point for resumed execution.

### State and Phase Consistency

- The local thread state file for this subsystem is `state/threads/consensusdevagent.json`.
- If PR plans exist, persisted state should not remain in a pre-plan phase such as `prd_gen`.
- If PR plans exist, the thread state should reflect the PR pipeline phase, e.g. `pr_pipeline`.
- PR plan count in local state must match expected generated PR plans for the PRDs already processed.

### Remote Backup Contract

- Every generated PR plan must produce both:
  - a human-readable markdown artifact
  - a machine-readable JSON artifact
- The JSON artifact is the recovery source of truth when local state is absent or stale.
- The PRDs branch must be retained if it contains JSON files required for reconstruction.

### Branch Hygiene

- Stale branches matching `forge-agent/build/consensusdevagent-*` should be removed to avoid CI noise and branch monitor confusion.
- `main` must be preserved.
- `forge-agent/build/consensusdevagent/prds` must be preserved if it contains JSON recovery artifacts.

### GitHub Safety and Platform Rules

- All GitHub operations must go through `GitHubTool`.
- No direct GitHub API access.
- No blind writes without SHA validation.
- Path validation is required before any write.
- Path traversal is forbidden.
- Generated code must never be directly executed.
- Credentials must never appear in logs or prompts.

## Failure Modes

### 1. Local State Saved Too Early

**Symptom**

- after restart, the agent shows `0 PRs done`
- execution begins regenerating PR specs from PR #1

**Likely Cause**

- local thread state was persisted before PR plan generation completed
- state still shows something like:
  - `"state": "prd_gen"`
  - empty `pr_plans_by_prd`

**Expected Handling**

- detect inconsistency between saved phase and remote PR plan artifacts
- inspect PRDs branch for `prd-XXX-pr-plan.json`
- reconstruct PR plan state from GitHub instead of regenerating

### 2. Local Thread State Missing

**Symptom**

- `state/threads/consensusdevagent.json` is absent, deleted, or corrupted

**Expected Handling**

- startup should still discover resumable work if sufficient metadata exists elsewhere, or resume should reconstruct from GitHub PR plan JSON once thread selection occurs
- recovery depends on the PRDs branch retaining the JSON artifacts

### 3. Recovery Artifacts Deleted

**Symptom**

- local state is missing or stale, and GitHub PR plan JSON files are also unavailable

**Impact**

- PR planning state cannot be reconstructed deterministically
- the system may have to regenerate planning work, risking duplication or divergence

**Prevention**

- preserve `forge-agent/build/consensusdevagent/prds` if it has JSON files

### 4. Branch Accumulation / Monitor Confusion

**Symptom**

- old build branches accumulate
- CI failures on stale branches obscure current status
- branch monitor behavior becomes noisy or misleading

**Expected Handling**

- delete stale `forge-agent/build/consensusdevagent-*` branches
- retain only the required branches called out in the runbook

### 5. Mid-Gate Backend Restart

**Symptom**

- backend restarts while awaiting gate approval

**Impact**

- gate state is lost
- pending approval does not auto-resolve on recovery

**Expected Handling**

- operator must explicitly re-approve
- subsystem must not infer or replay prior gate approval

### 6. GitHub Rate Limit or Access Failures

**Impact**

- recovery artifact reads or writes may fail
- state backup to PRDs branch may be delayed or interrupted

**Required Platform Behavior**

- use bounded retries only
- `403` primary limit: exponential backoff starting at 60s
- `429` secondary limit: respect `Retry-After` exactly
- use ETag caching on polling endpoints
- stop after max 3 attempts total

### 7. Unsafe Write Attempts

**Impact**

- corruption of repository state or security violations

**Required Handling**

- reject invalid paths
- reject path traversal
- reject writes without SHA context
- never bypass `GitHubTool`

## Dependencies

### Platform Dependencies

- Forge startup/bootstrap flow
- thread-state persistence layer
- `director.resume()` orchestration entry point
- terminal/UI prompt for incomplete-thread selection

### Storage Dependencies

- local filesystem state:
  - `state/threads/consensusdevagent.json`
- GitHub PRDs branch as remote recovery store:
  - `forge-agent/build/consensusdevagent/prds`

### Service Dependencies

- `GitHubTool` for all GitHub reads/writes
- branch monitoring infrastructure, affected by stale branch accumulation
- retry/backoff framework shared by GitHub and model-provider operations

### Policy Dependencies

This subsystem must conform to repository-wide operational and security rules, including:

- validate paths before any write
- never use direct GitHub API calls
- never retry indefinitely
- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- do not ignore `SECURITY_REFUSAL`

### Observability / Operator Dependencies

Operational inspection commonly relies on checking:

- `"state"` in `consensusdevagent.json`
- PR plan presence/count in local state
- presence of `prd-XXX-pr-plan.json` in the PRDs branch

These checks are diagnostic aids for validating whether the subsystem is in:

- pre-PR-planning
- recovered PR pipeline state
- stale local state requiring reconstruction