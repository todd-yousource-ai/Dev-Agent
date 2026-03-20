# Code Conventions - Forge Platform

## File and Directory Naming

1. Place source files under the canonical subsystem directory only:
   - `src/cal/` for Conversation Abstraction Layer
   - `src/dtl/` for Data Trust Label
   - `src/trustflow/` for TrustFlow audit stream
   - `src/vtz/` for Virtual Trust Zone
   - `src/trustlock/` for cryptographic machine identity
   - `src/mcp/` for MCP Policy Engine
   - `src/rewind/` for Forge Rewind
   - `sdk/connector/` for Connector SDK code

2. Place tests under `tests/<subsystem>/` and mirror the source tree exactly.
   - Example: `src/dtl/policy/engine.py` → `tests/dtl/policy/test_engine.py`

3. Name Python source files in `snake_case.py`.

4. Name TypeScript source files in `kebab-case.ts` or `kebab-case.tsx`. Do not mix casing styles within the same package.

5. Name Go source files in `snake_case.go`. Name Go test files with `_test.go`.

6. Prefix Python test files with `test_`.
   - Example: `test_consensus_runner.py`

7. Keep one primary module responsibility per file. If a file name requires `and`, split the file.
   - Bad: `parser_and_validator.py`
   - Good: `parser.py`, `validator.py`

8. Do not create generic top-level directories such as `misc/`, `helpers/`, `temp/`, or `utils/`. Create a domain-specific directory instead.
   - Bad: `src/utils/retry.py`
   - Good: `src/mcp/retry_policy.py`

9. Store subsystem-specific fixtures under the matching mirrored test path.
   - Example: `tests/trustflow/events/fixtures/`

10. Name branch prefixes from build metadata as:
    - `forge-agent/build/{engineer_id}/{subsystem_slug}`

11. Name branches exactly with the mandatory format:
    - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
    - Example: `forge-agent/build/e17/consensus-dev-agent/pr-042-add-path-validation`

12. Use lowercase hyphenated `subsystem_slug` values in branch names, even if the source directory uses a shorter canonical alias.

13. Do not write generated, staged, or exported files to a user-supplied path until the path has been validated.
    Use:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```

14. Call `validate_write_path(...)` immediately before any write operation that uses a path originating outside the current function, including:
    - CLI arguments
    - API request fields
    - environment-derived paths
    - config file paths
    - agent-produced file paths

15. Never concatenate path segments manually for a write target if any segment is user- or agent-supplied. Validate the final resolved path before opening the file.

## Class and Function Naming

1. Name Python classes in `PascalCase`.

2. Name Python functions and methods in `snake_case`.

3. Name TypeScript classes, React components, and exported types in `PascalCase`.

4. Name TypeScript functions, variables, and object properties in `camelCase`, except when matching an external API contract.

5. Name Go exported identifiers in `PascalCase` and unexported identifiers in `camelCase`.

6. Name booleans as predicates:
   - Prefix with `is_`, `has_`, `can_` in Python
   - Prefix with `is`, `has`, `can` in TypeScript and Go

7. Name functions after the action they perform, not the abstraction level.
   - Bad: `handle_data()`
   - Good: `parse_consensus_vote()`

8. Name functions returning collections in plural form.
   - Example: `load_relevant_docs()`, `list_candidate_branches()`

9. Name functions that may raise on invalid input with a validating verb.
   - Example: `validate_write_path()`, `parse_stage_intent()`

10. For dataclasses and structured plan objects, use field names exactly as defined by the build pipeline contract when representing the Stage 1 core entity:
    - `intent`
    - `subsystem`
    - `scope_statement`
    - `branch_prefix`
    - `relevant_docs`

11. Do not alias or rename the Stage 1 contract fields in serializers, DTOs, or persistence models unless an adapter layer performs explicit mapping.

12. Suffix adapter classes with their integration target.
    - Example: `AnthropicClient`, `GitHubStatusAdapter`, `PathSecurityAdapter`

13. Suffix exception types with `Error`.
    - Example: `ConsensusResolutionError`

14. Prefix test functions with `test_` and describe behavior, condition, and expected result.
    - Example: `test_resolve_votes_when_quorum_met_returns_consensus()`

15. Name accessibility identifiers using:
    - `{module}-{component}-{role}-{context?}`
    Set them on all interactive UI elements via `.accessibilityIdentifier()`.

16. Use lowercase hyphen-separated accessibility identifiers only.
    - Good: `settings-anthropic-key-test-button`
    - Bad: `SettingsAnthropicKeyTestButton`

17. Include stable entity context in accessibility identifiers for repeated interactive elements.
    - Examples:
      - `navigator-project-row-{projectId}`
      - `stream-gate-yes-button-{gateId}`

## Error and Exception Patterns

1. Raise specific exception types. Do not raise bare `Exception`.

2. Define subsystem-specific exception classes in a local `errors` module when three or more call sites need to distinguish the same failure mode.
   - Example: `src/cal/errors.py`

3. Use exception names that describe the failing invariant, not the symptom.
   - Bad: `RequestFailedError`
   - Good: `ConsensusQuorumNotMetError`

4. Include actionable context in exception messages:
   - the operation
   - the identifier or path involved
   - the violated rule or expected state

5. Do not include secrets, API keys, tokens, or full credential-bearing URLs in exception messages or logs.

6. Convert external library exceptions at the subsystem boundary into project-defined error types.
   - Example: catch SDK transport errors in `src/mcp/` and raise `PolicyEvaluationError`

7. Validate write paths before raising file-write errors related to user- or agent-supplied destinations.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(target_path)
   ```

