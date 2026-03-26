# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`

2. **CI workflow files** use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is accepted.

3. **Repo-root files** — the following files must live at the repository root with no directory prefix: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate these by basename against the known set, never by directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` so that `src/` is importable in tests. Do not create or move it manually.

5. **Branch names** follow the mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric, no underscores.
   - `subsystem_slug` — lowercase kebab-case.
   - `N` — zero-padded to 3 digits.
   - `title_slug` — lowercase kebab-case summary of the PR purpose.

---

## 2. Class and Function Naming

6. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `is_docs_pr`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal symbols** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.

10. **SwiftUI accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    ```
    Every interactive SwiftUI element must have `.accessibilityIdentifier()` set using this convention.

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** Never write to a user-supplied path without validation:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    This is non-negotiable. Any code that opens a file for writing, creates a directory, or moves/copies a file must call `validate_write_path` first.

12. **Fail loudly on traversal.** `validate_write_path` returns a safe default when it detects path traversal (e.g., `../`). Log a warning at minimum when the returned path differs from the supplied path. Never silently succeed with the original unsafe path.

13. **Custom exceptions** inherit from a project-level base exception class and use `PascalCase` ending in `Error`: `PathTraversalError`, `PipelineStageError`.

---

## 4. Import and Module Organisation

14. **Import order** (enforced by linter):
    1. Standard library
    2. Third-party packages
    3. Project imports (`from src.consensus import …`)
    — Separated by a single blank line between each group.

15. **Absolute imports only.** Use `from src.build_director import BuildPipeline`, not relative imports.

16. **No wildcard imports.** `from module import *` is forbidden.

17. **Guard heavy imports.** If a module is only needed in a single branch (e.g., macOS-only Swift tooling), import it inside the function or behind a conditional.

---

## 5. Comment and Documentation Rules

18. **Module docstring** is mandatory on every `.py` file. First line states purpose; second paragraph (if needed) lists key classes/constants.

19. **Public function/method docstring** uses imperative mood, states what the function does, its parameters, return value, and any exceptions raised.

20. **Inline comments** explain *why*, not *what*. Do not restate the code.

21. **TODO format:** `# TODO(engineer_id): description — tracking-issue-URL`

22. **Keyword lists for doc classification** (such as the former `_docs_keywords`) must not be hard-coded in pipeline logic. If classification is needed, externalise it into configuration or derive it from PR labels/paths.

---

## 6. CraftedDevAgent-Specific Patterns

23. **Agent write operations** — every agent code path that writes to disk must:
    1. Call `validate_write_path` (rule 11).
    2. Write to a temporary location first, then atomically move to the target.
    3. Never write outside the current repository work tree.

24. **CI workflow generation** — use `ci_workflow.ensure()` as the single entry point. Do not manually author or edit `crafted-ci.yml` / `crafted-ci-macos.yml`; they are generated artifacts.

25. **Root-file detection** — when the agent creates or modifies repo-root files (rule 3), validate the file's basename against the canonical set before committing. Reject any path that places a root-required file inside a subdirectory.

26. **Accessibility identifiers in generated Swift** — when the agent generates or modifies SwiftUI views, it must attach `.accessibilityIdentifier()` to every interactive element using the `{module}-{component}-{role}-{context?}` pattern (rule 10). Generated identifiers must be deterministic and stable across regenerations.

27. **Branch creation** — the agent must construct branch names programmatically using the template in rule 5. Hard-coded branch names are forbidden.

28. **Consensus system prompts** — reference `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` from `src/consensus.py` by import. Do not duplicate prompt text in agent modules.

29. **Pipeline stage ordering** — `BuildPipeline` in `src/build_director.py` is the single orchestrator. Agents must not invoke CI, commit, or push outside of a `BuildPipeline` stage. Direct `git` or GitHub API calls from agent logic are prohibited; route through the pipeline.

30. **Test isolation** — agent tests must not depend on network access, real GitHub tokens, or filesystem state outside of `tmp_path` / `tmpdir` fixtures. Mock `validate_write_path` and `ci_workflow.ensure()` at the boundary.