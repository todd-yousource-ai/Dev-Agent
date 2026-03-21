

# Code Conventions — Forge Platform

> Authoritative coding conventions for all Forge subsystems.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem acronyms exactly:**

   ```
   src/cal/           - Conversation Abstraction Layer
   src/dtl/           - Data Trust Label
   src/trustflow/     - TrustFlow audit stream
   src/vtz/           - Virtual Trust Zone enforcement
   src/trustlock/     - Cryptographic machine identity (TPM-anchored)
   src/mcp/           - MCP Policy Engine
   src/rewind/        - Forge Rewind replay engine
   sdk/connector/     - Forge Connector SDK
   ```

2. **Test directories mirror `src/` exactly:**

   ```
   tests/cal/
   tests/dtl/
   tests/trustflow/
   tests/vtz/
   tests/trustlock/
   tests/mcp/
   tests/rewind/
   tests/connector/
   ```

3. **File names** use `snake_case.py` — no hyphens, no uppercase, no abbreviations that are not already the canonical subsystem slug (e.g., `cal`, `dtl`, `vtz`).

4. **One public class per file.** The file name must match the class name in snake_case form (e.g., `class TrustFlowAuditor` → `trust_flow_auditor.py`).

5. **No runtime template files.** Every generated or source file must be complete and self-contained. Do not create files whose only purpose is to call or dispatch to another generated file.

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Subsystem prefix is encouraged for top-level public classes (`CalSession`, `DtlLabel`, `VtzEnforcer`).

7. **Functions and methods:** `snake_case`. Verbs first (`validate_path`, `fetch_build_map`, `strip_code_fences`).

8. **Constants:** `UPPER_SNAKE_CASE`, defined at module level.

9. **Private members:** Single leading underscore (`_internal_cache`). Double underscores only when name-mangling is intentionally required.

10. **axIdentifier naming (macOS / SwiftUI):**
    Every interactive element must have `.accessibilityIdentifier()` set, using the pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Examples:

    ```
    "auth-touchid-button"
    "auth-passcode-button"
    "settings-anthropic-key-field"
    "settings-anthropic-key-test-button"
    "settings-anthropic-key-reveal-button"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    "stream-gate-skip-button-{gateId}"
    "stream-gate-stop-button-{gateId}"
    ```

    All four segments are lowercase-hyphenated. The `{context}` segment is required when multiple instances of the same component can exist simultaneously.

---

## 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a single `ForgeError` base class defined in `src/forge_error.py`.

12. **Subsystem exceptions** follow `{Subsystem}{Noun}Error` naming: `CalSessionExpiredError`, `VtzPathTraversalError`, `DtlSchemaValidationError`.

13. **Never catch bare `Exception` or `BaseException`** outside of top-level entry points or explicit fault barriers.

14. **Error messages** must include: (a) what failed, (b) the offending value or context identifier, (c) the expected state. Example:

    ```python
    raise VtzPathTraversalError(
        f"Write blocked: path '{user_path}' escapes sandbox root '{sandbox_root}'"
    )
    ```

15. **Graceful None returns are allowed only where the TRD explicitly requires them.** Example: `fetch_build_map()` must return `None` (not raise) when no map exists yet. Document this at the call site with a comment citing the TRD.

---

## 4. Import and Module Organisation

16. **Import order** (enforced by `isort` with `profile=black`):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/`)
    4. Local / relative imports

    Separate each group with a blank line.

17. **Absolute imports from `src/`** are mandatory for cross-subsystem references:

    ```python
    from src.vtz.path_security import validate_write_path
    ```

18. **No dynamic code loading.** Do not use `eval()`, `exec()`, or `importlib.import_module()` to load generated files at runtime.

19. **Circular imports** are a blocking CI error. If two subsystems depend on each other, extract the shared type or protocol into `src/shared/`.

---

## 5. Comment and Documentation Rules

20. **Every public function and class** must have a docstring (Google style):

    ```python
    def validate_write_path(user_supplied_path: str) -> Path:
        """Validate and return a safe write path inside the sandbox.

        Args:
            user_supplied_path: Raw path string from the caller.

        Returns:
            Resolved Path guaranteed to be within the sandbox root.

        Raises:
            VtzPathTraversalError: If the path escapes the sandbox.
        """
    ```

21. **Inline comments** explain *why*, not *what*. If the code needs a *what* comment, the code should be refactored first.

22. **TRD citations** are required when a design decision is non-obvious. Format: `# Per TRD-16 §5.3: fetch_build_map returns None when no map exists.`

23. **TODO format:** `# TODO(engineer_id): description — FORGE-XXXX` (must reference a tracker ticket).

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security — Mandatory Pre-Write Validation

24. **Every write operation** — file create, file overwrite, directory create — must validate the target path before any I/O:

    ```python
    from src.vtz.path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    safe_path.write_text(content)
    ```

    No exceptions. No shortcuts. Agent-generated paths are treated as untrusted input.

### 6.2 Branch Naming

25. **All agent branches** must follow this exact pattern:

    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

    - `engineer_id`: The assigned engineer identifier (lowercase alphanumeric + hyphens).
    - `subsystem_slug`: One of `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`.
    - `N`: Zero-padded 3-digit PR sequence number.
    - `title_slug`: Lowercase-hyphenated summary, max 48 characters.

    Example: `forge-agent/build/eng-042/trustflow/pr-007-add-audit-event-schema`

### 6.3 Canonical `_strip_code_fences()` Function

26. The `_strip_code_fences()` utility appears in **exactly five modules**. All five copies must be **byte-identical**. Any change to the sanitisation logic must be applied atomically to all five in a single commit. The function contract:

    | Input | Output |
    |---|---|
    | `None` | `None` (returned unchanged) |
    | `""` (empty string) | `""` (returned unchanged) |
    | Code with no fences or unicode | Input returned unmodified |
    | Code with fences | Fences stripped; trailing newline preserved |

    The function must be **synchron