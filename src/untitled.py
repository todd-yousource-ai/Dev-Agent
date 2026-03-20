I'll implement the three artifacts specified in the plan. Let me analyze the context carefully to resolve naming collisions and establish canonical conventions.

```python
# First, let me create the directory structure and all three files

import os

# forge-standards/naming/CANONICAL_NAMING.md
# forge-standards/naming/GLOSSARY.md
# src/naming_registry.py
```

Here are the implementations:

**forge-standards/naming/CANONICAL_NAMING.md:**

```
# Canonical Naming Conventions — Consensus Dev Agent

> **Owner:** Forge Platform Engineering
> **Status:** Authoritative
> **Applies to:** All 12 TRDs, all Python/Swift source, all IPC boundaries
> **Change process:** Any modification requires PR review by platform-eng + security-eng

---

## 1. Purpose

This document is the single source of truth for naming conventions across the
Consensus Dev Agent codebase. All new code, TRD amendments, and review feedback
MUST conform to these rules. Where existing code deviates, the canonical name
defined here takes precedence and the old name is listed in §8 Deprecated Aliases.

**Security note:** Consistent naming prevents confusion-based vulnerabilities
where two subsystems use different names for the same concept, leading to
misrouted data, bypassed gates, or silent identity mismatches.

---

## 2. Entity Naming Rules

### 2.1 Types and Classes — PascalCase

All domain types, classes, structs, enums, and protocols use **PascalCase**.
No underscores, no prefixes (except Swift protocols which may use `-Protocol` suffix
at the process boundary only).

| Context       | Convention     | Example                        |
|---------------|----------------|--------------------------------|
| Python class  | PascalCase     | `ConsensusEngine`, `BuildLedger` |
| Swift class   | PascalCase     | `ForgeXPCService`, `BuildIntent` |
| Swift struct  | PascalCase     | `PRPlan`, `ReviewVerdict`       |
| Enum type     | PascalCase     | `BuildStage`, `PRStatus`        |
| Protocol      | PascalCase     | `ConsensusProvider`             |

### 2.2 Fields, Variables, Parameters — snake_case (Python) / camelCase (Swift)

| Language | Convention  | Example                          |
|----------|-------------|----------------------------------|
| Python   | snake_case  | `build_id`, `pr_number`, `stage_name` |
| Swift    | camelCase   | `buildId`, `prNumber`, `stageName`    |

**Process-boundary rule:** When a value crosses XPC/IPC from Swift to Python or
vice versa, the JSON wire format uses **snake_case**. The Swift side converts
at the boundary. This is non-negotiable — the Python side never receives camelCase.

### 2.3 Constants and Enum Members — SCREAMING_SNAKE_CASE (Python) / camelCase (Swift)

| Language | Convention            | Example                                |
|----------|-----------------------|----------------------------------------|
| Python   | SCREAMING_SNAKE_CASE  | `MAX_REVIEW_PASSES = 3`, `STAGE_GENERATION` |
| Swift    | camelCase (enum case) | `.generation`, `.reviewPass`            |

### 2.4 Boolean Fields

Boolean fields MUST be prefixed with `is_`, `has_`, `can_`, or `should_` in Python
(`is`, `has`, `can`, `should` in Swift). Bare adjectives are prohibited.

```
# CORRECT
is_approved: bool
has_ci_passed: bool
can_merge: bool

# WRONG — ambiguous, prohibited
approved: bool
ci_passed: bool
mergeable: bool
```

---

## 3. Status Enum Naming Rules

All status enums follow a strict pattern to prevent the proliferation of
ad-hoc status strings observed in early development.

### 3.1 Canonical Status Enum Names

Each subsystem defines at most ONE status enum for its primary entity:

| Enum Name           | Owning Module          | Members (SCREAMING_SNAKE)                                    |
|---------------------|------------------------|--------------------------------------------------------------|
| `BuildStatus`       | `build_director.py`    | `PENDING`, `IN_PROGRESS`, `GENERATION`, `REVIEW`, `CI`, `GATED`, `APPROVED`, `MERGED`, `FAILED`, `CANCELLED` |
| `PRStatus`          | `build_ledger.py`      | `CLAIMED`, `IN_PROGRESS`, `REVIEW_PENDING`, `CI_PENDING`, `GATED`, `APPROVED`, `MERGED`, `FAILED` |
| `ConsensusStatus`   | `consensus.py`         | `PENDING`, `PROVIDER_A_COMPLETE`, `PROVIDER_B_COMPLETE`, `ARBITRATING`, `RESOLVED`, `FAILED` |
| `ReviewVerdict`     | `consensus.py`         | `APPROVED`, `CHANGES_REQUESTED`, `REJECTED`                  |
| `CIResult`          | `ci_runner.py`         | `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `TIMED_OUT`        |
| `GateDecision`      | `gate_manager.py`      | `WAITING`, `APPROVED`, `REJECTED`                            |

