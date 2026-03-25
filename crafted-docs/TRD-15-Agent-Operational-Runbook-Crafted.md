# TRD-15-Agent-Operational-Runbook-Crafted

_Source: `TRD-15-Agent-Operational-Runbook-Crafted.docx` — extracted 2026-03-25 19:25 UTC_

---

TRD-15: Agent Operational Runbook

Technical Requirements Document — v1.2

Field | Value
Product | Crafted
Document | TRD-15: Agent Operational Runbook
Version | 1.2
Status | Updated — Build Rules Console Outputs + File Location (March 2026)
Author | Todd Gould / YouSource.ai
Previous Version | v1.1 (2026-03-22)
Depends on | TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality)

# 1. Purpose

This document is the practical operational guide for running the Crafted Dev Agent in production. It contains hard-won lessons from the March 2026 build sprint — what works, what breaks, and exactly what to do in each situation.

This is not a specification document. It is a runbook. When something goes wrong, this is the first thing to open.

# 2. System Overview

The agent runs as two cooperating processes on macOS:

Crafted.app — Swift shell, macOS UI, WebSocket bridge server

Python backend — src/agent.py — all LLM calls, GitHub operations, build orchestration

Start: Click Crafted.app. Never run python agent.py from terminal directly — this breaks the UI connection.

Stop: Use /quit at the crafted> prompt, or at an approval gate. Never use pkill without reading §4.3 first.

Version: Check cat /Users/tgould/Agents/crafted-dev-agent/VERSION

# 3. Before You Start — Clean Run Checklist

Run through this checklist before every build session. Skipping steps leads to regeneration loops and wasted token spend.

## 3.1 GitHub Cleanup

# Delete all branches from the previous run

# Do this from github.com/todd-yousource-ai/Dev-Agent/branches

# Delete all branches starting with crafted-agent/build/<subsystem>-*

# Keep: main, crafted-agent/build/<subsystem>/prds (if it has JSON files)

Why: Old branches accumulate CI failures and confuse the branch monitor. The agent creates new branches automatically.

## 3.2 Local State Cleanup

# Wipe local thread state

rm /Users/tgould/Agents/crafted-dev-agent/workspace/todd-gould/state/threads/<subsystem>.json

# Verify it's gone

ls /Users/tgould/Agents/crafted-dev-agent/workspace/todd-gould/state/threads/

Why: A stale state file from a previous run will be offered as a resume option at startup. If it has incomplete or corrupt PR plans, it will cause regeneration loops.

IMPORTANT: Do NOT delete build_memory.json or build_rules.md. These are designed to persist across builds. See §11a and §11b.

## 3.3 Verify .env

cat /Users/tgould/Agents/crafted-dev-agent/.env | grep -E "ANTHROPIC|OPENAI|GITHUB" | head -5

Confirm all three API keys are present. A missing key causes silent failures that look like LLM timeouts.

## 3.4 Verify TRD Documents

