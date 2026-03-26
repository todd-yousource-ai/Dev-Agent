# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the project TRDs. Every convention is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - No new top-level directories without TRD approval.

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)

3. **Repo-root files** — the following must be committed at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validation uses basename matching against this known set, not parent-directory checks.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit the auto-generated `conftest.py`; regenerate via the CI ensure step.

5. **Test files** follow the pattern `tests/test_{module}.py`, mirroring the source file they cover.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - Segments are lowercase, hyphen-separated.
    - Dynamic context is appended with a curly-brace template variable: `navigator-project-row-{projectId}`.
    - Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.
    - Reference examples:
      ```
      "auth-touchid-button"
      "settings-anthropic-key-field"
      "settings-anthropic-key-test-button"
      "stream-gate-card-{gateId}"
      "stream-gate-yes-button-{gateId}"
      ```

---

## 3. Branch Naming

11. **All agent branches** use the format (kept as `forge-agent` for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{N:03d}` is zero-padded to three digits.
    - `{title_slug}` is lowercase, hyphen-separated, no special characters.
    - Example: `forge-agent/build/eng42/crafted-agent/pr-007-add-path-validation`

---

## 4. Error and Exception Patterns

12. **Path validation before every write.** No file-write operation may proceed without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Any function that writes to disk must include this call as its first I/O-related statement. Reviewers must reject PRs that perform writes without path validation.

13. **Fail loudly on security violations.** If `validate_write_path` returns a safe default (i.e., the original path was a traversal attempt), log a warning at `WARNING` level with the original and resolved paths.

14. **Custom exceptions** inherit from a single project base: `class CraftedError(Exception)`. Subsystem exceptions follow `Crafted{Domain}Error` (e.g., `CraftedPipelineError`, `CraftedPathSecurityError`).

---

## 5. Import and Module Organisation

15. **Import order** (enforced by linter config in `pyproject.toml`):
    1. Standard library
    2. Third-party packages
    3. Project modules (`from src.…` or `from path_security import …`)
    Separate each group with a blank line.

16. **No wildcard imports.** `from module import *` is prohibited.

17. **Relative imports are prohibited** in `src/`. Always use absolute imports rooted at `src`.

18. **Keyword lists for classification** (e.g., docs-PR detection) must be defined as module-level frozen sets, not inline literals:
    ```python
    _DOCS_KEYWORDS: frozenset[str] = frozenset({
        "naming convention", "glossary", "changelog",
    })
    ```

---

## 6. Comment and Documentation Rules

19. **Module docstring** — every `.py` file starts with a one-line module docstring stating its TRD source:
    ```python
    """BuildPipeline — see TRD-3-Build-Pipeline-Crafted."""
    ```

20. **Public functions and classes** require a docstring with: one-line summary, `Args:`, `Returns:`, and `Raises:` sections (Google style).

21. **Inline comments** explain *why*, not *what*. Comments restating the code are deleted during review.

22. **TODO format**: `# TODO(engineer_id): description — TRD-N §section`

---

## 7. CraftedAgent-Specific Patterns

23. **Path-security import is non-optional.** Any module that touches the filesystem must import `path_security`. CI checks grep for unguarded `open(…, 'w')`, `pathlib.Path.write_*`, or `shutil.*` calls that lack a preceding `validate_write_path`.

24. **`ci_workflow.ensure()` is the single entry point** for CI bootstrap. It generates `conftest.py` and validates workflow file names. Do not manually create or rename CI YAML files.

25. **Root-file validation** — when the agent commits files, it must check each file's basename against the known root-file set (Rule 3). Files matching the set must have an empty directory component; files not matching must have a non-empty directory component.

26. **axIdentifier coverage** — every PR that adds or modifies a SwiftUI interactive element must include the corresponding `accessibilityIdentifier` in the diff. CI UI tests reference these identifiers; missing identifiers break the test suite.

27. **Docs-PR detection** uses keyword matching against the PR title (lowercase). The keyword set is maintained in a single `frozenset` (Rule 18). Do not scatter keyword checks across multiple files.

28. **Consensus prompts** (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`) are defined only in `src/consensus.py`. Other modules must import them; duplication is prohibited.

---

*Last updated from TRDs: TRD-1-macOS-Application-Shell-Crafted, TRD-3-Build-Pipeline-Crafted, forge_architecture_context, GitHub-Integration-Lessons-Learned, AGENTS.*