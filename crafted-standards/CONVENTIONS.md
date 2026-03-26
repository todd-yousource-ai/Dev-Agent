# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu pipeline)
   - `crafted-ci-macos.yml` (macOS Swift pipeline)

3. **Repo-root files** — the following files **must** exist at the repository root (no subdirectory prefix). Validate by basename against this canonical set:
   - `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit or delete this file.

5. **Branch names** follow this mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric, no underscores.
   - `subsystem_slug` — lowercase kebab-case (e.g., `crafted-dev-agent`).
   - `N` — zero-padded to three digits (e.g., `001`).
   - `title_slug` — lowercase kebab-case summary, max 48 characters.

---

## 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `run_build`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

10. **Swift accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element:
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
    - All segments are lowercase kebab-case.
    - `{context}` is optional; include it when the same component appears in multiple contexts.
    - Dynamic suffixes (e.g., `{projectId}`, `{gateId}`) are appended with a hyphen.

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** No file-write operation may proceed without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal attempt
    ```
    - If the function returns a safe default, log the traversal attempt at `WARNING` level.
    - Never catch and silence the return silently; always emit a log entry.

12. **Raise domain-specific exceptions**, never bare `Exception`. Name them `<Context>Error` (e.g., `PathTraversalError`, `BuildPipelineError`).

13. **Error messages** must include the operation attempted, the offending value, and the remediation hint:
    ```python
    raise BuildPipelineError(
        f"Branch name '{branch}' does not match pattern "
        f"'forge-agent/build/{{engineer_id}}/{{subsystem_slug}}/pr-{{N:03d}}-{{title_slug}}'. "
        f"Rename the branch and retry."
    )
    ```

14. **Never swallow exceptions in agent write paths.** `except` blocks must re-raise or convert to a domain error.

---

## 4. Import and Module Organisation

15. **Import order** (enforce with `isort`, profile `black`):
    1. Standard library
    2. Third-party packages
    3. Project modules (`src.*`, `path_security`, etc.)

    Separate each group with a blank line.

16. **No wildcard imports.** Always `from module import Name` or `import module`.

17. **`path_security` is a mandatory import** in any module that performs filesystem writes. A linter check or code-review gate must flag write calls (`open(..., 'w')`, `pathlib.Path.write_text`, `shutil.copy`, etc.) that lack a preceding `validate_write_path` call in the same scope.

18. **`conftest.py` sys-path manipulation** is the only sanctioned way to make `src/` importable in tests. Do not add `sys.path` hacks in test files.

---

## 5. Comment and Documentation Rules

19. **Module docstring** required at the top of every `src/*.py` file. First line: one-sentence purpose. Second paragraph (optional): key classes/constants exported.
    ```python
    """ConsensusEngine and generation-system prompt constants.

    Exports: ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM, UI_ADDENDUM.
    """
    ```

20. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

21. **TODO/FIXME format**: `# TODO(engineer_id): description — tracking-issue-url`

22. **Keyword-based classification of PRs** (e.g., docs vs. code) was removed in v6.0. Do **not** reintroduce keyword-list heuristics (`_docs_keywords`-style patterns). PR classification is now handled upstream.

---

## 6. CraftedDevAgent-Specific Patterns

23. **Agent write guard.** Every CraftedDevAgent code path that writes to disk must:
    1. Call `validate_write_path(target)`.
    2. Receive the sanitised path.
    3. Use **only** the sanitised path for the write.
    ```python
    from path_security import validate_write_path

    def agent_write(target: str, content: str) -> None:
        safe = validate_write_path(target)
        safe.write_text(content, encoding="utf-8")
    ```

24. **Repo-root file validation.** Before committing, agents must check that root-only files are not nested:
    ```python
    ROOT_ONLY = {
        "README.md", "CODEOWNERS", "LICENSE", ".gitignore",
        ".editorconfig", "VERSION", "Makefile", "pyproject.toml",
    }

    def validate_root_files(staged: list[str]) -> None:
        for path in staged:
            basename = os.path.basename(path)
            if basename in ROOT_ONLY and os.path.dirname(path) != "":
                raise PathError(f"'{basename}' must live at repo root, found at '{path}'")
    ```

25. **Branch creation.** Agents must programmatically construct branch names using the template in rule 5. Hard-coded branch names are prohibited.

26. **CI workflow integrity.** Agents must not modify `crafted-ci.yml` or `crafted-ci-macos.yml` unless the change is explicitly requested and reviewed. `conftest.py` regeneration is handled exclusively by `ci_workflow.ensure()`.

27. **Accessibility identifiers are mandatory.** Every SwiftUI interactive element generated or modified by the agent