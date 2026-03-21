

# Code Conventions — Forge Platform

Version: 1.0
Scope: All Forge subsystems, with dedicated section for ConsensusDevAgent

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

2. **Test directories must mirror source directories 1-to-1.** A file at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

3. **All filenames are `snake_case`, lowercase, no hyphens.** Example: `trust_label_validator.py`, not `TrustLabelValidator.py` or `trust-label-validator.py`.

4. **No generic filenames.** Banned: `utils.py`, `helpers.py`, `common.py`, `misc.py`. Name the file after the capability it provides (e.g., `path_security.py`, `fence_sanitizer.py`).

5. **Configuration files live at repo root or in a top-level `config/` directory.** Never nest config files inside `src/`.

6. **Branch naming is mandatory and follows this format:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: GitHub username or agent identifier.
   - `subsystem_slug`: lowercase hyphenated subsystem (e.g., `consensus-engine`, `trust-flow`).
   - `N`: zero-padded three-digit PR sequence number.
   - `title_slug`: lowercase hyphenated summary, max 40 characters.

   Example: `forge-agent/build/jdoe/consensus-engine/pr-007-add-quorum-resolver`

---

## 2. Class and Function Naming

7. **Classes use `PascalCase`.** Example: `ConsensusDevAgent`, `TrustLabelValidator`.

8. **Functions and methods use `snake_case`.** Example: `resolve_quorum()`, `validate_write_path()`.

9. **Private functions are prefixed with a single underscore.** Example: `_strip_code_fences()`. Double underscores are reserved for Python name-mangling and must not be used for simple privacy.

10. **Boolean-returning functions start with `is_`, `has_`, `can_`, or `should_`.** Example: `is_quorum_met()`, `has_valid_signature()`.

11. **Constants are `UPPER_SNAKE_CASE` and defined at module level.** Example: `MAX_RETRY_COUNT = 3`, `DEFAULT_TIMEOUT_S = 30`.

12. **Acronyms in identifiers follow PascalCase rules.** Write `McpPolicyEngine`, not `MCPPolicyEngine`. Write `DtlParser`, not `DTLParser`. In snake_case: `mcp_policy_engine`.

13. **axIdentifier strings (macOS UI) follow this convention:**

    ```
    {module}-{component}-{role}-{context?}
    ```

    Set via `.accessibilityIdentifier()` on every interactive element. Examples:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

    Every interactive SwiftUI element without an `accessibilityIdentifier` is a CI failure.

---

## 3. Error and Exception Patterns

14. **Define one exception base class per subsystem.** It lives in `<subsystem>/exceptions.py`.

    ```python
    # src/cal/exceptions.py
    class CalError(Exception):
        """Base exception for the CAL subsystem."""
    ```

15. **All custom exceptions inherit from the subsystem base class.** Never raise bare `Exception`, `ValueError`, or `RuntimeError` for domain errors.

    ```python
    class SessionExpiredError(CalError):
        """Raised when a CAL session token has expired."""
    ```

16. **Exception class names end with `Error`.** Not `Exception`, not `Failure`. Example: `QuorumNotMetError`, `PathTraversalError`.

17. **Include structured context in exceptions.** Pass a human-readable message plus keyword attributes; never format data into the message string alone.

    ```python
    class PathTraversalError(ForgeSecurityError):
        def __init__(self, attempted_path: str, resolved_path: str):
            self.attempted_path = attempted_path
            self.resolved_path = resolved_path
            super().__init__(
                f"Path traversal blocked: {attempted_path!r} resolved to {resolved_path!r}"
            )
    ```

18. **Never silently swallow exceptions.** Every `except` block must log at `WARNING` or above, re-raise, or raise a new domain exception. Bare `except: pass` is a CI lint failure.

19. **`fetch_build_map()` and similar lookup functions return `None` on absence — they must never raise.** This is critical for first-run / empty-state scenarios (first 5 PRs of any build). Document this contract in the docstring.

---

## 4. Import and Module Organisation

20. **Import order (enforced by `isort` with `profile=black`):**

    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/...`)
    4. Local / relative imports

    Separate each group with a single blank line.

21. **Absolute imports for cross-subsystem references.** Use `from src.cal.session import Session`, never `from ...cal.session import Session`.

22. **Relative imports only within the same subsystem.** `from .exceptions import CalError` is fine inside `src/cal/`.

23. **No wildcard imports.** `from module import *` is banned everywhere.

24. **No dynamic code loading in generated files.** Generated files must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files. Every generated file must be complete and self-contained.

25. **Lazy imports are permitted only for optional heavy dependencies** (e.g., ML frameworks) and must be wrapped in a function-scoped import with a comment explaining why.

---

## 5. Comment and Documentation Rules

26. **Every public function, class, and method has a docstring.** Use Google-style docstrings:

    ```python
    def validate_write_path(user_supplied_path: str) -> Path:
        """Validate and resolve a path, blocking directory traversal.

        Args:
            user_supplied_path: The raw path string from untrusted input.

        Returns:
            A resolved, safe Path within the allowed write root.

        Raises:
            PathTraversalError: If the resolved path escapes the write root.
        """
    ```

27. **No TODO without a tracking reference.** Write `# TODO(FORGE-1234): ...` or `# TODO(@username): ...`. Naked `# TODO: fix later` is a lint failure.

28. **Inline comments explain _why_, not _what_.** The code already shows what. Bad: `# increment counter`. Good: `# Retry budget resets after quorum is reached`.

29. **Module-level docstrings are required.** The first line of every `.py` file must be a module docstring describing the file's purpose and which subsystem it belongs to.

30. **Type hints are mandatory on all public function signatures.** Use `from __future__ import annotations` at the top of every file. Return types are never omitted (`-> None` is explicit).

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security

31. **Validate paths