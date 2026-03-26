# CONVENTIONS.md — CraftedApp Subsystem

All rules below are derived from project TRDs and architecture documents. Every rule is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Python backend files** use `snake_case.py` and live under `src/`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu)
   - `crafted-ci-macos.yml` (macOS Swift)

3. **Repo-root files** must remain at the repository root with no directory prefix. Validate by basename against this set:
   - `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never delete or relocate it manually.

5. **Branch names** follow this exact pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no spaces.
   - `subsystem_slug`: lowercase, hyphen-separated (e.g., `crafted-app`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase, hyphen-separated summary (e.g., `add-auth-flow`).

---

## 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`.

7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure`.

8. **Swift types** use `PascalCase` for structs, classes, enums, and protocols.

9. **Swift properties and methods** use `camelCase`.

10. **Accessibility identifiers (axIdentifier)** follow the pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase, hyphen-separated.
    - `{context}` is optional; when present it carries a dynamic ID.
    - Set via `.accessibilityIdentifier()` on **every** interactive element.
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

11. **Validate paths before ANY file-system write.** Use the project's `path_security` module:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
    `validate_write_path` returns a safe default on directory-traversal attempts. Never bypass this call.

12. **Never construct file paths from raw user input** without passing through `validate_write_path` first.

13. **Exceptions must be specific.** Catch the narrowest exception type possible; bare `except:` and `except Exception:` at module boundaries require a logged reason and re-raise or explicit recovery.

---

## 4. Import and Module Organisation

14. **Import order** (separated by blank lines):
    1. Standard library
    2. Third-party packages
    3. Project-local (`src.*`, `path_security`, etc.)

15. **Relative imports are prohibited** in `src/` modules. Always use absolute imports rooted at `src`:
    ```python
    from src.consensus import ConsensusEngine
    ```

16. **`conftest.py` at repo root** ensures `src/` is on `sys.path` for pytest. Do not duplicate this logic in test files.

---

## 5. Comment and Documentation Rules

17. **Every Python module** starts with a single-line docstring stating its primary responsibility (as modelled in the architecture: `consensus.py` → `ConsensusEngine`, etc.).

18. **Public functions and classes** require a docstring (Google style) with `Args`, `Returns`, and `Raises` sections where applicable.

19. **Inline comments** explain *why*, not *what*. Do not restate code.

20. **TODO / FIXME comments** must include an engineer ID or issue reference:
    ```python
    # TODO(jdoe): Handle token refresh — see #142
    ```

21. **Keyword-based classification of PRs for docs** (e.g., "naming convention", "glossary", "changelog") was removed in TRD v6.0. Do not reintroduce keyword-list heuristics in PR classifiers.

---

## 6. CraftedApp-Specific Patterns

22. **`ConsensusEngine`** and its prompt constants (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`) live exclusively in `src/consensus.py`. Do not scatter prompt text across modules.

23. **`BuildPipeline`** lives exclusively in `src/build_director.py`. All build-orchestration logic enters through this class.

24. **CI workflow generation** is handled by `ci_workflow.ensure()`. Manual edits to `crafted-ci.yml` or `crafted-ci-macos.yml` will be overwritten; change the generator instead.

25. **Root-file validation**: any tooling that writes repo-root files must check the target filename against the canonical basename set (Rule 3). Use basename comparison, not directory comparison.

26. **axIdentifier coverage**: every SwiftUI view that contains an interactive control (button, text field, toggle, picker, navigation link) must set `.accessibilityIdentifier()` conforming to Rule 10. PR reviews must verify this.

27. **Path-security gate in agents**: any agent or automated code path that writes files must call `validate_write_path` (Rule 11) as the **first** operation before opening a file handle. This is a non-negotiable security invariant.

28. **Branch creation by automation** must use the `forge-agent/build/…` pattern from Rule 5. Any CI job that detects a non-conforming branch name from an automated actor must fail the pipeline.