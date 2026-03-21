# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and executing the end-to-end build of the `ConsensusDevAgent` workstream across multiple PRDs and PRs, while preserving resumability across application restarts.

Its primary responsibilities are:

- maintain per-thread execution state for the `ConsensusDevAgent` build
- detect incomplete build threads at startup without requiring an explicit resume command
- present resumable build threads to the operator during normal startup
- resume execution through `director.resume()` after operator selection
- persist local thread state for in-progress execution
- persist PR plan artifacts to the GitHub `prds` branch as disaster-recovery backups
- reconstruct execution state from GitHub-backed PR plan JSON if local state is lost or stale
- prevent uncontrolled branch accumulation by relying on disposable build branches and operator cleanup guidance

Normal restart behavior is automatic. No `/resume`, `/continue`, or `/ledger resume` command is required. On startup, the agent bootstraps, scans for incomplete thread state, and prompts the operator to resume a known build thread or start fresh.

This subsystem therefore enforces continuity of a build thread across restarts, partial failures, and local state loss, with GitHub-hosted PR plan JSON serving as the authoritative recovery source when local state is insufficient.

---

## Component Boundaries

### In Scope

The subsystem includes:

- detection of incomplete `ConsensusDevAgent` build threads during startup
- local thread-state persistence under the workspace state directory
- resume-selection UX for incomplete builds
- transition into resumed execution via `director.resume()`
- persistence of PR planning artifacts for each PRD
- reconstruction of PR plan state from GitHub-hosted JSON artifacts
- operational assumptions around branch hygiene for `forge-agent/build/consensusdevagent-*`
- state inspection and recovery behavior for this specific thread type

### Out of Scope

The subsystem does **not** own:

- the general application bootstrap process beyond consuming its completion
- GUI shell behavior such as launching `ForgeAgent.app`
- implementation details of PRD generation or PR code generation themselves
- GitHub API access outside the platform-standard `GitHubTool`
- gate decision persistence across backend restarts
- automatic recovery of operator approvals after a backend restart
- indefinite retry loops or self-healing beyond bounded retry/error-handling patterns
- arbitrary branch retention policies outside documented operator runbook expectations

### External Interfaces

This subsystem interacts with:

- startup thread discovery logic
- `director.resume()` for continuation of a selected build thread
- local filesystem state under the thread-state directory
- GitHub `prds` branch artifacts for recovery
- GitHubTool for all GitHub operations
- branch monitor behavior indirectly, via branch naming and branch cleanup expectations

---

## Data Flow

### 1. Startup Discovery

On normal startup:

1. operator launches `ForgeAgent.app`
2. agent bootstraps
3. subsystem scans local thread-state storage for incomplete build threads
4. if an incomplete `ConsensusDevAgent` thread exists, the operator is shown a resumable entry such as:
   - thread name
   - PRD progress
   - PR progress
   - recency
   - task summary
5. operator selects the thread number to resume, or presses Enter to start a fresh build

This is automatic discovery. No explicit resume command is part of the normal flow.

### 2. Local State Read

The canonical local state file for this thread is:

- `.../state/threads/consensusdevagent.json`

The subsystem reads key fields such as:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

These fields determine whether the thread is still in PRD generation, has entered the PR pipeline, or has recoverable PR plan data.

### 3. Resume Handoff

After operator selection, control passes into:

- `director.resume()`

The resume path must restore the thread to the appropriate stage based on persisted state. If valid PR plan state already exists, execution should continue from the PR pipeline rather than regenerating plans.

### 4. PR Plan Persistence to GitHub

After each PR plan is generated, the subsystem writes two artifacts into the GitHub `prds` branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The markdown file is human-readable.  
The JSON file is machine-readable and is the recovery-critical backup.

### 5. Disaster Recovery Reconstruction

If local thread state is deleted, corrupted, or reflects an earlier phase than actual progress, the subsystem recovers by reading the GitHub-hosted PR plan JSON files and reconstructing the full PR plan state.

This is the defined recovery path when:

- local state is wiped
- local state shows `state: "prd_gen"` despite completed PR planning
- `pr_plans_by_prd` is empty locally but GitHub JSON backups exist

### 6. Branch Lifecycle Expectations

Build execution may create ephemeral branches under:

- `forge-agent/build/consensusdevagent-*`

These branches are not intended to accumulate indefinitely. Old branches should be removed per runbook guidance to avoid CI noise and branch-monitor confusion. The subsystem relies on fresh branch creation rather than long-term reuse of stale build branches.

---

## Key Invariants

### Resume Is Startup-Driven

Normal restart recovery is automatic at startup. The subsystem must not require a dedicated operator command to discover resumable `ConsensusDevAgent` threads.

### Operator Selection Precedes Resume

Even though discovery is automatic, resumption is operator-selected. The subsystem must not silently resume the wrong incomplete thread without explicit user choice from the startup prompt.

### Local Thread State Is Per-Thread and Durable

`consensusdevagent.json` is the local persistence unit for this build thread. It must reflect the thread’s current phase sufficiently for resume and diagnostics.