8. Raise validation errors before performing side effects. Do not partially write files and then validate afterward.

9. For batch operations, collect per-item failures and raise a summary error only after all independent items have been attempted, unless the operation contract is explicitly fail-fast.

10. In tests, assert the exception type and a stable fragment of the message.

11. When re-raising with added context, use exception chaining.
   - Python: `raise ConsensusPlanError("...") from err`

12. Return structured error results only when the public API contract requires non-throwing behavior. Do not mix ad hoc dict-based error returns with exceptions in the same layer.

## Import and Module Organisation

1. Group imports in this order:
   1. standard library
   2. third-party packages
   3. first-party project modules

2. Separate each import group with a single blank line.

3. Prefer absolute imports from the subsystem root over deep relative imports.
   - Good: `from src.dtl.policy.engine import PolicyEngine`
   - Bad: `from ...policy.engine import PolicyEngine`

4. Import only the symbols used in the file. Do not use wildcard imports.

5. Keep module-level side effects out of import time.
   - Do not open files, invoke subprocesses, fetch network resources, or mutate global state at import time.

6. Place shared exception types, DTOs, and protocol interfaces in dedicated modules:
   - `errors.py`
   - `models.py`
   - `protocols.py`
   - `types.py`
   Use only when the file contents match the name exactly.

7. Do not create a `utils` import sink. If a helper is domain-specific, place it in the domain module.
   - Example: `src/rewind/checkpoint_clock.py`, not `src/common/utils.py`

8. Keep one public responsibility per module. If imports form cycles, split the shared contract into a third module rather than using local imports as a permanent fix.

9. In test modules, import the public module under test first; patch collaborators at the boundary where I/O occurs.

10. Mock all external I/O in tests, including:
    - API calls
    - file system access
    - subprocess execution

11. Keep tests independent. Do not share mutable global fixtures across test files.

12. Use `pytest` for Python, `Jest` for TypeScript, and `go test` for Go.

13. Every public function and class must have at least one test.

14. For every public function and class, write at minimum:
    - one happy-path test
    - one edge-case test
    - one error/failure-case test

15. Use fixtures and parameterization for repeated test inputs rather than duplicating test bodies.

## Comment and Documentation Rules

1. Write comments only when the code cannot make the intent obvious through naming and structure.

