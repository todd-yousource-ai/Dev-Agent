# CONVENTIONS.md — CraftedAgent Subsystem

All rules below are derived from the CraftedAgent TRD documents. Every rule is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - `src/path_security.py` — `validate_write_path`

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runner)
   - `crafted-ci-macos.yml` (macOS Swift runner)

3. **Repo-root files** must be committed without any directory prefix. The following basenames are validated against a known allowlist; never nest them in subdirectories:
   ```
   README.md, CODEOWNERS, LICENSE, .gitignore, .editorconfig,
   VERSION, Makefile, pyproject.toml
   ```

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never delete or relocate it manually.

5. **Test files** use the pattern `tests/test_{module_name}.py`, mirroring the source file they cover.

---

## 2. Branch Naming

6. All agent branches follow this exact template (the `forge-agent` prefix is intentional and must not be changed):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `{engineer_id}` — lowercase alphanumeric identifier of the authoring engineer.
   - `{subsystem_slug}` — lowercase, hyphen-separated subsystem name (e.g., `crafted-agent`).
   - `{N:03d}` — zero-padded, three-digit PR sequence number.
   - `{title_slug}` — lowercase, hyphen-separated summary (max 48 chars).

---

## 3. Class and Function Naming

7. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `PathSecurityError`.

8. **Python functions and methods** use `snake_case`: `validate_write_path`, `ensure`.

9. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

10. **Private/internal module constants** are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.

11. **Swift accessibility identifiers** follow the pattern `{module}-{component}-{role}-{context?}`:
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
    Every interactive SwiftUI element must have `.accessibilityIdentifier()` set using this convention. Omitting `{context}` is allowed only when the element is globally unique.

---

## 4. Error and Exception Patterns

12. **Validate paths before ANY filesystem write.** Never write to a user-supplied path without sanitisation:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on directory-traversal attempt
    ```

13. `validate_write_path` must return a **safe default path** (not raise) when a traversal attack is detected. Callers must not catch and suppress the substitution silently — log a warning at minimum.

14. Custom exceptions inherit from a single subsystem base class `CraftedAgentError(Exception)`.

15. Never use bare `except:`. Always catch the narrowest applicable type.

---

## 5. Import and Module Organisation

16. **Import order** (enforced by linter config in `pyproject.toml`):
    1. Standard library
    2. Third-party packages
    3. `src/` project modules (absolute imports from `src`)

17. Separate each group with one blank line.

18. Do not use relative imports. All internal imports reference the `src` package:
    ```python
    from src.consensus import ConsensusEngine
    from src.build_director import BuildPipeline
    ```

19. Circular imports are forbidden. If module A needs a type from module B and vice-versa, extract the shared type into a dedicated `src/types_.py` or `src/protocols.py` module.

---

## 6. Comment and Documentation Rules

20. Every public class and function has a docstring. Use imperative mood in the summary line:
    ```python
    def validate_write_path(path: str) -> str:
        """Sanitise and return a safe filesystem path for writing."""
    ```

21. Inline comments explain **why**, not **what**. If the code needs a "what" comment, refactor for clarity instead.

22. TODO comments include an engineer ID and issue reference:
    ```python
    # TODO(engineer_id): handle timeout retry — see GH-142
    ```

23. Do not commit commented-out code. Use version control history instead.

---

## 7. CraftedAgent-Specific Patterns

24. **Docs-only PR detection** (v6.0+): Classification is performed by the pipeline's label/path heuristics, **not** by keyword matching against the PR title. The v5.0 keyword-list approach (`_docs_keywords`) has been removed; do not reintroduce it.

25. **CI workflow bootstrap**: Call `ci_workflow.ensure()` at the start of every pipeline run. This guarantees `conftest.py` and required fixture files exist before `pytest` collection.

26. **Root-file validation**: When committing files, validate each filename's **basename** against the known root-file allowlist (rule 3). Do not validate by checking whether the path starts with `/`.

27. **Accessibility identifiers are test contracts.** Changing an `axIdentifier` string is a breaking change for UI tests. Update the corresponding XCUITest query in the same commit.

28. **System prompt constants** (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`) are defined only in `src/consensus.py`. Other modules must import them — never duplicate the string literals.

29. **Pipeline entry point**: `BuildPipeline` in `src/build_director.py` is the sole orchestrator. Agent logic must not invoke CI steps directly; it delegates through `BuildPipeline` methods.

30. **Path traversal rule applies to all agents.** Any CraftedAgent code path that writes to disk — logs, artefacts, generated code, temp files — must call `validate_write_path` first. No exceptions.