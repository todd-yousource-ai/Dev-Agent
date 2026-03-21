

# Code Conventions — Forge Platform

> Authoritative coding conventions for the Forge platform and the **ConsensusDevAgent** subsystem. Every rule is mandatory unless explicitly marked *optional*. Violations must be caught in CI or code review.

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

2. **Python files** use `snake_case.py`. No hyphens, no uppercase.
3. **Swift files** use `PascalCase.swift`, one primary type per file, filename matches the type name.
4. **Test files** are prefixed `test_` (Python) or suffixed `Tests` (Swift) and live under `tests/<subsystem>/`, mirroring the source path depth-for-depth.
5. **No orphan directories.** Every directory must contain an `__init__.py` (Python) or at least one source file; empty namespace placeholders are not allowed.

---

## 2. Branch Naming

6. **All agent-created branches must follow this format exactly:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — lowercase alphanumeric, hyphens allowed.
   - `subsystem_slug` — must match a directory name under `src/` or `sdk/`.
   - `N` — zero-padded to three digits (`001`, `012`, `137`).
   - `title_slug` — lowercase, hyphen-separated, max 48 characters.

7. **Manual feature branches** use `feat/{subsystem_slug}/{short-description}`. Hotfix branches use `fix/{subsystem_slug}/{short-description}`.

---

## 3. Class and Function Naming

8. **Python classes** — `PascalCase`. No underscores.
9. **Python functions and methods** — `snake_case`. Verbs first (`fetch_build_map`, `validate_write_path`).
10. **Constants** — `UPPER_SNAKE_CASE`, defined at module level.
11. **Private helpers** — single leading underscore (`_strip_code_fences`). Never use double underscores for name-mangling unless overriding a dunder method.
12. **Swift types** — `PascalCase`. Protocols end in `-able`, `-ing`, or `-Protocol` only when disambiguation is required.
13. **Swift methods and properties** — `camelCase`. Boolean properties read as assertions (`isValid`, `hasConsensus`).

---

## 4. Accessibility Identifier Convention (macOS / SwiftUI)

14. **Every interactive element** must set `.accessibilityIdentifier()`.
15. **Format:** `{module}-{component}-{role}-{context?}`

    ```swift
    // Static elements
    "auth-touchid-button"
    "auth-passcode-button"
    "settings-anthropic-key-field"
    "settings-anthropic-key-test-button"
    "settings-anthropic-key-reveal-button"

    // Dynamic elements — append the entity ID
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    "stream-gate-skip-button-{gateId}"
    "stream-gate-stop-button-{gateId}"
    ```

16. **Segments are always lowercase, hyphen-separated.** No underscores, no camelCase inside identifiers.

---

## 5. Error and Exception Patterns

17. **Custom exceptions** inherit from a single project base class, `ForgeError`.

    ```python
    class ForgeError(Exception):
        """Base for all Forge-raised exceptions."""

    class PathTraversalError(ForgeError): ...
    class ConsensusTimeoutError(ForgeError): ...
    ```

18. **Never catch bare `Exception`** except at top-level entrypoints or event loops where the error is logged and re-raised or converted to a structured response.
19. **Error messages** must include the subsystem name and enough context to locate the failure without a stack trace:

    ```python
    raise PathTraversalError(
        f"[vtz] Write blocked: resolved path '{resolved}' escapes sandbox '{sandbox_root}'"
    )
    ```

20. **Swift errors** conform to `LocalizedError` and provide `errorDescription`.

---

## 6. Path Security

21. **Validate paths before ANY write.** No exceptions, no shortcuts.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    ```

22. **Never construct a writable path by string concatenation.** Use `pathlib.Path` and resolve before writing.
23. **Agent-generated code must not write outside its designated output directory.** The output directory is injected via configuration, never hard-coded.

---

## 7. Import and Module Organisation

24. **Import order** (enforced by `isort` with the `black` profile):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/…`)
    4. Local / relative imports

    Each group is separated by a single blank line.

25. **No wildcard imports** (`from module import *`) anywhere.
26. **Relative imports** are allowed only within a single subsystem package. Cross-subsystem references use absolute imports rooted at `src/`:

    ```python
    # Inside src/cal/session.py — OK
    from .message import Message

    # Cross-subsystem — absolute
    from src.vtz.enforcer import enforce_zone
    ```

27. **Generated files must not use `eval()`, `exec()`, or `importlib.import_module()`** to load other generated files. Every generated file must be complete and self-contained.

---

## 8. Shared Utility Functions

28. **The `_strip_code_fences()` function must be identical across all five modules that use it.** Any change to sanitisation logic must be applied to all five simultaneously, verified by a dedicated CI check.
29. **Contract for `_strip_code_fences()`:**
    - Accept an empty string or `None` and return it unchanged.
    - Preserve trailing newline on non-empty output.
    - Do not modify code that has no fences or Unicode characters.
    - Must be synchronous (no `async`).

30. When a utility is shared by more than two subsystems, extract it into `src/common/` and import it. Do not copy-paste.

---

## 9. Comment and Documentation Rules

31. **Module-level docstring** is required in every Python file. First line is a single sentence summarising purpose.
32. **Public functions and methods** require a docstring with `Args`, `Returns`, and `Raises` sections (Google-style).
33. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.
34. **TODO format:** `# TODO(engineer_id): description — JIRA-123` or `# TODO(agent): description — TRD-N §section`.
35. **No commented-out code** in `main` or any long-lived branch. Use version control.
36. **Swift documentation** uses `///` doc comments with `- Parameter`, `- Returns`, and `- Throws` tags.

---

## 10. ConsensusDevAgent-Specific Patterns

37. **`fetch_build_map()` must return `None` gracefully** when no build map exists yet (expected for the first five PRs of any build). It must never raise an exception in that case.
38. **No template files with runtime plac