# TRD-2-Consensus-Engine

_Source: `TRD-2-Consensus-Engine.docx` — extracted 2026-03-21 18:58 UTC_

---

# TRD-2: Consensus Engine

Technical Requirements Document — v2.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-2: Consensus Engine
Version | 2.0
Status | Updated — Native Output Requirement (March 2026)
Author | YouSource.ai
Previous Version | v1.0 (2026-03-19)
Depends on | TRD-1 (macOS Application Shell)
Required by | TRD-3 (Build Pipeline)

## What Changed from v1.0

One targeted addition in response to the Apple App Store rejection pattern affecting AI-generated applications in 2026. All other sections are unchanged from v1.0.

Addition in v2.0: - §4.4 — Native output requirement: prohibition on wrapper generation, eval(), and runtime interpreters - §8.1 — GENERATION_SYSTEM updated to explicitly prohibit wrapper output

## 4.4 Native Output Requirement (New in v2.0)

### 4.4.1 The Problem

Apple is blocking App Store submissions from AI coding tools that generate wrapper applications — apps that contain an interpreter, runtime loader, or dynamic code evaluator rather than compiled native code. This is not an AI policy. It is an App Store policy that has always existed: apps must have deterministic, reviewable behavior. An app that evaluates or loads code at runtime cannot be reviewed deterministically.

The same problem applies beyond the App Store. Enterprise deployment policies, government security requirements, and corporate IT controls all require that software behave predictably at a binary level. A wrapper that loads generated code at runtime cannot be audited, signed, or verified the way a compiled artifact can.

Every vibe coding tool that promised “describe it and it appears” hit this wall because they took a shortcut: generate a runtime wrapper that executes instructions rather than generating real compiled code. The Consensus Engine must never take this shortcut.

### 4.4.2 Requirement — Native Compiled Output Only

This is a hard requirement. It is not configurable. It cannot be overridden by a PR specification.

The Consensus Engine must produce source code that:

Compiles or executes directly without an intermediary runtime, wrapper, or interpreter layer injected by the agent

Contains no eval(), exec(), or dynamic code loading unless the PR specification explicitly requires it as the product’s own feature (e.g., a Python REPL is a valid product feature; a wrapper around generated code is not)

Is written to real source files that a human engineer could read, modify, and own without agent involvement

Passes a static analysis tool (ruff for Python, swiftlint for Swift, eslint for TypeScript) without suppression annotations added solely to silence agent-generated patterns

Produces a deterministic binary or bytecode — the same source compiled twice produces functionally identical output

### 4.4.3 What This Prohibits

The following output patterns are prohibited regardless of how they are framed in a task prompt:

Prohibited pattern | Why prohibited
A Python file that calls exec(open('generated.py').read()) | Loads generated code at runtime — not reviewable
A Swift file that downloads and evaluates a script | Dynamic code loading — App Store violation
A launcher that reads instructions from a JSON file and dispatches to a generated module | Runtime-driven behavior — not deterministic
Any file whose primary function is to interpret or execute other agent-generated output | Wrapper pattern — defeats the purpose of code generation
Template files with placeholders intended to be filled in at runtime | Not real source code — produces non-deterministic behavior

### 4.4.4 What This Requires

The following patterns are required for all generated output:

Required pattern | Why required
Python modules with real classes, functions, and imports | Direct execution, reviewable, testable
Swift files with real types, functions, and protocols | Compiles to native binary via Xcode
TypeScript files with real interfaces and exported functions | Transpiles to deterministic JavaScript
SQL migration files with real DDL statements | Executed directly by database engine
YAML/JSON configuration files with real values | Read directly by the target system

### 4.4.5 Enforcement

The pre-commit validation in the build pipeline (TRD-3 §pre-commit) must include a native output check that rejects: - Any Python file where eval( or exec( appears outside of a test file or an explicit REPL implementation - Any generated file whose entire body is a wrapper around another generated file - Any file smaller than 10 lines that consists only of imports and a call to another generated module

This check runs before the ruff gate and before commit. A violation is treated as a generation failure and triggers the fix loop with the specific error: “Generated code contains prohibited wrapper pattern. Rewrite as native implementation.”

## 8.1 GENERATION_SYSTEM — Updated (v2.0)

The GENERATION_SYSTEM prompt gains one explicit prohibition. The full updated prompt:

GENERATION_SYSTEM = """You are a senior engineer building production-quality software.
You receive a technical task with full context from the project's technical specifications.

Requirements:
- Implement EXACTLY what the task specifies — no more, no less
- Ground every decision in the provided TRD/PRD document excerpts
- Fail closed: prefer explicit error handling over silent degradation
- Security: validate all inputs, reject dangerous paths, never use shell=True
- No placeholder comments like "# TODO: implement this"
- Complete, runnable code only

CRITICAL — Native output requirement:
- Do NOT generate wrappers, launchers, or runtime loaders
- Do NOT use eval(), exec(), or importlib.import_module() to load other generated files
- Do NOT generate template files with runtime placeholders
- Do NOT generate a file whose only job is to call or dispatch to another generated file
- Every file must be a complete, self-contained implementation of its specified purpose
- The output must compile or execute directly without any intermediary agent-managed layer
- A human engineer must be able to read, own, and modify the output without agent involvement

This requirement exists because App Store review, enterprise deployment, and security
audit all require deterministic, reviewable software behavior. Wrapper patterns that
load or evaluate code at runtime cannot be reviewed, signed, or audited.

Respond with ONLY the implementation — no markdown fences, no explanation.
The output will be written directly to a file and executed.
"""

## Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial specification
2.0 | 2026-03-20 | YouSource.ai | Native output requirement (§4.4) — prohibits wrapper generation, eval(), runtime loaders. GENERATION_SYSTEM updated with explicit prohibition. Driven by Apple App Store rejection pattern for vibe-coded AI apps.