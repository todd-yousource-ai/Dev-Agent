# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place code only in approved subsystem directories.**
   - Use these exact roots:
     - `src/cal/` — Conversation Abstraction Layer
     - `src/dtl/` — Data Trust Label
     - `src/trustflow/` — TrustFlow audit stream
     - `src/vtz/` — Virtual Trust Zone
     - `src/trustlock/` — Cryptographic machine identity
     - `src/mcp/` — MCP Policy Engine
     - `src/rewind/` — Forge Rewind replay engine
     - `sdk/connector/` — Forge Connector SDK
   - Do not create alternate top-level subsystem directories.

2. **Mirror source structure exactly in tests.**
   - For any file under `src/<subsystem>/...`, place tests under `tests/<subsystem>/...` with matching nested directories.
   - Example:
     - Source: `src/dtl/policy/resolver.py`
     - Test: `tests/dtl/policy/test_resolver.py`

3. **Name Python source files in `snake_case`.**
   - Valid: `consensus_runner.py`, `path_security.py`
   - Invalid: `ConsensusRunner.py`, `consensus-runner.py`

4. **Name test files with a `test_` prefix.**
   - Use `test_<module>.py` for unit tests.
   - One module should generally map to one primary test file.

5. **Keep one primary responsibility per module file.**
   - If a file contains unrelated concepts, split it.
   - Example: separate `branch_naming.py` and `path_security.py`, not `utils.py`.

6. **Do not create generic catch-all filenames.**
   - Forbidden unless already established by framework constraints:
     - `helpers.py`
     - `misc.py`
     - `common.py`
     - `stuff.py`
     - `temp.py`

7. **Use branch names in the mandatory format.**
   - Exact pattern:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e17/consensusdevagent/pr-042-add-path-validation`

8. **Set `branch_prefix` values using the documented prefix only.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem}`
   - Do not include the PR number or title in `branch_prefix`.

9. **Use lowercase directory names for all new directories.**
   - Separate words with underscores only when needed for clarity.
   - Do not use spaces or camelCase in directory names.

10. **Store subsystem-specific tests only under `tests/<subsystem>/`.**
    - Do not place subsystem tests in a shared `tests/unit/` or `tests/integration/` root unless an existing test harness requires it.
    - If test type separation is needed, nest inside the mirrored path:
      - `tests/dtl/integration/...`

---

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Valid: `ConsensusPlanner`, `WritePathValidator`
   - Invalid: `consensusPlanner`, `consensus_planner`

2. **Name functions and methods in `snake_case`.**
   - Valid: `validate_write_path`, `build_branch_name`
   - Invalid: `validateWritePath`, `BuildBranchName`

3. **Name boolean-returning functions with an `is_`, `has_`, or `should_` prefix.**
   - Valid: `is_safe_path`, `has_consensus`, `should_retry`
   - Invalid: `safe_path`, `consensus_ready`

4. **Name exception classes with an `Error` suffix.**
   - Valid: `PathTraversalError`, `ConsensusTimeoutError`
   - Invalid: `PathTraversalException`, `ConsensusTimeout`

5. **Use domain-specific names taken from TRDs for core entities.**
   - Use exact field names from the core dataclass where applicable:
     - `intent`
     - `subsystem`
     - `scope_statement`
     - `branch_prefix`
     - `relevant_docs`
   - Do not rename these to synonyms like `goal`, `area`, `scope`, or `docs`.

6. **Name public functions with explicit verbs.**
   - Valid: `validate_write_path`, `derive_scope_statement`, `load_relevant_docs`
   - Invalid: `scope_statement`, `docs_for_scope`

7. **Avoid abbreviated names unless the abbreviation is a documented subsystem name.**
   - Allowed: `dtl`, `vtz`, `mcp`
   - Avoid: `cfg`, `mgr`, `util`, `svc`

8. **Suffix factory functions with their output when construction intent is not obvious.**
   - Valid: `build_consensus_plan`, `create_stage_entity`
   - Avoid ambiguous names like `build` or `create`

9. **Name constants in `UPPER_SNAKE_CASE`.**
   - Example:
     - `TEST_GENERATION_SYSTEM`
   - Do not use lowercase module constants for values intended to be imported elsewhere.

10. **Treat any non-underscored function or class as public and test it.**
    - If it is not intended to be public, prefix it with a single underscore.

