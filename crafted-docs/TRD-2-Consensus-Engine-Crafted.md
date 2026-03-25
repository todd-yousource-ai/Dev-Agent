# TRD-2-Consensus-Engine-Crafted

_Source: `TRD-2-Consensus-Engine-Crafted.docx` — extracted 2026-03-25 20:37 UTC_

---

TRD-2: Consensus Engine

Technical Requirements Document — v3.0

Field | Value
Product | Crafted
Document | TRD-2: Consensus Engine
Version | 3.0
Status | Updated — Prompt Audit Fixes (March 2026)
Author | YouSource.ai
Previous Version | v2.0 (2026-03-20)
Depends on | TRD-1 (macOS Application Shell)
Required by | TRD-3 (Build Pipeline)

# 1. Purpose and Scope

This document specifies the Consensus Engine — the dual-model code generation and arbitration subsystem of the Crafted Dev Agent. It owns the system prompts, generation algorithm, evaluation scoring, improvement pass, and pre-PR review. All LLM calls for code generation flow through this module.

The Consensus Engine uses Claude (Anthropic) and OpenAI GPT in parallel to generate implementations, evaluates both with a single comparative evaluation call, and selects the winner based on security, correctness, and spec compliance. A conditional improvement pass runs on close races.

# 2. Design Decisions

Decision | Choice | Rationale
Parallel generation | Both models generate simultaneously | Eliminates sequential latency; wall-clock time = max(claude, openai) not sum
Single comparative evaluation | Claude scores both in one call | ~50% token reduction vs evaluating each model separately; Claude has full Forge context
Conditional improvement | Only on close races (score delta < 2) | Clear winners don't benefit; improvement pass adds cost only when meaningful
Context truncation | Max 60,000 tokens of injected context | Prevents context bloat on large PRDs; least-specific sections truncated from end
Evaluator identity | Claude always arbitrates | Claude has deeper Forge platform context; instructed to evaluate with strict objectivity

# 3. ConsensusResult Dataclass

@dataclass

class ConsensusResult:

task:           str           # Original PR task description

claude_code:    str           # Claude's generated implementation

openai_code:    str           # OpenAI's generated implementation

claude_score:   dict          # {score: int, rationale: str}

openai_score:   dict          # {score: int, rationale: str}

winner:         str           # "claude" | "openai"

rationale:      str           # One-sentence technical reason for winner

final_code:     str           # Winning code (after improvement pass if run)

improvements:   list[str]     # Improvements applied to winning code

duration_sec:   float         # Wall-clock time for the full consensus run

token_estimate: int           # Estimated token usage

timestamp:      float         # Unix timestamp

# 4. System Prompts

## 4.1 Forge Engineering Standards Summary

Injected into every generation and review system prompt via the {FORGE_STANDARDS_SUMMARY} placeholder:

Forge Engineering Standards (key rules):

- Secure by design, deny-by-default

- No hardcoded secrets; all external input validated

- Fail closed on auth/crypto/identity errors

- Small composable modules; no silent failure paths

- Production-grade: every error surfaces with context

- Every dependency justified

## 4.2 GENERATION_SYSTEM (Python/default)

Applied to all non-Swift PRs. Instructs the model to implement every acceptance criterion, write to exact target files, fail closed on all error paths, and respond with only the implementation code:

You are a senior security-focused engineer on the Forge platform

(enterprise AI agent runtime enforcement, defense/financial sector clients).

{FORGE_STANDARDS_SUMMARY}

You will receive a PR specification with:

- Target files: the exact file(s) to create or modify

- Description: what this PR builds

- Implementation plan: step-by-step guidance

- Acceptance criteria: every item MUST be satisfied in the output

- Test cases: the tests that will be run against your code

Rules:

- Implement EVERY acceptance criterion — they are the contract

- Write to the exact target files specified — do not invent new filenames

- If the target file ends in .md — output clean markdown, not Python

- If the target file ends in .py — output valid Python, not markdown

- All error paths must fail closed and log explicitly

- No swallowed exceptions, no silent failures

- No hardcoded secrets or credentials

Respond with ONLY the implementation — no markdown fences, no explanation.

Include docstrings explaining security assumptions and failure behavior.

## 4.3 SWIFT_GENERATION_SYSTEM (Swift)

Applied to all Swift PRs. Universal Swift rules regardless of whether the PR involves UI:

You are a senior macOS/Swift engineer on the Forge platform

(enterprise AI agent runtime enforcement, defense/financial sector clients).

{FORGE_STANDARDS_SUMMARY}

Swift rules that apply to every PR:

- Use Swift 5.9+ syntax. Target macOS 13.0 minimum.

- Use Swift concurrency (async/await, actors) — no DispatchQueue unless bridging legacy code.

- Actors for shared mutable state. No class-level locks.

- All Keychain operations use Security.framework directly — no third-party wrappers.

- Never force-unwrap optionals. Use guard-let or if-let with explicit failure paths.

- Error types conform to LocalizedError with a meaningful errorDescription.

- Every public function and type has a documentation comment.

Rules:

- Implement EVERY acceptance criterion — they are the contract

