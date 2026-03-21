# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build orchestration subsystem responsible for driving a multi-PRD, multi-PR implementation thread for the `ConsensusDevAgent` workstream and recovering that thread across process restarts.

Its primary responsibilities are:

- Maintain thread-local execution state for the `ConsensusDevAgent` build pipeline.
- Detect incomplete build threads automatically during Forge startup.
- Offer resumable recovery without requiring an explicit resume command.
- Persist enough state locally and in GitHub to reconstruct progress after interruption.
- Continue execution from the correct pipeline stage, especially the PR-planning / PR-pipeline stages.
- Avoid duplicate or stale branch state that would interfere with branch monitoring and CI.

Normal restart behavior is automatic:

1. ForgeAgent boots.
2. Startup scans for incomplete build threads.
3. If `ConsensusDevAgent` has unfinished work, the operator is prompted to resume by selecting the thread number.
4. `director.resume()` is invoked for the selected thread.
5. Execution continues from persisted state.

No `/resume`, `/continue`, or `/ledger resume` command is part of the normal recovery path.

This subsystem is therefore not just task execution; it is the recovery-aware state manager for a specific build thread family.

## Component Boundaries

ConsensusDevAgent owns:

- The persisted thread state for the `consensusdevagent` build thread.
- Recovery detection for incomplete `ConsensusDevAgent` work at startup.
- Reconstruction of PR planning state from local thread state and GitHub-backed PRD/PR-plan artifacts.
- Progress accounting such as:
  - current pipeline `state`
  - PRD count
  - generated PR plans
  - completed PR count
- The naming/domain of `ConsensusDevAgent` thread artifacts, including:
  - local thread state file
  - `prds/consensusdevagent/*` recovery artifacts
  - build branches prefixed with `forge-agent/build/consensusdevagent-*`

ConsensusDevAgent does **not** own:

- Global app bootstrap.
- Generic prompt rendering or operator input collection.
- Direct GitHub API access.
- CI execution semantics.
- Gate decision persistence across backend restarts.
- Undo semantics for gate decisions.
- Arbitrary repository mutation outside validated Forge flows.

Operationally adjacent but outside this subsystem:

- **Forge bootstrap/runtime**: starts the app and surfaces incomplete threads.
- **Director**: performs `director.resume()` after operator selection.
- **GitHubTool**: all GitHub reads/writes must route through it; direct GitHub API usage is forbidden.
- **Consensus engine / model routing**: generation backend selection and retry logic.
- **Gate system**: gates wait for operator action and do not auto-resolve.

## Data Flow

### 1. Startup Recovery Detection

On normal startup:

1. ForgeAgent app launches.
2. Bootstrap completes.
3. Thread state store is scanned for incomplete threads.
4. If `consensusdevagent` thread state indicates unfinished work, startup displays a resume option such as:
   - agent name
   - PRD progress
   - PR completion count
   - age of the thread
5. Operator selects the thread.
6. `director.resume()` resumes execution from persisted state.

This is the canonical restart path.

### 2. Local State Persistence

Primary local state is stored in:

- `.../state/threads/consensusdevagent.json`

This file contains the execution snapshot used to determine:

- current pipeline `state`
- PRD generation status
- PR-plan presence
- PR pipeline readiness
- PR progress metadata

Operational inspection focuses on fields such as:

- `"state"`
- `"prd_count"`
- `"pr_plans"` / `"pr_plans_by_prd"`

Expected interpretation:

- If PR plans exist, `"state"` should typically be `pr_pipeline`.
- PR plan count should align with the expected PR count derived from PRDs.

### 3. GitHub-Backed Recovery Artifacts

After each PR plan is generated, two recovery artifacts are written to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Roles:

- `.md`: human-readable plan summary.
- `.json`: machine-readable disaster recovery backup.

If local thread state is lost or incomplete, the subsystem reconstructs planning state from the JSON artifacts in GitHub. This is the authoritative recovery path for PR plan reconstruction.

### 4. Resume Reconstruction Path

On resume, reconstruction proceeds conceptually as follows:

1. Read local `consensusdevagent.json`.
2. Determine current pipeline stage.
3. If local state is complete enough, continue directly.
4. If local state is missing or stale for PR plans:
   - enumerate `prds/consensusdevagent/*-pr-plan.json` in the GitHub PRDs branch
   - rebuild `pr_plans_by_prd` / equivalent in-memory planning state
   - transition back to PR pipeline execution
5. Continue from the next unfinished PR/PRD unit.

### 5. Branch Hygiene Interaction

Operational guidance requires deletion of stale branches matching:

- `forge-agent/build/consensusdevagent-*`

Except:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it still contains JSON files

This branch hygiene is required because stale branches:

- accumulate CI failures
- confuse branch monitoring
- are not needed for recovery if GitHub PRD JSON artifacts remain intact

The subsystem depends on clean branch state but does not itself define generic branch garbage collection policy for the whole platform.

## Key Invariants

1. **Normal restart requires no explicit resume command**
   - Recovery is initiated automatically at startup.
   - Resume is operator-selected from discovered incomplete threads.

