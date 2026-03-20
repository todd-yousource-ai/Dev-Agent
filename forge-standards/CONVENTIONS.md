# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place code only in the approved subsystem roots.**
   - Use these directories exactly:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`
   - Do not create alternate subsystem roots such as `src/common_trust/`, `src/consensus/`, or `lib/forge/` unless explicitly added to the TRDs.

2. **Mirror source layout exactly under tests.**
   - For any source file under `src/<subsystem>/...`, create tests under `tests/<subsystem>/...` with matching nested folders.
   - Example:
     - Source: `src/dtl/policy/evaluator.py`
     - Test: `tests/dtl/policy/test_evaluator.py`

3. **Name Python files in `snake_case`.**
   - Examples:
     - `intent_entity.py`
     - `path_security.py`
     - `build_plan_parser.py`
   - Do not use hyphens, spaces, or PascalCase in filenames.

4. **Use `test_*.py` naming for Python test files.**
   - Examples:
     - `test_intent_entity.py`
     - `test_validate_write_path.py`

5. **Keep one primary responsibility per module file.**
   - A file named `intent_entity.py` must contain the dataclass/entity and closely related helpers only.
   - Do not mix unrelated concerns such as path validation, git branch naming, and API transport in the same module.

6. **Store shared path-write protections in a dedicated security-oriented module.**
   - Put write-path validation utilities in a module such as `path_security.py`.
   - All filesystem write call sites must import from that module rather than reimplement traversal checks inline.

7. **Use the mandatory branch naming format for all generated or documented branch names.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e17/dtl/pr-042-add-policy-cache`
   - `subsystem_slug` must match the subsystem directory name or approved slug.

8. **Set `branch_prefix` values to the TRD-defined prefix shape only.**
   - Use:
     - `forge-agent/build/{engineer_id}/{subsystem}`
   - Do not append PR number or title into `branch_prefix`; those belong only in full branch names.

9. **Use doc-derived subsystem names consistently across entities and paths.**
   - If `IntentEntity.subsystem` is `DTL`, source and test placement must resolve to the corresponding approved slug directory such as `src/dtl/` and `tests/dtl/`.
   - Do not invent aliases for the same subsystem within the codebase.

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Examples:
     - `IntentEntity`
     - `BranchNameBuilder`
     - `ConsensusDecisionEngine`

2. **Name functions and methods in `snake_case`.**
   - Examples:
     - `validate_write_path`
     - `build_branch_name`
     - `derive_scope_statement`

3. **Use nouns for dataclasses and entities.**
   - Dataclasses representing persisted or transported state must be named as entities, not actions.
   - Correct:
     - `IntentEntity`
     - `BuildPlan`
   - Incorrect:
     - `BuildingIntent`
     - `ProcessedPlanning`

4. **Use verb-first names for functions that perform actions.**
   - Correct:
     - `validate_write_path`
     - `load_relevant_docs`
     - `generate_test_cases`
   - Incorrect:
     - `path_validation`
     - `docs_loader`

5. **Name boolean-returning functions and properties as predicates.**
   - Prefix with `is_`, `has_`, `can_`, or `should_`.
   - Examples:
     - `is_safe_branch_name`
     - `has_relevant_docs`

6. **Keep public API names explicit about subsystem semantics.**
   - Prefer:
     - `derive_subsystem_from_docs`
     - `build_consensus_prompt`
   - Avoid vague names such as:
     - `process`
     - `handle`
     - `run_step`

7. **Name exception classes with the `Error` suffix.**
   - Examples:
     - `PathTraversalError`
     - `InvalidBranchNameError`
     - `ConsensusTimeoutError`

8. **Use the TRD field names exactly when implementing the core dataclass/entity.**
   - Required field names:
     - `intent`
     - `subsystem`
     - `scope_statement`
     - `branch_prefix`
     - `relevant_docs`
   - Do not rename them to synonyms such as `user_intent`, `subsystem_name`, or `docs`.