### 3.2 Rules

1. Status values are **SCREAMING_SNAKE_CASE** strings in Python, stored and transmitted as such.
2. Status enums inherit from `str, enum.Enum` so they serialize naturally to JSON.
3. No subsystem may invent ad-hoc status strings outside its canonical enum.
4. Unknown status values received from external input MUST cause a **fail-closed**
   rejection with logged context — never silent coercion to a default.

---

## 4. Identifier Format Patterns

### 4.1 Primary Identifiers

| Identifier       | Format                         | Example                                      | Generated By         |
|------------------|--------------------------------|----------------------------------------------|----------------------|
| `build_id`       | `build-{UUIDv4}`              | `build-a1b2c3d4-e5f6-7890-abcd-ef1234567890` | `build_director.py`  |
| `pr_plan_id`     | `prplan-{UUIDv4}`             | `prplan-...`                                  | `build_director.py`  |
| `consensus_id`   | `cons-{UUIDv4}`               | `cons-...`                                    | `consensus.py`       |
| `review_pass_id` | `review-{pass_number}-{UUIDv4}` | `review-1-...`                              | `consensus.py`       |
| `ledger_entry_id`| `ledger-{UUIDv4}`             | `ledger-...`                                  | `build_ledger.py`    |
| `gate_id`        | `gate-{UUIDv4}`               | `gate-...`                                    | `gate_manager.py`    |

### 4.2 Rules

1. All UUIDs are **v4**, lowercase, hyphenated. No other UUID format is accepted.
2. Identifiers are **opaque** to all subsystems except the generator. No subsystem
   may parse the UUID portion to extract meaning.
3. Prefixes (`build-`, `prplan-`, `cons-`, etc.) are mandatory and validated on receipt.
   A `build_id` that does not start with `build-` MUST be rejected fail-closed.
4. Identifiers MUST NOT appear in log messages without the `[REDACT-SAFE]` marker
   confirming they contain no embedded secrets. Current identifiers are redact-safe
   by construction (UUID only).

---

## 5. File and Module Naming

### 5.1 Python Modules

| Convention          | Rule                                                       |
|---------------------|------------------------------------------------------------|
| Module files        | `snake_case.py` — no hyphens, no uppercase                |
| Test files          | `test_{module_name}.py`                                    |
| Config files        | `snake_case.yaml` or `snake_case.json`                     |
| Constants modules   | `{subsystem}_constants.py`                                 |

### 5.2 Swift Files

| Convention          | Rule                                                       |
|---------------------|------------------------------------------------------------|
| Source files        | `PascalCase.swift` — one primary type per file             |
| Test files          | `{TypeName}Tests.swift`                                    |
| XPC protocol files  | `{ServiceName}Protocol.swift`                              |

### 5.3 Documentation and Standards

| Convention          | Rule                                                       |
|---------------------|------------------------------------------------------------|
| TRDs                | `TRD-{number}-{Hyphenated-Title}.md`                      |
| Standards           | `SCREAMING_SNAKE.md` in `forge-standards/`                 |
| Architecture docs   | `PascalCase.md` or `SCREAMING_SNAKE.md`                    |

---

## 6. Process-Boundary Terms (XPC / IPC)

When domain objects cross the Swift ↔ Python boundary via XPC:

### 6.1 Wire Format

- **Encoding:** JSON over XPC, UTF-8, no BOM.
- **Field names:** Always `snake_case` on the wire.
- **Enum values:** Always `SCREAMING_SNAKE_CASE` strings on the wire.
- **Timestamps:** ISO 8601 with timezone, e.g. `2025-01-15T10:30:00Z`.
- **Identifiers:** Full prefixed form (e.g. `build-{uuid}`), never bare UUIDs.

### 6.2 Canonical Message Types

| XPC Message Type          | Direction       | Payload Root Key      |
|---------------------------|-----------------|-----------------------|
| `build_intent`            | Swift → Python  | `intent`              |
| `build_status_update`     | Python → Swift  | `status`              |
| `gate_request`            | Python → Swift  | `gate`                |
| `gate_response`           | Swift → Python  | `decision`            |
| `pr_plan_update`          | Python → Swift  | `pr_plan`             |
| `consensus_result`        | Python → Swift  | `consensus`           |

### 6.3 Unknown Message Handling

Per Forge invariant: **XPC unknown message types are discarded and logged — never
raised as exceptions.** The log entry MUST include the unknown type string and a
timestamp. The unknown type string is truncated to 256 chars before logging to
prevent log injection.

---

## 7. Collision Resolution Log

This section documents every naming collision found across TRDs and codebase,
the decision made, and the rationale.

