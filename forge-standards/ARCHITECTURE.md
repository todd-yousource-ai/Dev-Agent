# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the repository build workflow for the `ConsensusDevAgent` target. It maintains resumable thread state across application restarts, reconstructs execution state when possible from GitHub-backed artifacts, and advances work through the PRD → PR-plan → PR pipeline.

Its core responsibilities are:

- detect an incomplete `ConsensusDevAgent` build thread during Forge startup
- present that thread as resumable without requiring an explicit recovery command
- restore thread execution via `director.resume()` after operator selection
- persist local per-thread state for in-progress execution
- persist PR-plan artifacts to GitHub as durable recovery state
- reconstruct missing local execution state from GitHub PR-plan JSON when local state is lost or stale
- continue execution from the correct pipeline stage rather than restarting generation unnecessarily

Normal recovery is automatic at startup. There is no `/resume`, `/continue`, or `/ledger resume` command for standard restart behavior.

## Component Boundaries

This subsystem includes:

- thread discovery for incomplete `ConsensusDevAgent` builds at startup
- local thread-state storage and inspection for `consensusdevagent.json`
- resume selection UX for incomplete build threads
- mapping restored state into `director.resume()`
- PR-plan persistence and recovery logic for `prds/consensusdevagent/*.json` and corresponding markdown summaries
- state-machine interpretation of build progress, including whether execution is in PRD generation or PR pipeline phases

This subsystem does **not** include:

- general app bootstrap behavior beyond the point that resumable threads are listed
- direct GitHub API usage outside the platform GitHub toolchain
- CI execution semantics
- gate auto-resolution
- approval persistence across backend restarts
- arbitrary branch cleanup policy beyond operational guidance
- generated code execution
- direct mutation of unrelated agent thread state

Operationally adjacent but outside subsystem logic:

- deleting stale branches such as `forge-agent/build/consensusdevagent-*`
- manually wiping local thread state
- manual GitHub inspection during disaster recovery
- operator re-approval after backend restart during gate wait

## Data Flow

### 1. Startup discovery

On normal application startup:

1. Forge bootstraps.
2. The system scans local thread state for incomplete builds.
3. If an incomplete `ConsensusDevAgent` thread exists, it is displayed in the startup resume menu with summarized progress, such as:
   - PRD count completed
   - PR count completed
   - recency metadata
   - thread description

No explicit recovery command is required.

### 2. Resume selection

After the operator selects the thread by number:

1. the selected incomplete thread is loaded
2. the subsystem invokes `director.resume()`
3. execution resumes from the persisted workflow state

The resume entrypoint assumes the thread represents an incomplete build, not a fresh build request.

### 3. Local state persistence

The primary local state file is the thread-state JSON:

- `.../state/threads/consensusdevagent.json`

This file records the workflow state machine and generated planning artifacts, including fields used operationally to inspect status:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

Operationally important interpretation:

- `state: "pr_pipeline"` indicates PR plans exist and the build should proceed through PR execution
- `state: "prd_gen"` with empty `pr_plans_by_prd` indicates state was saved before PR plans were generated, and naive restart may incorrectly regenerate work

### 4. GitHub-backed durable recovery state

After each PR plan is generated, the subsystem writes two artifacts to the GitHub PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Semantics:

- `.md` is the human-readable plan summary
- `.json` is the machine-readable recovery source of truth for PR-plan reconstruction

These JSON artifacts are the disaster-recovery backup when local thread state is lost, wiped, or stale.

### 5. Reconstruction on resume

If local state is incomplete or missing, the subsystem must reconstruct plan state from GitHub PR-plan JSON artifacts.

Expected reconstruction behavior:

1. inspect local thread state
2. if local state indicates pre-plan generation but GitHub contains PR-plan JSON artifacts
3. read the JSON artifacts from the PRDs branch
4. rebuild the in-memory/local plan graph
5. transition execution to the correct post-plan stage
6. resume PR pipeline instead of regenerating PR plans from scratch

This recovery path is required to prevent repeated regeneration after restart.

## Key Invariants

### Automatic restart recovery

- Normal restart recovery is automatic.
- No explicit resume command is required for standard startup recovery.
- Incomplete threads must be discoverable from startup state and presentable to the operator.

### Single thread identity

- The `ConsensusDevAgent` build thread is represented by a stable local thread-state file:
  - `consensusdevagent.json`
- Resume behavior must bind to that thread identity rather than infer a new build.