2. **Thread state is keyed by the `consensusdevagent` thread identity**
   - Local persistence must map deterministically to `consensusdevagent.json`.
   - Recovery prompts must correspond to that persisted thread.

3. **PR plan JSON files are the disaster recovery source of truth for generated PR plans**
   - If local state is lost, recovery reconstructs from GitHub JSON artifacts.
   - Human-readable markdown alone is insufficient for full reconstruction.

4. **If PR plans exist, execution state should reflect PR pipeline readiness**
   - A state such as `prd_gen` with empty `pr_plans_by_prd` after PR plans were already generated indicates stale or prematurely saved state.

5. **All GitHub operations must go through GitHubTool**
   - Direct GitHub API calls are forbidden.
   - Writes must validate paths and must not be blind writes without SHA protection.

6. **Recovery must not duplicate work when durable artifacts already exist**
   - Existing PR-plan JSON artifacts must be used to reconstruct state instead of regenerating plans from scratch.

7. **Branch hygiene must preserve recovery artifacts**
   - Old `forge-agent/build/consensusdevagent-*` branches may be removed.
   - The PRDs branch must be preserved if it contains JSON recovery files.

8. **Retries are bounded**
   - Never retry indefinitely.
   - Max 3 attempts total.
   - Backend/provider-specific retry rules apply.

9. **Gate semantics are strict**
   - Gates never auto-resolve.
   - If the backend restarts mid-gate, gate state is lost and operator re-approval is required.
   - No undo on gate decisions.

10. **Security constraints are hard requirements**
    - No shell injection.
    - No credentials in logs.
    - No credentials in prompts.
    - No direct execution of generated code.
    - No path traversal.
    - No blind GitHub write.
    - No context in system prompt.
    - Must not ignore `SECURITY_REFUSAL`.

## Failure Modes

### Local thread state lost

Example:
- `consensusdevagent.json` is deleted or corrupted.

Effect:
- Normal local resume metadata is unavailable.

Recovery:
- Reconstruct PR plan state from `prds/consensusdevagent/*-pr-plan.json` in the GitHub PRDs branch.
- Resume from reconstructed PR pipeline state.

### Local state saved too early / stale state

Symptom:
- After restart, system reports `0 PRs done` and starts regenerating PRs from the beginning.

Diagnostic signature:
- `"state": "prd_gen"`
- `pr_plans_by_prd` empty or equivalent empty plan map

Cause:
- Local thread state persisted before PR plans were incorporated.

Recovery:
- Check GitHub PRD JSON artifacts.
- Rehydrate planning state from PR-plan JSON files.
- Transition to `pr_pipeline` rather than regenerating plans.

### Stale build branches interfere with monitoring

Symptom:
- Old CI failures and branch monitor confusion.

Cause:
- Accumulation of `forge-agent/build/consensusdevagent-*` branches.

Recovery:
- Delete stale branches.
- Preserve `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery artifacts.

### Backend restarts during a gate

Effect:
- Gate state is lost.

Required behavior:
- Do not auto-resolve.
- Require explicit operator re-approval.
- Do not assume prior approval survives restart.

### GitHub rate limiting or provider failures

Required handling:
- In `_claude_json`: retry after 10 seconds, then fall back to OpenAI.
- In `consensus.py`: retry with the other provider.
- Never exceed 3 total attempts.
- On `403` primary rate limits: exponential backoff starting at 60 seconds.
- On `429` secondary limits: respect `Retry-After` exactly.
- Use ETag caching on polling endpoints.

### Unsafe or invalid write attempts

Examples:
- path traversal
- blind writes without SHA
- direct GitHub API usage
- credential leakage
- generated code direct execution

Required handling:
- Stop immediately.
- Do not retry.
- Do not rephrase.
- Emit error card.
- Gate.
- Log full prompt context as required by platform policy.
- Require explicit operator override.

## Dependencies

ConsensusDevAgent depends on:

### Runtime / Orchestration
- ForgeAgent application bootstrap
- Incomplete-thread discovery during startup
- Director resume flow via `director.resume()`

### Persistence
- Local thread state storage under `state/threads/consensusdevagent.json`
- GitHub-backed PRD branch storage for durable PR-plan JSON artifacts

### GitHub Integration
- `GitHubTool` for all GitHub operations
- Path validation before any write
- SHA-aware writes only
- ETag caching for polling endpoints

### Generation / Consensus
- Consensus engine and provider routing
- `_claude_json` fallback behavior
- `consensus.py` alternate-provider retry behavior

### Operational Controls
- Gate system with explicit operator approval semantics
- CI / branch monitor ecosystem affected by branch naming and cleanup discipline

### Repository/Platform Policy
- Security checklist enforcement before every PR
- Forbidden-pattern enforcement
- Repository structure and critical file conventions
- Version management and CI routing rules where relevant to PR execution

This subsystem should be understood as a recovery-centric orchestration layer for the `ConsensusDevAgent` build thread, bounded by Forge runtime lifecycle, GitHubTool-mediated persistence, and strict platform safety and gate semantics.