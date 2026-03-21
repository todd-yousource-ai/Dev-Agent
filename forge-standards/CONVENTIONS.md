

# Code Conventions — Forge Platform

> Canonical reference for all contributors and agents operating within the Forge mono-repo.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout.** Top-level source directories use short, lowercase acronyms that map 1-to-1 with subsystems:

   ```
   src/cal/           – Conversation Abstraction Layer
   src/dtl/           – Data Trust Label
   src/trustflow/     – TrustFlow audit stream
   src/vtz/           – Virtual Trust Zone enforcement
   src/trustlock/     – Cryptographic machine identity (TPM-anchored)
   src/mcp/           – MCP Policy Engine
   src/rewind/        – Forge Rewind replay engine
   sdk/connector/     – Forge Connector SDK
   ```

2. **Test mirror rule.** Every test directory mirrors `src/` exactly:

   ```
   tests/cal/
   tests/dtl/
   tests/trustflow/
   ...
   ```

3. **File names** are `snake_case`, all lowercase, no hyphens:
   `consensus_engine.py`, `trust_label_schema.py`.

4. **No single-letter or ambiguous file names.** `utils.py` is banned at the repo root. Scope it: `src/cal/cal_utils.py`.

5. **Generated files** carry a `.gen.` infix so they are instantly recognisable:
   `build_map.gen.json`, `schema.gen.py`.

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Suffix with role when the role is not obvious:
   `ConsensusDevAgent`, `TrustFlowAuditor`, `BuildMapResolver`.

7. **Functions and methods:** `snake_case`. Start with a verb:
   `validate_write_path()`, `fetch_build_map()`, `strip_code_fences()`.

8. **Constants:** `UPPER_SNAKE_CASE`, defined at module level:
   `MAX_RETRIES = 3`, `DEFAULT_GATE_TIMEOUT_S = 30`.

9. **Private members:** Single leading underscore `_internal_method()`. Double underscore name-mangling is prohibited unless solving a concrete inheritance collision.

10. **Boolean variables and functions** use `is_`, `has_`, `can_`, or `should_` prefixes:
    `is_authenticated`, `has_valid_signature()`.

---

## 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a per-subsystem base that itself inherits `Exception`:

    ```python
    # src/cal/exceptions.py
    class CALError(Exception): ...
    class CALTimeoutError(CALError): ...
    ```

12. **Never catch bare `Exception` in production code** unless re-raising or logging-and-raising. Catch the narrowest type possible.

13. **Error messages** must include the subsystem tag and be machine-parseable:

    ```python
    raise PathTraversalError(f"[vtz] blocked write: {user_path!r} escapes sandbox")
    ```

14. **Graceful `None` returns vs. exceptions.** Functions that query optional state (e.g., `fetch_build_map()` when no map exists yet) must return `None` — **never raise**. Document this in the docstring:

    ```python
    def fetch_build_map() -> BuildMap | None:
        """Return the current build map, or None if no map exists yet."""
    ```

15. **`validate_write_path()` is mandatory before every file-system write**, no exceptions:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

---

## 4. Import and Module Organisation

16. **Import order** (enforced by `isort` with the profile below):
    1. Standard library
    2. Third-party packages
    3. Forge `src/` modules (absolute imports)
    4. Local relative imports

    Blank line between each group.

17. **Absolute imports only** at the package boundary. Relative imports (`from . import x`) are permitted only *within* a subsystem package.

18. **No dynamic loading in generated code.** Generated files must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

19. **No circular imports.** If two subsystems need each other, extract the shared type into a `_types` or `_protocol` module.

---

## 5. Comment and Documentation Rules

20. **Every public function and class** has a docstring (Google style):

    ```python
    def strip_code_fences(text: str | None) -> str | None:
        """Remove Markdown code fences and stray Unicode from generated output.

        Args:
            text: Raw generated text, or None.

        Returns:
            Cleaned text with trailing newline preserved, or the input
            unchanged if it is empty / None / has no fences.
        """
    ```

21. **Inline comments** explain *why*, not *what*. If the *what* is not obvious from the code, rename the variable or extract a function instead.

22. **TODO format:** `# TODO(engineer_id): description — FORGE-<ticket>`. TODOs without a ticket number are rejected in CI.

23. **No commented-out code** in `main` or any release branch.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Branch Naming (mandatory)

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

Examples:
```
forge-agent/build/e017/cal/pr-001-init-conversation-layer
forge-agent/build/e042/trustflow/pr-003-add-audit-sink
```

### 6.2 Generated Code Rules

24. **Every generated file is self-contained.** It must not exist solely to call or dispatch to another generated file.

25. **No runtime placeholders.** Template variables must be resolved at generation time; the output must be valid, runnable code.

26. **Canonical `_strip_code_fences()` implementation.** The function exists in exactly five modules. All five copies must be **byte-identical**. CI enforces this via checksum comparison. The function contract:

    | Input | Output |
    |---|---|
    | `None` | `None` (returned unchanged) |
    | `""` | `""` (returned unchanged) |
    | Text without fences or special Unicode | Returned unchanged |
    | Text with fences | Fences removed, trailing newline preserved |

    The function must be **synchronous** — no `async`.

27. **Path security in agents.** Every agent action that writes to disk must call `validate_write_path()` (rule 15). There are zero exceptions for "known-safe" paths.

### 6.3 macOS UI — Accessibility Identifier Convention

28. **Pattern:** `{module}-{component}-{role}-{context?}`
    Set via `.accessibilityIdentifier()` on **all** interactive elements.

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

29. Identifiers use **kebab-case**, never camelCase or snake_case.

### 6.4 Testing

30. **Test file naming:** `test_<module_under_test>.py`, placed in the mirrored `tests/` directory (rule 2).

31. **Live-system tests** (e.g., `TestBuildMapLive`) must verify grac