- Write to the exact target files specified — do not invent new filenames

- All error paths must fail closed with explicit logging

- No force-unwrapped optionals, no silent failures

Respond with ONLY the implementation code — no markdown fences, no explanation.

Include comments explaining security assumptions and failure behavior.

# §4.4 Native Output Enforcement (New in v2.0)

A post-generation check rejects code that uses wrapper patterns instead of native implementation: eval(), exec(), importlib.import_module() as a runtime loader, or runtime code injection patterns. If detected, the PR is regenerated. This targets the common LLM pattern of wrapping code in a loader rather than implementing it directly.

The check runs after both models generate, before the comparative evaluation. A PR that generates wrapper code from both models triggers a regeneration with an explicit prohibition added to the prompt.

# §4.5 Swift Prompt Split (New in v3.0)

## The Problem

The previous SWIFT_GENERATION_SYSTEM applied all 14 rules to every Swift PR regardless of whether it involved UI. A PR building the macOS IPC bridge, a Keychain helper, or a background daemon received SwiftUI rules, WCAG compliance instructions, and accessibilityLabel requirements — noise that consumed tokens and could confuse the model's focus.

## The Fix

The prompt is now split into two parts:

SWIFT_GENERATION_SYSTEM — universal Swift rules that apply to every PR regardless of content (§4.3 above).

SWIFT_UI_ADDENDUM — SwiftUI-specific rules, appended only when the PR involves UI components:

All UI code uses SwiftUI, no AppKit unless explicitly required

@MainActor on all MainActor-bound types and functions

SwiftUI views are composable — keep View bodies focused and under ~100 lines

@EnvironmentObject for shared state, not singletons

No hardcoded user-visible strings — use LocalizedStringKey

Every interactive element has an accessibilityLabel (WCAG 2.1 AA)

.accessibilityIdentifier() on interactive elements for XCUITest

## Dispatch Logic

In consensus.py run(), after selecting lang == "swift", the first 500 characters of the combined task + context are scanned for UI keywords:

_ui_keywords = {"view", "swiftui", " ui ", "screen", "window", "button",

"toolbar", "sheet", "alert", "navigation", "list", "form"}

_combined = (task + " " + context[:500]).lower()

if any(kw in _combined for kw in _ui_keywords):

gen_system = gen_system.rstrip() + "\n" + SWIFT_UI_ADDENDUM

Right-altitude principle: apply Swift concurrency, error handling, and security patterns universally. Apply SwiftUI-specific rules only when the PR involves UI components.

# 5. Token Budget

The consensus engine tracks per-provider token usage and enforces budget limits:

Parameter | Value | Description
MAX_CONTEXT_TOKENS | 60,000 | Maximum context injected into generation prompts; truncated from end if exceeded
CLOSE_RACE_THRESHOLD | 2 | Score delta below which improvement pass runs
Soft cap | Configurable | Warns operator when approaching budget; logged once
Hard cap | Configurable | Raises TokenBudgetExceeded; build stops with cost report

Context truncation removes the least-specific sections from the end of the context string. The most specific sections (acceptance criteria, implementation plan, target files) are preserved at the front.

# 6. Generation Algorithm

## 6.1 Run Sequence

Step | Operation | Provider
1 | Generate implementation in parallel | Claude + OpenAI simultaneously
2 | Truncate context to MAX_CONTEXT_TOKENS | N/A (local)
3 | Native output check — reject wrappers, eval(), runtime loaders | Local (no LLM)
4 | Single comparative evaluation — scores both implementations | Claude only
5 | Select winner based on scores | Local (no LLM)
6 (conditional) | Improvement pass — only if score delta < 2 | Claude (winning model)
7 | Return ConsensusResult | N/A

## 6.2 Language Routing

The language parameter in run() selects the system prompt:

language=="swift" → SWIFT_GENERATION_SYSTEM (+ SWIFT_UI_ADDENDUM if UI keywords detected)

language=="python" (default) → GENERATION_SYSTEM

language=="go", "typescript", "rust" → GENERATION_SYSTEM (language noted in task description)

# 7. Comparative Evaluation (COMPARATIVE_EVAL_SYSTEM)

## 7.1 Evaluation Criteria

Priority | Criterion | What it measures
1 (highest) | Security posture | Fail-closed behavior, input validation, no injection surface
2 | Spec compliance | Does the implementation match the TRD/PRD requirements exactly
3 | Correctness | Error handling completeness, edge cases, type safety
4 | Forge Engineering Standards | Traceability, audit logging, determinism
5 | Code quality | Clarity, maintainability, no unnecessary complexity

## 7.2 JSON Response Schema

{

"winner": "claude" | "openai",

"claude_score": 1-10,

"openai_score": 1-10,

"rationale": "one concrete sentence citing the specific technical reason for the winner",

"claude_weaknesses": ["specific technical weakness, max 3"],

"openai_weaknesses": ["specific technical weakness, max 3"],

"evaluator": "claude"

}

# 8. System Prompt Specifications

## 8.1 IMPROVEMENT_SYSTEM

