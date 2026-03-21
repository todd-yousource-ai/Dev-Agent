# TRD-15-Agent-Operational-Runbook

_Source: `TRD-15-Agent-Operational-Runbook.docx` — extracted 2026-03-21 18:58 UTC_

---

# TRD-15: Agent Operational Runbook

Technical Requirements Document — v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-15: Agent Operational Runbook
Version | 1.0
Status | Production Reference (March 2026)
Author | Todd Gould / YouSource.ai
Date | 2026-03-20
Depends on | TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality)

## 1. Purpose

This document is the practical operational guide for running the Forge Dev Agent in production. It contains hard-won lessons from the March 2026 build sprint — what works, what breaks, and exactly what to do in each situation.

This is not a specification document. It is a runbook. When something goes wrong, this is the first thing to open.

## 2. System Overview

The agent runs as two cooperating processes on macOS:

ForgeAgent.app — Swift shell, macOS UI, WebSocket bridge server

Python backend — src/agent.py — all LLM calls, GitHub operations, build orchestration

Start: Click ForgeAgent.app. Never run python agent.py from terminal directly — this breaks the UI connection.

Stop: Use /quit at the forge> prompt, or at an approval gate. Never use pkill without reading §4.3 first.

Version: Check cat /Users/tgould/Agents/forge-dev-agent/VERSION

## 3. Before You Start — Clean Run Checklist

Run through this checklist before every build session. Skipping steps leads to regeneration loops and wasted token spend.

### 3.1 GitHub Cleanup

# Delete all branches from the previous run
# Do this from github.com/todd-yousource-ai/Dev-Agent/branches
# Delete all branches starting with forge-agent/build/consensusdevagent-*
# Keep: main, forge-agent/build/consensusdevagent/prds (if it has JSON files)

Why: Old branches accumulate CI failures and confuse the branch monitor. The agent creates new branches automatically.

### 3.2 Local State Cleanup

# Wipe local thread state
rm /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json

# Verify it's gone
ls /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/

Why: A stale state file from a previous run will be offered as a resume option at startup. If it has incomplete or corrupt PR plans, it will cause regeneration loops. Start clean.

### 3.3 Verify .env

cat /Users/tgould/Agents/forge-dev-agent/.env | grep -E "ANTHROPIC|OPENAI|GITHUB" | head -5

Confirm all three API keys are present. A missing key causes silent failures that look like LLM timeouts.

### 3.4 Verify TRD Documents