9. **Use the macOS accessibility identifier format exactly for all interactive UI elements.**
   - Format:
     - `{module}-{component}-{role}-{context?}`
   - Set via `.accessibilityIdentifier(...)`.
   - Examples:
     - `"auth-touchid-button"`
     - `"settings-anthropic-key-field"`
     - `"navigator-project-row-{projectId}"`
   - For dynamic identifiers, include the runtime identifier at the end.

## Error and Exception Patterns

1. **Validate paths before any filesystem write.**
   - Every write path derived from user, agent, config, prompt, or external input must be passed through `validate_write_path(...)` before opening, creating, replacing, or deleting files.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - This rule applies to:
     - file writes
     - file overwrites
     - directory creation
     - archive extraction targets
     - generated test output
     - patch application destinations

2. **Never write to an unvalidated path, even after manual normalization.**
   - Calls such as `os.path.abspath`, `Path.resolve`, or string replacement do not satisfy the validation requirement by themselves.
   - `validate_write_path(...)` must still be called at the final write site.

3. **Raise typed exceptions for validation failures.**
   - Do not return `None`, `False`, or string error codes for invalid paths, invalid branch names, or malformed intent entities.
   - Raise a specific exception class.

4. **Raise early on malformed branch names or prefixes.**
   - If a branch name does not match:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - raise `InvalidBranchNameError` or an equally specific typed exception.

5. **Preserve the original exception as context when wrapping lower-level errors.**
   - Use:
   ```python
   try:
       ...
   except OSError as exc:
       raise PathWriteError(f"failed to write {safe_path}") from exc
   ```

6. **Do not suppress filesystem, subprocess, or network exceptions silently.**
   - Empty `except` blocks and fallback-on-error behavior without logging or re-raising are not allowed.

7. **Error messages must include the failing input or identifier when safe to do so.**
   - Include values such as branch names, subsystem slugs, or doc names.
   - Do not include secrets, tokens, credentials, or private key material.

8. **Use one exception type per failure category.**
   - Examples:
     - path security failures → `PathTraversalError`
     - branch format failures → `InvalidBranchNameError`
     - doc resolution failures → `DocumentResolutionError`
   - Do not raise generic `ValueError` when a project-specific exception exists.

## Import and Module Organisation

1. **Group imports in this exact order.**
   1. Standard library
   2. Third-party packages
   3. First-party project imports
   - Separate groups with a single blank line.

2. **Import path validation from the shared module, not via local aliases.**
   - Use:
   ```python
   from path_security import validate_write_path
   ```
   - Do not redefine a wrapper such as `safe_write_path = validate_write_path` unless required by an interface boundary.

3. **Keep first-party imports rooted in the subsystem or shared package structure.**
   - Prefer explicit imports that show ownership.
   - Example:
   ```python
   from src.dtl.policy.evaluator import PolicyEvaluator
   ```
   - Do not use ambiguous relative chains when an absolute first-party path is available.

4. **Do not create circular imports between subsystem modules.**
   - If `src/dtl/...` and `src/mcp/...` need shared logic, move the shared logic into an approved shared module rather than importing each other bidirectionally.

5. **Keep UI accessibility identifiers defined close to the interactive element.**
   - Assign `.accessibilityIdentifier(...)` inline with the UI element declaration or via a local constant in the same view file.
   - Do not centralize unrelated identifiers into a single global string dump.

6. **Expose one clear public entrypoint per module.**
   - If a module exists to build branch names, expose `build_branch_name(...)` as the public function and prefix internal helpers with `_`.

7. **Keep test-only helpers inside the test tree unless used by production code.**
   - Fixtures, mocks, and data builders for tests belong under `tests/...`, not `src/...`.

## Comment and Documentation Rules

1. **Document every public function and class.**
   - Each public API must include a docstring describing:
     - purpose
     - parameters
     - return value
     - raised exceptions

2. **Do not use comments to restate obvious code.**
   - Remove comments like:
     - `# increment i`
     - `# validate the path`
   - Keep comments only when they explain a non-obvious constraint, TRD requirement, or security reason.

3. **Reference TRD-driven constraints in comments where the code would otherwise look arbitrary.**
   - Example acceptable comment:
   ```python
   # TRD: branch names must use pr-{N:03d} for deterministic sorting.
   ```

