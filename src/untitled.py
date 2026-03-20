

I'll implement the three artifacts: canonical naming conventions, glossary, and a naming validation module. Let me analyze the forge context carefully to resolve all naming collisions and establish authoritative conventions.

```python
# forge-standards/naming/CANONICAL_NAMING.md
```

Here are the files:

**forge-standards/naming/CANONICAL_NAMING.md**

```markdown
# Canonical Naming Conventions — Consensus Dev Agent

> **Status:** Normative · **Owner:** PRD-001 Cross-TRD Architecture Baseline
> **Precedence:** This document is authoritative for all shared domain terms.
> All subsequent schema PRs, TRD amendments, and code contributions MUST conform.

---

## 1. Purpose

This document eliminates naming collisions across TRDs and codebases by defining
a single, enforceable set of naming rules for every shared entity, status, identifier,
file path, and process-boundary message type in the Consensus Dev Agent system.

Every term that crosses a module boundary or appears in more than one TRD is governed
here. Module-internal names MAY deviate only if they never appear in any public API,
persisted schema, or XPC message.

---

## 2. Precedence Chain

When naming conflicts arise, resolution follows this strict order:

1. **This document** (`CANONICAL_NAMING.md`) — highest authority
2. **GLOSSARY.md** — defines semantics; naming form must match this document
3. **Owning TRD** — may add module-scoped detail but must not contradict (1) or (2)
4. **Source code** — must conform; non-conforming code is a migration debt item

If a TRD predates this document and uses a deprecated name, the TRD is considered
stale on that term. A migration entry in Section 8 tracks the required update.

---

## 3. Entity Naming Rules

### 3.1 General Rules

| Rule ID | Rule | Example |
|---------|------|---------|
| E-1 | Entities use **PascalCase** in all schemas, Swift types, and Python classes. | `BuildLedger`, `PRSpec` |
| E-2 | Entity names are **singular nouns** unless the entity inherently represents a collection. | `PRSpec` (not `PRSpecs`), `BuildLedger` (ledger is singular) |
| E-3 | Abbreviations of 2–3 letters remain **ALL-CAPS** in PascalCase contexts. | `PRSpec`, `XPCMessage`, `CIResult` |
| E-4 | Abbreviations of 4+ letters use **Title Case**. | `HttpClient` (not `HTTPClient`) |
| E-5 | No Hungarian notation. Type information is not encoded in the name. | `ledger` (not `objLedger`) |
| E-6 | Boolean fields/variables use **is_**, **has_**, or **can_** prefixes in Python; `is`, `has`, `can` in Swift. | `is_approved`, `hasQuorum` |

### 3.2 Canonical Entity Names

These names are **locked**. All code, schemas, and documentation MUST use exactly
these forms:

| Canonical Name | Category | Replaces (Deprecated) | Owning TRD |
|----------------|----------|----------------------|-------------|
| `PRSpec` | Plan entity | `PRPlanEntry`, `pr_plan_entry`, `PlanItem` | TRD-3 |
| `BuildLedger` | Orchestration state | `BuildThread`, `build_thread`, `BuildState` | TRD-3 |
| `BuildStage` | Pipeline phase | `BuildStep`, `PipelineStage`, `build_phase` | TRD-3 |
| `ConsensusResult` | Engine output | `ConsensusOutcome`, `consensus_output`, `MergedResult` | TRD-2 |
| `GenerationRequest` | Engine input | `GenRequest`, `gen_task`, `TaskPrompt` | TRD-2 |
| `ReviewCycle` | Review iteration | `ReviewPass`, `ReviewRound`, `review_iteration` | TRD-4 |
| `ReviewVerdict` | Review decision | `ReviewResult`, `ReviewOutcome`, `review_decision` | TRD-4 |
| `GateDecision` | Operator gate | `GateResult`, `ApprovalResult`, `gate_outcome` | TRD-3 |
| `CIResult` | CI execution | `CIOutcome`, `ci_output`, `PipelineResult` | TRD-6 |
| `DocumentRef` | Document pointer | `DocReference`, `document_id`, `DocPointer` | TRD-7 |
| `AgentConfig` | Configuration | `Config`, `Settings`, `agent_settings` | TRD-1 |
| `ProviderResponse` | LLM response | `LLMResponse`, `llm_result`, `ModelOutput` | TRD-2 |
| `ClaimTicket` | Ledger claim | `ClaimToken`, `LockTicket`, `claim_handle` | TRD-3 |

### 3.3 Compound Entity Rules

| Rule ID | Rule | Example |
|---------|------|---------|
| E-7 | Relationship entities join both entity names, **owner first**. | `BuildLedgerEntry` (not `EntryBuildLedger`) |
| E-8 | Collection wrapper types append `List` or `Set`, never `Array` or `Collection`. | `PRSpecList` |
| E-9 | Request/response pairs use the base name + `Request`/`Response`. | `GenerationRequest`, `GenerationResponse` |

---

## 4. Status and Enum Naming Rules

### 4.1 General Rules

| Rule ID | Rule | Example |
|---------|------|---------|
| S-1 | Enum type names are **PascalCase singular nouns**. | `BuildStage`, `ReviewVerdict` |
| S-2 | Enum cases are **SCREAMING_SNAKE_CASE** in Python, **camelCase** in Swift. | Python: `PENDING_REVIEW`; Swift: `pendingReview` |
| S-3 | Status enums end with the word `Status` only if the entity name does not already imply state. | `ClaimStatus` (not `ClaimTicketStatus` — ticket already implies trackable state) |
| S-4 | Lifecycle enums progress left-to-right: creation → active → terminal. | `PENDING → IN_PROGRESS → SUCCEEDED → FAILED` |
| S-5 | Terminal failure states use `FAILED`, never `ERROR` or `ERRORED`. | `GENERATION_FAILED` (not `GENERATION_ERROR`) |
| S-6 | Terminal success states use `SUCCEEDED`, never `COMPLETED`, `DONE`, or `FINISHED`. | `BUILD_SUCCEEDED` |

### 4.2 Canonical Status Enums

| Enum Name | Cases (Python form) | Owning TRD |
|-----------|-------------------|-------------|
| `BuildStage` | `PLANNING`, `GENERATION`, `REVIEW`, `CI`, `GATE`, `MERGE`, `SUCCEEDED`, `FAILED` | TRD-3 |
| `ConsensusPhase` | `PARALLEL_GENERATION`, `ARBITRATION`, `MERGE`, `SUCCEEDED`, `FAILED` | TRD-2 |
| `ReviewVerdict` | `APPROVED`, `CHANGES_REQUESTED`, `FAILED` | TRD-4 |
| `GateDecision` | `APPROVED`, `REJECTED`, `PENDING` | TRD-3 |
| `ClaimStatus` | `HELD`, `RELEASED`, `EXPIRED`, `STOLEN` | TRD-3 |
| `CIStatus` | `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `TIMED_OUT` | TRD-6 |

