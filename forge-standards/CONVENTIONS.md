# CONVENTIONS.md — Crafted Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively. No hyphens, no camelCase in filenames.
   ```
   src/consensus.py
   src/build_director.py
   src/github_tools.py
   src/build_ledger.py
   src/document_store.py
   src/ci_workflow.py
   ```

2. **Subsystem directories** under `src/` use short, lowercase slugs matching their acronym or canonical name:
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

3. **Test directories** mirror `src/` structure exactly. A module at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

4. **CI workflow files** use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or alias them.

5. **`conftest.py`** at the repository root is auto-committed by `ci_workflow.ensure()` to make `src/` importable. Never hand-edit this file; regenerate it via the CI workflow module.

6. **Branch naming** follows this mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no underscores.
   - `subsystem_slug`: matches the `src/` directory name (e.g., `cal`, `trustflow`).
   - `N`: zero-padded to three digits.
   - `title_slug`: lowercase, hyphens only, max 48 characters.

---

## 2. Class and Function Naming

7. **Python classes**: `PascalCase`. One primary class per module; the class name maps directly to the filename.
   ```python
   # src/build_ledger.py
   class BuildLedger:
       ...
   ```

8. **Python functions and methods**: `snake_case`. Prefix private helpers with a single underscore.
   ```python
   def claim_build(self, build_id: str) -> bool:
       ...

   def _validate_heartbeat(self, timestamp: float) -> bool:
       ...
   ```

9. **Module-level constants**: `UPPER_SNAKE_CASE`.
   ```python
   GENERATION_SYSTEM = "..."
   SWIFT_GENERATION_SYSTEM = "..."
   UI_ADDENDUM = "..."
   ```

10. **Private module-level variables** (not exported): prefix with a single underscore and use `lower_snake_case`.
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog"}
    ```

11. **Swift accessibility identifiers** (`axIdentifier`) follow the pattern `{module}-{component}-{role}-{context?}`. Set via `.accessibilityIdentifier()` on every interactive element.
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
    - All segments are lowercase, hyphen-separated.
    - Dynamic suffixes (e.g., `{projectId}`, `{gateId}`) are appended after the role segment.
    - Every interactive SwiftUI element **must** have an `axIdentifier`. Omission is a review blocker.

---

## 3. Error and Exception Patterns

12. **Custom exceptions** inherit from a single base per subsystem. Name them `{Noun}Error`.
    ```python
    class BuildLedgerError(Exception):
        """Base for all BuildLedger failures."""

    class ClaimConflictError(BuildLedgerError):
        """Raised when a build is already claimed."""
    ```

13. **Never catch bare `Exception`** in library code. Catch the narrowest type; re-raise unknown exceptions.

14. **Path validation before any write**: Every agent or tool that writes to disk must call `validate_write_path` first. This is non-negotiable.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    If `validate_write_path` is not called before `open(..., "w")`, `open(..., "a")`, `pathlib.Path.write_text()`, or any equivalent, the code fails review.

15. **Error messages** must include the operation attempted and the failing input. No bare `raise ValueError("invalid")`.
    ```python
    raise ClaimConflictError(
        f"Build {build_id} already claimed by {existing_owner}"
    )
    ```

---

## 4. Import and Module Organisation

16. **Import order** (enforced by `isort` with `profile=black`):
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules (absolute imports from `src`)
    4. Relative imports (only within the same subsystem directory)

    Separate each group with a blank line.

17. **Absolute imports** from `src/` for cross-subsystem references:
    ```python
    from src.build_ledger import BuildLedger
    from src.consensus import GENERATION_SYSTEM
    ```

18. **Relative imports** only within the same subsystem package:
    ```python
    # Inside src/cal/session.py
    from .tokens import TokenBucket
    ```

19. **No wildcard imports** (`from module import *`) anywhere. Every name must be explicitly imported.

20. **Circular import prevention**: If module A needs a type from module B at runtime and B imports A, move the shared type to a `_types.py` file within the subsystem or use `TYPE_CHECKING`:
    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from src.build_ledger import BuildLedger
    ```

---

## 5. Comment and Documentation Rules

21. **Every public class and function** has a docstring. Use imperative mood, single-line summary, then optional blank line and detail.
    ```python
    def claim_build(self, build_id: str) -> bool:
        """Claim exclusive ownership of a build.

        Returns True if the claim succeeded, False if already held.
        Raises BuildLedgerError on storage failure.
        """
    ```

22. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.
    ```python
    # Heartbeat interval is 30 s to stay under the 60 s lease timeout
    HEARTBEAT_INTERVAL = 30
    ```

23. **TODO format**: `# TODO(engineer_id): description — YYYY-MM-DD`. TODOs without a date and owner are rejected in review.

24. **No commented-out code** in main branches. Use version control history instead.

25. **Module-level docstring** required for every file in `src/`. First line states the module's single responsibility.
    ```python
    """BuildLedger — claim/release tracking and heartbeat management for builds."""
    ```

---

##