# Code Conventions — Forge Platform

*Authoritative reference for all code contributed by human engineers and ConsensusDevAgent builds.*
*Last updated: 2025-07-10 · Canonical location: `CONVENTIONS.md` at repo root.*

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly.**

| Path prefix | Subsystem |
|---|---|
| `src/cal/` | Conversation Abstraction Layer |
| `src/dtl/` | Data Trust Label |
| `src/trustflow/` | TrustFlow audit stream |
| `src/vtz/` | Virtual Trust Zone enforcement |
| `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
| `src/mcp/` | MCP Policy Engine |
| `src/rewind/` | Forge Rewind replay engine |
| `sdk/connector/` | Forge Connector SDK |
| `tests/<subsystem>/` | Tests — mirrors `src/` structure exactly |

2. **Python files** use `snake_case.py`. Never uppercase, never hyphens.
   ```
   src/dtl/label_validator.py    ✓
   src/dtl/LabelValidator.py     ✗
   src/dtl/label-validator.py    ✗
   ```

3. **TypeScript / Swift files** use `PascalCase` for component/class files, `camelCase` for utility modules.
   ```
   StreamGateCard.swift          ✓  (component)
   formatTimestamp.ts            ✓  (utility)
   ```

4. **Test files** are named `test_<module>.py` (Python) or `<Module>.test.ts` (TypeScript). Every source module in `src/<subsystem>/` must have a corresponding test file in `tests/<subsystem>/`.

5. **No file may exceed 500 lines.** If it does, split by responsibility.

---

## 2. Branch Naming

6. **All agent-authored branches** follow this exact template — no exceptions:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   Example:
   ```
   forge-agent/build/eng-042/dtl/pr-007-add-label-expiry
   ```

7. `subsystem_slug` must match one of the directory names in rule 1 (`cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`).

8. `title_slug` is lowercase, hyphen-separated, max 48 characters.

---

## 3. Class and Function Naming

9. **Python** — PEP 8 strictly:
   - Classes: `PascalCase` — `LabelValidator`, `ConsensusRound`
   - Functions / methods: `snake_case` — `validate_label()`, `run_consensus()`
   - Constants: `UPPER_SNAKE` — `MAX_RETRY_COUNT`, `DEFAULT_QUORUM`
   - Private members: single leading underscore — `_internal_state`

10. **TypeScript** — classes and interfaces `PascalCase`; functions and variables `camelCase`; constants `UPPER_SNAKE`.

11. **Swift / macOS shell** — types `PascalCase`; properties and methods `camelCase`.

12. **Accessibility identifiers** (macOS application shell) follow the pattern `{module}-{component}-{role}-{context?}` and must be set via `.accessibilityIdentifier()` on every interactive element:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    "stream-gate-skip-button-{gateId}"
    "stream-gate-stop-button-{gateId}"
    ```

---

## 4. Error and Exception Patterns

13. **Every subsystem defines its own exception hierarchy** rooted in a single base class:

    ```python
    # src/dtl/exceptions.py
    class DTLError(Exception):
        """Base for all DTL exceptions."""

    class LabelExpiredError(DTLError): ...
    class LabelSchemaError(DTLError): ...
    ```

14. **Never catch bare `Exception` or `BaseException`** unless immediately re-raising or logging and re-raising.

15. **Error messages are structured.** Include `subsystem`, `operation`, and `detail`:

    ```python
    raise LabelSchemaError(
        f"[dtl.validate] Schema version mismatch: "
        f"expected={expected}, got={actual}"
    )
    ```

16. **All I/O-facing functions** (network, file, subprocess) must wrap calls in try/except, log the failure with context, and re-raise as a subsystem-specific exception.

---

## 5. Path Security

17. **Validate every path before any write operation.** This is non-negotiable — agent and human code alike.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

18. Never construct write paths with string concatenation or f-strings from untrusted input without passing through `validate_write_path` first.

19. Read paths from external input must also be validated via `validate_read_path` to prevent information disclosure.

---

## 6. Import and Module Organisation

20. **Import order** (enforced by `isort` with the profile below):

    ```
    # 1. stdlib
    import os
    from pathlib import Path

    # 2. third-party
    import httpx
    import pydantic

    # 3. forge platform shared
    from path_security import validate_write_path

    # 4. same subsystem
    from .exceptions import DTLError
    from .label_validator import LabelValidator
    ```

    A blank line separates each group.

21. **No wildcard imports** (`from x import *`) anywhere.

22. **Circular imports** are a merge-blocking defect. Use interface protocols or deferred imports if unavoidable.

23. **Dataclasses over dicts** for any structure with more than two fields. Use `@dataclass(frozen=True)` or Pydantic `BaseModel` as appropriate. The canonical build-pipeline entity is a dataclass:

    ```python
    @dataclass
    class BuildEntity:
        intent: str
        subsystem: str
        scope_statement: str
        branch_prefix: str
        relevant_docs: list[str]
    ```

---

## 7. Comment and Documentation Rules

24. **Every public class and function** has a docstring. Use Google-style format:

    ```python
    def validate_label(raw: dict, schema_version: int = 2) -> Label:
        """Parse and validate a raw label dict against the DTL schema.

        Args:
            raw: Untrusted label payload from external source.
            schema_version: Target schema version (default 2).

        Returns:
            A validated Label instance.

        Raises:
            LabelSchemaError: If the payload does not conform.
        """
    ```

25. **Inline comments** explain *why*, never *what*. If you need to explain what the code does, refactor the code.

26. **TODO / FIXME / HACK** comments must include an owner and a tracking reference:

    ```python
    # TODO(eng-042): Replace polling with SSE once TrustFlow v2 ships — FORGE-1184
    ```

27. **No commented-out code** in main or release branches. Use version control.

---

## 8. ConsensusDevAgent-Specific Patterns

### 8.1 Test Generation Requirements

28. **Minimum test coverage per public surface:**
    - One happy-path test.
    - One edge-case test.
    - One error/failure-case test.

29. **Framework