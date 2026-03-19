# TRD-13-Recovery-State-Management

_Source: `TRD-13-Recovery-State-Management.docx` — extracted 2026-03-19 23:49 UTC_

---

TRD-13: Recovery and State Management

Forge Dev Agent  |  YouSource.ai  |  v1.0  |  2026-03-19

Version | 1.0
Status | Draft
Author | Todd Gould / YouSource.ai
Date | 2026-03-19
Dependencies | TRD-4 (Multi-Agent Coordination), TRD-12 (Backend Runtime Startup)

# 1. Purpose and Scope

This TRD defines the recovery and state management subsystem for the Forge Dev Agent. It replaces the current ad-hoc recovery flow (/recover, /clear confirm, ambiguous /prd start resume behavior) with a deterministic, operator-facing save/restore/continue lifecycle.

### In Scope

Local and GitHub save points

Restore from local, GitHub, or both with divergence detection

Explicit continue command to resume build execution

Hardened /prd start that refuses to overwrite active threads

Clear state commands with confirmation gates

### Out of Scope

Multi-agent coordination (handled by Build Ledger TRD)

iMessage/WhatsApp notification gateway (separate TRD)

# 2. Problem Statement

The current recovery flow has four critical failure modes observed in production:

/prd start overwrites active threads — running it on a live session discards all PRD/PR plans and starts from scratch with no warning.

/recover loops indefinitely — when it cannot find audit log entries, it reports Fixed then immediately re-diagnoses the same issue.

No clear save confirmation — operators do not know if state was persisted before a restart.

Local and GitHub state diverge silently — after a crash, the agent picks one source of truth without telling the operator, leading to lost progress or phantom state.

# 3. Architecture

## 3.1 State Layers

Two independent persistence layers, each with distinct commands:

LOCAL STATE

Path:     workspace/<engineer>/thread_state.json

Contains: PRD plan, PR plan, completed PRs,

scope statement, relevant docs

GITHUB STATE

Path:     forge-ledger/<engineer>/state.json

Contains: Same as local + commit SHA + timestamp

Authority: GitHub is source of truth for multi-agent coordination

## 3.2 Command Surface

### Save Commands

Command | Action | Output
/save local | Serialize thread state to local disk | ✓ Local save complete — [timestamp] — [path]
/save github | Commit state to GitHub ledger | ✓ GitHub save complete — commit [SHA] — [timestamp]
/save | Both, in order (local first) | Both confirmations, or error with which layer failed

### Restore Commands

Command | Action | Output
/restore local | Load thread state from local disk | ✓ Restored from local — PRD-00X, N/M PRs done — saved [timestamp]
/restore github | Pull state from GitHub ledger | ✓ Restored from GitHub — PRD-00X, N/M PRs done — commit [SHA]
/restore | Load both, compare, prompt on divergence | See Section 3.3

### Continue Command

Command | Action | Output
/continue | Resume build from current thread state | ▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]

### PRD Lifecycle Commands

Command | Action
/prd start | ONLY valid when no active thread exists. If active thread found: print summary and require /prd start --force or /continue
/prd start --force | Explicitly discard active thread and start fresh. Requires typing CONFIRM

### Clear Commands

Command | Action
/clear local | Wipe local thread state. Prints what will be deleted, requires yes
/clear github | Wipe GitHub ledger state. Prints what will be deleted, requires yes
/clear all | Both layers. Requires typing CONFIRM

## 3.3 Divergence Detection

When /restore is run without a target, the agent loads both layers and compares:

No divergence: Both layers agree — restore silently, print single confirmation.

Divergence detected — example output:

⚠  Local and GitHub state diverge:

Local  : ConsensusDevAgent — PRD-001, 3/11 PRs done

Saved: 2026-03-19 18:45:00 (2h ago)

GitHub : ConsensusDevAgent — PRD-001, 0/11 PRs done

Saved: 2026-03-19 16:30:00 (4h ago)

Conflict fields: completed_prs, pr_plans_by_prd

Which to restore? (local / github / cancel)

### Conflict Resolution Rules

local selected: restore local, update GitHub to match

github selected: restore GitHub, update local to match

cancel selected: neither layer modified, return to prompt

### Auto-Resolution (Non-Interactive Mode)

If AUTO_RESTORE=github is set in .env, GitHub wins automatically with a printed warning. This enables unattended operation in CI/CD environments.

# 4. Implementation Requirements

## 4.1 SaveManager (new module: src/save_manager.py)

class SaveManager:

save_local(thread: BuildThread) -> SaveResult

save_github(thread: BuildThread, github: GitHubTool) -> SaveResult

save_all(thread, github) -> tuple[SaveResult, SaveResult]

restore_local() -> BuildThread | None

restore_github(github) -> BuildThread | None

restore(github) -> RestoreResult  # handles divergence

clear_local(confirm: bool) -> None

clear_github(github, confirm: bool) -> None

## 4.2 SaveResult Dataclass

@dataclass

class SaveResult:

success: bool

layer: str          # 'local' | 'github'

timestamp: str

path: str           # local path or GitHub commit SHA

prd_id: str         # current PRD

prs_done: int

prs_total: int

error: str | None

## 4.3 RestoreResult Dataclass

@dataclass

class RestoreResult:

thread: BuildThread | None

source: str              # 'local' | 'github' | 'cancelled'

diverged: bool

local_summary: str | None

github_summary: str | None

conflict_fields: list[str]

## 4.4 Agent REPL Integration

All new commands registered in agent.py command dispatch. Each command must:

Print a clear section header (e.g., '── SAVE ──────────────────')

Print exactly what was saved/restored/cleared with timestamp and location

Print the recommended next command

Never silently succeed or fail

## 4.5 /prd start Guard

if active_thread_exists:

print(f'''

⚠  Active build thread detected: {thread.subsystem}

PRD-{current_prd}, {prs_done}/{prs_total} PRs done

Started: {thread.created_at}

Options:

/continue          — resume this build

/restore           — restore from a save point

/prd start --force — discard and start fresh (requires CONFIRM)

''')

return

## 4.6 /continue Implementation

# Load current thread state

# Determine resume point:

#   - If mid-PR:        retry the current PR from scratch

#   - If between PRs:   start next PR

#   - If PRD complete:  start next PRD

# Print resume banner

# Hand off to build_director._stage_build_loop()

# 5. Non-Functional Requirements

All save operations complete in < 5 seconds

Divergence detection compares field-by-field, not string hash

GitHub save uses atomic commit (single API call, no partial state)

Local save uses write-then-rename (atomic on POSIX)

All commands work in non-interactive mode (for future CI/CD integration)

No save operation blocks the build loop — saves are async fire-and-forget with error logging

# 6. Migration

Existing /recover command kept for backward compatibility — prints deprecation notice pointing to /restore and /continue

Existing /clear confirm mapped to /clear all

Existing /backup mapped to /save github

# 7. Acceptance Criteria

/save prints timestamp and location for both layers

/restore detects divergence and prompts operator before overwriting

/continue resumes from exact PR that failed, not from PRD start

/prd start refuses if active thread exists, prints clear options

/clear all requires typing CONFIRM before wiping state

Recovery loop in /recover cannot occur — /restore + /continue are stateless checks

All commands work correctly after agent restart with no active session

Divergence prompt shows field-level diff, not just summary

AUTO_RESTORE=github resolves divergence without operator input

# 8. Dependencies

TRD-4: Multi-Agent Coordination (Build Ledger GitHub schema)

TRD-12: Backend Runtime Startup (agent REPL command dispatch)