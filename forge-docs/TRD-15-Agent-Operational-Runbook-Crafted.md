# TRD-15-Agent-Operational-Runbook-Crafted

_Source: `TRD-15-Agent-Operational-Runbook-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-15: Agent Operational Runbook

Technical Requirements Document — v1.1

Product: Crafted Document: TRD-15: Agent Operational Runbook Version: 1.1 Status: Updated — Build Memory + Context Trim Console Outputs (March 2026) Author: Todd Gould / YouSource.ai Previous Version: v1.0 (2026-03-20) Depends on: TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality)

## What Changed from v1.0

Two additions. All sections from v1.0 are unchanged.

§12a — Build memory console outputs: what operators see at startup and during PR execution (new)

§11a — New file location: workspace/{engineer_id}/build_memory.json (new)

## §12a. Build Memory and Context Trim Console Outputs (New in v1.1)

### Startup — Build Memory Summary

If prior completed PRs exist from previous runs, the agent displays a summary immediately after document loading at startup:

Build memory: 8 PR(s) completed across prior run(s).
  CI clean first-pass: 5/8 PRs    Avg fix attempts: 2.4
Completed PRs (most relevant patterns available for injection):
  PR #1: Consensus Engine core  [✓ CI clean]  → src/consensus.py
  PR #2: Build Director phase split  [⚠ 7 attempts]  → src/build_director.py
  PR #3: Auth module  [✓ CI clean]  → src/auth.py
  ...

This output is informational — it tells you how the previous run went and confirms the agent has learned from it. No action required.

### During PR Execution — Build Memory Record

After each successful PR completes (after CI passes), a memory record is written:

✓ PR #3: Auth module
  💾 Build memory: PR #3 recorded (CI clean)

  ✓ PR #7: Failure handler multi-turn loop
  💾 Build memory: PR #7 recorded (4 attempts)

The label in parentheses tells you immediately whether this PR passed CI on the first attempt (CI clean) or required fix loop passes (N attempts). This is your real-time signal of code generation health across the build.

### During Fix Loop — Context Trim

When the fix loop’s conversation history grows past the 30k token threshold, old turns are trimmed automatically:

Running tests (attempt 9/20)...
  ✗ Assertion Error
  Strategy: test_driven (assertion_error) — multi-turn consensus...
  ✂  Context trimmed: 8 old turns removed (42,300 → 18,100 est. tokens)
  Winner: claude

This is normal and expected for PRs requiring many fix attempts. The trim preserves the original problem statement (first turn) and the most recent 3 exchange pairs. No action required — the build continues normally.

### What to Watch For

Output | Meaning | Action
💾 Build memory: PR #N recorded (CI clean) | PR passed on first test run — no fix loop needed | None — good signal
💾 Build memory: PR #N recorded (N attempts) | PR needed N fix loop passes before tests passed | None unless N > 10
✂ Context trimmed: N old turns removed | Fix loop history trimmed to prevent context rot | None — automatic
Build memory: N PR(s) completed… at startup | Prior run data loaded — generation will have pattern context | None

## §11a. New File Location: build_memory.json (New in v1.1)

A new persistent file is created in the workspace directory:

/Users/tgould/Agents/crafted/workspace/todd-gould/build_memory.json

Property | Value
Created | Automatically on first successful PR completion
Updated | After every successful PR (atomic write via temp file)
Cleared by thread state wipe | No — intentionally survives rm on thread JSON
Cleared by version upgrade (patch.py) | No — workspace/ directory is not touched by patches
Manual clear | Delete the file, or call mem.clear() from a script
Size | ~1-5KB per 10 PRs — grows slowly

Important: do not delete build_memory.json as part of the ‘clean run checklist’ (§3). Unlike thread state, build memory is designed to persist across builds. Deleting it loses the cross-run learning accumulated from prior runs.

The only reason to delete it is if you want the agent to start completely fresh on a new subsystem with no prior context — for example, when switching from one build project to a different one entirely.

## Updated Reference: Key File Locations

File | Path | Purpose
Agent source | /Users/tgould/Agents/crafted/src/ | Python backend
Thread state | /Users/tgould/Agents/crafted/workspace/todd-gould/state/threads/ | Local persistence — cleared for fresh builds
Build memory | /Users/tgould/Agents/crafted/workspace/todd-gould/build_memory.json | Cross-run PR notes — NOT cleared for fresh builds
Patch backups | /Users/tgould/Agents/crafted/workspace/patches/ | Pre-patch snapshots
Audit logs | /Users/tgould/Agents/crafted/logs/todd-gould/ | Build history
TRD documents | /Users/tgould/Agents/Mac-Docs/ | LLM context
Environment config | /Users/tgould/Agents/crafted/.env | API keys
Sentinel file | workspace/.patch_in_progress | Patch state flush trigger

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — operational lessons from March 2026 build sprint
1.1 | 2026-03-22 | Build memory console outputs: startup summary, per-PR record line, context trim notification (§12a). New file location: workspace/{engineer_id}/build_memory.json, note that it intentionally survives thread state wipes (§11a). Updated key file locations table.