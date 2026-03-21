# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the Forge build thread responsible for generating and executing the end-to-end build plan for the `ConsensusDevAgent` product thread. Its primary responsibilities are:

- detect resumable incomplete work at agent startup
- restore thread-local execution state for the `ConsensusDevAgent` build
- reconstruct PR planning state from GitHub-backed artifacts when local state is incomplete or lost
- continue the PR pipeline from the last durable checkpoint
- persist machine-readable recovery artifacts for each PRD/PR plan pair
- maintain branch hygiene for `forge-agent/build/consensusdevagent-*` branches so stale branches do not interfere with monitoring or CI interpretation

This subsystem is restart-oriented: normal recovery is automatic and requires no explicit `/resume`, `/continue`, or `/ledger resume` command. On startup, Forge enumerates incomplete build threads and presents them for operator selection. Selecting the `ConsensusDevAgent` thread invokes the internal resume path (`director.resume()` in the product flow) and continues from persisted state.

Operationally, the subsystem supports two persistence layers:

1. **Local thread state**
   - canonical runtime checkpoint during normal execution
   - stored as a thread JSON file, e.g. `state/threads/consensusdevagent.json`

2. **GitHub-backed PRD/PR-plan artifacts**
   - durable disaster-recovery backup
   - stored on the `forge-agent/build/consensusdevagent/prds` branch when JSON files exist
   - includes:
     - `prds/consensusdevagent/prd-001-pr-plan.md`
     - `prds/consensusdevagent/prd-001-pr-plan.json`

The JSON artifacts are the recovery source of truth when local thread state is missing or stale with respect to generated PR plans.

## Component Boundaries

ConsensusDevAgent owns:

- thread-specific lifecycle for the `ConsensusDevAgent` build
- identification of incomplete build work for this product thread
- serialization/deserialization of thread execution state
- PRD-to-PR-plan recovery for this thread
- use of GitHub PRD-plan JSON files as disaster recovery inputs
- branch namespace management for `forge-agent/build/consensusdevagent-*`

ConsensusDevAgent does **not** own:

- global application bootstrap
- operator UI shell beyond exposing resumable thread metadata
- generic gate semantics
- direct GitHub API access
- direct consensus provider retry policy outside shared consensus abstractions
- arbitrary code execution of generated content

It operates within the following platform constraints:

- all GitHub operations must go through `GitHubTool`; direct GitHub API calls are forbidden
- all write paths must be validated before write
- blind GitHub writes without SHA are forbidden
- generated code must never be directly executed
- shell injection, path traversal, credential leakage, and prompt credential inclusion are forbidden
- gates never auto-resolve; they wait for explicit operator action
- if the backend restarts during a gate, gate state is lost and must be re-approved by an operator
- no undo exists for gate decisions

## Data Flow

### 1. Startup and thread discovery

On normal application startup:

1. `ForgeAgent.app` launches
2. bootstrap completes
3. the runtime scans thread state for incomplete builds
4. if a `ConsensusDevAgent` thread is incomplete, it is listed as resumable
5. operator selects the thread
6. resume flow begins

Important property: recovery is startup-driven. There is no separate normal-case resume command path.

### 2. Local state restore

The subsystem first loads local thread state from the thread JSON file:

- expected file: `state/threads/consensusdevagent.json`
- inspected fields include:
  - `state`
  - `prd_count`
  - `pr_plans` / `pr_plans_by_prd`

The local state determines whether the thread is:

- still generating PRDs
- in PR pipeline execution
- incomplete but resumable
- inconsistent and requiring reconstruction from GitHub artifacts

A valid resumed PR pipeline should reflect:
- `state == "pr_pipeline"` when PR plans already exist
- PR plan count consistent with the expected PR count derived from generated planning artifacts

### 3. GitHub-backed recovery

After each PR plan is generated, the subsystem persists two artifacts on the PRDs branch:

- human-readable markdown plan
- machine-readable JSON plan

The JSON file is the durable backup used for disaster recovery.

If local state is missing, deleted, or stale—for example:
- local thread state was wiped
- local state says `state == "prd_gen"`
- `pr_plans_by_prd == {}`
- but PR plan JSON files already exist on GitHub

then the subsystem must reconstruct PR pipeline state by reading the JSON artifacts from the PRDs branch and rebuilding in-memory/local execution state from them.

This boundary is critical: GitHub PR-plan JSON is the durable recovery substrate for already-generated plans.

### 4. Branch lifecycle

The subsystem creates build branches automatically as work proceeds. Old branches matching:

- `forge-agent/build/consensusdevagent-*`

must be deleted during operational cleanup because stale branches:
- accumulate CI failures
- confuse branch monitoring
- can make current thread progress ambiguous

The following branches are retained:
- `main`
- `forge-agent/build/consensusdevagent/prds` if it still contains JSON recovery files

### 5. Manual reset path

A full local reset is supported by deleting the thread state file:

- `state/threads/consensusdevagent.json`