---

## Error and Exception Patterns

1. **Validate paths before any write operation.**
   - Every write using a user-supplied or externally-derived path must call `validate_write_path` first.
   - Required pattern:
     ```python
     from path_security import validate_write_path

     safe_path = validate_write_path(user_supplied_path)
     ```
   - Do not write to the original unvalidated path variable after validation.

2. **Use the validated path variable for all subsequent file operations.**
   - Valid:
     ```python
     safe_path = validate_write_path(output_path)
     safe_path.write_text(content)
     ```
   - Invalid:
     ```python
     safe_path = validate_write_path(output_path)
     output_path.write_text(content)
     ```

3. **Raise specific exceptions, never bare `Exception`.**
   - Define or use a domain error type that communicates the failure cause.
   - Invalid:
     ```python
     raise Exception("bad path")
     ```

4. **Include actionable context in exception messages.**
   - Messages must identify the operation and the offending value or entity.
   - Valid:
     - `"refused write outside workspace: {path}"`
     - `"invalid branch name format: {branch_name}"`

5. **Catch exceptions only at boundaries where you can add context or recover.**
   - Allowed:
     - API boundary
     - CLI entrypoint
     - worker loop
     - task orchestration layer
   - Do not wrap internal logic in broad `try/except` blocks that only log and continue.

6. **Do not swallow exceptions.**
   - Every caught exception must be:
     - re-raised,
     - wrapped with additional context, or
     - converted to a structured failure result.

7. **Preserve original exceptions when adding context.**
   - Use exception chaining.
   - Pattern:
     ```python
     try:
         ...
     except OSError as exc:
         raise PathWriteError(f"failed to write file: {safe_path}") from exc
     ```

8. **Use `ValueError` for invalid caller-provided values only when no project-specific error exists.**
   - Prefer a named project exception for branch parsing, scope derivation, path validation, and consensus execution failures.

9. **Return structured results for expected decision outcomes; raise exceptions for invariant violations.**
   - Example:
     - “consensus not reached” may be a result state
     - “malformed stage entity” should be an exception

10. **Never perform destructive recovery silently.**
    - Do not auto-delete, overwrite, truncate, or rename files after an error unless the function name and docstring explicitly state that behavior.

---

## Import and Module Organisation

1. **Group imports in this order, with one blank line between groups.**
   1. Standard library
   2. Third-party packages
   3. First-party project modules

2. **Sort imports alphabetically within each group.**
   - Keep import ordering stable to minimize diff noise.

3. **Import from the most specific module available.**
   - Prefer:
     ```python
     from path_security import validate_write_path
     ```
   - Avoid:
     ```python
     import path_security
     ```

4. **Do not use wildcard imports.**
   - Forbidden:
     ```python
     from module import *
     ```

5. **Keep module-level side effects out of import time.**
   - Do not perform file writes, network calls, subprocess execution, or environment mutation during import.

6. **Limit a module to one clearly defined domain area.**
   - If a module needs names from multiple unrelated subsystems, move orchestration logic into a higher-level module.

7. **Put shared constants near the domain that owns them.**
   - Example:
     - Keep `TEST_GENERATION_SYSTEM` with test generation logic, not in a global constants dump file.

8. **Do not create circular imports to share types.**
   - If two modules need each other’s types, extract shared protocols, dataclasses, or enums into a separate dependency-neutral module.

9. **Use explicit re-exports only in intentional package APIs.**
   - If `__init__.py` re-exports symbols, keep the list minimal and stable.
   - Do not use `__init__.py` to hide chaotic internal structure.

10. **Separate boundary modules from pure logic modules.**
    - Boundary modules handle filesystem, subprocess, API, or UI interaction.
    - Pure logic modules contain parsing, transformation, validation, and decision logic.
    - Mock only the boundary modules in tests.

---

## Comment and Documentation Rules

1. **Write comments only when they add information not obvious from code.**
   - Valid uses:
     - documenting invariants
     - explaining a non-obvious TRD-driven rule
     - warning about boundary conditions
   - Do not restate the next line of code.

2. **Reference the governing TRD when implementing a mandated behavior.**
   - Use short references in comments or docstrings.
   - Example:
     - `# TRD-2 §8.3.1: every public function must have at least one test`

