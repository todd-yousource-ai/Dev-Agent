# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the project TRDs and are mandatory for every contributor and automated agent.

---

## 1. Code Conventions

### 1.1 Language Defaults

1. Python files use **Python 3.11+** syntax. Type hints are required on all public function signatures.
2. Swift files target the **macOS SwiftUI** framework and follow Swift 5.9+ conventions.
3. All source files use **UTF-8 encoding** with a single trailing newline.

---

## 2. File and Directory Naming

4. Python backend files live under `src/` and use **snake_case**: `src/consensus.py`, `src/build_director.py`.
5. The following files **must live at the repository root** (no directory prefix): `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`. Validate these by **basename against a known set**, never by directory.
6. CI workflow files are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is permitted.
7. `conftest.py` is **auto-committed** by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit this file.
8. Test files mirror source paths: `src/build_director.py` → `tests/test_build_director.py`.

---

## 3. Class and Function Naming

9. Python classes use **PascalCase**: `ConsensusEngine`, `BuildPipeline`.
10. Python functions and methods use **snake_case**: `validate_write_path`, `ensure`.
11. Python constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`.
12. Swift types use **PascalCase**; Swift properties and methods use **camelCase**.
13. Accessibility identifiers in SwiftUI follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on **every** interactive element:
    - `"auth-touchid-button"`
    - `"settings-anthropic-key-field"`
    - `"navigator-project-row-{projectId}"`
    - `"stream-gate-yes-button-{gateId}"`

---

## 4. Error and Exception Patterns

14. Raise domain-specific exceptions (e.g., `PathTraversalError`, `PipelineError`), never bare `Exception`.
15. Every `except` block must log the error **before** re-raising or returning a safe default.
16. Path validation failures return a **safe default path**, never `None` or an empty string.

---

## 5. Import and Module Organisation

17. Group imports in this order, separated by a blank line:
    1. Standard library
    2. Third-party packages
    3. Project-local (`from src.consensus import …`)
18. Do **not** use wildcard imports (`from module import *`).
19. The `conftest.py` at repo root ensures `src/` is on `sys.path`; do not add manual `sys.path` hacks elsewhere.

---

## 6. Comment and Documentation Rules

20. Every public class and function must have a **docstring** (Google style for Python, `///` doc comments for Swift).
21. Inline comments explain **why**, not what.
22. Removed or deprecated code must reference the TRD version where the change occurred (e.g., `# Removed in TRD-3 v6.0 — keyword-based docs-PR detection`).
23. Do **not** leave TODO comments without a linked issue number: `# TODO(#142): …`.

---

## 7. CraftedAgent-Specific Patterns

### 7.1 Path Security — Validate Before ANY Write

24. **Every** file-write operation performed by an agent must call `validate_write_path` first:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
25. Never construct output paths by string concatenation from user input. Always validate through the security module.

### 7.2 Branch Naming

26. Agent branches **must** follow this exact pattern (the `forge-agent` prefix is kept intentionally for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    Example: `forge-agent/build/e42/crafted-agent/pr-007-fix-path-validation`

### 7.3 Docs-PR Detection

27. Docs-PR classification is determined by **label and path-based heuristics only**. The keyword-list approach (`_docs_keywords`) was removed in TRD-3 v6.0 and must **not** be reintroduced.

### 7.4 Root-File Validation

28. When an agent commits files, validate every file destined for the repo root against the **known root-file basename set** (rule 5). Reject or relocate any file that does not belong.

### 7.5 CI Workflow Integrity

29. Agents must call `ci_workflow.ensure()` before opening a PR to guarantee `conftest.py` and workflow files are present and correctly named.

### 7.6 Accessibility Identifiers (SwiftUI)

30. Every interactive SwiftUI element must carry an `.accessibilityIdentifier()` following the `{module}-{component}-{role}-{context?}` convention (rule 13). UI PRs missing identifiers will be rejected by review.