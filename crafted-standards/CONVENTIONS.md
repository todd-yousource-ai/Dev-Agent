# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the CraftedAgent TRD documents. Every rule is mandatory unless explicitly marked **(recommended)**.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)

3. **Repo-root files** are validated by basename, not directory. The following must always exist at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never manually delete or relocate it.

5. **Test files** use the pattern `tests/test_{module}.py`, mirroring the source file they cover (e.g., `tests/test_consensus.py`).

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`. Do not use double underscores for name mangling unless strictly required by inheritance.

10. **Swift accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, all lowercase, hyphen-separated:
    ```
    auth-touchid-button
    auth-passcode-button
    settings-anthropic-key-field
    settings-anthropic-key-test-button
    settings-anthropic-key-reveal-button
    navigator-project-row-{projectId}
    stream-gate-card-{gateId}
    stream-gate-yes-button-{gateId}
    stream-gate-skip-button-{gateId}
    stream-gate-stop-button-{gateId}
    ```
    Every interactive SwiftUI element must have `.accessibilityIdentifier()` set using this scheme.

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** No file-write operation may proceed without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempt; never raises.
    ```

12. **Fail closed.** If `validate_write_path` detects traversal (e.g., `../`), it returns a safe default path — never `None`, never the original malicious path.

13. **Custom exceptions** (when needed) inherit from a single project base `class CraftedError(Exception)` and use `PascalCase` ending in `Error`: `PathTraversalError`, `PipelineStageError`.

14. **Never silently swallow exceptions.** Catch blocks must either re-raise, log at `WARNING`+ level, or return a documented sentinel value (as `validate_write_path` does).

---

## 4. Import and Module Organisation

15. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. `src/` project modules

    Separate each group with a blank line.

16. **Relative imports are prohibited.** Always use absolute imports rooted at `src/`:
    ```python
    from path_security import validate_write_path
    from consensus import ConsensusEngine
    ```

17. **No star imports** (`from module import *`). Every imported name must be explicit.

---

## 5. Comment and Documentation Rules

18. **Module docstring** is mandatory at the top of every `.py` file, stating purpose in one sentence.

19. **Public functions and classes** require a docstring (Google style):
    ```python
    def validate_write_path(user_path: str) -> str:
        """Sanitise a user-supplied path, returning a safe default on traversal.

        Args:
            user_path: The raw path string from external input.

        Returns:
            A validated, safe filesystem path.
        """
    ```

20. **Inline comments** explain *why*, not *what*. Do not restate the code.

21. **TODO format**: `# TODO(engineer_id): description — tracking-issue-url`

---

## 6. CraftedAgent-Specific Patterns

### 6.1 Branch Naming

22. **All agent branches** must follow this exact format (kept as `forge-agent` for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{engineer_id}` — the assigned engineer's identifier.
    - `{subsystem_slug}` — lowercase hyphenated subsystem name (e.g., `crafted-agent`).
    - `{N:03d}` — zero-padded PR sequence number (e.g., `001`).
    - `{title_slug}` — lowercase hyphenated summary (e.g., `add-path-validation`).

    Example: `forge-agent/build/eng42/crafted-agent/pr-007-add-path-validation`

### 6.2 CI Pipeline

23. `ci_workflow.ensure()` must be called before test execution to guarantee `conftest.py` exists for `src/` import resolution. Do not bypass this step.

24. The Ubuntu CI file (`crafted-ci.yml`) and the macOS Swift CI file (`crafted-ci-macos.yml`) are the only two CI entry points. Do not create additional workflow files without TRD amendment.

### 6.3 Path Security

25. **Every agent-initiated file write** must be preceded by `validate_write_path`. This applies to:
    - Generated source files
    - Configuration files
    - Temporary/scratch files
    - Any path derived from user or external input

26. Path validation is **not optional** in tests. Test helpers that write to disk must also call `validate_write_path` or use a pre-validated fixture path.

### 6.4 Docs PR Detection (Legacy, Removed)

27. The keyword-list approach for docs PR detection (`_docs_keywords` set, `_is_docs_pr` boolean) was **removed in v6.0**. Do not reintroduce keyword-set matching for PR classification. Use the classification mechanism defined in the current TRD version.

### 6.5 Swift UI Identifiers

28. Every new interactive SwiftUI view element must include an `.accessibilityIdentifier()` conforming to Rule 10 before the PR is mergeable. UI tests rely on these identifiers; omitting them breaks the test contract.

### 6.6 Repo-Root File Validation

29. Any tooling that creates or moves files must validate repo-root candidates by **basename against the known set** (Rule 3), not by checking whether the target directory is `/`. This prevents false negatives when paths are resolved differently across platforms.