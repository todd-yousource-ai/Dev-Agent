# TRD-13-Recovery-State-Management-Crafted

_Source: `TRD-13-Recovery-State-Management-Crafted.docx` — extracted 2026-03-24 15:38 UTC_

---

TRD-13: Recovery and State Management

Technical Requirements Document — v6.0

Field | Value
Product | Crafted
Document | TRD-13: Recovery and State Management
Version | 6.0
Status | Updated — BuildRules Self-Improving Rules Engine (March 2026)
Author | Todd Gould / YouSource.ai
Previous Version | v5.0 (2026-03-22)
Depends on | TRD-3 (Build Pipeline), TRD-4 (Multi-Agent), TRD-12 (Backend Runtime)

# 1. Purpose and Scope

This TRD defines the recovery and state management subsystem for the Crafted Dev Agent. It specifies the deterministic, operator-facing save/restore/continue lifecycle that ensures a build session of 26+ PRDs and ~150 PRs can survive restarts, patches, crashes, and machine reboots without losing progress or requiring expensive LLM regeneration.

In scope: StateAutosave daemon, patch sentinel protocol, three-layer persistence model, GitHub recovery path, resume routing, per-PR stage checkpoints, context manager, build memory, and build rules engine. Out of scope: multi-agent coordination (TRD-4), notification gateway, hot reload (deferred to v3.0).

# 2. Production Failure Modes

The following failure modes were identified in the March 2026 build sprint and fixed in v2.0–v4.0:

Failure Mode | Root Cause | Fix
PR plan regeneration on restart | pr_plans_by_prd stored as single dict, iterated as key strings | Detect and wrap in list before iterating
State saved as prd_gen, re-enters PRD generation | Autosave wrote state=prd_gen during PRD approval | Force state=pr_pipeline on every save when pr_plans exist
State lost during patch application | Patch overwrote source files before autosave fired | Patch sentinel protocol — flush before writing files
/ledger resume reconstructed incomplete state | Ledger only had PRD-001 entries; others timed out | Augment with GitHub JSON files after ledger read
impl_files always empty → untitled.py | PRPlanner omitted impl_files from arbitrated response | PRPlanner now explicitly reads impl_files and test_files
completed_prd_ids lost completed PRDs | set.add() called on wrong variable | Fixed to call list.append() on correct field
422 on PR reopen → agent crash | pr_number=None when create_pr returned 422 | Recover by finding existing open PR on the branch

# 3. Three-Layer Persistence Model

## 3.1 State Layers

Layer | Location | Contents | Recovery
Layer 1 — Local disk | workspace/<engineer>/state/threads/<slug>.json | Full PRSpec objects, build state, completed PR tracking | Type 1 at startup resume prompt
Layer 2 — GitHub JSON | prds/<subsystem>/<prd-id>-pr-plan.json on prds branch | Full PRSpec JSON per PRD — survives disk wipe | Automatic in resume() or /ledger resume
Layer 3 — GitHub ledger | forge-coordination/BUILD_LEDGER.json | PR status and completion tracking | /ledger resume (partial recovery)

Layer 1 is the primary recovery path — fastest, most complete. Layer 2 is disaster recovery — survives full disk wipe. Layer 3 alone is insufficient (missing PRSpec detail for most PRDs).

# 4. StateAutosave Daemon

## 4.1 Design

Background thread saves BuildThread state to disk every 30 seconds regardless of build loop activity. Wakes every 1 second to check for patch sentinel. Hash-compares state before writing to avoid redundant disk writes.

class StateAutosave:

INTERVAL = 30  # seconds between save attempts

def _save_now(self):

thread = self._director._thread

if thread is None: return

# Force pr_pipeline state when PR plans exist

if getattr(thread, 'pr_plans_by_prd', {}):

thread.state = 'pr_pipeline'

# Hash-compare to avoid redundant writes

...

if current_hash != self._last_hash:

self._thread_store.save(thread)

## 4.2 State Forced to pr_pipeline

The autosave daemon forces thread.state = 'pr_pipeline' on every save when pr_plans_by_prd is non-empty. Critical: prevents a crash during PRD approval from causing PRD regeneration on the next restart.

# 5. Patch Sentinel Protocol

## 5.1 Problem

Applying a patch mid-run caused state loss: patch overwrites source files → agent crashes → autosave hadn't fired in last 30 seconds → state lost.

## 5.2 Solution

# patch.py writes sentinel BEFORE overwriting source files:

_sentinel = self._root / 'workspace' / '.patch_in_progress'

_sentinel.write_text('1')

time.sleep(2)  # Give autosave 2 seconds to flush

_sentinel.unlink(missing_ok=True)

# Then write source files

# StateAutosave checks sentinel every second:

if _sentinel.exists():

