

# Code Conventions — Forge Platform

_Authoritative coding standards for the Forge platform and ConsensusDevAgent subsystem. Every rule is mandatory unless explicitly marked **[advisory]**._

---

## 1. File and Directory Naming

1. **Source layout.** All production code lives under `src/` in subsystem directories. Each directory is a single, lowercase abbreviation or word:

   ```
   src/cal/           - Conversation Abstraction Layer
   src/dtl/           - Data Trust Label components
   src/trustflow/     - TrustFlow audit stream components
   src/vtz/           - Virtual Trust Zone enforcement
   src/trustlock/     - Cryptographic machine identity (TPM-anchored)
   src/mcp/           - MCP Policy Engine
   src/rewind/        - Forge Rewind replay engine
   sdk/connector/     - Forge Connector SDK
   ```

2. **Test layout mirrors source exactly.** Tests for `src/cal/session.py` live at `tests/cal/test_session.py`. No exceptions.

3. **File names** use `snake_case`, all lowercase, no hyphens: `trust_label.py`, `gate_renderer.swift`. Maximum 40 characters before the extension.

4. **No generic names.** Files named `utils.py`, `helpers.py`, `misc.py`, or `common.py` are prohibited. Name files after the specific capability they provide (e.g., `path_security.py`, `fence_sanitizer.py`).

5. **Branch naming (mandatory format):**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   Example: `forge-agent/build/e-042/trustflow/pr-007-add-audit-sink`

6. **Generated files** carry the suffix `_gen` before the extension: `schema_gen.py`, `routes_gen.swift`. Never hand-edit a `_gen` file.

---

## 2. Class and Function Naming

7. **Python classes:** `PascalCase`. No trailing `Base`, `Manager`, or `Helper` unless the class is an abstract base registered with `abc.ABC`.

8. **Python functions and variables:** `snake_case`. Boolean variables start with `is_`, `has_`, `can_`, or `should_`.

9. **Swift types:** `PascalCase`. Swift functions and properties: `camelCase`.

10. **axIdentifier naming (Swift/macOS UI).** Every interactive element must have `.accessibilityIdentifier()` set, following this pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    Examples:
    ```
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

11. **Constants:** `UPPER_SNAKE_CASE` in Python, `camelCase` with `let` in Swift.

12. **Private members:** Prefix with a single underscore in Python (`_internal_state`). Use `private` or `fileprivate` access control in Swift — no underscore prefix.

13. **Acronyms** in identifiers are treated as words: `HttpClient`, `McpPolicyEngine`, `VtzEnforcer` — not `HTTPClient` or `MCPPolicyEngine`.

---

## 3. Error and Exception Patterns

14. **Custom exceptions** inherit from a single project root: `ForgeError(Exception)`. Subsystem exceptions inherit from `ForgeError` and are named `{Subsystem}{Fault}Error`:
    ```python
    class TrustFlowValidationError(ForgeError): ...
    class VtzPathTraversalError(ForgeError): ...
    ```

15. **Never catch bare `Exception` or `BaseException`** unless immediately re-raising after logging.

16. **Fail fast on invalid input.** Validate at the boundary; raise before doing work. Do not return `None` to signal failure from a function whose return type is not `Optional`.

17. **Graceful `None` returns** are required only where explicitly specified — e.g., `fetch_build_map()` must return `None` (not raise) when no build map exists yet.

18. **Error messages** follow the format `"[SUBSYSTEM] Verb phrase: {detail}"`:
    ```python
    raise VtzPathTraversalError("[VTZ] Blocked path traversal: {user_path!r}")
    ```

19. **Swift errors** conform to `LocalizedError` and provide `errorDescription`.

---

## 4. Import and Module Organisation

20. **Import order** (enforced by linter, separated by blank lines):
    1. Standard library
    2. Third-party packages
    3. Forge platform (`src/`)
    4. Local relative imports

21. **No wildcard imports.** `from module import *` is forbidden everywhere.

22. **No dynamic code loading in generated files.** Generated code must never call `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

23. **Every generated file must be complete and self-contained.** No template files with runtime placeholders. No file whose sole purpose is to dispatch to another generated file.

24. **Circular imports** are a build-breaking defect. If module A needs a type from module B and vice-versa, extract the shared type into a third module under the same subsystem.

25. **Type stubs.** Public functions in `src/` must have type annotations. Use `from __future__ import annotations` at the top of every Python file.

---

## 5. Comment and Documentation Rules

26. **Module docstring** is mandatory on every `.py` file. First line: one-sentence purpose. Second paragraph (if needed): design rationale.

27. **Public function/method docstring** uses Google-style:
    ```python
    def enforce_zone(zone_id: str, policy: Policy) -> ZoneResult:
        """Enforce a VTZ policy on the specified zone.

        Args:
            zone_id: Unique zone identifier from the trust registry.
            policy: Policy instance to apply.

        Returns:
            ZoneResult with enforcement outcome and audit trace.

        Raises:
            VtzPolicyConflictError: If conflicting policies exist.
        """
    ```

28. **Inline comments** explain _why_, not _what_. If a comment restates the code, delete it.

29. **TODO format:** `# TODO(engineer_id): Description — tracking-issue-URL`. TODOs without an engineer ID are rejected in review.

30. **No commented-out code** in any committed file. Use version control history.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security

31. **Validate paths before ANY write operation.** Every agent-initiated file write must pass through `validate_write_path` before execution:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises VtzPathTraversalError on traversal
    ```
    No write call (`open(..., 'w')`, `pathlib.Path.write_text`, `shutil.copy`, etc.) may reference a path that has not been validated through this function. This is non-negotiable.

### 6.2 Code Fence Sanitization

32. **The `_strip_code_fences()` function must be identical across all five modules that define it.** Any change to the sanitization logic must be applied to all five simultaneously in a single commit.

33. **`_strip_code_fences()` contract:**
    - Accept an empty string or `None` and return it unchanged.
    - Preserve trailing newline on non-empty output.
    - Do not modify code that has no fences or unicode characters.
    - Must be synchronous (no `async