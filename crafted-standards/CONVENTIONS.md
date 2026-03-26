# CONVENTIONS.md — CraftedAgent Subsystem

---

## Code Conventions

### 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path` and all path-sanitisation helpers

2. **CI workflow files** use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or add alternative workflow files without updating both.

3. **Repo-root files** — the following files must always be committed at the repository root (no directory prefix): `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate by basename against this known set, never by parent directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or delete this file; it is regenerated on every CI run.

5. **Branch naming** follows this exact pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric, no underscores.
   - `subsystem_slug` — lowercase kebab-case (e.g., `crafted-agent`).
   - `N` — zero-padded to 3 digits.
   - `title_slug` — lowercase kebab-case, max 48 characters, ASCII only.

---

### 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedAgent`.

7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure_workflow`, `run_build`.

8. **Constants and system prompts** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal helpers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Never use double-underscore name-mangling unless truly required for inheritance conflict avoidance.

10. **Swift accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element:
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
    Every interactive SwiftUI element must have an `accessibilityIdentifier`. Omission is a review-blocking defect.

---

### 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a single project base class (e.g., `CraftedError`) and use `PascalCase` ending in `Error`:
    ```python
    class PathTraversalError(CraftedError): ...
    class BuildPipelineError(CraftedError): ...
    ```

12. **Never swallow exceptions silently.** Every `except` block must either re-raise, log at `WARNING` or above, or return a well-defined error sentinel.

13. **Path validation failures** must raise `PathTraversalError` or return a safe default path. They must never proceed with the original user-supplied path:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```

14. **Fail-fast on CI configuration errors.** If `crafted-ci.yml` or `crafted-ci-macos.yml` cannot be parsed or is missing, raise immediately — do not fall back to a default pipeline.

---

### 4. Import and Module Organisation

15. **Import order** (enforced by `isort` with the `black` profile):
    1. Standard library
    2. Third-party packages
    3. Local `src/` modules

    Separate each group with a single blank line.

16. **Absolute imports only** from `src/`:
    ```python
    from consensus import ConsensusEngine
    from build_director import BuildPipeline
    from path_security import validate_write_path
    ```
    Do not use relative imports (e.g., `from .consensus import ...`).

17. **No wildcard imports.** `from module import *` is prohibited everywhere.

18. **Guard heavy optional imports** behind `TYPE_CHECKING`:
    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from heavy_module import HeavyType
    ```

---

### 5. Comment and Documentation Rules

19. **Every public class and function** must have a docstring (Google style):
    ```python
    def validate_write_path(user_path: str) -> Path:
        """Sanitise and validate a user-supplied path before writing.

        Args:
            user_path: Raw path string from agent or user input.

        Returns:
            A resolved, safe Path inside the allowed write tree.

        Raises:
            PathTraversalError: If the path escapes the sandbox.
        """
    ```

20. **Inline comments** explain *why*, not *what*. If the code needs a *what* comment, refactor for clarity first.

21. **TODO format**: `# TODO(engineer_id): description — tracked in issue #NNN`. Bare `# TODO` without an owner and issue number is not permitted.

22. **No keyword-stuffing in PR titles or docs.** The legacy `_docs_keywords` pattern (v5.0) was removed in v6.0. Do not reintroduce keyword-list heuristics for PR classification; use structured labels instead.

---

### 6. CraftedAgent-Specific Patterns

23. **Validate paths before ANY write.** This is the single most critical security rule. Every agent code path that writes to disk must call `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    safe_path.write_text(content)
    ```
    No exceptions. No shortcuts. Reviewed in every PR.

24. **Accessibility identifiers are mandatory.** Every SwiftUI `Button`, `TextField`, `Toggle`, `NavigationLink`, or custom interactive view must set `.accessibilityIdentifier()` using the `{module}-{component}-{role}-{context?}` convention (rule 10). UI tests assert on these identifiers.

25. **System prompt constants are centralised in `src/consensus.py`.** Never inline system prompt text in agent orchestration code. Reference `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, or `UI_ADDENDUM` by import.

26. **CI workflow integrity.** Do not manually edit `conftest.py` or the generated CI files. Changes to CI configuration go through `ci_workflow.ensure()` or the `BuildPipeline` in `src/build_director.py`.

27. **Root-file validation.** Any agent operation that commits files must check whether the filename's basename matches the repo-root-only set (rule 3). If it does, the file must be written to the repo root — never nested inside a subdirectory.

28. **Branch lifecycle.** Branches matching the `forge-agent/build/...` pattern are ephemeral. They must be