# Code Conventions - Forge Platform

## File and Directory Naming

1. Place code only in the approved top-level subsystem directories:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`

2. Place tests under `tests/<subsystem>/` and mirror the source tree exactly.
   - Example:
     - Source: `src/mcp/policy/evaluator.py`
     - Test: `tests/mcp/policy/test_evaluator.py`

3. Do not create new top-level source directories without an approved TRD update.

4. Name Python modules with lowercase snake_case.
   - Use `policy_engine.py`, not `PolicyEngine.py` or `policy-engine.py`.

5. Name test files `test_<module>.py` for pytest discovery.
   - Example: `test_evaluator.py`

6. Keep one primary responsibility per module file.
   - If a file name requires `and`, split it into separate modules.

7. Store subsystem-specific helpers under that subsystem’s directory, not in shared miscellaneous folders.
   - Use `src/dtl/validators.py`
   - Do not use `src/common/misc.py` unless that directory is already defined and owned.

8. Name branch prefixes and working branches exactly as follows:
   - Prefix stored in build entities: `forge-agent/build/{engineer_id}/{subsystem_slug}`
   - Full branch name: `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

9. Use the TRD subsystem slug in directory, branch, and test paths consistently.
   - Example: `mcp` in `src/mcp/`, `tests/mcp/`, and `forge-agent/build/alex/mcp/pr-014-policy-cache`

10. Before writing any file derived from user input, validate the target path.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Never call file write APIs on an unvalidated user-supplied path.

---

## Class and Function Naming

1. Name Python classes with PascalCase.
   - Example: `ConsensusPlanner`, `BuildIntent`

2. Name Python functions and methods with snake_case.
   - Example: `derive_scope_statement()`, `validate_branch_name()`

3. Name boolean-returning functions with an `is_`, `has_`, `can_`, or `should_` prefix.
   - Example: `is_terminal_state()`, `has_conflicts()`

4. Name factory functions with a verb that describes construction.
   - Use `build_plan()`, `create_stage_context()`, or `load_entity()`
   - Do not use ambiguous names like `handle_data()`

5. Name exception classes with an `Error` suffix.
   - Example: `PathTraversalError`, `ConsensusTimeoutError`

6. Name dataclasses and DTO-style types as singular nouns.
   - Example: `BuildIntent`, `ScopeDocument`
   - Do not use plural names like `BuildIntents`

7. For the Stage 1 core dataclass, preserve the TRD field names exactly when implementing the entity:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

8. Use explicit subsystem prefixes only when a type would otherwise collide across subsystems.
   - Prefer `PolicyEvaluator`
   - Use `McpPolicyEvaluator` only if another `PolicyEvaluator` exists in the same import surface

9. Name public functions so their side effects are obvious.
   - Use `write_plan_file()` for disk writes
   - Use `fetch_consensus()` for network calls
   - Do not hide I/O behind names like `process_plan()`

10. Name accessibility identifiers using this exact pattern for all interactive UI elements:
    - `{module}-{component}-{role}-{context?}`

11. Set accessibility identifiers via `.accessibilityIdentifier()` on every interactive element.

12. Follow the TRD examples when composing accessibility identifiers:
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

13. When an identifier includes a dynamic value, append it at the end and preserve the static prefix unchanged.
    - Use `navigator-project-row-42`
    - Do not use `navigator-42-project-row`

---

## Error and Exception Patterns

1. Raise exceptions, do not return sentinel error values like `None`, `False`, or `"ERROR"` for failure paths.

2. Use the most specific exception type available. If no suitable built-in exception exists, define a project-specific exception with an `Error` suffix.

3. Include actionable context in every raised exception message.
   - Good: `raise ValueError(f"Invalid subsystem slug: {slug}")`
   - Bad: `raise ValueError("Invalid input")`

4. Validate external input at the boundary of the system.
   - Validate branch names when received
   - Validate subsystem slugs before path construction
   - Validate file paths before writes
   - Validate document lists before filtering

5. Perform path validation before any write, including:
   - file creation
   - overwrites
   - temp file writes
   - generated test output
   - exported reports

