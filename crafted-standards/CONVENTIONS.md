# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python modules** use `snake_case` with no abbreviations: `build_director.py`, `consensus.py`, `path_security.py`, `ci_workflow.py`.

2. **CI workflow files** are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming variants are permitted.

3. **Repo-root files** — the following files must live at the repository root with no directory prefix: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate membership by basename against a known set, never by parent directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` specifically to enable `src/` imports. Never hand-write or relocate this file; treat it as a generated artifact.

5. **Branch names** must follow this exact pattern (the `forge-agent` prefix is kept intentionally for compatibility — do not change it):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric + hyphens.
   - `subsystem_slug`: lowercase, hyphen-delimited (e.g., `crafted-dev-agent`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase, hyphen-delimited, max 48 characters.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path()`, `ensure()`.

8. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private module-level variables** are prefixed with a single underscore and use `snake_case`: `_docs_keywords`, `_is_docs_pr`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    - All segments are lowercase, hyphen-delimited.
    - The optional `{context}` segment is appended with a hyphen when a dynamic discriminator (e.g., an ID) is needed.
    - Examples:
      ```
      "auth-touchid-button"
      "settings-anthropic-key-field"
      "settings-anthropic-key-test-button"
      "navigator-project-row-{projectId}"
      "stream-gate-card-{gateId}"
      "stream-gate-yes-button-{gateId}"
      ```
    - Every interactive SwiftUI element must have `.accessibilityIdentifier()` set using this convention. No element ships without one.

---

## 3. Error and Exception Patterns

11. **Path traversal defence**: validate every user-supplied path before any write operation. Always use the `path_security` module:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt — never raises to the caller.
    ```
    No file-write code may skip this call. If `validate_write_path` is unreachable, the write must not proceed.

12. **Fail-closed on unknown paths**: if a path cannot be validated (module import failure, unexpected return value), treat it as a traversal attempt and abort the write.

13. **Exception classes** are defined per module and inherit from a single project-level base (e.g., `CraftedError`). Never raise bare `Exception` or `RuntimeError`.

---

## 4. Import and Module Organisation

14. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. Project-internal (`src.*`)
    — separated by a single blank line between each group.

15. **Canonical module locations**:
    | Module | Canonical path | Exports |
    |---|---|---|
    | `consensus` | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
    | `build_director` | `src/build_director.py` | `BuildPipeline` |
    | `path_security` | `src/path_security.py` | `validate_write_path` |
    | `ci_workflow` | `src/ci_workflow.py` | `ensure()` |

16. **No wildcard imports** (`from module import *`) anywhere in production code.

17. **Relative imports are prohibited** in the `src/` package. Always use absolute imports from `src`.

---

## 5. Comment and Documentation Rules

18. **Every public class and function** must have a docstring. Use imperative mood for the first line (`Validate the write path.`, not `Validates the write path.`).

19. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

20. **Keyword-based heuristics** (e.g., detecting docs PRs by title) must document the keyword list inline with the matching logic. When a heuristic is removed, delete both the list and the matching code in the same commit — do not leave orphaned constants.

21. **TRD references**: when a block of code implements a specific TRD requirement, annotate it with a comment of the form:
    ```python
    # TRD-3 §4.2 — CI workflow must auto-commit conftest.py
    ```

---

## 6. CraftedDevAgent-Specific Patterns

22. **Path validation is non-negotiable**: no agent code path may write to disk without first calling `validate_write_path`. This applies to generated code, config files, logs, and temporary artifacts.

23. **Branch creation**: agents must programmatically construct branch names using the pattern in rule 5. Hard-coded branch names are forbidden.

24. **Root-file guard**: before committing, agents must check that any file whose basename matches the root-file set (rule 3) is placed at the repo root. A file named `README.md` nested inside a subdirectory is a build error.

25. **CI workflow idempotency**: `ci_workflow.ensure()` must be safe to call multiple times without duplicating `conftest.py` or corrupting workflow YAML. All ensure functions must be idempotent.

26. **Accessibility identifier completeness**: every SwiftUI PR must include a check (automated or in review checklist) that all new interactive elements have an `accessibilityIdentifier` conforming to rule 10. Missing identifiers block merge.

27. **Consensus prompts are constants**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` are defined as module-level constants in `src/consensus.py`. They are never constructed dynamically at call sites.

28. **No deprecated heuristics in new code**: keyword-list-based detection patterns (e.g., `_docs_keywords` from TRD-3 v5.0) were removed in v6.0. Do not reintroduce keyword-set heuristics for PR classification. Use the current mechanism documented in the active TRD version.