ls /Users/tgould/Agents/Mac-Docs/*.docx | wc -l
# Should show 17 or more

The agent loads all .docx files from Mac-Docs/ at startup. Missing docs means the LLM generates with less context.

### 3.5 Check Agent Version

cat /Users/tgould/Agents/forge-dev-agent/VERSION
# Should show the latest version (e.g., 38.98.0)

## 4. Startup and Resume

### 4.1 Normal Startup

Click ForgeAgent.app

Wait for forge> prompt (bootstrap takes ~45 seconds — Rust installer may pause up to 10s, this is normal)

If a previous build exists, you will see:

Found 1 incomplete build thread(s):
[1] ConsensusDevAgent   0/26 PRDs   0 PRs done   (2h ago)
Type a number to resume, or press Enter to start fresh:

Type 1 to resume, or press Enter to start fresh

### 4.2 When to Type 1 vs /ledger resume vs Enter

Situation | Command | What happens
Resume prompt shows and you want to continue | Type 1 | Restores from local state, auto-recovers GitHub JSON if needed
Resume prompt shows but local state is stale/wrong | Press Enter, then /clear local | Start fresh
No resume prompt, but you know a build was running | Type /ledger resume | Reconstructs from GitHub ledger + JSON files
Starting a brand new build | Press Enter | New scope/PRD/PR pipeline

Important: /ledger resume is for disaster recovery only — when local state is completely gone. For normal restarts, always type 1. The local state restore is faster and more complete than ledger reconstruction.

### 4.3 The 0 PRs done Situation

If the resume prompt shows 0/26 PRDs, 0 PRs done after you know PRs were completed previously, the local state has empty pr_plans_by_prd. Type 1 anyway — the agent will automatically check GitHub for saved PR plan JSON files and recover them before deciding to regenerate.

You will see in the build output:

↻  Local PR plans empty — checking GitHub for saved plans...
✓  Recovered 12 PR plans from GitHub — skipping regeneration

If you see ⚠  No PR plans found on GitHub — will regenerate, the PR plans were never committed to GitHub (they were generated before v38-91). Regeneration is unavoidable in this case.

## 5. The Build Phases

Understanding which phase the build is in tells you what you can and cannot do safely.

### 5.1 Phase 1: PRD Generation (~30–45 minutes)

What’s happening: The agent generates 26 PRD documents using consensus AI, then generates the PR plan for each PRD. Each completed PR plan is saved to both local disk and GitHub.

Observable: Messages like Spec complete for PR #1 in 141.2s

What you CAN do: - Watch the build log - Apply patches using the sentinel workflow (see §7)

What you CANNOT do safely: - Kill the agent without applying a patch first — state from the current 30-second autosave window may be lost - Apply a patch without using the sentinel workflow

If interrupted: Restart, type 1. The agent checks GitHub for any completed PR plan JSON files and recovers them. Only uncommitted plans need to regenerate.

### 5.2 Phase 2: PR Execution (~3–8 hours for 23 PRs)

What’s happening: For each PR spec, the agent generates code, runs tests locally (up to 20 attempts), then pushes to GitHub and waits for CI. If CI fails, it autonomously fixes and re-runs CI (up to 3 cycles).

Observable: Messages like Running tests (attempt 1/20)... and CI notification sent: PR #41 PASSED

What you CAN do: - Apply patches using the sentinel workflow - Walk away and let it run — autosave handles state every 30 seconds - Check GitHub PRs tab to see which PRs have passed CI

Batch boundaries: Every 5 PRs the agent pauses and asks Continue with next 5 PRs for PRD-001? (yes / done). This is a safe window to apply patches without the sentinel protocol if needed.

If interrupted: Restart, type 1. Already-completed PRs are skipped. The current in-progress PR restarts from code generation.

## 6. State Persistence — How It Works

### 6.1 What Gets Saved and When

Event | What gets saved | Where
Every 30 seconds (autosave) | Full thread state | Local disk
Patch sentinel detected | Immediate full flush | Local disk
PR plan generated | Full PRSpec JSON | GitHub prds branch
PR plan generated | Markdown summary | GitHub prds branch
PR completed | Completion record | Local disk + BUILD_LEDGER.json
Clean exit | Final state flush | Local disk

### 6.2 What the State File Contains

# Inspect current state
cat /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json \
  | python3 -m json.tool | grep -E '"state"|"prd_count"|"pr_plans"' | head -10

Key fields to check: - "state": should be "pr_pipeline" if PR plans exist - PR plan count: grep -c "pr_num" — should match expected PR count per PRD

### 6.3 State Saved to GitHub

After each PR plan generates, two files appear in the GitHub prds branch:

prds/consensusdevagent/prd-001-pr-plan.md    # Human-readable table
prds/consensusdevagent/prd-001-pr-plan.json  # Full machine-readable specs

The JSON file is the disaster recovery backup. If local state is ever completely lost, the agent reads these files on resume and reconstructs the full plan.

## 7. Applying Patches Mid-Run (Sentinel Workflow)

### 7.1 The Safe Workflow

Never kill the agent before running the patch. Always run the patch first, then kill.

# Step 1: Run the patch (this writes the sentinel and flushes state)
cd /Users/tgould/Agents/forge-dev-agent
python patch.py /path/to/forge-dev-agent-vNN.zip

# Step 2: Wait for confirmation
# You will see:
#   ✓  Backup: backup-v38-97-0-20260320-180942
#   Applying 69 file(s)...
#   ✓  Applied: 69 files
#   ✓  Cleared __pycache__ (stale bytecode removed)
#   ✓  Validation passed
#   Patch complete: 38.97.0 → 38.98.0

# Step 3: Kill the agent (state is already on disk)
pkill -f agent.py
pkill -f bridge.py

# Step 4: Click ForgeAgent.app to restart
# Step 5: Type 1 to resume

### 7.2 Why This Order Matters

When patch.py starts: 1. It writes workspace/.patch_in_progress (the sentinel file) 2. The autosave loop sees the sentinel within 1 second and flushes state to disk immediately 3. patch.py waits 2 seconds (state guaranteed on disk) 4. patch.py overwrites source files 5. You then kill the agent — state is already safe

If you kill the agent before running the patch, you may lose up to 30 seconds of state (the autosave interval). During active build execution that 30-second window often contains a completed LLM call that will need to be re-run.

### 7.3 If the Agent Is at an Approval Gate

If the build is paused waiting for your input (yes/skip/stop, batch continuation), you do not need the sentinel workflow. Type your response first, wait for the next phase to begin, then apply the patch using the sentinel workflow.

### 7.4 What Happens If You Get It Wrong

If you accidentally kill before patching: 1. Apply the patch (the agent is already dead, sentinel is not needed) 2. Restart 3. Type 1 4. State may be 30 seconds behind — unlikely to cause regeneration unless it was exactly mid-PR-plan-generation

## 8. When Things Go Wrong

### 8.1 PRs Are Regenerating Every Restart

Symptom: After restart, the agent shows 0 PRs done and begins Generating spec for PR #1...

Diagnosis:

cat /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json \
  | python3 -m json.tool | grep -E '"state"|pr_plans' | head -5

If "state": "prd_gen" and pr_plans_by_prd is empty {}, the state was saved before PR plans were generated.

Fix: Check GitHub for JSON files:

github.com/todd-yousource-ai/Dev-Agent/tree/forge-agent/build/consensusdevagent/prds

If prd-001-pr-plan.json exists, type 1 and the agent will auto-recover. If not, type /ledger resume — it may reconstruct partial plans from the ledger.

If neither works, the plans need to be regenerated. Let it run uninterrupted this time.

### 8.2 UI Not Opening

Symptom: Click ForgeAgent.app, nothing happens or UI is blank.

Cause: Previous agent/bridge process still running, or startup hanging on Rust download.

Fix:

pkill -f agent.py; pkill -f bridge.py
# Wait 3 seconds
# Click ForgeAgent.app

If it still hangs, check Terminal for the bootstrap status. The Rust installer sometimes pauses for 10 seconds — this is normal. Wait for it to either succeed or fail before assuming a hang.

### 8.3 Path is not defined Error

Symptom: ERROR Unhandled error in PR #N: name 'Path' is not defined

Cause: Old bug in CI fix loop code (fixed in v38-97). Apply latest patch.

### 8.4 untitled.py Still Appearing in CI

Symptom: CI shows ruff (invalid-syntax): src/untitled.py

Cause: PR was generated before v38-98 which fixed the impl_files population bug. The spec has empty impl_files.

Fix: This PR’s branch has broken code. The CI fix loop will attempt to fix it — but untitled.py is a structural issue, not a code issue. It’s better to delete the branch, wipe that specific PR from local state, and let it regenerate with the fixed code.

Or: let the current run finish and start clean tomorrow with v38-98 — the impl_files fix means this won’t happen on new PRs.

### 8.5 CI Keeps Failing After 3 Fix Cycles

Symptom: PR #N left as draft — CI failed after 3 CI fix cycles.

What it means: The CI failure is a persistent environment issue not addressable by LLM fix — likely a structural test dependency or a missing package that requires manual requirements.txt edit.

Fix: 1. Click the PR link in the build log 2. Read the CI failure annotations 3. If it’s a missing package: add it to requirements.txt manually, commit to that branch 4. CI will re-run and pass 5. Manually mark the PR ready for review in GitHub

### 8.6 BUILD_LEDGER.json Write Timeouts

Symptom: WARNING Retrying (GithubRetry(total=9...)) after ReadTimeoutError

What it means: GitHub API rate limiting on the ledger file. Non-fatal — the build continues. The ledger is not the primary persistence mechanism (local disk and JSON files are).

No action needed. If it persists more than 2 minutes on a single PR, it may be a GitHub service degradation. Check github.com/status.

### 8.7 IndexError: list index out of range in Strategy Selection

Symptom: IndexError: list index out of range in failure_handler.py around the strategy list.

Cause: Old bug — strategy list had 3 entries but loop ran up to 6+ attempts (fixed in v38-88). Apply latest patch.

## 9. Token Cost Management

### 9.1 Cost Drivers

Driver | Cost range | Prevention
PR plan regeneration | $5–15 per regeneration cycle | Don’t interrupt PRD generation phase
20-pass fix loop per PR | $0–7 per PR | Good PR specs with clear impl_files
CI fix cycles | $1–3 per CI cycle | Ensure requirements.txt is complete
Repeated restarts mid-run | Multiplies all of above | Use sentinel workflow for patches

### 9.2 Running Cost Check

# Check current API usage
# Anthropic: console.anthropic.com
# OpenAI: platform.openai.com/usage

### 9.3 Warning Signs

Stop and investigate if: - Total spend exceeds $150 before PRD-001 is complete - The same PR has been attempted more than 5 times - The build has been running more than 8 hours without completing PRD-001

### 9.4 Emergency Stop

If you need to stop immediately: 1. Apply the latest patch first (sentinel will flush state) 2. Then pkill -f agent.py; pkill -f bridge.py 3. State is preserved. Restart tomorrow, type 1.

Do NOT just close the terminal window — the agent process continues running in the background.

## 10. The Clean Run Protocol for Tomorrow

This is the exact sequence for a successful uninterrupted build run starting from scratch.

### Step 1: Prepare (5 minutes)

# 1. Verify latest version is installed
cat /Users/tgould/Agents/forge-dev-agent/VERSION
# Should be 38.98.0 or higher

# 2. Delete local state
rm /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/consensusdevagent.json

# 3. Verify .env has all keys
grep -c "=" /Users/tgould/Agents/forge-dev-agent/.env
# Should be at least 5 lines

### Step 2: GitHub Cleanup (5 minutes)

Go to github.com/todd-yousource-ai/Dev-Agent/branches and delete: - All branches starting with forge-agent/build/consensusdevagent-pr* - Keep: main - Optional keep: forge-agent/build/consensusdevagent/prds (has JSON recovery files)

### Step 3: Start and Scope (3 minutes)

Click ForgeAgent.app

Wait for bootstrap (45 seconds)

Press Enter at resume prompt (starting fresh)

Type /prd start

Enter intent: Build the complete ConsensusDevAgent

Confirm scope when prompted

### Step 4: PRD Generation — Do Not Interrupt (30–45 minutes)

Watch the build log — Generating spec for PR #N... messages confirm progress

Every completed plan saves to disk and GitHub automatically

Do NOT apply patches

Do NOT restart

You will know this phase is complete when you see PR PLAN — PRD-001: Cross-TRD Architecture... and 23 PRs to implement

### Step 5: PR Execution — Monitor and Patch Safely (3–8 hours)

Watch for CI notification sent: PR #N PASSED — each one is real progress

Apply any patches using the sentinel workflow (§7)

At batch boundaries (Continue with next 5 PRs?) you can safely apply patches without sentinel

If you need to stop overnight, let the current PR complete its CI check, then apply patch + pkill

### Step 6: Completion

When all 23 PRs for all 26 PRDs complete: - The agent prints a build summary with total PRs merged and cost - Review PRs on GitHub and merge manually (auto-merge is not enabled by design)

## 11. Reference: Key File Locations

File | Path | Purpose
Agent source | /Users/tgould/Agents/forge-dev-agent/src/ | Python backend
Thread state | /Users/tgould/Agents/forge-dev-agent/workspace/todd-gould/state/threads/ | Local persistence
Patch backups | /Users/tgould/Agents/forge-dev-agent/workspace/patches/ | Pre-patch snapshots
Audit logs | /Users/tgould/Agents/forge-dev-agent/logs/todd-gould/ | Build history
TRD documents | /Users/tgould/Agents/Mac-Docs/ | LLM context
Environment config | /Users/tgould/Agents/forge-dev-agent/.env | API keys
Sentinel file | workspace/.patch_in_progress | Patch state flush trigger

## 12. Reference: Key Commands

Command | When | What it does
Type 1 | At startup resume prompt | Restore from local state
Press Enter | At startup resume prompt | Start fresh build
/ledger resume | When local state is gone | Reconstruct from GitHub
/backup | At forge> prompt | Archive current state
/status | At forge> prompt | Show build progress
/clear local | At forge> prompt | Wipe local thread state (with confirmation)
/quit | At gate or forge> prompt | Clean shutdown with final save
python patch.py <zip> | Terminal | Apply version upgrade

Commands that only work at gates or forge> prompt (not mid-execution): /quit, /backup, /save, /ledger status

Why: During active build execution, stdin is consumed by the build loop’s input() calls. Chat box input goes to whatever gate is currently blocking (approval gates, batch continuation prompts). Commands typed mid-execution are interpreted as gate responses.

## Appendix A: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-20 | YouSource.ai | Initial document — operational lessons from March 2026 sprint