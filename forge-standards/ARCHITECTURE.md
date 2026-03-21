# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge build-thread subsystem responsible for driving a multi-PRD, multi-PR implementation workflow for the `ConsensusDevAgent` product thread.

Its responsibilities are:

- maintain durable per-thread execution state for an in-progress build
- detect and offer recovery of incomplete builds automatically at startup
- resume execution through `director.resume()` after operator selection
- generate and track PRD-level PR plans
- persist recovery artifacts both locally and in GitHub
- reconstruct execution state from GitHub-backed PR plan JSON when local thread state is incomplete or lost
- coordinate branch hygiene expectations for this thread family

This subsystem is not the generic startup shell, not the global director, and not GitHub transport itself. It is the thread-specific state and recovery surface for the `ConsensusDevAgent` build pipeline.

Operationally, normal restart requires no explicit resume command. On agent startup, Forge scans thread state, identifies incomplete `ConsensusDevAgent` work, presents it in the startup menu, and resumes only if the operator selects that thread.

## Component Boundaries

### Inside this subsystem

- thread identity and state for `ConsensusDevAgent`
- local persisted thread file:
  - `workspace/<user>/state/threads/consensusdevagent.json`
- state machine progression relevant to PRD generation and PR pipeline execution
- PR plan tracking, including `pr_plans` / `pr_plans_by_prd`
- recovery-time inspection of local state
- reconstruction from GitHub PR plan JSON backups
- branch namespace conventions for this thread:
  - `forge-agent/build/consensusdevagent-*`
  - retained PRD branch:
    - `forge-agent/build/consensusdevagent/prds` when it contains JSON artifacts

### Outside this subsystem

- Forge application bootstrap and prompt rendering
- global incomplete-thread discovery mechanism
- `director.resume()` implementation
- GitHub API transport and authentication
- CI execution and branch monitor implementation
- code generation internals for PR contents
- operator policy for manual cleanup beyond documented runbook steps

### Explicit non-responsibilities

ConsensusDevAgent does **not**:

- require `/resume`, `/continue`, or `/ledger resume` for normal restart
- auto-resume without operator selection from the incomplete-thread menu
- directly call the GitHub API; all GitHub operations must go through `GitHubTool`
- assume gate decisions survive backend restarts
- auto-resolve gates or undo gate decisions

## Data Flow

### 1. Startup discovery

On normal startup:

1. Operator launches `ForgeAgent.app`
2. Forge bootstraps, typically in ~45 seconds
3. startup logic scans persisted thread state
4. if an incomplete `ConsensusDevAgent` thread exists, Forge shows it in the incomplete-build list
5. operator selects the thread number to resume
6. `director.resume()` is invoked for that thread

There is no command-driven resume path required for this normal recovery flow.

### 2. Local state persistence

The primary local state artifact is:

```text
.../state/threads/consensusdevagent.json
```

This file stores thread execution state, including at minimum:

- thread state marker, e.g. `"state"`
- PRD count metadata, e.g. `"prd_count"`
- PR plan metadata, e.g. `"pr_plans"` or `pr_plans_by_prd`

This local JSON is the immediate source of truth during normal execution and restart detection.

### 3. PR plan generation persistence to GitHub

After each PR plan is generated, the subsystem persists two artifacts to the GitHub PRDs branch:

```text
prds/consensusdevagent/prd-001-pr-plan.md
prds/consensusdevagent/prd-001-pr-plan.json
```

Semantics:

- `.md` file: human-readable summary/table
- `.json` file: machine-readable recovery artifact

The JSON file is the disaster-recovery backup. If local thread state is missing, stale, or saved before PR plan generation completed, resume logic can reconstruct the plan set from these GitHub artifacts.

### 4. Recovery and reconstruction path

If restart finds inconsistent local state, the subsystem must distinguish between:

- genuinely incomplete planning
- lost or stale local state despite completed PR plan generation

Known case:

- local state shows `"state": "prd_gen"`
- `pr_plans_by_prd` is empty

This indicates the state snapshot predates PR plan generation. In that case, recovery should inspect GitHub-backed `prds/consensusdevagent/*.json` files and rebuild the in-memory/local plan representation from those persisted artifacts.

### 5. Branch lifecycle expectations

Operational runbook guidance defines branch hygiene:

- delete stale branches matching:
  - `forge-agent/build/consensusdevagent-*`
- keep:
  - `main`
  - `forge-agent/build/consensusdevagent/prds` if it contains JSON files

Rationale: stale branches accumulate CI failures and confuse branch monitoring; the agent can create fresh working branches automatically.

