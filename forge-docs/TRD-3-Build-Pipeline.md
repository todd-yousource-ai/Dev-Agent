# TRD-3-Build-Pipeline

_Source: `TRD-3-Build-Pipeline.docx` — extracted 2026-03-19 18:29 UTC_

---

TRD-3

Build Pipeline and 3-Pass Review

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Build Pipeline — the directed, human-in-the-loop system that takes a plain-language build intent and produces merged pull requests in a GitHub repository.

The Pipeline owns:

All 8 pipeline stages — from scope confirmation through CI gate

The 3-pass iterative review cycle (Stage 6) that calls the Consensus Engine

The BuildThread state object and its persistence across restarts

All operator gate interactions — displaying options, reading responses, routing decisions

The resume protocol — restarting a build session from the last checkpoint

The REPL command router — dispatching /prd, /patch, /ledger, /clear, etc.

Error escalation — routing failures to FailureHandler, surfacing errors to UI

# 2. Pipeline Overview

## 2.1 Stage Sequence

## 2.2 Complexity Budget

The original _stage_interleaved() had McCabe complexity 88. This TRD mandates the following maximums for all pipeline classes:

# 3. BuildThread v2 Schema

## 3.1 Core Dataclass

## 3.2 Supporting Dataclasses

### 3.2.1 PRDItem

### 3.2.2 PRDResult

### 3.2.3 PRSpec

### 3.2.4 PRExecution

# 4. ThreadStateStore v2

## 4.1 Persistence Contract

ThreadStateStore is the single persistence mechanism for BuildThread. All pipeline stages save through it — never write thread state directly to disk. Writes are atomic (tmp file + rename).

## 4.2 PersistedThread Schema

## 4.3 Atomic Write Protocol

# 5. Stage Interface Contract

# 6. Stage 1: ScopeStage

## 6.1 Responsibilities

Parse plain-language intent against loaded TRD documents

Identify subsystem, scope statement, relevant docs, and ambiguities

Resolve ambiguities one at a time — never re-scope (infinite loop risk)

Show operator the scope summary and await confirmation

Create BuildThread on confirmation

Save to ThreadStateStore as first checkpoint

## 6.2 System Prompt

## 6.3 Ambiguity Protocol

## 6.4 Scope Confirmation Gate

# 7. Stage 2: PRDPlanStage

## 7.1 Responsibilities

Run Consensus Engine to decompose scope into ordered PRD list

Display plan to operator with complexity indicators and dependencies

Show estimated cost before commitment

Accept operator approval or single correction (re-decompose once)

Commit PRD_PLAN.md to GitHub on approval

Initialize build ledger entry (TRD-4)

Save checkpoint to ThreadStateStore

## 7.2 Token Budget

## 7.3 Correction Protocol

## 7.4 PRD_PLAN.md Commit

# 8. Stage 3: PRDGenerationStage

## 8.1 Responsibilities

For each PRDItem in the plan: generate a full PRD via Consensus Engine

Export as .docx to local temp directory for operator review

Show inline preview (first 18 lines) in build stream

Present per-PRD review gate: yes / skip / stop / [correction → regenerate]

Commit approved PRD markdown to GitHub

Mark PRD complete in ThreadStateStore

Skip PRDs already in completed_prd_ids (resume support)

## 8.2 PRD Generation Call

## 8.3 Correction Protocol

## 8.4 .docx Export Protocol

## 8.5 GitHub Commit

# 9. Stage 4: PRPlanStage

## 9.1 Responsibilities

For each approved PRD: generate a full ordered PR list via PRPlanner

Display the full plan in the build stream

Show estimated PR build cost before execution

Auto-save to BuildThread (no operator gate — plan is visible for audit)

Commit pr-plan.md to GitHub branch for visibility

Update build ledger with PR plan (TRD-4)

## 9.2 PR Numbering

## 9.3 PR Plan Commit

# 10. Stage 5: CodeGenerationStage

## 10.1 Responsibilities

For each approved PRSpec: check OI-13 gate, then generate implementation + tests

Validate ALL model-supplied file paths through path_security before any use

Inject prior-PR dependency code as context for dependent PRs

Route MCP components to MCPGenerator

Pass results to Stage 6 (ThreePassReviewStage)

## 10.2 Path Security Gate

## 10.3 Dependency Code Injection

## 10.4 Unmet Dependency Warning

# 11. Stage 6: ThreePassReviewStage

## 11.1 Overview

The 3-Pass Review Stage is the primary quality gate for generated code. It runs after code generation and before test execution. Each pass uses a different evaluation lens. Both Claude and GPT-4o review independently per pass. Claude synthesizes the feedback and applies targeted fixes.

## 11.2 Pass Structure

## 11.3 Per-Pass Protocol

## 11.4 Confidence Gate

## 11.5 Review System Prompts

## 11.6 Issue Merging

# 12. Stage 7: TestStage

## 12.1 Responsibilities

Write implementation and test files to workspace directory

Run TestRunner (pytest / go test / jest / cargo test depending on language)

On failure: enter retry loop — generate fixes via Consensus Engine

Syntax error fast-path: skip fix loop, regenerate implementation directly

After MAX_TEST_RETRIES: escalate to FailureHandler

On local pass: mark PR as locally passing, save checkpoint

## 12.2 Retry Loop

# 13. Stage 8: CIGate

## 13.1 Protocol

# 14. Gate Protocol

## 14.1 Gate Card XPC Schema

## 14.2 Operator Response Routing

## 14.3 Gate Timeout

# 15. Resume Protocol

## 15.1 Checkpoint Guarantees

On restart, the pipeline resumes from the last saved checkpoint. Each checkpoint represents a point where the operator has already made a decision — the pipeline never re-asks a question the operator already answered.

## 15.2 Resume Entry Point

## 15.3 Decomp Variable Re-constitution

# 16. Error Escalation

## 16.1 Error Type Routing

## 16.2 _execute_pr Top-Level Guard

## 16.3 _safe_commit

# 17. REPL Decomposition — CommandRouter

## 17.1 Motivation

The current agent.main() function has McCabe complexity 84. Every command handler is a branch in the REPL loop. This TRD mandates a CommandRouter class that dispatches to per-command handler functions, each with max complexity 10.

## 17.2 CommandRouter

## 17.3 Command Handler Specifications

# 18. Audit Trail

## 18.1 Event Schema

## 18.2 Required Events

# 19. Complexity Budget

All pipeline stage classes and the CommandRouter must meet these limits. McCabe complexity is measured by counting branching points (if, while, for, except, with, and/or operators) + 1.

# 20. State Machine Transitions

# 21. Testing Requirements

## 21.1 Unit Tests

## 21.2 Review Prompt Regression Tests

# 22. Performance Requirements

# 23. Out of Scope

# 24. Open Questions

# Appendix A: BuildThread Field Reference

# Appendix B: Gate Type Reference

# Appendix C: Document Change Log