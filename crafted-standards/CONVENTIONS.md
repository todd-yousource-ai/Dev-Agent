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

3. **Repo-root files** — the following files must exist at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validate these by basename against the known set, never by directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or remove it.

5. **Test files** follow `tests/test_{module_name}.py` mirroring the source module they cover.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path()`, `ensure()`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.
    - Use lowercase kebab-case.
    - Parameterised identifiers append the dynamic ID: `"navigator-project-row-{projectId}"`, `"stream-gate-yes-button-{gateId}"`.
    - Examples:
      ```
      "auth-touchid-button"
      "auth-passcode-button"
      "settings-anthropic-key-field"
      "settings-anthropic-key-test-button"
      "settings-anthropic-key-reveal-button"
      "stream-gate-card-{gateId}"
      "stream-gate-skip-button-{gateId}"
      "stream-gate-stop-button-{gateId}"
      ```

---

## 3. Error and Exception Patterns

11. **Validate paths before ANY write.** Every agent write operation must call `validate_write_path()` from `path_security` before touching the filesystem:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal attempt
    ```
    Never pass a user-supplied path directly to `open()`, `shutil`, or `pathlib.write_*`.

12. **Fail loud, fail early.** If `validate_write_path` returns a safe default (i.e., the original path was unsafe), log a warning at `WARNING` level with the original and resolved paths.

13. **Custom exceptions** inherit from a single project base class (e.g., `CraftedError`) and are named `{Domain}Error` — `PathTraversalError`, `PipelineError`.

14. **Never bare `except`.** Always catch a specific exception type or, at minimum, `Exception`.

---

## 4. Import and Module Organisation

15. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. Project-local (`src.*`)
    Each group separated by a blank line.

16. **Absolute imports only.** Use `from src.consensus import ConsensusEngine`, never relative `from .consensus import …`.

17. **No wildcard imports.** `from module import *` is prohibited.

18. **Lazy heavy imports** — imports that pull large dependencies (e.g., ML frameworks) go inside the function that needs them, with a comment: `# lazy: heavy dependency`.

---

## 5. Comment and Documentation Rules

19. **Module docstring** — every `.py` file starts with a one-line module docstring stating its responsibility.

20. **Public functions and classes** require a docstring (Google style):
    ```python
    def validate_write_path(raw_path: str) -> Path:
        """Sanitise and validate a user-supplied path for writing.

        Args:
            raw_path: The unvalidated path string from the caller.

        Returns:
            A resolved, safe Path. Falls back to a safe default on traversal.

        Raises:
            PathTraversalError: When the path escapes the workspace root.
        """
    ```

21. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

22. **TODO format:** `# TODO(engineer_id): description — TICKET-NNN` (must reference a ticket or PR number).

---

## 6. CraftedDevAgent-Specific Patterns

### 6.1 Branch Naming

23. **All agent branches** must follow exactly:
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id` — the ID of the assigned engineer.
    - `subsystem_slug` — lowercase kebab-case subsystem name (e.g., `crafted-dev-agent`).
    - `N` — zero-padded to three digits (`001`, `012`).
    - `title_slug` — lowercase kebab-case summary, max 48 characters.
    - The prefix `forge-agent` is mandatory and kept for compatibility; do not rename to `crafted-agent`.

### 6.2 Docs-PR Detection (Removed Keyword Approach)

24. Keyword-based docs-PR detection (`_docs_keywords` set with title matching) was **removed in v6.0**. Do not reintroduce keyword heuristics for classifying documentation PRs. Use label-based or path-based detection instead.

### 6.3 Path Security Gate

25. Every code path that writes to disk — file creation, file update, directory creation — must pass through the `path_security.validate_write_path` gate. This is non-negotiable and applies to agent-generated code, CI artefacts, and temporary files.

### 6.4 CI Workflow Integrity

26. Do not rename `crafted-ci.yml` or `crafted-ci-macos.yml`. Other tooling and status checks depend on these exact filenames.

27. The `ci_workflow.ensure()` function is the single owner of `conftest.py` generation. Manual edits to `conftest.py` will be overwritten on the next pipeline run.

### 6.5 Repo-Root File Validation

28. When the agent creates or moves files, validate repo-root files by **basename** against the known set (`README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`). Never validate by checking whether the parent directory is `/`.

### 6.6 Accessibility Identifiers in Swift UI Code

29. Every PR that adds or modifies a SwiftUI interactive element must include an `.accessibilityIdentifier()` conforming to rule 10. CI may enforce this via a grep-based lint step.

30. Identifiers must be unique within their view hierarchy. Parameterised identifiers (containing `{id}`) must use the model's stable identifier, not an array index.