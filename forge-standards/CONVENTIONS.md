

# Code Conventions — Forge Platform

> Authoritative coding conventions for the Forge platform and the **ConsensusDevAgent** subsystem.
> Every rule is mandatory unless explicitly marked **(advisory)**. PR reviewers must enforce these during code review.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem boundaries exactly.**

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

2. **Test directories mirror source directories one-to-one.** A source file at `src/cal/session.py` must have its tests at `tests/cal/test_session.py`. No exceptions.

3. **All filenames are lowercase `snake_case`.** No hyphens, no camelCase, no uppercase letters in filenames.

4. **Every directory containing Python files must have an `__init__.py`**, even if empty. Implicit namespace packages are not permitted.

5. **Generated files** carry a `_gen` suffix before the extension (e.g., `schema_gen.py`, `manifest_gen.json`) so they are trivially identifiable and `.gitignore`-able.

6. **Branch naming is mandatory and machine-enforced:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — GitHub handle or numeric ID of the assigned engineer.
   - `subsystem_slug` — one of `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`.
   - `N` — zero-padded three-digit sequential PR number within the build.
   - `title_slug` — lowercase-hyphenated summary, max 48 characters.

   Example: `forge-agent/build/jdoe/trustflow/pr-007-add-event-replay`

---

## 2. Class and Function Naming

7. **Classes** use `PascalCase`. Acronyms of three or fewer letters stay uppercase; longer acronyms use title case.

   ```python
   class DTLValidator:       # ✓  (three-letter acronym)
   class McpPolicyEngine:    # ✓  (three-letter acronym, also acceptable as MCP)
   class TrustFlowEmitter:   # ✓
   class Dtlvalidator:       # ✗
   ```

8. **Functions and methods** use `snake_case`. No trailing underscores except to avoid keyword collisions (e.g., `type_`).

9. **Private helpers** are prefixed with a single underscore (`_strip_code_fences`). Double-underscore name-mangling is prohibited unless genuinely required for inheritance safety.

10. **Constants** use `UPPER_SNAKE_CASE` and must be defined at module level or inside a frozen dataclass / `enum.Enum`.

11. **Boolean variables and parameters** start with `is_`, `has_`, `can_`, `should_`, or `allow_`.

12. **axIdentifier strings** (macOS SwiftUI accessibility layer) follow this pattern exactly:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Set via `.accessibilityIdentifier()` on **all** interactive elements. Examples:

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

    Omit the `{context}` segment only when the element is globally unique.

---

## 3. Error and Exception Patterns

13. **Define one base exception per subsystem** in `<subsystem>/exceptions.py`:

    ```python
    class TrustFlowError(Exception):
        """Base for all TrustFlow errors."""
    ```

    All subsystem-specific exceptions inherit from this base.

14. **Never catch bare `Exception` or `BaseException`** outside of top-level entry points or explicit crash-barrier boundaries (which must be commented as such).

15. **Error messages are sentences**: capitalised first word, no trailing period, no f-string interpolation of secrets or PII.

    ```python
    raise DTLValidationError(f"Label checksum mismatch for artifact {artifact_id}")
    ```

16. **Re-raising must preserve the chain.** Use `raise X from err`, never bare `raise X`.

17. **`fetch_build_map()` and similar nullable queries must return `None` gracefully** — never raise — when the requested resource does not yet exist. This is the expected state for early-stage builds (first ≈5 PRs). Test with `TestBuildMapLive`.

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` with profile `black`):

    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/*`, `sdk/*`)
    4. Local relative imports

    Separate each group with a single blank line.

19. **Absolute imports from `src/` and `sdk/`** are required in production code. Relative imports are permitted only within the same subsystem package and only one level deep (e.g., `from .exceptions import TrustFlowError`).

20. **No wildcard imports** (`from x import *`) anywhere.

21. **No dynamic loading of generated files.** Generated modules must not use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files. Every generated file must be complete and self-contained. See §8 rule 36.

22. **Circular imports are CI-blocking.** The linter step runs `import-linter` contracts; any cycle fails the build.

---

## 5. Comment and Documentation Rules

23. **Every public class and public function has a docstring.** Use Google-style docstrings:

    ```python
    def validate_label(label: DTLabel, *, strict: bool = False) -> ValidationResult:
        """Validate a Data Trust Label against the current schema.

        Args:
            label: The label instance to validate.
            strict: If True, treat warnings as errors.

        Returns:
            A ValidationResult with any diagnostics attached.

        Raises:
            DTLValidationError: If the label is structurally invalid.
        """
    ```

24. **Inline comments explain *why*, never *what*.** If the code needs a "what" comment, refactor the code.

25. **TODO format is enforced:**

    ```python
    # TODO(engineer_id): <description> — tracking issue #NNN
    ```

    TODOs without an owner and issue number are rejected by the linter.

26. **No commented-out code in `main` or release branches.** Use version control.

---

## 6. Path Security and I/O

27. **Validate paths before ANY write operation.** Every code path that writes to the filesystem must call `validate_write_path` first:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

    This applies to agent-generated code, user-supplied inputs, and test fixtures. No exceptions.

28. **Never construct file paths via string concatenation.** Use `pathlib.Path` or `os.path.join`.

29. **Temporary files** must use `tempfile.NamedTemporaryFile` or `