Called only on close races (score delta < CLOSE_RACE_THRESHOLD=2). Instructs the model to apply the specific weaknesses identified in the comparative evaluation to the winning implementation. Does not restructure or rewrite — targeted fixes only.

You are improving the winning implementation of a Forge component.

Apply only the specific improvements listed. Do not restructure or rewrite.

{FORGE_STANDARDS_SUMMARY}

Respond with ONLY the improved code — no markdown fences.

## REVIEW_SYSTEM — Updated (v3.0)

Pre-PR review: runs after tests pass, before GitHub commit. Catches what tests cannot — missing error handling, security gaps, spec non-compliance, poor naming, unnecessary complexity.

You are a Forge senior code reviewer conducting a pre-PR quality check.

You receive a single implementation that has already passed its test suite.

Your job: catch what tests cannot — missing error handling, security gaps,

spec non-compliance, poor naming, unnecessary complexity.

Make ONLY targeted, minimal corrections. Don't make changes beyond

what's needed to fix the identified issues.

{FORGE_STANDARDS_SUMMARY}

Respond ONLY in valid JSON — no preamble, no markdown fences:

{

"verdict": "approved" | "needs_changes",

"issues": ["specific issue description", ...],

"improved_code": "complete corrected file if needs_changes, else empty string"

}

Rules:

- If verdict is "approved":      improved_code MUST be an empty string.

- If verdict is "needs_changes": improved_code MUST be the full corrected file.

- Maximum 5 issues listed. Focus on blocking issues only.

- Do not invent requirements not in the spec or acceptance criteria.

# §8.1 REVIEW_SYSTEM — Updated (v3.0)

## The Change

The previous absolute prohibition ('Do NOT restructure or rewrite') blocked the reviewer from fixing fundamentally wrong architectural choices — a class where the spec requires a module-level function, stateful code that should be stateless. The new wording prevents gratuitous rewrites without blocking necessary structural fixes.

 | Text
Before (v2.0) | Make ONLY targeted, minimal corrections. Do NOT restructure or rewrite.
After (v3.0) | Make ONLY targeted, minimal corrections. Don't make changes beyond what's needed to fix the identified issues.

Right-altitude principle: fix identified issues with the minimum change required. Don't make unrelated improvements.

# §8.2 COMPARATIVE_EVAL_SYSTEM Scoring Scale — Updated (v3.0)

## The Problem

The v2.0 scale defined anchors at 7 (production-ready) and 5 (serious issues) but left 5–7 undefined. The CRITICAL/IMPORTANT framing was compensating for an underspecified scale rather than adding information. A model asked to score 6 had no definition to anchor to, producing inconsistent scoring across calls.

## The Fix

Score | Label | Meaning
9–10 | Exemplary | Exceeds spec, no issues, production-ready without changes
7–8 | Good | Meets spec, minor issues only, production-ready with small fixes
5–6 | Acceptable | Mostly correct, has gaps that need addressing before merge
3–4 | Problematic | Missing key requirements or significant correctness issues
1–2 | Failing | Does not implement the spec or has blocking security/correctness flaws

Winner selection guidance (replaces CRITICAL/IMPORTANT framing):

Select the winner based on which implementation better satisfies

security, correctness, and spec compliance — in that order of priority.

# 9. LLM Telemetry

Every consensus run emits telemetry to the audit log:

audit.log_event("consensus_complete", {

"task":          task[:100],

"winner":        winner,

"claude_score":  claude_score["score"],

"openai_score":  openai_score["score"],

"rationale":     rationale,

"duration_sec":  duration_sec,

"token_estimate": token_estimate,

"improvement_applied": bool(improvements),

})

LLM trace log: every prompt and response written to logs/llm_trace.log with call number, provider, stage, token count, and duration. Terminal verbosity controlled by CRAFTED_LLM_VERBOSE env var (0=silent, 1=preview, 2=full). See TRD-15 §9 for the full observability specification.

# 10. Acceptance Criteria

Both models generate implementations in parallel — wall-clock time = max(claude, openai)

Single comparative evaluation call — not two separate per-model evaluations

Improvement pass runs if and only if score delta < CLOSE_RACE_THRESHOLD (2)

Context truncated to MAX_CONTEXT_TOKENS (60,000) before injection

Native output check rejects eval(), exec(), and runtime loaders before evaluation

SWIFT_UI_ADDENDUM injected only when PR task/context contains UI keywords

REVIEW_SYSTEM minimum-change principle enforced — no gratuitous rewrites

COMPARATIVE_EVAL_SYSTEM scoring scale uses full band anchors at every level

All consensus calls recorded in audit log with scores, winner, and rationale

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 | Native output requirement (§4.4) — prohibits wrapper generation, eval(), runtime loaders. GENERATION_SYSTEM updated with explicit prohibition.
3.0 | 2026-03-22 | SP-6: SWIFT_GENERATION_SYSTEM split into universal base + SWIFT_UI_ADDENDUM with keyword dispatch (§4.5). SP-8: REVIEW_SYSTEM absolute prohibition softened to minimum-change principle (§8.1). SP-9: COMPARATIVE_EVAL_SYSTEM scoring scale fully defined with band anchors; CRITICAL/IMPORTANT framing removed (§8.2).