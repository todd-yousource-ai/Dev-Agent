# Architecture - ConsensusDevAgent

## What This Subsystem Does

ConsensusDevAgent is the long-running build-thread subsystem responsible for planning and executing the end-to-end construction of the `ConsensusDevAgent` deliverable across multiple PRDs and PRs, with resumable state and disaster-recovery support.

Its core responsibilities are:

- detect previously incomplete build threads on startup
- present resumable thread candidates to the operator
- resume an existing thread when selected
- persist thread progress locally during execution
- persist PR-plan artifacts to GitHub as recovery checkpoints
- reconstruct execution state from GitHub-backed PR-plan JSON when local thread state is missing or stale

This subsystem explicitly supports **automatic recovery on normal restart**. No explicit resume command is required during startup flow. Recovery begins as part of bootstrap, after which the operator may select a discovered incomplete thread.

Operationally, a normal restart behaves as follows:

1. `ForgeAgent.app` starts
2. bootstrap completes in approximately 45 seconds
3. incomplete build threads are discovered automatically
4. the operator selects the `ConsensusDevAgent` thread
5. `director.resume()` continues execution from persisted state

The subsystem therefore acts as the continuity layer between:
- user-visible build-thread lifecycle
- local thread-state persistence
- GitHub-backed PR-plan recovery artifacts

## Component Boundaries

### In Scope

ConsensusDevAgent owns:

- build-thread identity for `ConsensusDevAgent`
- local persisted thread state for that build
- startup-time detection of incomplete work
- resume selection UX for the thread
- transition back into active execution via `director.resume()`
- PR-plan persistence artifacts under the PRDs branch
- reconstruction of PR execution plan from PR-plan JSON artifacts when needed

Concrete state locations and artifacts include:

- local thread state:
  - `state/threads/consensusdevagent.json`
- GitHub recovery artifacts:
  - `prds/consensusdevagent/prd-001-pr-plan.md`
  - `prds/consensusdevagent/prd-001-pr-plan.json`

### Out of Scope

This subsystem does **not** own:

- raw GitHub API usage
- branch lifecycle policy outside its own build namespace
- gate approval durability across backend restarts
- automatic operator-decision replay
- indefinite retries or self-healing beyond bounded recovery behavior

Relevant platform-wide constraints that apply here:

- all GitHub operations must go through `GitHubTool`; direct GitHub API use is forbidden
- gates do not auto-resolve
- if backend restarts mid-gate, gate state is lost and the operator must re-approve
- there is no undo for gate decisions

### Operational Boundary

The subsystem’s branch namespace is ephemeral. Operational guidance is to delete old branches matching:

- `forge-agent/build/consensusdevagent-*`

while preserving:

- `main`
- `forge-agent/build/consensusdevagent/prds` if it contains JSON recovery files

This indicates a hard boundary between:
- transient build branches
- durable PR-plan recovery state stored on the PRDs branch

## Data Flow

### 1. Startup Detection

On normal application startup:

- the platform bootstraps
- thread-state storage is scanned for incomplete build threads
- if `consensusdevagent.json` indicates incomplete work, the thread is surfaced to the operator

The prompt includes summary progress such as:

- PRD count completed
- PR count completed
- recency of activity
- build description

### 2. Operator Selection

The operator selects the incomplete `ConsensusDevAgent` thread by number.

This selection is the only explicit recovery action required in the normal path. No `/resume`, `/continue`, or `/ledger resume` command is required.

### 3. Resume Execution

After selection, control passes to `director.resume()`.

Resume behavior depends on the persisted state model, especially fields such as:

- `state`
- `prd_count`
- `pr_plans`
- `pr_plans_by_prd`

Operationally, state inspection focuses on whether the thread is already in PR-pipeline execution and whether expected PR plans exist.

### 4. Local State Persistence

The subsystem writes progress to:

- `state/threads/consensusdevagent.json`

This file is the primary local resume source. It tracks the current phase and generated plans.

Expected interpretation:

- if `state` is `pr_pipeline` and PR plans exist, execution should continue from PR processing
- if `state` is earlier, such as `prd_gen`, and PR plan collections are empty, local state may be stale relative to already-generated artifacts

### 5. GitHub Recovery Checkpointing

After each PR plan is generated, the subsystem writes two durable artifacts to the PRDs branch:

- markdown summary for humans
- JSON specification for machine recovery

Pattern:

- `prds/consensusdevagent/prd-XXX-pr-plan.md`
- `prds/consensusdevagent/prd-XXX-pr-plan.json`

The JSON file is the authoritative disaster-recovery backup for PR-plan reconstruction.

### 6. Recovery Reconstruction

If local thread state is missing, wiped, or predates PR-plan generation:

- the subsystem reads PR-plan JSON from the PRDs branch
- reconstructs the full PR plan set
- resumes execution without needing the original local generation state

This is the intended recovery path after local state loss.

## Key Invariants

### Recovery Is Automatic at Startup

Normal restart must not require a command-based resume protocol.

Invariant:

- incomplete `ConsensusDevAgent` builds are discovered automatically during startup

### Resume Requires Thread Selection, Not Recommanding the Workflow

