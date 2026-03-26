# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the project TRDs and architecture documents. Every rule is mandatory unless explicitly marked *recommended*.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)

3. **Repo-root files** — the following files must always be committed at the repository root (no directory prefix). Validate by basename, not by directory:
   - `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` so that `src/` is importable in tests. Never hand-edit this file; if it drifts, delete and let the pipeline regenerate it.

5. **Test files** follow the pattern `tests/test_{module}.py` mirroring the source file they cover (e.g., `tests/test_consensus.py` for `src/consensus.py`).

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `PathSecurity`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `run_build`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Do not use double underscores for name-mangling unless there is a concrete inheritance collision.

10. **Branch names** follow this exact template (the `forge-agent` prefix is kept intentionally for compatibility — do not rename):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{N:03d}` — zero-padded to three digits.
    - `{title_slug}` — lowercase, hyphens only, no underscores.

---

## 3. Error and Exception Patterns

11. **Validate paths before ANY write operation.** Every agent-initiated write must pass through `path_security.validate_write_path`:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Never call `open(..., "w")`, `Path.write_text()`, or `shutil.copy` with a raw user-supplied path.

12. **Return safe defaults on traversal detection.** `validate_write_path` must return a safe default path (not raise) when directory traversal is detected, so the caller always receives a usable value. Log a warning at the call site when the returned path differs from the supplied path.

13. **Custom exceptions** inherit from a single project base: `class CraftedAgentError(Exception)`. Subsystem exceptions extend it (e.g., `PathTraversalError(CraftedAgentError)`).

14. **Never silently swallow exceptions.** Every `except` block must either re-raise, log at `WARNING` or above, or convert to a well-typed return value. Bare `except:` is prohibited.

---

## 4. Import and Module Organisation

15. **Import order** (enforced by `isort` with the `black` profile):
    1. Standard library
    2. Third-party packages
    3. Project modules (`from src.…` or `from path_security import …`)

16. **Relative imports are prohibited** inside `src/`. Always use absolute imports rooted at `src`:
    ```python
    from src.consensus import ConsensusEngine   # ✓
    from .consensus import ConsensusEngine       # ✗
    ```

17. **`__all__` is required** in every public module to make the API surface explicit.

---

## 5. Comment and Documentation Rules

18. **Module docstring** — every `.py` file begins with a one-line module docstring stating its responsibility, matching the TRD role:
    ```python
    """ConsensusEngine, GENERATION_SYSTEM, and SWIFT_GENERATION_SYSTEM + UI_ADDENDUM."""
    ```

19. **Public functions and classes** require a Google-style docstring with `Args:`, `Returns:`, and `Raises:` sections.

20. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

21. **TODO format**: `# TODO(engineer_id): description — refs TRD-N §section` so TODOs are traceable to a person and spec section.

---

## 6. CraftedAgent-Specific Patterns

### 6.1 Accessibility Identifiers (SwiftUI)

22. **axIdentifier format**: `{module}-{component}-{role}-{context?}`
    Set via `.accessibilityIdentifier()` on **every** interactive element.

23. **Canonical examples** (do not deviate from this pattern):
    | Identifier | Usage |
    |---|---|
    | `auth-touchid-button` | Touch ID authentication button |
    | `auth-passcode-button` | Passcode fallback button |
    | `settings-anthropic-key-field` | API key text field |
    | `settings-anthropic-key-test-button` | Key validation button |
    | `settings-anthropic-key-reveal-button` | Key reveal toggle |
    | `navigator-project-row-{projectId}` | Project list row |
    | `stream-gate-card-{gateId}` | Gate card container |
    | `stream-gate-yes-button-{gateId}` | Gate approval button |
    | `stream-gate-skip-button-{gateId}` | Gate skip button |
    | `stream-gate-stop-button-{gateId}` | Gate stop button |

24. Dynamic segments (`{projectId}`, `{gateId}`) are interpolated at runtime. Static segments are always lowercase with hyphens — no underscores, no camelCase.

### 6.2 Docs-PR Detection

25. Docs-PR classification logic was **removed in TRD v6.0**. Do not re-introduce keyword-list matching (`_docs_keywords`, `_is_docs_pr`). Classification of documentation-only PRs is handled by file-path diffstat, not title keywords.

### 6.3 CI Workflow Discipline

26. Every PR must pass both `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift) before merge.

27. Do not add CI files outside the two canonical names. If a new runner OS is needed, create a TRD amendment first.

### 6.4 Root-File Validation

28. Before committing, validate that repo-root files match the known basename set (Rule 3). Use basename comparison — never assert on an absolute directory path.

---

*Last updated from TRD-1, TRD-3, GitHub-Integration-Lessons-Learned, and forge_architecture_context.*