self._save_now()   # Flush immediately

## 5.3 Safe Patch Workflow

Run python patch.py /path/to/vNN.zip → Wait for ✓ Applied message (sentinel flush complete) → pkill agent and bridge → Restart → type 1.

Never pkill before patching. The 2-second window is a practical guarantee, not a hard guarantee against SIGKILL.

# 6. GitHub Recovery Path

## 6.1 PR Plan JSON Backup

Every completed PR plan is committed to GitHub as both markdown and JSON on the prds branch. The JSON contains complete PRSpec objects. Once committed, plans are permanently recoverable.

## 6.2 Automatic Recovery in resume()

When local pr_plans_by_prd is empty but GitHub JSON exists, resume() fetches all prd-id-pr-plan.json files from the prds branch and populates pr_plans_by_prd. Console output: ✓ Recovered N PR plans from GitHub — skipping regeneration.

## 6.3 /ledger resume with JSON Augmentation

/ledger resume now reads the BUILD_LEDGER.json first, then supplements with GitHub JSON files for any PRDs not covered by the ledger. This reconstructs complete state for all PRDs that have committed JSON files, not just PRD-001.

# 7. Resume Routing

Situation | Command | What happens
Local state exists | Type 1 at startup | director.resume(saved) — full local restore
Local state empty, GitHub JSON exists | Type 1 then auto-recovery | GitHub JSON fetched, pr_pipeline state set, execution begins
Local state empty, no GitHub JSON | Type /ledger resume | Ledger + JSON reconstruction, then execution
Clean start | Press Enter at startup | New build from scratch

## 7.2 State Detection

On resume, if pr_plans_by_prd is non-empty, thread.state is forced to pr_pipeline regardless of the saved state value. PRSpec reconstruction handles both list format (normal) and single-dict format (from older saves). PRDItem reconstruction handles both 'id' and 'prd_id' key names.

# 8. Per-PR Stage Checkpoints (v3.0)

## 8.1 Why This Exists

v2.0 saved state after each complete PR (not during). A crash mid-PR lost the entire PR's work — code generation, test fixes, CI fix cycles. For long PRs that took 30+ minutes, this was a significant cost.

## 8.2 Checkpoint Stages

Stage | Description
branch_opened | Branch created on GitHub; next resume skips branch creation
code_generated | Implementation and test code generated; next resume skips generation
tests_passed | Local tests passed; next resume skips local test loop
committed | Files committed to branch; next resume skips commit
ci_passed | CI passed; next resume skips CI wait

## 8.3 Implementation

_save_pr_checkpoint(exc, thread, stage) persists the in_progress_pr dict to thread state after each stage. On resume, the checkpoint stage is read and the PR execution resumes from that point. This is the mechanism that prevents $100+ losses from crashes during long fix loops.

# PRSpec.checkpoint field values:

# pending → branch_opened → code_generated →

# tests_passed → committed → ci_passed

# §9. ContextManager — Fix Loop History Trimming (New in v5.0)

## Why This Exists

The fix loop runs up to 20 attempts. By attempt 8–10, the history contains 16–20 messages each carrying complete file contents and CI logs. Token counts routinely exceed 60–80k, causing context rot — the model's attention spreads too thin.

This implements the vendor-recommended clear_tool_uses pattern: trim old turns while preserving the spec-anchor first turn and recent working context.

## Implementation

_ctx_mgr = ContextManager(

trigger_tokens=30_000,   # trim when estimated tokens exceed this

keep_tail=6,             # retain last 6 messages (3 exchange pairs)

min_savings_tokens=5_000,# skip trim if savings < this threshold

max_failure_chars=8_000, # truncate CI log/test output to this length

)

maybe_trim() preserves history[0] (spec-anchor first turn) and history[-keep_tail:] (most recent 3 exchange pairs). Discards middle turns. Estimates tokens from character count (3 chars/token ratio).

truncate_failure_output() caps CI logs at 8,000 chars, retaining 70% head (first failure — root cause) and 30% tail (summary, pass/fail counts). Saves ~40k chars (~13k tokens) per attempt.

# §10. BuildMemory — Cross-Run PR Note Persistence (New in v5.0)

## Storage

# Location: workspace/{engineer_id}/build_memory.json

# Format: JSON, one note per completed PR

# Survives: fresh installs, thread state wipes, version upgrades

# Cleared by: explicit mem.clear() call only — never automatic

The file lives in workspace/{engineer_id}/ alongside thread state JSON. Unlike thread state (which is cleared for fresh builds), build_memory.json is intentionally persistent. Clearing thread state does NOT clear build memory.

## Note Schema