6. Use this exact write pattern for user-influenced paths:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(target_path)
   with open(safe_path, "w", encoding="utf-8") as f:
       f.write(contents)
   ```

7. Do not swallow exceptions from security checks.
   - If `validate_write_path()` raises, propagate it or wrap it with preserved cause.

8. When wrapping an exception, use `raise ... from exc` to keep the original traceback.
   ```python
   try:
       safe_path = validate_write_path(target_path)
   except Exception as exc:
       raise PathWriteError(f"Refused write to path: {target_path}") from exc
   ```

9. For public APIs, document the exceptions that callers are expected to handle.

10. Never catch broad `Exception` unless the block immediately re-raises a typed project exception with preserved cause.

---

## Import and Module Organisation

1. Group imports in this order:
   1. Standard library
   2. Third-party packages
   3. First-party Forge modules

2. Separate each import group with a single blank line.

3. Import modules from their owning subsystem path.
   - Example: `from src.mcp.policy.evaluator import PolicyEvaluator`
   - Do not re-home MCP code under unrelated subsystems for convenience.

4. Do not use wildcard imports.
   - Forbidden: `from src.dtl.labels import *`

5. Import only the symbols used by the file.

6. Avoid circular imports by moving shared contracts into a lower-level module owned by the same subsystem.
   - Example: move shared types to `src/trustflow/types.py`

7. Keep module-level side effects out of import time.
   - No network calls
   - No file writes
   - No subprocess execution
   - No environment mutation

8. Define constants in uppercase snake_case at module scope.
   - Example: `TEST_GENERATION_SYSTEM = """..."""`

9. Keep prompt or policy strings in named constants, not inline in business logic, when they are reused or versioned.

10. Store subsystem-local prompt constants in the owning subsystem module rather than duplicating text across files.

---

## Comment and Documentation Rules

1. Write comments only for intent, invariants, security constraints, or non-obvious decisions.
   - Do not comment restatements of the code.

2. Every public function and class must have a docstring.

3. Public docstrings must state:
   - what the function/class does
   - required inputs
   - return value or produced effect
   - raised exceptions that callers should expect

4. For functions that perform I/O, state the side effect explicitly in the first or second docstring line.
   - Example: `Writes the generated plan to disk after validating the path.`

5. For security-sensitive code, include a short invariant comment at the enforcement point.
   - Example:
     ```python
     # Security invariant: all user-influenced write targets must be validated first.
     safe_path = validate_write_path(target_path)
     ```

6. Keep inline comments on the line above the code they describe, not trailing at the end of dense statements.

7. When implementing behavior derived from a TRD, reference the TRD section in a concise comment near the constraint.
   - Example: `# TRD-2 §8.3.1: every public function requires tests.`

8. Do not leave commented-out code in committed files.

9. Update docstrings and comments in the same change that alters behavior.

10. When a dataclass field comes from a TRD-defined schema, preserve the field name and document it exactly once at the type definition.

---

## ConsensusDevAgent-Specific Patterns

1. Implement the Stage 1 core entity as a dataclass with these exact fields:
   - `intent: str`
   - `subsystem: str`
   - `scope_statement: str`
   - `branch_prefix: str`
   - `relevant_docs: list[str]`

2. Do not rename Stage 1 fields when mapping between planner, pipeline, and persistence layers.

3. Populate `branch_prefix` with exactly:
   `forge-agent/build/{engineer_id}/{subsystem_slug}`

4. Generate full branch names with exactly:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

5. Zero-pad PR numbers to 3 digits.
   - Use `pr-001`, `pr-014`, `pr-125`

6. Normalize `subsystem_slug` and `title_slug` to lowercase kebab-safe slugs before branch generation.

7. Validate generated branch names against the mandatory pattern before use in git commands.

8. Treat `relevant_docs` as the authoritative document filter input for downstream scoped retrieval.
   - Do not recompute a different document set in later stages without recording the reason.

9. Keep `scope_statement` to 2–3 sentences when generating it from source docs.

10. Derive `subsystem` from docs, using canonical names from the TRD or subsystem directory names.

11. Store test-generation instructions in a constant named `TEST_GENERATION_SYSTEM` when implementing the test generation subsystem behavior.

12. Enforce the TRD test minimums for every public function and class:
   - at least one test exists
   - happy path covered
   - one edge case covered
   - one error/failure case covered

13. Use `pytest` for Python tests in this subsystem.

14. Use fixtures and `@pytest.mark.parametrize` for repetitive Python test cases.

15. Mock all external I/O in tests:
   - API calls
   - file system access
   - subprocess calls

16. Keep tests independent. Do not share mutable state across tests.

17. When generating tests, place them in the mirrored `tests/<subsystem>/...` path for the source under test.

18. When generated tests write fixtures, snapshots, or temporary outputs based on dynamic names, validate the write path before creating them.

19. For any agent-produced file write, use a dedicated helper that validates the path before opening the file.

20. Prefer small, typed helper functions for branch formatting, scope derivation, doc filtering, and test path resolution over one large orchestration function.