3. **Document all public classes and functions with a concise docstring.**
   - Include:
     - purpose
     - key inputs
     - return value or side effects
     - raised exceptions if non-obvious

4. **Document any function that writes to disk with its path validation behavior.**
   - The docstring must state that the path is validated via `validate_write_path` before writing.

5. **Do not use TODO without an owner or tracking reference.**
   - Valid:
     - `TODO(e17, PR-042): replace temporary branch slug parser with shared validator`
   - Invalid:
     - `TODO: fix this later`

6. **Use examples in docstrings for strict formatting rules.**
   - Required for:
     - branch naming
     - accessibility identifier formatting
     - path validation usage

7. **Keep line comments above the code they apply to.**
   - Avoid end-of-line comments except for short, critical clarifications.

8. **When defining accessibility identifiers, include the naming convention in nearby comments if generated dynamically.**
   - Required convention:
     - `{module}-{component}-{role}-{context?}`
   - Example values:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`

9. **Set `.accessibilityIdentifier()` on all interactive UI elements.**
   - Every button, field, row, toggle, or other interactive element must have an identifier.
   - Use the exact convention from TRD-1 §13.1.

10. **Do not leave commented-out code in committed files.**
    - Remove it or replace it with a tracked TODO reference if the intent must be preserved.

---

## ConsensusDevAgent-Specific Patterns

1. **Represent the core stage entity using the documented field names exactly.**
   - Required fields:
     - `intent: str`
     - `subsystem: str`
     - `scope_statement: str`
     - `branch_prefix: str`
     - `relevant_docs: list[str]`
   - Do not rename or omit these fields in the primary planning dataclass.

2. **Populate `subsystem` from documentation-derived terminology, not ad hoc labels.**
   - Use names like `DTL`, `Payments`, or other doc-backed subsystem names.
   - Do not infer casual aliases that do not appear in project docs.

3. **Generate `scope_statement` as 2–3 sentences only.**
   - Do not use bullets, fragments, or a single oversized paragraph.

4. **Store only document names in `relevant_docs`.**
   - Use identifiers or filenames from scope analysis.
   - Do not place full document contents, summaries, or paths in this field unless the owning type explicitly requires paths.

5. **Set `branch_prefix` before branch creation and derive full branch names from it.**
   - `branch_prefix` must equal:
     - `forge-agent/build/{engineer_id}/{subsystem}`
   - Full branch names must append:
     - `/pr-{N:03d}-{title_slug}`

6. **Validate generated branch names against the mandatory pattern before use.**
   - Reject names that do not match:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

7. **Keep test generation prompts in a named constant called `TEST_GENERATION_SYSTEM`.**
   - If the subsystem emits or consumes the standard test prompt, use that exact constant name.

8. **Enforce minimum public API test coverage from TRD-2 §8.3.1.**
   - Every public function and class must have at least one test.
   - Each public unit must cover:
     - one happy path
     - one edge case
     - one error/failure case minimum

9. **Use `pytest` for Python tests in this subsystem.**
   - Use fixtures and `@pytest.mark.parametrize` for repetitive cases.
   - Do not duplicate near-identical test bodies across inputs.

10. **Mock all external I/O in tests.**
    - Required mocking targets:
      - API calls
      - filesystem access
      - subprocess execution
    - Tests must not depend on network availability, shared mutable state, or real external services.

11. **Keep tests independent.**
    - No test may rely on execution order, global mutable state, or artifacts created by another test.

12. **Separate pure consensus logic from agent execution side effects.**
    - Parsing intent, selecting docs, deriving scope, and formatting branch names must be implemented in pure functions or side-effect-free classes.
    - File writes, subprocess calls, and branch creation belong in boundary adapters.

13. **Validate any file path produced from intent, doc names, branch names, or generated output before writing.**
    - Derived paths are not implicitly safe just because they were generated internally.

14. **Use accessibility identifiers for any macOS shell UI owned by the subsystem.**
    - Apply `.accessibilityIdentifier()` to every interactive element using:
      - `{module}-{component}-{role}-{context?}`

15. **When generating dynamic accessibility identifiers, keep the stable semantic parts first and the variable context last.**
    - Valid:
      - `stream-gate-yes-button-{gateId}`
      - `navigator-project-row-{projectId}`
    - Invalid:
      - `{gateId}-stream-gate-yes`
      - `button-stream-{gateId}-yes`