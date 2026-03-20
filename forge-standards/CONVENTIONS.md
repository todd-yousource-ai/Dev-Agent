# Code Conventions - Forge Platform

## File and Directory Naming

1. Place implementation code only in the approved subsystem roots:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`

2. Place tests under `tests/<subsystem>/` and mirror the source tree exactly.
   - Example: `src/dtl/policy/engine.py` → `tests/dtl/policy/test_engine.py`
   - Example: `sdk/connector/client.ts` → `tests/connector/client.test.ts`

3. Name Python modules in `snake_case`.
   - Valid: `path_security.py`, `consensus_runner.py`
   - Invalid: `PathSecurity.py`, `consensus-runner.py`

4. Name TypeScript files in `kebab-case` or `*.test.ts` for tests, and do not mix styles inside the same directory.
   - Valid: `consensus-engine.ts`, `consensus-engine.test.ts`

5. Name Go packages and directories in lowercase, with no underscores unless matching an external protocol or generated code requirement.

6. Prefix test files with `test_` for Python and suffix with `.test.ts` for TypeScript.
   - Python: `test_validator.py`
   - TypeScript: `validator.test.ts`

7. Do not create catch-all filenames such as `utils.py`, `helpers.py`, `common.py`, or `misc.ts` unless the directory scope is already highly specific and the file contains only functionality for that scope.
   - Prefer `path_validator.py` over `utils.py`

8. Keep one primary responsibility per module. If a file defines unrelated concepts, split it.
   - Example: separate `branch_naming.py` and `write_path_guard.py`

9. Name dataclass/model files after the entity they define.
   - Valid: `build_intent.py`, `scope_plan.py`

10. For files implementing the Build Pipeline core dataclass fields, use names that match the domain terms from the TRD.
    - Example: `intent_record.py` for fields like `intent`, `subsystem`, `scope_statement`, `branch_prefix`, `relevant_docs`

11. Store subsystem-specific fixtures under the mirrored test subtree, not in a global dump folder.
    - Valid: `tests/dtl/fixtures/policy_inputs.json`

12. Keep accessibility-related UI code grouped by feature and ensure any file containing interactive macOS UI components uses identifiers following the project axIdentifier format.

13. Do not write to user-supplied paths directly. Any module that writes files based on external input must import and use:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```

14. Apply path validation before **any** write operation, including:
    - file creation
    - overwrite
    - append
    - temp artifact generation in user-selected directories
    - export/import output paths
    - generated test output paths

15. Do not hide write-path validation inside unrelated helpers. Use a clearly named function or inline validation at the write site.

## Class and Function Naming

1. Name Python classes in `PascalCase`.
   - Valid: `ConsensusPlanner`, `BuildIntent`, `WritePathGuard`

2. Name Python functions and methods in `snake_case`.
   - Valid: `generate_tests`, `validate_branch_name`, `load_relevant_docs`

3. Name TypeScript classes and interfaces in `PascalCase`.

4. Name TypeScript functions in `camelCase`.
   - Valid: `generateTests`, `validateWritePath`

5. Name Go exported identifiers in `PascalCase` and unexported identifiers in `camelCase`, following standard Go visibility.

6. Name boolean-returning functions with an explicit predicate form.
   - Prefer `is_valid_branch_name`, `has_required_docs`, `can_write_to_path`
   - Avoid `branch_ok`, `docs`, `writeable`

7. Name validation functions with the `validate_` prefix only when they raise or return a structured validation result.
   - Use `validate_write_path()` when it raises on invalid input
   - Use `is_safe_path()` only for pure boolean checks

8. Name factory functions with `build_`, `create_`, or `make_` based on output semantics.
   - `build_branch_prefix()` for derived strings
   - `create_test_fixture()` for object/fixture creation

9. Name functions that perform external side effects with a verb that makes the effect obvious.
   - `write_manifest`, `run_subprocess`, `fetch_consensus_votes`
   - Avoid vague names like `process`, `handle`, `execute` without context

10. Public APIs must use domain vocabulary from Forge and the subsystem TRDs.
    - Prefer `subsystem`, `scope_statement`, `relevant_docs`, `branch_prefix`
    - Avoid synonyms like `area`, `summary`, or `documents` for these fields

