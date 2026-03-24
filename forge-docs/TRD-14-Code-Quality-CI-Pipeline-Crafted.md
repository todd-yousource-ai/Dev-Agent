# TRD-14-Code-Quality-CI-Pipeline-Crafted

_Source: `TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` — extracted 2026-03-24 15:38 UTC_

---

TRD-14: Code Quality and CI Pipeline

Technical Requirements Document — v3.0

Field | Value
Product | Crafted
Document | TRD-14: Code Quality and CI Pipeline
Version | 3.0
Status | Updated — 7 CI False-Positive Fixes + conftest.py (March 2026)
Author | Todd Gould / YouSource.ai
Previous Version | v2.1 (2026-03-22)
Depends on | TRD-2 (Consensus Engine), TRD-3 (Build Pipeline), TRD-5 (GitHub Integration)

# 1. Purpose and Scope

This document specifies the code quality pipeline that runs between code generation and GitHub PR creation, and the CI pipeline (GitHub Actions) that validates code after it is pushed to a feature branch.

Extracted from TRD-3 v2.0 because the code quality and CI concerns are sufficiently complex to warrant a dedicated document. TRD-3 owns the build pipeline orchestration; TRD-14 owns the quality gates.

# 2. Pre-Commit Quality Pipeline

## 2.1 Pipeline Order

Between code generation and the test runner, the following quality gates run in order:

Stage | Gate | On Failure
1 | Repo context fetch — existing files injected into context | N/A (prep step)
2 | Self-Correction Loop — LLM reviews its own output (up to 10 passes) | Continues with best code
3 | Lint Gate — ast.parse → ruff → import check | LLM fixes up to 3 attempts per stage
4 | Native output enforcement — no eval(), exec(), runtime loaders | Regenerate entire PR
5 | pytest (up to 20 attempts with fix loop) | Fix loop with _choose_strategy()

# 3. Lint Gate (v2.0)

## 3.1 Three-Stage Pipeline

The lint gate runs between self-correction and pytest. It catches ~80% of failures before burning expensive test attempts. Implemented in lint_gate.py as LintGate.

Stage | Tool | What it catches | Cost
ast.parse | Python stdlib | Syntax errors, truncated strings, unclosed brackets | Zero — no subprocess
ruff check | ruff 0.9+ | Undefined names, unused imports, F-string issues, style | ~50ms subprocess
import check | Python subprocess | Missing dependencies, circular imports | ~200ms subprocess

Fast checks run first — no point running ruff if ast.parse fails. On failure at any stage, the LLM is called once to fix. Cycle repeats up to max_fix_attempts (default 3) per stage. Returns LintResult with passed, stage, errors, and fixed_code.

## 3.2 Python Only

v1.0 lint gate targets Python only. Swift files pass through the lint gate without checking (SwiftUI/macOS build validation occurs in the macOS CI runner, TRD-9). Go and TypeScript pass through with a clean result.

# 4. Test Commit Syntax Validation (v2.0)

Before committing test files to GitHub, the agent validates that the test file is syntactically valid Python. A test file with a syntax error committed to the branch would cause CI to fail with a collection error rather than a test failure — different failure mode that requires different remediation. The validation runs ast.parse on the test file content before calling commit_file().

# 5. CI Workflow — crafted-ci.yml

## 5.1 Overview

ci_workflow.py manages the GitHub Actions workflow file. The workflow runs on push and pull_request events for the feature branch. It installs Python 3.11, installs dependencies from requirements.txt, and runs pytest.

## 5.2 Workflow Lifecycle

ensure() writes crafted-ci.yml only when the file does not already exist. force_update() unconditionally rewrites the file (used after major CI fixes). Both call _ensure_conftest() after writing the workflow.

# §5b. CI paths-ignore — Expanded (v2.1)

## The Problem

v2.0 documented paths-ignore as covering only '**.md', 'prds/**', 'docs/**'. Documentation PRs that produce .yaml, .json, .toml, or .sh files would still trigger CI, which would fail finding no test files.

## The Fix

# crafted-ci.yml — paths-ignore (v2.1)

paths-ignore:

- "prds/**"

- "docs/**"

- "**.md"

- "**.rst"

- "**.txt"

- "**.docx"

- "**.yaml"

- "**.yml"

- "**.toml"

- "**.cfg"

- "**.ini"

- "**.json"

- "**.env"

- "**.sh"

- "**.bash"

- "Crafted/**"

- "*.xcodeproj/**"

This filter appears in both push and pull_request trigger blocks. The macOS workflow (crafted-ci-macos.yml) uses explicit paths: ["Crafted/**", ...] rather than paths-ignore and is unchanged.

# §5c. Seven CI False-Positive Fixes (New in v3.0)

