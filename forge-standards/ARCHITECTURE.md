# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the complete implementation workflow for the `ConsensusDevAgent` target within Forge.

Its core responsibilities are:

- detect and resume incomplete `ConsensusDevAgent` build threads on startup
- persist thread progress locally and reconstruct it from GitHub-backed artifacts when local state is incomplete or lost
- generate and track PRD-to-PR planning state
- drive the PR pipeline for the build
- expose resumable operational state to the director/runtime layer

This subsystem is designed for automatic recovery during normal restarts. A manual resume command is not required. On startup, Forge scans for incomplete build threads and presents them for operator selection. Resumption then proceeds through the director path (`director.resume()`), using persisted thread state.

Recovery model:

1. ForgeAgent boots
2. incomplete thread(s) are discovered automatically
3. operator selects the thread
4. subsystem resumes from saved state
5. if local state is insufficient, GitHub-backed PR plan JSON artifacts are used to reconstruct planning state

The subsystem therefore treats GitHub PRD/PR-plan artifacts as durable recovery data, not just output.

## Component Boundaries

ConsensusDevAgent is bounded to build-thread lifecycle management for the `ConsensusDevAgent` target.

It includes:

- thread discovery and identification for incomplete `ConsensusDevAgent` work
- local thread-state persistence and loading
- resume/recovery logic for normal restart
- PRD progress tracking
- PR plan tracking (`pr_plans`, `pr_plans_by_prd`)
- reconstruction of PR planning state from GitHub PRD-plan JSON files
- coordination with the director/runtime to continue execution from the correct phase

It does not include:

- app bootstrap itself
- generic thread-selection UI beyond supplying resumable thread metadata
- direct GitHub API usage outside the platform GitHub abstraction
- CI execution or branch-monitor policy
- gate auto-resolution
- provider-level retry policy implementation
- arbitrary code execution of generated artifacts

Operationally relevant repository/branch boundary:

- transient build branches matching `forge-agent/build/consensusdevagent-*` are disposable
- `main` is retained
- `forge-agent/build/consensusdevagent/prds` is retained if it contains JSON PR-plan artifacts, because those files are part of recovery state

## Data Flow

### 1. Startup and Thread Discovery

On normal startup, ForgeAgent boots and scans persisted thread state for incomplete builds. If a `ConsensusDevAgent` thread exists and is incomplete, the operator is shown resumable metadata such as:

- agent name
- PRD completion count
- PR completion count
- recency
- build description

No `/resume` or equivalent command is required for this path.

### 2. Local State Load

The subsystem loads the local thread state file for this build thread, operationally represented as:

- `state/threads/consensusdevagent.json`

Important fields include:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

The `state` field determines which phase of the pipeline should resume. For example:

- `pr_pipeline` indicates PR plans exist and execution should continue in PR processing
- `prd_gen` with empty `pr_plans_by_prd` indicates planning state may be missing locally

### 3. Resume Decision

After operator selection, the director invokes resume for the thread. ConsensusDevAgent interprets the loaded state and continues from the last durable checkpoint.

Expected behavior:

- if local state is complete enough, continue directly
- if local state is incomplete but GitHub PR-plan JSON artifacts exist, reconstruct planning state first
- if neither local nor GitHub-backed recovery data is adequate, restart or require operator intervention depending on surrounding orchestration policy

### 4. GitHub-Backed Recovery

After each PR plan is generated, the subsystem writes durable planning artifacts to the PRDs branch:

- `prds/consensusdevagent/prd-001-pr-plan.md`
- `prds/consensusdevagent/prd-001-pr-plan.json`

The JSON artifact is the machine-readable recovery source of truth for PR planning reconstruction. If local thread state is wiped or saved before `pr_plans_by_prd` was populated, the subsystem reads these JSON files from the retained PRDs branch and reconstructs the full plan.

### 5. Continuation of PR Pipeline

Once planning state is present, the subsystem resumes the PR pipeline instead of regenerating from PR #1. Correct resume behavior depends on durable synchronization between:

- local thread state phase
- local or reconstructed `pr_plans`
- GitHub PR-plan JSON artifacts

## Key Invariants

### Automatic restart recovery

Normal restart recovery must not require a manual resume command. Incomplete `ConsensusDevAgent` threads must be discoverable automatically at startup.

### Thread identity is stable

The subsystem must map persisted state, resumable UI metadata, and GitHub PR-plan artifacts to the same logical `ConsensusDevAgent` build thread.

