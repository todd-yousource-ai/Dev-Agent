# Code Conventions - Forge Platform

## File and Directory Naming

1. Place implementation code only in approved subsystem roots:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`

2. Place tests under `tests/<subsystem>/` and mirror the source tree exactly.
   - Example: `src/dtl/policy/evaluator.py` → `tests/dtl/policy/test_evaluator.py`

3. Name Python source files in `snake_case`.
   - Use `consensus_runner.py`, not `ConsensusRunner.py` or `consensus-runner.py`

4. Name test files `test_<module>.py`.
   - Example: `test_path_security.py`

5. Keep one primary module responsibility per file.
   - Do not combine path validation, API transport, and domain models in the same file.

6. Store reusable dataclasses and DTO-style models in files named after the entity.
   - Example: `build_intent.py`, `consensus_result.py`

7. Name branch prefixes and actual working branches using the mandatory pattern:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example: `forge-agent/build/e123/consensusdevagent/pr-014-path-validation`

8. When persisting or generating files from user or agent input, validate the target path before any write.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)  # raises on traversal
   ```

9. Never write directly to a raw user-supplied path string.
   - Always write using the validated path object/value returned by `validate_write_path(...)`.

10. Keep subsystem-specific code inside its subsystem directory.
    - ConsensusDevAgent code must not be added to unrelated roots such as `src/dtl/` unless it is implementing DTL-specific behavior.

11. If a module owns a public API, place its tests in the mirrored path and ensure every public function and class has at least one test file reference.

## Class and Function Naming

1. Name classes in `PascalCase`.
   - Examples: `ConsensusPlanner`, `BuildIntent`, `PathValidationError`

2. Name functions and methods in `snake_case`.
   - Examples: `validate_write_path`, `build_scope_statement`, `run_consensus_round`

3. Name boolean-returning functions and predicates with explicit intent.
   - Prefer `is_valid_branch_name`, `has_required_docs`, `can_write_path`
   - Do not use vague names like `check_branch`

4. Name constants in `UPPER_SNAKE_CASE`.
   - Example: `TEST_GENERATION_SYSTEM`

5. Name dataclasses after the domain entity they represent.
   - Example: `BuildIntent`

6. For the Stage 1 core dataclass, preserve the documented field names exactly when implemented:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

7. Use noun names for data containers and verb names for actions.
   - Noun: `ConsensusResult`
   - Verb: `generate_tests`

8. Suffix custom exceptions with `Error`.
   - Examples: `PathTraversalError`, `ConsensusTimeoutError`

9. Name internal helper functions with a leading underscore only when they are module-private.
   - Example: `_normalize_subsystem_slug`

10. Use `axIdentifier` values for macOS interactive UI elements with the exact convention:
    - `{module}-{component}-{role}-{context?}`

11. Set `.accessibilityIdentifier(...)` on all interactive macOS UI elements.

12. Follow the documented `axIdentifier` format exactly for UI identifiers.
    - Valid examples:
      - `auth-touchid-button`
      - `auth-passcode-button`
      - `settings-anthropic-key-field`
      - `settings-anthropic-key-test-button`
      - `settings-anthropic-key-reveal-button`
      - `navigator-project-row-{projectId}`
      - `stream-gate-card-{gateId}`
      - `stream-gate-yes-button-{gateId}`
      - `stream-gate-skip-button-{gateId}`
      - `stream-gate-stop-button-{gateId}`

13. When an identifier refers to a specific record, include the stable record identifier in the trailing context segment.
    - Example: `navigator-project-row-42`

## Error and Exception Patterns

1. Raise exceptions immediately when path validation fails; do not sanitize and continue silently.

2. Validate paths before any file creation, overwrite, append, rename, move, or delete operation.

3. Use domain-specific exception classes for expected operational failures.
   - Examples:
     - `InvalidBranchNameError`
     - `MissingRelevantDocsError`
     - `PathTraversalError`

