# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for orchestrating generation and execution of a multi-PRD, multi-PR development pipeline for the `ConsensusDevAgent` build target.

Its core responsibilities are:

- maintain durable progress for an in-flight build thread named `ConsensusDevAgent`
- automatically detect incomplete work at ForgeAgent startup
- offer resumable continuation of prior work without requiring any explicit recovery command
- persist intermediate planning artifacts locally and to GitHub
- reconstruct lost local planning state from GitHub-backed PR plan JSON artifacts
- coordinate progression from PRD generation into PR planning and downstream PR execution

Operationally, recovery is **startup-driven**, not command-driven. On normal restart:

1. `ForgeAgent.app` launches
2. the agent bootstraps
3. incomplete build threads are detected automatically
4. the operator selects the thread to resume
5. `director.resume()` is invoked for that thread

There is no normal `/resume`, `/continue`, or `/ledger resume` command path for this subsystem.

This subsystem is specifically concerned with **thread lifecycle, resumability, and PRD/PR plan continuity** for the `ConsensusDevAgent` build. It is not the general-purpose GitHub client, consensus engine, or document store itself.

---

## Component Boundaries

### Inside this subsystem

The ConsensusDevAgent subsystem owns:

- build-thread identity for `ConsensusDevAgent`
- local thread state persistence
- incomplete-thread detection on startup
- presentation of resumable thread choices to the operator
- transition into resumed execution via `director.resume()`
- tracking high-level state such as:
  - current thread `state`
  - PRD counts
  - PR plan presence/count
- reconstruction of PR planning state from GitHub-backed JSON artifacts when local state is incomplete or lost
- operational expectations around branch hygiene for this build target

### Outside this subsystem

The subsystem does **not** own:

- direct GitHub API access  
  - all GitHub operations must go through `GitHubTool`
- consensus provider implementations
- document store implementation
- CI execution/routing logic
- version management policy
- gate approval persistence across backend restarts
- direct execution of generated code
- arbitrary filesystem writes outside validated paths
- security policy definition beyond enforcing consumption of platform rules

### Explicit boundaries with adjacent platform capabilities

#### GitHub operations
All GitHub reads/writes used by this subsystem must be mediated by `GitHubTool`. The subsystem may request:

- branch inspection
- artifact existence checks
- PR plan artifact reads/writes
- branch cleanup workflows

It must not bypass `GitHubTool` or perform blind writes without SHA protection.

#### Operator interaction
The subsystem may prompt the operator to select a resumable thread at startup. It does not silently resume without selection when multiple or resumable threads are presented.

#### Recovery semantics
The subsystem supports:

- automatic detection of incomplete threads
- operator-selected resume
- state reconstruction from GitHub PR plan JSON backups

It does not support:

- command-triggered normal restart recovery
- automatic restoration of lost gate approvals after backend restart

---

## Data Flow

### 1. Startup and incomplete-thread discovery

On normal startup:

1. `ForgeAgent.app` launches.
2. Forge bootstrap completes.
3. thread state files are inspected for incomplete build threads.
4. if `consensusdevagent` has incomplete work, the operator is shown a resumable entry such as:
   - build name
   - PRD completion count
   - PR completion count
   - relative recency
   - build description
5. operator selects the thread.
6. the subsystem resumes through `director.resume()`.

Primary local state location:

