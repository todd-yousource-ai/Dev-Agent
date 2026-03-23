# TRD-14-Code-Quality-CI-Pipeline-Crafted

_Source: `TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-14: Code Quality and CI Pipeline

Technical Requirements Document — v2.1

Product: Crafted Document: TRD-14: Code Quality and CI Pipeline Version: 2.1 Status: Updated — Expanded paths-ignore (March 2026) Author: Todd Gould / YouSource.ai Previous Version: v2.0 (2026-03-21) Depends on: TRD-2 (Consensus Engine), TRD-3 (Build Pipeline), TRD-5 (GitHub Integration)

## What Changed from v2.0

One targeted fix. All sections from v2.0 are unchanged.

§5b — CI paths-ignore expanded to cover all non-code file types, not just .md and .docx (updated)

## §5b. CI paths-ignore — Expanded (v2.1)

### The Problem

v2.0 documented paths-ignore as covering ‘.md’, ’prds/’, ’docs/**’. This was insufficient for documentation PRs that produce .yaml, .json, .toml, or .sh files — for example, a naming conventions PR that produces NAMING_CONVENTIONS.yaml or a CI configuration PR that produces shell scripts.

A documentation PR (spec.pr_type == “documentation”) with impl_files containing .yaml files would still trigger CI, which would then fail finding no test files or no Python source to validate.

### The Fix

The paths-ignore list in the _build_workflow() template in ci_workflow.py is expanded to cover the complete non-code surface. This matches the _NON_CODE_EXTS set used by the build pipeline routing.

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

This filter appears in both the push and pull_request trigger blocks. The macOS workflow (crafted-ci-macos.yml) is unchanged — it uses explicit paths: [“Crafted/**“, …] rather than paths-ignore.

### Interaction with pr_type

The paths-ignore filter and the spec.pr_type routing are complementary, not redundant. The paths-ignore prevents CI from triggering on documentation PRs at the GitHub Actions level — a zero-cost gate with no agent involvement. The spec.pr_type routing prevents the agent from generating test files or waiting for CI locally. Both need to be correct for documentation PRs to complete cleanly.

### Fresh Build Note

ci_workflow.py writes crafted-ci.yml only when the file does not already exist in the repository. For fresh builds (no existing workflow file), the new template is written automatically at the start of the first directed build. For repositories with an existing workflow, force_update() must be called explicitly or the file updated manually.

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-20 | Initial document — extracted from TRD-3 v2.0 production implementation
2.0 | 2026-03-21 | Lint Gate (ast → ruff → import), test commit syntax validation, CI per-file syntax check, PYTHONPATH fix for local packages, docs PR test commit suppression
2.1 | 2026-03-22 | paths-ignore expanded from **.md only to full non-code surface: .rst, .txt, .yaml, .yml, .toml, .cfg, .ini, .json, .env, .sh, .bash (§5b). Aligns with _NON_CODE_EXTS in build pipeline routing.