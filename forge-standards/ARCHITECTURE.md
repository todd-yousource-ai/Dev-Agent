# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build thread subsystem responsible for planning and executing the end-to-end build of the `ConsensusDevAgent` workstream across PRDs and PRs, with restart-safe recovery.

Its core responsibilities are:

- maintain per-thread build state for the `ConsensusDevAgent` thread
- detect incomplete work automatically at agent startup
- allow operator selection of an incomplete thread for continuation
- resume execution without any explicit `/resume`, `/continue`, or `/ledger resume` command
- persist PR planning artifacts to both local thread state and GitHub
- reconstruct PR planning state from GitHub-backed JSON artifacts if local state is missing or stale
- continue the build pipeline from the last durable checkpoint, typically `pr_pipeline`

Operationally, normal recovery works as follows:

1. ForgeAgent starts
2. bootstrap completes
3. incomplete build threads are discovered automatically
4. operator selects the `ConsensusDevAgent` thread
5. `director.resume()` resumes the thread from persisted state

This subsystem exists to ensure that build progress for `ConsensusDevAgent` survives process restarts and local state loss, while preventing accidental duplicate planning or ambiguous branch state.

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- thread-level state for the `ConsensusDevAgent` build
- startup-time detection of incomplete `ConsensusDevAgent` threads
- resume selection and handoff into `director.resume()`
- PRD-to-PR planning progress tracking
- local persisted thread state, including fields such as:
  - `state`
  - `prd_count`
  - `pr_plans`
  - `pr_plans_by_prd`
- recovery from GitHub-hosted PR plan JSON artifacts
- use of the dedicated PRDs branch for durable machine-readable planning backups:
  - `forge-agent/build/consensusdevagent/prds`
- branch hygiene rules for `forge-agent/build/consensusdevagent-*`

### Out of Scope

ConsensusDevAgent does not own:

- app bootstrap itself
- general thread orchestration outside the `ConsensusDevAgent` thread
- direct GitHub API usage
- gate persistence across backend restarts
- automatic operator approval replay after restart
- arbitrary branch recovery outside the documented naming pattern
- direct execution of generated code

### Explicit External Boundaries

- **Director**: performs the actual resume entrypoint via `director.resume()`
- **GitHubTool**: the only allowed mechanism for GitHub operations
- **GitHub PRDs branch**: durable backup store for PR plan JSON/Markdown artifacts
- **Local filesystem thread state**: fast local checkpoint storage, not the sole source of truth after PR plans are published

## Data Flow

### 1. Startup Detection

On normal startup, no recovery command is required.

The subsystem participates in automatic incomplete-thread discovery:

- ForgeAgent boots
- thread state is scanned
- if an incomplete `ConsensusDevAgent` thread exists, the operator is shown a resumable entry such as:
  - thread name
  - PRD progress
  - PR completion count
  - age of last activity

The operator selects the thread by number, after which control passes to `director.resume()`.

### 2. Local State Read

The subsystem reads local thread state from the thread state file for `ConsensusDevAgent`, operationally located at:

- `.../state/threads/consensusdevagent.json`

Important fields include:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

This local file is used to determine the current pipeline stage and expected resume point.

### 3. PR Plan Persistence

After each PR plan is generated, the subsystem persists artifacts to the GitHub PRDs branch as two files per PRD:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

Semantics:

- `.md` is the human-readable summary
- `.json` is the machine-readable recovery artifact

The JSON artifact is the disaster-recovery source used to reconstruct planning state if local thread state is incomplete, deleted, or stale.

### 4. Resume Reconstruction

If local state indicates planning has not been persisted correctly—for example:

- `state` is still `prd_gen`
- `pr_plans_by_prd` is empty

—but GitHub contains PR plan JSON files, the subsystem reconstructs the full PR planning state from the GitHub PRDs branch.

This recovery path prevents unnecessary regeneration of PR plans after restart.

### 5. Branch Hygiene

Operationally, stale branches matching:

- `forge-agent/build/consensusdevagent-*`

should be deleted, except for:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it contains JSON files

This is not cosmetic. Old branches accumulate CI failures and interfere with branch monitoring. The subsystem assumes branch space is kept clean enough that newly created branches reflect current work rather than historical noise.

## Key Invariants

### Automatic Recovery Requires No Command

Normal restart recovery must be startup-driven.

Invariant:

- no `/resume`
- no `/continue`
- no `/ledger resume`

Recovery is initiated by startup discovery plus operator selection.

### Local State Is Resumable but Not Solely Authoritative

The local thread state file is a checkpoint, but once PR plan JSON files exist in GitHub, those JSON files form the durable recovery backup for PR planning.

Invariant:

- PR planning recovery must be possible even if local thread state is lost

### GitHub Operations Must Go Through GitHubTool

All GitHub reads/writes relevant to recovery and artifact persistence must go through `GitHubTool`.

Invariant:

- never use the GitHub API directly

