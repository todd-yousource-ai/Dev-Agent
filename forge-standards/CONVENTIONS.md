# Code Conventions - Forge Platform

## File and Directory Naming

1. Place code only in approved subsystem roots:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`
   - `tests/<subsystem>/`

2. Mirror source structure exactly under `tests/`.
   - Example: `src/mcp/policy_loader.py` → `tests/mcp/test_policy_loader.py`
   - Do not place tests in a shared `tests/unit/` or `tests/integration/` tree unless that tree still mirrors the source path beneath it.

3. Name Python files in `snake_case.py`.
   - Use nouns for modules that define data structures or services: `build_map.py`, `path_security.py`
   - Use verb-noun names only for operation-focused modules: `fetch_build_map.py`

4. Do not create placeholder, dispatcher, or pass-through generated files.
   - A generated file must not exist only to call another generated file.
   - A generated file must be complete and self-contained.

5. Do not create template source files containing runtime placeholders.
   - Forbidden: `{{TOKEN}}`, `${RUNTIME_VALUE}`, `<REPLACE_ME>`
   - Generate concrete code only.

6. Keep one primary responsibility per file.
   - If a file name cannot describe its purpose in 2–4 words, split it.

7. Name test files `test_<module_name>.py`.
   - Example: `src/rewind/replay_engine.py` → `tests/rewind/test_replay_engine.py`

8. Store shared test fixtures beside the mirrored test area for that subsystem.
   - Example: `tests/trustflow/fixtures/stream_events.json`

9. Use the mandatory branch naming format for all work:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example: `forge-agent/build/e17/consensus-dev-agent/pr-007-build-map-retry`

10. Use lowercase kebab-case for non-Python artifact names when a slug is needed in paths, branch names, or generated identifiers.
    - Example: `consensus-dev-agent`, `build-map-retry`

---

## Class and Function Naming

1. Name classes in `PascalCase`.
   - Examples: `ConsensusDevAgent`, `BuildMapClient`, `PathValidationError`

2. Name functions and methods in `snake_case`.
   - Examples: `fetch_build_map`, `validate_write_path`, `_strip_code_fences`

3. Prefix internal helpers with a single leading underscore.
   - Example: `_normalize_gate_vote`
   - Do not use double-underscore name mangling.

4. Name boolean-returning functions with `is_`, `has_`, `can_`, or `should_`.
   - Examples: `is_terminal_state`, `has_valid_signature`

5. Name async functions with the same semantic name as sync functions; do not add `_async` suffix unless a sync version with the same purpose exists in the same module.
   - Preferred: `fetch_build_map`
   - Allowed only for paired APIs: `fetch_build_map` / `fetch_build_map_async`

6. `_strip_code_fences()` is a reserved function name and contract.
   - Every `_strip_code_fences()` implementation across all five modules must be byte-for-byte identical in logic.
   - It must:
     - accept `None` or `""` and return it unchanged
     - preserve a trailing newline on non-empty output
     - leave unfenced code unchanged
     - leave unicode characters unchanged
     - remain synchronous
   - Any change to this function must be applied to all five modules in the same change set.

7. Use explicit action names for side-effecting functions.
   - Preferred: `write_build_map`, `delete_checkpoint`, `publish_event`
   - Avoid vague names like `handle`, `process`, `run`, unless the enclosing type makes the action specific.

8. Name exception classes with the `Error` suffix.
   - Examples: `BuildMapNotFoundError`, `PathTraversalError`

9. In UI code, assign `axIdentifier` values to all interactive elements using this exact format:
   - `{module}-{component}-{role}-{context?}`
   - Examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`
     - `navigator-project-row-{projectId}`
     - `stream-gate-yes-button-{gateId}`

10. Keep `axIdentifier` segments lowercase and hyphen-separated.
    - Dynamic suffixes must appear at the end.
    - Do not reorder fixed segments once introduced.

---

## Error and Exception Patterns

1. Validate paths before any write using `validate_write_path`.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Perform this validation before opening, creating, overwriting, renaming, moving, or deleting any file path derived from external or user-controlled input.

