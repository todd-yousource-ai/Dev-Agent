# CONVENTIONS.md — Crafted Subsystem

All conventions below are derived from the Crafted TRD corpus and Forge architecture context. Every rule is mandatory for code contributed to the Crafted subsystem.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively.
   - `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/build_ledger.py`, `src/document_store.py`, `src/ci_workflow.py`.
2. **Subsystem directories** are short, lowercase abbreviations matching their canonical names:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK
3. **Tests mirror `src/` exactly.** A source file `src/cal/router.py` has its tests at `tests/cal/test_router.py`. No exceptions.
4. **CI workflow files** are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or split these without TRD update.
5. **`conftest.py`** at the repo root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit this file.

---

## 2. Branch Naming

6. **Branch format is mandatory and must not be altered:**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no spaces.
   - `subsystem_slug`: e.g. `crafted`, `cal`, `trustflow`.
   - `N`: zero-padded to three digits (`001`, `042`).
   - `title_slug`: lowercase, hyphen-delimited summary (max 48 chars).
   - The `forge-agent` prefix is kept intentionally for compatibility — do not change it to any other prefix.

---

## 3. Class and Function Naming

7. **Python classes** use `PascalCase`: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`, `BuildLedger`, `GitHubTool`, `WebhookReceiver`.
8. **Python functions and methods** use `snake_case`: `validate_write_path`, `claim_release`, `chunk`, `embed`, `retrieve`.
9. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
10. **Private module-level variables** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.
11. **Swift types** follow standard Swift `PascalCase` for types and `camelCase` for properties/methods. No deviation.

---

## 4. Crafted-Specific Patterns

### 4.1 axIdentifier Naming (macOS UI)

12. **Every interactive SwiftUI element** must have `.accessibilityIdentifier()` set. No interactive element ships without one.
13. **axIdentifier format:**
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase, hyphen-delimited.
    - `context` is optional and used for dynamic IDs (row indices, entity IDs).
14. **Canonical examples (follow these patterns exactly):**
    | Identifier | Meaning |
    |---|---|
    | `auth-touchid-button` | Touch ID authentication button |
    | `auth-passcode-button` | Passcode fallback button |
    | `settings-anthropic-key-field` | API key text field |
    | `settings-anthropic-key-test-button` | Key validation button |
    | `settings-anthropic-key-reveal-button` | Key visibility toggle |
    | `navigator-project-row-{projectId}` | Project list row (dynamic) |
    | `stream-gate-card-{gateId}` | Gate card container (dynamic) |
    | `stream-gate-yes-button-{gateId}` | Gate approval button (dynamic) |
    | `stream-gate-skip-button-{gateId}` | Gate skip button (dynamic) |
    | `stream-gate-stop-button-{gateId}` | Gate stop button (dynamic) |
15. **Dynamic segments** (e.g. `{projectId}`, `{gateId}`) must be the real entity identifier, not an array index.

### 4.2 Path Security

16. **Validate every path before any write operation.** No exceptions, no shortcuts.
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
17. `validate_write_path` returns a safe default on directory-traversal attempts. Callers must use the returned `safe_path`, never the original input after validation.
18. **Never construct write paths via string concatenation.** Always pass raw user input through `validate_write_path` first, then use `pathlib` operations on the result.

### 4.3 CI Workflow and PR Classification

19. **PR type routing** is handled by `src/build_director.py`. The `pr_type` value drives which CI jobs run and which confidence gates apply.
20. **Docs-only PR detection** (historical v5.0 pattern, removed in v6.0): keyword-list matching against title is deprecated. Do not reintroduce `_docs_keywords` set-based matching. Use the current `build_director` routing logic only.
21. **`ci_workflow.ensure()`** must be called before any CI run to guarantee `conftest.py` and workflow files are in sync. Do not manually push workflow file edits that bypass this function.

### 4.4 Consensus and Generation

22. **`ConsensusEngine`** is the single entry point for all LLM generation in Crafted. Do not call LLM APIs directly from any other module.
23. **System prompts** are defined as module-level constants in `src/consensus.py`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`. To modify prompt content, edit these constants — do not inline prompt strings elsewhere.

### 4.5 Build Ledger

24. **All build claims** go through `BuildLedger.claim()` and `BuildLedger.release()`. Never write build-state metadata outside the ledger.
25. **Heartbeat** must be maintained for any active claim. If a process crashes without releasing, the heartbeat timeout triggers automatic release.

---

## 5. Error and Exception Patterns

26. **Define custom exceptions** in a `_exceptions.py` file within each subsystem directory (e.g. `src/cal/_exceptions.py`). Keep them as flat class hierarchies inheriting from a single subsystem base exception.
27. **Never catch bare `Exception` or `BaseException`** in production code paths. Catch the narrowest type possible.
28. **Path validation failures** must raise (or log-and-return-safe-default, per `validate_write_path` contract) — never silently succeed with the unsafe path.
29. **CI failures** must produce a non-zero exit code. Do not swallow errors to keep a pipeline green.

---

## 6. Import and Module Organisation

30. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules (absolute imports from `src`)
    4. Relative imports within the same subsystem package
    Each group separated by a blank line.
31. **Absolute imports** for cross-subsystem references: `from src.build_ledger import BuildLedger`. Never use relative imports to