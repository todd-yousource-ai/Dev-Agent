# TRD-2-Consensus-Engine-Crafted

_Source: `TRD-2-Consensus-Engine-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-2: Consensus Engine

Technical Requirements Document — v3.0

Product: Crafted Document: TRD-2: Consensus Engine Version: 3.0 Status: Updated — Prompt Audit Fixes (March 2026) Author: YouSource.ai Previous Version: v2.0 (2026-03-20) Depends on: TRD-1 (macOS Application Shell) Required by: TRD-3 (Build Pipeline)

## What Changed from v2.0

Three prompt-level changes from the system prompt audit (SP-6, SP-8, SP-9). All sections from v2.0 are unchanged unless noted.

§4.5 — Swift prompt split: SWIFT_GENERATION_SYSTEM divided into universal base + SWIFT_UI_ADDENDUM, injected conditionally (new)

§8.1 — REVIEW_SYSTEM: absolute restructuring prohibition replaced with minimum-change principle (updated)

§8.2 — COMPARATIVE_EVAL_SYSTEM: scoring scale fully defined with band anchors at every level (updated)

## §4.5 Swift Prompt Split (New in v3.0)

### The Problem

The previous SWIFT_GENERATION_SYSTEM applied all 14 rules to every Swift PR regardless of whether it involved UI. A PR building the macOS IPC bridge, a Keychain helper, or a background daemon received SwiftUI rules, WCAG compliance instructions, and accessibilityLabel requirements — noise that consumed tokens and could confuse the model’s focus.

### The Fix

The prompt is now split into two parts:

SWIFT_GENERATION_SYSTEM — universal Swift rules that apply to every PR regardless of content:

Swift 5.9+ syntax, macOS 13.0 minimum target

Swift concurrency (async/await, actors) — no DispatchQueue unless bridging legacy code

Actors for shared mutable state, no class-level locks

Keychain via Security.framework directly, no third-party wrappers

Never force-unwrap optionals — guard-let or if-let with explicit failure paths

Error types conform to LocalizedError with meaningful errorDescription

Every public function and type has a documentation comment

SWIFT_UI_ADDENDUM — SwiftUI-specific rules, appended only when the PR involves UI components:

All UI code uses SwiftUI, no AppKit unless explicitly required

@MainActor on all MainActor-bound types and functions

SwiftUI views are composable, keep View bodies focused and under ~100 lines

@EnvironmentObject for shared state, not singletons

No hardcoded user-visible strings — use LocalizedStringKey

Every interactive element has an accessibilityLabel (WCAG 2.1 AA)

.accessibilityIdentifier() on interactive elements for XCUITest

### Dispatch Logic

In consensus.py run(), after selecting lang == “swift”, the first 500 characters of the combined task + context are scanned for UI keywords:

_ui_keywords = {"view", "swiftui", " ui ", "screen", "window", "button",
                "toolbar", "sheet", "alert", "navigation", "list", "form"}

_combined = (task + " " + context[:500]).lower()
if any(kw in _combined for kw in _ui_keywords):
    gen_system = gen_system.rstrip() + "\n" + SWIFT_UI_ADDENDUM

### Right-altitude principle

Apply Swift concurrency, error handling, and security patterns universally. Apply SwiftUI-specific rules only when the PR involves UI components.

## §8.1 REVIEW_SYSTEM — Updated (v3.0)

### The Change

The previous absolute prohibition blocked the reviewer from fixing fundamentally wrong architectural choices — a class where the spec requires a module-level function, stateful code that should be stateless. The new wording prevents gratuitous rewrites without blocking necessary structural fixes.

 | Text
Before (v2.0) | Make ONLY targeted, minimal corrections. Do NOT restructure or rewrite.
After (v3.0) | Make ONLY targeted, minimal corrections. Don’t make changes beyond what’s needed to fix the identified issues.

### Right-altitude principle

Fix identified issues with the minimum change required. Don’t make unrelated improvements.

## §8.2 COMPARATIVE_EVAL_SYSTEM Scoring Scale — Updated (v3.0)

### The Problem

The v2.0 scale defined anchors at 7 (production-ready) and 5 (serious issues) but left 5–7 undefined. The CRITICAL/IMPORTANT framing was compensating for an underspecified scale rather than adding information. A model asked to score 6 had no definition to anchor to, producing inconsistent scoring across calls.

### The Fix

Full band anchors defined at every meaningful level. CRITICAL/IMPORTANT framing removed. Explicit priority order for winner selection added.

Score | Label | Meaning
9–10 | Exemplary | Exceeds spec, no issues, production-ready without changes
7–8 | Good | Meets spec, minor issues only, production-ready with small fixes
5–6 | Acceptable | Mostly correct, has gaps that need addressing before merge
3–4 | Problematic | Missing key requirements or significant correctness issues
1–2 | Failing | Does not implement the spec or has blocking security/correctness flaws

Winner selection guidance (replaces IMPORTANT framing):

Select the winner based on which implementation better satisfies security, correctness, and spec compliance — in that order of priority.

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification
2.0 | 2026-03-20 | Native output requirement (§4.4) — prohibits wrapper generation, eval(), runtime loaders. GENERATION_SYSTEM updated with explicit prohibition.
3.0 | 2026-03-22 | SP-6: SWIFT_GENERATION_SYSTEM split into universal base + SWIFT_UI_ADDENDUM with keyword dispatch (§4.5). SP-8: REVIEW_SYSTEM absolute prohibition softened to minimum-change principle (§8.1). SP-9: COMPARATIVE_EVAL_SYSTEM scoring scale fully defined with band anchors; CRITICAL/IMPORTANT framing removed (§8.2).