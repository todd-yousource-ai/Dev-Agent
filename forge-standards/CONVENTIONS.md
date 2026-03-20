# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place code only in approved subsystem roots.**  
   Use these directories exactly:
   - `src/cal/` for Conversation Abstraction Layer
   - `src/dtl/` for Data Trust Label
   - `src/trustflow/` for TrustFlow audit stream
   - `src/vtz/` for Virtual Trust Zone
   - `src/trustlock/` for cryptographic machine identity
   - `src/mcp/` for MCP Policy Engine
   - `src/rewind/` for Forge Rewind
   - `sdk/connector/` for Connector SDK
   - `tests/<subsystem>/` for tests

2. **Mirror source structure exactly under `tests/`.**  
   If implementation is `src/dtl/policy/evaluator.py`, the test file must be under `tests/dtl/policy/test_evaluator.py`.

3. **Name Python modules in `snake_case`.**  
   Valid: `path_security.py`, `consensus_runner.py`  
   Invalid: `PathSecurity.py`, `consensus-runner.py`

4. **Name test files `test_<module>.py`.**  
   Valid: `test_consensus_runner.py`  
   Invalid: `consensus_runner_test.py`

5. **Keep one primary responsibility per module.**  
   If a file defines unrelated concerns, split it. Example: do not combine path validation and LLM prompt building in one module.

6. **Store subsystem-specific helpers under that subsystem, not in shared roots.**  
   Example: a DTL parser belongs in `src/dtl/...`, not `src/common/...`, unless it is used by 3 or more subsystems and has no subsystem-specific imports.

7. **Use `branch_prefix` values that match the mandatory branch naming convention.**  
   All generated branch names must follow:  
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

8. **Set `branch_prefix` to the stable prefix only.**  
   For planning objects, use:  
   `forge-agent/build/{engineer_id}/{subsystem_slug}`  
   Append `/pr-{N:03d}-{title_slug}` only when creating the concrete branch.

9. **Keep title slugs lowercase and hyphenated.**  
   Valid: `fix-path-validation`  
   Invalid: `FixPathValidation`, `fix_path_validation`

10. **Do not write generated artifacts outside validated project paths.**  
    Before any file creation, overwrite, rename, or deletion, validate the destination path with `validate_write_path`.

11. **Validate every user-supplied or model-generated write path before use.**  
    Required pattern:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Never pass raw paths directly to `open()`, `Path.write_text()`, `shutil`, or similar write APIs.

12. **Do not bypass path validation for “internal” paths.**  
    If the path originates from CLI args, config, prompts, task plans, PR metadata, or generated code actions, treat it as untrusted and validate it.

---

## Class and Function Naming

1. **Name classes in `PascalCase`.**  
   Valid: `ConsensusPlanner`, `BuildIntent`, `PathSecurityError`

2. **Name functions and methods in `snake_case`.**  
   Valid: `validate_write_path`, `build_scope_statement`, `run_consensus_round`

3. **Name constants in `UPPER_SNAKE_CASE`.**  
   Valid: `TEST_GENERATION_SYSTEM`, `DEFAULT_TIMEOUT_SECONDS`

4. **Use noun names for dataclasses that represent persisted or passed state.**  
   Valid: `BuildIntent`, `ScopePlan`, `ConsensusDecision`

5. **Use verb names for functions that perform actions.**  
   Valid: `generate_tests`, `apply_patch`, `collect_relevant_docs`

6. **Suffix boolean-returning functions with intent-revealing predicates when possible.**  
   Prefer `is_valid_path`, `has_pending_changes`, `should_retry`.

7. **Name exceptions with an `Error` suffix.**  
   Valid: `PathTraversalError`, `ConsensusTimeoutError`

8. **Do not abbreviate subsystem names in class names unless the subsystem directory uses that abbreviation officially.**  
   Valid: `DtlLabelResolver` inside `src/dtl/...`  
   Invalid: `TLResolver` for TrustLock unless the abbreviation is already standardized

9. **Match dataclass field names to TRD terminology exactly where specified.**  
   Use these field names when implementing the Stage 1 core entity:
   - `intent`
   - `subsystem`
   - `scope_statement`
   - `branch_prefix`
   - `relevant_docs`

10. **Preserve declared field semantics in code comments and serialization keys.**  
    Do not rename `scope_statement` to `scope` in JSON, DTOs, or templates unless there is an explicit adapter layer.

11. **Use descriptive suffixes for UI accessibility identifiers in Swift/macOS code.**  
    Follow the format:  
    `{module}-{component}-{role}-{context?}`