### Writes Must Be Path-Validated

Before any write, paths must be validated.

Invariant:

- no path traversal
- no unsafe or unvalidated repository writes

### Blind GitHub Writes Are Forbidden

GitHub writes must not ignore repository object identity.

Invariant:

- no write without SHA-aware safety
- no blind overwrite of remote content

### PR Plan JSON Is the Disaster-Recovery Artifact

For each generated PR plan, the machine-readable JSON artifact must exist or be treated as missing durability.

Invariant:

- `.json` recovery artifacts are required for reconstruction
- Markdown alone is insufficient for machine recovery

### Gates Never Auto-Resolve

If the backend restarts during a gate, gate state is lost.

Invariant:

- gates wait for explicit operator action
- approval does not survive restart unless reissued
- there is no undo for gate decisions

### Error Handling Is Bounded

Retry behavior is constrained.

Invariant:

- maximum 3 attempts total
- no infinite retries
- provider/tool-specific retry policies must be respected
- hard-stop conditions must emit an error card, gate, and log full prompt context
- operator override is required after terminal refusal conditions

### Security Constraints Always Apply

The subsystem must not violate repository-wide forbidden patterns.

Invariant:

- no shell injection
- no credential in logs
- no credential in prompts
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt
- no ignoring `SECURITY_REFUSAL`

## Failure Modes

### Local Thread State Missing

Symptom:

- `consensusdevagent.json` does not exist, was wiped, or is unreadable

Effect:

- local resume position is unavailable

Recovery:

- inspect GitHub PRDs branch for `prds/consensusdevagent/*-pr-plan.json`
- reconstruct PR planning state from JSON artifacts
- continue from reconstructed state

### Local State Stale or Saved Too Early

Symptom:

- restart shows `0 PRs done`
- agent begins regenerating PR specs from the beginning
- local state has:
  - `"state": "prd_gen"`
  - empty `pr_plans_by_prd`

Cause:

- state checkpoint was saved before PR plans were captured locally

Recovery:

- read GitHub-backed PR plan JSON artifacts
- rebuild `pr_plans_by_prd`
- advance effective resume stage to the PR pipeline instead of regenerating plans

### PRDs Branch Missing or Incomplete

Symptom:

- expected JSON recovery artifacts are absent

Effect:

- full disaster recovery from GitHub is not possible

Impact:

- subsystem may need to regenerate missing PR plans
- recovery fidelity drops to whatever remains in local thread state

### Stale Build Branch Accumulation

Symptom:

- multiple old `forge-agent/build/consensusdevagent-*` branches remain
- CI failures and branch monitor noise accumulate

Effect:

- operator confusion
- monitoring ambiguity
- increased chance of resuming from or inspecting the wrong branch set

Mitigation:

- delete old build branches
- retain only `main` and `forge-agent/build/consensusdevagent/prds` when it still contains JSON files

### Backend Restart During Gate

Symptom:

- process restarts while waiting on an approval gate

Effect:

- gate state is lost
- approval does not auto-replay

Required behavior:

- do not auto-resolve
- require operator to re-approve explicitly

### GitHub Rate Limiting or Provider Failure

Relevant constraints:

- `403` primary limit: exponential backoff starting at 60s
- `429` secondary limit: respect `Retry-After` exactly
- polling endpoints must use ETag caching
- retries are capped at 3 total attempts

Effect:

- delayed persistence or delayed recovery reads

Required behavior:

- bounded retries only
- fail closed with explicit surfaced error when retry budget is exhausted

### Terminal Model/Tool Refusal

Symptom:

- hard refusal or unrecoverable generation error

Required behavior:

- stop
- do not retry indefinitely
- do not silently rephrase around the refusal
- emit error card
- gate
- log full prompt context
- require explicit operator override

## Dependencies

### Runtime Dependencies

- ForgeAgent startup/bootstrap flow
- thread discovery and incomplete-build listing
- `director.resume()` for resumed execution
- local filesystem access for thread state persistence
- GitHub-backed branch storage for PR plan artifacts

### Tooling Dependencies

- `GitHubTool` for all GitHub operations
- consensus/generation stack as defined by repository-wide consensus engine usage
- document store access where generation requires repository context documents

### Repository/Operational Dependencies

- branch naming and retention conventions for `forge-agent/build/consensusdevagent-*`
- preserved `forge-agent/build/consensusdevagent/prds` branch when JSON artifacts exist
- operator runbook procedures for:
  - startup resume
  - state inspection
  - local state wipe
  - stale-branch cleanup
  - diagnosis of PR regeneration loops

### Critical Documents and Policy Dependencies

This subsystem is constrained by repository-wide guidance in:

- `AGENTS`
- repository identity and structure documents
- consensus engine usage guidance
- document store usage guidance
- GitHub operation rules
- error handling patterns
- CI routing
- version management
- security checklist
- critical files guidance
- forbidden patterns list

These policies are architectural constraints, not optional implementation guidance.