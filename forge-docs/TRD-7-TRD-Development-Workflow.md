# TRD-7-TRD-Development-Workflow

_Source: `TRD-7-TRD-Development-Workflow.docx` — extracted 2026-03-19 19:56 UTC_

---

TRD-7

TRD Development Workflow

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the TRD Development Workflow — a structured, AI-facilitated process that guides a person from a raw product idea to a complete set of implementation-ready Technical Requirements Documents.

The core problem this workflow solves: most people who want to build software have an idea, not a specification. They think in features and use cases, not interfaces and error contracts. They skip dependencies, leave security implicit, and do not know what they do not know. An AI that simply asks "what do you want to build?" produces vague outputs.

This workflow is a design facilitator. It knows what questions to ask, in what order, and when enough has been said to write a section. It surfaces gaps, resolves contradictions, and produces TRDs that an AI agent — or a human engineer — can build from without ambiguity.

The workflow owns:

Eight structured phases from product vision through TRD generation

Dynamic question generation — Claude asks the right follow-up questions based on what has been said, not a fixed script

Question taxonomy — a coverage map ensuring every TRD domain is addressed for every component

Completion signals — knowing when enough information has been gathered to write a section

Gap detection — identifying missing interfaces, error contracts, and ownership ambiguities before writing

TRD outline for operator review before full generation begins

TRD generation using the Consensus Engine with the session transcript as context

Per-TRD iterative refinement — targeted correction without full regeneration

PRODUCT_CONTEXT.md synthesis — the platform context document loaded into every future build

Session persistence — sessions span hours or days with full resume support

# 2. Design Decisions

# 3. Session Phases

## 3.1 Phase Overview

## 3.2 TRDSession Dataclass

# 4. Phase 1: Product Vision Interview

## 4.1 Purpose

Establish shared understanding of what is being built before any technical discussion. The agent must resist moving to architecture too early — operators with technical backgrounds instinctively skip to "how" before "what" and "why" are fully resolved.

## 4.2 Opening

## 4.3 Vision Domain Coverage

## 4.4 Product Vision Output Schema

# 5. Phase 2: Architecture Discovery

## 5.1 Purpose

Map the technical landscape without locking in decisions. The goal is to understand the data flows, external systems, processing boundaries, and auth model well enough to propose TRD boundaries. Architecture Discovery does not define the solution — it surfaces the constraints.

## 5.2 Architecture Domain Coverage

## 5.3 Architecture Sketch Output

# 6. Phase 3: TRD Boundary Definition

## 6.1 Claude Proposes Boundaries

## 6.2 TRDBoundary Dataclass

## 6.3 Boundary Approval Gate

# 7. Phase 4: Per-TRD Deep Dive

## 7.1 Purpose

For each approved TRD boundary, gather enough detail to write the TRD at implementation depth. Claude works through nine taxonomy domains, asking one question at a time, tracking coverage, and probing thin areas before moving on.

## 7.2 Question Taxonomy — Nine Domains

## 7.3 Per-Domain Question Generation

## 7.4 Coverage Tracking

## 7.5 Transition Between TRDs

# 8. Phase 5: Gap Detection and Resolution

## 8.1 Gap Detection Analysis

## 8.2 Gap Resolution Protocol

# 9. Phase 6: TRD Outline Review

## 9.1 Outline Generation

## 9.2 Outline Presentation Format

## 9.3 Outline Correction Protocol

# 10. Phase 7: PRODUCT_CONTEXT.md Generation

## 10.1 Purpose

The PRODUCT_CONTEXT.md is the platform context document that the Consensus Engine (TRD-2 Section 6.3) injects into every code generation prompt. It is the single-page answer to "what system am I building?" — grounding every future AI-generated implementation in the product's architectural intent.

## 10.2 Content

# 11. Phase 8: TRD Generation

## 11.1 Generation System Prompt

## 11.2 Generation User Prompt

## 11.3 Per-TRD Approval Gate

# 12. Iterative Refinement

## 12.1 Correction Protocol

## 12.2 Expansion Protocol

# 13. Question Generation Protocol

## 13.1 One Question at a Time — Enforcement

## 13.2 Question Quality Rules

## 13.3 "I Don't Know" Handling

# 14. Completion Signals

## 14.1 Phase Completion Signals

## 14.2 Domain Completion Signals

# 15. Product Context Document

## 15.1 PRODUCT_CONTEXT.md Template

## 15.2 Loading into Doc Store

# 16. TRD Generation System Prompts

## 16.1 Section-Level Correction Prompt

## 16.2 Section Expansion Prompt

# 17. CommandRouter Integration

## 17.1 _handle_trd() Handler

# 18. TRDSession Persistence

## 18.1 Storage

## 18.2 Resume Protocol

# 19. Testing Requirements

## 19.1 Prompt Regression Tests

# 20. Performance Requirements

# 21. Out of Scope

# 22. Open Questions

# Appendix A: Question Taxonomy Reference

This taxonomy is a coverage map — not a script. Claude generates questions dynamically. This reference is used to check that all domains have been addressed, not to dictate the exact wording of questions.

# Appendix B: TRD Outline Template

# Appendix C: Document Change Log