12. **Apply `.accessibilityIdentifier()` to every interactive SwiftUI/AppKit control.**  
    Required examples:
    - `auth-touchid-button`
    - `settings-anthropic-key-field`
    - `settings-anthropic-key-test-button`
    - `navigator-project-row-{projectId}`
    - `stream-gate-yes-button-{gateId}`

13. **Include runtime identifiers in `axIdentifier` strings only as the final segment.**  
    Valid: `navigator-project-row-1234`  
    Invalid: `navigator-1234-project-row`

---

## Error and Exception Patterns

1. **Raise specific exceptions, never bare `Exception`.**  
   Define or reuse typed errors for:
   - path traversal / invalid write path
   - document resolution failure
   - consensus timeout
   - invalid branch name
   - unsupported subsystem

2. **Validate before mutating state.**  
   Perform all path, branch name, and input checks before writing files, creating branches, or spawning subprocesses.

3. **Fail closed on path validation.**  
   If `validate_write_path` raises, stop the write immediately and propagate or convert to a typed application error.

4. **Do not catch and ignore file-system or subprocess errors.**  
   Either:
   - re-raise unchanged, or
   - wrap in a subsystem-specific `...Error` with the original exception attached

5. **Preserve the original exception when wrapping.**  
   Use:
   ```python
   try:
       ...
   except OSError as exc:
       raise ConsensusWorkspaceError("failed to write workspace file") from exc
   ```

6. **Include actionable context in exception messages.**  
   Message must include the operation and target.  
   Valid: `failed to write plan file: tests/dtl/policy/test_evaluator.py`

7. **Never include secrets in exception messages.**  
   Do not log or raise API keys, tokens, passcodes, or raw auth headers.

8. **Return structured error results only at process boundaries.**  
   Inside modules, prefer exceptions. Convert to CLI/API error payloads only in the top-level handler.

9. **Treat validation failures as first-class test cases.**  
   Every public validator must have tests for:
   - valid input
   - one edge input
   - one invalid input

10. **When a branch name does not match the mandatory format, raise immediately.**  
    Validate against:  
    `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

---

## Import and Module Organisation

1. **Group imports in this order with one blank line between groups:**
   1. standard library
   2. third-party packages
   3. local application imports

2. **Sort imports alphabetically within each group.**

3. **Do not use wildcard imports.**  
   Invalid: `from path_security import *`

4. **Import path validation directly in every module that performs writes.**  
   Required:
   ```python
   from path_security import validate_write_path
   ```
   Do not rely on callers to have validated the path already.

5. **Keep modules acyclic within a subsystem whenever possible.**  
   If two modules import each other, extract the shared contract or utility into a third module.

6. **Keep CLI/process-boundary code separate from domain logic.**  
   CLI entrypoints may parse args and render output; business rules belong in subsystem modules.

7. **Do not place test-only helpers in production modules.**  
   Put fixtures, factories, and mocks under `tests/` or test support packages.

8. **One module should expose one clear public surface.**  
   If a module is intended for reuse, define its public API explicitly with stable function/class names and avoid leaking internal helpers.

9. **Name internal helpers with a leading underscore only when they are truly module-private.**  
   Do not use underscore prefixes for functions imported across modules.

10. **Keep external I/O behind thin adapter modules.**  
    API clients, file-system writers, and subprocess runners should live in dedicated modules so tests can mock them cleanly.

---

## Comment and Documentation Rules

1. **Write comments only for intent, invariants, or non-obvious constraints.**  
   Do not comment on syntax-obvious operations.

2. **Document every public function and class with a concise docstring.**  
   Include:
   - what it does
   - required inputs
   - raised exceptions for invalid input or failed writes

3. **When implementing TRD-defined structures or conventions, reference the exact TRD term in the docstring or adjacent comment.**  
   Example: mention `branch_prefix` or `scope_statement` exactly as defined.

4. **Do not restate type information in comments.**  
   Invalid: `# branch_prefix is a string`

5. **Add comments above any code that enforces a security boundary.**  
   Required for path validation, secret redaction, and branch-name validation.

6. **Keep comments synchronized with behavior.**  
   When changing validation rules, update the comment/docstring in the same commit.

7. **Use examples in documentation for generated formats.**  
   For branch names and accessibility identifiers, include one valid example in the docstring or module docs.

8. **For UI accessibility identifiers, document the exact identifier string near the view definition.**  
   Example:
   ```swift
   // axIdentifier: settings-anthropic-key-test-button
   Button("Test Key") { ... }
       .accessibilityIdentifier("settings-anthropic-key-test-button")
   ```

