

# Code Conventions — Forge Platform

> Authoritative coding standards for all Forge subsystems and the ConsensusDevAgent build pipeline.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly:**

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

2. **Python files** use `snake_case.py`. No hyphens, no uppercase.
   ```
   src/dtl/label_validator.py   ✅
   src/dtl/LabelValidator.py    ❌
   src/dtl/label-validator.py   ❌
   ```

3. **TypeScript/Swift files** use `PascalCase` for files that export a single class or component, `camelCase` for utility modules.
   ```
   StreamGateCard.swift   ✅  (exports struct StreamGateCard)
   formatTimestamp.ts     ✅  (exports utility function)
   ```

4. **Test files** are named `test_<module>.py` (Python) or `<Module>.test.ts` (TypeScript) and live under `tests/<subsystem>/`, mirroring the source path depth.
   ```
   src/cal/session_manager.py
   tests/cal/test_session_manager.py
   ```

5. **No file shall exceed 500 lines.** Split into focused modules before that threshold.

6. **Every directory containing Python code must have an `__init__.py`**, even if empty.

---

## 2. Class and Function Naming

7. **Python classes** — `PascalCase`. No suffixes like `Impl` or `Base` unless the class is genuinely abstract (in which case use `Abstract` prefix or `Base` suffix).
   ```python
   class ConsensusEngine:        ✅
   class AbstractGatePolicy:     ✅
   class consensus_engine:       ❌
   ```

8. **Python functions and methods** — `snake_case`, verb-first.
   ```python
   def validate_write_path(path: str) -> Path:   ✅
   def path_validate(path: str) -> Path:          ❌
   ```

9. **Constants** — `UPPER_SNAKE_CASE`, defined at module level.
   ```python
   MAX_RETRY_COUNT = 3
   DEFAULT_GATE_TIMEOUT_S = 30
   ```

10. **TypeScript** follows the same spirit: `PascalCase` classes/interfaces/types, `camelCase` functions/variables, `UPPER_SNAKE_CASE` constants.

11. **Boolean variables and functions** start with `is_`, `has_`, `can_`, or `should_`.
    ```python
    is_authenticated = True
    def has_valid_signature(label: TrustLabel) -> bool: ...
    ```

12. **Private members** use a single leading underscore. Never use double underscores for name-mangling unless explicitly required by a framework.

13. **Accessibility identifiers (macOS / SwiftUI)** follow the pattern:
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

---

## 3. Error and Exception Patterns

14. **All custom exceptions inherit from a single base:**
    ```python
    class ForgeError(Exception):
        """Root exception for the Forge platform."""
        def __init__(self, message: str, *, code: str | None = None):
            self.code = code
            super().__init__(message)
    ```

15. **Subsystem exceptions are namespaced** under the subsystem module and extend `ForgeError`:
    ```python
    # src/dtl/exceptions.py
    from forge.exceptions import ForgeError

    class LabelValidationError(ForgeError): ...
    class LabelExpiredError(LabelValidationError): ...
    ```

16. **Never catch bare `Exception` or `BaseException`** in production code unless immediately re-raising after logging.

17. **Error messages are static, structured strings** — no f-string interpolation of user-supplied data into log messages. Pass context via exception attributes.
    ```python
    raise LabelValidationError(
        "Label signature mismatch",
        code="DTL_SIG_001",
    )
    ```

18. **Every raised exception must have a unique, grep-able `code` string** in the format `{SUBSYSTEM}_{CATEGORY}_{NNN}` (e.g., `VTZ_AUTH_003`).

19. **Return types, not exceptions, for expected control flow.** Use `Result`-style patterns or explicit `None` returns for anticipated "not-found" cases. Exceptions are for genuinely exceptional states.

---

## 4. Import and Module Organisation

20. **Import order** (enforced by `isort` with the profile below):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`forge.*`, `sdk.*`)
    4. Local / relative imports

    Separate each group with a blank line.

    ```ini
    # pyproject.toml
    [tool.isort]
    profile = "black"
    known_first_party = ["forge", "sdk"]
    ```

21. **Absolute imports for cross-subsystem references:**
    ```python
    from forge.dtl.label_validator import validate_label   ✅
    from ..dtl.label_validator import validate_label        ❌  (cross-subsystem)
    ```

22. **Relative imports only within the same subsystem:**
    ```python
    # Inside src/dtl/label_validator.py
    from .exceptions import LabelValidationError            ✅
    ```

23. **No wildcard imports** (`from module import *`) anywhere.

24. **Lazy imports** are permitted only for heavy optional dependencies (e.g., ML frameworks) and must be wrapped in a function-scoped import with a comment explaining why.

---

## 5. Comment and Documentation Rules

25. **Every public class and function has a docstring.** Use Google-style format:
    ```python
    def validate_write_path(user_supplied_path: str) -> Path:
        """Validate and sanitise a user-supplied path before writing.

        Args:
            user_supplied_path: Raw path string from external input.

        Returns:
            A resolved, safe Path object within the allowed write root.

        Raises:
            ForgeError: If the path contains traversal sequences or
                escapes the sandbox.
        """
    ```

26. **Inline comments explain *why*, never *what*.** If the code needs a comment to explain *what* it does, refactor for clarity first.

27. **TODO format** — always include assignee and ticket:
    ```python
    # TODO(alice, FORGE-1234): Replace naive retry with exponential backoff.
    ```

28. **No commented-out code in main.** Delete it; that's what version control is for.

29. **Type hints are mandatory** for all function signatures and class attributes. Use `from __future__ import annotations` in every Python file