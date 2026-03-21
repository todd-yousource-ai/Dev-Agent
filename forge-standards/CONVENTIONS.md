

# Code Conventions — Forge Platform

> **Scope:** All code in the Forge monorepo, with dedicated section for the ConsensusDevAgent subsystem.
> Last updated: 2025-07-10

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem boundaries exactly.**

   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   tests/<subsystem>/ # Tests mirror src/ structure exactly
   ```

2. **Test directories mirror `src/` one-to-one.** A file at `src/cal/session.py` must have its tests at `tests/cal/test_session.py`. No exceptions.

3. **Python files** use `snake_case.py`. No hyphens, no uppercase.

4. **Swift files** use `PascalCase.swift`, matching the primary type declared inside.

5. **Directories** use lowercase slugs with no separators (`trustflow`, not `trust_flow` or `trust-flow`).

6. **Branch names** follow this mandatory pattern:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: GitHub username, lowercase.
   - `subsystem_slug`: matches `src/` directory name (e.g., `cal`, `vtz`).
   - `N`: zero-padded three-digit PR sequence number.
   - `title_slug`: kebab-case summary, max 40 characters.

   Example: `forge-agent/build/jdoe/trustflow/pr-007-add-audit-sink`

---

## 2. Class and Function Naming

7. **Python classes** use `PascalCase`. Acronyms longer than two letters are title-cased (`McpPolicyEngine`, not `MCPPolicyEngine`).

8. **Python functions and variables** use `snake_case`. No trailing underscores except to avoid keyword collision (`type_`).

9. **Constants** use `UPPER_SNAKE_CASE` and are declared at module level.

10. **Swift types** use `PascalCase`. Swift properties and methods use `camelCase`.

11. **axIdentifier values** (SwiftUI accessibility identifiers) follow this convention exactly:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Set via `.accessibilityIdentifier()` on **every** interactive element. Examples:

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

    Omit `{context?}` only when the element is globally unique.

---

## 3. Error and Exception Patterns

12. **Define one exception base class per subsystem** in `<subsystem>/errors.py`:

    ```python
    class TrustFlowError(Exception):
        """Base for all TrustFlow exceptions."""
    ```

13. **Specific exceptions inherit from the subsystem base**, never from bare `Exception`:

    ```python
    class AuditSinkFullError(TrustFlowError): ...
    ```

14. **Never catch bare `Exception` or `BaseException`** unless re-raising. Catch the narrowest type possible.

15. **Error messages include the subsystem prefix** for grep-ability:

    ```python
    raise PathTraversalError(f"[vtz] blocked write to disallowed path: {path}")
    ```

16. **Path validation before any write.** Every code path that writes to disk must call `validate_write_path` first. No inline checks — use the canonical function:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

17. **`fetch_build_map()` and similar first-run accessors must return `None` gracefully** when no data exists yet. They must never raise an exception on absence. Validate this with a dedicated test (`TestBuildMapLive`).

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` with `profile = black`):

    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/`)
    4. Local relative imports

    Separate each group with a single blank line.

19. **No wildcard imports** (`from x import *`) anywhere.

20. **No runtime dynamic loading of generated files.** Generated code must not use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

21. **Relative imports only within the same subsystem.** Cross-subsystem imports use absolute paths:

    ```python
    # Inside src/trustflow/sink.py — OK:
    from .config import SinkConfig

    # Cross-subsystem — always absolute:
    from src.vtz.enforcer import enforce_zone
    ```

22. **Circular imports are a build-breaking error.** If two modules need each other, extract the shared type into a third module.

---

## 5. Comment and Documentation Rules

23. **Every public function and class has a docstring.** Use Google-style docstrings:

    ```python
    def validate_write_path(path: str) -> Path:
        """Validate and resolve a path, blocking directory traversal.

        Args:
            path: User-supplied filesystem path.

        Returns:
            Resolved pathlib.Path guaranteed to be inside the workspace.

        Raises:
            PathTraversalError: If the path escapes the workspace root.
        """
    ```

24. **No TODO without an issue link.** Format: `# TODO(forge#1234): description`.

25. **Inline comments explain _why_, not _what_.** If a comment restates the code, delete it.

26. **Type hints on every function signature.** Use `from __future__ import annotations` at the top of every Python file for forward-reference support.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Generated File Rules

27. **Every generated file must be complete and self-contained.** It must not:
    - Use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.
    - Contain runtime template placeholders (e.g., `{{VALUE}}`).
    - Exist solely to call or dispatch to another generated file.

28. **Generated files carry a header comment** identifying the generation system and timestamp:

    ```python
    # Generated by ConsensusDevAgent GENERATION_SYSTEM v2.0
    # Timestamp: 2025-07-10T14:23:00Z
    # DO NOT EDIT — regenerate via `forge agent generate`
    ```

### 6.2 `_strip_code_fences()` Canonical Implementation

29. **The `_strip_code_fences()` function must be identical across all five modules that use it.** The canonical copy lives in `src/cal/sanitise.py`. All other modules must import from there; no duplicated implementations.

30. **`_strip_code_fences()` contract:**
    - Accept an empty string or `None` → return unchanged.
    - Preserve trailing newline on non-empty output.
    - Leave code with no fences or Unicode characters unmodified.
    - Must be synchronous (no `async`).

31. **Any change to `_strip_code_fences