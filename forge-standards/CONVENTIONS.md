

# Code Conventions — Forge Platform

> **Scope:** All code in the Forge mono-repo, with §6 dedicated to the ConsensusDevAgent subsystem.
> Version: 1.0 · Effective immediately · Every PR must comply.

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

2. **Test files mirror source files 1-to-1.** `src/cal/session.py` → `tests/cal/test_session.py`. No exceptions.

3. **All file and directory names use `snake_case`.** No hyphens, no camelCase, no uppercase in file names.

4. **Generated files live under `gen/` at the repo root**, never inside `src/`. Generated files must never be imported by other generated files (see §6.6).

5. **Branch naming is mandatory and machine-enforced:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: GitHub handle, lowercase.
   - `subsystem_slug`: one of `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`.
   - `N`: zero-padded three-digit PR sequence number.
   - `title_slug`: kebab-case summary, max 48 chars.

   Example: `forge-agent/build/alee/trustflow/pr-007-add-audit-retention-policy`

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Suffix with the pattern role when applicable: `…Error`, `…Handler`, `…Policy`, `…Gate`, `…Session`.

7. **Functions and methods:** `snake_case`. Verb-first: `validate_write_path`, `fetch_build_map`, `strip_code_fences`.

8. **Private helpers:** Single leading underscore (`_strip_code_fences`). Never use double underscores for name-mangling unless genuinely required.

9. **Constants:** `UPPER_SNAKE_CASE`. Define at module level, never inside a function.

10. **Type aliases:** `PascalCase`, suffixed with `T` only when disambiguating from a concrete class (e.g., `GateResultT`).

11. **axIdentifier strings (macOS UI):** Follow the pattern `{module}-{component}-{role}-{context?}`. Set via `.accessibilityIdentifier()` on every interactive element.

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    ```

    - All segments are lowercase kebab-case.
    - `{context}` is optional; include it when multiple instances of the same component exist (e.g., per `gateId`).

---

## 3. Error and Exception Patterns

12. **Define one base exception per subsystem** in `<subsystem>/errors.py`:

    ```python
    class TrustFlowError(Exception):
        """Base for all TrustFlow exceptions."""
    ```

13. **All subsystem exceptions inherit from that base.** Never raise bare `Exception`, `ValueError`, or `RuntimeError` in library code.

14. **Exception class names end in `Error`**, not `Exception`.

15. **Include structured context** in every raised exception:

    ```python
    raise PathTraversalError(
        f"Blocked write to disallowed path: {user_path}",
        attempted_path=user_path,
        resolved_path=resolved,
    )
    ```

16. **Never silently swallow exceptions.** `except SomeError: pass` is forbidden. At minimum, log at `warning` level.

17. **Graceful `None` returns are required where documented.** Example: `fetch_build_map()` must return `None` (never raise) when no map exists yet — this is the expected state for the first 5 PRs of any build.

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` with `profile = black`):

    1. Standard library
    2. Third-party packages
    3. Forge `src/` packages
    4. Forge `sdk/` packages
    5. Local relative imports

    Separate each group with a blank line.

19. **No wildcard imports** (`from x import *`) anywhere.

20. **No circular imports.** If two subsystems need each other, extract the shared type into `src/common/types.py`.

21. **Lazy imports** are allowed only inside functions that are called at runtime for optional heavy dependencies (e.g., ML model loaders). Document the reason with a comment.

22. **Never use `eval()`, `exec()`, or `importlib.import_module()` to load generated files** or to dispatch between modules. Every module must be a complete, self-contained unit.

---

## 5. Comment and Documentation Rules

23. **Every public module, class, and function has a docstring.** Use Google-style:

    ```python
    def validate_write_path(user_path: str) -> Path:
        """Resolve and validate a user-supplied path for safe writing.

        Args:
            user_path: Raw path string from external input.

        Returns:
            Resolved pathlib.Path guaranteed to be inside the allowed tree.

        Raises:
            PathTraversalError: If the resolved path escapes the sandbox.
        """
    ```

24. **Inline comments explain *why*, not *what*.** Delete comments that restate the code.

25. **TODO format:** `# TODO(username): YYYY-MM-DD — description`. TODOs without a date and owner are rejected in review.

26. **No commented-out code in `main` or release branches.** Use version control history.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security — Validate Before Every Write

27. **Every agent write operation must validate the target path first.** No exceptions, no shortcuts.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

28. **Never construct a writable path from string concatenation alone.** Always pass through `validate_write_path` even if the path looks safe.

### 6.2 The `_strip_code_fences()` Contract

29. **All five modules that define `_strip_code_fences()` must contain byte-identical implementations.** Any change to one must be applied to all five simultaneously in the same commit.

30. The function must satisfy these invariants:
    - Accept `""` or `None` → return the input unchanged.
    - Preserve a trailing newline on non-empty output.
    - Leave content unmodified when no fences or Unicode replacement characters are present.
    - Be synchronous (never `async`).

31. **CI runs a dedicated check** (`scripts/check_strip_fences_sync.py`) that diffs the AST of all five copies and fails the build on divergence.

### 6.3 Build Map Resilience

32. `fetch_build_map()` must return `None` gracefully when no build map exists. It must never raise an exception. This is the normal state during the first 5 PRs of any build.

33. **All callers of `fetch_build_map()` must handle the `None` case explicitly** — never assume a map