

# Code Conventions — Forge Platform

> Canonical reference for all contributors and autonomous agents operating within the Forge monorepo. Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout.** Production code lives under `src/` in subsystem directories. Each subsystem uses a short, lowercase slug:

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

2. **Test layout mirrors source exactly.** A module at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

3. **File names** are `snake_case`, all lowercase, no hyphens: `trust_label.py`, `gate_resolver.py`.

4. **No single-purpose dispatch files.** Every file must be a complete, self-contained unit. Never create a file whose only job is to import and re-call another file.

5. **Branch naming (mandatory format):**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   Examples:
   ```
   forge-agent/build/e-042/cal/pr-007-session-timeout-fix
   forge-agent/build/e-113/vtz/pr-001-zone-bootstrap
   ```

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Suffix with the pattern role when applicable — `*Engine`, `*Resolver`, `*Handler`, `*Gate`, `*Policy`.

   ```python
   class ConsensusEngine: ...
   class TrustLabelResolver: ...
   class StreamGateHandler: ...
   ```

7. **Functions and methods:** `snake_case`. Verb-first: `validate_quorum()`, `fetch_build_map()`, `strip_code_fences()`.

8. **Constants:** `UPPER_SNAKE_CASE`, defined at module level.

   ```python
   MAX_RETRY_COUNT = 3
   DEFAULT_QUORUM_THRESHOLD = 0.67
   ```

9. **Private internals:** Single leading underscore. Reserve double underscore for name-mangling only when subclass collision is a real risk.

   ```python
   def _strip_code_fences(raw: str) -> str: ...
   ```

10. **axIdentifier naming (macOS UI elements).** Format: `{module}-{component}-{role}-{context?}`. Set via `.accessibilityIdentifier()` on every interactive element.

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

---

## 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a single `ForgeError` base in `src/errors.py`:

    ```python
    class ForgeError(Exception): ...
    class QuorumNotReachedError(ForgeError): ...
    class PathTraversalError(ForgeError): ...
    class TrustZoneViolationError(ForgeError): ...
    ```

12. **Never silently swallow exceptions.** Bare `except:` and `except Exception: pass` are forbidden. Always log or re-raise.

13. **Graceful `None` returns over exceptions for missing-data lookups.** `fetch_build_map()` must return `None` — never raise — when no map exists yet (first ≤5 PRs of any build).

14. **Validate paths before ANY write.** No file-write operation may proceed without traversal validation:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

    This is non-negotiable for agents and human contributors alike.

---

## 4. Import and Module Organisation

15. **Import order** (enforced by `isort` with the profile below):

    ```
    1. stdlib
    2. third-party
    3. forge top-level (`src.*`, `sdk.*`)
    4. local relative
    ```

    Separate each group with a blank line.

16. **No dynamic code loading in generated files.** Generated modules must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

17. **No runtime placeholders in templates.** Generated files must be complete as written — no `{{PLACEHOLDER}}` strings that require a second pass.

18. **Prefer absolute imports** within `src/`:

    ```python
    from src.cal.session import CalSession        # yes
    from ..session import CalSession               # only inside the same subsystem package
    ```

---

## 5. Comment and Documentation Rules

19. **Module docstring** required in every `.py` file. First line: one-sentence purpose. Followed by a blank line and optional details.

    ```python
    """Resolve Data Trust Labels for outbound payloads.

    Implements DTL v2 label resolution including inheritance
    from parent trust zones.
    """
    ```

20. **Public functions and classes** require a docstring with `Args:`, `Returns:`, and `Raises:` sections (Google style).

21. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

22. **TODO format:** `# TODO(engineer_id): description — tracking-ref` . TODOs without an owner are rejected in review.

23. **No commented-out code** in main branch. Use version control history.

---

## 6. ConsensusDevAgent-Specific Patterns

24. **Identical utility functions across agent modules.** `_strip_code_fences()` must be byte-identical in all five modules that use it. A change to one copy requires the same change to all five. The function contract:

    | Input | Output |
    |---|---|
    | `None` | `None` (returned unchanged) |
    | `""` (empty string) | `""` (returned unchanged) |
    | Code without fences/unicode | Returned unmodified |
    | Code with fences | Fences stripped; trailing newline preserved |

    The function must be synchronous — no `async`.

25. **Generation system prohibitions (GENERATION_SYSTEM v2.0):**
    - No `eval()`, `exec()`, or `importlib.import_module()` in generated output.
    - No template files with runtime placeholders.
    - No dispatch-only files (a file that only calls another generated file).
    - Every generated file must be complete and self-contained.

26. **Build map tolerance.** Any function that reads a build map (e.g., `fetch_build_map()`) must handle the absence of that map gracefully by returning `None`. This is the expected state for the first PRs of any build and must never raise an exception.

27. **Agent write safety.** Before performing any filesystem write, agents must call `validate_write_path()` (rule 14). Agents must treat a `PathTraversalError` as a hard stop — no retry, no fallback path.

28. **Agent branch discipline.** Agents must create branches using the exact format in rule 5. Deviations cause CI rejection.

29. **Qu