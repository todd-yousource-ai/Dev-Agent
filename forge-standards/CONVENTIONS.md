

# Code Conventions — Forge Platform

> Authoritative coding standards for all Forge subsystems and the ConsensusDevAgent pipeline.
> Every rule is mandatory unless explicitly marked **(advisory)**.

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

2. **Python files** use `snake_case.py`. Never uppercase, never hyphens.
3. **TypeScript/Swift files** use `PascalCase.ts` / `PascalCase.swift` for classes and components, `camelCase.ts` for pure-function utility modules.
4. **Test files** are named `test_<module_name>.py` (Python) or `<ModuleName>.test.ts` (TypeScript). The test file must live at the same relative depth under `tests/` as the source file lives under `src/`.
5. **No file may exceed 500 lines.** Split into sub-modules before reaching this limit.
6. **Directory `__init__.py` files** export the public API of the package and nothing else. Keep them under 30 lines.

---

## 2. Branch Naming

7. **All agent-created branches** must follow:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — the operator or agent identity string (lowercase, no spaces).
   - `subsystem_slug` — one of: `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, `connector`.
   - `N` — zero-padded three-digit PR sequence number.
   - `title_slug` — kebab-case summary, max 48 characters.

   Example: `forge-agent/build/eng-042/dtl/pr-007-add-label-validation`

8. **Manual branches** by human engineers follow `{username}/{subsystem_slug}/{short-description}`.

---

## 3. Class and Function Naming

9. **Python classes** — `PascalCase`. Suffix with the pattern role when applicable: `*Service`, `*Handler`, `*Strategy`, `*Error`.
10. **Python functions and methods** — `snake_case`. Prefix private helpers with a single underscore.
11. **TypeScript/Swift classes and protocols** — `PascalCase`.
12. **Constants** — `UPPER_SNAKE_CASE`, defined at module level or in a dedicated `constants.py` / `constants.ts`.
13. **Boolean variables and functions** — prefix with `is_`, `has_`, `can_`, or `should_` (Python) / `is`, `has`, `can`, `should` (TS/Swift).
14. **Dataclass / model fields** — `snake_case` in Python, `camelCase` in TypeScript. Never abbreviate below 3 characters except universally understood terms (`id`, `url`, `db`).

---

## 4. Accessibility Identifier Naming (macOS / SwiftUI)

15. All interactive SwiftUI elements **must** have an `.accessibilityIdentifier()`.
16. Identifiers follow the pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    | Example | Breakdown |
    |---|---|
    | `auth-touchid-button` | module=auth, component=touchid, role=button |
    | `settings-anthropic-key-field` | module=settings, component=anthropic-key, role=field |
    | `navigator-project-row-{projectId}` | dynamic context appended |
    | `stream-gate-yes-button-{gateId}` | dynamic context appended |

17. Dynamic segments use the entity's canonical ID. Never use array indices as identifiers.

---

## 5. Error and Exception Patterns

18. **Every subsystem defines its own exception hierarchy** rooted in a single base:

    ```python
    # src/dtl/exceptions.py
    class DTLError(Exception):
        """Base for all DTL exceptions."""

    class LabelValidationError(DTLError): ...
    class LabelNotFoundError(DTLError): ...
    ```

19. **Never catch bare `Exception`** except at the outermost request/event boundary.
20. **Error messages must be structured.** Include `what`, `why`, and `action`:

    ```python
    raise LabelValidationError(
        f"Label '{label_id}' failed schema check: "
        f"field 'scope' is required. "
        f"Re-run with a valid TrustLabel payload."
    )
    ```

21. **All I/O boundaries** (network, file, subprocess) must be wrapped in a `try/except` that converts raw OS/library errors into domain-specific exceptions from rule 18.
22. **Retriable operations** use an explicit `max_retries` parameter (never infinite) and exponential backoff with jitter.

---

## 6. Path Security

23. **Validate every path before any write operation.** No exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

24. **Never construct write paths via string concatenation.** Use `pathlib.Path` and resolve before validation.
25. `validate_write_path` must reject any path containing `..`, symlink escape, or destinations outside the project workspace root.

---

## 7. Import and Module Organisation

26. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src.*`, `sdk.*`)
    4. Local relative imports

    Separate each group with a blank line.

27. **No wildcard imports** (`from x import *`) anywhere.
28. **Circular imports are a build-breaking error.** If two modules need each other, extract shared types into a `_types.py` or `protocols.py` module.
29. **Lazy imports** are permitted only when a module has a heavy load cost (e.g., ML model). Mark with `# lazy: heavy dependency`.
30. **Re-exports** happen only in `__init__.py` via an explicit `__all__` list.

---

## 8. Comment and Documentation Rules

31. **Every public class, function, and module** must have a docstring (Google style for Python, TSDoc for TypeScript).

    ```python
    def resolve_label(label_id: str, version: int | None = None) -> TrustLabel:
        """Fetch and validate a TrustLabel by ID.

        Args:
            label_id: Canonical label identifier.
            version: Pin to a specific version. Defaults to latest.

        Returns:
            Validated TrustLabel instance.

        Raises:
            LabelNotFoundError: If label_id does not exist.
            LabelValidationError: If the stored label fails schema check.
        """
    ```

32. **Inline comments** explain *why*, never *what*. If the *what* is unclear, rename the variable or extract a function.
33. **TODO format**: `# TODO(engineer_id): <description> — tracked in <issue-url>`. TODOs without an issue link are forbidden in `main`.
34. **No commented-out code** in `main`. Use version control history.

---

## 9. ConsensusDevAgent-Specific Patterns

### 9.1 Pipeline Dataclass Contracts

35. The canonical pipeline entity dataclass **must** contain at minimum:

    ```python
    @dataclasses.dataclass
    class BuildEntity:
        intent: str                  # Raw operator intent