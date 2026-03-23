# TRD-13-Recovery-State-Management-Crafted

_Source: `TRD-13-Recovery-State-Management-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-13: Recovery and State Management

Technical Requirements Document — v5.0

Product: Crafted Document: TRD-13: Recovery and State Management Version: 5.0 Status: Updated — Context Manager + Build Memory (March 2026) Author: Todd Gould / YouSource.ai Previous Version: v4.0 (2026-03-21) Depends on: TRD-3 (Build Pipeline), TRD-4 (Multi-Agent), TRD-12 (Backend Runtime)

## What Changed from v4.0

Two new modules. All sections from v4.0 are unchanged.

§9 — ContextManager: fix loop history trimming and failure output truncation (new)

§10 — BuildMemory: cross-run PR note persistence and injection (new)

## §9. ContextManager — Fix Loop History Trimming (New in v5.0)

### Why This Exists

The fix loop runs up to 20 attempts. Each turn appends a user message (failure output + full current implementation) and an assistant message (full regenerated implementation). By attempt 8–10, the history contains 16–20 messages, each carrying complete file contents and CI logs. Token counts routinely exceed 60–80k, causing context rot — the model’s attention spreads too thin to reason accurately about the current failure.

This implements the vendor-recommended clear_tool_uses pattern: trim old turns while preserving the spec-anchor first turn and recent working context.

### Implementation

Implemented in context_manager.py as ContextManager. Module-level instance _ctx_mgr in failure_handler.py is shared across all fix loop invocations.

_ctx_mgr = ContextManager(
    trigger_tokens=30_000,    # trim when estimated tokens exceed this
    keep_tail=6,              # retain last 6 messages (3 exchange pairs)
    min_savings_tokens=5_000, # skip trim if savings < this threshold
    max_failure_chars=8_000,  # truncate CI log/test output to this length
)

### maybe_trim() — History Trimming

Called after each assistant turn is appended to history. Estimates token count from character count (3 chars/token ratio). If above trigger_tokens:

Preserves history[0] — the spec-anchor first turn (original impl + tests + failure). This is the contract the model must satisfy; it must never be lost.

Preserves history[-keep_tail:] — the 6 most recent messages (3 exchange pairs). This is the working memory the model needs right now.

Discards middle turns — old failed attempts, CI logs from 8 attempts ago. These add noise without adding signal.

# After each assistant turn is appended:
claude_history, c_trim = _ctx_mgr.maybe_trim(claude_history)
openai_history, _      = _ctx_mgr.maybe_trim(openai_history)
if c_trim.triggered:
    print(f"  ✂  Context trimmed: {c_trim.turns_removed} old turns removed"
          f" ({c_trim.tokens_before:,} → {c_trim.tokens_after:,} est. tokens)")

### truncate_failure_output() — CI Log Truncation

Called before each failure output is added to a turn prompt. Caps CI/test output at max_failure_chars (8,000). Retains 70% from the head (first failure — usually the root cause) and 30% from the tail (summary line, pass/fail counts). Inserts a truncation notice when content is removed.

A 5,000-line pytest traceback contributes almost nothing beyond the first failure and the final summary. Truncating it saves ~40k chars (~13k tokens) per attempt.

### Token Estimation

Uses character count divided by 3.0 (conservative — real ratio is ~3.5 for code, ~4 for prose). Errs toward trimming slightly earlier. No tokenizer required — fast enough to run after every turn.

## §10. BuildMemory — Cross-Run PR Note Persistence (New in v5.0)

### Why This Exists

Each fresh install starts from TRDs and nothing else. Patterns from prior runs — which code structures succeeded, which CI configurations work, which interfaces were built — are thrown away. The model must re-discover everything from the spec alone on every run.

BuildMemory provides structured cross-run learning: after each successful PR, a compact note is written to disk. On the next run, these notes are injected at startup and into each PR’s generation context. The value compounds over 5–10 runs.

### Storage

# Location: workspace/{engineer_id}/build_memory.json
# Format: JSON, one note per completed PR
# Survives: fresh installs, thread state wipes, version upgrades
# Cleared by: explicit mem.clear() call only — never automatic

The file lives in workspace/{engineer_id}/ alongside thread state JSON. Unlike thread state (which is cleared for fresh builds), build_memory.json is intentionally persistent. Clearing thread state does not clear build memory.

### Note Schema

Field | Type | Description
run_id | ISO timestamp | When this note was written
pr_num | int | PR number within the build
pr_title | str | PR title
subsystem | str | Build subsystem (e.g. Crafted)
impl_files | list[str] | Target implementation file paths
language | str | Programming language
patterns | list[str] | Up to 8 top-level class/function signatures extracted from generated code
ci_clean | bool | True if CI passed on the first test run (no fix loop needed)
fix_attempts | int | Total fix loop attempts (1 = passed first time)
note | str | Optional summary (max 300 chars)

### Pattern Extraction

After each successful PR, _extract_patterns() scans the generated implementation code using regex to extract top-level class and function signatures. These tell future runs what interfaces already exist in the codebase, helping the model make consistent naming and calling decisions.

# Python example — extracted from consensus.py:
patterns = [
    "class ConsensusEngine:",
    "async def run(self, task, context)",
    "def _arbitrate(self, claude_result, oai_result)",
]

### Write Path — record_pr()

Called in build_director.py immediately after the thread_store.save() call in the PR success path. Non-fatal — a record_pr() failure is logged as a warning and does not affect the build.

# After thread_store.save() in PR success path:
_fix_attempts = len(_failure_recs) if _failure_recs else 1
_ci_clean     = _fix_attempts <= 1
self._build_memory.record_pr(
    pr_num=exc.spec.pr_num, pr_title=exc.spec.title,
    subsystem=thread.subsystem, impl_files=exc.spec.impl_files or [],
    language=exc.spec.language or "python",
    impl_code=exc.impl_code or "",
    ci_clean=_ci_clean, fix_attempts=_fix_attempts,
)
# Console output: 💾 Build memory: PR #N recorded (CI clean / N attempts)

### Startup Injection — startup_injection()

Called in agent.py after doc_store.load(). Returns a summary block appended to startup_lines if any notes exist. Shows: total PRs recorded, CI clean rate, avg fix attempts, per-PR one-liner list. Capped at 2,000 chars.

# Example startup output when prior runs exist:
Build memory: 8 PR(s) completed across prior run(s).
  CI clean first-pass: 5/8 PRs    Avg fix attempts: 2.4
Completed PRs (most relevant patterns available for injection):
  PR #1: Consensus Engine core  [✓ CI clean]  → src/consensus.py
  PR #2: Build Director phase split  [⚠ 7 attempts]  → src/build_director.py

### Per-PR Injection — pr_generation_injection()

Called in build_director.py _execute_pr_inner after doc_ctx assembly. Scores all notes for relevance to the current PR: file overlap +10, same subsystem +5, title word overlap +2, recency +1. Returns top 6 most relevant notes with patterns. Capped at 1,200 chars.

### Deduplication

record_pr() deduplicates by pr_num — re-recording the same PR number replaces the existing entry rather than appending. This handles retry scenarios where a PR succeeds on a second run after failing on the first.

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 AM | StateAutosave, patch sentinel, GitHub JSON recovery, resume routing fixes
3.0 | 2026-03-20 PM | Per-PR save (not batch-only), mid-PR stage checkpoints, in_progress_pr, _save_pr_checkpoint(), 29 recovery smoke tests
4.0 | 2026-03-21 | completed_prd_ids set.add() fix, enriched spec persistence, 422 PR recovery (pr_number=None eliminated), _slug scoping fix
5.0 | 2026-03-22 | ContextManager: fix loop history trimming at 30k tokens, failure output truncation at 8k chars, spec-anchor first turn preservation (§9). BuildMemory: cross-run PR note persistence, startup injection, per-PR generation context injection, pattern extraction from generated code (§10).