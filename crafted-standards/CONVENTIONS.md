# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - New modules follow the same pattern: `src/{domain}_{role}.py` (e.g., `src/path_security.py`).

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)
   - No other naming variants are permitted.

3. **Repo-root files** — the following files must always be committed at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validation is performed by basename against this known set, not by directory path.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or relocate this file.

5. **Test files** are named `test_{module}.py` and placed in a `tests/` directory mirroring `src/` structure.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `is_docs_pr`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element:
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
    Every interactive SwiftUI view must have an `axIdentifier`. Omitting one is a review blocker.

---

## 3. Branch Naming

11. **All agent branches** must match this exact pattern (kept as `forge-agent` for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{engineer_id}` — alphanumeric engineer identifier.
    - `{subsystem_slug}` — lowercase, hyphen-separated subsystem name (e.g., `crafted-dev-agent`).
    - `{N:03d}` — zero-padded three-digit PR sequence number.
    - `{title_slug}` — lowercase, hyphen-separated summary (max 48 chars).

    Example: `forge-agent/build/eng42/crafted-dev-agent/pr-007-add-path-validation`

---

## 4. Error and Exception Patterns

12. **Path validation before every write.** No file-system write may occur without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Any code path that skips this call is a review blocker.

13. **Fail-safe defaults.** `validate_write_path` returns a safe default path (never raises) when it detects directory traversal. Callers must not catch-and-ignore its return value; they must use the returned `safe_path`.

14. **Custom exceptions** are defined in a dedicated `src/exceptions.py` module, subclass `Exception`, and use `PascalCase` names ending in `Error` (e.g., `PathTraversalError`, `PipelineStepError`).

15. **Never use bare `except:`.** Always catch a specific exception type or, at minimum, `except Exception`.

---

## 5. Import and Module Organisation

16. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. Local `src.*` modules

    Separate each group with a single blank line.

17. **No wildcard imports.** `from module import *` is prohibited.

18. **Relative imports are prohibited** inside `src/`. Always use absolute imports: `from src.consensus import ConsensusEngine`.

19. **`conftest.py` sys-path manipulation** is the only sanctioned mechanism for making `src/` importable in tests. Do not add `sys.path` hacks in test files.

---

## 6. Comment and Documentation Rules

20. **Module docstring** — every `.py` file begins with a one-line module docstring stating its responsibility:
    ```python
    """ConsensusEngine: multi-model consensus and generation system prompts."""
    ```

21. **Public functions and classes** require a docstring with at minimum: one-line summary, `Args:`, and `Returns:` sections (Google-style).

22. **Inline comments** explain *why*, not *what*. If the code needs a *what* comment, refactor for clarity first.

23. **TODO format:** `# TODO(engineer_id): description — tracking-issue-url`

24. **No commented-out code** may be merged. Delete it; version control preserves history.

---

## 7. CraftedDevAgent-Specific Patterns

25. **Keyword-based classification is removed.** The v5.0 `_docs_keywords` / `_is_docs_pr` pattern was removed in v6.0. Do not re-introduce keyword-set heuristics for PR classification. Use structured metadata instead.

26. **`ci_workflow.ensure()` is the single entry point** for CI bootstrapping. All CI-related file generation (including `conftest.py` auto-commit) flows through this method. Do not create CI files manually.

27. **Root-file validation** must check by basename, not by directory path:
    ```python
    ROOT_FILES = {
        "README.md", "CODEOWNERS", "LICENSE", ".gitignore",
        ".editorconfig", "VERSION", "Makefile", "pyproject.toml",
    }
    assert Path(filepath).name in ROOT_FILES
    ```

28. **Agent write operations** always follow this sequence:
    1. Validate the target path (`validate_write_path`).
    2. Perform the write.
    3. Log the written path and byte count.

    Skipping any step is a review blocker.

29. **SwiftUI code generated by the agent** must include `.accessibilityIdentifier()` for every interactive element, following the naming convention in rule 10. The agent must validate generated Swift source for identifier presence before committing.

30. **PR title and branch slug must stay in sync.** The `{title_slug}` portion of the branch name (rule 11) must be derivable from the PR title by lowercasing, replacing non-alphanumeric characters with hyphens, and truncating to 48 characters.