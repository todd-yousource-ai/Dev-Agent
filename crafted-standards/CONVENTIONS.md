# CONVENTIONS.md — CraftedApp Subsystem

---

## 1. File and Directory Naming

1. **Python modules** use `snake_case` with no abbreviations:
   - `src/consensus.py`, `src/build_director.py`, `src/path_security.py`.
2. **CI workflow files** are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming variants are permitted.
3. **Repo-root files** — the following files must always live at the repository root with no directory prefix: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validation checks basename membership against this known set, not directory path.
4. **conftest.py** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit or relocate it; regenerate through the CI helper.
5. **Test files** mirror the source file they test: `src/consensus.py` → `tests/test_consensus.py`.

---

## 2. Branch Naming

6. **All agent branches** follow this exact template (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `{engineer_id}` — lowercase alphanumeric identifier of the engineer or agent.
   - `{subsystem_slug}` — e.g. `crafted-app`, `build-pipeline`.
   - `{N:03d}` — zero-padded three-digit PR sequence number.
   - `{title_slug}` — kebab-case summary, max 48 characters.

---

## 3. Class and Function Naming

7. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`.
8. **Python functions and variables** use `snake_case`: `validate_write_path`, `safe_path`.
9. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
10. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.
11. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element:
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
    All four segments are lowercase kebab-case. The `{context?}` segment is required when there are multiple instances (e.g., dynamic IDs).

---

## 4. Error and Exception Patterns

12. **Path validation before every write.** Import and call `validate_write_path` before any file-system write operation:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    The function returns a safe default on directory-traversal attempts; never bypass it with raw `open()` on user-supplied paths.
13. **Fail loudly on invalid paths.** If `validate_write_path` returns a fallback path that differs from the requested path, log a warning at `WARNING` level including the original requested path (sanitised to remove secrets).
14. **No bare `except`.** Always catch a specific exception class. Prefer `except OSError` or `except ValueError` over `except Exception` unless re-raising.

---

## 5. Import and Module Organisation

15. **Import order** (enforced by linter): stdlib → third-party → local `src/` modules, separated by blank lines.
16. **Local imports** use explicit relative paths from `src/`:
    ```python
    from src.consensus import ConsensusEngine
    from src.build_director import BuildPipeline
    ```
17. **No wildcard imports.** `from module import *` is banned in all files.
18. **Lazy imports** are permitted only inside functions when avoiding circular dependencies; add a `# lazy import: circular` comment.

---

## 6. Comment and Documentation Rules

19. **Every public class and function** has a docstring. Use Google-style format:
    ```python
    def validate_write_path(user_path: str) -> str:
        """Validate and sanitise a user-supplied file path.

        Args:
            user_path: The raw path received from the caller.

        Returns:
            A safe absolute path. Falls back to a default if traversal is detected.

        Raises:
            ValueError: If user_path is empty.
        """
    ```
20. **Inline comments** explain *why*, not *what*. Ban comments that restate the code (e.g., `# increment counter`).
21. **TODO format:** `# TODO(engineer_id): description — YYYY-MM-DD`. TODOs without a date and owner are rejected in review.

---

## 7. CraftedApp-Specific Patterns

22. **Keyword detection for docs PRs** is handled by set membership, not ad-hoc string checks:
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog", ...}
    _is_docs_pr = any(kw in title_lower for kw in _docs_keywords)
    ```
    When modifying detection logic, update the `_docs_keywords` set — do not add one-off `if` branches.
23. **ConsensusEngine prompt constants** live exclusively in `src/consensus.py`. The three canonical constants are `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM`. Never duplicate prompt text in other modules; import these constants.
24. **BuildPipeline** is the single entry point in `src/build_director.py` for orchestrating builds. All build steps are methods on `BuildPipeline`; standalone build functions outside this class are prohibited.
25. **CI workflow regeneration.** Call `ci_workflow.ensure()` after modifying any CI-related file. This auto-commits `conftest.py` and validates workflow YAML. Manual edits to generated CI files are overwritten on next ensure call.
26. **Repo-root file validation** checks filenames by basename against the known set (Rule 3). Path-based validation (e.g., checking `startswith("/")`) is not used for root-file detection.
27. **Accessibility identifiers are mandatory** on every interactive SwiftUI element before merge. CI may include a lint step that greps for `.accessibilityIdentifier(` on `Button`, `TextField`, `SecureField`, `Toggle`, and `Picker` views.