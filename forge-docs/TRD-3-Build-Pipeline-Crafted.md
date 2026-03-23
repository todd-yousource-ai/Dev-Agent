# TRD-3-Build-Pipeline-Crafted

_Source: `TRD-3-Build-Pipeline-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-3: Build Pipeline and Iterative Code Quality Engine

Technical Requirements Document — v6.0

Product: Crafted Document: TRD-3: Build Pipeline and Iterative Code Quality Engine Version: 6.0 Status: Updated — PR Type Field + Build Memory Injection (March 2026) Author: YouSource.ai Previous Version: v5.0 (2026-03-21) Depends on: TRD-1, TRD-2 v3, TRD-5, TRD-13 v5, TRD-14, TRD-15

## What Changed from v5.0

Two targeted changes. All sections from v5.0 are unchanged unless noted.

§2a — PR type detection: keyword-based _is_docs_pr replaced by spec.pr_type field (updated)

§2b — PRSpec.pr_type field: new field with three values, set by planner from impl_files (new)

§5f — Build memory injection: cross-run PR pattern context injected into generation (new)

## §2a. PR Type Detection — Updated (v6.0)

### The Problem with Keyword Detection

v5.0 used a Python keyword list (_docs_keywords) to detect documentation PRs by scanning the PR title. This was fragile in two ways: a PR titled ‘Define DTL event schema’ wouldn’t match any keyword despite producing .json files, and a PR titled ‘Document the runbook’ could match ‘documentation’ but might produce a Python script.

Keyword matching is classification logic that belongs in the planner (which has the full spec), not in routing code that only has the title string.

### The Fix

The _docs_keywords set is removed entirely. PR type routing now reads spec.pr_type, a field set by the planner when it generates the PR list. A deterministic extension-based safety net handles old saved state that predates the pr_type field.

# v5.0 — keyword list (removed in v6.0)
_docs_keywords = {"naming convention", "glossary", "changelog", ...}
_is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...

# v6.0 — reads spec.pr_type (set by planner)
_is_docs_pr = (
    spec.pr_type == "documentation"
    or (spec.pr_type == "implementation" and _all_non_code(spec.impl_files))
)
_is_test_only_pr = spec.pr_type == "test"

The safety net (_all_non_code) catches old state: if all impl_files have non-code extensions and pr_type is still ‘implementation’ (pre-v6.0 state), treat as documentation. This covers resumed builds from earlier versions.

### Note on _is_test_only_pr

In v5.0, _is_test_only_pr was used in four places in build_director.py but was never assigned — a latent NameError. v6.0 fixes this as a side effect: spec.pr_type == “test” always evaluates cleanly.

## §2b. PRSpec.pr_type Field (New in v6.0)

### Field Definition

A new pr_type field on PRSpec carries the classification from the planner to the execution layer. This is the single source of truth for routing.

@dataclass
class PRSpec:
    ...
    # PR type — set by planner from impl_files; drives routing in build_director.
    # "implementation": produces code files (.py, .go, .ts, .swift, .rs, etc.)
    # "documentation":  produces only non-code files (.md, .yaml, .json, etc.)
    # "test":           produces only test files validating other PRs' code
    pr_type: str = "implementation"

pr_type value | Local test loop | CI gate | Test file generated
“implementation” | Full fix loop (20 passes) | Runs on commit | Yes
“documentation” | Skipped (always passes) | Skipped (paths-ignore) | No
“test” | Skipped (deps not merged) | Runs after deps merge | N/A (impl IS test)

### Planner Instruction (PR_LIST_SYSTEM)

PR_LIST_SYSTEM now includes a PR TYPE RULE section that instructs the model to set pr_type based on impl_files:

PR TYPE RULE:
Set pr_type based on the impl_files:
- "implementation": PR creates or modifies code files (.py, .go, .ts, .swift, .rs, etc.)
- "documentation":  PR creates only non-code files (.md, .rst, .yaml, .json, .toml, etc.)
- "test":           PR creates only test files with no corresponding implementation

### Extension Safety Net in _parse_pr_list

When constructing PRSpec objects from the LLM’s JSON response, _parse_pr_list applies a safety net: if pr_type is ‘implementation’ but all impl_files have non-code extensions, it overrides to ‘documentation’. This prevents misclassification from reaching the execution layer.

### Deserialization Safety

Both PRSpec deserialization sites in build_director.py (_PRSPEC_DEFAULTS and the inline construction in the pr_plan restoration path) include (“pr_type”, “implementation”) as a default. Resumed builds from pre-v6.0 state default to ‘implementation’ and the extension safety net handles any actual documentation PRs.

## §5f. Build Memory Injection (New in v6.0)

### What It Is

After the doc_ctx and forge_injection blocks are assembled in _execute_pr_inner, a build memory block is appended. It contains compact summaries of previously completed PRs from prior runs — what was built, which patterns exist in the codebase, whether CI passed clean.

Note: forge_injection refers to Forge security platform context injected into the build — this is a Forge (security product) integration and is preserved as-is.

# In _execute_pr_inner, after doc_ctx injection:
_mem_block = self._build_memory.pr_generation_injection(
    pr_title   = spec.title,
    impl_files = spec.impl_files or [],
    subsystem  = thread.subsystem,
)
if _mem_block:
    context += f"\n\n{_mem_block}"

### What the Block Contains

Up to 6 most-relevant prior PR notes, scored by file overlap (+10), same subsystem (+5), title word overlap (+2), and recency (+1). Each note includes:

PR title and CI result (clean or N attempts)

Target files

Up to 4 extracted class/function signatures already in the codebase

### Why It Matters

Without this, the generation context has no knowledge of interfaces already committed in earlier PRs of the same build. The model may redefine classes, use wrong function signatures, or import from paths that don’t match what was actually built. The injection compounds over 5–10 runs — each run starts with more context about the existing codebase.

See TRD-13 §10 for the full BuildMemory specification.

## Updated Detection Logic Summary (v6.0)

PR Type | Detection | Local Tests | CI | Example
implementation | spec.pr_type == “implementation” | Full fix loop (20 passes) | Runs on commit | consensus.py, branding.py
documentation | spec.pr_type == “documentation” OR all impl_files non-code | None — always passes | Skipped (paths-ignore) | NAMING_CONVENTIONS.md, GLOSSARY.yaml
test | spec.pr_type == “test” | Skip — deps not merged yet | Runs after deps merge | test_naming_convention.py

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 AM | Production implementation: 20-pass loop, CI fix loop, sanitization, StateAutosave, GitHub JSON backup, impl_files fix, patch sentinel
3.0 | 2026-03-20 PM | Multi-turn fix loop, grounding system prompt, full acceptance criteria in context, OI13 noise fix, docs PR routing, build interface map, 60K context window
4.0 | 2026-03-20 PM | Native output enforcement gate (§5d), wrapper detection in CI fix loop (§9a)
5.0 | 2026-03-21 | Three PR types (Code/Docs/Test-only). New pre-test pipeline: Repo Context Fetch, Self-Correction Loop (10 passes), Lint Gate. _gen_context with existing file content. Test-only PRs skip local loop. 422 PR recovery.
6.0 | 2026-03-22 | PR type routing replaced keyword detection with spec.pr_type field (§2a/§2b). _docs_keywords removed. Build memory injection into generation context (§5f). _is_test_only_pr latent NameError fixed.