# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the CraftedAgent TRD documents and are mandatory for every contributor.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - New modules follow the same `{domain}_{role}.py` pattern (e.g., `src/path_security.py`).

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)
   - No other naming variants are permitted.

3. **Repo-root files** — the following files must always be committed at the repository root (no directory prefix): `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validation checks basename against this known set, not parent directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` so that `src/` is importable in tests. Never delete or relocate it manually.

5. **Test files** are named `test_{module}.py` and placed in `tests/` mirroring the `src/` structure.

---

## 2. Branch Naming

6. Every agent-created branch must match this exact pattern:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — lowercase alphanumeric identifier of the assigned engineer.
   - `subsystem_slug` — lowercase hyphenated subsystem name (e.g., `crafted-agent`).
   - `N` — zero-padded three-digit PR sequence number (e.g., `001`).
   - `title_slug` — lowercase hyphenated summary, max 48 characters.
   - The prefix `forge-agent` is kept intentionally for compatibility; do not rename to `crafted-agent`.

---

## 3. Class and Function Naming

7. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `PathSecurityValidator`.

8. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure_ci_workflow`.

9. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

10. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Double-underscore name-mangling is not used.

11. **Swift accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.
    - Segments are lowercase, hyphen-separated.
    - Dynamic context is appended with a hyphen: `navigator-project-row-{projectId}`, `stream-gate-yes-button-{gateId}`.
    - Reference examples:
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

## 4. Error and Exception Patterns

12. **Path validation before every write.** Any function that writes to a user-supplied or agent-supplied path must call `validate_write_path` first. No exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempt; never raises.
    ```

13. **Fail-safe defaults over exceptions** for security-sensitive helpers. `validate_write_path` returns a safe default path rather than raising, so a compromised input can never bypass the guard via an uncaught exception.

14. **Domain exceptions** must be defined per module in a dedicated `exceptions.py` or at the top of the module, inheriting from a common `CraftedAgentError` base class.

15. Never use bare `except:`. Always catch a specific exception type or, at minimum, `except Exception`.

---

## 5. Import and Module Organisation

16. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. `src/` project modules (absolute imports from `src`).
    - Blank line between each group.

17. **Absolute imports only.** Relative imports (`from . import x`) are prohibited in `src/`.

18. **No circular imports.** If module A needs a type from module B and vice versa, extract the shared type into a third module or use `TYPE_CHECKING` guards:

    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from src.build_director import BuildPipeline
    ```

---

## 6. Comment and Documentation Rules

19. **Every public class and function** must have a docstring (Google style):

    ```python
    def validate_write_path(user_path: str) -> str:
        """Sanitise and validate a write target path.

        Args:
            user_path: The raw path supplied by the caller or agent.

        Returns:
            A verified absolute path safe for writing,
            or a safe default if traversal is detected.
        """
    ```

20. **Inline comments** explain *why*, not *what*. Do not restate the code.

21. **TODO / FIXME** comments must include an engineer ID and tracking reference:
    ```python
    # TODO(engineer_id): Migrate to async path validation — see PR-012
    ```

22. **No commented-out code** in main-branch commits. Use version control history instead.

---

## 7. CraftedAgent-Specific Patterns

### 7.1 Path Security Gate

23. The `path_security` module is the single source of truth for write-path validation. Other modules must not implement their own traversal checks.

24. Unit tests for any file-writing function must include at least one traversal-attack input (e.g., `../../etc/passwd`) and assert the safe default is returned.

### 7.2 CI Workflow Integrity

25. `ci_workflow.ensure()` is the only mechanism that creates or updates `conftest.py` and CI YAML files. Manual edits to these generated files are overwritten on the next pipeline run.

26. CI YAML changes must be tested locally with `act` (or equivalent) before push when modifying `crafted-ci.yml` or `crafted-ci-macos.yml`.

### 7.3 Docs-PR Detection (Legacy Reference)

27. The keyword-list approach (`_docs_keywords` set matched against PR title) was removed in TRD v6.0. Do not reintroduce keyword-set heuristics for PR classification. Use label-based or path-based detection instead.

### 7.4 Root-File Validation

28. Any automation that commits files must validate repo-root files by **basename membership** in the known set (rule 3), not by checking whether the file's parent directory is `/`.

### 7.5 Swift / macOS Conventions

29. All SwiftUI interactive elements must carry an `accessibilityIdentifier` following rule 11 before merging.

30. macOS-specific Swift tests run exclusively in `crafted-ci-macos.yml`. Do not add Xcode build steps to `crafted-ci.yml`.

---

*