2. Never write directly to a user-supplied path string.
   - Forbidden:
   ```python
   with open(user_supplied_path, "w") as f:
       ...
   ```
   - Required:
   ```python
   safe_path = validate_write_path(user_supplied_path)
   with open(safe_path, "w") as f:
       ...
   ```

3. Let path validation failures raise immediately.
   - Do not catch and ignore traversal-related exceptions.
   - If converting to a domain error, preserve the original exception as the cause:
   ```python
   try:
       safe_path = validate_write_path(user_supplied_path)
   except Exception as exc:
       raise ArtifactWriteError(f"Invalid write path: {user_supplied_path}") from exc
   ```

4. Return `None` for missing build maps in the initial no-map state.
   - `fetch_build_map()` must return `None` gracefully when no build map exists yet.
   - It must not raise for this condition.
   - This behavior must be covered by a live-style test equivalent to `TestBuildMapLive`.

5. Raise exceptions only for actual failure states, not for expected absence.
   - Missing optional artifact at startup: return `None`
   - Corrupt artifact content, permission failures, invalid schema: raise a typed `Error`

6. Use typed exceptions for domain failures.
   - Prefer `BuildMapLoadError`, `ConsensusGenerationError`, `PolicyValidationError`
   - Do not raise bare `Exception`.

7. Preserve causality when wrapping lower-level exceptions.
   - Always use `raise ... from exc`.

8. Fail fast on forbidden dynamic code loading in generated code paths.
   - Do not use:
     - `eval()`
     - `exec()`
     - `importlib.import_module()`
   - Treat attempts to introduce these in generation flows as blocking errors during review and CI.

9. Do not silently sanitize invalid runtime placeholders in generated files.
   - Reject the generation step instead of writing partial templates.

10. Error messages must include the concrete artifact or identifier involved.
    - Include path, module name, gate ID, project ID, or subsystem slug where applicable.

---

## Import and Module Organisation

1. Organize imports in this order, with one blank line between groups:
   1. standard library
   2. third-party packages
   3. first-party Forge modules

2. Within each import group, sort imports alphabetically by module path.

3. Prefer absolute imports from the project root package structure.
   - Preferred: `from src.mcp.policy_loader import PolicyLoader`
   - Avoid deep relative imports like `from ..shared.loader import PolicyLoader`

4. Import concrete symbols only when they are used directly three or more times in the file; otherwise import the module.
   - Preferred for repeated use:
   ```python
   from path_security import validate_write_path
   ```
   - Preferred for occasional use:
   ```python
   import json
   ```

5. Do not perform dynamic module loading in generated or consensus-controlled code.
   - Forbidden:
   ```python
   import importlib
   importlib.import_module(module_name)
   ```

6. Keep module top levels free of side effects.
   - Allowed: constant definitions, class definitions, function definitions
   - Forbidden: network calls, file writes, environment mutation, process spawning

7. Export only stable public APIs from package `__init__.py` files.
   - Do not use `__init__.py` to execute registration logic.

8. Split modules before they require unrelated imports from multiple subsystems.
   - If a module imports from `src/mcp/`, `src/trustflow/`, and `src/rewind/` for unrelated tasks, separate those tasks into subsystem-local modules.

9. Place shared sanitization helpers with the owning subsystem, then duplicate only where the TRD explicitly requires identical copies.
   - `_strip_code_fences()` is the exception: keep each required copy identical across all five modules.

10. Keep test imports aligned to mirrored source modules.
    - Tests for `src/cal/session_state.py` must import that module directly rather than reaching through unrelated façade modules.

---

## Comment and Documentation Rules

1. Write comments only when they add information not obvious from the code.
   - Explain constraints, invariants, protocol expectations, or TRD-mandated behavior.
   - Do not restate the next line of code.

2. When implementing a TRD-mandated behavior, include a short reference comment at the enforcement point.
   - Example:
   ```python
   # TRD-16: missing build map is an expected startup state; return None
   return None
   ```

3. Document any function with externally significant edge-case behavior using a docstring.
   - Required for:
     - `fetch_build_map()`
     - `_strip_code_fences()`
     - any path-validation wrapper
     - any function that returns `None` for expected absence

