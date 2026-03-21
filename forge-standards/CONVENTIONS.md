

# Code Conventions — Forge Platform

**Scope:** All code in the Forge monorepo, with dedicated section for the ConsensusDevAgent subsystem.
**Authority:** Treat every numbered rule as a linting-level requirement. PRs that violate any rule must be blocked until fixed.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly:**

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

2. **File names** use `snake_case.py` (Python), `PascalCase.swift` (Swift). No hyphens in source files. No uppercase in Python filenames.

3. **Test files** are named `test_<module_under_test>.py` and live in `tests/<subsystem>/` at the same relative depth as the source module they cover.

4. **No orphan directories.** Every directory under `src/` or `tests/` must contain an `__init__.py` (Python) or be a valid Swift package target.

5. **Generated files** are written to `build/gen/` — never into `src/`. Each generated file must be complete and self-contained (see Rule 38).

---

## 2. Class and Function Naming

6. **Python classes:** `PascalCase`. No suffix like `Class` or `Obj`.
7. **Python functions and methods:** `snake_case`. Verbs first (`fetch_build_map`, `validate_write_path`).
8. **Swift types:** `PascalCase`. Protocols end in `-able`, `-ing`, or `-Provider` (e.g., `TrustFlowAuditable`).
9. **Swift methods and properties:** `camelCase`.
10. **Constants:** `UPPER_SNAKE_CASE` in Python. `static let camelCase` in Swift.
11. **Private symbols** are prefixed with a single underscore in Python (`_strip_code_fences`). In Swift, use `private` access control instead of naming conventions.
12. **Acronyms** in identifiers follow platform convention: `DTLParser` (Swift), `dtl_parser` (Python). Never `d_t_l_parser`.

---

## 3. Error and Exception Patterns

13. **Custom exceptions** inherit from a single `ForgeError` base in `src/forge_errors.py`.
14. **Subsystem exceptions** are scoped: `CalError(ForgeError)`, `VtzError(ForgeError)`, etc.
15. **Never raise bare `Exception` or `RuntimeError`.** Always use a typed subclass.
16. **Error messages** are a single, grep-friendly sentence starting with the subsystem tag:
    ```python
    raise VtzPathTraversalError("[vtz] Write path escapes sandbox: {path}")
    ```
17. **Catch-and-log, then re-raise** when an exception crosses a subsystem boundary. Never silently swallow.
18. **Graceful `None` returns** are required for lookup functions that run before state exists. `fetch_build_map()` must return `None` (not raise) when no map has been created yet — this is the normal state for the first 5 PRs of any build.

---

## 4. Import and Module Organisation

19. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. Forge-internal (`src.*`, `sdk.*`)
    4. Local relative imports

    Blank line between each group.

20. **No wildcard imports** (`from x import *`) anywhere in the codebase.
21. **Relative imports** are allowed only within the same subsystem package. Cross-subsystem imports must be absolute:
    ```python
    # Good (inside src/cal/)
    from .session import CalSession

    # Good (cross-subsystem)
    from src.vtz.enforcer import enforce_zone

    # Bad
    from ..vtz.enforcer import enforce_zone
    ```
22. **Generated code must not use `eval()`, `exec()`, or `importlib.import_module()`** to load other generated files.

---

## 5. Comment and Documentation Rules

23. **Every public function and class** has a docstring. Use Google-style:
    ```python
    def validate_write_path(user_path: str) -> Path:
        """Resolve and validate a write path against sandbox policy.

        Args:
            user_path: The raw, untrusted path string.

        Returns:
            A resolved Path guaranteed to be inside the allowed write root.

        Raises:
            VtzPathTraversalError: If the path escapes the sandbox.
        """
    ```
24. **No `TODO` without a ticket ID.** Format: `# TODO(FORGE-1234): explanation`.
25. **Inline comments** explain *why*, not *what*. If the *what* is unclear, rename the symbol instead.
26. **Module-level docstring** is required at the top of every file, one sentence minimum, describing purpose.

---

## 6. Path Security

27. **Validate paths before ANY write operation.** No exceptions.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```
28. **Never construct write paths via string concatenation or f-strings.** Use `pathlib.Path` / `validate_write_path` exclusively.
29. **Symlink resolution** is mandatory before comparison. `validate_write_path` must call `Path.resolve()` internally.

---

## 7. macOS / Swift UI Conventions

30. **Accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}` and are set via `.accessibilityIdentifier()` on every interactive element:
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
31. **No interactive SwiftUI element** may ship without an `accessibilityIdentifier`. CI UI-test harnesses depend on these selectors.

---

## 8. Shared Utility Duplication Rule

32. **Identical utility functions must stay identical.** `_strip_code_fences()` exists in five modules. Any change to the sanitisation logic must be applied to all five simultaneously in the same PR.
33. **`_strip_code_fences()` contract:**
    - Accept `""` or `None` → return unchanged.
    - Preserve trailing newline on non-empty output.
    - Do not modify code that has no fences or Unicode characters.
    - Must be synchronous — no `async`.

---

## 9. Branch Naming

34. **Agent build branches** follow this exact pattern:
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id`: lowercase alphanumeric, hyphens allowed.
    - `subsystem_slug`: matches a directory name under `src/` (e.g., `cal`, `vtz`, `trustflow`).
    - `N`: zero-padded to 3 digits.
    - `title_slug`: lowercase, hyphen-separated, max 48 characters.

    Example: `forge-agent/build/alice/vtz/pr-007-sandbox-escape-