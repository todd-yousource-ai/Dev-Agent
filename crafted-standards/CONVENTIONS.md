# CONVENTIONS.md — CraftedApp Subsystem

---

## 1. Code Conventions

### 1.1 Language Boundaries

1. **Python** is used for all backend orchestration, build pipeline, CI workflow generation, and agent tooling. Target Python 3.11+.
2. **Swift** is used for all macOS application code (SwiftUI, accessibility, native UI). Target the Swift version specified in `crafted-ci-macos.yml`.
3. Never mix languages in a single source file.

---

## 2. File and Directory Naming

4. Python source files use **snake_case** exclusively: `build_director.py`, `consensus.py`, `path_security.py`.
5. Swift source files use **PascalCase** matching their primary type: `StreamGateCard.swift`, `AuthTouchIDView.swift`.
6. CI workflow files are named with the `crafted-` prefix: `crafted-ci.yml` (Ubuntu/Python) and `crafted-ci-macos.yml` (macOS/Swift).
7. The following files **must live at the repository root** and are validated by basename, not by directory path: `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
8. Never nest root-required files inside subdirectories. CI may reject commits that relocate them.
9. `conftest.py` is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests — do not delete or relocate it manually.

---

## 3. Class and Function Naming

10. Python classes use **PascalCase**: `ConsensusEngine`, `BuildPipeline`.
11. Python functions and methods use **snake_case**: `validate_write_path`, `ensure`.
12. Python module-level constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
13. Swift types (structs, classes, enums, protocols) use **PascalCase**: `StreamGateCard`, `NavigatorProjectRow`.
14. Swift methods, properties, and local variables use **camelCase**: `gateId`, `projectId`, `testAnthropicKey`.
15. Private Python helpers that are internal to a module are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

---

## 4. Error and Exception Patterns

16. Validate all file-system paths **before any write operation**. Use `path_security.validate_write_path`:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
17. Never catch `Exception` or `BaseException` bare unless you immediately re-raise or log with full traceback.
18. Custom exceptions inherit from a project-specific base (e.g., `CraftedError`) rather than bare `Exception`.
19. On path traversal detection, `validate_write_path` returns a **safe default path** — it does not raise. Callers must check the returned value, not assume the original path was used.

---

## 5. Import and Module Organisation

20. Group imports in this order, separated by a blank line:
    1. Standard library
    2. Third-party packages
    3. Project-local (`src.*`) modules
21. Canonical module locations:
    | Module | Contents |
    |---|---|
    | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
    | `src/build_director.py` | `BuildPipeline` |
    | `src/path_security.py` | `validate_write_path` |
22. Do not use wildcard imports (`from module import *`) anywhere.
23. Prefer explicit named imports over importing an entire module when only one or two symbols are needed.

---

## 6. Comment and Documentation Rules

24. Every Python module has a single-line module docstring stating its purpose.
25. Every public class and public function has a docstring (Google style for Python).
26. Swift public types and methods have `///` doc comments.
27. Inline comments explain **why**, not **what**. Do not restate the code.
28. TODO comments must include an engineer ID or ticket reference: `# TODO(eng-042): migrate to async`.

---

## 7. CraftedApp-Specific Patterns

### 7.1 Branch Naming (Mandatory)

29. All agent/build branches follow this exact pattern:
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id`: the assigned engineer identifier (e.g., `eng-042`).
    - `subsystem_slug`: lowercase, hyphen-separated subsystem name (e.g., `crafted-app`).
    - `N`: zero-padded three-digit PR sequence number.
    - `title_slug`: lowercase, hyphen-separated summary (e.g., `add-stream-gate`).

    Example: `forge-agent/build/eng-042/crafted-app/pr-007-add-stream-gate`

30. The prefix `forge-agent` is kept **intentionally** for tooling compatibility — do not rename it.

### 7.2 Accessibility Identifier Convention (axIdentifier)

31. Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.
32. Identifiers follow the pattern: `{module}-{component}-{role}-{context?}`
    - All segments are **lowercase**, separated by **hyphens**.
    - `context` is optional and typically a dynamic ID suffix.
33. Reference examples (authoritative):
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
34. Dynamic segments (e.g., `{gateId}`) are interpolated at runtime using the entity's stable identifier. Never use array indices as identifiers.

### 7.3 CI Workflow Rules

35. Python CI runs on Ubuntu via `crafted-ci.yml`. Swift/macOS CI runs via `crafted-ci-macos.yml`.
36. Do not combine Ubuntu and macOS jobs into a single workflow file.
37. `conftest.py` existence is enforced by CI — if missing, `ci_workflow.ensure()` regenerates and commits it.

### 7.4 Path Security

38. **No agent or automated tool may write to an arbitrary user-supplied path** without first passing it through `validate_write_path`.
39. This rule applies to all write operations: file creation, file overwrite, directory creation, symlink creation.
40. Path validation is enforced at the call site, not deferred to a framework or middleware layer.

### 7.5 Docs-Only PR Detection (Deprecated)

41. The keyword-list approach for detecting docs-only PRs (`_docs_keywords` set, `_is_docs_pr` flag) was **removed in v6.0**. Do not reintroduce keyword-matching for PR classification. Use the replacement mechanism defined in the current pipeline version.