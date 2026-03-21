# TRD-13-Recovery-State-Management

_Source: `TRD-13-Recovery-State-Management.docx` — extracted 2026-03-21 21:32 UTC_

---

# TRD-13: Recovery and State Management

Technical Requirements Document — v3.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-13: Recovery and State Management
Version | 3.0
Status | Updated — Session 2 Production Implementation (March 2026)
Author | Todd Gould / YouSource.ai
Previous Version | v2.0 (2026-03-20 AM)
Depends on | TRD-3 (Build Pipeline), TRD-4 (Multi-Agent Coordination), TRD-12 (Backend Runtime)

## What Changed from v2.0

v2.0 documented the StateAutosave daemon, patch sentinel, and GitHub JSON recovery — all operating at the PRD/PR-plan level. This version documents the critical per-PR stage checkpoint system added in the second sprint, which addresses the most expensive failure mode: losing multiple completed PRs to a crash mid-batch.

Major additions in v3.0: - Per-PR save: state saved after each individual PR completes, not per batch (§2.2 — new failure mode) - Mid-PR stage checkpoints: four save points within a single PR execution (§7 — new) - in_progress_pr field on BuildThread — persists checkpoint across restarts (§7.1) - _save_pr_checkpoint() helper — wires all stage transitions (§7.2) - Restart sequence: exactly automatic, type 1, no command needed (§8 — clarified) - Recovery smoke tests: 29 automated tests validating all recovery paths (§11 — new)

Sections 1–6 and 9–10 are unchanged from v2.0. Only the sections below are new or updated.

## 2.2 New Failure Mode: Batch-Only State Save (Added in v3.0)

### Root Cause

In v2.0, thread_store.save() fired only after an entire 5-PR batch completed. The save point was here:

# v2.0 — save only after full batch
for exc in executions:  # batch of 5 PRs
    success = await self._execute_pr(exc, thread)
    if success:
        thread.completed_pr_nums_by_prd[prd_id].append(exc.spec.pr_num)
        # NO SAVE HERE

# Save fires here — after all 5 PRs
self._thread_store.save(thread)

Impact: A crash during PR #3 of a batch lost PRs #1 and #2 entirely. On restart, all 5 PRs re-executed.

Financial cost: Each PR costs approximately $0.63 in LLM tokens (code generation + 5 fix attempts average). A crash before the 5th PR in a batch wastes 4 × $0.63 = $2.52. Over a 150-PR build with 10 expected restarts, this accumulates to $25+ in wasted tokens, plus the time cost of re-running.

### Fix (v3.0)

State is now saved immediately after each individual PR completes:

for exc in executions:
    success = await self._execute_pr(exc, thread)
    if success:
        thread.completed_pr_nums_by_prd[prd_id].append(exc.spec.pr_num)
        # Save immediately — crash during next PR loses only that PR
        self._thread_store.save(thread)

Result: A crash during PR #3 preserves PRs #1 and #2. On restart, only PR #3 re-executes from the beginning. Maximum loss is one PR’s token cost (~$0.63), not the entire batch.

## 7. Mid-PR Stage Checkpoints (New in v3.0)

### 7.1 The Problem Within a Single PR

Even with per-PR saves, a single PR can take 25+ minutes: code generation (60–120s), 20 local fix loop attempts (up to 40 min), and CI wait (1–3 min × 3 cycles). A crash at minute 24 — after tests have passed but before CI completes — previously meant restarting from code generation.

The per-PR save in §2.2 prevents losing prior PRs. Stage checkpoints prevent losing progress within the current PR.

### 7.2 Checkpoint Stages

Four checkpoints are saved within each PR execution:

Stage | When saved | What it means
branch_opened | After branch created + draft PR opened on GitHub | Branch and PR exist; safe to retry without creating duplicates
tests_passed | After local pytest passes (all LLM fix attempts done) | All LLM work complete; only GitHub commit + CI remain
committed | After code committed to GitHub branch | Code is on GitHub; CI just needs to run
ci_passed | After GitHub Actions green | CI done; only mark-ready step remains

The in_progress_pr field on BuildThread persists the current checkpoint:

thread.in_progress_pr = {
    "pr_num":     exc.spec.pr_num,
    "pr_number":  exc.pr_number,      # GitHub PR number
    "pr_url":     exc.pr_url,
    "impl_code":  exc.impl_code,      # generated code preserved
    "test_code":  exc.test_code,
    "checkpoint": "tests_passed",     # last reached stage
    "branch":     exc.spec.branch,
    "prd_id":     prd_id,
}

### 7.3 _save_pr_checkpoint() Helper

All checkpoint saves go through a single helper:

def _save_pr_checkpoint(self, exc: PRExecution, thread: BuildThread, stage: str) -> None:
    """
    Save state immediately after a PR reaches a new stage.
    A crash at any stage resumes from here, not from code generation.
    """
    exc.checkpoint = stage
    thread.in_progress_pr = {
        "pr_num": exc.spec.pr_num,
        "checkpoint": stage,
        "impl_code": exc.impl_code,
        ...
    }
    self._thread_store.save(thread)

### 7.4 Stage Transition Map

_open_draft_pr() completes
    → _save_pr_checkpoint(exc, thread, "branch_opened")

run_fix_loop() returns passed=True
    → _save_pr_checkpoint(exc, thread, "tests_passed")

_safe_commit() writes code to GitHub
    → _save_pr_checkpoint(exc, thread, "committed")

ci_result.passed == True
    → _save_pr_checkpoint(exc, thread, "ci_passed")

