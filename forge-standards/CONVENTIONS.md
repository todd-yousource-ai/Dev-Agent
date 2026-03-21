

# Code Conventions — Forge Platform

> **Scope:** All code in the Forge mono-repo, with extra rules for the ConsensusDevAgent subsystem. Every rule is mandatory unless marked *(recommended)*.

---

## 1. File and Directory Naming

1. **Source layout.** Top-level directories use the canonical short names:

   | Directory | Purpose |
   |---|---|
   | `src/cal/` | Conversation Abstraction Layer |
   | `src/dtl/` | Data Trust Label components |
   | `src/trustflow/` | TrustFlow audit stream |
   | `src/vtz/` | Virtual Trust Zone enforcement |
   | `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
   | `src/mcp/` | MCP Policy Engine |
   | `src/rewind/` | Forge Rewind replay engine |
   | `sdk/connector/` | Forge Connector SDK |
   | `tests/<subsystem>/` | Tests — must mirror `src/` structure exactly |

2. **Python files:** `snake_case.py`. Maximum 3 words before the extension (e.g., `build_map_loader.py`, not `consensus_dev_agent_build_map_loader.py`).

3. **Swift files:** `PascalCase.swift`, one primary type per file. File name matches the type name.

4. **No dots in directory names.** Use hyphens for multi-word directories in non-Python contexts (e.g., `forge-agent/`). Use underscores for Python packages.

5. **Test files:** Prefix with `test_` (Python) or suffix with `Tests` (Swift). Place them at the **exact mirror path** under `tests/`.

   ```
   src/cal/session_manager.py   →  tests/cal/test_session_manager.py
   src/dtl/label_parser.py      →  tests/dtl/test_label_parser.py
   ```

---

## 2. Branch Naming

6. **Agent branches** must follow this pattern exactly:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id`: lowercase GitHub handle or numeric ID.
   - `subsystem_slug`: matches a `src/` directory name (e.g., `cal`, `trustflow`).
   - `N`: zero-padded to 3 digits (`001`, `012`).
   - `title_slug`: lowercase, hyphen-separated, max 5 words.

   Example: `forge-agent/build/mchen/trustflow/pr-007-add-audit-sink`

7. **Human branches** use `feat/`, `fix/`, or `chore/` prefixes with the same subsystem slug: `feat/vtz/enforce-zone-boundary`.

---

## 3. Class and Function Naming

8. **Python classes:** `PascalCase`. Suffix with the architectural role when the role is not obvious: `SessionManager`, `AuditSinkProtocol`, `LabelParserError`.

9. **Python functions and methods:** `snake_case`. Start with a verb: `fetch_build_map()`, `validate_write_path()`, `strip_code_fences()`.

10. **Swift types and protocols:** `PascalCase`. Protocols use adjective or `-able`/`-ible` suffixes where possible: `Trustable`, `GateResolvable`.

11. **Constants:** `UPPER_SNAKE_CASE` in Python; `static let camelCase` in Swift.

12. **Private members:** Prefix with a single underscore in Python (`_internal_state`). Use `private` access control in Swift.

13. **axIdentifier convention (Swift/macOS).** Set `.accessibilityIdentifier()` on **every** interactive element. Format:

    ```
    {module}-{component}-{role}-{context?}
    ```

    Examples:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    "stream-gate-skip-button-{gateId}"
    "stream-gate-stop-button-{gateId}"
    ```

    All segments are lowercase, hyphen-separated. Dynamic IDs are appended after the last hyphen.

---

## 4. Error and Exception Patterns

14. **Custom exceptions** inherit from a single base per subsystem:

    ```python
    class TrustFlowError(ForgeError): ...
    class AuditSinkConnectionError(TrustFlowError): ...
    ```

15. **Never catch bare `Exception`** except at a top-level boundary (CLI entry point, HTTP handler). Always re-raise or log with traceback.

16. **Error messages** must include: (a) what failed, (b) the input that caused it, (c) a suggested fix when possible.

    ```python
    raise PathTraversalError(
        f"Write blocked: '{user_path}' resolves outside sandbox. "
        f"Resolved to '{resolved}'. Use a relative path under the project root."
    )
    ```

17. **`fetch_build_map()` and similar nullable fetchers** must return `None` gracefully when the resource does not yet exist. They must **never** raise an exception for a missing resource during the first N PRs of a build.

---

## 5. Path Security

18. **Validate every write path before any filesystem write.** No exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError
    ```

19. `validate_write_path` must reject: path traversal (`..`), absolute paths outside the sandbox, and symlinks that escape the project root.

20. Never construct write paths with string concatenation. Use `pathlib.Path` and call `validate_write_path` on the result.

---

## 6. Import and Module Organisation

21. **Import order** (enforce with `isort`, profile `black`):

    1. Standard library
    2. Third-party packages
    3. Forge platform (`src.*`)
    4. Local/relative imports

    Separate each group with a blank line.

22. **No wildcard imports** (`from module import *`) anywhere.

23. **Relative imports** only within the same subsystem package. Cross-subsystem imports use absolute paths: `from src.trustflow.audit_sink import AuditSink`.

24. **Lazy imports** are allowed for heavy optional dependencies. Wrap in a function, document why.

25. **Generated code must never** use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files. Every generated file must be complete and self-contained — no runtime placeholders, no dispatch-only stubs.

---

## 7. Comment and Documentation Rules

26. **Module docstring** required in every Python file. One sentence stating purpose, then a blank line, then details if needed.

27. **Public functions and classes** require a docstring. Use Google-style:

    ```python
    def fetch_build_map(project_id: str) -> Optional[BuildMap]:
        """Fetch the current build map for a project.

        Returns None if no map has been generated yet (expected for
        the first 5 PRs of any build).

        Args:
            project_id: The Forge project identifier.

        Returns:
            The build map, or None if not yet available.
        """
    ```

28. **Inline comments** explain *why*, not *what*. If the code needs a *what* comment, simplify the code instead.

29. **TODO format:** `# TODO(username): description — JIRA-123` or `# TODO(username): description` if no ticket exists yet. Never leave anonymous TODOs.

30. **No commented-out code** in `main` or any release branch. Use version control.

---

## 8. ConsensusDevAgent-Specific Patterns

31. **`_strip_code_fences()` must be identical** across all five modules that define it. Any change to sanitization logic must be applied to all five