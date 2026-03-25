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

3. **Repo-root files** — the following files must always be committed at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validate by basename against this known set, never by directory path.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never commit a hand-written `conftest.py` that conflicts with this.

5. **Test files** follow pytest discovery: `tests/test_{module}.py`, mirroring the source module name.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `run_build`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal helpers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - Every interactive element must have `.accessibilityIdentifier()` set.
    - Segments are lowercase, hyphen-delimited.
    - Dynamic context is appended with a curly-brace template variable in documentation but rendered literally at runtime.
    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

---

## 3. Branch Naming

11. **All agent branches** must use the forge-agent prefix (kept for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{N:03d}` — zero-padded three-digit PR sequence number.
    - `{title_slug}` — lowercase, hyphen-delimited summary (max 48 chars).
    - Example: `forge-agent/build/eng-042/crafted-dev-agent/pr-007-fix-path-validation`

---

## 4. Error and Exception Patterns

12. **Path validation before every write.** No file-system write may occur without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    If the path fails validation, the function returns a safe default — never raise and silently continue writing to the original path.

13. **Custom exceptions** are defined per module in a `_errors` section or a dedicated `src/errors.py`. Name them `{Domain}Error` (e.g., `PathTraversalError`, `BuildPipelineError`).

14. **Never catch bare `Exception`** except at top-level orchestration boundaries. Always catch the narrowest type.

---

## 5. Import and Module Organisation

15. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. Local `src/` modules

16. **Absolute imports only** from `src/`:
    ```python
    from consensus import ConsensusEngine       # YES
    from .consensus import ConsensusEngine       # NO
    ```

17. **No star imports** (`from module import *` is forbidden).

18. **Keyword-list constants** that were used in v5.0-style detection (e.g., `_docs_keywords`) are removed as of v6.0. Do not reintroduce keyword-set heuristics for PR classification; use the current classification mechanism instead.

---

## 6. Comment and Documentation Rules

19. **Module docstring** — every `src/*.py` file starts with a one-line module docstring stating its primary export:
    ```python
    """ConsensusEngine and generation-system prompt constants."""
    ```

20. **Public functions and classes** require a docstring (Google style):
    ```python
    def validate_write_path(raw: str) -> Path:
        """Sanitise and validate a write-target path.

        Args:
            raw: User-supplied or agent-supplied file path.

        Returns:
            A resolved Path guaranteed to be within the allowed directory tree.
        """
    ```

21. **Inline comments** explain *why*, not *what*. Code should be self-documenting for the *what*.

22. **TODO/FIXME** comments must include an engineer ID or issue number:
    ```python
    # TODO(eng-042): Replace placeholder timeout with config value
    ```

---

## 7. CraftedDevAgent-Specific Patterns

23. **Agent write-path security is non-negotiable.** Every code path that writes to disk — file creation, file overwrite, directory creation — must pass through `validate_write_path`. This applies to generated code, config files, CI artifacts, and temporary files.

24. **Root-file basename validation.** When the agent creates or modifies repo-root files (rule 3), validate the target filename against the known basename set. Reject any path that resolves outside the repo root or does not match the set.

25. **CI workflow generation.** The agent must produce exactly two CI files (`crafted-ci.yml`, `crafted-ci-macos.yml`). Any additional workflow file requires explicit approval in the PR description.

26. **Accessibility identifiers in generated SwiftUI code.** When the agent generates or modifies SwiftUI views, every interactive element (`Button`, `TextField`, `Toggle`, `SecureField`, navigation rows, gate cards) must include an `.accessibilityIdentifier()` conforming to rule 10.

27. **Branch creation.** The agent must format branch names per rule 11 before pushing. A pre-push check must reject branches that do not match the `forge-agent/build/…` pattern.

28. **Prompt constants locality.** `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` live exclusively in `src/consensus.py`. Other modules import them — never duplicate the strings.

29. **No deprecated keyword heuristics.** Per rule 18, the agent must not reintroduce `_docs_keywords`-style sets for PR title classification. If classification logic is needed, use the mechanism defined in the current pipeline version (v6.0+).

30. **Test coverage for path security.** Every PR that touches file-write logic must include or update a test in `tests/test_path_security.py` that exercises both valid paths and traversal attempts.