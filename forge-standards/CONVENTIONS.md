# Code Conventions - Forge Platform

## File and Directory Naming

1. Place production code only in approved subsystem roots:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`

2. Place tests under `tests/<subsystem>/` and mirror the production tree exactly.
   - Example:
     - `src/dtl/policy/engine.py`
     - `tests/dtl/policy/test_engine.py`

3. Name Python source files in `snake_case`.
   - Valid: `consensus_runner.py`
   - Invalid: `ConsensusRunner.py`, `consensus-runner.py`

4. Name test files `test_<module>.py`.
   - Valid: `test_consensus_runner.py`

5. Keep one primary responsibility per module file. Do not combine unrelated subsystem concerns in the same file.
   - Valid: `src/mcp/policy/evaluator.py`
   - Invalid: `src/mcp/policy_and_audit_utils.py`

6. Store subsystem-specific helpers inside that subsystem’s directory, not in cross-subsystem “misc” or “utils” buckets.
   - Valid: `src/trustflow/serialization/event_encoder.py`
   - Invalid: `src/common/misc.py`

7. Do not create directories whose names differ from the approved subsystem slug.
   - Valid: `src/dtl/`
   - Invalid: `src/data_trust_label/`

8. Name branch prefixes using the build convention exactly:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example: `forge-agent/build/e17/consensusdevagent/pr-042-add-vote-aggregator`

9. When a dataclass or module represents build pipeline intent metadata, keep `branch_prefix` values in the form:
   - `forge-agent/build/{engineer_id}/{subsystem}`
   - Do not append PR title text to `branch_prefix`; append it only to full branch names.

10. Do not write to any user-supplied path before validating it.
    Use this exact pattern before every file write where a path came from input, config, environment, request payload, CLI argument, or external document:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Perform validation before opening, creating, renaming, copying, or deleting files.

11. Treat derived output paths as untrusted if any segment originates from external input. Validate the final resolved write path, not just the original segment.

12. Keep generated artifacts in subsystem-owned output directories; do not emit files into repository root.

## Class and Function Naming

1. Name Python classes in `PascalCase`.
   - Valid: `ConsensusPlanner`, `BuildIntent`

2. Name Python functions and methods in `snake_case`.
   - Valid: `collect_votes`, `validate_scope_statement`

3. Name dataclasses as nouns describing the entity they model.
   - Valid: `BuildIntent`, `ConsensusResult`
   - Invalid: `BuildIntentProcessor`

4. Name functions with a verb-first pattern describing the action they perform.
   - Valid: `generate_test_plan`, `load_relevant_docs`, `apply_vote_threshold`

5. Public function names must be specific to subsystem behavior; do not use generic names like `process`, `handle`, `run`, or `execute` without a subsystem qualifier.
   - Valid: `run_consensus_round`, `process_operator_intent`
   - Invalid: `run`, `process`

6. Name boolean-returning functions and boolean fields with affirmative prefixes:
   - `is_`
   - `has_`
   - `can_`
   - `should_`

7. Name exception classes with the `Error` suffix.
   - Valid: `ConsensusTimeoutError`, `PathValidationError`

8. Name pytest fixtures in `snake_case` and by the resource they provide.
   - Valid: `build_intent`, `mock_vote_store`

9. Name constants in `UPPER_SNAKE_CASE`.
   - Valid: `TEST_GENERATION_SYSTEM`

10. Do not abbreviate subsystem names in public class or function names unless the subsystem directory itself is the abbreviation from the standards.
    - Valid inside `src/dtl/`: `LabelPolicy`
    - Invalid: `LblPlcy`

11. For Swift/macOS interactive UI elements, set `.accessibilityIdentifier()` on every interactive control using this exact pattern:
    - `{module}-{component}-{role}-{context?}`
    - Examples:
      - `auth-touchid-button`
      - `settings-anthropic-key-field`
      - `navigator-project-row-{projectId}`
      - `stream-gate-yes-button-{gateId}`

12. Keep accessibility identifier segments lowercase and hyphen-separated. Do not use spaces, underscores, or camelCase in identifiers.

## Error and Exception Patterns

1. Raise typed exceptions, never bare `Exception`.
   - Valid: `raise ConsensusValidationError("missing scope statement")`
   - Invalid: `raise Exception("bad input")`

2. Create subsystem-local exception classes when the caller can recover differently based on failure type.
   - Example categories:
     - validation
     - timeout
     - external service failure
     - path security failure
     - consensus mismatch

3. Include the failing entity and reason in every exception message.
   - Valid: `"branch name 'foo' does not match forge-agent/build/... format"`

4. Validate inputs at the boundary of every public API.
   - Validate:
     - required fields
     - enum-like values
     - branch format
     - subsystem slug
     - path safety before write

5. Fail before performing side effects.
   - Example order:
     1. validate request
     2. validate path
     3. prepare content
     4. write file

6. Convert external library exceptions into project-defined exceptions at subsystem boundaries.
   - Valid: catch HTTP client timeout and raise `ConsensusBackendTimeoutError`

7. Never swallow exceptions with empty `except` blocks.
   - Invalid:
     ```python
     try:
         write_output()
     except:
         pass
     ```

8. When catching and re-raising, preserve the original exception using `from`.
   ```python
   try:
       safe_path = validate_write_path(path)
   except ValueError as exc:
       raise PathValidationError(f"invalid write path: {path}") from exc
   ```

9. Return structured error data only at transport boundaries; inside core logic, use exceptions for failure flow.

10. Do not use exceptions for expected branch decisions when a boolean or typed result object is sufficient.

## Import and Module Organisation

1. Group imports in this order with one blank line between groups:
   1. standard library
   2. third-party packages
   3. local project imports

2. Within each group, sort imports alphabetically by module path.

3. Import from the narrowest stable module that owns the symbol.
   - Valid: `from src.dtl.policy.engine import PolicyEngine`
   - Invalid: `from src.dtl import *`

4. Do not use wildcard imports.

5. Keep modules acyclic across subsystem boundaries. If two subsystems need each other, extract the shared contract into a lower-level shared module owned by one side.

6. Keep transport, orchestration, domain logic, and persistence in separate modules.
   - Example split:
     - `api.py` for request handling
     - `service.py` for orchestration
     - `models.py` for dataclasses/types
     - `repository.py` for storage

7. Do not place test-only helpers in production modules. Store them under `tests/<subsystem>/helpers/` or fixtures in `conftest.py`.

8. Keep external I/O wrappers isolated behind modules that can be mocked in tests.
   - Examples:
     - API client wrappers
     - file system writer modules
     - subprocess adapters

9. If a module performs file writes, centralize path validation in that module before any write operation.

10. Keep public module APIs explicit with named exports; do not rely on incidental imports from sibling modules.

## Comment and Documentation Rules

1. Write docstrings for every public class and public function.

2. In docstrings, document:
   - purpose
   - required inputs
   - return value
   - raised exceptions for non-obvious failure modes

3. Do not restate the function name in comments.
   - Invalid: `# Increment the counter`
   - Valid: `# Counter is persisted only after quorum to avoid partial state`