---

## 5. Identifier Naming Rules

| Rule ID | Rule | Example |
|---------|------|---------|
| I-1 | Identifiers in schemas and APIs use **snake_case**. | `pr_spec_id`, `build_ledger_id` |
| I-2 | Primary identifiers end with `_id`. | `pr_spec_id` (not `pr_spec_key`) |
| I-3 | Foreign-key references repeat the canonical entity name + `_id`. | `build_ledger_id` in a `PRSpec` record |
| I-4 | UUIDs are always `str` in Python, `String` in Swift. Never raw bytes in APIs. | `pr_spec_id: str` |
| I-5 | Timestamp fields end with `_at` and are ISO-8601 UTC strings in APIs. | `created_at`, `claimed_at` |
| I-6 | Duration fields end with `_seconds` (integer) or `_ms` (integer). Never bare `timeout`. | `heartbeat_interval_seconds` |
| I-7 | Boolean fields follow E-6 and never use bare adjectives. | `is_terminal` (not `terminal`) |

---

## 6. File and Path Conventions

### 6.1 Python Backend

| Rule ID | Rule | Example |
|---------|------|---------|
| F-1 | Module files are **snake_case**, singular nouns matching the primary class. | `build_ledger.py` → `BuildLedger` |
| F-2 | Test files mirror source: `test_<module>.py`. | `test_build_ledger.py` |
| F-3 | Schema files: `<entity>_schema.py` or in `schemas/<entity>.py`. | `schemas/pr_spec.py` |
| F-4 | No `utils.py`, `helpers.py`, or `misc.py`. Every module has a named responsibility. | `path_security.py` (not `utils.py`) |

### 6.2 Swift Frontend

| Rule ID | Rule | Example |
|---------|------|---------|
| F-5 | Swift files match their primary type in **PascalCase**. | `BuildLedgerView.swift` |
| F-6 | SwiftUI views: `<Entity>View.swift`. | `PRSpecView.swift` |
| F-7 | View models: `<Entity>ViewModel.swift`. | `PRSpecViewModel.swift` |

### 6.3 Documentation

| Rule ID | Rule | Example |
|---------|------|---------|
| F-8 | TRDs: `TRD-<number>-<Title-Kebab-Case>.md`. | `TRD-3-Build-Pipeline.md` |
| F-9 | Standards: live under `forge-standards/<category>/`. | `forge-standards/naming/CANONICAL_NAMING.md` |

---

## 7. XPC and Process-Boundary Terms

### 7.1 Message Type Rules

