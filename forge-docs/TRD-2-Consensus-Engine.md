# TRD-2-Consensus-Engine

_Source: `TRD-2-Consensus-Engine.docx` — extracted 2026-03-19 18:29 UTC_

---

TRD-2

Consensus Engine

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Consensus Engine — the subsystem that takes a task prompt and produces a single best implementation by running two LLM providers in parallel and having Claude arbitrate the result.

The Consensus Engine is called by the Build Pipeline (TRD-3) for:

Code generation — implementation files for each PR

Test generation — test files for each PR

PRD generation — product requirement documents for each PRD item

PRD decomposition — breaking a scope statement into an ordered PRD list

The Engine does not own the 3-pass iterative review cycle. That is Stage 6 of the Build Pipeline (TRD-3), which calls back into the Engine for each review pass. The Engine provides the generation and arbitration primitives; the Pipeline orchestrates the passes.

# 2. Design Decisions

## 2.1 Two-Provider Architecture

The Engine uses exactly two providers in v1: Anthropic Claude and OpenAI GPT-4o. Claude arbitrates. This is a deliberate cost and complexity decision — not a limitation to be overcome in v1.

## 2.2 What the Engine Does NOT Do

It does not run the 3-pass review cycle — that is TRD-3

It does not manage GitHub operations — that is TRD-5

It does not persist build state — that is the Build Pipeline's ThreadStateStore

It does not make decisions about which PR to build next — that is TRD-3

It does not enforce gate logic — operators interact with TRD-3, not the Engine

# 3. Provider Protocol

## 3.1 ProviderAdapter Interface

Every LLM provider is wrapped in a ProviderAdapter. Adding a new provider means implementing this protocol and registering it in the provider registry — no changes to the ConsensusEngine core.

## 3.2 Anthropic Adapter

## 3.3 OpenAI Adapter

## 3.4 Provider Registry

# 4. Generation Pipeline

## 4.1 ConsensusResult Schema

## 4.2 Parallel Generation

## 4.3 Fallback State Machine

# 5. Arbitration

## 5.1 Arbitration System Prompt

The arbitration prompt is the most security-sensitive prompt in the system. It must instruct Claude to evaluate both implementations objectively — penalizing self-preference explicitly.

## 5.2 Arbitration User Prompt

## 5.3 Arbitration Implementation

## 5.4 Tie Resolution Rule

# 6. Context Injection

## 6.1 Document Context Protocol

Every generation call includes document context extracted from the project's loaded TRD/PRD documents. The context is injected into the user prompt — NOT the system prompt — to preserve the system prompt's instruction authority.

## 6.2 Doc Filter Protocol

The BuildThread carries a relevant_docs list set during scope confirmation. This list restricts which documents are searched for context, preventing cross-subsystem contamination when building a specific component.

## 6.3 Forge Context Injection

The current codebase injects a hardcoded Forge architecture summary into every generation prompt. For the new app, this is replaced by a configurable platform context loaded from a file in the project's document store.

# 7. Token Budget and OI-13 Gate

## 7.1 TokenBudget

## 7.2 Budget Enforcement in the Engine

## 7.3 OI-13 Gate Configuration

The OI-13 gate replaces the hardcoded Forge-specific memory budget constants. Limits are now per-project, configured in Settings, and stored in UserDefaults (non-sensitive values — not secrets).

# 8. ConsensusEngine Public API

## 8.1 Engine Interface

## 8.2 Task Type Configurations

## 8.3 Generation System Prompts

### 8.3.1 Test Generation System

### 8.3.2 Review System (used by TRD-3 Stage 6)

# 9. Result Persistence and Surfacing

## 9.1 Audit Log Entry

## 9.2 PR Body Attribution

## 9.3 Build Ledger Integration

# 10. Improvement Pass

## 10.1 When the Improvement Pass Runs

After arbitration, if the winning implementation has identified weaknesses and both scores are below 8, an improvement pass is offered. This takes the winner's content plus the loser's weaknesses and asks Claude to produce a synthesis.

## 10.2 Improvement Prompt

# 11. Error Types

# 12. Default Provider Configurations

# 13. Testing Strategy

## 13.1 Unit Tests

The consensus engine is non-deterministic — different runs with the same input produce different outputs. Unit tests focus on the deterministic structural behavior: routing, fallback logic, budget enforcement, schema validation.

## 13.2 Determinism Tests

Tests that verify the structural behavior is deterministic regardless of LLM output.

Winner selection: given mock ProviderResults with known scores, verify winner_provider matches expected logic

Tie resolution: given equal scores, verify Claude always wins tiebreak

Fallback routing: given one failed ProviderResult, verify single_provider_mode=True and no arbitration call

Budget gates: inject mock results with known costs, verify WARN and STOP fire at correct thresholds

Prompt injection check: verify ARBITRATION_SYSTEM contains the objectivity instruction text (regression test against prompt edits removing it)

## 13.3 Prompt Regression Tests

The arbitration prompt is the most important prompt in the system. Any edit that weakens the objectivity requirement must be caught.

## 13.4 Mock Provider for Testing

# 14. Performance Requirements

# 15. Dependencies

# 16. Out of Scope

# 17. Open Questions

# Appendix A: Cost Model Reference

Approximate costs for common operations. Updated Q1 2026. Verify against provider pricing pages before each release.

# Appendix B: Document Change Log