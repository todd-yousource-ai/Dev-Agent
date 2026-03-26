# CONVENTIONS.md — CraftedAgent Subsystem

All rules derived from project TRDs. Every convention is mandatory unless marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Python backend files** use `snake_case.py` and live under `src/`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu)
   - `crafted-ci-macos.yml` (macOS Swift)

3. **Repo-root files** must be committed without any directory prefix. Validate by basename against this exact set:
   ```
   README.md, CODEOWNERS, LICENSE, .gitignore, .editorconfig,
   VERSION, Makefile, pyproject.toml
   ```

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` for `src/` import resolution. Never manually create or relocate it.

5. **No spaces, no uppercase** in directory names. Use hyphens for multi-word directory names (`crafted-agent/`, not `CraftedAgent/`).

---

## 2. Class and Function Naming

6. **Classes**: `PascalCase` — e.g., `ConsensusEngine`, `BuildPipeline`.

7. **Functions and methods**: `snake_case` — e.g., `validate_write_path`, `ensure`.

8. **Module-level constants**: `UPPER_SNAKE_CASE` — e.g., `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private/internal module constants**: prefix with `_` — e.g., `_docs_keywords`, `_is_docs_pr`.

10. **axIdentifier strings** (SwiftUI accessibility identifiers) follow the pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase, hyphen-separated.
    - The optional `{context}` segment uses a dynamic ID when the element repeats.
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

11. **Validate paths before ANY write.** Every agent-initiated file write must call `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempt
    ```

12. **Never silently swallow exceptions.** Catch specific exception types; log or re-raise.

13. **Path traversal violations** must return a safe default path (not raise), per `validate_write_path` contract. Callers must not bypass the returned value.

14. **Repo-root file validation** must reject any path that resolves outside the repo root or contains `..` segments before writing.

---

## 4. Import and Module Organisation

15. **Import order** (enforced, separated by blank lines):
    1. Standard library
    2. Third-party packages
    3. Project-local (`src.*` / relative imports)

16. **Always import from `src/`** for backend modules. Do not duplicate modules outside `src/`.

17. **Do not manually edit `conftest.py`** — it is machine-generated for `src/` import path setup.

18. **No wildcard imports** (`from module import *`). Always import names explicitly.

---

## 5. Comment and Documentation Rules

19. **Every public class and function** must have a single-line docstring at minimum.

20. **Inline comments** explain *why*, not *what*. Do not restate the code.

21. **TRD references**: when a block of code implements a specific TRD requirement, add a comment of the form:
    ```python
    # TRD-3 §5.0: keyword-based docs-PR detection (removed in v6.0)
    ```

22. **axIdentifier comments** in SwiftUI source must include the convention reminder on first use in each file:
    ```swift
    // Convention: {module}-{component}-{role}-{context?}
    ```

---

## 6. CraftedAgent-Specific Patterns

### 6.1 Branch Naming

23. **Mandatory format** (kept as `forge-agent` for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `{N:03d}` — zero-padded to three digits.
    - `{title_slug}` — lowercase, hyphens only, no special characters.
    - Example: `forge-agent/build/eng42/crafted-agent/pr-007-fix-path-validation`

### 6.2 CI Workflow Rules

24. `crafted-ci.yml` targets **Ubuntu** runners only.

25. `crafted-ci-macos.yml` targets **macOS** runners and includes Swift build/test steps.

26. Both workflow files must live in `.github/workflows/`. No other location is valid.

### 6.3 Write-Path Security

27. **No file write** may occur without a preceding `validate_write_path` call. This applies to agent-generated code, config emission, and artifact staging.

28. Repo-root files (rule 3) are validated by **basename membership**, not by checking the parent directory string.

### 6.4 Docs-PR Detection (Historical Reference)

29. The v5.0 keyword-list approach (`_docs_keywords` set matched against PR title) was **removed in v6.0**. Do not re-introduce keyword-set heuristics for docs-PR classification. Use the current detection mechanism defined in `build_director.py`.

### 6.5 Consensus Engine Constants

30. `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` must be defined **only** in `src/consensus.py`. Other modules must import them; duplication is prohibited.