# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place source files only in approved Forge directories.**
   - Use these top-level paths exactly:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`
     - `tests/<subsystem>/`
   - Do not create new top-level source directories for ConsensusDevAgent code.

2. **Mirror test paths exactly from source paths.**
   - A source file at `src/mcp/policy_loader.py` must have tests under `tests/mcp/`.
   - Preserve the same relative structure beneath the subsystem root.
   - Example:
     - Source: `src/cal/session/stream_parser.py`
     - Test: `tests/cal/session/test_stream_parser.py`

3. **Name Python files in `snake_case`.**
   - Allowed: `build_map_client.py`, `path_security.py`
   - Forbidden: `BuildMapClient.py`, `build-map-client.py`

4. **Name test files `test_<unit>.py`.**
   - Use the source module stem as `<unit>`.
   - Example:
     - `src/trustflow/audit_writer.py` → `tests/trustflow/test_audit_writer.py`

5. **Do not create generated dispatcher files.**
   - A generated file must implement real logic.
   - Forbidden patterns:
     - A file whose only purpose is to import another generated file and call it
     - A file containing only routing glue to another generated artifact
     - Template files with runtime placeholders

6. **Every generated file must be self-contained.**
   - Do not require `eval()`, `exec()`, or `importlib.import_module()` to load related generated files.
   - Use normal static imports only.

7. **Use mandatory branch naming for all ConsensusDevAgent work.**
   - Format exactly:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e17/consensus-dev-agent/pr-007-build-map-fallback`

8. **Use lowercase slash-delimited subsystem slugs in paths and branch names.**
   - Use directory names already standardized by Forge.
   - Do not invent alternate spellings for an existing subsystem.

## Class and Function Naming

1. **Use `PascalCase` for classes.**
   - Examples:
     - `ConsensusSession`
     - `BuildMapClient`
     - `PathValidationError`

2. **Use `snake_case` for functions, methods, and variables.**
   - Examples:
     - `fetch_build_map`
     - `validate_write_path`
     - `_strip_code_fences`

3. **Prefix internal helpers with a single leading underscore.**
   - Example:
     - `_normalize_branch_name`
     - `_strip_code_fences`
   - Do not use double underscore name-mangling for subsystem helpers.

4. **Keep `_strip_code_fences()` named exactly the same in every module that defines it.**
   - The function name must be `_strip_code_fences`.
   - Do not rename variants such as `_remove_code_fences`, `strip_code_block`, or `sanitize_fences`.

5. **Keep `_strip_code_fences()` behavior identical across all five modules.**
   - If one implementation changes, update all five in the same change set.
   - The function must:
     - Accept `""` or `None` and return it unchanged
     - Preserve a trailing newline on non-empty output
     - Leave code unchanged when there are no fences
     - Leave unicode characters unchanged
     - Remain synchronous

6. **Name exception classes with the `Error` suffix.**
   - Examples:
     - `PathTraversalError`
     - `BuildMapFetchError`
     - `ConsensusMismatchError`

7. **Use descriptive boolean names.**
   - Prefer:
     - `is_ready`
     - `has_build_map`
     - `should_retry`
   - Avoid vague names like `flag`, `done`, or `status_ok`.

8. **Use `axIdentifier` values with the exact format `{module}-{component}-{role}-{context?}` for interactive UI elements.**
   - Set via `.accessibilityIdentifier()`.
   - Examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`
     - `stream-gate-yes-button-{gateId}`

9. **Do not omit the contextual suffix when multiple interactive elements are repeated in a collection.**
   - Required:
     - `navigator-project-row-{projectId}`
     - `stream-gate-stop-button-{gateId}`
   - Forbidden:
     - `navigator-project-row`
     - `stream-gate-stop-button`

## Error and Exception Patterns

1. **Validate every user-supplied write path before any write operation.**
   - Call `validate_write_path()` before opening, creating, overwriting, moving, or deleting a file path derived from external input.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Do not pass raw user input directly to `open()`, `Path.write_text()`, `shutil.move()`, or similar APIs.

2. **Use the validated path object/value returned by `validate_write_path()`.**
   - After validation, write only to `safe_path`.
   - Do not validate one variable and then write using another equivalent-looking path string.

3. **Raise specific exceptions for contract violations; return `None` only for documented absence cases.**
   - Example:
     - `fetch_build_map()` must return `None` when no build map exists yet.
     - It must not raise an exception for that first-build state.

4. **Implement the build-map missing case exactly as a graceful absence path.**
   - `fetch_build_map()` must support the state where no map exists for the first 5 PRs of a build.
   - Tests must verify this using a case equivalent to `TestBuildMapLive`.

5. **Do not convert security validation failures into silent fallbacks.**
   - If `validate_write_path()` raises, allow the operation to fail explicitly or wrap and re-raise with subsystem context.
   - Do not continue with a best-effort write.

6. **Wrap external-system failures only when adding actionable context.**
   - Good:
     - `raise BuildMapFetchError(f"failed to fetch build map for build_id={build_id}") from exc`
   - Bad:
     - `raise Exception("failed")`

7. **Never use broad `except:` blocks.**
   - Catch explicit exception types.
   - If a catch-all is temporarily required at a process boundary, re-raise an `Error`-suffixed exception with the original exception chained.

## Import and Module Organisation

1. **Use only static imports.**
   - Forbidden:
     - `eval()`
     - `exec()`
     - `importlib.import_module()` for generated-file loading
   - Required:
     - normal `import` / `from ... import ...`

2. **Order imports in three groups, top to bottom.**
   - Standard library
   - Third-party packages
   - Local project imports
   - Separate groups with one blank line.

3. **Import from the owning subsystem module directly.**
   - Prefer:
     - `from src.mcp.policy_loader import PolicyLoader`
   - Avoid indirect barrel modules created only to re-export names.

4. **Do not create modules whose only purpose is dispatch.**
   - If a module exists, it must contain business logic, domain logic, or a stable interface implementation.
   - Remove one-line forwarding modules.

5. **Keep sanitization helpers local only when they are intentionally duplicated by TRD requirement.**
   - `_strip_code_fences()` is the exception: it may exist in multiple modules, but the source text and behavior must remain identical across all five.

6. **Keep module names aligned with a single responsibility.**
   - Good:
     - `build_map_client.py`
     - `path_security.py`
     - `consensus_reconciler.py`
   - Bad:
     - `helpers.py`
     - `misc_utils.py`
     - `stuff.py`

## Comment and Documentation Rules

1. **Write comments only for non-obvious intent, invariants, or TRD-driven behavior.**
   - Good comment:
     - `# Missing build map is expected for the first 5 PRs; return None instead of raising.`
   - Bad comment:
     - `# Increment counter`

