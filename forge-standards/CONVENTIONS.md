# CONVENTIONS.md — Crafted Subsystem

All conventions below are derived from the Crafted TRD documents and Forge architecture standards. Every rule is mandatory for code contributed to the Crafted subsystem.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively. No hyphens, no camelCase.
   - `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/build_ledger.py`, `src/document_store.py`, `src/ci_workflow.py`

2. **Subsystem directories** under `src/` use short lowercase slugs matching their acronym or name:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

3. **Test files** mirror `src/` structure exactly under `tests/`:
   - Source `src/build_ledger.py` → Test `tests/test_build_ledger.py`
   - Source `src/cal/session.py` → Test `tests/cal/test_session.py`

4. **CI workflow files** use these exact names:
   - `crafted-ci.yml` — Ubuntu pipeline
   - `crafted-ci-macos.yml` — macOS Swift pipeline

5. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` so that `src/` is importable in tests. Do not manually create or delete this file; the pipeline owns it.

---

## 2. Branch Naming

6. **All agent branches** must follow this exact pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — the claiming engineer's identifier (lowercase, no spaces).
   - `subsystem_slug` — e.g., `crafted`, `cal`, `trustflow`.
   - `N` — zero-padded to three digits (`001`, `012`, `137`).
   - `title_slug` — kebab-case summary, max 48 characters.

   Example: `forge-agent/build/eng-042/crafted/pr-007-add-gate-timeout`

---

## 3. Class and Function Naming

7. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `GitHubTool`, `WebhookReceiver`, `BuildLedger`, `DocumentStore`.

8. **Python functions and methods** use `snake_case`: `validate_write_path()`, `claim()`, `release()`, `heartbeat()`, `chunk()`, `embed()`, `retrieve()`.

9. **Module-level constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

10. **Private/internal symbols** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

11. **Swift types** (macOS app shell) use standard Swift conventions: `PascalCase` for types and protocols, `camelCase` for functions, properties, and local variables.

---

## 4. Accessibility Identifier Convention (axIdentifier)

12. **Every interactive SwiftUI element** must have `.accessibilityIdentifier()` set. No exceptions for buttons, fields, rows, or cards.

13. **axIdentifier format**: `{module}-{component}-{role}-{context?}`
    - All segments are lowercase kebab-case.
    - `context` is optional and is appended only when the element is dynamic (e.g., repeated in a list).

14. **Canonical examples** (use these as templates):
    | Identifier | Breakdown |
    |---|---|
    | `auth-touchid-button` | module=auth, component=touchid, role=button |
    | `auth-passcode-button` | module=auth, component=passcode, role=button |
    | `settings-anthropic-key-field` | module=settings, component=anthropic-key, role=field |
    | `settings-anthropic-key-test-button` | module=settings, component=anthropic-key-test, role=button |
    | `settings-anthropic-key-reveal-button` | module=settings, component=anthropic-key-reveal, role=button |
    | `navigator-project-row-{projectId}` | dynamic context with runtime ID |
    | `stream-gate-card-{gateId}` | dynamic context with gate ID |
    | `stream-gate-yes-button-{gateId}` | dynamic context with gate ID |
    | `stream-gate-skip-button-{gateId}` | dynamic context with gate ID |
    | `stream-gate-stop-button-{gateId}` | dynamic context with gate ID |

15. **Dynamic context values** (e.g., `{projectId}`, `{gateId}`) must be the entity's stable identifier, never an index or display name.

---

## 5. Path Security and Write Validation

16. **Every file write** must be preceded by path validation. No exceptions, no shortcuts:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
17. `validate_write_path` returns a safe default on directory-traversal attempts. Never catch or suppress its safety behaviour.

18. **Never construct write paths** with string concatenation or f-strings from user input. Always pass through `validate_write_path` first.

---

## 6. Error and Exception Patterns

19. **Custom exceptions** are named `{Domain}Error` in `PascalCase`: `BuildLedgerError`, `PathTraversalError`, `ConsensusError`.

20. **Raise early, catch late.** Validate inputs at function entry; let exceptions propagate to the orchestration layer (`build_director.py`) for handling.

21. **Never use bare `except:`.** Always catch a specific exception type. At minimum use `except Exception:`.

22. **Log before re-raising.** When catching an exception only to add context, log the original, then `raise ... from err`.

---

## 7. Import and Module Organisation

23. **Import order** (enforced by linter, separated by blank lines):
    1. Standard library
    2. Third-party packages
    3. Forge/Crafted `src/` modules

24. **Relative imports** are forbidden at the package boundary. Use absolute imports from `src/`:
    ```python
    from src.build_ledger import BuildLedger      # correct
    from ..build_ledger import BuildLedger         # forbidden
    ```

25. **No wildcard imports** (`from module import *`) anywhere in the codebase.

26. **Lazy imports** are permitted only inside functions when a module has heavy initialisation cost. Add a comment explaining why:
    ```python
    def generate():
        # Lazy: avoids loading model weights at import time
        from src.consensus import ConsensusEngine
    ```

---

## 8. Comment and Documentation Rules

27. **Every public class and function** must have a docstring. Use imperative mood for the first line:
    ```python
    def claim(task_id: str) -> bool:
        """Claim a build task in the ledger."""
    ```

28. **Inline comments** explain *why*, never *what*. The code explains what.

29. **TODO format**: `# TODO(engineer_id): description — tracking-issue-url`

30. **No commented-out code** may be committed. Use version control history instead.

---

## 9. Crafted-Specific Patterns

31. **PR-type routing** is owned by `src/build_director.py