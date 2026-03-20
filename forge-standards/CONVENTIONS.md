# Code Conventions — Forge Platform

> Authoritative coding standards for the Forge platform and the **ConsensusDevAgent** subsystem.
> Every rule is mandatory unless explicitly marked *(advisory)*.

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

2. **Python files** use `snake_case.py`. No hyphens in importable module names.

3. **TypeScript files** use `kebab-case.ts` for source, `kebab-case.test.ts` for tests.

4. **Go files** use `snake_case.go` per stdlib convention.

5. **Test files** live under `tests/<subsystem>/` and mirror the source path:
   - Source: `src/dtl/label_validator.py`
   - Test:   `tests/dtl/test_label_validator.py`

6. **No file shall exceed 500 lines.** Split at logical boundaries before hitting that limit.

7. **Configuration and data files** use `kebab-case` with appropriate extensions: `.yaml`, `.json`, `.toml`.

---

## 2. Branch Naming

8. **All agent-created branches** follow this exact pattern:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — the assigned engineer identifier (lowercase, no spaces).
   - `subsystem_slug` — matches the directory name under `src/` (e.g., `dtl`, `cal`, `vtz`).
   - `N` — zero-padded to three digits (`001`, `002`, …).
   - `title_slug` — lowercase, hyphen-delimited summary ≤ 40 characters.

   Example: `forge-agent/build/eng-042/trustflow/pr-007-add-audit-replay`

9. **Human branches** follow `<username>/<subsystem>/<short-description>`.

---

## 3. Class and Function Naming

10. **Python** — classes: `PascalCase`; functions/methods: `snake_case`; constants: `UPPER_SNAKE_CASE`.

11. **TypeScript** — classes/interfaces: `PascalCase`; functions/variables: `camelCase`; constants: `UPPER_SNAKE_CASE`; type aliases: `PascalCase`.

12. **Go** — exported identifiers: `PascalCase`; unexported: `camelCase`. Acronyms stay uppercase (`HTTPClient`, not `HttpClient`).

13. **Prefix private helpers** with a single underscore in Python (`_resolve_scope`). Never use double underscores for name mangling unless absolutely required.

14. **Boolean variables and functions** start with `is_`, `has_`, `can_`, or `should_`:
    ```python
    is_validated: bool
    has_quorum: bool
    def can_merge(pr: PullRequest) -> bool: ...
    ```

15. **Factory functions** are named `create_<thing>` or `build_<thing>`. Never `make_` or `new_`.

16. **Dataclass names** describe the entity, not the role: `BuildIntent`, not `BuildIntentData` or `BuildIntentDataclass`.

---

## 4. Error and Exception Patterns

17. **All custom exceptions** inherit from a single project root:
    ```python
    class ForgeError(Exception):
        """Base for all Forge-originated errors."""

    class ConsensusError(ForgeError): ...
    class PathTraversalError(ForgeError): ...
    class QuorumNotReachedError(ConsensusError): ...
    ```

18. **Never catch bare `Exception` or `BaseException`** unless re-raising. Catch the narrowest type.

19. **Error messages** are lowercase, do not end with a period, and include the failing value:
    ```python
    raise PathTraversalError(f"path escapes workspace: {user_path!r}")
    ```

20. **Every I/O call** (network, file, subprocess) must be wrapped in an explicit `try/except` with a typed re-raise or structured log.

21. **Return errors, don't print them.** Functions return `Result` types or raise; they never call `print()` or `sys.exit()` for error signalling.

---

## 5. Path Security

22. **Validate paths before ANY write operation.** No exceptions.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    ```

23. **Never construct file paths with string concatenation or f-strings.** Use `pathlib.Path` / `os.path.join`, then pass through `validate_write_path`.

24. **Symlink resolution** is mandatory before writing. `validate_write_path` must call `Path.resolve()` and confirm the result is inside the workspace root.

---

## 6. Import and Module Organisation

25. **Import order** (enforced by `isort` with the `black` profile):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src.*`, `sdk.*`)
    4. Local / relative imports

    Separate each group with a single blank line.

26. **No wildcard imports** (`from module import *`). Ever.

27. **Relative imports** are permitted only within the same subsystem package (e.g., inside `src/dtl/`). Cross-subsystem imports use absolute paths:
    ```python
    # Good (cross-subsystem)
    from src.vtz.enforcer import enforce_zone

    # Good (intra-subsystem)
    from .label_validator import validate_label
    ```

28. **Circular imports** are a build-breaking defect. If two modules need each other, extract the shared type into a `_types.py` within the subsystem.

29. **Lazy imports** for heavy dependencies (ML models, large SDKs) are allowed inside functions, with a comment explaining why.

---

## 7. Comment and Documentation Rules

30. **Every public class and function** has a docstring. Use Google-style for Python:
    ```python
    def resolve_scope(intent: str, docs: list[str]) -> ScopeStatement:
        """Derive a scope statement from operator intent and matched docs.

        Args:
            intent: Raw operator intent string.
            docs: List of document names filtered by relevance.

        Returns:
            A ScopeStatement with subsystem and scope text populated.

        Raises:
            ConsensusError: If no docs match the intent.
        """
    ```

31. **Inline comments** explain *why*, never *what*. If the "what" is unclear, rename the variable or function instead.

32. **TODO format** — always include the engineer ID and a ticket/issue reference:
    ```python
    # TODO(eng-042): handle rate-limit retry — FORGE-1184
    ```

33. **No commented-out code** in `main` or any long-lived branch. Delete it; Git remembers.

34. **Module-level docstrings** are required for every `__init__.py` that exports public symbols. State what the package provides in one sentence.

---

## 8. ConsensusDevAgent-Specific Patterns

### 8.1 Build Intent Dataclass

35. **The `BuildIntent` dataclass** is the single source of truth entering the pipeline. Required fields:

    ```python
    @dataclass(frozen=True)
    class BuildIntent:
        intent:          str            # Raw operator intent
        subsystem:       str            # e.g., "DTL", "