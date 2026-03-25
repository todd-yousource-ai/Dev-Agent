# TRD-3-Build-Pipeline-Crafted

_Source: `TRD-3-Build-Pipeline-Crafted.docx` — extracted 2026-03-25 19:25 UTC_

---

TRD-3: Build Pipeline and Iterative Code Quality Engine

Technical Requirements Document — v7.0

Field | Value
Product | Crafted
Document | TRD-3: Build Pipeline and Iterative Code Quality Engine
Version | 7.0
Status | Updated — Confidence-Gated Scope + conftest.py Auto-Commit (March 2026)
Author | YouSource.ai
Previous Version | v6.0 (2026-03-22)
Depends on | TRD-1, TRD-2 v3, TRD-5, TRD-13 v6, TRD-14 v3, TRD-15

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Crafted Dev Agent build pipeline — the end-to-end automation that transforms TRD/PRD documents into tested, CI-passing pull requests on GitHub.

The pipeline owns: scope definition, PRD decomposition, PR plan generation, code generation via consensus AI, pre-commit validation, local test execution, CI gate, and PR lifecycle management. All stateful aspects of execution (recovery, persistence) are covered in TRD-13. GitHub API operations are covered in TRD-5. Test execution environment is covered in TRD-14.

# 2. Build Phase Structure

## 2.1 Pipeline Phases

The agent executes four sequential phases per build session:

Phase | State | Description
1. Scoping | scoping | Operator provides intent; agent grounds scope in TRDs; confidence gate
2. PRD Generation | prd_gen | Consensus AI decomposes scope into ordered PRD units; each PRD committed to GitHub
3. PR Planning | prd_gen → pr_pipeline | For each PRD, consensus AI generates a PR plan (list of PRSpec objects); saved to GitHub JSON
4. PR Execution | pr_pipeline | For each PR spec, code generated → linted → tested → committed → CI gate → merged

## 2.2 Interleaved Execution

The pipeline uses interleaved PRD-then-PR execution: generate one PRD's PR plan, immediately execute all PRs in that plan, then move to the next PRD. This minimises the window between planning and execution, reducing the chance of scope drift.

# §1c. Confidence-Gated Scope Phase (New in v7.0)

## Why This Exists

The scope phase previously proceeded regardless of how well the loaded TRDs actually covered the build intent. A weakly-grounded scope produced ambiguous PRD decompositions discovered at PRD generation time — 30+ API calls in and $5–15 in spend. The confidence gate surfaces document coverage gaps at the scope gate instead: 1 API call, zero generation cost.

## SCOPE_SYSTEM Changes

Two new fields added to the SCOPE_SYSTEM JSON response schema:

confidence — integer 0–100. Self-assessed probability that the scope is complete and unambiguous given the documents provided.

coverage_gaps — list of specific TRD sections or interfaces missing from the provided documents.

Score | Label | Meaning
90–100 | Ready | Documents fully cover scope; no meaningful gaps; ready to build
75–89 | Minor gaps | Most requirements clear; operator input can resolve remaining gaps
60–74 | Significant gaps | Key interfaces or acceptance criteria unclear
< 60 | Insufficient | Document coverage too thin to define reliable scope

## _stage_scope Gate Logic

_CONFIDENCE_THRESHOLD = 85

if confidence < _CONFIDENCE_THRESHOLD:

# Display coverage gaps as targeted bullet points

# Present three options to operator:

#   yes / proceed  → override and continue with current scope

#   <answer>       → provide gap information, trigger one-shot re-scope

#   no             → cancel build

Labels in scope summary: ✓ for ≥90%, ⚠ for 60–89%, ✗ for <60%. One-shot re-scope: operator gap answers trigger exactly one additional SCOPE_SYSTEM call — no loop.

# 3. PRD Generation Phase

## 3.1 Consensus PRD Generation