2. Comment invariants, security constraints, and cross-document contract requirements directly above the relevant code.

3. When a function enforces path safety for writes, add a short comment stating that write paths must be validated before use.
   - Example:
   ```python
   # Validate externally supplied paths before any write.
   safe_path = validate_write_path(target_path)
   ```

4. Do not write comments that restate the next line of code.
   - Bad: `# increment i`
   - Good: comment why the increment must occur before retry backoff resets

5. Use docstrings on all public classes and public functions.

6. In docstrings for contract-bound objects, list field names exactly as required by the TRD or pipeline contract.

7. Document non-obvious parameter constraints in the docstring `Args` section.
   - Example: whether a path must already be validated, whether an identifier must be slug-safe

8. Document raised exceptions in public APIs when callers are expected to handle them.

9. Keep examples in docs synchronized with actual naming conventions:
   - branch names must use `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - accessibility identifiers must use `{module}-{component}-{role}-{context?}`

10. For TODO comments, include an owner and a triggering condition.
    - Format: `TODO(<owner>): <action> when <condition>`

11. Remove resolved TODOs in the same change that resolves them.

12. Do not leave commented-out code in committed files.

## ConsensusDevAgent-Specific Patterns

1. Represent the Stage 1 build intent entity with a typed structure whose field names match the contract exactly:
   - `intent: str`
   - `subsystem: str`
   - `scope_statement: str`
   - `branch_prefix: str`
   - `relevant_docs: list[str]`

2. Set `branch_prefix` to:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}`
   Do not include the PR suffix in this field.

3. When constructing a full branch name, append the PR segment to `branch_prefix` using:
   - `pr-{N:03d}-{title_slug}`

4. Validate that every generated branch name matches:
   - `^forge-agent/build/[^/]+/[^/]+/pr-\d{3}-[a-z0-9-]+$`
   Reject the branch name before any git operation if it does not match.

5. Derive `subsystem` from relevant documentation scope, using the canonical subsystem name from project docs. Do not infer a new subsystem label ad hoc in code.

6. Populate `relevant_docs` with document names, not file contents and not paths.

7. Keep `scope_statement` to 2–3 sentences when generating or storing Stage 1 planning data.

8. Any ConsensusDevAgent file generation flow must validate output paths immediately before write.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(output_path)
   ```

9. When the agent proposes file writes, store both the original proposed path and the validated resolved path in separate variables.
   - Example: `proposed_path`, `safe_output_path`

10. Do not pass unvalidated agent-produced paths into:
    - `open`
    - `Path.write_text`
    - `Path.write_bytes`
    - archive writers
    - template renderers that write to disk

11. For agent-generated tests, enforce the TRD test contract:
    - `pytest` for Python
    - `Jest` for TypeScript
    - `go test` for Go
    - at least one happy path, one edge case, and one failure case per public function/class
    - external I/O mocked
    - tests independent

12. When generating UI automation or macOS shell code, assign `.accessibilityIdentifier()` to every interactive element.

13. Build accessibility identifiers exactly as:
    - `{module}-{component}-{role}-{context?}`
    Examples:
    - `auth-touchid-button`
    - `settings-anthropic-key-field`
    - `settings-anthropic-key-test-button`
    - `settings-anthropic-key-reveal-button`
    - `navigator-project-row-{projectId}`
    - `stream-gate-card-{gateId}`
    - `stream-gate-yes-button-{gateId}`
    - `stream-gate-skip-button-{gateId}`
    - `stream-gate-stop-button-{gateId}`

14. For repeated UI elements, use stable business identifiers in accessibility IDs; do not use array indices.

15. When ConsensusDevAgent emits code patches, preserve mirrored test placement for every new public module added under `src/<subsystem>/`.

16. If a generated change introduces a new public function or class, include its tests in the same patch.

17. If a generated change adds external I/O behavior, include boundary mocks in the same patch’s tests.

18. Do not generate placeholder modules named `helpers`, `common_utils`, or `misc`; choose a domain-specific name tied to the subsystem capability.