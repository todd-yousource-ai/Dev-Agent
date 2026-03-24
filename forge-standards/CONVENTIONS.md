# CONVENTIONS.md — Crafted Subsystem

All rules derived from the Crafted TRD documents and Forge architecture context. Every rule is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively. No hyphens, no camelCase in filenames.
   - `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/build_ledger.py`, `src/document_store.py`, `src/ci_workflow.py`

2. **Subsystem directories** under `src/` use short lowercase slugs matching the canonical abbreviation:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

3. **Test directories** mirror `src/` structure exactly. A source file at `src/cal/router.py` has tests at `tests/cal/test_router.py`. No exceptions.

4. **CI workflow files** are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming variants are permitted.

5. **`conftest.py`** at the repository root is auto-committed by `ci_workflow.ensure()` to guarantee `src/` is importable. Never manually edit or delete this file.

---

## 2. Branch Naming

6. **All agent branches** follow this exact pattern:
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric identifier of the assigned engineer.
   - `subsystem_slug` — lowercase slug of the subsystem (e.g., `crafted`, `cal`, `trustflow`).
   - `N` — zero-padded to three digits (e.g., `001`, `042`).
   - `title_slug` — kebab-case summary, max 48 characters.
   - The `forge-agent` prefix is **kept intentionally for compatibility**. Do not rename it.

---

## 3. Class and Function Naming

7. **Classes** use `PascalCase`: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`, `BuildLedger`, `GitHubTool`, `WebhookReceiver`.

8. **Functions and methods** use `snake_case`: `validate_write_path()`, `ensure()`, `claim()`, `release()`, `chunk()`, `embed()`, `retrieve()`.

9. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

10. **Private/internal identifiers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Never use double underscores for name-mangling unless specifically required by the Python data model.

---

## 4. Crafted-Specific Patterns

### 4.1 axIdentifier Naming (macOS / SwiftUI)

11. Every interactive SwiftUI element **must** have an `.accessibilityIdentifier()` set.

12. The identifier string follows this pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are **lowercase kebab-case**.
    - `context` is optional and used for dynamic items (row IDs, gate IDs).

13. Canonical examples (deviate only by extending, never by restructuring):
    ```
    "auth-touchid-button"
    "auth-passcode-button"
    "settings-anthropic-key-field"
    "settings-anthropic-key-test-button"
    "settings-anthropic-key-reveal-button"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    "stream-gate-skip-button-{gateId}"
    "stream-gate-stop-button-{gateId}"
    ```

14. Dynamic suffixes (e.g., `{projectId}`, `{gateId}`) are interpolated at runtime. In tests, match them with a prefix or regex — never hard-code a UUID.

### 4.2 Path Security

15. **Validate every path before any write operation.** No exceptions, no shortcuts.
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
    `validate_write_path` returns a safe default on directory-traversal attempts. Never write to a path that has not passed through this function.

16. Any PR that introduces a file-write without a preceding `validate_write_path` call **must** be rejected in review.

### 4.3 PR Type Routing and Docs Detection

17. PR classification logic lives in `src/build_director.py`. The `pr_type` routing determines pipeline behaviour (build vs. docs vs. hotfix).

18. Docs-PR detection (v6.0+) is handled by the build director's routing logic, **not** by keyword-list matching. The v5.0 keyword-list pattern (`_docs_keywords` set + `any(kw in title_lower ...)`) was removed in v6.0. Do not reintroduce it.

### 4.4 Consensus and Generation Systems

19. `src/consensus.py` owns `ConsensusEngine` and all system-prompt constants: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM`. These constants must not be duplicated elsewhere.

20. When generating Swift code via the consensus engine, always combine `SWIFT_GENERATION_SYSTEM` with `UI_ADDENDUM`. Never use `SWIFT_GENERATION_SYSTEM` alone for UI-related generation.

---

## 5. Error and Exception Patterns

21. **Custom exceptions** are defined per-subsystem in a `exceptions.py` file within the subsystem directory (e.g., `src/cal/exceptions.py`).

22. Exception class names end with `Error` (not `Exception`): `PathTraversalError`, `LedgerClaimError`, `ConsensusTimeoutError`.

23. All exceptions raised across subsystem boundaries must inherit from a shared `ForgeError` base class to enable uniform catch handling in the build pipeline.

24. Never use bare `except:`. Always catch a specific exception type. At minimum, use `except Exception:` and log the traceback.

25. Path-security violations raise immediately. They must not be caught and silently swallowed anywhere in the call chain.

---

## 6. Import and Module Organisation

26. **Import order** (enforced by linter configuration):
    1. Standard library imports
    2. Third-party imports
    3. Forge/Crafted `src/` imports
    4. Relative imports (within the same subsystem only)

    Separate each group with a single blank line.

27. **Relative imports** are permitted only within a subsystem package (e.g., inside `src/cal/`). Cross-subsystem imports must use absolute paths from `src/`:
    ```python
    # Correct (cross-subsystem)
    from src.build_ledger import BuildLedger

    # Correct (intra-subsystem)
    from .exceptions import LedgerClaimError

    # Wrong (relative cross-subsystem)
    from ..cal.router import route
    ```

28. **Circular imports** are forbidden. If two modules need each other, extract the shared type or interface into a third module.

29. The `conftest.py` generated by `ci_workflow.ensure()` adds `src/` to `sys.path`. Tests import from `src/` as if it were a top