4. Write comments only for:
   - non-obvious invariants
   - security constraints
   - protocol assumptions
   - workaround rationale
   - cross-document traceability

5. When implementing behavior derived from a TRD, include the TRD identifier in a nearby comment or docstring.
   - Example:
     ```python
     # TRD-2-Consensus-Engine 8.3.1: public APIs require happy, edge, and failure tests.
     ```

6. Keep comments adjacent to the code they constrain. Do not place block comments far from the logic they describe.

7. Update comments and docstrings in the same change when behavior changes. Do not leave stale documentation.

8. Use examples in docstrings only when the call shape or data format is non-obvious.

9. For UI automation identifiers, include the exact `axIdentifier` string format in the view code near `.accessibilityIdentifier()` assignment when the context segment is dynamic.

## ConsensusDevAgent-Specific Patterns

1. Model operator/build intent as a dataclass with these fields when representing Stage 1 core intent:
   - `intent: str`
   - `subsystem: str`
   - `scope_statement: str`
   - `branch_prefix: str`
   - `relevant_docs: list[str]`

2. Populate `subsystem` from documentation-derived scope, not from free-form user wording when both are available.

3. Keep `scope_statement` to 2–3 sentences sourced from relevant docs; do not store an unconstrained paragraph dump.

4. Fill `relevant_docs` with document names only. Do not place full document contents in this field.

5. Generate `branch_prefix` exactly as:
   - `forge-agent/build/{engineer_id}/{subsystem}`
   Store the full PR branch name separately if needed.

6. Any code that creates or validates build branches must enforce the mandatory full branch format:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

7. Validate branch components separately before concatenation:
   - `engineer_id`
   - `subsystem_slug`
   - zero-padded PR number
   - title slug

8. In ConsensusDevAgent test generation, use:
   - `pytest` for Python
   - `Jest` for TypeScript
   - `go test` for Go

9. Add at least one test for every public function and public class.

10. For each public function/class test set, include at minimum:
    - one happy path case
    - one edge case
    - one error or failure case

11. Use `pytest` fixtures and `@pytest.mark.parametrize` for repetitive Python test cases.

12. Mock all external I/O in tests, including:
    - API calls
    - file system access
    - subprocess execution

13. Keep tests independent. Do not share mutable global state across tests.

14. When a ConsensusDevAgent component writes generated files, validate the destination path before writing using:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```

15. In file-writing code paths, use the validated path object/value returned by `validate_write_path`; do not continue using the original unvalidated string.

16. Structure ConsensusDevAgent modules so planning, consensus evaluation, document filtering, and artifact writing are separate units with independently testable public APIs.

17. For generated tests, assert behavior, not implementation details, unless the implementation detail is itself the contract.

18. When testing error paths, assert the specific project-defined exception type, not only the message text.

19. If a ConsensusDevAgent module invokes subprocesses or external models, isolate that call behind an adapter interface and mock the adapter in unit tests.

20. Do not permit any write path derived from prompt text, repo metadata, CLI flags, or agent messages without `validate_write_path` being called in the same code path before the write.