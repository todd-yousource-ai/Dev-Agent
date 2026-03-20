# TRD-13-Recovery-State-Management

_Source: `TRD-13-Recovery-State-Management.docx` — extracted 2026-03-20 00:25 UTC_

---

# TRD-13: Recovery and State Management

Version: 1.0

Status: Draft

Author: Todd Gould / YouSource.ai

Date: 2026-03-19

## 1. Purpose and Scope

This TRD defines the recovery and state management subsystem for the Forge Dev Agent. It replaces the current ad-hoc recovery flow (/recover, /clear confirm, ambiguous /prd start resume behavior) with a deterministic, operator-facing save/restore/continue lifecycle.

In scope:

Local and GitHub save points

Restore from local, GitHub, or both with divergence detection

Explicit continue command to resume build execution

Hardened `/prd start` that refuses to overwrite active threads

Clear state commands with confirmation gates

Out of scope:

Multi-agent coordination (handled by Build Ledger TRD)

iMessage/WhatsApp notification gateway (separate TRD)

## 2. Problem Statement

The current recovery flow has four critical failure modes observed in production:

`/prd start` overwrites active threads — running it on a live session discards all PRD/PR plans and starts from scratch with no warning

`/recover` loops indefinitely — when it can't find audit log entries, it reports "Fixed" then immediately re-diagnoses the same issue

No clear save confirmation — operators don't know if state was persisted before a restart

Local and GitHub state diverge silently — after a crash, the agent picks one source of truth without telling the operator, leading to lost progress or phantom state

## 3. Architecture

### 3.1 State Layers

Two independent persistence layers, each with distinct commands:

┌─────────────────────────────────────────────────────┐

│  LOCAL STATE                                        │

│  Path: workspace/<engineer>/thread_state.json       │

│  Contains: PRD plan, PR plan, completed PRs,        │

│            scope statement, relevant docs           │

└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐

│  GITHUB STATE                                       │

│  Path: forge-ledger/<engineer>/state.json           │

│  Contains: Same as local + commit SHA + timestamp   │

│  Authority: GitHub is the source of truth for       │

│             multi-agent coordination                │

└─────────────────────────────────────────────────────┘

### 3.2 Command Surface

#### Save Commands

| Command | Action | Output |

|---------|--------|--------|

| `/save local` | Serialize thread state to local disk | `✓ Local save complete — [timestamp] — [path]` |

| `/save github` | Commit state to GitHub ledger | `✓ GitHub save complete — commit [SHA] — [timestamp]` |

| `/save` | Both, in order (local first) | Both confirmations, or error with which layer failed |

#### Restore Commands

| Command | Action | Output |

|---------|--------|--------|

| `/restore local` | Load thread state from local disk | `✓ Restored from local — PRD-00X, N/M PRs done — saved [timestamp]` |

| `/restore github` | Pull state from GitHub ledger | `✓ Restored from GitHub — PRD-00X, N/M PRs done — commit [SHA]` |

| `/restore` | Load both, compare, prompt on divergence | See §3.3 |

#### Continue Command

| Command | Action | Output |

|---------|--------|--------|

| `/continue` | Resume build from current thread state | `▶ Resuming ConsensusDevAgent — PRD-00X, PR #N: [title]` |

#### PRD Lifecycle

| Command | Action |

|---------|--------|

| `/prd start` | **Only valid when no active thread exists.** If active thread found: print thread summary and require `/prd start --force` or `/continue` |

| `/prd start --force` | Explicitly discard active thread and start fresh. Requires typing `CONFIRM` |

#### Clear Commands

| Command | Action |

|---------|--------|

| `/clear local` | Wipe local thread state. Prints what will be deleted, requires `yes` |

| `/clear github` | Wipe GitHub ledger state. Prints what will be deleted, requires `yes` |

| `/clear all` | Both layers. Requires typing `CONFIRM` |

### 3.3 Divergence Detection

When /restore is run without a target, the agent loads both layers and compares:

No divergence: Both layers agree → restore silently, print single confirmation.