| Rule ID | Rule | Example |
|---------|------|---------|
| X-1 | XPC message types are **dot-delimited**, lowercase, max 3 segments. | `build.stage.update` |
| X-2 | First segment is the **domain**: `build`, `consensus`, `review`, `ci`, `gate`, `config`. | `consensus.result.ready` |
| X-3 | Second segment is the **entity** (singular, canonical). | `build.ledger.claimed` |
| X-4 | Third segment is the **event verb** in past tense or present imperative. | `build.stage.transitioned`, `gate.decision.request` |
| X-5 | Unknown message types are **discarded and logged**, never raised as exceptions. | See TRD-11 §XPC |

### 7.2 Canonical XPC Message Types

| Message Type | Direction | Payload Entity | Owning TRD |
|-------------|-----------|---------------|-------------|
| `build.stage.transitioned` | Backend → Frontend | `BuildStage` | TRD-3 |
| `build.ledger.claimed` | Backend → Frontend | `ClaimTicket` | TRD-3 |
| `build.ledger.released` | Backend → Frontend | `ClaimTicket` | TRD-3 |
| `consensus.result.ready` | Engine → Pipeline | `ConsensusResult` | TRD-2 |
| `consensus.phase.updated` | Engine → Frontend | `ConsensusPhase` | TRD-2 |
| `review.verdict.ready` | Review → Pipeline | `ReviewVerdict` | TRD-4 |
| `review.cycle.started` | Review → Frontend | `ReviewCycle` | TRD-4 |
| `ci.status.updated` | CI → Pipeline | `CIStatus` | TRD-6 |
| `ci.result.ready` | CI → Pipeline | `CIResult` | TRD-6 |
| `gate.decision.request` | Pipeline → Frontend | `GateDecision` | TRD-3 |
| `gate.decision.received` | Frontend → Pipeline | `GateDecision` | TRD-3 |

---

## 8. Enforcement and Migration

### 8.1 Enforcement

- **CI lint rule** (`naming_lint.py`): validates all public symbols, schema fields,
  and XPC message types against this document. Non-conforming code fails CI.
- **PR review checklist**: every PR introducing a new shared term must reference
  this document and GLOSSARY.md. If the term is new, it must be added to the
  glossary in the same PR.
- **Schema migration**: any schema change that renames a field must include a
  migration script and a deprecation entry in the glossary.

### 8.2 Known Migration Debt

| Current Name | Target Canonical Name | Location | Tracking |
|-------------|----------------------|----------|----------|
| `BuildThread` | `BuildLedger` | `src/build_ledger.py` internal comments | Migration-001 |
| `PRPlanEntry` | `PRSpec` | `src/build_director.py` | Migration-002 |
| `ConsensusOutcome` | `ConsensusResult` | `src/consensus.py` | Migration-003 |
| `ReviewPass` | `ReviewCycle` | `src/review_engine.py` | Migration-004 |
| `review_decision` | `ReviewVerdict` | `src/review_engine.py` | Migration-005 |

### 8.3 Adding New Terms

1. Check GLOSSARY.md for existing canonical name.
2. If no entry exists, propose in the PR description with: name, category, definition, owning TRD.
3. Naming review is **mandatory** for any term crossing module boundaries.
4. After merge, update GLOSSARY.md in the same PR — no deferred glossary updates.

---

## 9. Security Considerations

- **Path validation**: all file path references in naming rules assume
  `path_security.validate_write_path()` enforcement. Names that would produce
  path-traversal risks (e.g., `../`) are invalid by definition.
- **No secrets in names**: entity names, enum values, and identifiers MUST NOT
  encode secrets, tokens, or credentials. Violation is a security defect.
- **XPC unknown types**: per TRD-11, unknown message types are discarded and
  logged. The naming system does not define fallback behavior — unknown is unknown.
```

**forge-standards/naming/GLOSSARY.md**

```markdown
# Glossary — Consensus Dev Agent Shared Domain Terms

> **Status:** Normative · **Owner:** PRD-001 Cross-TRD Architecture Baseline
> **Precedence:** Subordinate to `CANONICAL_NAMING.md` on naming form;
> authoritative on term semantics and deprecation status.

---

## How to Read This Glossary

Each entry contains:

| Field | Meaning |
|-------|---------|
| **Canonical Name** | The one true name. Use exactly this form everywhere. |
| **Category** | `entity`, `enum`, `identifier`, `xpc-message`, `concept` |
| **Definition** | Precise semantic meaning in the Consensus Dev Agent domain. |
| **Owning TRD** | The TRD that defines the primary specification. |
| **Deprecated Aliases** | Names that previously referred to this concept. Do not use. |
| **Notes** | Usage constraints, relationships, or security considerations. |

---

## A

### AgentConfig

| Field | Value |
|-------|-------|
| Canonical Name | `AgentConfig` |
| Category | entity |
| Definition | Top-level configuration object for a Consensus Dev Agent instance. Contains provider keys (by reference