4. Include actionable context in exception messages.
   - Good: `Invalid branch name 'foo': expected forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Bad: `branch invalid`

5. Do not catch broad exceptions (`except Exception`) unless the block re-raises a domain-specific error with preserved context.

6. When wrapping exceptions, include the original exception as the cause.
   - Example:
   ```python
   try:
       safe_path = validate_write_path(path)
   except Exception as exc:
       raise PathTraversalError(f"Rejected write path: {path}") from exc
   ```

7. Use explicit failure paths for missing required TRD-derived data.
   - If `subsystem`, `scope_statement`, or `relevant_docs` cannot be derived, raise a named error instead of defaulting to empty values.

8. Return structured error results only at API boundaries; inside core logic, prefer raised exceptions.

9. Do not use magic sentinel values such as `None`, `False`, or `""` to represent parse or validation failures when an exception is required.

## Import and Module Organisation

1. Group imports in this order:
   1. Standard library
   2. Third-party packages
   3. Internal project imports

2. Separate each import group with a single blank line.

3. Use absolute imports for project modules when importing across subsystem boundaries.
   - Example: `from src.mcp.policy_engine import PolicyEngine`

4. Use local relative imports only for tightly coupled modules within the same package when already established by that package.

5. Import `validate_write_path` directly from `path_security` in every write path that accepts external input.
   - Required form:
   ```python
   from path_security import validate_write_path
   ```

6. Do not hide file-writing behavior inside utility modules without visible path validation at the write call site or an immediately adjacent helper.

7. Keep module top levels limited to declarations, constants, and pure setup.
   - Do not execute file writes, subprocesses, or network calls at import time.

8. Keep public exports explicit.
   - If a package exposes a stable API, define `__all__` or a dedicated package interface module.

9. Split large modules by responsibility before they exceed a single cohesive concern.
   - Example split:
     - `branch_naming.py`
     - `path_security.py`
     - `build_intent.py`
     - `test_generation.py`

10. Keep test dependencies isolated from production modules.
    - Production code must not import from `tests/`.

## Comment and Documentation Rules

1. Write comments only when they explain intent, invariants, or non-obvious constraints.
   - Do not comment obvious assignments or straightforward control flow.

2. Document every public function and class with a concise docstring stating:
   - what it does
   - its required inputs
   - what it returns or raises

3. In docstrings and comments, name TRD-derived invariants explicitly when they affect behavior.
   - Example: `Branch names must follow forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}.`

4. When code enforces a security requirement, add a brief comment naming the enforced rule.
   - Example:
   ```python
   # Security rule: validate paths before any write to prevent traversal.
   safe_path = validate_write_path(target_path)
   ```

5. Keep doc examples executable or near-executable.
   - Do not include pseudocode that diverges from the real API.

6. For dataclasses and structured entities derived from TRDs, keep field comments aligned with the documented meaning.
   - Example for `BuildIntent`:
   ```python
   @dataclass
   class BuildIntent:
       intent: str              # Raw operator intent
       subsystem: str           # Derived from docs
       scope_statement: str     # 2-3 sentence scope from docs
       branch_prefix: str       # forge-agent/build/{engineer_id}/{subsystem}
       relevant_docs: list[str] # Doc names from scope
   ```

7. When adding test modules, include a module-level comment or docstring only if it clarifies the external dependency being mocked or the behavior partition under test.

8. Do not use TODO comments without an owner or explicit next action.
   - Required format: `TODO(engineer_id): add traversal test for symlinked temp dirs`

## ConsensusDevAgent-Specific Patterns

1. Represent Stage 1 build-planning data as a dedicated dataclass, not a raw dictionary.

2. Implement the Stage 1 core entity with the documented fields and semantics:
   ```python
   @dataclass
   class BuildIntent:
       intent: str
       subsystem: str
       scope_statement: str
       branch_prefix: str
       relevant_docs: list[str]
   ```

3. Populate `branch_prefix` using the documented branch base:
   - `forge-agent/build/{engineer_id}/{subsystem}`

4. Generate the final branch name by extending the prefix to the mandatory full pattern:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

5. Validate generated branch names against the full naming convention before use in any git command, PR metadata, or artifact output.

6. Store relevant documentation references as `list[str]` containing document names, not mixed objects or ad hoc dictionaries.

7. Derive `scope_statement` as a 2–3 sentence summary from documentation; do not use bullet fragments or placeholder text.

8. Keep subsystem derivation explicit and deterministic.
   - If the subsystem cannot be derived from docs, fail with a named error.

9. Implement test generation to follow the required framework by language:
   - Python → `pytest`
   - TypeScript → `Jest`
   - Go → `go test`

10. Add at least one test for every public function and class.

11. For every public unit under test, include at minimum:
   - one happy-path test
   - one edge-case test
   - one error or failure-case test

12. Use fixtures and parametrization for repetitive test cases.

13. Mock all external I/O in tests, including:
   - API calls
   - file system access
   - subprocess execution

14. Keep tests independent.
   - Do not share mutable state across tests.

15. Do not let tests depend on execution order.

16. In ConsensusDevAgent code that writes generated files, enforce path validation immediately before the write operation, even if the path was previously validated upstream.

17. For generated macOS UI code in this subsystem, require `.accessibilityIdentifier(...)` on every interactive element before code is considered complete.

18. When generating identifiers for repeated UI elements, append the stable domain identifier in the `context` slot of the `axIdentifier` format.

19. Keep prompt constants and system instructions in named constants using `UPPER_SNAKE_CASE`.
   - Example: `TEST_GENERATION_SYSTEM`

20. Keep consensus, planning, and execution concerns in separate modules.
   - Example structure:
   ```text
   src/<subsystem>/planning/
   src/<subsystem>/consensus/
   src/<subsystem>/execution/
   ```

21. Do not store unvalidated operator intent directly in file paths, branch names, or module names.
   - Normalize and validate first, then format into the target convention.

22. When generating code or tests into mirrored directories, compute the destination path from the source tree shape, then validate the destination path before writing.