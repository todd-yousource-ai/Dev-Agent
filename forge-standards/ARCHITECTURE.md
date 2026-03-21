# Architecture - ConsensusDevAgent

## What This Subsystem Does

`ConsensusDevAgent` is the long-running build thread subsystem responsible for orchestrating multi-PRD, multi-PR implementation work under Forge. It manages resumable execution of a build thread, persists progress locally and to GitHub, and reconstructs execution state after restart or partial local state loss.

Its primary responsibilities are:

- Track the lifecycle of a named build thread (`ConsensusDevAgent`) across agent restarts.
- Persist thread state locally under the Forge workspace thread state store.
- Persist PR planning artifacts to a dedicated Git branch as disaster-recovery state.
- Detect incomplete build threads automatically at startup.
- Offer operator-driven resume selection for incomplete builds.
- Rehydrate PR execution state from persisted local thread state and, if needed, from GitHub-backed PR plan JSON artifacts.
- Continue execution from the recovered state via `director.resume()`.

Normal restart behavior is automatic. No explicit `/resume`, `/continue`, or `/ledger resume` command is required. On startup, the agent bootstraps, scans for incomplete thread state, presents resumable threads, and resumes the selected thread.

This subsystem is specifically concerned with build-thread continuity and PR-plan recoverability. It is not the consensus engine itself, not the document store itself, and not a generic GitHub client.

## Component Boundaries

### In Scope

- Detection of incomplete `ConsensusDevAgent` thread state at startup.
- Presentation of resumable thread candidates to the operator.
- Resume dispatch into the director (`director.resume()`).
- Local persistence of thread state, including state machine stage and PR planning metadata.
- Recovery of PR plans from GitHub `prds` branch artifacts when local state is incomplete or lost.
- Operational expectations for branch hygiene relevant to this thread’s recovery behavior.

### Out of Scope

- LLM consensus generation logic.
- Document generation semantics for PRDs beyond storing/recovering produced artifacts.
- Direct GitHub API usage; all GitHub operations must go through `GitHubTool`.
- CI execution and CI policy decisions.
- Gate approval persistence; gate state is explicitly not durable across backend restart.
- General-purpose branch management beyond the operational runbook guidance for this thread family.

### External Interfaces

- **Startup/bootstrap flow**: discovers incomplete thread state.
- **Director**: receives resume invocation.
- **Local state store**: thread JSON file for execution state.
- **GitHubTool**: reads/writes PR plan artifacts in the `prds` branch.
- **Operator terminal UI**: selects which incomplete thread to resume.

## Data Flow

### 1. Normal Startup and Resume Discovery

On application startup:

1. `ForgeAgent.app` launches.
2. Agent bootstraps; expected startup is approximately 45 seconds.
3. The subsystem scans persisted thread state for incomplete builds.
4. If an incomplete `ConsensusDevAgent` thread exists, the operator is shown a resume menu similar to:

   - thread name
   - PRD completion count
   - completed PR count
   - age
   - build description

5. Operator selects the thread by number.
6. The system invokes `director.resume()` for that thread.

There is no command-based resume path for standard recovery.

### 2. Local State Persistence

Primary local state is stored as a thread JSON file:

- `.../state/threads/consensusdevagent.json`

This file contains, at minimum, state machine data and PR-planning metadata used to continue execution. Operationally important fields include:

- `state`
- `prd_count`
- `pr_plans` / `pr_plans_by_prd`

Expected interpretation:

- If PR plans exist, `state` should be `pr_pipeline`.
- PR plan count should match the expected generated PR count for the current PRD set.

### 3. GitHub-Backed Recovery State

After each PR plan is generated, two artifacts are written to the GitHub `prds` branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The `.json` artifact is the authoritative disaster-recovery backup for PR planning. If local thread state is missing, stale, or was saved before PR plans were recorded, the subsystem reconstructs the PR plan state from these JSON files during resume.

This creates a two-tier persistence model:

- **Local thread JSON**: fast path for normal resume.
- **GitHub PR plan JSON**: recovery path for local-state loss or pre-persistence races.

### 4. Recovery After Partial State Loss

A known failure mode is restart after local state persisted an earlier phase, e.g.:

- `state: "prd_gen"`
- `pr_plans_by_prd: {}`

In that case, the agent may incorrectly appear to have `0 PRs done` and start regenerating PRs. Recovery proceeds by inspecting the GitHub `prds` branch for existing PR plan JSON files and reconstructing the PR plan state from them.

### 5. Operational Reset Path

If thread state must be forcibly reset:

- Delete branches matching `forge-agent/build/consensusdevagent-*`
- Keep:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files
- Remove local thread state file:
  - `.../state/threads/consensusdevagent.json`

This reset intentionally preserves GitHub PRD/PR-plan recovery artifacts while removing corrupted or stale local execution state and obsolete build branches.

## Key Invariants

1. **Normal restart requires no explicit resume command**  
   Resume discovery is part of startup. The operator only selects a discovered thread.

2. **Incomplete thread detection must occur on startup**  
   If resumable thread state exists, it must be surfaced to the operator before a fresh build path is chosen.

