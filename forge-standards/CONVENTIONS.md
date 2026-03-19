# Code Conventions — Forge Platform

> Authoritative coding conventions for all Forge subsystems.
> Every rule is mandatory unless explicitly marked **(advisory)**.
> Last updated: 2025-06-30

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

2. **Python files** use `snake_case.py`. Never use hyphens in Python filenames.

3. **TypeScript files** use `camelCase.ts` for modules, `PascalCase.tsx` for React/SwiftUI-bridged components.

4. **Go files** use `snake_case.go`, one package per directory.

5. **Test files** live under `tests/<subsystem>/` and are named `test_<module>.py` (Python), `<module>.test.ts` (TypeScript), or `<module>_test.go` (Go). The directory tree under `tests/` must mirror the tree under `src/` exactly — no flattening.

6. **Configuration / data files** use `kebab-case` (e.g., `trust-policy-defaults.yaml`).

7. **No single-letter or ambiguous directory names.** Every directory must map to a documented subsystem slug or well-known concern (`utils/`, `types/`, `fixtures/`).

---

## 2. Class and Function Naming

8. **Python** — classes: `PascalCase`; functions / methods: `snake_case`; constants: `UPPER_SNAKE_CASE`; private members: single leading underscore `_internal`.

9. **TypeScript** — classes and interfaces: `PascalCase`; functions: `camelCase`; constants: `UPPER_SNAKE_CASE`; type aliases: `PascalCase`.

10. **Go** — exported identifiers: `PascalCase`; unexported: `camelCase`; acronyms keep consistent casing (`HTTPClient`, not `HttpClient`).

11. **Dataclass / model names** must include the subsystem prefix when shared across subsystem boundaries (e.g., `DTLTrustLabel`, `VTZEnclaveContext`).

12. **Boolean variables and functions** must read as predicates: `is_valid`, `has_quorum`, `can_merge` — never bare adjectives.

13. **axIdentifier naming (macOS UI)** follows the pattern `{module}-{component}-{role}-{context?}`:

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

    Set via `.accessibilityIdentifier()` on **every** interactive element. Omission is a review blocker.

---

## 3. Error and Exception Patterns

14. **Custom exceptions inherit from a per-subsystem base.**

    ```python
    # src/dtl/exceptions.py
    class DTLError(Exception):
        """Base for all DTL subsystem errors."""

    class DTLValidationError(DTLError): ...
    class DTLSchemaVersionError(DTLError): ...
    ```

15. **Exception class names** end with `Error` (Python/TS) or implement the `error` interface (Go). Never use `Exception` as a suffix in new code.

16. **Never catch bare `Exception` / `BaseException`** unless re-raising. Catch the narrowest type possible.

17. **Error messages are structured.** Include: what failed, which input caused it, and what the caller should do.

    ```python
    raise DTLValidationError(
        f"Trust label schema version {version} unsupported. "
        f"Supported: {SUPPORTED_VERSIONS}. "
        "Upgrade the DTL package or convert the label."
    )
    ```

18. **Go errors** wrap with `fmt.Errorf("vtz: failed to seal enclave %s: %w", id, err)` — always include the subsystem prefix before the colon.

19. **Never swallow errors silently.** If an exception is intentionally ignored, add a comment starting with `# INTENTIONAL:` explaining why.

---

## 4. Import and Module Organisation

20. **Python import order** (enforced by `isort` with `profile = black`):

    1. Standard library
    2. Third-party packages
    3. Forge packages (`src.*`, `sdk.*`)
    4. Local relative imports

    Blank line between each group.

21. **No wildcard imports** (`from x import *`) anywhere — including `__init__.py`.

22. **Circular imports are build failures.** If two subsystems need each other, extract shared types into a `types` or `interfaces` submodule at the common ancestor.

23. **TypeScript barrel files** (`index.ts`) are allowed only at subsystem root. Re-export only the public API; keep internal modules unexported.

24. **Go packages** must not import `internal/` packages across subsystem boundaries.

---

## 5. Comment and Documentation Rules

25. **Every public function, class, and method has a docstring / doc comment.** No exceptions.

    - Python: Google-style docstrings.
    - TypeScript: JSDoc `/** ... */`.
    - Go: standard `// FuncName ...` godoc comment.

26. **Inline comments explain *why*, not *what*.** If a comment restates the code, delete it.

27. **TODO format:** `# TODO(username): description — JIRA-123` or `# TODO(username): description — 2025-Q3`. Bare `# TODO` without an owner is a lint failure.

28. **Magic numbers are banned.** Extract to a named constant with a docstring or inline comment explaining derivation.

29. **Each module file starts with a one-line module docstring** describing its purpose and the subsystem it belongs to.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security

30. **Validate paths before ANY file-system write.**

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

    Any write operation that bypasses `validate_write_path` is a **P0 security defect** and must not pass code review.

31. **Agent-generated code is written only to the workspace sandbox** defined by the active `VirtualTrustZone`. Absolute paths outside the sandbox must raise `VTZEscapeError`.

### 6.2 Branch Naming

32. **All agent-created branches follow this exact pattern:**

    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

    - `engineer_id`: alphanumeric, no dots.
    - `subsystem_slug`: must match a known slug in `src/` or `sdk/`.
    - `N`: zero-padded 3-digit PR sequence number.
    - `title_slug`: lowercase kebab-case, max 48 chars.

    Example: `forge-agent/build/eng042/dtl/pr-007-add-schema-v2-migration`

### 6.3 Build Pipeline Dataclass Contracts

33. **Stage output dataclasses are immutable** (`frozen=True` in Python, `readonly` in TypeScript). No stage may mutate a previous stage's output; create a new instance instead.

34. **Dataclass field names match the canonical TRD field names exactly** (e.g., `intent`, `subsystem`, `scope_statement`, `branch_prefix`, `relevant_docs`). Do not rename or alias.

35. **Every dataclass used across pipeline stages