# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place code only in approved subsystem roots.**  
   Use these top-level paths exactly:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`
   - `tests/<subsystem>/`

2. **Mirror source structure exactly under `tests/`.**  
   If implementation lives at `src/dtl/policy/evaluator.py`, tests must live under `tests/dtl/policy/`, for example:
   - `src/dtl/policy/evaluator.py`
   - `tests/dtl/policy/test_evaluator.py`

3. **Name Python files in `snake_case`.**  
   Valid examples:
   - `consensus_runner.py`
   - `path_security.py`
   - `plan_builder.py`

4. **Name test files `test_<module>.py`.**  
   Examples:
   - `test_consensus_runner.py`
   - `test_path_security.py`

5. **Keep one primary responsibility per module file.**  
   Do not combine unrelated concerns in the same file.  
   Example:
   - `path_security.py` contains path validation logic only.
   - `branch_naming.py` contains branch formatting/parsing only.

6. **Do not create ad hoc directory abbreviations.**  
   Use only the subsystem abbreviations defined by project standards (`cal`, `dtl`, `vtz`, etc.). Do not invent alternatives like `consensusdev`, `trust`, or `labels`.

7. **Use branch names in the mandatory format for all build work.**  
   Format:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`  
   Example:
   `forge-agent/build/e17/dtl/pr-042-add-consensus-retry`

8. **Set `branch_prefix` values to the non-PR portion of the mandatory branch format.**  
   Use:
   `forge-agent/build/{engineer_id}/{subsystem_slug}`  
   Example:
   `forge-agent/build/e17/dtl`

9. **Use the canonical subsystem slug in branch names and paths.**  
   If the subsystem directory is `src/dtl/`, the branch slug must be `dtl`, not `data-trust-label`.

10. **Do not write to a user-supplied path before validation.**  
    Every filesystem write must validate the target path first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Apply this before:
    - file creation
    - file overwrite
    - temp file promotion
    - log export
    - artifact generation

11. **Validate destination paths before directory creation as well as file writes.**  
    If code may call `mkdir`, `open(..., "w")`, `write_text`, `write_bytes`, archive extraction, or rename/move into a target path, validate first.

12. **Do not construct write paths by string concatenation alone.**  
    Build paths with path utilities, then pass the final result through `validate_write_path(...)` before writing.

## Class and Function Naming

1. **Name classes in `PascalCase`.**  
   Examples:
   - `ConsensusPlanner`
   - `BuildIntent`
   - `PathWriteGuard`

2. **Name functions and methods in `snake_case`.**  
   Examples:
   - `validate_write_path`
   - `build_branch_name`
   - `collect_relevant_docs`

3. **Name constants in `UPPER_SNAKE_CASE`.**  
   Examples:
   - `TEST_GENERATION_SYSTEM`
   - `DEFAULT_BRANCH_PREFIX`
   - `MAX_RETRY_ATTEMPTS`

4. **Use noun names for dataclasses and value objects.**  
   Good:
   - `BuildIntent`
   - `ScopeStatement`
   - `RelevantDocSet`  
   Avoid:
   - `Building`
   - `PlanningData`

5. **Use verb phrases for functions that perform actions.**  
   Good:
   - `generate_test_plan`
   - `validate_branch_name`
   - `write_artifact_manifest`

6. **Use `is_`, `has_`, or `can_` prefixes for boolean-returning functions.**  
   Examples:
   - `is_safe_path`
   - `has_required_docs`
   - `can_retry_stage`

7. **Name exception classes with an `Error` suffix.**  
   Examples:
   - `PathTraversalError`
   - `InvalidBranchNameError`
   - `ConsensusTimeoutError`

8. **Keep public API names stable and explicit.**  
   Do not use single-letter or shortened public names such as `gen_plan`, `cfg`, or `ctx` unless they are established domain terms.

9. **Name dataclass fields exactly after their domain meaning from TRDs when representing core build entities.**  
   For the Stage 1 core entity, use these field names exactly:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