Field | Type | Description
run_id | ISO timestamp | When this note was written
pr_num | int | PR number within the build
pr_title | str | PR title
subsystem | str | Build subsystem
impl_files | list[str] | Target implementation file paths
language | str | Programming language
patterns | list[str] | Up to 8 top-level class/function signatures extracted from generated code
ci_clean | bool | True if CI passed on the first test run
fix_attempts | int | Total fix loop attempts (1 = passed first time)
note | str | Optional summary (max 300 chars)

## Injection Points

startup_injection() — Called at agent startup after doc_store.load(). Shows total PRs, CI clean rate, avg fix attempts. Capped at 2,000 chars.

pr_generation_injection() — Called before code generation. Scores notes by file overlap (+10), subsystem (+5), title words (+2), recency (+1). Returns top 6 relevant notes with patterns. Capped at 1,200 chars.

record_pr() — Called after thread_store.save() in PR success path. Non-fatal. Deduplicates by pr_num (re-recording replaces existing entry).

# §11. BuildRules — Self-Improving Generation Rules (New in v6.0)

## Why This Exists

build_memory.py records what happened on each PR — patterns, CI clean rate, fix attempts. But observation alone doesn't change future behavior. BuildRules closes the loop: it analyzes the failure history, synthesizes actionable coding rules, and writes them to Mac-Docs where DocumentStore picks them up on the next run.

When the agent sees the same failure pattern 3+ times, it updates its own generation rules. The value compounds — each run the agent starts with more project-specific guidance derived from its own history.

## File Location

Property | Value
Module | src/build_rules.py
Rules file | Mac-Docs/build_rules.md
Loaded by | DocumentStore at startup (standard doc loading — no special injection)
Created | After first build run with ≥3 recurring patterns
Pruned | MAX_RULES_AGE=10 — oldest sections removed when exceeded
Cleared by | Manual deletion only — never automatic
Distinct from | build_memory.json (in workspace/) — rules file is in Mac-Docs

IMPORTANT: build_rules.md lives in Mac-Docs, not workspace. DocumentStore loads it automatically at startup. It should NOT be deleted when clearing workspace state for a fresh build.

## Trigger

analyze_and_update() is called at build completion (after mark_done()). Runs only if ≥3 PRs completed AND ≥1 pattern meets MIN_OCCURRENCES=3. A pattern qualifies when the same file or subsystem appears in 3+ PRs that each required >3 fix attempts.

## Rules Synthesis

One LLM call generates at most 8 specific, actionable rules from the pattern data. Rules are appended as a dated section to build_rules.md. Atomic write via temp file rename. Sections pruned to MAX_RULES_AGE=10 on each write.

## Console Output

# At build completion when rules were derived:

📋 Build rules: 4 rule(s) derived from 12 PRs and saved to Mac-Docs

# At startup when rules file exists:

📋 Build rules: 12 rule(s) active from 3 prior run(s) — loaded into generation context

## §7 Note — pr_type Test Example (Bug Fix in v6.0)

The PR_LIST_SYSTEM JSON schema was missing a concrete example for pr_type: "test". Without it, the model defaulted to 'implementation' for test-only PRs on every run — silently defeating pr_type routing without any error. Fixed by adding a fourth schema entry demonstrating pr_type: "test" with depends_on_prs. Found and fixed by the regression test suite (test_regression_taxonomy.py).

# 11. Acceptance Criteria

## Implemented

State autosaves every 30 seconds regardless of build loop activity

Patch application flushes state before source files change

PR plans committed to GitHub as JSON on generation

resume() automatically recovers PR plans from GitHub when local is empty

/ledger resume reconstructs complete state from GitHub (all PRDs, not just PRD-001)

state = pr_pipeline forced on save when PR plans exist

Per-PR stage checkpoints — resume from last checkpoint, not code generation restart

ContextManager trims history at 30k tokens, preserving spec-anchor first turn

BuildMemory persists PR notes across fresh installs

BuildRules derives actionable coding rules from build history after each run

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 | Production implementation: StateAutosave daemon, patch sentinel, GitHub JSON backup, automatic recovery in resume(), divergence root causes documented
3.0 | 2026-03-20 PM | Per-PR save (not batch-only), mid-PR stage checkpoints, in_progress_pr, _save_pr_checkpoint(), 29 recovery smoke tests
4.0 | 2026-03-21 | completed_prd_ids set.add() fix, enriched spec persistence, 422 PR recovery (pr_number=None eliminated), _slug scoping fix
5.0 | 2026-03-22 | ContextManager (§9): history trimming at 30k tokens, failure output truncation at 8k chars. BuildMemory (§10): cross-run PR notes, startup injection, per-PR generation injection.
6.0 | 2026-03-22 | BuildRules (§11): self-improving rules engine, MAX_RULES_AGE=10, atomic writes to Mac-Docs/build_rules.md. pr_type test example bug fix (§7 note).