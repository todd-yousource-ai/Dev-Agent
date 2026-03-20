# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place code only in the approved subsystem roots.**
   - Use these exact roots:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`
   - Put tests under `tests/<subsystem>/` and mirror the source structure exactly.
   - Example:
     - Source: `src/dtl/policy/validator.py`
     - Test: `tests/dtl/policy/test_validator.py`

2. **Name Python modules in `snake_case`.**
   - Valid: `path_security.py`, `consensus_runner.py`
   - Invalid: `PathSecurity.py`, `consensusRunner.py`

3. **Name test files `test_<module>.py`.**
   - For `src/mcp/router.py`, create `tests/mcp/test_router.py` or `tests/mcp/.../test_router.py` matching the source path.
   - Do not use suffix forms like `router_test.py`.

4. **Keep one primary responsibility per file.**
   - A file must define one main unit: one service, one model group, one adapter, or one utility area.
   - Split files once they contain unrelated concerns such as transport handling plus persistence logic.

5. **Use subsystem-prefixed paths consistently in new code.**
   - Do not place `dtl` code under `src/cal/` or shared utilities inside a random subsystem.
   - Cross-subsystem shared code must live in an explicit shared module approved by the package layout, not copied between folders.

6. **Use the build branch naming convention exactly for all ConsensusDevAgent work.**
   - Format:
     `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     `forge-agent/build/e17/consensusdevagent/pr-042-add-path-validation`

7. **Set `branch_prefix` values from build metadata using the documented format.**
   - `branch_prefix` must be:
     `forge-agent/build/{engineer_id}/{subsystem}`
   - Do not include the PR number or title in `branch_prefix`.

8. **Name accessibility identifiers using the macOS application shell convention wherever UI code exists.**
   - Format:
     `{module}-{component}-{role}-{context?}`
   - Examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`
   - Apply `.accessibilityIdentifier()` to all interactive UI elements.

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Valid: `ConsensusPlanner`, `WritePathValidator`
   - Invalid: `consensusPlanner`, `write_path_validator`

2. **Name functions and methods in `snake_case`.**
   - Valid: `validate_write_path`, `generate_consensus_plan`
   - Invalid: `validateWritePath`, `GenerateConsensusPlan`

3. **Name booleans with `is_`, `has_`, `can_`, or `should_` prefixes.**
   - Valid: `is_valid`, `has_consensus`, `should_retry`
   - Invalid: `valid_flag`, `retry`

4. **Name exception classes with the `Error` suffix.**
   - Valid: `PathTraversalError`, `ConsensusTimeoutError`
   - Invalid: `PathTraversalException`, `ConsensusTimeout`

5. **Name public functions after the action they perform.**
   - Use imperative verbs:
     - `load_context`
     - `validate_write_path`
     - `build_pr_branch_name`
   - Avoid vague names like `handle`, `process`, `do_work` unless the domain object is explicit in the full name.

6. **Name dataclasses and typed models after the domain entity they represent.**
   - For the build pipeline core dataclass, use names like `BuildIntent`, `SubsystemScope`, or `PrdPlan`.
   - Field names must match documented semantics directly:
     - `intent`
     - `subsystem`
     - `scope_statement`
     - `branch_prefix`
     - `relevant_docs`

7. **Keep public API names stable and explicit.**
   - Do not abbreviate domain terms in public functions unless the subsystem directory already standardizes the abbreviation, such as `dtl`, `mcp`, or `vtz`.

## Error and Exception Patterns

1. **Validate paths before any write operation, without exception.**
   - Every write using a user-supplied or derived path must call `validate_write_path` first.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)  # raises on traversal
   ```
   - Apply this before:
     - file creation
     - file overwrite
     - append operations
     - temp file creation in user-selected directories
     - archive extraction outputs

2. **Use validation-returned paths for the write, never the original input.**
   - Correct:
   ```python
   safe_path = validate_write_path(path)
   safe_path.write_text(data)
   ```
   - Incorrect:
   ```python
   validate_write_path(path)
   path.write_text(data)
   ```

3. **Raise specific exceptions for domain failures.**
   - Use a dedicated exception type for each distinct failure class:
     - path traversal
     - unsupported subsystem
     - consensus quorum failure
     - branch naming validation failure
   - Do not raise bare `Exception`.

4. **Do not swallow exceptions from security checks.**
   - If `validate_write_path` raises, propagate the error or convert it to a typed domain error with the original exception chained.
   - Use:
   ```python
   except PathTraversalError as exc:
       raise ArtifactWriteError(str(exc)) from exc
   ```

5. **Convert external library failures at subsystem boundaries.**
   - Wrap third-party exceptions when crossing into Forge domain layers so callers receive Forge-specific errors.

6. **Include actionable context in exception messages.**
   - Messages must identify the operation and the rejected entity.
   - Valid:
     - `invalid branch name: expected forge-agent/build/... format`
     - `write blocked for path outside workspace: {path}`
   - Invalid:
     - `failed`
     - `bad input`

7. **Return values for expected outcomes; use exceptions for violated invariants or failed operations.**
   - Do not return `None` or `False` to represent path traversal, branch format violations, or impossible state transitions when the caller cannot safely continue.

## Import and Module Organisation