4. **When implementing required field shapes from the TRDs, keep the documented order in dataclass definitions.**
   - For the core entity, define fields in this order:
   ```python
   intent: str
   subsystem: str
   scope_statement: str
   branch_prefix: str
   relevant_docs: list[str]
   ```

5. **Use examples in docstrings for format-constrained values.**
   - For branch name builders and accessibility identifiers, include one valid example in the docstring.

6. **Write TODO comments only with a concrete next action.**
   - Required format:
     - `TODO(<owner>): <specific action>`
   - Example:
     - `TODO(consensus-agent): add retry budget metric to timeout path`
   - Do not leave bare `TODO` or `FIXME` comments.

7. **Keep test intent explicit in test names instead of long explanatory comments.**
   - Prefer:
     - `test_build_branch_name_rejects_non_zero_padded_pr_number`
   - Avoid adding a comment to explain a vague test name.

## ConsensusDevAgent-Specific Patterns

1. **Implement the core intent entity with the TRD-defined fields and semantics.**
   - The entity must include:
   ```python
   intent: str
   subsystem: str
   scope_statement: str
   branch_prefix: str
   relevant_docs: list[str]
   ```
   - `scope_statement` must be 2–3 sentences derived from docs.
   - `relevant_docs` must contain doc names, not raw doc contents.

2. **Construct `branch_prefix` from engineer ID and subsystem only.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem}`
   - Example:
     - `forge-agent/build/e17/dtl`

3. **Generate full branch names using the mandatory format and zero-padded PR numbers.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Required examples:
     - `pr-001-initialize-consensus-engine`
     - `pr-042-add-policy-cache`
   - `pr-7-title` is invalid.

4. **Normalize `title_slug` to lowercase kebab-case.**
   - Convert spaces and underscores to hyphens.
   - Remove characters that are not lowercase letters, digits, or hyphens.
   - Collapse repeated hyphens.

5. **Derive subsystem selection from approved docs, then map to approved source roots.**
   - If docs indicate `DTL`, code must be placed under `src/dtl/` and tests under `tests/dtl/`.
   - Apply the same rule for `cal`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, and `sdk/connector`.

6. **Follow the test generation minimum for every public API.**
   - Every public function and public class must have at least one test.
   - Every tested public API must include at minimum:
     - one happy-path test
     - one edge-case test
     - one error/failure-case test

7. **Use the required test frameworks by language.**
   - Python: `pytest`
   - TypeScript: `Jest`
   - Go: `go test`

8. **Use fixtures and parameterization for repetitive test cases.**
   - In Python, use `@pytest.fixture` and `@pytest.mark.parametrize` instead of manual loops across similar assertions.

9. **Mock all external I/O in tests.**
   - Mock:
     - API calls
     - filesystem operations
     - subprocess execution
   - Tests must not require network access, real file writes, or shelling out to system tools.

10. **Keep tests independent.**
    - Do not share mutable global state between tests.
    - Each test must set up and tear down its own data or use isolated fixtures.

11. **Apply path validation inside agent-driven code generation flows before emitting files.**
    - This includes generated:
      - source files
      - tests
      - snapshots
      - patches
      - temp output promoted into the repo

12. **Use accessibility identifiers on all interactive macOS UI elements produced by the subsystem.**
    - Apply `.accessibilityIdentifier()` to buttons, text fields, toggles, rows, and other interactive controls.
    - Follow:
      - `{module}-{component}-{role}-{context?}`
    - Examples:
      - `"settings-anthropic-key-test-button"`
      - `"stream-gate-yes-button-{gateId}"`

13. **Keep dynamic accessibility identifier context at the end of the identifier.**
    - Correct:
      - `"navigator-project-row-{projectId}"`
    - Incorrect:
      - `"navigator-{projectId}-project-row"`

14. **When generating tests or code from templates, preserve these conventions in the emitted output.**
    - Templates must emit:
      - correct file placement
      - required branch naming format
      - path validation before writes
      - required test coverage shape
      - accessibility identifiers for interactive macOS UI controls