Each PRD unit is generated using the consensus engine (Claude + OpenAI). The PRD planner decomposes the scope statement into an ordered list of PRDItems, then generates a full PRD document and PR plan for each.

## 3.2 PR Plan JSON Backup

Every completed PR plan is committed to GitHub as both markdown (human-readable summary) and JSON (full PRSpec objects) on the prds branch. This enables recovery of PR plans after a restart without regeneration — see TRD-13 §6.

## 3.3 Completed PRD Tracking

completed_prd_ids is a list that tracks which PRDs have fully completed PR execution. On resume, PRDs in this list are skipped entirely. The set.add() operation uses list.append() to avoid the mutability bug that caused double-processing in earlier versions.

# 4. PR Planning — PRSpec and PR_LIST_SYSTEM

## 4.1 PRSpec Dataclass

Each PR is represented as a PRSpec dataclass with all fields required for execution:

@dataclass

class PRSpec:

pr_num:              int

title:               str

branch:              str

summary:             str

description_md:      str

impl_files:          list[str]

test_files:          list[str]

impl_plan:           dict

test_plan:           dict

acceptance_criteria: list[str]

language:            str

framework:           str

security_critical:   bool

depends_on_prs:      list[int]

estimated_complexity: str

status: str = "pending"

pr_type: str = "implementation"   # implementation | documentation | test

checkpoint: str = "pending"        # branch_opened | code_generated | ...

# §2a. PR Type Detection — Updated (v6.0)

## The Problem with Keyword Detection

v5.0 used a Python keyword list (_docs_keywords) to detect documentation PRs by scanning the PR title. This was fragile in two ways: a PR titled 'Define DTL event schema' wouldn't match any keyword despite producing .json files, and a PR titled 'Document the runbook' could match 'documentation' but might produce a Python script.

## The Fix

# v5.0 — keyword list (removed in v6.0)

_docs_keywords = {"naming convention", "glossary", "changelog", ...}

_is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...

# v6.0 — reads spec.pr_type (set by planner)

_is_docs_pr = (

spec.pr_type == "documentation"

or (spec.pr_type == "implementation" and _all_non_code(spec.impl_files))

)

_is_test_only_pr = spec.pr_type == "test"

The safety net (_all_non_code) catches old state: if all impl_files have non-code extensions and pr_type is still 'implementation' (pre-v6.0 state), treat as documentation. The latent _is_test_only_pr NameError from v5.0 is also fixed.

# §2b. PRSpec.pr_type Field (New in v6.0)

pr_type value | Local test loop | CI gate | Test file generated
"implementation" | Full fix loop (20 passes) | Runs on commit | Yes
"documentation" | Skipped (always passes) | Skipped (paths-ignore) | No
"test" | Skipped (deps not merged) | Runs after deps merge | N/A (impl IS test)

## Planner Instruction (PR_LIST_SYSTEM)

PR TYPE RULE:

Set pr_type based on the impl_files:

- "implementation": PR creates or modifies code files (.py, .go, .ts, .swift, .rs, etc.)

- "documentation":  PR creates only non-code files (.md, .rst, .yaml, .json, .toml, etc.)

- "test":           PR creates only test files with no corresponding implementation

A fourth JSON example in the schema demonstrates pr_type: "test" with depends_on_prs. Extension safety net in _parse_pr_list overrides 'implementation' to 'documentation' when all impl_files have non-code extensions. Both PRSpec deserialization sites include ("pr_type", "implementation") as default.

# 5. PR Execution Pipeline

## 5.1 Execution Stages

Each PR moves through the following stages, checkpointed to disk after each:

Stage | Checkpoint key | Description
Branch creation | branch_opened | Create feature branch from default branch
Code generation | code_generated | Consensus AI generates impl + test code
Repo context fetch | code_generated | Existing file content fetched from GitHub before generation
Self-correction | code_generated | LLM reviews its own output for issues (up to 10 passes)
Lint gate | code_generated | ast.parse → ruff → import check; LLM fixes on failure
Test execution | tests_passed | pytest locally up to 20 attempts with fix loop
Commit to branch | committed | impl + test files committed to feature branch
CI gate | ci_passed | GitHub Actions CI run passes
PR ready | complete | PR marked ready-for-review