1. **Group imports into three blocks in this order: standard library, third-party, local.**
   - Separate each block with one blank line.
   - Example:
   ```python
   from dataclasses import dataclass
   from pathlib import Path

   import pytest

   from src.dtl.policy.validator import PolicyValidator
   from src.dtl.path_security import validate_write_path
   ```

2. **Sort imports alphabetically within each block.**
   - Do not manually preserve historical ordering.

3. **Use absolute imports from the project root package layout.**
   - Prefer stable imports that reflect the real module path.
   - Avoid deep relative imports like `from ...utils import x` in production code.

4. **Keep module top sections limited to imports, constants, and top-level declarations.**
   - Do not perform file writes, network calls, subprocess execution, or environment mutation at import time.

5. **Keep security-sensitive helpers in clearly named modules.**
   - Path validation logic must live in a module named `path_security.py` or an equivalently explicit security module, not hidden in generic `utils.py`.

6. **Do not create catch-all `utils.py` files for mixed concerns.**
   - Name modules by responsibility:
     - `branch_naming.py`
     - `path_security.py`
     - `consensus_scoring.py`
   - Split unrelated helpers into separate modules.

7. **Mirror source package structure in tests.**
   - If a production module is `src/rewind/replay/session_store.py`, the test module path must mirror it under `tests/rewind/replay/test_session_store.py`.

## Comment and Documentation Rules

1. **Write docstrings for every public class and public function.**
   - State:
     - purpose
     - key inputs
     - return value or side effect
     - raised exceptions when non-obvious

2. **Document security-critical steps inline immediately above the guarded operation.**
   - Required for path validation before writes.
   - Example:
   ```python
   # Validate destination path before any write to block traversal attacks.
   safe_path = validate_write_path(output_path)
   ```

3. **Use comments to explain why, not restate what the code already says.**
   - Valid:
     - `# Use deterministic branch formatting so PR automation can parse engineer and subsystem.`
   - Invalid:
     - `# Increment i`

4. **Keep comments synchronized with TRD terminology.**
   - Use exact domain terms from documentation such as:
     - `subsystem`
     - `branch_prefix`
     - `scope_statement`
     - `relevant_docs`
   - Do not rename these concepts in comments.

5. **Document any field that maps directly to a TRD-defined structure using the TRD name.**
   - For dataclasses matching the build pipeline core dataclass, preserve the documented field meaning in comments or docstrings.

6. **Include concrete examples in docs for formatted identifiers.**
   - For branch naming and accessibility identifiers, show one valid example in the docstring or module documentation where the formatter is implemented.

7. **Do not leave placeholder comments or generated boilerplate markers in committed code.**
   - Remove comments like:
     - `# TODO: handle this better` unless accompanied by a tracked issue ID
     - `# generated by agent`
     - `# placeholder`

## ConsensusDevAgent-Specific Patterns

1. **Represent the build request core entity as a typed dataclass or equivalent typed model with the documented fields.**
   - Include at minimum:
   ```python
   intent: str
   subsystem: str
   scope_statement: str
   branch_prefix: str
   relevant_docs: list[str]
   ```

2. **Populate `subsystem` only from documented subsystem names.**
   - Use names derived from docs such as `DTL`, `Payments`, or the canonical subsystem label for the request.
   - Do not invent ad hoc aliases in pipeline state.

3. **Generate `branch_prefix` deterministically from engineer and subsystem.**
   - Format:
     `forge-agent/build/{engineer_id}/{subsystem}`
   - Use a dedicated formatter function.
   - Validate generated values before use in Git operations.

4. **Generate full branch names using the mandatory branch format and zero-padded PR numbers.**
   - Required format:
     `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - `N` must always be three digits minimum.
   - Convert titles to lowercase hyphenated slugs.
   - Reject branch names that do not match the exact pattern.

5. **Require at least one test for every public function and class in ConsensusDevAgent code.**
   - For each public API, cover:
     - happy path
     - one edge case
     - one error or failure case

6. **Use the required test framework by language.**
   - Python: `pytest`
   - TypeScript: `Jest`
   - Go: `go test`

7. **Use fixtures and parametrization for repetitive test cases.**
   - Do not duplicate equivalent branch-format, path-validation, or subsystem-mapping cases across multiple test functions when `pytest.mark.parametrize` or fixtures fit.

8. **Mock all external I/O in tests.**
   - Mock:
     - API calls
     - filesystem access
     - subprocess execution
   - Tests must not depend on real Git state, network access, or writable local directories.

9. **Keep tests independent.**
   - Do not share mutable global state between tests.
   - Each test must set up its own inputs and mocks.

10. **Write explicit tests for path validation before write operations.**
    - Every function that writes files must have a test proving:
      - `validate_write_path` is called before the write
      - traversal input raises an error
      - the validated path, not the raw path, is used for output

11. **Write explicit tests for branch naming formatters and validators.**
    - Minimum required cases:
      - valid branch name
      - invalid engineer ID
      - invalid subsystem slug
      - PR number padding
      - invalid title slug characters

12. **Name accessibility identifiers in agent-driven UI surfaces with the required pattern.**
    - Format:
      `{module}-{component}-{role}-{context?}`
    - For lists or repeated controls, include the stable domain identifier in the context segment.
    - Example:
      `stream-gate-yes-button-{gateId}`

13. **Do not merge agent-generated code that writes files, creates branches, or emits artifacts without corresponding validation tests.**
    - Path-writing code requires path-security tests.
    - Branch-generation code requires branch-format validation tests.