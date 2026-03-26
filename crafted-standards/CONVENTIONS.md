# CONVENTIONS.md — CraftedApp Subsystem

---

## Code Conventions

### 1. File and Directory Naming

1. **Python files** use `snake_case.py` exclusively. No hyphens, no camelCase.
   - `src/consensus.py`, `src/build_director.py`, `src/path_security.py`

2. **CI workflow files** are named with the `crafted-` prefix:
   - `crafted-ci.yml` — Ubuntu pipeline.
   - `crafted-ci-macos.yml` — macOS Swift pipeline.

3. **Repo-root files** must live at the repository root with no directory prefix. Validate by basename against this exact set:
   - `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`

4. **Branch names** follow this mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `{N:03d}` is zero-padded to three digits.
   - `{title_slug}` is lowercase, hyphen-separated, no underscores.
   - Example: `forge-agent/build/e42/crafted-app/pr-007-add-gate-ui`

5. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or delete this file.

---

### 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`.

7. **Python functions and methods** use `snake_case`: `validate_write_path()`, `ensure()`.

8. **Python module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Swift types** follow standard Swift `PascalCase` for types and `camelCase` for properties and methods.

10. **Accessibility identifiers** (axIdentifier) follow a strict hyphenated pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase, separated by hyphens.
    - The optional `{context}` segment uses a dynamic ID appended after a final hyphen.
    - Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.
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

### 3. Error and Exception Patterns

11. **Path validation before every write.** Agents and backend code must call `validate_write_path()` before any filesystem write. Never write to a user-supplied path directly.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempts.
    ```

12. **Fail loudly on traversal.** If `validate_write_path` returns a safe default (meaning the original path was unsafe), log the incident at `WARNING` level with the original path value.

13. **No bare `except`.** Always catch specific exception types. Never write `except:` or `except Exception:` without re-raising or explicit justification in a comment.

14. **Error messages** must include the operation attempted, the resource involved, and the failing condition:
    ```python
    raise ValueError(f"Cannot write to '{path}': directory traversal detected")
    ```

---

### 4. Import and Module Organisation

15. **Import order** (enforced top-to-bottom, separated by blank lines):
    1. Standard library imports.
    2. Third-party imports.
    3. Local `src/` imports.

16. **Canonical module locations:**
    | Symbol | Module |
    |---|---|
    | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` | `src/consensus.py` |
    | `BuildPipeline` | `src/build_director.py` |
    | `validate_write_path` | `src/path_security.py` (or `path_security`) |

17. **No wildcard imports.** Never use `from module import *`.

18. **No circular imports.** If module A imports from module B, module B must not import from module A. Extract shared symbols into a third module if needed.

---

### 5. Comment and Documentation Rules

19. **Every Python module** starts with a single-line docstring stating its purpose and primary exports:
    ```python
    """ConsensusEngine and generation-system prompt constants."""
    ```

20. **Every public function and class** has a docstring. Use imperative mood for the first line:
    ```python
    def validate_write_path(path: str) -> str:
        """Validate and sanitize a filesystem path against directory traversal."""
    ```

21. **Inline comments** explain *why*, not *what*. Do not restate the code.

22. **No keyword-list detection in PR titles.** The v5.0 `_docs_keywords` pattern was removed in v6.0. Do not reintroduce keyword-set matching for classifying PRs. Use explicit labels or path-based detection instead.

---

### 6. CraftedApp-Specific Patterns

23. **axIdentifier coverage is mandatory.** Every SwiftUI `Button`, `TextField`, `SecureField`, `Toggle`, and custom interactive control must carry `.accessibilityIdentifier()` matching the pattern in rule 10. UI reviews must verify this.

24. **Gate-card identifiers** embed the gate ID:
    ```swift
    .accessibilityIdentifier("stream-gate-card-\(gate.id)")
    .accessibilityIdentifier("stream-gate-yes-button-\(gate.id)")
    .accessibilityIdentifier("stream-gate-skip-button-\(gate.id)")
    .accessibilityIdentifier("stream-gate-stop-button-\(gate.id)")
    ```

25. **Dual-CI is required.** Every PR that touches Swift code must pass both `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Python-only PRs require at minimum `crafted-ci.yml`.

26. **Root-file validation.** Any automation that writes repo-root files must validate the target filename against the allowed basename set (rule 3) before committing. Reject unknown filenames.

27. **Prompt constants are append-only.** `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` in `src/consensus.py` must not be shortened or have content removed without an explicit TRD revision. New instructions are appended.

28. **`conftest.py` is machine-managed.** Do not add custom fixtures or test configuration to the auto-generated `conftest.py`. Place project-specific fixtures in `tests/fixtures/` or a separate `tests/conftest_custom.py` that the auto-generated file imports.