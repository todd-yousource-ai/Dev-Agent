# CONVENTIONS.md — CraftedApp Subsystem

---

## Code Conventions

### 1. File and Directory Naming

1. **Python backend files** use `snake_case.py` and live under `src/`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)

3. **Repo-root files** — the following must live at repository root with no directory prefix: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate membership by basename against this known set, never by parent directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or delete this file.

5. **Branch naming** follows this mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric identifier of the authoring engineer.
   - `subsystem_slug` — lowercase hyphenated subsystem name (e.g., `crafted-app`).
   - `N` — zero-padded to three digits (e.g., `001`, `042`).
   - `title_slug` — lowercase, hyphen-separated summary (e.g., `add-auth-flow`).

---

### 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`.

7. **Python functions and variables** use `snake_case`: `validate_write_path`, `safe_path`.

8. **Swift types** use `PascalCase`; Swift properties and methods use `camelCase`, per standard Swift API Design Guidelines.

9. **Accessibility identifiers** (set via `.accessibilityIdentifier()` on every interactive SwiftUI element) follow the pattern:
   ```
   {module}-{component}-{role}-{context?}
   ```
   - All segments are lowercase, hyphen-separated.
   - `context` is optional; when present it is typically a dynamic ID.
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

10. **Constants** in Python use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

---

### 3. Error and Exception Patterns

11. **Path validation before every write.** Import and call `validate_write_path` before any filesystem write that involves a user-supplied or externally-derived path:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempt; never raises.
    ```
    No write to disk may proceed with an unvalidated path.

12. **Fail closed.** If `validate_write_path` detects traversal (e.g., `../`), it returns a safe default path — it does not raise an exception. Callers must use the returned value, never the original input.

13. **Custom exceptions** (when needed) inherit from a single project base exception class and use `PascalCase` names ending in `Error` (e.g., `PipelineStageError`).

---

### 4. Import and Module Organisation

14. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. Project modules (`from src.…` or relative)

    Separate each group with a single blank line.

15. **No wildcard imports.** Always import specific names:
    ```python
    from path_security import validate_write_path   # ✓
    from path_security import *                      # ✗
    ```

16. **`src/` is the Python package root.** All project imports resolve from `src/`. The auto-generated `conftest.py` ensures this for the test suite.

---

### 5. Comment and Documentation Rules

17. **Every public class and function** has a docstring (Google style for Python, `///` doc comments for Swift).

18. **Inline comments** explain *why*, not *what*. Do not restate the code.

19. **TODO format:** `# TODO(engineer_id): description — YYYY-MM-DD`. No anonymous TODOs.

20. **Keyword-driven doc detection is removed** (deprecated in TRD-3 v6.0). Do not rely on title keyword lists (`_docs_keywords`) for classifying documentation PRs.

---

### 6. CraftedApp-Specific Patterns

21. **axIdentifier coverage.** Every interactive SwiftUI element (buttons, text fields, toggles, rows) must have `.accessibilityIdentifier()` set using the naming convention in rule 9. UI tests locate elements exclusively by these identifiers.

22. **Dual-CI matrix.** Every PR must pass both `crafted-ci.yml` (Ubuntu, Python tests) and `crafted-ci-macos.yml` (macOS, Swift build + tests). Do not merge with either workflow failing.

23. **ConsensusEngine is the single generation entry point.** All prompt-based generation flows route through `ConsensusEngine` in `src/consensus.py`. Direct model calls outside this class are prohibited.

24. **Generation system prompts** are stored as module-level constants in `src/consensus.py`:
    - `GENERATION_SYSTEM` — general generation.
    - `SWIFT_GENERATION_SYSTEM` — Swift code generation.
    - `UI_ADDENDUM` — appended for UI-related generation tasks.

    Never inline system prompt strings at call sites.

25. **Repo-root file validation.** Any agent or pipeline step that writes repo-root files must validate the target filename against the known basename set (rule 3) before committing. Reject or warn on unknown root-level files.

26. **Path security is non-negotiable.** Every agent, script, or pipeline stage that writes to the filesystem must import and call `validate_write_path` (rule 11). Code reviews must verify this on every PR that introduces or modifies file-write logic.