## 5.2 Mid-PR Stage Checkpoints

_save_pr_checkpoint() persists in_progress_pr to disk after each stage transition. If the agent crashes mid-PR, resume() resumes from the last checkpoint — not from code generation restart. This is the key mechanism that prevents $100+ losses from crashes during long PRs.

# §5a. Repo Context Fetch (v5.0)

Before code generation, RepoContextFetcher fetches existing file content from GitHub for all impl_files and dep PR files. Strategy: try current branch first, then main, then dep branches. Files not found are recorded as new. The content is injected as a structured block in the generation context.

=== EXISTING CODEBASE CONTEXT ===

--- src/consensus.py (main) ---

class ConsensusEngine:  # existing content...

--- src/new_module.py (new) ---

(new file — does not exist yet)

NOTE: 1 file(s) above already exist.

Make targeted edits — preserve existing structure and style.

# §5b. Self-Correction Loop (v5.0)

SelfCorrectionLoop runs between code generation and the lint gate. Claude and OpenAI each review code against a structured checklist (syntax → imports → logic → edge cases → spec alignment). If issues found, both models generate a fix. Max 10 passes per PR. Does not run for documentation or test-only PRs.

Review and fix conversations are kept separate: review accumulates cross-pass context; fix calls start fresh focused on specific issues. Longer response wins tie when both models fix.

# §5c. Lint Gate (v5.0)

LintGate runs between self-correction and pytest. Three stages in order:

ast.parse — syntax errors (instant, catches truncated strings, unclosed brackets)

ruff check — imports, undefined names, style violations

import check — can the file actually be imported in the test environment?

On failure at any stage, the LLM is called once to fix. The cycle repeats up to max_fix_attempts (3) per stage. Fast checks first — no point running ruff if ast.parse fails. Lint gate catches ~80% of failures before expensive test attempts.

# §5d. Native Output Enforcement Gate (v4.0)

After consensus generation, the output is checked for wrapper patterns that would fail at runtime: eval(), exec(), importlib.import_module() as a loader, and runtime code injection patterns. A PR that generates wrapper code rather than native implementation is rejected and regenerated. This prevents the common LLM pattern of wrapping code in a loader function rather than implementing it directly.

# §5e. Fix Loop — Multi-Turn Consensus

## Overview

The fix loop runs up to MAX_TEST_RETRIES=20 attempts. Each attempt: run tests → classify failure → select strategy → generate fix using consensus engine → re-run tests. The strategy is selected by _choose_strategy(failure_type, attempt, records):

Failure Type | Early (1–4) | Mid (5–7) | Late (8+)
compile_error / syntax_error | test_driven immediately | test_driven | nuclear every 3rd
assertion_error | test_driven | test_driven → nuclear at 6 | nuclear majority
import_error / type_error / runtime_error | converse (diagnostic) | test_driven | nuclear every 3rd
timeout / unknown | converse | test_driven | nuclear every 3rd

Hard escalation: attempt ≥ 8 triggers nuclear every 3rd attempt; attempt ≥ 15 alternates nuclear/test_driven regardless of failure type. _score_fix() arbitrates between Claude and OpenAI fixes by counting assertion token overlap rather than response length.

## Early Bail-Out

After 5 consecutive failures of the same unresolvable type (unknown/syntax_error on a test-only PR), the fix loop exits with passed=False rather than burning all 20 attempts. This targets the specific failure mode where dependency PRs haven't merged yet.

# §5f. Build Memory Injection (New in v6.0)

## What It Is

After doc_ctx assembly in _execute_pr_inner, a build memory block is appended to the generation context. It contains compact summaries of previously completed PRs from prior runs — what was built, which patterns exist, whether CI passed clean.

