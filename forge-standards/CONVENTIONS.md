# Code Conventions — Forge Platform

> **Scope:** All code in the Forge mono-repo, with FullPlatform-specific rules in §6.
> Every rule is mandatory unless marked *(recommended)*.

---

## 1. File and Directory Naming

1. **Python modules** use `snake_case.py`. No hyphens, no uppercase.
   ```
   src/build_director.py    # ✓
   src/BuildDirector.py     # ✗
   ```

2. **Subsystem directories** live directly under `src/` and use short lowercase slugs matching their acronym or name:
   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity (TPM-anchored)
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   ```

3. **Tests mirror `src/` exactly.** A module at `src/cal/session.py` has tests at `tests/cal/test_session.py`. No exceptions.

4. **Canonical backend files** — keep these names stable; tooling depends on them:
   | Path | Contents |
   |---|---|
   | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
   | `src/build_director.py` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
   | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
   | `src/build_ledger.py` | `BuildLedger`, claim/release, heartbeat |
   | `src/document_store.py` | `DocumentStore`, `chunk()`, `embed()`, `retrieve()` |
   | `src/ci_workflow.py` | CI YAML generation (`crafted-ci.yml`, `crafted-ci-macos.yml`) |

5. **CI workflow files** are named exactly:
   - `crafted-ci.yml` — Ubuntu runners.
   - `crafted-ci-macos.yml` — macOS Swift runners.
   - `conftest.py` at repo root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit this file.

6. **Branch naming** (mandatory, kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase GitHub handle.
   - `subsystem_slug`: matches the `src/` directory name (e.g., `cal`, `vtz`, `build-pipeline`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase, hyphens only, max 48 chars.

   ```
   forge-agent/build/jdoe/trustflow/pr-017-add-audit-rotation   # ✓
   feature/my-thing                                               # ✗
   ```

---

## 2. Class and Function Naming

7. **Classes** use `PascalCase`. Acronyms of 3+ letters are title-cased: `MtlsHandler`, not `MTLSHandler`. Two-letter acronyms stay uppercase: `UIAddendum`, `CI`.

8. **Functions and methods** use `snake_case`. Public functions start with a verb:
   ```python
   def validate_write_path(path: str) -> Path: ...
   def retrieve_context(query: str, top_k: int = 5) -> list[Chunk]: ...
   ```

9. **Private helpers** are prefixed with a single underscore:
   ```python
   def _normalize_slug(raw: str) -> str: ...
   ```

10. **Constants** are `UPPER_SNAKE_CASE` and defined at module level:
    ```python
    MAX_CHUNK_TOKENS = 512
    GENERATION_SYSTEM = "..."
    ```

11. **Enum members** are `UPPER_SNAKE_CASE`:
    ```python
    class PRType(enum.Enum):
        FEATURE = "feature"
        DOCS = "docs"
        HOTFIX = "hotfix"
    ```

12. **Swift types** (macOS shell) follow Swift API Design Guidelines — `PascalCase` types, `camelCase` members. No additional prefixes.

---

## 3. Error and Exception Patterns

13. **Custom exceptions** inherit from a single base per subsystem:
    ```python
    class ForgeError(Exception):
        """Root for all Forge-raised errors."""

    class TrustFlowError(ForgeError): ...
    class BuildLedgerConflict(ForgeError): ...
    ```

14. **Never catch bare `Exception` in library code.** Catch the narrowest type. CLI entry points and webhook handlers may catch `ForgeError` at the boundary.

15. **Error messages** are a single lowercase sentence, no trailing period, with interpolated context:
    ```python
    raise BuildLedgerConflict(f"task {task_id} already claimed by {owner}")
    ```

16. **Path-security violations** must raise `PathTraversalError(ForgeError)` — never silently return. The `validate_write_path` helper returns a safe default **or** raises; callers must not bypass it:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Call this **before ANY file write** that involves user- or agent-supplied paths.

17. **Retry-able operations** (network, GitHub API) use structured retry with back-off. Attach the original exception via `raise ... from err`.

---

## 4. Import and Module Organisation

18. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. `src.*` / local imports

    Separate each group with a blank line.

19. **Absolute imports only** from `src/`:
    ```python
    from src.build_ledger import BuildLedger          # ✓
    from ..build_ledger import BuildLedger             # ✗
    ```

20. **No wildcard imports.** `from module import *` is forbidden everywhere.

21. **Lazy imports** are allowed only for heavy optional dependencies (e.g., ML frameworks). Mark them with an inline comment:
    ```python
    def embed(text: str) -> list[float]:
        import sentence_transformers  # lazy: heavy dependency
        ...
    ```

22. **Circular-import prevention:** If module A needs a type from module B at runtime, import inside the function. For type-checking only, use:
    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.cal.session import Session
    ```

---

## 5. Comment and Documentation Rules

23. **Every public class and function** has a docstring (Google-style):
    ```python
    def claim_task(self, task_id: str, owner: str) -> ClaimReceipt:
        """Atomically claim a build task.

        Args:
            task_id: Unique task identifier from the build queue.
            owner: GitHub handle of the claiming agent.

        Returns:
            ClaimReceipt with lease expiry and heartbeat interval.

        Raises:
            BuildLedgerConflict: If the task is already claimed.
        """
    ```

24. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

25. **TODO format:**
    ```python
    # TODO(jdoe): migrate to async after Python 3.13 bump — #142
    ```
    Must include owner handle and issue number.

26. **No commented-