4. In `_strip_code_fences()` docstrings, state all contract requirements explicitly:
   - returns `None` and `""` unchanged
   - preserves trailing newline
   - does not alter unfenced content
   - synchronous only

5. Do not use TODO comments without an owner and concrete action.
   - Required format:
   ```python
   # TODO(e17): replace polling with build-map event subscription
   ```

6. Do not leave commented-out code in committed files.
   - Remove it or restore it as active code with tests.

7. Keep docstring style consistent within a module.
   - If a module uses triple-double-quoted summary docstrings, keep that style for all public classes and functions in that module.

8. For UI accessibility identifiers, add comments only when the context segment is non-obvious or derived from a domain object.
   - Example:
   ```swift
   // context = gateId from stream payload
   .accessibilityIdentifier("stream-gate-yes-button-\(gateId)")
   ```

9. When behavior must stay synchronized across multiple files, state that explicitly in a comment above the duplicated block.
   - Example:
   ```python
   # Keep identical across all five modules per TRD-14.
   def _strip_code_fences(value):
       ...
   ```

10. Include concrete examples in docs for naming formats that are easy to misuse.
    - Required for branch names and `axIdentifier` patterns.

---

## ConsensusDevAgent-Specific Patterns

1. Treat every generated file as a final artifact, not an intermediate dispatcher.
   - Each generated file must contain complete logic for its stated purpose.
   - Do not generate files whose only purpose is to invoke another generated file.

2. Ban runtime code execution in generated artifacts.
   - Do not generate code that uses `eval()`, `exec()`, or `importlib.import_module()`.

3. Ban runtime template substitution in generated artifacts.
   - Generated output must be directly executable or importable without placeholder expansion.

4. Apply path validation before any agent-driven write, including:
   - generated source files
   - test files
   - patches exported to disk
   - logs or reports written from user-selected destinations

5. Standardize branch creation to the mandatory Forge format:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - `subsystem_slug` must be lowercase kebab-case.
   - `title_slug` must be lowercase kebab-case.
   - `N` must be zero-padded to 3 digits.

6. When creating or updating any of the five modules that contain `_strip_code_fences()`, update all five in the same PR.
   - Do not merge partial synchronization.
   - Add tests proving identical behavior for all five copies.

7. Add a regression test for the no-build-map startup case whenever touching build map retrieval logic.
   - Minimum assertion: `fetch_build_map()` returns `None` and does not raise when the map is absent.

8. Keep consensus code paths deterministic.
   - Do not rely on runtime dynamic imports, generated dispatch chains, or hidden file indirection.
   - Inputs and outputs must be traceable to explicit modules and functions.

9. Use explicit subsystem-local filenames for generated outputs.
   - Preferred: `src/cal/conversation_state.py`
   - Avoid vague names like `generated_helper.py`, `runtime_adapter.py`, `dispatch_layer.py`

10. For interactive macOS shell surfaces produced by this subsystem, set `.accessibilityIdentifier()` on every interactive control.
    - Use the exact format `{module}-{component}-{role}-{context?}`.
    - Missing identifiers on interactive elements are convention violations.

11. When an identifier includes a domain object key, append it as the final segment only.
    - Correct: `stream-gate-stop-button-{gateId}`
    - Incorrect: `stream-{gateId}-gate-stop-button`

12. When writing code that may create project-scoped rows or gate-scoped actions, encode the scope directly in the identifier.
    - Examples:
      - `navigator-project-row-{projectId}`
      - `stream-gate-skip-button-{gateId}`

13. Do not collapse expected absence into error-handling branches in agent orchestration.
    - If a missing artifact is a valid bootstrap state, represent it as `None` and branch explicitly on `is None`.

14. Keep sanitization logic synchronous in consensus-critical text cleanup paths.
    - `_strip_code_fences()` must not become `async def`.
    - Do not wrap it in async-only adapters unless a synchronous entry point remains available.

15. When duplicating TRD-required logic across modules, verify identity with tests instead of relying on reviewer inspection alone.
    - Add a test that compares outputs for the same corpus, including:
      - `None`
      - empty string
      - plain unfenced code
      - fenced code
      - unicode content
      - content with trailing newline