10. **Do not alias accessibility identifier concepts with different terms.**  
    Use `ax_identifier` in code when representing or generating accessibility identifiers.

## Error and Exception Patterns

1. **Raise exceptions instead of returning silent failure codes for invalid internal states.**  
   Invalid branch formats, path traversal attempts, missing required docs, and malformed stage entities must raise explicit exceptions.

2. **Use specific exception types for expected failure modes.**  
   Do not raise bare `Exception`.  
   Prefer:
   - `InvalidBranchNameError`
   - `PathTraversalError`
   - `MissingRelevantDocsError`

3. **Make exception messages include the invalid value and the violated rule.**  
   Good:
   - `InvalidBranchNameError: branch 'forge/build/x' does not match 'forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}'`

4. **Fail before side effects.**  
   Validate inputs, branch names, required fields, and write paths before:
   - creating files
   - mutating state
   - starting subprocesses
   - calling external APIs

5. **Wrap external I/O failures at the subsystem boundary.**  
   Convert raw filesystem, subprocess, or API exceptions into domain-specific errors when crossing module boundaries.

6. **Do not suppress exceptions with broad `except` blocks.**  
   If catching an exception, either:
   - handle it fully and deterministically, or
   - re-raise a more specific domain exception with context.

7. **Preserve the original exception as the cause when re-raising.**  
   Use exception chaining:
   ```python
   raise ArtifactWriteError(f"failed to write artifact to {safe_path}") from err
   ```

8. **Treat any unvalidated write path as an error condition.**  
   Code review should reject any write operation that lacks a prior `validate_write_path(...)` call on the effective destination.

## Import and Module Organisation

1. **Group imports in this order with one blank line between groups:**
   1. standard library
   2. third-party packages
   3. local application imports

2. **Use absolute imports for project modules.**  
   Prefer:
   ```python
   from path_security import validate_write_path
   ```
   or the package-qualified project form used by the subsystem. Do not use relative imports like `from ..utils import ...` in new modules unless the package layout requires it.

3. **Import only what the module uses.**  
   Remove unused imports immediately. Do not import entire modules when a single symbol is sufficient unless namespace clarity is required.

4. **Keep module top levels free of side effects.**  
   Do not perform file writes, network calls, subprocess launches, or environment mutation at import time.

5. **Define constants near the top of the module, below imports.**  
   Example:
   ```python
   TEST_GENERATION_SYSTEM = """..."""
   ```

6. **Separate protocol/type definitions from runtime orchestration when files become mixed-purpose.**  
   If a module grows to include dataclasses, validation, and execution logic, split it into focused modules.

7. **Keep test helpers inside the mirrored `tests/<subsystem>/` tree unless reused across multiple subsystem test packages.**  
   Shared reusable test utilities may live in a dedicated `tests/helpers/` package only when used by more than one subsystem.

## Comment and Documentation Rules

1. **Write comments only for non-obvious intent, invariants, or TRD-required behavior.**  
   Do not comment what the next line literally does.

2. **Reference the governing TRD rule when implementing a mandatory convention.**  
   Example comment:
   ```python
   # TRD: validate paths before any write to prevent traversal on user-supplied targets.
   ```

3. **Document every public function and class with a concise docstring.**  
   The docstring must state:
   - purpose
   - key inputs
   - raised exceptions for invalid usage or failure

4. **Document dataclass fields that encode TRD-defined build concepts.**  
   For the core build entity, include field comments or docstrings for:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

5. **Do not use placeholder comments such as `TODO`, `FIXME`, or `hack` without an actionable qualifier.**  
   If such a comment is necessary, include:
   - exact problem
   - owner or subsystem
   - removal condition

6. **Keep examples in documentation consistent with mandatory formats.**  
   Branch examples must use:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

7. **For UI-facing code, document accessibility identifier format where identifiers are assigned or generated.**  
   Use the convention exactly:
   `{module}-{component}-{role}-{context?}`