_mark_pr_ready() + completed_pr_nums_by_prd updated
    → self._thread_store.save(thread)   ← final per-PR save

### 7.5 Cost Analysis

Recovery granularity | Max tokens lost on crash | Max time lost
Per-batch (v2.0) | 4 PRs × ~$0.63 = $2.52 | 4 PRs × 25 min = 100 min
Per-PR (v3.0 §2.2) | 1 PR × ~$0.63 = $0.63 | 1 PR × 25 min = 25 min
Per-stage (v3.0 §7) | 1 code generation = $0.18 | ~2 min

Over a 150-PR build with 10 restarts: per-stage checkpoints save approximately $23 and 16 hours compared to v2.0 batch-only saves.

## 8. Restart Sequence (Clarified in v3.0)

### 8.1 Normal Restart — No Command Required

Recovery is automatic at startup. No /resume, no /continue, no /ledger resume command needed for normal restarts.

The sequence:

1. Click ForgeAgent.app
2. Agent bootstraps (~45 seconds)
3. Agent detects incomplete build automatically:

   ┌──────────────────────────────────────────────────────┐
   │ Found 1 incomplete build thread(s):                  │
   │   [1] ConsensusDevAgent   2/26 PRDs  14 PRs done     │
   │       (0h ago)                                       │
   │       Build the complete ConsensusDevAgent           │
   │                                                      │
   │ ⟩ Type a number to resume, or press Enter for fresh  │
   └──────────────────────────────────────────────────────┘

4. Type: 1
5. director.resume() fires — reads state, skips completed PRs,
   resumes at correct stage within the in-progress PR

One keystroke. That’s the entire restart procedure.

### 8.2 What resume() Does with Checkpoints

Reads thread state from disk
  → completed_pr_nums_by_prd = {PRD-001: [1, 2, 3]}
  → in_progress_pr = {pr_num: 4, checkpoint: "tests_passed",
                       impl_code: "def foo(): ..."}

For PRD-001:
  → PRs 1, 2, 3: in completed_pr_nums_by_prd → skipped ✓
  → PR 4: checkpoint="tests_passed"
           code already written and tested
           resumes at commit stage (skips LLM calls)
  → PR 5: pending → starts from code generation

### 8.3 Recovery Command Reference

Situation | How to recover
Normal restart (local state exists) | Type 1 at startup prompt
Local state empty, GitHub JSON exists | Type 1 — auto-recovery fires
Local state wiped (disk failure) | Type /ledger resume
Fresh start | Press Enter at startup prompt

/ledger resume is disaster recovery only — for when local disk is gone. The normal flow never needs it.

## 11. Recovery Smoke Tests (New in v3.0)

Automated tests validate all recovery paths without requiring a real build. Run with:

PYTHONPATH=src python3 -m pytest tests/test_smoke_recovery.py -v -s

### 11.1 Test Coverage

Test class | What it validates
TestPerPRStateSave | thread_store.save() called after each individual PR, not batch end
TestResumeSkipsCorrectPRs | After PRs 1–5 done, resume starts at PR 6
TestStateMachineResume | State forced to pr_pipeline when plans exist; never re-enters prd_gen
TestMidBatchCrashRecovery | Crash at PR 3 of 5 → resumes at PR 4; max loss = 1 batch on no saves
TestGitHubJSONRecovery | Wipe local disk → recover from GitHub JSON → impl_files preserved
TestAutosaveDaemon | State forced correctly; None thread handled; sentinel triggers flush
TestRecoveryDiagnostics | Identifies correct recovery path from saved state
TestMidPRCheckpoints | All 4 stage checkpoints wired; in_progress_pr persists; cost analysis

### 11.2 Key Test: Mid-Batch Crash

def test_crash_after_pr3_resumes_from_pr4(self, tmp_path):
    """
    Simulate: batch of 5 PRs, PRs 1-3 complete with per-PR saves,
    crash during PR 4. After restart, should resume from PR 4, not PR 1.
    """
    # PRs 1, 2, 3 each save state immediately on completion
    for pr_num in [1, 2, 3]:
        thread.completed_pr_nums_by_prd["PRD-001"].append(pr_num)
        store.save(thread)  # per-PR save

    # === CRASH during PR 4 ===
    saved = store.load("testsystem")
    done_nums = set(saved["completed_pr_nums_by_prd"]["PRD-001"])
    assert done_nums == {1, 2, 3}  # PRs 1-3 preserved

    remaining = [n for n in range(1, 24) if n not in done_nums]
    assert remaining[0] == 4  # resumes at PR 4, not PR 1

### 11.3 Key Test: Cost Analysis

The cost test documents the financial rationale and runs automatically:

Cost analysis — batch of 5 PRs, crash at PR 5:
  Batch-only save (v2.0):       $2.52 lost (4 PRs)
  Per-PR save (v3.0 §2.2):      $0.63 lost (1 PR max)
  Per-stage checkpoint (v3.0 §7): $0.18 lost (1 generation max)
  Savings vs batch-only:         $2.34 per crash

## Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial specification
2.0 | 2026-03-20 AM | YouSource.ai | StateAutosave, patch sentinel, GitHub JSON recovery, resume routing fixes, production failure modes documented
3.0 | 2026-03-20 PM | YouSource.ai | Per-PR save (batch-only was $100+ risk), mid-PR stage checkpoints, in_progress_pr field, _save_pr_checkpoint(), restart sequence clarified (automatic, type 1), 29 recovery smoke tests