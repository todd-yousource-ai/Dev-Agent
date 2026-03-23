# Code Conventions — Forge Platform

> **Scope:** All code in the Forge mono-repo, with subsystem-specific rules for **FullPlatform**.
> Every rule is mandatory unless explicitly marked *(recommended)*.

---

## 1. File and Directory Naming

1. **Python files** use `snake_case.py` — no hyphens, no uppercase.
2. **Swift files** use `PascalCase.swift`, matching the primary type they declare.
3. **Subsystem source directories** live directly under `src/` and use short, lowercase slugs:

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

4. **Tests mirror `src/` exactly**: a module at `src/vtz/policy.py` is tested at `tests/vtz/test_policy.py`.
5. **Top-level orchestration files** keep their canonical names — do not rename or relocate:
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`+`UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, `pr_type` routing
   - `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
   - `src/build_ledger.py` — `BuildLedger`, claim/release, heartbeat
   - `src/document_store.py` — `DocumentStore`, `chunk()`, `embed()`, `retrieve()`
   - `src/ci_workflow.py` — CI YAML generation, `conftest.py` auto-commit
6. **CI workflow files** are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not create alternative workflow names.
7. `conftest.py` at repo root is **auto-committed** by `ci_workflow.ensure()` to support `src/` imports — never hand-edit.

---

## 2. Branch Naming

8. All agent-authored branches **must** follow this format exactly:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — numeric or short alphanumeric, no dots.
   - `subsystem_slug` — lowercase, hyphen-separated (e.g., `full-platform`, `trust-flow`).
   - `N` — zero-padded to three digits (`001`, `012`).
   - `title_slug` — lowercase, hyphens only, max 48 characters.

   Example: `forge-agent/build/42/full-platform/pr-007-add-vtz-sandbox`

---

## 3. Class and Function Naming

9. **Python classes**: `PascalCase`. Suffix domain role when ambiguous — `Engine`, `Store`, `Gate`, `Policy`, `Handler`.
10. **Python functions / methods**: `snake_case`. Prefix with verb — `validate_`, `emit_`, `retrieve_`, `build_`.
11. **Swift types**: `PascalCase`. Views end in `View`; view-models end in `ViewModel`.
12. **Constants**:
    - Python module-level: `UPPER_SNAKE_CASE`.
    - Swift global: `static let camelCase` inside an `enum` namespace.
13. **Private members**: prefix with a single underscore in Python (`_internal_cache`). In Swift, use `private` access control — no underscore prefix.
14. **Protocols / ABCs**: name after capability, not implementation — `Auditable`, `Rewindable`, `TrustScored`.

---

## 4. Error and Exception Patterns

15. Define one base exception per subsystem in `<subsystem>/errors.py`:

    ```python
    class VTZError(Exception):
        """Base for all VTZ exceptions."""
    ```

16. Concrete exceptions subclass the base and carry structured context:

    ```python
    class PathTraversalError(VTZError):
        def __init__(self, attempted_path: str, resolved_path: str):
            self.attempted_path = attempted_path
            self.resolved_path = resolved_path
            super().__init__(
                f"Path traversal blocked: {attempted_path!r} resolved to {resolved_path!r}"
            )
    ```

17. Never catch bare `Exception` in production code. Catch the narrowest subclass; re-raise unknown errors.
18. All user-facing error messages must be free of internal paths and stack details.
19. Swift errors conform to `LocalizedError` and supply `errorDescription`.

---

## 5. Import and Module Organisation

20. Group imports in this order, separated by a blank line:
    1. Standard library
    2. Third-party packages
    3. Forge `src/` modules (absolute imports from repo root)
    4. Local relative imports (only within the same subsystem package)

21. Never use wildcard imports (`from x import *`).
22. Circular imports are build-blocking. If two subsystems need each other, extract the shared type into `src/shared/types.py`.
23. In Swift, import only the module needed — prefer `import struct Foundation.UUID` over `import Foundation` *(recommended)*.

---

## 6. Comment and Documentation Rules

24. Every public Python function/class has a docstring (Google style):

    ```python
    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Return the top-k most relevant chunks for a query.

        Args:
            query: Natural-language search string.
            top_k: Maximum results to return.

        Returns:
            Ranked list of Chunk objects with similarity scores.

        Raises:
            DocumentStoreError: If the index is not initialised.
        """
    ```

25. Every public Swift function/type has a `///` doc comment.
26. Inline comments (`#` / `//`) explain **why**, not **what**. If the code needs a "what" comment, refactor for clarity.
27. TODO/FIXME format: `# TODO(engineer_id): description — tracking-issue-url`.
28. Never commit commented-out code. Use version control history instead.

---

## 7. Path Security

29. **Validate every path before any write operation.** No exceptions, no shortcuts:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt; raises PathTraversalError
    # if strict mode is enabled.
    ```

30. Never construct file paths with string concatenation. Use `pathlib.Path` and resolve before comparison.
31. Disallow symlink targets outside the project sandbox — `validate_write_path` enforces this.

---

## 8. FullPlatform-Specific Patterns

### 8.1 Accessibility Identifiers (macOS / SwiftUI)

32. Every interactive SwiftUI element **must** set `.accessibilityIdentifier()`.
33. Identifier format: `{module}-{component}-{role}-{context?}`

    | Identifier | Element |
    |---|---|
    | `auth-touchid-button` | Touch ID authentication button |
    | `auth-passcode-button` | Passcode fallback button |
    | `settings-anthropic-key-field` | API key text field |
    | `settings-anthropic-key-test-button` | Key validation button |
    | `settings-anthropic-key-reveal-button` | Show/hide key toggle |
    | `navigator-project-row