8. **Assign `.accessibilityIdentifier()` on all interactive elements in the macOS application shell.**  
   Required examples include patterns like:
   - `auth-touchid-button`
   - `settings-anthropic-key-field`
   - `settings-anthropic-key-test-button`
   - `navigator-project-row-{projectId}`
   - `stream-gate-yes-button-{gateId}`

9. **Generate accessibility identifiers with stable domain IDs, not display text.**  
   Use `projectId`, `gateId`, or equivalent stable identifiers. Do not use labels that can change due to localization or copy edits.

## ConsensusDevAgent-Specific Patterns

1. **Represent the Stage 1 core build entity as a dataclass with the TRD-defined fields.**  
   Include these fields exactly:
   ```python
   @dataclass
   class BuildIntent:
       intent: str
       subsystem: str
       scope_statement: str
       branch_prefix: str
       relevant_docs: list[str]
   ```

2. **Populate `subsystem` from documentation-derived canonical subsystem names only.**  
   Do not derive `subsystem` from free-form operator wording if docs identify a canonical subsystem.

3. **Keep `scope_statement` to 2–3 sentences.**  
   Reject or rewrite longer scope statements before persisting or handing off to later stages.

4. **Populate `relevant_docs` with document names, not file paths or prose excerpts.**  
   Good:
   - `TRD-2-Consensus-Engine`
   - `TRD-3-Build-Pipeline`  
   Avoid:
   - `/docs/trd/consensus.md`
   - `the consensus engine section about retries`

5. **Build branch names only from validated components.**  
   Validate:
   - `engineer_id`
   - `subsystem_slug`
   - `N` as zero-padded 3-digit PR number
   - `title_slug`

6. **Use lowercase kebab-case for `subsystem_slug` and `title_slug` in branch names.**  
   Good:
   - `dtl`
   - `consensus-agent`
   - `add-path-validation`

7. **Reject branch names that do not match the exact mandatory template.**  
   Do not auto-correct malformed branch names silently.

8. **Encode test generation behavior to the project testing standard.**  
   All generated tests must satisfy these minimums:
   - use `pytest` for Python
   - give every public function and class at least one test
   - cover happy path, one edge case, and one error/failure case
   - use fixtures and `@pytest.mark.parametrize` for repetitive cases
   - mock all external I/O
   - keep tests independent with no shared mutable state

9. **Treat filesystem, API, subprocess, and network interactions as external I/O in generated tests.**  
   Generated tests must mock or fake these dependencies rather than invoking real systems.

10. **Generate tests in the mirrored subsystem test path only.**  
    Example:
    - source: `src/mcp/policy/compiler.py`
    - test: `tests/mcp/policy/test_compiler.py`

11. **Require at least one failure-path test for path validation in modules that perform writes.**  
    If a module writes files, its tests must include a case where `validate_write_path(...)` rejects an unsafe path.

12. **Keep test cases independent and non-order-dependent.**  
    A test must pass when run alone, with the full suite, or in a randomized order.

13. **Use fixtures for reusable build entities and doc sets.**  
    Example fixtures:
    - a valid `BuildIntent`
    - a canonical `relevant_docs` list
    - a safe temporary output path

14. **Do not let generated tests hit the real repository root via user-controlled paths.**  
    Use temporary directories and validated paths only.

15. **When generating UI automation or accessibility checks, assert exact `axIdentifier` strings.**  
    Do not assert partial matches when the identifier format is deterministic.

16. **Name generated test functions by scenario, not implementation detail.**  
    Good:
    - `test_validate_write_path_rejects_traversal`
    - `test_build_branch_name_formats_zero_padded_pr_number`
    - `test_build_intent_requires_canonical_subsystem`

17. **When code writes artifacts from operator or agent input, follow this sequence exactly:**
    1. derive target path
    2. validate with `validate_write_path(...)`
    3. perform write
    4. raise a domain-specific error on failure

18. **Do not merge ConsensusDevAgent changes that add public functions or classes without corresponding tests.**  
    This is a hard requirement, not a recommendation.