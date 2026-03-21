# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and executing the end-to-end build of the `ConsensusDevAgent` target across PRDs and PRs, while preserving recoverable progress across application restarts.

Its core responsibilities are:

- Detect an incomplete `ConsensusDevAgent` build thread on Forge startup.
- Present resumable build threads to the operator without requiring a manual resume command.
- Rehydrate local execution state from persisted thread state and, if necessary, reconstruct PR planning state from GitHub-backed PRD plan artifacts.
- Continue execution at the correct pipeline phase, especially the PR pipeline phase.
- Persist machine-readable PR plan outputs to the dedicated GitHub PRDs branch as disaster-recovery state.
- Avoid re-running already planned or completed work when valid persisted state exists.

Normal recovery behavior is automatic at startup:

1. Operator launches `ForgeAgent.app`.
2. Forge bootstraps.
3. The system scans for incomplete build threads.
4. If an incomplete `ConsensusDevAgent` thread exists, it is shown in the startup resume menu.
5. Operator selects the thread by number.
6. `director.resume()` continues execution from persisted state.

No `/resume`, `/continue`, or `/ledger resume` command is required for normal restarts.

## Component Boundaries

This subsystem includes:

- Detection of incomplete `ConsensusDevAgent` thread state at startup.
- Presentation of resumable thread metadata to the operator.
- Resume orchestration via `director.resume()`.
- Local thread-state consumption from:
  - `state/threads/consensusdevagent.json`
- Recovery of PR plan state from GitHub-backed artifacts in the PRDs branch.
- Continuation of the PR pipeline using recovered `pr_plans` / `pr_plans_by_prd` state.

This subsystem does not include:

- General-purpose command parsing for resume operations.
- Manual operator recovery commands for normal restart.
- Direct GitHub API usage outside the platform GitHub abstraction.
- Branch cleanup policy execution itself, except insofar as stale branches affect recoverability and monitoring.
- Persistence semantics for unrelated agent threads.

Related but external responsibilities:

- Startup/bootstrap UX belongs to the Forge application shell.
- GitHub operations belong to `GitHubTool`; all GitHub interactions must go through that tool.
- Consensus generation, document loading, CI routing, gate handling, and version management are separate subsystems, though their outputs may participate in the overall build thread.

Operational boundary notes:

- Old branches matching `forge-agent/build/consensusdevagent-*` are considered disposable and should be deleted operationally.
- `main` must be kept.
- `forge-agent/build/consensusdevagent/prds` must be kept if it contains JSON files, because those files serve as recovery artifacts.
- Deleting local thread state is a destructive local reset:
  - `state/threads/consensusdevagent.json`

## Data Flow

### 1. Startup detection

On normal startup, Forge scans persisted thread state for incomplete builds.

Primary local state source:

- `state/threads/consensusdevagent.json`

If an incomplete thread exists, the UI presents:

- thread name
- PRD progress
- PR progress
- age / recency
- operator choice to resume or start fresh

### 2. Resume selection

When the operator selects the `ConsensusDevAgent` thread from the startup menu, the director invokes resume flow:

- `director.resume()`

Resume is selection-based from detected thread state, not command-driven.

### 3. Local state inspection and phase selection

The subsystem reads the local thread JSON and determines the pipeline phase from fields such as:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

Expected interpretation:

- If PR plans exist, `state` should be `pr_pipeline`.
- PR plan count should match expected PR count per PRD.
- If `state` is earlier, such as `prd_gen`, and `pr_plans_by_prd` is empty, then PR planning state was not successfully persisted locally before restart.

### 4. GitHub-backed PR-plan recovery

After each PR plan is generated, two artifacts are written to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The `.md` file is human-readable.
The `.json` file is the authoritative machine-readable recovery artifact.

If local thread state is missing, stale, or was saved before PR planning completed, the subsystem must reconstruct plan state from the JSON artifacts in the PRDs branch and resume from reconstructed planning data rather than regenerate from scratch.

### 5. Continuation of execution

After state rehydration, the subsystem resumes the build at the correct point in the pipeline, typically:

- PR planning continuation, or
- PR execution from existing plans

The subsystem must prefer recovered persisted plan state over speculative regeneration.

## Key Invariants

1. **Normal restart requires no explicit resume command**
   - Recovery is automatic at startup.
   - Resume is initiated by selecting a detected incomplete thread.

2. **Local thread state is the first recovery source**
   - `state/threads/consensusdevagent.json` is the canonical local checkpoint.

3. **GitHub PR-plan JSON artifacts are the disaster-recovery backup**
   - If local state is lost or incomplete, PR plans must be reconstructed from the PRDs branch JSON files.

4. **PR pipeline state must be internally consistent**
   - If PR plans exist, thread `state` should be `pr_pipeline`.
   - PR plan counts must align with expected PR count per PRD.