Invariant:

- the operator selects a discovered thread
- the system resumes via `director.resume()`
- no separate resume command vocabulary is required for normal restart

### Local State Is Not the Only Source of Truth

Invariant:

- local thread state is resumable state
- GitHub PR-plan JSON is disaster-recovery state

If the two diverge, PR-plan JSON must be sufficient to reconstruct execution planning.

### PR-Plan JSON Must Be Durable

Invariant:

- each generated PR plan produces a corresponding JSON artifact in the PRDs branch

Without this, full recovery from local-state loss is not guaranteed.

### PRDs Branch Is Special

Invariant:

- the PRDs branch for `consensusdevagent` may contain durable recovery artifacts and must be preserved if it contains JSON files

By contrast, old build branches in the `forge-agent/build/consensusdevagent-*` namespace are disposable.

### State-Phase Semantics Matter

Invariant:

- `state` must reflect the true execution phase closely enough for resume logic to choose the correct continuation point

Operationally important examples:

- `pr_pipeline` implies PR plans should already exist
- `prd_gen` with empty `pr_plans_by_prd` implies the state may have been captured before plan generation completed

### Platform Safety Rules Apply

The subsystem must comply with repository-wide and platform-wide invariants, including:

- all GitHub operations go through `GitHubTool`
- validate paths before any write
- never retry indefinitely; maximum 3 attempts total
- respect 403/429 retry policies exactly
- use ETag caching on polling endpoints
- never perform blind GitHub writes without SHA
- never execute generated code directly
- never allow path traversal or shell injection
- never place credentials in logs or prompts
- never ignore `SECURITY_REFUSAL`

## Failure Modes

### Stale Local State Causes PR Regeneration

Symptom:

- on restart, the subsystem reports `0 PRs done`
- execution begins regenerating PR specs from PR #1

Likely cause:

- local thread state was saved before PR plans were generated
- `state` remains `prd_gen`
- `pr_plans_by_prd` is empty

Effect:

- resume logic cannot infer prior PR planning from local state alone

Expected recovery action:

- inspect GitHub PRDs branch for existing `*-pr-plan.json` files
- reconstruct state from those JSON artifacts

### Local Thread State Loss

Symptom:

- `state/threads/consensusdevagent.json` is missing or intentionally wiped

Effect:

- local resume source is unavailable

Expected recovery action:

- recover from PR-plan JSON stored in the PRDs branch

Operationally, deleting the local thread file is a supported troubleshooting step only because GitHub-hosted JSON recovery artifacts exist.

### PRDs Branch Cleanup Mistake

Symptom:

- PRDs branch or its JSON files are deleted during cleanup

Effect:

- disaster-recovery source of truth is lost
- only local state remains, if any

Consequence:

- recovery robustness is significantly reduced
- full reconstruction may become impossible after local-state loss

### Mid-Gate Backend Restart

Symptom:

- backend restarts while waiting on an approval gate

Effect:

- gate state is lost

Consequence:

- operator must explicitly re-approve
- gate decisions are not auto-replayed
- there is no undo mechanism

This subsystem must not assume that in-flight approvals survive restart.

### GitHub Write/Read Failures

Because recovery depends on durable GitHub artifacts, failures in GitHub operations can compromise recoverability.

System constraints for handling these failures:

- route all operations through `GitHubTool`
- follow bounded retry behavior only
- stop after max retry budget
- emit error card, gate, and log full prompt context when required by platform policy
- require explicit operator override rather than silent continuation

### Branch Accumulation

Symptom:

- old `forge-agent/build/consensusdevagent-*` branches accumulate
- CI failures and branch-monitor confusion increase

Effect:

- operational noise and monitoring ambiguity

Mitigation:

- remove old build branches
- preserve only `main` and the PRDs branch if it contains JSON recovery artifacts

## Dependencies

### Director / Resume Orchestration

The subsystem depends on the platform director to resume work:

- `director.resume()`

This is the transition point from discovered persisted thread state back into active execution.

### Local Thread-State Store

The subsystem depends on filesystem-backed thread persistence at:

- `state/threads/consensusdevagent.json`

This is the primary local source for progress, phase, and plan metadata.

### GitHubTool

All GitHub interactions must use `GitHubTool`.

This includes:

- reading PR-plan recovery artifacts
- writing PR-plan markdown and JSON
- interacting with PRDs branch state

Direct GitHub API usage is forbidden.

### Git Branch Layout

The subsystem depends on a branch layout with a durable PRDs branch and ephemeral build branches:

- durable:
  - `forge-agent/build/consensusdevagent/prds`
- ephemeral:
  - `forge-agent/build/consensusdevagent-*`

### Repository Operational Policies

This subsystem is constrained by repository-wide operational rules documented in the repo, including:

- error handling and bounded retries
- path validation before writes
- CI routing rules
- version management rules
- security checklist requirements
- forbidden pattern enforcement

### Recovery Artifacts

The subsystem depends on machine-readable PR-plan JSON artifacts as its disaster-recovery substrate.

Without these artifacts, the system can resume only from surviving local state, which is a weaker recovery mode.