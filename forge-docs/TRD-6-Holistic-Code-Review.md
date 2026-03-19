# TRD-6-Holistic-Code-Review

_Source: `TRD-6-Holistic-Code-Review.docx` — extracted 2026-03-19 15:58 UTC_

---

TRD-6

Holistic Code Review

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Holistic Code Review capability — a standalone workflow that points the Consensus Dev Agent at an existing codebase branch, runs five structured review passes, produces a documented review report, and executes targeted fix pull requests.

This is a different workflow from the build pipeline (TRD-3). Where TRD-3 builds new software from specifications, TRD-6 reviews and improves existing software. The two workflows share infrastructure (Consensus Engine, GitHubTool) but have separate state objects, orchestration, and output formats.

The Holistic Code Review owns:

ReviewDirector — orchestration of the full review workflow

Five review lenses — lint/correctness, security/cyber hygiene, performance, test quality, architecture

Consensus integration — both Claude and GPT-4o review each file independently per lens

Issue aggregation — deduplication, severity ranking, fixability classification

Review report — structured markdown document committed to GitHub before any PR

Operator gate — exclusion of files/issues, fix scope selection, cost confirmation

Fix execution — applying fixable issues per-file with one commit per file

PR creation — per-lens or combined PR with full documentation

Review manifest — persistence for incremental and diff-mode re-reviews

# 2. Design Decisions

# 3. Review Workflow — End-to-End Sequence

# 4. ReviewSession State Object

# 5. File Selection and Chunking

## 5.1 File Type Filter

## 5.2 Auto-Exclude Patterns

## 5.3 File Chunking

## 5.4 Diff Mode — Changed Files Only

# 6. Five Review Lenses

## 6.1 Lens Overview

## 6.2 Lens 1 — Lint and Correctness

## 6.3 Lens 2 — Security and Cyber Hygiene

## 6.4 Lens 3 — Performance and Optimization

## 6.5 Lens 4 — Test Quality

## 6.6 Lens 5 — Architecture and Maintainability

# 7. Consensus Integration — Per-File, Per-Lens Protocol

## 7.1 Review Call Structure

## 7.2 Review User Prompt

# 8. Issue Aggregation — Deduplication, Ranking, Fixability

## 8.1 Deduplication

## 8.2 Severity Model

## 8.3 Fixability Classification

# 9. Review Report

## 9.1 Report Location

## 9.2 Report Structure

## 9.3 Report Commit Protocol

# 10. Operator Review Gate

## 10.1 Gate 1 — Scope Confirmation

## 10.2 Gate 2 — Proceed to Fix

## 10.3 Gate 3 — Lens Selection

## 10.4 File and Issue Exclusion

# 11. Fix Execution

## 11.1 Fix Branch Creation

## 11.2 Per-File Fix Protocol

## 11.3 Syntax Check

# 12. PR Creation and Structure

## 12.1 PR Mode Selection

## 12.2 PR Description

# 13. Review Manifest — Persistence and Incremental Mode

## 13.1 Manifest Schema

## 13.2 Diff Mode Logic

# 14. Cost Model

## 14.1 Pre-Review Cost Estimate

## 14.2 Typical Costs

# 15. REPL Integration — /review Commands

# 16. ReviewDirector — Orchestration Class

# 17. Testing Requirements

## 17.1 Lens Prompt Regression Tests

# 18. Performance Requirements

# 19. Out of Scope

# 20. Open Questions

# Appendix A: Review Lens Prompt Reference

# Appendix B: Issue Schema Reference

# Appendix C: Review Report Template

The following template is used by build_report() to generate the markdown review report. All placeholders are replaced with actual session data.

# Appendix D: Document Change Log