ls /Users/tgould/Agents/Mac-Docs/*.docx | wc -l

# Should show 17 or more

The agent loads all .docx files from Mac-Docs/ at startup. Missing docs means the LLM generates with less context.

## 3.5 Check Agent Version

cat /Users/tgould/Agents/crafted-dev-agent/VERSION

# Should show the latest version (e.g., 38.153.0)

# 4. Startup and Resume

## 4.1 Normal Startup

1. Click Crafted.app
2. Wait for crafted> prompt (bootstrap takes ~45 seconds — Rust installer may pause up to 10s, this is normal)
3. If a previous build exists, you will see:

Found 1 incomplete build thread(s):

[1] ConsensusDevAgent 0/26 PRDs  0 PRs done (2h ago)

Type a number to resume, or press Enter to start fresh:

4. Type 1 to resume, or press Enter to start fresh.

## 4.2 When to Type 1 vs /ledger resume vs Enter

Situation | Command | What happens
Resume prompt shows and you want to continue | Type 1 | Restores from local state, auto-recovers GitHub JSON if needed
Resume prompt shows but local state is stale/wrong | Press Enter, then /clear local | Start fresh
No resume prompt, but you know a build was running | Type /ledger resume | Reconstructs from GitHub ledger + JSON files
Starting a brand new build | Press Enter | New scope/PRD/PR pipeline

IMPORTANT: /ledger resume is for disaster recovery only — when local state is completely gone. For normal restarts, always type 1.

## 4.3 The 0 PRs done Situation

If the resume prompt shows 0/26 PRDs, 0 PRs done after you know PRs were completed previously, the local state has empty pr_plans_by_prd. Type 1 anyway — the agent will automatically check GitHub for saved PR plan JSON files.

↺ Local PR plans empty — checking GitHub for saved plans...

✓ Recovered 12 PR plans from GitHub — skipping regeneration

# 5. The Build Phases

## 5.1 Phase 1: PRD Generation (~30–45 minutes)

What's happening: The agent generates PRD documents using consensus AI, then generates the PR plan for each PRD. Each completed PR plan is saved to both local disk and GitHub.

Observable: Messages like Spec complete for PR #1 in 141.2s

What you CAN do: Watch the build log. Apply patches using the sentinel workflow (see §7).

What you CANNOT do safely: Kill the agent without applying a patch first. Apply a patch without using the sentinel workflow.

If interrupted: Restart, type 1. The agent checks GitHub for completed PR plan JSON files and recovers them.

## 5.2 Phase 2: PR Execution (~3–8 hours for 23+ PRs)

What's happening: For each PR spec, the agent generates code, runs tests locally (up to 20 attempts), then pushes to GitHub and waits for CI. If CI fails, it autonomously fixes and re-runs CI (up to 3 cycles).

Observable: Messages like Running tests (attempt 1/20)... and CI notification sent: PR #41 PASSED

What you CAN do: Apply patches using the sentinel workflow. Walk away and let it run — autosave handles state every 30 seconds.

Batch boundaries: Every 5 PRs the agent pauses and asks Continue with next batch? (y/n). This is your opportunity to check GitHub for merged PRs before proceeding.

# 6. Interpreting Build Output

## 6.1 Normal Output Sequence for a Clean PR

▶  PR #3: Auth module

✓ Repo context: 1 existing file fetched (main)

Self-correction: pass 1/10... clean (no issues found)

✓ Lint gate: clean (syntax)

Running tests (attempt 1/20)...

✓ Tests passed (1 attempt)

💾 Build memory: PR #3 recorded (CI clean)

✓ PR #3 merged

## 6.2 PR with Fix Loop

▶  PR #7: Failure handler multi-turn loop

Running tests (attempt 1/20)...

✗ Assertion Error

AssertionError: expected 'test_driven', got 'converse'

Strategy: test_driven (assertion_error) — multi-turn consensus...

Winner: claude

Running tests (attempt 2/20)...

✓ Tests passed (2 attempts)

💾 Build memory: PR #7 recorded (2 attempts)

# 7. Applying Patches Mid-Run

## 7.1 The Sentinel Workflow (ONLY safe method)

1. Wait for a point between PRs (after ✓ PR #N merged, before ▶ PR #N+1 starts)
2. Run python patch.py /path/to/crafted-dev-agent-vNN.zip
3. Wait for ✓ Applied: N files
4. pkill the agent (Ctrl+C or pkill -f agent.py)
5. Restart Crafted.app
6. Type 1 to resume from exactly where it left off

NEVER: Kill the agent before running the patch. State will be from the last autosave tick, not current.

## 7.2 Patching During the Fix Loop

If the agent is stuck in a fix loop (attempt 15+/20), patching is safe using the sentinel workflow. The state checkpoint ensures resume continues from the current PR's last saved stage, not from code generation restart.

# 8. CI Failures and Interventions

## 8.1 CI Fix Cycle

After local tests pass, the agent pushes to GitHub and waits for CI. If CI fails, it automatically fetches the CI log, generates a fix, commits, and re-waits. Up to 3 CI fix cycles per PR.

## 8.2 When CI Keeps Failing

If a PR fails all 3 CI fix cycles, the agent marks it failed and moves to the next PR. The failed PR remains as a draft PR on GitHub for manual inspection. You will see: ✗ PR #N: 3 CI fix cycles failed — moving on

## 8.3 Checking CI Status Manually

# In the GitHub Actions tab, look for:

# - Crafted CI (ubuntu) — main Python test job

# - Crafted CI — macOS (Swift) — only triggers for Swift files

# 9. Troubleshooting

## 9.1 'No module named X' in CI but tests pass locally

Add X to requirements.txt. The CI environment is clean ubuntu-latest with only requirements.txt installed. Local environment may have X installed globally.

## 9.2 Agent stuck at 'Generating scope...' for >5 minutes

SCOPE_SYSTEM is hitting the Anthropic rate limit. Wait 60 seconds and the agent will retry automatically. If it persists, check your ANTHROPIC_API_KEY balance.

## 9.3 'Port already in use' when starting bridge

lsof -ti TCP:7474 | xargs kill -9

## 9.4 Resume shows 0 PRs done but you completed PRs

Type 1 anyway. The agent will auto-recover PR plans from GitHub. You will see: ✓ Recovered N PR plans from GitHub — skipping regeneration

# 10. REPL Commands

Command | Description
/quit | Clean shutdown — saves current state before exiting
/status | Show current build thread state (phase, PRD count, PR count)
/verbose [0|1|2] | Set LLM verbosity. 0=silent, 1=preview (default), 2=full
/v | Cycle verbose level 0→1→2→0
/clear local | Wipe local thread state (with confirmation)
/ledger resume | Reconstruct state from GitHub ledger + JSON files
/backup | Archive local state to patches/ directory
/patch /path/to/vNN.zip | Apply a patch using the sentinel workflow

# §11a. New File Location: build_memory.json (New in v1.1)

A persistent file created in the workspace directory:

/Users/tgould/Agents/crafted-dev-agent/workspace/todd-gould/build_memory.json

Property | Value
Created | Automatically on first successful PR completion
Updated | After every successful PR (atomic write via temp file)
Cleared by thread state wipe | No — intentionally survives rm on thread JSON
Cleared by version upgrade (patch.py) | No — workspace/ directory is not touched by patches
Manual clear | Delete the file, or call mem.clear() from a script
Size | ~1-5KB per 10 PRs — grows slowly

IMPORTANT: Do not delete build_memory.json as part of the clean run checklist (§3). Unlike thread state, build memory is designed to persist across builds. Deleting it loses the cross-run learning accumulated from prior runs.

# §11b. New File Location: build_rules.md (New in v1.2)

A second learning-system file exists in Mac-Docs:

/Users/tgould/Agents/Mac-Docs/build_rules.md

Property | Value
Created | After first build run where ≥3 patterns meet the occurrence threshold
Updated | After every subsequent build run with qualifying patterns
Cleared by thread state wipe | No — lives in Mac-Docs, not workspace/
Cleared by docs reset/re-sync | Potentially — see note below
Manual clear | Delete the file from Mac-Docs
Sections pruned | Oldest sections pruned when more than 10 run sections exist

IMPORTANT distinction from build_memory.json: build_rules.md lives in Mac-Docs. If you clear and re-sync Mac-Docs from scratch, this file will be deleted. The agent will rebuild it after the next complete run. The loss of build_rules.md is less severe than losing build_memory.json — rules can be re-derived from the next run.

# §12a. Build Memory Console Outputs (New in v1.1)

## Startup — Build Memory Summary

Build memory: 8 PR(s) completed across prior run(s).

CI clean first-pass: 5/8 PRs    Avg fix attempts: 2.4

Completed PRs (most relevant patterns available for injection):

PR #1: Consensus Engine core  [✓ CI clean]  → src/consensus.py

PR #2: Build Director phase split  [⚠ 7 attempts]  → src/build_director.py

## During PR Execution — Build Memory Record

✓ PR #3: Auth module

💾 Build memory: PR #3 recorded (CI clean)

✓ PR #7: Failure handler multi-turn loop

💾 Build memory: PR #7 recorded (4 attempts)

## During Fix Loop — Context Trim

Running tests (attempt 9/20)...

✗ Assertion Error

Strategy: test_driven (assertion_error) — multi-turn consensus...

✂  Context trimmed: 8 old turns removed (42,300 → 18,100 est. tokens)

Winner: claude

# §12b. Build Rules Console Outputs (New in v1.2)

## At Startup — Build Rules Summary

📋 Build rules: 12 rule(s) active from 3 prior run(s) — loaded into generation context

## At Build Completion — Rules Derived

📋 Build rules: 4 rule(s) derived from 12 PRs and saved to Mac-Docs

## What to Watch For

Output | Meaning | Action
💾 Build memory: PR #N recorded (CI clean) | PR passed on first test run | None — good signal
💾 Build memory: PR #N recorded (N attempts) | PR needed N fix loop passes | None unless N > 10
✂  Context trimmed: N old turns removed | Fix loop history trimmed to prevent context rot | None — automatic
📋 Build rules: N rule(s) active from N prior run(s) | Prior run rules loaded | None
📋 Build rules: N rule(s) derived from N PRs | New rules written to Mac-Docs | None — automatic
Build memory: N PR(s) completed... at startup | Prior run data loaded | None

# Updated Reference: Key File Locations

File | Path | Purpose
Agent source | /Users/tgould/Agents/crafted-dev-agent/src/ | Python backend
Thread state | /Users/tgould/Agents/crafted-dev-agent/workspace/todd-gould/state/threads/ | Local persistence — cleared for fresh builds
Build memory | /Users/tgould/Agents/crafted-dev-agent/workspace/todd-gould/build_memory.json | Cross-run PR notes — NOT cleared for fresh builds
Build rules | /Users/tgould/Agents/Mac-Docs/build_rules.md | Self-improving coding rules — NOT cleared for fresh builds; survives unless Mac-Docs is wiped
Patch backups | /Users/tgould/Agents/crafted-dev-agent/workspace/patches/ | Pre-patch snapshots
Audit logs | /Users/tgould/Agents/crafted-dev-agent/logs/todd-gould/ | Build history
TRD documents | /Users/tgould/Agents/Mac-Docs/ | LLM context
Environment config | /Users/tgould/Agents/crafted-dev-agent/.env | API keys
Sentinel file | workspace/.patch_in_progress | Patch state flush trigger

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — operational lessons from March 2026 build sprint
1.1 | 2026-03-22 | Build memory console outputs (§12a). build_memory.json file location and persistence note (§11a). Updated key file locations table.
1.2 | 2026-03-22 | Build rules console outputs (§12b). build_rules.md file location in Mac-Docs, persistence distinction from build_memory.json, note about docs re-sync risk (§11b). Updated key file locations table with build_rules.md entry.