11. Every public function and public class must be testable as a standalone unit and must have at least one test.

12. For macOS interactive UI elements, set `.accessibilityIdentifier()` using this exact pattern:
    ```text
    {module}-{component}-{role}-{context?}
    ```

13. Use lowercase hyphen-separated segments for all accessibility identifiers.
    - Valid: `auth-touchid-button`
    - Valid: `settings-anthropic-key-test-button`
    - Valid: `navigator-project-row-123`

14. Include a stable context suffix in accessibility identifiers when rendering repeated entities.
    - Use IDs such as project ID or gate ID:
      - `stream-gate-card-{gateId}`
      - `stream-gate-yes-button-{gateId}`

15. Apply accessibility identifiers to **all** interactive macOS UI elements, not only buttons.
    - Include buttons, text fields, toggles, selectors, rows, and actionable cards

## Error and Exception Patterns

1. Raise specific exceptions for validation failures; do not raise bare `Exception`.

2. When rejecting a user-supplied write path, let `validate_write_path()` raise or wrap its failure in a project-specific exception that preserves the original cause.

3. Validate before side effects. Do not start a write, subprocess, network call, or DB mutation and then validate required preconditions afterward.

4. Use guard clauses at the top of functions for:
   - invalid paths
   - malformed branch names
   - missing required docs
   - unsupported subsystem names
   - empty operator intent when intent is required

5. Include the invalid value and the rule name in exception messages when safe to do so.
   - Good: `Invalid branch name 'foo/bar': must match forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

6. Do not swallow filesystem, subprocess, or API exceptions. Either:
   - re-raise them unchanged, or
   - wrap them in a subsystem-specific error with contextual fields

7. When wrapping exceptions, keep the original exception as the cause.
   - Python:
     ```python
     raise BuildArtifactWriteError(f"Failed to write manifest to {safe_path}") from exc
     ```

8. Return structured error data for expected validation outcomes at API boundaries; raise exceptions for programmer errors and failed invariants inside the subsystem.

9. Do not use sentinel values such as `None`, `False`, or empty string to represent detailed failure states when the caller needs the reason.

10. Any branch-name validation must enforce this exact mandatory format:
    ```text
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

11. Reject branch names with:
    - missing `forge-agent/build/` prefix
    - non-slug subsystem segments
    - PR numbers not zero-padded to 3 digits
    - missing title slug
    - spaces or uppercase letters in slug segments

12. If a subsystem is derived from documentation, raise an error when the derived subsystem does not map cleanly to the allowed directory/subsystem naming.

## Import and Module Organisation

1. Group imports in this order:
   1. standard library
   2. third-party packages
   3. first-party Forge modules

2. Separate each import group with a single blank line.

3. Do not use wildcard imports.

4. Import from the narrowest module that owns the symbol.
   - Prefer `from path_security import validate_write_path`
   - Avoid importing a broad package root just to access one function

5. Any module performing writes from external input must explicitly import `validate_write_path` in that module. Do not rely on transitive wrappers unless the wrapper’s name clearly indicates path validation.

6. Keep module top-level code side-effect free.
   - Allowed: constant definitions, lightweight dataclass declarations
   - Not allowed: network calls, file writes, subprocess execution, environment mutation

7. Organize modules so domain models, validators, I/O, and orchestration are separate files when each exceeds trivial size.
   - Example split:
     - `models/build_intent.py`
     - `validation/branch_name.py`
     - `io/manifest_writer.py`
     - `orchestration/consensus_runner.py`

8. Avoid circular imports by moving shared contracts into dedicated model or protocol modules.

9. Co-locate tests with the mirrored subsystem path and keep test support code in that subtree.
   - Example: `tests/mcp/policy/conftest.py`

10. Keep language-specific test frameworks consistent with the TRD:
    - Python: `pytest`
    - TypeScript: `Jest`
    - Go: `go test`

11. Mock all external I/O in tests:
    - API calls
    - filesystem operations
    - subprocesses

12. Keep tests independent; do not share mutable global state across test cases.

