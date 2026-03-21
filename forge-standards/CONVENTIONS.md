

# Code Conventions — Forge Platform

> **Scope**: All code in the Forge monorepo. §6 adds rules specific to the ConsensusDevAgent subsystem.
> Version: 1.0 · Effective immediately · Violations block merge.

---

## 1. File and Directory Naming

1. **Source layout** — every subsystem lives under its canonical prefix. Never create parallel roots.

   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   tests/<subsystem>/ # Mirrors src/ structure exactly
   ```

2. **Test mirror rule** — for every file `src/cal/gate_resolver.py`, a corresponding `tests/cal/test_gate_resolver.py` must exist. No exceptions.

3. **File names** — `snake_case` only. No hyphens, no uppercase, no spaces.
   ```
   gate_resolver.py        ✓
   GateResolver.py         ✗
   gate-resolver.py        ✗
   ```

4. **Module `__init__.py`** — every package directory must contain one. It may be empty but must exist.

5. **Generated files** — suffix with `_gen.py` (e.g., `trust_policy_gen.py`). Never manually edit a `_gen.py` file.

6. **Configuration / data files** — use `.toml` for config, `.json` for serialised data, `.yaml` only for CI pipeline definitions.

---

## 2. Class and Function Naming

7. **Classes** — `PascalCase`. Acronyms three letters or longer are title-cased: `McpPolicyEngine`, not `MCPPolicyEngine`. Two-letter acronyms stay uppercase: `DTLabel`.

8. **Functions and methods** — `snake_case`. Verbs first: `fetch_build_map()`, `validate_write_path()`, `resolve_gate()`.

9. **Private members** — single leading underscore `_strip_code_fences()`. Never use double underscore name-mangling unless explicitly avoiding subclass collision.

10. **Constants** — `UPPER_SNAKE_CASE`, defined at module level: `MAX_RETRY_COUNT = 3`.

11. **Type aliases** — `PascalCase` with a `T` suffix only when the alias is generic (`GateResultT`). Concrete aliases drop the suffix (`TrustScore`).

12. **Boolean variables and parameters** — prefix with `is_`, `has_`, `should_`, or `can_`: `is_verified`, `has_quorum`.

13. **axIdentifier naming (Swift / macOS UI)** — every interactive element must set `.accessibilityIdentifier()` following this pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Examples:
    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

    All tokens are lowercase kebab-case. The optional `{context}` carries a dynamic ID.

---

## 3. Error and Exception Patterns

14. **Custom exceptions** — inherit from a single `ForgeError` base class defined in `src/forge_errors.py`.

    ```python
    class ForgeError(Exception):
        """Base for all Forge-raised exceptions."""

    class PathTraversalError(ForgeError): ...
    class QuorumNotReachedError(ForgeError): ...
    ```

15. **Never catch bare `Exception`** unless re-raising or logging-then-raising. Catch the narrowest type.

    ```python
    # ✓
    except QuorumNotReachedError as exc:
        log.error("Quorum failed: %s", exc)
        raise

    # ✗
    except Exception:
        pass
    ```

16. **Error messages** — start with a lowercase verb, include the failing value, omit trailing periods.

    ```python
    raise PathTraversalError(f"blocked write to disallowed path: {user_path!r}")
    ```

17. **Return `None` for expected absence; raise for unexpected failure.** `fetch_build_map()` returns `None` when no map exists yet (first 5 PRs of a build). It must never raise.

18. **Validation before I/O** — validate every user- or agent-supplied path before any write:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

    No code path may skip this call. Agent-generated paths are treated as user-supplied.

---

## 4. Import and Module Organisation

19. **Import order** (enforced by `isort` with `profile = black`):
    1. Standard library
    2. Third-party packages
    3. Forge-internal (`src/…`)
    4. Local relative imports

    Separate each group with a single blank line.

20. **Absolute imports only** between subsystems:

    ```python
    # ✓  from another subsystem
    from src.vtz.enforcer import enforce_zone

    # ✗
    from ...vtz.enforcer import enforce_zone
    ```

21. **Relative imports allowed** within the same package only, and only one level deep:

    ```python
    # inside src/cal/
    from .gate_resolver import resolve_gate   # ✓
    from ..dtl.labels import DTLabel          # ✗ — use absolute
    ```

22. **No runtime dynamic loading in generated code** — generated files must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

23. **No wildcard imports** — `from module import *` is forbidden everywhere.

24. **Lazy imports** — permitted only inside functions when the import is expensive and the function is rarely called. Add a comment: `# lazy: heavy dependency`.

---

## 5. Comment and Documentation Rules

25. **Module docstring** — every `.py` file starts with a one-line module docstring:

    ```python
    """TrustFlow event emitter for gate resolution outcomes."""
    ```

26. **Public function / method docstring** — Google-style, including `Args`, `Returns`, and `Raises` sections when applicable.

    ```python
    def fetch_build_map(project_id: str) -> dict | None:
        """Fetch the current build map for a project.

        Args:
            project_id: UUID of the target project.

        Returns:
            The build map dict, or None if no map exists yet.

        Raises:
            ForgeError: If the backing store is unreachable.
        """
    ```

27. **Inline comments** — explain *why*, never *what*. Place on the line above the code, not at end-of-line (unless the comment is ≤ 30 chars).

28. **TODO format** — `# TODO(username): description — TICKET-123`. TODOs without a ticket are rejected in review.

29. **No commented-out code** — delete it. Git has history.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Branch Naming (mandatory)

30. Every agent-created branch must follow this exact template:

    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

    - `engineer_id` — the numeric or short-string ID of the requesting engineer.
    - `subsystem_slug` — matches a directory name under `src/` (e.g., `cal`, `vtz`).
    - `