## Key Invariants

### Recovery invariants

- normal restart is automatic at startup; no explicit resume command is required
- incomplete `ConsensusDevAgent` work must be discoverable from persisted thread state
- resume requires operator selection from the startup menu
- if local state is unavailable or stale, GitHub PR plan JSON is the recovery source

### Persistence invariants

- local thread state must exist as a single durable JSON file per thread identity
- after each PR plan generation, corresponding `.md` and `.json` artifacts must be written to the PRDs branch
- PR plan JSON in GitHub must be sufficient to reconstruct full PR planning state for the thread

### State-machine invariants

- `"state"` must reflect actual execution phase
- if PR plans exist, expected state should be `pr_pipeline`
- PR plan count must match expected PR count per PRD
- `pr_plans_by_prd` must not be empty once PR plans have been generated and persisted

### GitHub operation invariants

- all GitHub operations go through `GitHubTool`; never use the GitHub API directly
- validate paths before any write
- never perform blind GitHub writes without SHA
- use ETag caching on polling endpoints
- retry behavior is bounded:
  - max 3 attempts total
  - `_claude_json`: retry after 10s, then fall back to OpenAI
  - `consensus.py`: retry with the other provider
- rate limiting behavior must be respected:
  - `403` primary: exponential backoff starting at 60s
  - `429` secondary: respect `Retry-After` exactly

### Safety invariants

The subsystem must preserve repository-wide forbidden-pattern constraints:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write without SHA
- no context in system prompt
- no ignoring `SECURITY_REFUSAL`

### Gate invariants

- gates never auto-resolve
- gates wait for operator action
- if backend restarts mid-gate, gate state is lost and operator must re-approve
- there is no undo for gate decisions

## Failure Modes

### 1. Lost local thread state

Symptom:

- `consensusdevagent.json` missing or manually wiped

Effect:

- startup may fail to detect prior local progress from disk alone

Recovery:

- inspect GitHub PRD JSON artifacts in the PRDs branch
- reconstruct PR plan state from `prds/consensusdevagent/*.json`
- recreate or resave local thread state

### 2. Stale local state causes PR regeneration

Symptom:

- after restart, agent shows `0 PRs done`
- execution restarts at “Generating spec for PR #1...”

Likely cause:

- local state saved before PR plans were generated
- `"state": "prd_gen"`
- `pr_plans_by_prd` is empty

Recovery:

- verify corresponding PR plan JSON exists in GitHub
- rebuild PR planning state from GitHub backup
- transition back to the correct pipeline phase rather than regenerating from scratch

### 3. Excess stale branches

Symptom:

- CI failures accumulate on historical branches
- branch monitor becomes noisy or misleading

Cause:

- old `forge-agent/build/consensusdevagent-*` branches retained indefinitely

Recovery:

- delete stale branches in the namespace
- preserve `main`
- preserve `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery artifacts

### 4. Mid-gate backend restart

Symptom:

- pending approval state disappears after restart

Effect:

- gate state is not durable across backend restarts

Required behavior:

- do not auto-resolve or infer approval
- operator must explicitly re-approve

### 5. Transport or provider retry exhaustion

Symptom:

- repeated provider or GitHub failures

Required behavior:

- do not retry indefinitely
- stop after max 3 attempts
- emit error/gate behavior per subsystem conventions
- preserve enough context for operator recovery

## Dependencies

### Runtime dependencies

- Forge application startup/bootstrap sequence
- incomplete-thread discovery and resume menu
- `director.resume()` for continuation of thread execution
- local filesystem persistence for thread JSON state
- GitHub-backed PRDs branch for disaster recovery artifacts

### Platform/service dependencies

- `GitHubTool` for all GitHub reads/writes
- consensus/provider routing as defined by repository standards
- branch monitoring and CI systems, indirectly affected by branch lifecycle hygiene

### Repository-policy dependencies

This subsystem depends on and must comply with repository-wide architecture rules captured in the documented guidance, including:

- all GitHub ops go through `GitHubTool`
- validate paths before any write
- bounded retry policies
- explicit gate handling semantics
- security forbidden patterns
- no direct execution of generated code

### Critical persisted artifacts

- local:
  - `state/threads/consensusdevagent.json`
- remote:
  - `prds/consensusdevagent/prd-*-pr-plan.md`
  - `prds/consensusdevagent/prd-*-pr-plan.json`

These artifacts define the practical recovery boundary of the subsystem: local JSON is the primary live state, while GitHub PR plan JSON is the durable recovery backup for plan reconstruction.