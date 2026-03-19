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
   - Example:
     - Source: `src/dtl/label_parser.py`
     - Test: `tests/dtl/test_label_parser.py`

3. Name Python source files in `snake_case`.
   - Use `consensus_runner.py`, not `ConsensusRunner.py` or `consensus-runner.py`.

4. Name test files `test_<source_file>.py`.
   - Example: `policy_engine.py` → `test_policy_engine.py`

5. Keep one primary module responsibility per file.
   - Do not combine unrelated concerns such as path validation, API transport, and result formatting in the same file.

6. Store shared path-handling utilities in a dedicated module rather than reimplementing validation inline.

7. Do not write files outside repository-approved directories unless the path has been validated first.

8. Before **any** file write using a user-supplied or derived path, call `validate_write_path()` and use only the returned path.
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   with open(safe_path, "w", encoding="utf-8") as f:
       f.write(content)
   ```

9. Do not concatenate untrusted path segments manually for write targets.
   - Invalid: `open("output/" + user_name + ".txt", "w")`
   - Required: build the path, validate it, then write.

10. Use branch names in this exact format:
    `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
    - Example: `forge-agent/build/e17/consensusdevagent/pr-042-add-vote-timeout`

11. For build-planning metadata, set `branch_prefix` to:
    `forge-agent/build/{engineer_id}/{subsystem_slug}`

12. Use subsystem slugs that match the directory naming convention where possible.
    - Example: `dtl`, `mcp`, `rewind`, `connector`

---

## Class and Function Naming

1. Name classes in `PascalCase`.
   - Example: `ConsensusCoordinator`, `VoteAggregationResult`

2. Name functions and methods in `snake_case`.
   - Example: `collect_votes()`, `validate_consensus_state()`

3. Name boolean-returning functions with a predicate verb.
   - Preferred: `is_terminal_state()`, `has_conflict()`, `can_retry()`

4. Name constants in `UPPER_SNAKE_CASE`.
   - Example: `TEST_GENERATION_SYSTEM`, `DEFAULT_RETRY_LIMIT`

5. Name dataclasses as domain entities, not containers.
   - Preferred: `BuildIntent`, `ConsensusDecision`
   - Avoid: `BuildIntentData`, `ConsensusDecisionObject`

6. Preserve TRD-defined field names exactly when implementing documented dataclasses.
   - Example fields:
     - `intent`
     - `subsystem`
     - `scope_statement`
     - `branch_prefix`
     - `relevant_docs`

7. Use suffixes consistently by responsibility:
   - `...Error` for exceptions
   - `...Result` for returned aggregate outcomes
   - `...Request` / `...Response` for transport models
   - `...Config` for configuration objects
   - `...Client` for external service wrappers

8. Public functions and classes must remain externally testable and must have at least one test each.

9. Do not abbreviate domain names unless the abbreviation is already the canonical subsystem name.
   - Allowed: `dtl`, `mcp`, `vtz`
   - Avoid: `cfg`, `mgr`, `util` in public API names

10. Name internal helper functions with a leading underscore only when they are module-private.
    - Example: `_normalize_vote_payload()`

11. For UI accessibility identifiers, use this exact format:
    `{module}-{component}-{role}-{context?}`

12. Apply `.accessibilityIdentifier()` to **all interactive elements**.

13. Accessibility identifier examples to follow:
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

14. When an identifier includes an entity id, append it as the final segment.
    - Correct: `stream-gate-yes-button-{gateId}`
    - Incorrect: `stream-{gateId}-yes-button`

---

## Error and Exception Patterns

1. Raise typed exceptions, not generic `Exception`.
   - Preferred: `raise PathValidationError(path)`
   - Avoid: `raise Exception("bad path")`

2. Name custom exceptions with the `Error` suffix.
   - Example: `ConsensusTimeoutError`, `InvalidVoteError`

3. Raise immediately when `validate_write_path()` rejects a path; do not catch and continue with a fallback unvalidated path.

4. Do not suppress file-write validation errors.
   - Invalid pattern:
     ```python
     try:
         safe_path = validate_write_path(path)
     except Exception:
         safe_path = path
     ```

5. Include actionable context in exception messages:
   - operation being performed
   - entity identifier if applicable
   - rejected state or input

6. Do not include secrets, API keys, or full credential values in exception messages.

7. Convert external library errors into subsystem-specific exceptions at module boundaries.
   - Example: wrap HTTP client failures in `ConsensusProviderError`

8. Use one error path per failure mode.
   - Validation failure → validation exception
   - Timeout → timeout exception
   - External dependency failure → provider/client exception

