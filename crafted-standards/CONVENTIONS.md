# CONVENTIONS.md — CraftedApp Subsystem

All conventions below are derived from the project's TRD documents. Every rule is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
2. **CI workflow files** are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is accepted.
3. **Repo-root files** — the following files must always be committed at the repository root (no directory prefix): `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validation checks basename, not directory path.
4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit or relocate this file.
5. **Branch names** must follow the exact pattern:
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `N` is zero-padded to 3 digits.
   - `title_slug` is lowercase, hyphen-separated.
   - The `forge-agent` prefix is kept intentionally for compatibility — do not rename it.

---

## 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`.
7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure`.
8. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
9. **Private/internal module-level variables** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.
10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - Every segment is lowercase, separated by hyphens.
    - Dynamic context values are appended with brace interpolation in the format `{variableName}`.
    - Examples:
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

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** Import and call `validate_write_path` before any file-system write operation that involves a user-supplied or externally derived path:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Never write to an unvalidated path. The function returns a safe default when a traversal attack is detected — do not catch or suppress that behaviour.
12. **Fail-safe defaults.** When a security-sensitive function detects an invalid input, it must return a safe default value rather than raising an unhandled exception. `validate_write_path` is the canonical example.
13. **No bare `except`.** Always catch specific exception types. Security-related exceptions (path traversal, permission errors) must be logged before returning a safe default.

---

## 4. Import and Module Organisation

14. **Standard library → third-party → project imports**, separated by blank lines (isort-compatible).
15. **Project imports reference `src/` as the package root.** The auto-generated `conftest.py` handles `sys.path` for tests; do not add manual path hacks.
16. **Security imports are always explicit:**
    ```python
    from path_security import validate_write_path
    ```
    Never use `from path_security import *`.
17. **Keyword/constant lists** that are internal to a module are declared as module-level sets or frozensets prefixed with `_`:
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog"}
    ```

---

## 5. Comment and Documentation Rules

18. **Every SwiftUI interactive element** must have a `.accessibilityIdentifier()` modifier. Add a comment above the first usage in a file explaining the naming convention:
    ```swift
    // Convention: {module}-{component}-{role}-{context?}
    // Set via .accessibilityIdentifier() modifier on all interactive elements
    ```
19. **TRD references.** When a code block implements a specific TRD requirement, add a single-line comment citing the TRD section:
    ```python
    # TRD-3 §6.0 — docs-PR detection via label, not keyword list
    ```
20. **No TODO without a tracking issue.** Use the format `# TODO(#123): description`.
21. **Docstrings** are required on all public classes and functions. Use Google-style docstrings in Python.

---

## 6. CraftedApp-Specific Patterns

22. **axIdentifier coverage.** Every interactive SwiftUI element (buttons, text fields, toggles, navigation rows, gate cards) must carry an `.accessibilityIdentifier()` following rule 10. Pull requests that add interactive UI without identifiers must be rejected in review.
23. **CI parity.** All features must pass both `crafted-ci.yml` (Ubuntu / Python) and `crafted-ci-macos.yml` (macOS / Swift). Never add a CI job under a different filename.
24. **`ci_workflow.ensure()` is the sole owner of `conftest.py`.** If tests fail on import, re-run `ci_workflow.ensure()` rather than editing `conftest.py` manually.
25. **Root-file validation.** Any automation that creates or moves repo-root files (rule 3) must validate by basename against the known set, not by checking whether the file's directory is `/`:
    ```python
    ROOT_FILES = {"README.md", "CODEOWNERS", "LICENSE", ".gitignore",
                  ".editorconfig", "VERSION", "Makefile", "pyproject.toml"}
    assert filename in ROOT_FILES
    ```
26. **Path security is non-negotiable.** Every agent, script, or pipeline step that writes to the filesystem must call `validate_write_path` (rule 11). Code reviews must explicitly verify this for every new or modified write path.
27. **Keyword-list deprecation.** Do not use keyword matching for PR classification (the `_docs_keywords` pattern from TRD-3 v5.0 was removed in v6.0). Use labels or structured metadata instead.
28. **Branch name enforcement.** CI or pre-push hooks must reject branch names that do not match the pattern in rule 5. No ad-hoc branch names are permitted for agent-generated work.