_mem_block = self._build_memory.pr_generation_injection(

pr_title   = spec.title,

impl_files = spec.impl_files or [],

subsystem  = thread.subsystem,

)

if _mem_block:

context += f"\n\n{_mem_block}"

Up to 6 most-relevant prior PR notes scored by file overlap (+10), same subsystem (+5), title word overlap (+2), recency (+1). See TRD-13 §10 for the full BuildMemory specification.

# §5g. conftest.py Auto-Commit (New in v7.0)

## Why This Exists

The most common false-positive CI failure is ModuleNotFoundError caused by pytest not finding src/ modules. conftest.py at the repo root inserts src/ into sys.path at pytest startup, fixing imports for the agent's local fix loop. The job-level PYTHONPATH env var covers ruff and mypy in CI. Both are needed — neither alone covers all invocation layers.

# conftest.py — committed to repo root by ci_workflow.ensure()

import sys

from pathlib import Path

_src = Path(__file__).parent / "src"

if str(_src) not in sys.path:

sys.path.insert(0, str(_src))

ci_workflow.ensure() and force_update() both call _ensure_conftest(default_branch) after writing the CI workflow. Idempotent — checks if conftest.py already exists before committing. Non-fatal on error.

# 6. CI Gate

## 6.1 CI Trigger

After impl and test files are committed to the feature branch, the agent waits for GitHub Actions CI to complete. The CI workflow (crafted-ci.yml) runs pytest on ubuntu-latest. The agent polls for CI status via ci_checker.py.

## 6.2 CI Fix Loop

If CI fails, the agent has up to 3 CI fix cycles. Each cycle: download CI log → classify failure → generate fix → commit → wait for CI. After 3 CI failures the PR is marked failed and the agent moves to the next PR.

## 6.3 Documentation PRs

Documentation PRs (pr_type=="documentation") skip the CI gate entirely. The paths-ignore configuration (TRD-14 §5b) ensures CI is never triggered for non-code files.

# 7. Build Interface Map

After each successful PR, a build interface map is updated in the feature branch. It contains the class and function signatures extracted from all completed implementation files. This map is injected into the generation context for subsequent PRs, preventing interface inconsistencies across PRs in the same build.

# Updated Detection Logic Summary (v6.0)

PR Type | Detection | Local Tests | CI | Example
implementation | spec.pr_type == "implementation" | Full fix loop (20 passes) | Runs on commit | consensus.py, branding.py
documentation | spec.pr_type == "documentation" OR all impl_files non-code | None — always passes | Skipped (paths-ignore) | NAMING_CONVENTIONS.md, GLOSSARY.yaml
test | spec.pr_type == "test" | Skip — deps not merged yet | Runs after deps merge | test_naming_convention.py

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 AM | Production implementation: 20-pass loop, CI fix loop, sanitization, StateAutosave, GitHub JSON backup, impl_files fix, patch sentinel
3.0 | 2026-03-20 PM | Multi-turn fix loop, grounding system prompt, full acceptance criteria in context, OI13 noise fix, docs PR routing, build interface map, 60K context window
4.0 | 2026-03-20 PM | Native output enforcement gate (§5d), wrapper detection in CI fix loop
5.0 | 2026-03-21 | Three PR types. Pre-test pipeline: Repo Context Fetch, Self-Correction Loop (10 passes), Lint Gate. _gen_context with existing file content. Test-only PRs skip local loop. 422 PR recovery.
6.0 | 2026-03-22 | PR type routing: spec.pr_type field replaces keyword detection (§2a/§2b). Build memory injection into generation context (§5f). _is_test_only_pr latent NameError fixed.
7.0 | 2026-03-22 | Confidence-gated scope: SCOPE_SYSTEM returns confidence+coverage_gaps, _stage_scope gates at 85% with one-shot re-scope (§1c). conftest.py auto-committed by ci_workflow.ensure() (§5g).