9. **Do not leave TODO comments without an owner and condition.**  
   Format:  
   `TODO(<engineer_id>): remove after branch name validator is shared by CLI and API`

10. **Use module-level documentation for subsystem boundaries.**  
    If a module defines a boundary such as “filesystem writes” or “consensus orchestration,” state that at the top of the file.

---

## ConsensusDevAgent-Specific Patterns

1. **Represent the Stage 1 core entity as a dataclass with the exact TRD fields.**  
   Minimum shape:
   ```python
   @dataclass
   class BuildIntent:
       intent: str
       subsystem: str
       scope_statement: str
       branch_prefix: str
       relevant_docs: list[str]
   ```

2. **Populate `subsystem` from documentation-derived scope, not free-form user text.**  
   Normalize to approved subsystem names/slugs before using it in paths or branch names.

3. **Generate `scope_statement` as 2–3 sentences only.**  
   Do not store bullet lists or raw prompt fragments in this field.

4. **Store `relevant_docs` as document names only.**  
   Do not place raw document bodies, URLs, or summaries in `relevant_docs`.

5. **Derive `branch_prefix` before any branch creation logic runs.**  
   Use the format:  
   `forge-agent/build/{engineer_id}/{subsystem_slug}`

6. **Validate the final branch name before checkout or push.**  
   Final branch must be:  
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

7. **Pad PR numbers to exactly three digits.**  
   Valid: `pr-001-add-tests`  
   Invalid: `pr-1-add-tests`, `pr-0001-add-tests`

8. **Use lowercase subsystem slugs in branch names.**  
   Valid: `dtl`, `trustflow`, `mcp`  
   Invalid: `DTL`, `TrustFlow`

9. **Generate tests for every public function and class.**  
   Minimum required coverage per public API:
   - one happy path
   - one edge case
   - one error/failure case

10. **Use the project-standard test framework per language.**
    - Python: `pytest`
    - TypeScript: `Jest`
    - Go: `go test`

11. **Use fixtures and parameterization for repetitive test cases.**  
    In Python, prefer `@pytest.fixture` and `@pytest.mark.parametrize` over duplicated setup.

12. **Mock all external I/O in tests.**  
    This includes:
    - API calls
    - file system writes/reads when not explicitly testing FS integration
    - subprocess execution

13. **Keep tests independent.**  
    Do not share mutable global state, temporary directories, environment mutations, or singleton configuration across tests without reset logic.

14. **Write explicit tests for path validation on all write-capable code paths.**  
    Each file-writing public function must have a test proving it calls `validate_write_path` before writing.

15. **Use adapter boundaries to make ConsensusDevAgent code testable.**  
    Separate:
    - planning
    - branch naming
    - file writes
    - subprocess/git execution
    - document retrieval

16. **Do not embed prompt text inline in business logic if it is reused.**  
    Store reusable prompt/system text in named constants such as `TEST_GENERATION_SYSTEM`.

17. **Name reusable prompt constants in `UPPER_SNAKE_CASE` and keep them immutable.**  
    Valid: `TEST_GENERATION_SYSTEM`

18. **When code generates tests, enforce language-specific output placement.**  
    Generated Python tests must be written under `tests/<subsystem>/...` mirroring the source path exactly.

19. **When generating or modifying files, validate every destination path individually.**  
    Do not validate only the parent directory and assume child paths are safe.

20. **Before any automated write sequence, compute all target paths, then validate all of them.**  
    Abort the entire operation if any single path fails validation.

21. **Do not let ConsensusDevAgent write directly from raw model output.**  
    Parse generated plans, filenames, and patch targets into structured fields, validate them, then write.

22. **Expose branch naming and path validation through dedicated helper functions.**  
    Do not duplicate regexes or traversal checks across planner, executor, and CLI modules.

23. **Add regression tests for every bug involving traversal, branch formatting, or test placement.**  
    The regression test name must state the prevented behavior, e.g. `test_rejects_parent_traversal_in_generated_test_path`.

24. **For macOS UI generated by the subsystem, assign accessibility identifiers during view construction, not afterward.**  
    The `.accessibilityIdentifier()` call must be in the same declaration block as the interactive control.

25. **Use identifier templates for repeated UI rows and actions.**  
    Examples:
    - `navigator-project-row-{projectId}`
    - `stream-gate-card-{gateId}`
    - `stream-gate-stop-button-{gateId}`