5. **Recovery must not silently discard prior progress**
   - Existing PR plans on GitHub must be reused for reconstruction.
   - The agent must not reset to `0 PRs done` when valid persisted PR plan artifacts exist.

6. **PRDs branch preservation is mandatory for recovery**
   - `forge-agent/build/consensusdevagent/prds` must be retained if it contains JSON recovery files.

7. **GitHub access is mediated**
   - All GitHub operations go through `GitHubTool`.
   - Never use the GitHub API directly.

8. **Writes must be path-safe and version-safe**
   - Validate paths before any write.
   - No blind GitHub writes without SHA.
   - No path traversal.

9. **Retry behavior is bounded**
   - Never retry indefinitely.
   - Maximum 3 attempts total.
   - Provider/tool-specific retry rules must be respected.

10. **Gate state is not durable across backend restarts**
    - Gates never auto-resolve.
    - If backend restarts mid-gate, gate state is lost.
    - Operator must re-approve.
    - No undo on gate decisions.

## Failure Modes

### Local thread state missing

Example:
- `state/threads/consensusdevagent.json` was deleted or never written.

Effect:
- Local resume metadata may be unavailable or incomplete.

Expected handling:
- Recover PR planning state from GitHub PRDs branch JSON artifacts if they exist.
- Reconstruct execution context sufficiently to continue without regenerating completed planning work.

### Local thread state stale or saved too early

Symptom:
- On restart, agent shows `0 PRs done` and starts regenerating PR #1.

Diagnostic signature:
- `state` is `prd_gen`
- `pr_plans_by_prd` is empty `{}`

Effect:
- Local checkpoint reflects a pre-PR-planning phase even though PR plans may already exist remotely.

Expected handling:
- Inspect GitHub PRDs branch for `*-pr-plan.json`.
- Rehydrate `pr_plans` / `pr_plans_by_prd` from those artifacts.
- Transition resume state to the PR pipeline rather than regenerate plans.

### PRDs recovery branch removed or corrupted

Effect:
- Disaster-recovery source is unavailable.
- Recovery falls back to whatever local state remains.

Operational implication:
- Deleting `forge-agent/build/consensusdevagent/prds` when it contains JSON files destroys the authoritative remote recovery backup.

### Stale build branches accumulate

Effect:
- CI failures accumulate.
- Branch monitor becomes noisy or misleading.
- Operator may confuse obsolete build branches with active recovery state.

Operational expectation:
- Delete branches matching `forge-agent/build/consensusdevagent-*`.
- Preserve `main`.
- Preserve `forge-agent/build/consensusdevagent/prds` if it contains JSON files.

### Backend restart during gate

Effect:
- Gate state is lost.
- In-flight approval context does not auto-resume.

Expected handling:
- Do not auto-resolve.
- Require explicit operator re-approval.

### Tool/provider transient failures

Relevant constraints:
- Retry after 10s then fall back to OpenAI in `_claude_json`.
- In `consensus.py`, retry with the other provider.
- Maximum 3 attempts total.
- `403` primary rate limits: exponential backoff starting at 60s.
- `429` secondary rate limits: respect `Retry-After` exactly.
- Use ETag caching on polling endpoints.

### Security or policy refusal

Effect:
- Operation must stop rather than self-heal by prompt mutation or uncontrolled retries.

Required behavior:
- Stop.
- Do not retry indefinitely.
- Do not rephrase automatically.
- Emit error card.
- Gate.
- Log full prompt context.
- Require explicit operator override.

## Dependencies

### Required platform dependencies

- **Forge startup/runtime**
  - Provides bootstrap, prompt availability, and incomplete-thread discovery UX.

- **Director**
  - Executes resume orchestration via `director.resume()`.

- **Local thread state store**
  - Stores per-thread checkpoint data at:
    - `state/threads/consensusdevagent.json`

- **GitHubTool**
  - Required for all GitHub reads/writes.
  - Must be used for PRDs branch artifact persistence and recovery reads.

### Required persisted artifacts

- **Local checkpoint**
  - `state/threads/consensusdevagent.json`

- **Remote PR plan artifacts**
  - `prds/consensusdevagent/prd-###-pr-plan.md`
  - `prds/consensusdevagent/prd-###-pr-plan.json`

### Cross-cutting policy dependencies

- Path validation before any write.
- No direct GitHub API usage.
- No blind GitHub writes without SHA.
- Retry ceilings and rate-limit handling.
- Gate durability rules.
- Security forbiddens, including:
  - shell injection
  - credential in log
  - credential in prompt
  - direct execution of generated code
  - path traversal
  - blind GitHub write
  - context in system prompt
  - ignoring `SECURITY_REFUSAL`

### Operational dependencies

- Branch hygiene to prevent stale branch accumulation.
- Preservation of the PRDs branch as the recovery source of truth when local state is absent or inconsistent.