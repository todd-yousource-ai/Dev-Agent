# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - New modules follow the same pattern: `src/{domain}_{responsibility}.py`.

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` — Ubuntu pipeline.
   - `crafted-ci-macos.yml` — macOS Swift pipeline.
   - No other naming variants are permitted.

3. **Repo-root files** — the following files must always be committed at the repository root (no directory prefix): `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validation checks basename, not directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` so that `src/` is importable in tests. Never hand-edit or relocate this file.

5. **Test files** follow `tests/test_{module}.py`, mirroring the source module they cover.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `run_build`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Double underscores are reserved for Python name-mangling and must not be used for simple privacy.

10. **axIdentifier strings** (SwiftUI accessibility identifiers) follow the pattern `{module}-{component}-{role}-{context?}`:
    - Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.
    - Examples:
      ```
      "auth-touchid-button"
      "settings-anthropic-key-field"
      "navigator-project-row-{projectId}"
      "stream-gate-yes-button-{gateId}"
      ```
    - Use lowercase, hyphen-separated segments. Dynamic suffixes are appended after a final hyphen.

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** Any agent code that writes to disk must call `validate_write_path` first. No exceptions.
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal attempt
    ```

12. **Fail loudly, log context.** Exceptions must include the operation name and the offending input. Never silently swallow errors:
    ```python
    raise ValueError(f"validate_write_path: traversal detected in '{user_supplied_path}'")
    ```

13. **Custom exceptions** inherit from a single project base (`CraftedError` or equivalent) and are defined in the module that owns the domain logic, not in a catch-all `exceptions.py`.

---

## 4. Import and Module Organisation

14. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. `src/` project modules

    Separate each group with a blank line.

15. **Absolute imports only** from `src/`:
    ```python
    from src.consensus import ConsensusEngine
    ```
    Relative imports (`from .consensus import ...`) are prohibited.

16. **No wildcard imports.** `from module import *` is never permitted.

17. **`path_security` must be imported directly** — do not alias, wrap, or re-export `validate_write_path`.

---

## 5. Comment and Documentation Rules

18. **Module docstring** required at the top of every `.py` file. One sentence stating purpose.

19. **Public functions and classes** require a docstring (Google-style):
    ```python
    def validate_write_path(user_path: str) -> str:
        """Sanitise and validate a user-supplied path before writing.

        Args:
            user_path: The raw path string from the caller.

        Returns:
            A safe absolute path. Falls back to a default on traversal.

        Raises:
            ValueError: If the path cannot be resolved at all.
        """
    ```

20. **Inline comments** explain *why*, not *what*. Comments restating the code are deleted during review.

21. **TODO format:** `# TODO(engineer_id): description — YYYY-MM-DD`. Orphan TODOs without an owner are rejected in review.

---

## 6. CraftedDevAgent-Specific Patterns

### 6.1 Branch Naming

22. **Mandatory format:**
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id` — individual contributor identifier (lowercase, no spaces).
    - `subsystem_slug` — e.g., `crafted-dev-agent`, `build-pipeline`.
    - `N` — zero-padded three-digit PR sequence number.
    - `title_slug` — lowercase-hyphenated summary.
    - The prefix `forge-agent` is retained for tooling compatibility; do not rename to `crafted-agent`.

### 6.2 Path Security Gate

23. Every file-write code path in the agent must pass through the path-security gate:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    Pull requests that write files without this call are blocked.

### 6.3 Docs-PR Detection (Deprecated Keyword Approach)

24. The v5.0 keyword-set approach (`_docs_keywords` with `any(kw in title_lower ...)`) was **removed in v6.0**. Do not reintroduce keyword-list matching for docs-PR classification. Use the current detection mechanism defined in the active build pipeline.

### 6.4 CI Workflow Guarantees

25. `ci_workflow.ensure()` is the single entry point for CI setup. It auto-generates `conftest.py` and validates workflow file presence. Do not manually create or modify CI artifacts that `ensure()` manages.

26. Both `crafted-ci.yml` and `crafted-ci-macos.yml` must pass before a PR is merge-eligible. One failing platform blocks the merge.

### 6.5 Root-File Validation

27. When the agent commits files, it must validate that any file whose basename matches the root-required set (`README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`) is placed at the repo root. The check uses basename matching, not directory-prefix matching.

### 6.6 SwiftUI Accessibility Contract

28. Every interactive SwiftUI view committed by the agent must include an `.accessibilityIdentifier()` using the naming convention from rule 10. UI PRs missing identifiers are rejected during review.