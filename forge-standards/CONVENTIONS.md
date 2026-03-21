

# Code Conventions — Forge Platform

> Canonical reference for all contributors and autonomous agents operating within the Forge platform. Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem acronyms exactly.**

   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   ```

2. **Tests mirror `src/` exactly.** A source file at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

3. **Python filenames** use `snake_case`, lowercase only, no hyphens. Maximum 40 characters excluding extension.

4. **Swift filenames** use `PascalCase` matching the primary type declared inside (e.g., `StreamGateCard.swift`).

5. **No generic names.** Files named `utils.py`, `helpers.py`, `misc.py`, or `common.py` are prohibited. Name the file after the capability it provides (e.g., `path_security.py`, `fence_sanitiser.py`).

6. **Generated files** carry a `.gen.` infix before the extension (e.g., `build_map.gen.json`). Never hand-edit a `.gen.` file.

---

## 2. Branch Naming

7. **All agent-authored branches** must follow this exact pattern:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: lowercase GitHub handle or assigned agent ID.
   - `subsystem_slug`: one of `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`, or `infra`.
   - `N`: zero-padded three-digit PR sequence number.
   - `title_slug`: lowercase, hyphen-separated, ≤ 48 chars.

   Example: `forge-agent/build/agentK/trustflow/pr-012-add-audit-rotation`

8. Human feature branches use `feat/{subsystem_slug}/{title_slug}`. Hotfix branches use `fix/{subsystem_slug}/{title_slug}`.

---

## 3. Class and Function Naming

9. **Python** — classes: `PascalCase`; functions/methods: `snake_case`; constants: `UPPER_SNAKE_CASE`; private members: single leading underscore.

10. **Swift** — types/protocols: `PascalCase`; functions/properties: `camelCase`; constants: `camelCase` (static let) or `UPPER_SNAKE_CASE` for global compile-time values.

11. **Boolean variables and properties** start with `is_`, `has_`, `can_`, or `should_` (Python) / `is`, `has`, `can`, `should` (Swift).

12. **axIdentifier convention (SwiftUI).** Every interactive element must set `.accessibilityIdentifier()` following this pattern:

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

    Omitting `accessibilityIdentifier` on a tappable, editable, or toggleable element is a CI-blocking violation.

---

## 4. Error and Exception Patterns

13. **Custom exception hierarchy.** All Forge exceptions inherit from `ForgeError` (defined in `src/forge_errors.py`). Subsystem exceptions inherit from a subsystem base (e.g., `CALError(ForgeError)`).

14. **Exception class names** end with `Error`. Never `Exception` suffix, never bare `raise Exception(...)`.

15. **Error messages** are a single English sentence, begin with a lowercase word, contain no trailing period, and embed the failing value:

    ```python
    raise PathTraversalError(f"path escapes sandbox: {resolved_path}")
    ```

16. **Catch narrowly.** Bare `except:` and `except Exception:` are prohibited outside top-level CLI entry points. Catch the most specific type.

17. **Graceful None returns where specified.** Functions documented as "returns `None` on absence" (e.g., `fetch_build_map()`) must never raise when the resource simply does not exist yet. Reserve exceptions for invariant violations, not expected empty states.

---

## 5. Import and Module Organisation

18. **Import order** (enforced by `isort` with profile `black`):

    1. Standard library
    2. Third-party packages
    3. Forge platform (`src/…`)
    4. Local relative imports

    Blank line between each group. No wildcard (`*`) imports.

19. **Relative imports** are allowed only within the same subsystem package. Cross-subsystem imports must be absolute:

    ```python
    # Good  — inside src/cal/
    from .session import Session

    # Good  — cross-subsystem
    from src.dtl.label import TrustLabel

    # Bad
    from ..dtl.label import TrustLabel
    ```

20. **No runtime dynamic loading in generated files.** Generated code must never call `eval()`, `exec()`, or `importlib.import_module()`. Every generated file must be complete and self-contained.

21. **Lazy imports** are permitted only when a module has an import-time cost > 200 ms (measured, not guessed). Document the reason inline.

---

## 6. Path Security

22. **Validate every write path.** Before any file-system write (open, rename, symlink, shutil copy), call:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    ```

    This is non-negotiable for agent-generated code and human code alike. CI static analysis flags any `open(..., "w")` or `pathlib.Path.write_*` call not preceded by `validate_write_path` in the same function scope.

23. **Read paths** from untrusted input must also be validated via `validate_read_path()` to prevent symlink-based exfiltration.

---

## 7. Comment and Documentation Rules

24. **Module docstring** is required in every `.py` file. First line: one-sentence purpose. Second paragraph (if needed): design rationale or TRD reference.

    ```python
    """Enforce Virtual Trust Zone boundary checks at the syscall level.

    Implements the zone policy described in TRD-VTZ §4.2.
    """
    ```

25. **Public functions and methods** require a docstring with `Args:`, `Returns:`, and `Raises:` sections (Google style).

26. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

27. **TODO format:** `# TODO(owner): description — FORGE-{ticket}`. TODOs without a ticket number are rejected by CI.

28. **No commented-out code** in any merged branch. Use version control history instead.

---

## 8. Shared Utility Functions — Deduplication Rule

29. **The `_strip_code_fences()` function** must be byte-identical across every module that defines it (currently five). Any change to sanitisation logic must be applied to all