Divergence detected:

⚠  Local and GitHub state diverge:

Local  : ConsensusDevAgent — PRD-001, 3/11 PRs done

Saved: 2026-03-19 18:45:00 (2h ago)

GitHub : ConsensusDevAgent — PRD-001, 0/11 PRs done

Saved: 2026-03-19 16:30:00 (4h ago)

Conflict fields: completed_prs, pr_plans_by_prd

Which to restore? (local / github / cancel)

Conflict resolution rules:

If operator selects `local`: restore local, update GitHub to match

If operator selects `github`: restore GitHub, update local to match

If operator selects `cancel`: neither layer modified, return to prompt

Auto-resolution (non-interactive mode):

If AUTO_RESTORE=github is set in .env, GitHub wins automatically with a printed warning.

## 4. Implementation Requirements

### 4.1 SaveManager (new module: `src/save_manager.py`)

class SaveManager:

save_local(thread: BuildThread) -> SaveResult

save_github(thread: BuildThread, github: GitHubTool) -> SaveResult

save_all(thread, github) -> tuple[SaveResult, SaveResult]

restore_local() -> BuildThread | None

restore_github(github) -> BuildThread | None

restore(github) -> RestoreResult  # handles divergence

clear_local(confirm: bool) -> None

clear_github(github, confirm: bool) -> None

### 4.2 SaveResult dataclass

@dataclass

class SaveResult:

success: bool

layer: str          # "local" | "github"

timestamp: str

path: str           # local path or GitHub commit SHA

prd_id: str         # current PRD

prs_done: int

prs_total: int

error: str | None

### 4.3 RestoreResult dataclass

@dataclass

class RestoreResult:

thread: BuildThread | None

source: str              # "local" | "github" | "cancelled"

diverged: bool

local_summary: str | None

github_summary: str | None

conflict_fields: list[str]

### 4.4 Agent REPL Integration

All new commands registered in agent.py command dispatch. Each command:

Prints a clear header (e.g., `── SAVE ──────────────────`)

Prints exactly what was saved/restored/cleared

Prints the recommended next command

Never silently succeeds or fails

### 4.5 `/prd start` Guard

if active_thread_exists:

print(f"""

⚠  Active build thread detected: {thread.subsystem}

PRD-{current_prd}, {prs_done}/{prs_total} PRs done

Started: {thread.created_at}

Options:

/continue          — resume this build

/restore           — restore from a save point

/prd start --force — discard and start fresh (requires CONFIRM)

""")

return

### 4.6 `/continue` Implementation

# Load current thread state

# Determine resume point:

#   - If mid-PR: retry the current PR from scratch

#   - If between PRs: start next PR

#   - If PRD complete: start next PRD

# Print resume banner

# Hand off to build_director._stage_build_loop()

## 5. Non-Functional Requirements

All save operations complete in < 5 seconds

Divergence detection compares field-by-field, not string hash

GitHub save uses atomic commit (single API call, no partial state)

Local save uses write-then-rename (atomic on POSIX)

All commands work in non-interactive mode (for future CI/CD integration)

No save operation blocks the build loop — saves are async fire-and-forget with error logging

## 6. Migration

Existing /recover command:

Kept for backward compatibility

Prints deprecation notice pointing to `/restore` and `/continue`

Existing `/clear confirm` mapped to `/clear all`

## 7. Acceptance Criteria

☐  `/save` prints timestamp and location for both layers

☐  `/restore` detects divergence and prompts operator before overwriting

☐  `/continue` resumes from exact PR that failed, not from PRD start

☐  `/prd start` refuses if active thread exists, prints clear options

☐  `/clear all` requires typing `CONFIRM` before wiping state

☐  Recovery loop in `/recover` cannot occur — `/restore` + `/continue` are stateless checks

☐  All commands work correctly after agent restart with no active session

## 8. Dependencies

TRD-4: Multi-Agent Coordination (Build Ledger GitHub schema)

TRD-12: Backend Runtime Startup (agent REPL command dispatch)

## 9. Hot Reload for Patches