9. Return structured result objects for expected domain outcomes; raise exceptions only for invalid state, invariant violation, or failed external operations.

10. In tests, assert the specific exception type and a stable message fragment.

---

## Import and Module Organisation

1. Group imports in this order:
   1. Python standard library
   2. Third-party packages
   3. First-party project modules

2. Separate each import group with a single blank line.

3. Prefer explicit imports over wildcard imports.
   - Allowed: `from path_security import validate_write_path`
   - Forbidden: `from path_security import *`

4. Import from the owning subsystem module directly when possible.
   - Preferred: `from src.mcp.policy_engine import PolicyEngine`

5. Keep module dependencies directed inward by responsibility.
   - Shared utilities may be imported by subsystems.
   - Subsystems must not import unrelated peer implementation internals casually.

6. Do not create circular imports to share constants or types.
   - Move shared definitions into a dedicated shared module.

7. Keep external I/O isolated behind thin client or gateway modules so tests can mock them cleanly.

8. Put test fixtures close to the tests that use them unless reused across multiple modules.
   - Reusable fixtures belong in the nearest `conftest.py`.

9. Mock all external I/O in tests:
   - API calls
   - file system operations
   - subprocess execution

10. Tests must be independent and must not rely on shared mutable state.

---

## Comment and Documentation Rules

1. Write comments only when they explain intent, invariants, or non-obvious constraints.
   - Do not comment obvious syntax or restate the code.

2. Document every public module, class, and function with a concise docstring.

3. In docstrings, describe:
   - purpose
   - inputs
   - return value
   - raised exceptions when non-obvious

4. Keep comments and docstrings synchronized with current behavior; update or delete stale comments in the same change that alters behavior.

5. When implementing behavior derived from a TRD, reference the TRD section in the docstring or nearby comment.
   - Example: `Implements TRD-2 §8.3.1 test generation constraints.`

6. Do not leave placeholder comments such as:
   - `# TODO: handle later`
   - `# fix this`
   - `# temporary`
   Replace them with a tracked issue reference if work is deferred.

7. Use examples in documentation only when they match real naming and path conventions from this repository.

8. For accessibility-related UI code, include identifiers in code exactly as shipped; do not describe them abstractly in comments without setting them in the view.

---

## ConsensusDevAgent-Specific Patterns

1. Treat all operator-provided paths, filenames, and output targets as untrusted input.

2. Validate paths before **any** write in ConsensusDevAgent flows, including:
   - patch output
   - generated test files
   - temporary artifacts
   - logs written from user-directed locations
   - exported plans or reports

3. Use this exact safe-write pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(target_path)
   with open(safe_path, "w", encoding="utf-8") as f:
       f.write(payload)
   ```

4. When generating tests, enforce these minimums for every public function and class:
   - at least one test exists
   - happy path is covered
   - one edge case is covered
   - one error/failure case is covered

5. Use `pytest` for Python tests, `Jest` for TypeScript tests, and `go test` for Go tests.

6. Use fixtures and parametrization for repetitive test scenarios instead of copy-pasting similar tests.

7. Mock all external I/O in generated and handwritten tests.

8. Ensure generated tests are independent and order-insensitive.

9. When producing build-planning entities, include these fields exactly:
   - `intent: str`
   - `subsystem: str`
   - `scope_statement: str`
   - `branch_prefix: str`
   - `relevant_docs: list[str]`

10. Populate `subsystem` from documentation-derived subsystem names, not from ad hoc user wording.

11. Write `scope_statement` as 2–3 sentences derived from relevant docs; do not use bullet fragments.

12. Populate `relevant_docs` with document names used to derive scope; do not leave it empty if scope was doc-derived.

13. Generate branch names only from the mandatory convention:
    `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

14. Zero-pad PR numbers to exactly 3 digits.
    - Correct: `pr-007-fix-vote-merge`
    - Incorrect: `pr-7-fix-vote-merge`

15. Slugify titles to lowercase hyphenated text with no spaces or underscores.
    - Correct: `improve-consensus-retry`
    - Incorrect: `Improve_Consensus_Retry`

16. When generating UI code for the macOS application shell, assign `.accessibilityIdentifier()` on every interactive control before completing the task.

17. Build accessibility identifiers from stable domain context, not display text.
    - Preferred: `settings-anthropic-key-test-button`
    - Avoid: `settings-click-here-button`

18. For row-, card-, or entity-specific interactive elements, include the domain entity id as the final identifier segment.

19. Do not merge code that adds public API without corresponding tests.

20. Do not merge code that writes files through unvalidated paths.