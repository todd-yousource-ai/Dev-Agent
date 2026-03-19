

# Code Conventions — Forge Platform

> Authoritative coding conventions for all Forge subsystems.
> Every rule is mandatory unless explicitly marked **(advisory)**.
> Last updated: 2025-01-15

---

## 1. File and Directory Naming

1. **Source directories use abbreviated, lowercase subsystem slugs.** No underscores, no hyphens in top-level module names.

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

2. **Test directories mirror `src/` exactly.**

   ```
   tests/cal/
   tests/dtl/
   tests/trustflow/
   tests/vtz/
   ...
   ```

3. **Python files** use `snake_case.py`. Never uppercase, never hyphens.

   ```
   src/dtl/label_validator.py     ✅
   src/dtl/LabelValidator.py      ❌
   src/dtl/label-validator.py     ❌
   ```

4. **TypeScript/Swift files** use `PascalCase` for component/class files, `camelCase` for utility modules.

   ```
   StreamGateCard.swift            ✅  (component)
   consensusHelpers.ts             ✅  (utility)
   ```

5. **Test files** are prefixed `test_` (Python) or suffixed `.test.ts` / `.test.swift`.

   ```
   tests/dtl/test_label_validator.py
   sdk/connector/__tests__/handshake.test.ts
   ```

6. **No generic filenames.** `utils.py`, `helpers.py`, `misc.py` are banned. Name files after the capability they provide (e.g., `path_security.py`, `token_rotation.py`).

---

## 2. Class and Function Naming

7. **Python classes** use `PascalCase`. No suffixes like `Manager` or `Handler` unless the class genuinely manages lifecycle or handles events.

   ```python
   class ConsensusRound:       ✅
   class LabelValidator:       ✅
   class DataManager:          ❌  — name after what it does
   ```

8. **Python functions and methods** use `snake_case`. Prefix private helpers with a single underscore.

   ```python
   def validate_quorum(votes: list[Vote]) -> bool:    ✅
   def _merge_partial_results(a, b):                   ✅  (private)
   ```

9. **Constants** use `UPPER_SNAKE_CASE` and live at module top-level or in a dedicated `constants.py` per subsystem.

   ```python
   MAX_RETRIES = 3
   CONSENSUS_QUORUM_THRESHOLD = 0.67
   ```

10. **TypeScript** follows the same spirit: `PascalCase` classes/interfaces/types, `camelCase` functions/variables, `UPPER_SNAKE_CASE` constants.

11. **Boolean variables and functions** must read as assertions.

    ```python
    is_valid = True              ✅
    has_quorum = check_quorum()  ✅
    valid = True                 ❌
    ```

12. **Accessibility identifiers (SwiftUI)** follow the pattern `{module}-{component}-{role}-{context?}`. Set via `.accessibilityIdentifier()` on **every** interactive element.

    ```swift
    // Examples
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

13. **Define subsystem-specific exception hierarchies** rooted in a single base class per subsystem.

    ```python
    # src/dtl/exceptions.py
    class DTLError(Exception):
        """Base for all DTL exceptions."""

    class LabelValidationError(DTLError):
        """Raised when a trust label fails schema validation."""

    class LabelExpiredError(DTLError):
        """Raised when a trust label's TTL has elapsed."""
    ```

14. **Never catch bare `Exception` or `BaseException`** except at top-level entry points (CLI main, HTTP handler root). Always catch the narrowest type.

    ```python
    try:
        result = validate_label(payload)
    except LabelValidationError as exc:
        log.warning("Invalid label", error=str(exc))
        return ErrorResponse(status=422, detail=str(exc))
    ```

15. **Every exception must carry a machine-readable `code` attribute** for downstream consumption.

    ```python
    class ConsensusTimeoutError(ConsensusError):
        code = "CONSENSUS_TIMEOUT"
    ```

16. **No silent swallowing.** If you catch and continue, you must log at `WARNING` or higher with the exception context.

17. **Path validation before ANY write.** This is a security-critical rule with zero exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` with `profile = black`):

    ```
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (src/*)
    4. Local relative imports
    ```

    Separate each group with a blank line.

19. **Absolute imports for cross-subsystem references.** Relative imports are permitted only within the same subsystem package.

    ```python
    # Inside src/dtl/label_validator.py
    from dtl.exceptions import LabelValidationError    # ✅ relative-ok within dtl
    from cal.session import Session                     # ✅ absolute for cross-subsystem
    from .constants import MAX_LABEL_SIZE               # ✅ same package
    ```

20. **No wildcard imports.** `from module import *` is banned everywhere.

21. **Lazy imports** are permitted only when a dependency is heavy and rarely used. Annotate with `# lazy: <reason>`.

    ```python
    def export_pdf(report):
        import weasyprint  # lazy: 40 MB dep, only used in export path
        ...
    ```

22. **Circular import prevention.** If two subsystems need each other's types, use `TYPE_CHECKING` guards.

    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from cal.session import Session
    ```

---

## 5. Comment and Documentation Rules

23. **Every public class and function gets a docstring.** Use Google-style format.

    ```python
    def validate_quorum(votes: list[Vote], threshold: float = 0.67) -> bool:
        """Check whether votes meet the consensus quorum threshold.

        Args:
            votes: Collected votes from agent panel.
            threshold: Fraction of affirmative votes required. Defaults to 0.67.

        Returns:
            True if quorum is met.

        Raises:
            ConsensusError: If vote list is empty.
        """
    ```

24. **No commented-out code in committed files.** Use version control history