### Local state is not the only recovery source

Local thread state is recoverable and may be deleted or become stale. The architecture explicitly depends on GitHub-stored PR-plan JSON files as disaster-recovery backups.

### GitHub JSON artifacts are durable planning state

Human-readable markdown files are useful for operators, but the JSON PR-plan files are the canonical machine-readable recovery inputs for reconstruction.

### Resume phase must match plan availability

If PR plans exist, thread state should reflect a post-planning phase such as `pr_pipeline`. A state/plan mismatch is a correctness bug or incomplete checkpoint.

### No direct GitHub API usage

All GitHub operations must go through `GitHubTool`. This subsystem must not bypass the platform abstraction.

### Writes must be path-validated

Any file write performed by this subsystem or its collaborators must validate paths before writing.

### Blind GitHub writes are forbidden

GitHub writes must not occur without SHA-aware safety. This includes recovery artifacts and branch updates.

### Gates do not auto-resolve

If the subsystem enters or depends on a gated state, that gate remains pending until operator action. If the backend restarts mid-gate, gate state is lost and must be re-approved by the operator.

### Retry behavior is bounded

Transient provider or transport failures may be retried only within platform policy. Infinite retries are forbidden.

## Failure Modes

### Local thread state missing

Example:
- `state/threads/consensusdevagent.json` was deleted

Effect:
- incomplete build may not resume from local disk state alone

Recovery:
- reconstruct from GitHub PR-plan JSON files if present in the retained PRDs branch

### Local thread state stale or checkpointed too early

Symptom:
- on restart, agent reports `0 PRs done`
- PR generation begins again from PR #1

Likely diagnosis:
- local JSON shows `state: "prd_gen"`
- `pr_plans_by_prd` is empty

Cause:
- state was saved before PR plans were persisted into local thread state

Recovery:
- inspect GitHub PRDs branch for `prd-###-pr-plan.json`
- if present, rebuild `pr_plans` / `pr_plans_by_prd` from those artifacts and continue in PR pipeline

### PRDs branch removed or missing JSON artifacts

Effect:
- disaster-recovery reconstruction path is unavailable

Impact:
- if local state is also absent or incomplete, full planning continuity is lost

Operational implication:
- do not delete `forge-agent/build/consensusdevagent/prds` when it contains JSON artifacts

### Excess transient build branches

Effect:
- old `forge-agent/build/consensusdevagent-*` branches accumulate CI failures and confuse branch monitoring

Mitigation:
- delete old build branches
- retain only `main` and the PRDs branch containing recovery JSON if applicable

### Backend restart during gate

Effect:
- gate state is lost

Required behavior:
- gate must not auto-resolve
- operator must explicitly re-approve

### Provider or backend failure during generation

Handling must follow platform policies documented in the repository:

- bounded retries only
- provider failover where implemented
- for hard refusal/security-stop conditions: stop immediately, do not rephrase, emit error card, gate, and require explicit operator override

## Dependencies

ConsensusDevAgent depends on the following platform capabilities and rules:

### Runtime / Director

- startup bootstrap and incomplete-thread discovery
- operator thread selection
- `director.resume()` to re-enter execution from persisted state

### Local State Store

- per-thread JSON persistence
- durable checkpoint reads at startup
- fields sufficient to determine phase and planning completeness

### GitHubTool

- all GitHub reads/writes for PRD and PR-plan artifacts
- branch reads from retained PRDs branch
- SHA-safe writes
- polling behavior subject to platform caching/rate-limit rules

### Repository Conventions

- branch naming under `forge-agent/build/consensusdevagent-*`
- PRDs branch artifact layout under `prds/consensusdevagent/`
- markdown + JSON paired outputs per PRD plan

### Consensus / LLM Provider Layer

This subsystem may rely on shared generation infrastructure whose constraints apply here:

- retry after 10s then fallback in `_claude_json`
- retry with the other provider in `consensus.py`
- max 3 attempts total
- `403` primary rate limit: exponential backoff starting at 60s
- `429` secondary rate limit: respect `Retry-After` exactly

### Safety and Security Rules

The subsystem operates under repository-wide prohibitions, including:

- no shell injection
- no credential in log
- no credential in prompt
- no direct execution of generated code
- no path traversal
- no blind GitHub write
- no context in system prompt
- no ignoring `SECURITY_REFUSAL`

These are architectural constraints, not optional implementation details.