## Comment and Documentation Rules

1. Write comments only when they capture intent, invariant, security rationale, or non-obvious constraints.

2. Do not write comments that restate the code.
   - Avoid: `# increment counter`
   - Prefer: `# Retry counter is capped at 3 to match upstream API backoff policy`

3. Every public class and public function must have a docstring or language-equivalent documentation comment describing:
   - purpose
   - inputs
   - outputs
   - raised errors or failure conditions

4. In modules that validate paths or branch names, document the exact enforced format or security constraint in the docstring.

5. For Build Pipeline dataclasses, document each field using the TRD terminology exactly where possible:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

6. If a function derives values from TRD-defined conventions, reference the convention by name in the docstring.
   - Example: “Builds a branch prefix using the mandatory Forge agent branch naming convention.”

7. Keep inline TODO comments actionable and scoped.
   - Valid: `TODO(consensus): add malformed vote payload case once schema v2 lands`
   - Invalid: `TODO: improve this`

8. Remove resolved TODOs in the same change that resolves them.

9. For macOS UI code, add comments only when the accessibility identifier’s context source is not obvious.
   - Example: explain why `{gateId}` is stable if derived from a backing model rather than display order

10. Include example values in docs when a format is strict.
    - Branch names
    - accessibility identifiers
    - validated path usage

## ConsensusDevAgent-Specific Patterns

1. Represent operator/build intent in a dedicated dataclass or typed model that includes, at minimum:
   - `intent: str`
   - `subsystem: str`
   - `scope_statement: str`
   - `branch_prefix: str`
   - `relevant_docs: list[str]`

2. Name that model after the domain concept, such as `BuildIntent` or `ConsensusBuildIntent`; do not use generic names like `Data` or `Payload`.

3. Populate `branch_prefix` using the TRD-defined pattern:
   ```text
   forge-agent/build/{engineer_id}/{subsystem_slug}
   ```

4. When constructing a full branch name, append the PR/title suffix using:
   ```text
   /pr-{N:03d}-{title_slug}
   ```

5. Validate branch names before creating branches, writing branch metadata, or invoking CI workflows.

6. Derive `subsystem` from documentation scope and map it to an approved subsystem slug before using it in:
   - branch names
   - directory paths
   - test paths
   - generated artifacts

7. Store `relevant_docs` as document names/identifiers from scope discovery, not raw document blobs.

8. Keep consensus orchestration code separate from document parsing and artifact writing.
   - Example split:
     - `doc_scope_parser.py`
     - `consensus_vote_aggregator.py`
     - `artifact_writer.py`

9. Any artifact writer in ConsensusDevAgent must validate the destination path immediately before write, even if the path was validated earlier upstream.

10. Generated tests must satisfy all of the following minimums:
    - use `pytest` for Python, `Jest` for TypeScript, `go test` for Go
    - include at least one test for every public function and class
    - cover one happy path, one edge case, and one error/failure case
    - use fixtures and parametrization for repetitive cases
    - mock all external I/O
    - remain independent with no shared mutable state

11. When generating tests, mirror the source structure exactly under `tests/<subsystem>/`.

12. Name generated test cases after observable behavior, not implementation detail.
    - Good: `test_validate_write_path_rejects_traversal`
    - Bad: `test_internal_flag_set`

13. Keep consensus result objects deterministic.
    - Do not depend on unordered map iteration for vote summaries, artifact ordering, or emitted diagnostics.

14. When serializing consensus artifacts, use stable field ordering and stable filenames so repeated runs with identical inputs produce identical outputs.

15. Separate pure decision logic from side-effectful execution.
    - Pure modules: scope derivation, branch-name formatting, vote aggregation
    - Side-effect modules: file writes, API calls, subprocess runs

16. In tests for ConsensusDevAgent, explicitly cover:
    - path traversal rejection on write paths
    - branch naming conformance
    - subsystem-to-directory mapping
    - behavior when `relevant_docs` is empty or incomplete
    - failure propagation from external I/O

17. Do not allow a consensus flow to proceed with unresolved required inputs. Validate and fail fast before starting downstream generation or writes.