### 9.1 Problem

Every bug fix currently requires a full agent restart:

Operator runs `/patch`

New files written to disk

Agent must be killed and restarted

Active build state is lost

Resume is unreliable — operator re-runs from scratch

API calls are wasted re-running decomposition and PRD generation

In a production environment handling 14-PRD builds at ~$15/M tokens, a single forced restart can waste $5–15 in redundant API calls and 30–60 minutes of wall-clock time.

### 9.2 Solution: In-Process Hot Reload

When /patch is run during an active build, instead of writing files and printing "restart required", the agent:

Writes new files to disk (existing behavior)

Clears `__pycache__` (existing behavior)

Reloads changed modules in-place using `importlib.reload()`

Prints confirmation that new code is active

Build continues without interruption

### 9.3 Implementation

New method in patch.py: hot_reload(changed_files: list[str]) -> HotReloadResult

import importlib

import sys

def hot_reload(changed_files: list[str]) -> HotReloadResult:

"""

Reload changed Python modules in-place after a patch is applied.

Safe reload order (respects import dependencies):

1. Leaf modules first (no dependents): config, path_security, api_errors

2. Mid-tier: document_store, github_tools, thread_state, audit

3. Core: consensus, prd_planner, pr_planner, build_director

4. Entry: agent (cannot be reloaded — it is __main__)

Returns HotReloadResult with list of reloaded modules and any failures.

"""

RELOAD_ORDER = [

"config", "path_security", "api_errors",

"document_store", "github_tools", "thread_state", "audit",

"notifier", "build_ledger", "branch_scaffold",

"consensus", "prd_planner", "pr_planner",

"ci_workflow", "failure_handler", "build_director",

]

# agent.py cannot be reloaded (it is __main__)

# ForgeAgent.app launcher cannot be reloaded (separate process)

reloaded = []

failed = []

skipped = []

py_changed = [

f.replace("src/", "").replace(".py", "")

for f in changed_files

if f.endswith(".py") and "src/" in f

]

for mod_name in RELOAD_ORDER:

if mod_name not in py_changed:

skipped.append(mod_name)

continue

if mod_name not in sys.modules:

skipped.append(mod_name)

continue

try:

importlib.reload(sys.modules[mod_name])

reloaded.append(mod_name)

except Exception as exc:

failed.append((mod_name, str(exc)))

return HotReloadResult(reloaded=reloaded, failed=failed, skipped=skipped)

### 9.4 Limitations

`agent.py` cannot be hot-reloaded — it is `__main__`. Changes to the REPL command dispatch, startup sequence, or `/prd start` handler require a restart.

Changes to dataclass definitions (e.g. adding a field to `BuildThread`) require a restart — in-memory objects won't have the new field.

Changes to `ForgeAgentLauncher` (Swift/bash) always require an app restart.

When a patch contains changes only to agent.py or dataclass fields, the patch system prints:

⚠  This patch requires a restart (agent.py or dataclass changes detected).

Run /save first, then restart and resume.

### 9.5 Acceptance Criteria

☐  `/patch` hot-reloads changed modules without interrupting the build loop

☐  Reloaded modules are confirmed by name in the output

☐  Patches requiring restart are detected and flagged before applying

☐  Build state is preserved across a hot-reload patch

☐  Failed module reloads are reported but do not abort the patch

## 10. Checkpoint-First Architecture

### 10.1 Problem

The current save pattern is post-operation:

1. Call LLM (expensive — $0.50–2.00, 30–120 seconds)

2. Process result

3. Save state  ← crash here = lost work

A crash between steps 2 and 3 loses the entire API call. More critically, if the agent crashes *during* step 1 (timeout, network drop, OOM), there is no record that the call was attempted, and on resume the agent re-runs it.

### 10.2 Solution: Checkpoint-First Saves

Before every significant API call, save a checkpoint that records:

Intent: what operation is about to be attempted

Stage: which phase of the pipeline

Input hash: hash of the prompt/context being sent (for deduplication)

After the call completes, update the checkpoint with the result.