After deletion, recovery should rely on GitHub-backed PR-plan JSON if present. This enables stateless local recovery while preserving generated planning work.

## Key Invariants

1. **Normal restart does not require an explicit resume command**
   - Recovery is initiated through startup detection of incomplete threads.

2. **Incomplete `ConsensusDevAgent` builds must be discoverable as resumable threads**
   - The operator must be able to select the thread from startup recovery UI.

3. **Thread state is durable locally but not solely relied upon**
   - Local thread JSON is the primary execution checkpoint, but not the only recovery source.

4. **PR plan JSON on GitHub is the disaster recovery backup**
   - If local state is lost or stale, these files must be sufficient to reconstruct the PR pipeline.

5. **If PR plans exist, thread state must not regress to pre-plan generation behavior**
   - In particular, a resumed thread must not regenerate PRs from scratch when corresponding PR-plan JSON already exists.

6. **`state == "pr_pipeline"` is the expected state once PR plans exist**
   - If `state == "prd_gen"` and `pr_plans_by_prd` is empty while JSON artifacts exist remotely, local state is inconsistent.

7. **GitHub writes must be safe and validated**
   - no direct API usage
   - no path traversal
   - no blind writes without SHA
   - all writes go through `GitHubTool`

8. **Operational branch cleanup must preserve recovery artifacts**
   - delete stale `forge-agent/build/consensusdevagent-*` branches
   - preserve `forge-agent/build/consensusdevagent/prds` if it contains JSON files

9. **Gates are durable only in operator workflow, not across backend restarts**
   - restart during a gate loses gate state
   - operator must explicitly re-approve
   - gates never auto-resolve

10. **Retry behavior is bounded**
    - no infinite retries
    - max 3 attempts total where shared retry policy applies

## Failure Modes

### Lost local thread state

**Symptom**
- `state/threads/consensusdevagent.json` is missing or manually deleted

**Effect**
- local checkpoint is unavailable

**Expected handling**
- inspect GitHub PR-plan JSON artifacts on the PRDs branch
- reconstruct the PR pipeline from those machine-readable files
- resume from reconstructed state instead of restarting planning

### Stale local state causing PR regeneration

**Symptom**
- on restart, the agent reports `0 PRs done`
- begins generating PR specs from PR #1 again

**Likely diagnosis**
- local state persisted before PR plans were written
- thread JSON shows:
  - `state == "prd_gen"`
  - `pr_plans_by_prd == {}`

**Expected handling**
- verify whether PR-plan JSON files already exist on GitHub
- if they do, rebuild local state from GitHub artifacts
- do not treat the absence of local `pr_plans_by_prd` as authoritative if remote JSON exists

### Stale branch accumulation

**Symptom**
- CI failures attached to old branches
- branch monitor confusion
- ambiguous active branch state

**Expected handling**
- delete old `forge-agent/build/consensusdevagent-*` branches
- retain `main`
- retain `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery data

### Backend restart during a gate

**Symptom**
- process restarts while awaiting approval

**Effect**
- gate state is lost

**Expected handling**
- require explicit operator re-approval
- never auto-resolve the gate
- no implicit continuation past approval boundaries

### Provider/API failure in dependent systems

This subsystem inherits platform-wide error handling constraints:

- `_claude_json`: retry after 10s, then fall back to OpenAI
- `consensus.py`: retry with the other provider
- max 3 attempts total
- 403 primary rate limits: exponential backoff starting at 60s
- 429 secondary limits: respect `Retry-After` exactly
- ETag caching on polling endpoints

If a hard failure persists:
- stop
- do not endlessly retry
- emit an error card / gate per platform behavior
- log full prompt context where required by platform policy
- require explicit operator override

## Dependencies

### Runtime/platform dependencies

- Forge application bootstrap and startup recovery flow
- director resume path for incomplete thread continuation
- thread-state persistence layer under `state/threads/*.json`

### Storage dependencies

- local filesystem for thread state
- GitHub branch storage for PRD/PR-plan artifacts

### GitHub integration

- `GitHubTool` for all GitHub operations
- SHA-aware writes only
- validated repository paths before writes

### Planning/recovery artifacts

- PRD plan markdown files for operator readability
- PRD plan JSON files for machine reconstruction and disaster recovery

### Shared platform policies inherited by this subsystem

- consensus engine retry/fallback behavior
- document store usage conventions
- CI routing behavior
- version management rules
- security checklist and forbidden-pattern enforcement

### Security-critical inherited constraints

The subsystem must remain compliant with repository-wide forbidden patterns:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write without SHA
- no context embedded in the system prompt
- no ignoring `SECURITY_REFUSAL`

In short, ConsensusDevAgent is a restart-safe, thread-scoped build orchestration subsystem whose core architectural guarantee is: generated PR planning work for the `ConsensusDevAgent` thread must survive normal restarts and local state loss through GitHub-backed JSON recovery artifacts, while all mutation paths remain bounded, validated, and operator-safe.