### GitHub PR Plan JSON Is the Recovery Backup

For each generated PR plan, the corresponding `.json` artifact in the `prds` branch is the disaster-recovery source of truth when local thread state is missing or stale.

### PR Pipeline State Must Dominate PRD Generation State Once Plans Exist

If PR plans exist, effective execution state must be consistent with `pr_pipeline`. A state file indicating `prd_gen` while PR plans already exist is stale/incomplete and must not cause blind regeneration.

### Regeneration Must Not Happen When Recoverable Plans Exist

If local state lacks `pr_plans_by_prd` but GitHub `prds` JSON files exist, the subsystem must reconstruct the plan rather than regenerate from PR #1.

### All GitHub Operations Use GitHubTool

No direct GitHub API calls are permitted. This includes recovery reads and artifact writes.

### GitHub Writes Must Be Validated

Before any write:

- validate destination path
- avoid blind writes without SHA where applicable
- respect repository safety rules

### Retries Are Bounded

Recovery, polling, and provider interactions must follow platform retry policy:

- no indefinite retries
- maximum 3 attempts total
- `403` primary rate-limit: exponential backoff starting at 60s
- `429` secondary rate-limit: respect `Retry-After`
- use ETag caching on polling endpoints

### Gates Do Not Auto-Resolve

If a backend restart occurs mid-gate:

- gate state is lost
- operator must re-approve
- no automatic restoration of prior approval is allowed
- no undo exists for gate decisions

### Security Constraints Always Apply

The subsystem must preserve platform-wide prohibitions, including:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no placing context in the system prompt
- no ignoring `SECURITY_REFUSAL`

---

## Failure Modes

### Local State Missing

**Symptom:** `consensusdevagent.json` does not exist.  
**Impact:** startup discovery may not show the incomplete local thread.  
**Recovery:** reconstruct from GitHub `prds/consensusdevagent/*-pr-plan.json` if artifacts exist; otherwise start fresh.

### Local State Stale Before PR Planning

**Symptom:** state shows:
- `"state": "prd_gen"`
- empty `pr_plans_by_prd`

but GitHub contains PR plan JSON files.

**Impact:** on restart, the system appears to have `0 PRs done` and starts regenerating specs from PR #1.  
**Required handling:** detect GitHub recovery artifacts and reconstruct the PR plan state instead of regenerating.

### Local Thread State Manually Wiped

**Symptom:** operator deletes the local thread-state file.  
**Impact:** local resume metadata is lost.  
**Recovery:** rely on GitHub JSON disaster-recovery artifacts; if absent, thread continuity cannot be restored.

### PRDS Branch Missing or Incomplete

**Symptom:** expected JSON files are absent from the `forge-agent/build/consensusdevagent/prds` branch or equivalent retained PRDS branch.  
**Impact:** disaster recovery cannot reconstruct full PR planning state.  
**Recovery:** only local state remains; if both local and GitHub recovery state are absent, restart from scratch.

### Excess Stale Build Branches

**Symptom:** many old `forge-agent/build/consensusdevagent-*` branches remain.  
**Impact:** CI failures accumulate and branch monitor behavior becomes noisy or misleading.  
**Recovery:** delete old branches; keep `main` and `forge-agent/build/consensusdevagent/prds` if it still contains JSON recovery files.

### Backend Restart During Gate

**Symptom:** process restarts while waiting for operator approval.  
**Impact:** gate state is lost.  
**Recovery:** operator must explicitly re-approve. The subsystem must not auto-resolve or infer approval from prior context.

### Rate Limiting / Provider Failure

**Symptom:** GitHub or model-provider operations fail with retryable errors.  
**Impact:** temporary inability to load, persist, poll, or continue.  
**Handling:** bounded retries only; on terminal failure, emit error state/card, gate as required, and require explicit operator action.

### Unsafe Write or Path Violation

**Symptom:** attempted write path is invalid, traverses outside expected repository scope, or lacks required safety checks.  
**Impact:** write must not proceed.  
**Handling:** fail closed; log and gate according to platform error-handling patterns.

---

## Dependencies

### Runtime Dependencies

- application bootstrap completion before startup thread discovery
- local filesystem access to thread-state storage
- `director.resume()` for resumed execution
- GitHubTool for all repository reads/writes related to recovery artifacts
- branch-monitor ecosystem, indirectly affected by branch accumulation

### Persistent Data Dependencies

- local thread state:
  - `state/threads/consensusdevagent.json`
- GitHub PRDS artifacts:
  - `prds/consensusdevagent/prd-XXX-pr-plan.md`
  - `prds/consensusdevagent/prd-XXX-pr-plan.json`

### Operational Dependencies

- operator startup flow must allow resume selection
- operator branch cleanup may be required to remove old `forge-agent/build/consensusdevagent-*` branches
- retained PRDS branch must not be deleted if it still contains recovery JSON files

### Policy Dependencies

- GitHub operations policy: GitHubTool only
- retry/backoff policy for provider and GitHub failures
- gate semantics: gates wait, do not auto-resolve, and lose state on restart
- security rules and forbidden-pattern enforcement across all file and GitHub operations