On resume, if a checkpoint exists for an in-progress operation:

If result is present → use cached result, skip API call

If result is absent → operation was interrupted, retry

### 10.3 Checkpoint Schema

@dataclass

class OperationCheckpoint:

operation:    str        # "decompose" | "generate_prd" | "generate_pr_plan" | "generate_impl"

prd_id:       str | None # e.g. "PRD-001"

pr_num:       int | None # e.g. 3

input_hash:   str        # SHA-256 of prompt content

status:       str        # "pending" | "complete" | "failed"

started_at:   float

completed_at: float | None

result:       dict | None  # serialized result, None if not yet complete

### 10.4 Checkpoint Lifecycle

/prd start

│

├── CHECKPOINT: decompose — status=pending

├── [LLM call: decompose]

├── CHECKPOINT: decompose — status=complete, result=<prd_list>

│

├── CHECKPOINT: generate_prd PRD-001 — status=pending

├── [LLM call: generate_prd]

├── CHECKPOINT: generate_prd PRD-001 — status=complete

│

├── CHECKPOINT: generate_pr_plan PRD-001 — status=pending

├── [LLM call: generate_pr_plan]

├── CHECKPOINT: generate_pr_plan PRD-001 — status=complete

│

├── CHECKPOINT: generate_impl PR-001 — status=pending

├── [LLM call: generate_impl]

└── CHECKPOINT: generate_impl PR-001 — status=complete

### 10.5 Resume With Checkpoints

On resume, before any LLM call:

checkpoint = checkpoint_store.get(operation, prd_id, pr_num, input_hash)

if checkpoint and checkpoint.status == "complete" and checkpoint.result:

# Cache hit — skip API call, use saved result

logger.info(f"Checkpoint hit: {operation} {prd_id} — skipping API call")

return checkpoint.result

This means a full crash-and-resume costs zero additional API calls for already-completed operations, regardless of whether the thread state file was written.

### 10.6 Input Hash Stability

The input hash must be stable across restarts for cache hits to work. Hash inputs:

`decompose`: hash of full TRD corpus content

`generate_prd`: hash of PRD item ID + title + summary + TRD corpus

`generate_pr_plan`: hash of PRD result markdown

`generate_impl`: hash of PR spec title + impl_plan + doc context

Do NOT include timestamps, session IDs, or random seeds in the hash.

### 10.7 Checkpoint Storage

workspace/<engineer>/checkpoints/

decompose-<input_hash[:8]>.json

prd-001-<input_hash[:8]>.json

prd-001-pr-plan-<input_hash[:8]>.json

prd-001-pr-001-impl-<input_hash[:8]>.json

Checkpoints are retained for 7 days then auto-purged. The operator can force-clear with /clear checkpoints.

### 10.8 Acceptance Criteria

☐  Every LLM call is preceded by a checkpoint write

☐  Resume skips API calls for operations with complete checkpoints

☐  Input hash is stable — same inputs produce same hash across restarts

☐  Cache hit is logged and printed: `↩ Using cached result for [operation]`

☐  Checkpoint files are human-readable JSON for debugging

☐  `/clear checkpoints` removes all checkpoint files

☐  Stale checkpoints (> 7 days) are auto-purged on startup

## 11. Updated Acceptance Criteria (Full)

☐  `/save` prints timestamp and location for both layers

☐  `/restore` detects divergence and prompts operator before overwriting

☐  `/continue` resumes from exact PR that failed, not from PRD start

☐  `/prd start` refuses if active thread exists, prints clear options

☐  `/clear all` requires typing `CONFIRM` before wiping state

☐  Recovery loop in `/recover` cannot occur

☐  All commands work correctly after agent restart with no active session

☐  `/patch` hot-reloads changed modules without interrupting build loop

☐  Patches requiring restart are detected and flagged before applying

☐  Every LLM call is preceded by a checkpoint write

☐  Resume skips API calls for operations with complete checkpoints

☐  `/backup` flushes active in-memory thread before archiving

☐  Clean `/quit` always saves active thread state to disk