2. **When behavior is mandated by TRD, state the invariant in code comments or docstrings at the decision point.**
   - Required for:
     - missing build-map handling
     - path validation before writes
     - `_strip_code_fences()` parity across five modules

3. **Document `_strip_code_fences()` with its exact contract in every module that defines it.**
   - The docstring or adjacent comment must state:
     - returns `None` and `""` unchanged
     - preserves trailing newline on non-empty output
     - leaves unfenced code unchanged
     - leaves unicode unchanged
     - is synchronous

4. **Use examples in docs only when they match enforced formats exactly.**
   - For branch names, show the full mandatory pattern.
   - For `axIdentifier`, use `{module}-{component}-{role}-{context?}` examples only.

5. **Do not leave TODOs without an owner or condition.**
   - Allowed:
     - `# TODO(e17): replace mock build-map source after live endpoint rollout`
   - Forbidden:
     - `# TODO: fix later`

6. **Do not use comments as substitutes for missing validation.**
   - If a path must be safe, call `validate_write_path()`.
   - A comment saying input is trusted is insufficient unless the source is internally generated and enforced by code.

## ConsensusDevAgent-Specific Patterns

1. **Validate paths before any ConsensusDevAgent file write, patch write, artifact write, or transcript write.**
   - This includes:
     - generated source files
     - test files
     - temporary patch outputs
     - logs or transcripts written from task input
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(target_path)
   ```

2. **Use the Forge branch format for every agent-created branch without exception.**
   - Exact format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Zero-pad PR number to 3 digits.
   - Convert title to lowercase slug form.

3. **Implement `fetch_build_map()` so “not created yet” returns `None`.**
   - This is mandatory for early-build operation.
   - Never raise for the no-map-yet condition.
   - Add a live/integration test equivalent to `TestBuildMapLive` covering this case.

4. **Treat `_strip_code_fences()` as a locked multi-module contract.**
   - Before merging any change to one copy, update all five copies.
   - Add or update tests in every affected module set.
   - Do not introduce an async version.

5. **Do not generate placeholder-driven templates in ConsensusDevAgent outputs.**
   - Forbidden examples:
     - files containing unresolved runtime markers
     - files whose only job is to call another generated file
     - dynamic module-loading stubs

6. **Generate complete implementation files, not orchestration shells.**
   - Each generated file must contain the logic needed for its stated responsibility.
   - Split into multiple files only when each file has a distinct concrete responsibility.

7. **For interactive macOS UI produced by this subsystem, every interactive control must set `.accessibilityIdentifier()`.**
   - Use format:
     - `{module}-{component}-{role}-{context?}`
   - Apply to:
     - buttons
     - text fields
     - toggles
     - collection rows
     - action controls in repeated cards or lists

8. **For repeated UI elements, append stable domain context, not display text.**
   - Use IDs such as:
     - `{projectId}`
     - `{gateId}`
   - Do not use mutable labels like project names or button captions as the context token.

9. **When implementing absence-tolerant fetch APIs, distinguish “missing” from “failed.”**
   - Return `None` for documented not-yet-created resources such as the build map.
   - Raise a typed exception for transport errors, auth failures, schema violations, or unexpected server responses.

10. **Keep tests aligned with production contracts, not inferred behavior.**
    - Required assertions:
      - `fetch_build_map()` returns `None` when no map exists yet
      - `_strip_code_fences()` preserves trailing newline
      - `_strip_code_fences()` returns `None` unchanged
      - path validation occurs before any write path is used

11. **Do not merge ConsensusDevAgent code that writes files without an observable validation step.**
    - The validation call must appear in the same control flow before the write.
    - Indirect assumptions like “caller already validated it” are not acceptable unless the parameter type is a validated path object enforced by the API.