- `/Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

### 2. Local state tracking

The local thread state file stores the resumable execution state, including at minimum:

- thread `state`
- PRD count/progress
- PR plan structures
- downstream pipeline progress metadata

Operational inspection focuses on fields such as:

- `"state"`
- `"prd_count"`
- `"pr_plans"` or `pr_plans_by_prd`

Expected interpretation:

- if PR plans exist, state should typically be `pr_pipeline`
- PR plan count should align with expected PR count per PRD

### 3. PR plan persistence to GitHub

After each PR plan is generated, two artifacts are written to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Roles of these artifacts:

- `.md`: human-readable plan table
- `.json`: machine-readable source of truth for disaster recovery

The JSON artifact is the durable backup used to reconstruct planning state if local thread state is lost or persisted too early.

### 4. Recovery from incomplete local state

If the subsystem restarts and local state indicates an earlier stage such as `prd_gen`, with missing `pr_plans_by_prd`, but GitHub contains PR plan JSON artifacts, recovery proceeds by reading the JSON artifacts from the PRDs branch and reconstructing the full PR planning state.

This is the intended disaster recovery path when:

- local thread state was saved before PR plans were incorporated
- local thread state was deleted
- local thread state is otherwise incomplete but GitHub backups exist

### 5. Operational reset path

If local thread state must be wiped manually, the file:

- `/Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json`

may be removed, after which recovery depends on GitHub-backed PR plan JSON artifacts and fresh startup detection behavior.

Branch hygiene also affects correct behavior. Old branches matching:

- `forge-agent/build/consensusdevagent-*`

should generally be deleted, while retaining:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it contains JSON files

This prevents stale CI failures and branch-monitor ambiguity from interfering with resumed execution.

---

## Key Invariants

### Recovery invariants

- Normal restart recovery is automatic at startup.
- No explicit resume command is required for normal restart.
- Incomplete build detection must occur before offering a fresh build path.
- Resume enters through `director.resume()` after operator selection.

### State invariants

- `consensusdevagent.json` is the authoritative local thread-state snapshot.
- If PR plans exist locally, thread state should reflect a post-PRD planning phase, typically `pr_pipeline`.
- PR plan counts must remain consistent with the expected PR decomposition per PRD.
- Local state may be reconstructed from GitHub JSON backups if local state is missing or stale.

### Persistence invariants

- After each PR plan generation, both human-readable and machine-readable artifacts must be written.
- The `.json` PR plan artifact is the disaster-recovery source of truth.
- Recovery correctness depends on preserving the PRDs branch containing those JSON artifacts.

### GitHub invariants

- All GitHub operations go through `GitHubTool`; never use the GitHub API directly.
- Validate paths before any write.
- Never perform blind GitHub writes without SHA.
- Use ETag caching on polling endpoints.
- Respect platform retry/backoff behavior:
  - max 3 attempts total
  - `403` primary rate limits: exponential backoff starting at 60s
  - `429` secondary limits: respect `Retry-After` exactly

### Safety and security invariants

The subsystem must not violate repository-wide forbidden patterns, including:

- shell injection
- credential in log
- credential in prompt
- direct execution of generated code
- path traversal
- blind GitHub write
- context in system prompt
- ignoring `SECURITY_REFUSAL`

### Gate invariants

- Gates never auto-resolve.
- Gates wait for operator action.
- If backend restarts mid-gate, gate state is lost and must be re-approved by the operator.
- There is no undo for gate decisions.

---

## Failure Modes

### 1. Local thread state missing

**Symptom**
- `consensusdevagent.json` does not exist.

**Impact**
- local resumable metadata is unavailable

**Expected handling**
- inspect GitHub PRDs branch for `prd-*-pr-plan.json`
- reconstruct planning state from JSON artifacts if present
- otherwise begin fresh

### 2. Local state persisted too early

**Symptom**
- after restart, system reports `0 PRs done` and regenerates from PR #1
- local JSON shows:
  - `"state": "prd_gen"`
  - empty `pr_plans_by_prd`

**Impact**
- subsystem appears to regress to pre-plan phase

**Expected handling**
- treat GitHub PR plan JSON files as source of truth
- reload and reconstruct full PR plan state
- resume pipeline from reconstructed plan, not from empty local structures

### 3. PRDs branch deleted or missing JSON artifacts

**Symptom**
- local state lost and no backup plan JSON exists remotely

**Impact**
- disaster recovery path is unavailable

**Expected handling**
- build may need to restart planning generation from scratch
- operational runbook should preserve `forge-agent/build/consensusdevagent/prds` when it contains JSON files

### 4. Stale build branches accumulate

**Symptom**
- old `forge-agent/build/consensusdevagent-*` branches remain
- CI failures accumulate
- branch monitor becomes confused

**Impact**
- incorrect monitoring signals and operational ambiguity

**Expected handling**
- delete stale branches matching that prefix
- retain only `main` and the PRDs branch if it contains recovery JSON files

### 5. Backend restart during gate

**Symptom**
- process restarts while awaiting approval

**Impact**
- gate state is lost

**Expected handling**
- do not auto-resolve or infer approval
- require explicit operator re-approval

### 6. GitHub rate limiting or transient failures

**Symptom**
- `403` primary or `429` secondary rate limits
- transient provider/network failures

**Impact**
- delayed artifact reads/writes or polling

**Expected handling**
- apply bounded retries only
- obey backoff and `Retry-After`
- never retry indefinitely

### 7. Security refusal / unsafe generation path

**Symptom**
- generated action or request violates security constraints

**Impact**
- unsafe write, execution, or disclosure risk

**Expected handling**
- stop immediately
- do not retry or rephrase automatically
- emit error card
- gate
- log full prompt context
- require explicit operator override

---

## Dependencies

### Required platform dependencies

#### Director
Used to resume an incomplete build thread via `director.resume()` after operator selection.

#### Thread state store
Provides local persistence for build-thread execution state, including:

- lifecycle phase
- PRD progress
- PR plan metadata

#### GitHubTool
Mandatory interface for all GitHub operations, including:

- reading PR plan backups
- writing PR plan artifacts
- checking branch/file existence
- performing SHA-safe writes

#### Document store
Provides repository and build context documents used during generation and resume flows.

#### Consensus engine
Used by the broader build pipeline for generation tasks. This subsystem depends on it indirectly for PRD/PR plan creation but does not own provider-specific implementation.

### Operational dependencies

#### PRDs branch retention
Recovery depends on preserving:

- `forge-agent/build/consensusdevagent/prds`

when it contains machine-readable PR plan JSON backups.

#### Branch cleanup discipline
Reliable monitoring depends on deleting stale branches matching:

- `forge-agent/build/consensusdevagent-*`

except explicitly preserved branches.

#### Startup path
Normal recovery depends on the standard ForgeAgent startup path being used, because incomplete-thread discovery is performed during bootstrap.

### Cross-cutting repository rules this subsystem must honor

- read critical repository documents before modifying behavior
- follow repository structure and core loop expectations
- route CI through platform routing rules
- follow version management policy
- apply the security checklist before every PR
- respect documented error handling and fallback rules for provider calls

---