### Durable PR-plan recovery

- For every generated PR plan, a machine-readable JSON artifact must be written to the PRDs branch.
- GitHub PR-plan JSON is the recovery backup if local thread state is unavailable.
- Resume logic must prefer reconstructing completed plan work over regenerating it.

### Correct state-machine interpretation

- `state` must reflect the current lifecycle phase.
- If PR plans exist, the thread must not remain logically treated as pure `prd_gen`.
- `pr_pipeline` is the expected stage once PR plans exist and PR execution can proceed.

### No blind writes

All GitHub operations must go through `GitHubTool`. Never use the GitHub API directly.

For any GitHub write:

- validate paths before write
- do not perform blind writes without SHA protection
- preserve branch correctness

### Safety and refusal invariants

The subsystem must honor repository-wide safety rules:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt
- do not ignore `SECURITY_REFUSAL`

### Gate behavior

- gates never auto-resolve
- if backend restarts mid-gate, gate state is lost
- operator must explicitly re-approve
- there is no undo on gate decisions

ConsensusDevAgent may resume build state after restart, but it must not assume gate approvals survived restart.

## Failure Modes

### Local state lost

Example: `consensusdevagent.json` is deleted or corrupted.

Impact:

- startup may fail to show accurate progress
- resume may not know current PR-plan inventory

Required behavior:

- reconstruct from GitHub PR-plan JSON if available
- restore the plan graph and continue from the PR pipeline

### Local state stale or saved too early

Symptom:

- after restart, the system shows `0 PRs done`
- begins regenerating `PR #1`
- local state shows:
  - `state: "prd_gen"`
  - empty `pr_plans_by_prd`

Cause:

- state snapshot was persisted before PR-plan generation was reflected locally

Required behavior:

- detect mismatch between local state and GitHub PR-plan artifacts
- rebuild from GitHub artifacts
- avoid duplicate regeneration

### Missing GitHub recovery artifacts

If local state is lost and PR-plan JSON files were never persisted or are unavailable:

- full reconstruction is not possible
- the subsystem may need to regenerate plans
- operator may need to inspect repository state manually

This is a true degradation mode; GitHub JSON artifacts are the intended disaster-recovery mechanism.

### Stale build branches accumulating

Operational symptom:

- old `forge-agent/build/consensusdevagent-*` branches accumulate
- CI failures and branch monitoring become noisy/confusing

Impact:

- not a state-machine corruption issue, but degrades observability and branch routing clarity

Operational mitigation:

- delete stale `forge-agent/build/consensusdevagent-*` branches
- keep `main`
- keep `forge-agent/build/consensusdevagent/prds` if it contains JSON files

### Backend restart during gate wait

Impact:

- build thread may resume
- gate approval state is lost
- automatic continuation through the gate is forbidden

Required behavior:

- stop at gate boundary
- require explicit operator re-approval

### Upstream API/tooling errors

Repository-wide error handling requirements apply:

- do not retry indefinitely
- max 3 attempts total
- for `_claude_json`: retry after 10s, then fall back to OpenAI
- in `consensus.py`: retry with the other provider
- `403` primary rate/permission behavior: exponential backoff starting at 60s
- `429` secondary behavior: respect `Retry-After` exactly
- use ETag caching on polling endpoints

For hard refusal cases:

- stop
- do not retry
- do not rephrase
- emit error card
- gate
- log full prompt context
- require explicit operator override

## Dependencies

### Runtime/platform dependencies

- Forge application startup/bootstrap
- director resume orchestration via `director.resume()`
- local filesystem state store for thread JSON
- startup UI/CLI thread selection prompt

### Persistence dependencies

- local thread-state file:
  - `state/threads/consensusdevagent.json`
- GitHub PRDs branch persistence for recovery artifacts
- machine-readable PR-plan JSON under:
  - `prds/consensusdevagent/`

### Tooling dependencies

- `GitHubTool` for all GitHub reads/writes
- document-store and repository-context loading patterns defined by the repository
- consensus/provider failover mechanisms described in repository guidance

### Repository policy dependencies

ConsensusDevAgent operates under repository-wide architectural rules documented in the repo, including:

- AGENTS guidance
- repository identity and structure constraints
- core loop requirements
- consensus engine usage
- document store usage
- GitHub operation rules
- CI routing
- version management
- security checklist
- critical files guidance
- forbidden patterns list

These policies are not optional; this subsystem must conform to them while implementing resumable build-thread execution and recovery.