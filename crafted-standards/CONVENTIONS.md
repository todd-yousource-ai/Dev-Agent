# CONVENTIONS.md — CraftedApp Subsystem

---

## Code Conventions

### 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` naming.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path` and all path-sanitisation logic

2. **CI workflow files** use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or add variant copies.

3. **Repo-root files** — the following files must always be committed at the repository root with no directory prefix: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate by basename, not by directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to guarantee `src/` is importable in tests. Never hand-edit the generated `conftest.py`; regenerate it through the CI helper instead.

5. **Branch names** must follow this exact pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no dots or underscores.
   - `subsystem_slug`: lowercase hyphenated (e.g., `crafted-app`).
   - `N`: zero-padded to three digits (e.g., `001`).
   - `title_slug`: lowercase hyphenated summary, max 48 characters.

---

### 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `PathSecurityError`.

7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure_ci_workflow`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`. Do not use double underscores for name-mangling unless strictly necessary.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element:
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
    - `module`: top-level feature area (`auth`, `settings`, `navigator`, `stream`).
    - `component`: specific UI element group (`touchid`, `anthropic-key`, `project`, `gate`).
    - `role`: semantic role (`button`, `field`, `row`, `card`, `label`).
    - `context`: optional dynamic suffix, always a runtime id wrapped in braces in source (e.g., `\(gateId)`).

---

### 3. Error and Exception Patterns

11. **All custom exceptions** inherit from a single project base class (e.g., `CraftedError`) and use `PascalCase` ending in `Error`:
    ```python
    class CraftedError(Exception): ...
    class PathTraversalError(CraftedError): ...
    class PipelineStageError(CraftedError): ...
    ```

12. **Never catch bare `Exception`** in library code. Catch the narrowest relevant type and re-raise or wrap in a `CraftedError` subclass with context.

13. **Path validation errors must be raised, never silently swallowed.** `validate_write_path` returns a safe default on traversal detection, but the caller must log the incident at `WARNING` or higher.

---

### 4. Import and Module Organisation

14. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. `src.*` project modules

    Separate each group with a single blank line.

15. **Absolute imports only** from `src` package:
    ```python
    from src.consensus import ConsensusEngine
    from src.path_security import validate_write_path
    ```
    Do not use relative imports (e.g., `from .consensus import ...`).

16. **No wildcard imports** (`from module import *`) anywhere in production code.

---

### 5. Comment and Documentation Rules

17. **Every public class and function** must have a docstring (Google style):
    ```python
    def validate_write_path(user_supplied_path: str) -> str:
        """Sanitise and validate a user-supplied path before writing.

        Args:
            user_supplied_path: Raw path string from external input.

        Returns:
            A canonicalised safe path. Falls back to a project-local
            default if traversal is detected.

        Raises:
            PathTraversalError: When traversal is detected and logging
                the incident.
        """
    ```

18. **Inline comments** explain *why*, not *what*. Prohibit comments that merely restate the code.

19. **TODO / FIXME** comments must include an engineer id and a tracking reference:
    ```python
    # TODO(jsmith): Remove legacy keyword matching after v7.0 — CRAFT-1042
    ```

20. **Removed or deprecated features** must be annotated with the version in which removal occurred:
    ```python
    # Removed in v6.0 — keyword-based docs-PR detection replaced by label matching.
    ```

---

### 6. CraftedApp-Specific Patterns

21. **Path validation before every write.** Any code path that writes to disk must call `validate_write_path` first:
    ```python
    from src.path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    No exceptions. This applies to agent-generated code, CI scripts, and manual tooling.

22. **CI workflow bootstrap.** Always invoke `ci_workflow.ensure()` at pipeline start. This guarantees `conftest.py` exists for `src/` import resolution. Do not manually create or edit `conftest.py`.

23. **Docs-PR detection** relies solely on GitHub labels and path-based file matching (post-v6.0). Do not reintroduce keyword-list heuristics (`_docs_keywords` was removed in v6.0).

24. **Root-file validation.** When committing repo-root files, validate the file's basename against the known set (`README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`). Reject any attempt to place these files inside a subdirectory.

25. **SwiftUI views must set `.accessibilityIdentifier()`** on every interactive element (buttons, text fields, toggles, rows, cards) following the naming convention in rule 10. Omitting an identifier on an interactive element is a review-blocking issue.

26. **Consensus prompts** (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`) are authoritative constants defined only in `src/consensus.py`. Other modules must import them — never duplicate the prompt text.

27. **Branch protection.** Merges to `main` require a passing `crafted-ci.yml` (