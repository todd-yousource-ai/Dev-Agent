# TRD-16-Agent-Testing-and-Validation-Crafted

_Source: `TRD-16-Agent-Testing-and-Validation-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-16: Agent Testing and Validation

Technical Requirements Document — v3.0

Product: Crafted Document: TRD-16: Agent Testing and Validation Version: 3.0 Status: Updated — Failure Taxonomy + Regression Suite + Fix Loop Strategy (March 2026) Author: Todd Gould / YouSource.ai Previous Version: v2.0 (2026-03-21) Depends on: TRD-3 (Build Pipeline), TRD-13 (Recovery), TRD-14 (Code Quality), TRD-15 (Runbook)

## What Changed from v2.0

Three additions. All sections from v2.0 are unchanged.

§10 — v38 Failure Mode Taxonomy: 7 root cause buckets from open coding the v38 patch history (new)

§11 — Regression test suite: test_regression_taxonomy.py, 35 tests, v39 no-regression contract (new)

§8 update — Fix loop strategy dispatch: _choose_strategy() replaces static lookup table; _score_fix() replaces length arbitration (updated)

## §8 Update — Fix Loop Strategy Dispatch (Updated in v3.0)

### SP-2: _choose_strategy() — Replaces Static Lookup Table

v2.0 used a 20-element static list indexed by attempt number to select strategy. Strategy was determined by how many times something failed, not by what kind of failure occurred. A SyntaxError on attempt 6 got test_driven; an assertion error on attempt 2 got converse — both wrong.

v3.0 replaces this with _choose_strategy(failure_type, attempt, records) — failure type is the primary signal, attempt count is a secondary escalation override.

Failure Type | Early attempts (1-4) | Mid attempts (5-7) | Late (8+)
compile_error / syntax_error | test_driven immediately | test_driven | nuclear every 3rd
assertion_error | test_driven | test_driven until 6, then nuclear | nuclear majority
import_error / type_error / runtime_error | converse (diagnostic reasoning) | test_driven | nuclear every 3rd
timeout / unknown | converse | test_driven | nuclear every 3rd

Hard escalation overrides type-based logic: attempt >= 8 triggers nuclear every 3rd attempt; attempt >= 15 alternates nuclear/test_driven regardless of failure type.

### SP-3: _score_fix() — Replaces Length Arbitration

v2.0 arbitrated between Claude and OpenAI fix attempts by preferring the longer response. Longer ≠ better — a 600-line response padded with boilerplate could win over a clean 400-line correct fix.

v3.0 replaces this with _score_fix(code, failure_output): scores each response by how many of the failing test’s assertion tokens appear in the fix. A targeted fix that addresses the specific assertion scores higher than a verbose response that doesn’t.

# Scoring:
#   +2 for each failing assertion identifier found in the fix
#   +1 for each FAILED test name mentioned in the fix
# Falls back to length tiebreaker only when scores are equal.
# Claude wins ties (scores passed as claude first).

## §10. v38 Failure Mode Taxonomy (New in v3.0)

### Purpose

Open coding applied to the full v38.0–v38.136 patch history. Every patch was catalogued with an open code (raw observation), then grouped into axial categories (root cause buckets). This is the evaluation flywheel Analyze phase applied retroactively to the build sprint.

The taxonomy is stored in FAILURE_TAXONOMY.md at the repository root. It is the specification for the regression test suite (§11).

### Seven Root Cause Buckets

ID | Bucket | Root Mechanism | Detection Signature
FM-1 | State Persistence | Write timing — saves at batch boundaries, not PR boundaries | Agent re-runs completed work after restart
FM-2 | Code Generation Quality | No pre-commit validation; CI is first to catch syntax errors | CI first to catch syntax error, not local lint gate
FM-3 | Template Placeholder Leakage | Template not evaluated before write | Literal {identifier} in committed file
FM-4 | CI Environment Mismatch | Mac assumptions in code and config, Ubuntu in CI | Passes local, fails CI — not a logic error
FM-5 | Context Window Degradation | No history trimming; unresolvable loop runs to attempt 20 | Code quality decreases over fix attempts
FM-6 | GitHub API Operation Failures | Silent non-fatal handling on critical write paths | Agent reports success, repo disagrees
FM-7 | Dependency Resolution Failure | No pre-execution dependency check | 20 identical ImportErrors on same missing module

### How to Use

Before any v39 modular refactor is shipped:

Run pytest tests/test_regression_taxonomy.py — all 35 tests must be green

Any failing test means a known FM-N failure mode has been reintroduced

Do not ship until all tests pass

## §11. Regression Test Suite (New in v3.0)

### File

tests/test_regression_taxonomy.py — 35 tests across 8 classes. This is the v39 no-regression contract.

### Structure

Class | FM Bucket | Tests | Coverage
TestStatePersistence | FM-1 | 4 | Phase key round-trip, completed PR list reload, per-PRD tracking, build memory persistence
TestCodeGenerationQuality | FM-2 | 5 | Valid Python check, unterminated string detection, F541 f-string detection, impl_files required, pre-commit syntax
TestTemplatePlaceholder | FM-3 | 4 | YAML placeholder detection, clean YAML passes, Python braces boundary, CI workflow validation
TestCIEnvironmentParity | FM-4 | 4 | requirements.txt completeness, no Mac paths, pathlib usage, ruff config present
TestContextManagement | FM-5 | 5 | Trim at threshold, first turn preserved, failure output truncation, unresolvable bail-out, nuclear keeps system prompt
TestGitHubOperations | FM-6 | 5 | Path injection blocked, safe title passes, YAML valid before commit, placeholder in YAML detected, is_safe_path
TestDependencyResolution | FM-7 | 5 | ImportError classification, unresolvable heuristic, depends_on_prs is list, unmet dep detectable, met deps allow execution
TestBuildMemoryIntegration | FM-1 + FM-5 | 3 | CI clean rate tracked, pattern injection targets correct PR, deduplication on rerun

### Tagging Convention

Every test is tagged with a comment citing the patch range that introduced the fix — for example:

def test_completed_prs_survive_reload(self, tmp_workspace):
    """
    REGRESSION (v38.61–v38.65):
    A crash mid-batch discarded all completed PRs in the batch...
    """

When a test fails after a v39 change, the tag tells you exactly which patch range and root cause bucket to investigate.

### Coverage Requirement

Every FM-N bucket must have at minimum 3 tests. No bucket may have zero tests at v39 release. The current suite exceeds this: minimum 4 tests per bucket.

## Updated Test File Summary (v3.0)

File | Tests | Network | Cost
test_audit.py | Unit | None | $0
test_build_director.py | Unit | None | $0
test_build_map.py | Unit | None | $0
test_consensus.py | Unit | None | $0
test_document_store.py | Unit | None | $0
test_e2e.py | Integration | Localhost only | $0
test_failure_handler.py | Unit | None | $0
test_github_tools.py | Unit | None (mocked) | $0
test_integration.py | Integration | None (mocked) | $0
test_path_security.py | Unit | None | $0
test_prd_planner.py | Unit | None | $0
test_pre_pr_review.py | Unit | None | $0
test_regression_taxonomy.py | Regression | None | $0
test_sandbox.py | Unit | None | $0
test_smoke_recovery.py | Recovery | None (partial mock) | $0
test_smoke.py | Live | Anthropic + OpenAI + GitHub | ~$0.01
test_test_runner.py | Unit | None | $0

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — complete testing strategy from March 2026 build sprint
2.0 | 2026-03-21 | Self-Correction Loop (§6), Repo Context Fetcher (§7), fix loop improvements — failure classification, early bail-out, test growth gating (§8), LLM Observability (§9)
3.0 | 2026-03-22 | v38 failure mode taxonomy: 7 buckets from open coding full patch history, stored in FAILURE_TAXONOMY.md (§10). Regression test suite: test_regression_taxonomy.py, 35 tests across 8 classes, v39 no-regression contract (§11). Fix loop: _choose_strategy() replaces static lookup table with failure-type-aware dispatch; _score_fix() replaces length arbitration with assertion-content scoring (§8 update).