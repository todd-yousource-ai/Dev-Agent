

# Code Conventions — Forge Platform

> Canonical reference for all contributors and agents. Every rule is enforceable in CI. "MUST" means a PR will be rejected if violated.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly.**

   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   tests/<subsystem>/ # Tests mirror src/ structure exactly
   ```

2. **All filenames** MUST be lowercase `snake_case` with a `.py` extension (Python) or lowercase kebab-case for Swift/config. No spaces, no uppercase, no double underscores.

3. **Test files** MUST mirror the source file they cover: `src/cal/session.py` → `tests/cal/test_session.py`. Prefix is always `test_`.

4. **No orphan directories.** Every directory under `src/` and `tests/` MUST contain an `__init__.py` (Python) or a manifest file appropriate to its language.

5. **Generated files** MUST carry the suffix `_gen` before the extension (e.g., `schema_gen.py`). Never hand-edit a `_gen` file.

---

## 2. Class and Function Naming

6. **Classes** — `PascalCase`. Acronyms up to 3 letters stay uppercase; longer acronyms use title-case: `MCP`, `DTL`, `TrustFlowEngine`, `CalSession`.

7. **Functions and methods** — `snake_case`, verb-first: `validate_write_path()`, `fetch_build_map()`, `emit_trust_label()`.

8. **Constants** — `UPPER_SNAKE_CASE`, defined at module level: `MAX_RETRY_COUNT`, `DEFAULT_GATE_TIMEOUT_S`.

9. **Private internals** — single leading underscore: `_strip_code_fences()`, `_resolve_chain()`. Double underscores are reserved for Python name-mangling only when strictly required.

10. **axIdentifier naming (macOS/Swift UI).** Every interactive element MUST set `.accessibilityIdentifier()` using the pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Examples:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

    Context suffix is optional but MUST be present when the element is repeated in a list or parameterized view.

---

## 3. Error and Exception Patterns

11. **Custom exceptions** MUST inherit from a single root: `ForgeError(Exception)`. Each subsystem defines one module-level base: `CalError(ForgeError)`, `DTLError(ForgeError)`, etc.

12. **Never catch bare `Exception` or `BaseException`** except at a top-level entry point that logs and re-raises.

13. **Error messages** MUST be a single English sentence starting with a lowercase verb and including the offending value:

    ```python
    raise PathTraversalError(f"blocked write to disallowed path: {user_path!r}")
    ```

14. **Retriable errors** MUST expose a boolean property `retriable` on the exception class so callers do not need `isinstance` chains.

15. **Validation errors** MUST be raised **before** any side-effect (write, network call, queue publish). Fail fast, fail loud.

---

## 4. Import and Module Organisation

16. **Import order** (enforced by `isort` profile `black`):

    ```
    1. stdlib
    2. third-party
    3. forge platform (`from src.<subsystem>…`)
    4. local relative (single dot only: `from .session import …`)
    ```

    One blank line between each group.

17. **No wildcard imports** (`from x import *`) — ever.

18. **No circular imports.** If two subsystems need each other, extract the shared type into `src/common/types.py`.

19. **No dynamic code loading in generated files.** Generated code MUST NOT call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files. Every generated file MUST be complete and self-contained.

---

## 5. Comment and Documentation Rules

20. **Every public function and class** MUST have a docstring (Google style):

    ```python
    def fetch_build_map(project_id: str) -> BuildMap | None:
        """Return the current build map, or None if no map exists yet.

        Args:
            project_id: UUID of the target Forge project.

        Returns:
            A BuildMap instance, or None for the first PRs of any build.

        Raises:
            CalError: If the project cannot be resolved.
        """
    ```

21. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

22. **TODO format**: `# TODO(engineer_id): <description> — tracked in FORGE-<N>`. Untracked TODOs are rejected in CI.

23. **No commented-out code** in any file merged to `main`. Use version control.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security — Mandatory Write Validation

24. **Every file-write path** supplied or influenced by external input MUST be validated before the write occurs:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    ```

    This applies to agent-generated code, user-submitted paths, and any path assembled from config values. No exceptions.

### 6.2 Branch Naming

25. All ConsensusDevAgent branches MUST follow this exact pattern:

    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

    - `engineer_id` — the assigned engineer's lowercase slug.
    - `subsystem_slug` — matches the directory name under `src/` (e.g., `cal`, `dtl`, `vtz`).
    - `N` — zero-padded 3-digit PR sequence number within the build.
    - `title_slug` — lowercase kebab-case summary, max 48 characters.

    Example: `forge-agent/build/jchen/trustflow/pr-007-add-audit-envelope`

### 6.3 Shared Sanitisation Functions

26. The `_strip_code_fences()` function MUST be **identical** across every module that defines it. The canonical copy lives in `src/common/sanitise.py`; all other modules MUST import from there rather than re-implement. The function contract:

    - Accepts an empty string or `None` and returns it unchanged.
    - Preserves trailing newline on non-empty output.
    - Does not modify code that has no fences or Unicode characters.
    - Is synchronous (no `async`).

    Any change to sanitisation logic MUST be applied in the single canonical location.

### 6.4 Generation System Constraints

27. **Generated files MUST be self-contained.** A generated file MUST NOT:
    - Call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.
    - Contain runtime placeholders intended for later string substitution.
    - Exist solely to dispatch to another generated file.

28. **Every generated file** MUST be a complete, independently executable (or importable) unit that can be tested in isolation.

### 6.5 Graceful Degradation on Missing State

29. Functions that query build state that may not yet exist (e.g., `fetch_build_map()`