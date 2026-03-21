

# Code Conventions — Forge Platform

> Authoritative coding conventions for the Forge platform and the **ConsensusDevAgent** subsystem.
> Every rule is mandatory unless explicitly marked **(advisory)**. PR reviewers must enforce these rules; CI may automate enforcement where noted.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem boundaries exactly.**

   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Labels
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   tests/<subsystem>/ # Tests mirror src/ structure exactly
   ```

2. **Python files** use `snake_case.py`. No hyphens, no uppercase.
3. **Swift files** use `PascalCase.swift`, one primary type per file, filename matches the type name.
4. **Test files** are prefixed `test_` (Python) or suffixed `Tests` (Swift) and live under `tests/<subsystem>/`, mirroring the `src/` path segment-for-segment.

   ```
   src/cal/session.py       → tests/cal/test_session.py
   src/trustflow/emitter.py → tests/trustflow/test_emitter.py
   ```

5. **No generated file may exist solely to call or dispatch to another generated file.** Every file must be a complete, self-contained unit (see §6, rule 6).

---

## 2. Class and Function Naming

6. **Python classes** — `PascalCase`. No underscores.
7. **Python functions and methods** — `snake_case`. Verbs first (`validate_write_path`, `fetch_build_map`).
8. **Python constants** — `UPPER_SNAKE_CASE`, defined at module level.
9. **Swift types** — `PascalCase`. Protocols do **not** use an `I` prefix; use a `-able`/`-ing`/`-Protocol` suffix only when the noun form is ambiguous.
10. **Swift methods and properties** — `camelCase`.
11. **Accessibility identifiers (macOS / SwiftUI)** follow the pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Set via `.accessibilityIdentifier()` on **every** interactive element. Examples:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

12. **Branch names** are mandatory and follow this exact template:

    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

    - `engineer_id` — GitHub username, lowercase.
    - `subsystem_slug` — matches the `src/` directory name (e.g., `cal`, `vtz`, `trustflow`).
    - `N` — zero-padded to 3 digits.
    - `title_slug` — lowercase, hyphen-separated, ≤ 48 characters.

---

## 3. Error and Exception Patterns

13. **Define one base exception per subsystem** in `<subsystem>/exceptions.py`:

    ```python
    class CalError(Exception):
        """Base for all CAL exceptions."""
    ```

14. **All subsystem exceptions inherit from the subsystem base**, never from bare `Exception`.
15. **Never catch bare `Exception` or `BaseException`** except at a top-level entry point (CLI main, HTTP handler root). Always log the original traceback before re-raising or converting.
16. **Path traversal validation is required before every filesystem write.** No exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

17. **`fetch_build_map()` must return `None` (not raise) when no map exists.** This is the expected state for the first 5 PRs of any build. Tests must assert this (see `TestBuildMapLive`).

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` with profile `black`):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src.*`, `sdk.*`)
    4. Local relative imports

    Separate each group with a single blank line.

19. **No dynamic code loading in generated files.** Generated code must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.
20. **No circular imports.** If two modules need each other, extract the shared type into a third module or use `TYPE_CHECKING`-guarded imports.
21. **Relative imports** are permitted only within the same subsystem package. Cross-subsystem imports must be absolute:

    ```python
    # Good — cross-subsystem
    from src.vtz.enforcer import enforce_zone

    # Good — intra-subsystem
    from .session import Session
    ```

---

## 5. Comment and Documentation Rules

22. **Every public module, class, and function must have a docstring.** Use Google-style docstrings for Python:

    ```python
    def validate_write_path(path: str) -> Path:
        """Validate and resolve a user-supplied path for safe writing.

        Args:
            path: Raw path string from untrusted input.

        Returns:
            Resolved Path guaranteed to be within the allowed write root.

        Raises:
            PathTraversalError: If the resolved path escapes the sandbox.
        """
    ```

23. **Inline comments explain *why*, not *what*.** If a comment restates the code, delete it.
24. **TODO format** — `# TODO(username): description — TICKET-123`. TODOs without a ticket reference are rejected in review.
25. **No commented-out code in `main` or any release branch.** Use version control; don't comment-disable.

---

## 6. ConsensusDevAgent-Specific Patterns

26. **`_strip_code_fences()` is a canonical shared function.** The identical implementation must exist in all five modules that use it. Any change must be applied to all five simultaneously, in the same PR. The function contract:
    - Accepts an empty string or `None` → returns the value unchanged.
    - Preserves trailing newline on non-empty output.
    - Does not modify code that contains no fences or unicode characters.
    - Is synchronous — never `async`.

27. **Generated files must be self-contained.** A generated file must never:
    - Use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.
    - Consist of a template with runtime placeholders.
    - Exist solely to call or dispatch to another generated file.

28. **Gate interactions in the consensus stream** must use typed enums, not raw strings:

    ```python
    class GateAction(str, Enum):
        YES = "yes"
        SKIP = "skip"
        STOP = "stop"
    ```

29. **Every agent write operation** must call `validate_write_path()` (rule 16) **before** opening a file handle. There is no "trusted path" shortcut.

30. **Build-map access is defensive.** `fetch_build_map()` must:
    - Return `None` when no map exists (never raise).
    - Be covered by a `TestBuildMapLive` test that asserts graceful `None` return.

31. **PR sequencing.** Agent-authored PRs are numbered per-build. The branch name encodes the sequence (`pr-001`, `pr-002`, …). CI must reject a PR whose branch number is not exactly one greater than the last merged PR for that `engineer_id`/`subsystem_slug` pair, unless it is `pr-001`.

32. **