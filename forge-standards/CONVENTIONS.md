

# Code Conventions — Forge Platform

**Scope:** All code in the Forge monorepo, with dedicated section for the ConsensusDevAgent subsystem.
**Last updated:** 2025-06-30

---

## 1. File and Directory Naming

1. **Source layout is subsystem-based.** Each subsystem owns a directory under `src/`:

   | Directory | Subsystem |
   |---|---|
   | `src/cal/` | Conversation Abstraction Layer |
   | `src/dtl/` | Data Trust Label |
   | `src/trustflow/` | TrustFlow audit stream |
   | `src/vtz/` | Virtual Trust Zone enforcement |
   | `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
   | `src/mcp/` | MCP Policy Engine |
   | `src/rewind/` | Forge Rewind replay engine |
   | `sdk/connector/` | Forge Connector SDK |

2. **Tests mirror `src/` exactly.** A source file at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

3. **All file and directory names are lowercase-snake_case.** No camelCase, no hyphens, no spaces.
   - ✅ `trust_label_validator.py`
   - ❌ `TrustLabelValidator.py`, `trust-label-validator.py`

4. **Test files are prefixed with `test_`.** Test helper/fixture files are prefixed with `conftest` or `fixtures_`.

5. **Generated code files must be self-contained.** Every generated file is complete on its own — no template files with runtime placeholders, no dispatch-only stubs (see Rule 28).

---

## 2. Branch Naming

6. **Agent branches follow this exact pattern:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: the assigned engineer short-ID (e.g., `e017`).
   - `subsystem_slug`: lowercase-hyphenated subsystem name (e.g., `consensus-engine`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase-hyphenated summary, max 48 characters.

   Example: `forge-agent/build/e017/consensus-engine/pr-004-add-quorum-timeout`

---

## 3. Class and Function Naming

7. **Classes: PascalCase.** Acronyms of 3+ letters are title-cased: `McpPolicyEngine`, `DtlValidator`, `VtzEnforcer`.

8. **Functions and methods: lowercase_snake_case.** Prefix private helpers with a single underscore: `_strip_code_fences()`.

9. **Constants: UPPER_SNAKE_CASE.** Defined at module level: `MAX_QUORUM_TIMEOUT_SEC = 30`.

10. **Boolean variables and functions use affirmative prefixes:** `is_`, `has_`, `can_`, `should_`.
    - ✅ `is_quorum_reached`, `has_valid_signature`
    - ❌ `quorum_status`, `check_sig`

---

## 4. Accessibility Identifiers (macOS Shell)

11. **Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.**

12. **Identifier format:** `{module}-{component}-{role}-{context?}`

    ```
    auth-touchid-button
    auth-passcode-button
    settings-anthropic-key-field
    settings-anthropic-key-test-button
    settings-anthropic-key-reveal-button
    navigator-project-row-{projectId}
    stream-gate-card-{gateId}
    stream-gate-yes-button-{gateId}
    stream-gate-skip-button-{gateId}
    stream-gate-stop-button-{gateId}
    ```

13. **All segments are lowercase-hyphenated.** Dynamic suffixes are wrapped in braces in documentation but resolve to actual IDs at runtime.

---

## 5. Error and Exception Patterns

14. **Define one base exception per subsystem** in `<subsystem>/exceptions.py`:

    ```python
    class CalError(Exception):
        """Base exception for the Conversation Abstraction Layer."""
    ```

15. **Subclass from the subsystem base, not from bare `Exception`:**

    ```python
    class SessionExpiredError(CalError): ...
    class QuorumNotReachedError(ConsensusError): ...
    ```

16. **Never swallow exceptions silently.** Every `except` block must either re-raise, log at `WARNING`+, or convert to a domain-specific exception with the original as `__cause__`:

    ```python
    except OSError as exc:
        raise TrustLockIOError("TPM read failed") from exc
    ```

17. **`fetch_build_map()` and similar lookup functions return `None` on absence — never raise.** The caller decides whether absence is an error. This is critical during early builds (first 5 PRs) where no build map exists yet.

---

## 6. Path Security

18. **Validate every path before any filesystem write.** No exceptions, no shortcuts.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

19. **`validate_write_path` must be the single chokepoint.** Do not inline traversal checks. If you need to write a file, call this function first.

20. **Never construct write paths via string concatenation with user input.** Always resolve through `validate_write_path`.

---

## 7. Import and Module Organisation

21. **Import order (enforced by `isort` profile `black`):**
    1. Standard library
    2. Third-party packages
    3. Forge subsystem imports (`from src.cal import ...`)
    4. Local relative imports

    Separate each group with a blank line.

22. **No wildcard imports.** `from module import *` is banned everywhere.

23. **Generated code must never call `eval()`, `exec()`, or `importlib.import_module()`** to load other generated files. Each generated file is self-contained.

24. **Circular imports are build failures.** If two subsystems need each other, extract the shared type into a `_types.py` or `_protocols.py` module that both import.

---

## 8. Comment and Documentation Rules

25. **Every public class and function has a docstring.** Use Google-style format:

    ```python
    def reach_quorum(votes: list[Vote], threshold: int) -> bool:
        """Determine whether the vote set meets the quorum threshold.

        Args:
            votes: Collected votes from participating agents.
            threshold: Minimum number of agreeing votes required.

        Returns:
            True if quorum is reached, False otherwise.

        Raises:
            ConsensusError: If any vote has an invalid signature.
        """
    ```

26. **Inline comments explain _why_, not _what_.** If the code needs a _what_ comment, refactor the code instead.

27. **TODO format:** `# TODO(engineer_id): description — FORGE-{ticket}`. TODOs without a ticket number are rejected in review.

---

## 9. ConsensusDevAgent-Specific Patterns

### 9.1 Code-Fence Sanitisation

28. **The `_strip_code_fences()` function must be identical across all five modules that use it.** Any change to sanitisation logic is applied to all five simultaneously in a single PR.

29. **`_strip_code_fences()` contract:**
    - Accept an empty string or `None` → return the value unchanged.
    - Preserve trailing newline on non-empty output.
    - Do not modify code that contains no fences or Unicode replacement characters.
    - Must be synchronous (no `async`).

### 9.2 Generated File Rules

30. **Every generated file must be complete and self-contained.**
    