3. **`ConsensusDevAgent` thread state is durable locally**  
   Execution state must be persisted under the thread state store as JSON.

4. **PR plan JSON in GitHub is the disaster-recovery source of truth for generated PR plans**  
   If local thread state is absent or incomplete, recovery must reconstruct from `prds/consensusdevagent/*.json`.

5. **Human-readable and machine-readable PR plan artifacts are written together**  
   Each generated PR plan produces both `.md` and `.json`; the `.json` is required for machine recovery.

6. **Local state machine phase must align with available PR plan data**  
   If PR plans exist, thread `state` should be `pr_pipeline`, not `prd_gen`.

7. **Branch hygiene matters for correctness of monitoring and recovery operations**  
   Old `forge-agent/build/consensusdevagent-*` branches must be removed because they create CI noise and confuse branch monitoring.

8. **GitHub operations must flow through `GitHubTool` only**  
   No direct GitHub API calls are permitted inside this subsystem.

9. **Writes must be path-validated before execution**  
   This applies to local and repository-targeted writes.

10. **Gate decisions are not durable across backend restart**  
    If the backend restarts during a gate, gate state is lost and requires re-approval by the operator. Gates never auto-resolve.

11. **Retry behavior is bounded**  
    Never retry indefinitely; maximum 3 attempts total, subject to provider-specific retry policy.

## Failure Modes

### Stale or Incomplete Local Thread State

**Symptom**
- Restart shows `0 PRs done`
- Agent begins regenerating PR specs from the beginning

**Cause**
- Local thread state was saved before PR plans were persisted
- Example:
  - `state = "prd_gen"`
  - `pr_plans_by_prd = {}`

**Handling**
- Inspect local thread JSON
- Inspect GitHub `prds` branch for `prd-*-pr-plan.json`
- Reconstruct PR plans from GitHub-backed JSON artifacts
- Resume from reconstructed pipeline state rather than regenerating

### Lost Local Thread State

**Symptom**
- Thread JSON missing
- Normal local resume impossible

**Cause**
- File deletion, workspace corruption, manual wipe

**Handling**
- Use GitHub `prds` branch JSON artifacts as backup source
- Rebuild in-memory PR plan state on resume
- If intentionally resetting, preserve `forge-agent/build/consensusdevagent/prds` when JSON artifacts exist

### Branch Accumulation / Monitor Confusion

**Symptom**
- Excess CI failures
- Incorrect or noisy branch-monitor behavior

**Cause**
- Old `forge-agent/build/consensusdevagent-*` branches retained

**Handling**
- Delete stale branches in that namespace
- Preserve only `main` and the `prds` branch when it contains recovery JSON

### Backend Restart During Gate

**Symptom**
- Previously pending approval no longer exists after restart

**Cause**
- Gate state is not durably persisted

**Handling**
- Do not auto-resolve or infer approval state
- Re-present gate for explicit operator action

### Provider / Tool Failures

The wider subsystem adheres to repository-level error handling patterns:

- In `_claude_json`: retry after 10 seconds, then fall back to OpenAI
- In `consensus.py`: retry with the other provider
- Maximum 3 attempts total
- `403` on primary provider: exponential backoff starting at 60 seconds
- `429` secondary rate limit: honor `Retry-After` exactly
- ETag caching on polling endpoints

For hard refusal or security refusal cases:

- Stop immediately
- Do not retry
- Do not rephrase
- Emit error card
- Gate
- Log full prompt context
- Require explicit operator override

## Dependencies

### Runtime Dependencies

- **ForgeAgent bootstrap/runtime**
  - Provides application startup and prompt lifecycle.
- **Director**
  - Executes `resume()` for selected incomplete threads.
- **Local filesystem state store**
  - Stores thread execution JSON under `state/threads/`.
- **GitHubTool**
  - Sole allowed mechanism for GitHub reads/writes.
- **Operator terminal UI**
  - Presents resumable thread menu and accepts thread selection.

### Data Dependencies

- **Local thread state**
  - `state/threads/consensusdevagent.json`
- **GitHub PRD/PR-plan artifacts**
  - `prds/consensusdevagent/prd-*-pr-plan.md`
  - `prds/consensusdevagent/prd-*-pr-plan.json`

### Repository-Level Constraints Applied Here

- Validate paths before any write.
- Never perform blind GitHub writes without SHA protection.
- Never log credentials.
- Never place credentials in prompts.
- Never directly execute generated code.
- Prevent path traversal.
- Do not bypass `GitHubTool`.
- Do not ignore `SECURITY_REFUSAL`.
- Do not place context in the system prompt.

### Operational Dependencies

- Branch hygiene in `forge-agent/build/consensusdevagent-*`
- Preservation of `forge-agent/build/consensusdevagent/prds` when recovery JSON exists
- Manual inspection capability for local thread JSON during incident response

This subsystem is therefore best understood as the resumable execution and recovery layer for the `ConsensusDevAgent` build thread: it binds startup discovery, local state persistence, GitHub-backed PR-plan durability, and operator-selected resume into a single continuity mechanism.