| Collision                          | Resolution                      | Rationale                                                                                              | Date       |
|------------------------------------|---------------------------------|--------------------------------------------------------------------------------------------------------|------------|
| `PRSpec` vs `PRPlanEntry`          | **`PRPlanEntry`** is canonical  | `PRSpec` was used informally in TRD-3 early drafts. `PRPlanEntry` is more precise — it is one entry in a `PRPlan`, not a specification document. `PRSpec` is now a deprecated alias. | 2025-01-15 |
| `BuildThread` vs `BuildLedger`     | **`BuildLedger`** is canonical  | `BuildThread` was used in TRD-4 discussion to mean the ledger's per-PR tracking. The canonical module is `build_ledger.py` and the class is `BuildLedger`. `BuildThread` is deprecated. | 2025-01-15 |
| `merge_gate` vs `approval_gate`    | **`ApprovalGate`** is canonical | `merge_gate` conflated the merge action with the approval decision. The gate decides approval; the merge is a subsequent action. `merge_gate` is deprecated in code; `ApprovalGate` is the type. | 2025-01-15 |
| `task` vs `build_intent`           | **`BuildIntent`** is canonical  | `task` is overloaded (Python asyncio, general English). `BuildIntent` is the domain term for the operator's plain-language request that initiates a build. | 2025-01-15 |
| `provider` vs `llm_provider`       | **`LLMProvider`** is canonical  | `provider` alone is ambiguous (could be cloud provider, service provider). `LLMProvider` is explicit. | 2025-01-15 |
| `review_cycle` vs `review_pass`    | **`ReviewPass`** is canonical   | A "cycle" implies returning to start. A "pass" is one iteration of the up-to-3 review sequence. `ReviewPass` matches TRD-2 §4.3. | 2025-01-15 |
| `ci_run` vs `ci_execution`         | **`CIExecution`** is canonical  | `ci_run` is informal. `CIExecution` parallels `CIResult` and is used in TRD-6. | 2025-01-15 |
| `prompt` vs `generation_prompt`    | **`GenerationPrompt`** is canonical | `prompt` is dangerously overloaded. `GenerationPrompt` is the specific artifact sent to LLM providers for code generation. `ReviewPrompt` is the artifact for review. | 2025-01-15 |

---

## 8. Deprecated Aliases

These names MUST NOT appear in new code. Existing usages should be migrated.
The `NamingRegistry` (see `src/naming_registry.py`) can validate compliance.

| Deprecated Name    | Canonical Replacement | Migration Deadline |
|--------------------|-----------------------|--------------------|
| `PRSpec`           | `PRPlanEntry`         | Next release       |
| `BuildThread`      | `BuildLedger`         | Next release       |
| `merge_gate`       | `ApprovalGate`        | Next release       |
| `task` (as domain) | `BuildIntent`         | Next release       |
| `provider` (bare)  | `LLMProvider`         | Next release       |
| `review_cycle`     | `ReviewPass`          | Next release       |
| `ci_run`           | `CIExecution`         | Next release       |
| `prompt` (bare)    | `GenerationPrompt` / `ReviewPrompt` | Next release |

---

## 9. Ownership and Change Process

1. This document is owned by **Forge Platform Engineering**.
2. Changes require a PR with approvals from **platform-eng** and **security-eng**.
3. Any new domain term MUST be added to both this document and `GLOSSARY.md`.
4. The `NamingRegistry` in `src/naming_registry.py` MUST be updated in the same PR
   that adds or changes a canonical name.
5. CI validation via `NamingRegistry.validate_name()` enforces compliance.
```

**forge-standards/naming/GLOSSARY.md:**

```
# Domain Glossary — Consensus Dev Agent

> **Owner:** Forge Platform Engineering
> **Status:** Authoritative
> **Companion to:** `CANONICAL_NAMING.md`
> **Change process:** Same as `CANONICAL_NAMING.md` — PR with platform-eng + security-eng approval

---

## Usage

Every shared domain term used across TRDs or in cross-module interfaces MUST
appear in this glossary. Terms are alphabetical. Each entry specifies:

- **Canonical Name**: The name to use in code, docs, and conversation.
- **Definition**: Precise meaning, no ambiguity.
- **Owning TRD**: The TRD that authoritatively defines this concept.
- **Usage Scope**: Where the term appears (code module, wire protocol, UI, docs).
- **Security Notes**: Any security-relevant constraints on the term's usage.

---

## Glossary

| # | Canonical Name | Definition | Owning TRD | Usage Scope | Security Notes |
|---|----------------|------------|------------|-------------|----------------|
| 1 | **ApprovalGate** | A synchronization point where the build pipeline halts and waits indefinitely for an explicit operator approval or rejection. Gates never auto-approve. The operator's decision is a `GateDecision`. | TRD-3 | `gate_manager.py`, XPC (`gate_request`/`gate_response`), Swift UI | Gate timeout is infinite by design. Any mechanism that auto-approves is a security violation. |
| 2 | **Arbitration** | The process by which Claude evaluates two competing LLM outputs (from Provider A and Provider B) and selects