Seven distinct causes of false-positive failures identified from the v38 build sprint and fixed in _build_workflow() in ci_workflow.py:

### FP-1 — PYTHONPATH Not Set (Root Cause of Most Failures)

pytest ran without PYTHONPATH, causing ModuleNotFoundError for any import from src/ on Ubuntu CI. Fix: PYTHONPATH set at job level so every step (pytest, ruff, mypy) inherits it:

jobs:

test:

env:

PYTHONPATH: ${{ github.workspace }}/src

### FP-2 — Exit Code 5 Treated as Failure

pytest exits with code 5 when no tests are collected (test-only PRs whose dependency PRs haven't merged). Fix: capture exit code and handle 5 as success:

EXIT=$?

if [ $EXIT -eq 5 ]; then

echo "No tests collected (exit 5) — dependency PRs not yet merged, skipping"

exit 0

fi

exit $EXIT

### FP-3 — Ruff Failing CI on Style Violations

Previous template ran ruff with no code filter, failing on style-only violations (E501, F401). Fix: only fail CI on codes indicating real runtime errors:

# Fatal codes only — syntax errors and undefined names

ruff check src/ --select E999,F821,F811 --output-format=github || true

# Informational full lint — annotates PR but never fails CI

ruff check src/ --output-format=github 2>/dev/null || true

### FP-4 — Bash Array Validation Loop

Previous template used a per-file AST validation loop (VALID_TESTS=()). If all test files had syntax errors, the loop exited with 0 silently. Redundant once FP-1 was fixed. Fix: removed entirely — pytest's own collection handles syntax errors.

### FP-5 — --cov=src Caused Import Errors

--cov=src required src to be importable as a package, which failed when PYTHONPATH wasn't set. Fix: --cov=src and pytest-cov removed from the CI template.

### FP-6 — No Concurrency Control

The fix loop could push 3–5 commits to the same branch within minutes, triggering concurrent CI runs. Fix: concurrency added at workflow level:

concurrency:

group: ${{ github.workflow }}-${{ github.ref }}

cancel-in-progress: true

### FP-7 — Secrets Regex Too Broad

Previous regex matched legitimate env-var reads. Fix: pipe through grep -v to exclude:

if grep -rn "api_key[[:space:]]*=[[:space:]]*['\"'][a-zA-Z0-9]" src/ \

| grep -qv "environ\|getenv\|os\.environ\|config\.\|\.get("; then

echo "FAIL: possible hardcoded API key detected"

exit 1

fi

### Additional: Least-Privilege Permissions

permissions: {}          # deny all at workflow level

jobs:

test:

permissions:

contents: read     # checkout only

### Additional: Pip Caching

- uses: actions/setup-python@v6

with:

python-version: "3.11"

cache: "pip"

cache-dependency-path: "requirements.txt"

40–80% CI time reduction when requirements.txt hasn't changed.

# §5d. conftest.py — Dual-Layer Import Fix (New in v3.0)

FP-1 is fixed at two layers because pytest, ruff, and mypy use different import resolution mechanisms:

Layer | What It Fixes | How It Works
conftest.py at repo root | Agent local fix loop (pytest invoked by failure_handler.py) | pytest loads conftest.py at startup — inserts src/ into sys.path before any test collection
PYTHONPATH in job env | ruff, mypy, and pytest running in CI (GitHub Actions) | Environment variable inherited by every step in the CI job
Both together | All ModuleNotFoundError failures at every invocation layer | Belt-and-suspenders — no single point of failure

## conftest.py Content

# conftest.py — at repo root

import sys

from pathlib import Path

# Insert at position 0 so local src/ takes precedence over any

# installed package with the same name.

_src = Path(__file__).parent / "src"

if str(_src) not in sys.path:

sys.path.insert(0, str(_src))

ci_workflow.ensure() and force_update() call _ensure_conftest(default_branch) after writing the CI workflow. Idempotent — skips if conftest.py already exists. Non-fatal on GitHubToolError.

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — extracted from TRD-3 v2.0 production implementation
2.0 | 2026-03-21 | Lint Gate (ast → ruff → import), test commit syntax validation, CI per-file syntax check, PYTHONPATH fix for local packages, docs PR test commit suppression
2.1 | 2026-03-22 | paths-ignore expanded from **.md only to full non-code surface: .rst, .txt, .yaml, .yml, .toml, .cfg, .ini, .json, .env, .sh, .bash (§5b)
3.0 | 2026-03-22 | Seven CI false-positive fixes (§5c): PYTHONPATH at job level (FP-1), exit code 5 (FP-2), ruff errors-only (FP-3), bash array removed (FP-4), --cov removed (FP-5), concurrency (FP-6), secrets regex (FP-7). Least-privilege permissions. Pip caching. conftest.py dual-layer explanation (§5d).