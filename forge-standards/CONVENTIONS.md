# CONVENTIONS.md — Crafted Subsystem

All rules derived from project TRDs. Every rule is mandatory unless marked `[OPTIONAL]`.

---

## 1. File and Directory Naming

1. **Python source files** use `snake_case.py` exclusively. No hyphens, no camelCase.
   ```
   src/consensus.py
   src/build_director.py
   src/build_ledger.py
   src/ci_workflow.py
   src/document_store.py
   src/github_tools.py
   ```

2. **Subsystem directories** under `src/` use short lowercase slugs with no underscores or hyphens:
   ```
   src/cal/          # Conversation Abstraction Layer
   src/dtl/          # Data Trust Label
   src/trustflow/    # TrustFlow audit stream
   src/vtz/          # Virtual Trust Zone enforcement
   src/trustlock/    # Cryptographic machine identity
   src/mcp/          # MCP Policy Engine
   src/rewind/       # Forge Rewind replay engine
   sdk/connector/    # Forge Connector SDK
   ```

3. **Test files** mirror `src/` structure exactly. A source file at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. Prefix every test file with `test_`.

4. **CI workflow files** are named precisely:
   - `crafted-ci.yml` — Ubuntu pipeline
   - `crafted-ci-macos.yml` — macOS Swift pipeline

   No other naming is permitted for Crafted CI definitions.

5. **`conftest.py`** at repo root is auto-committed by `ci_workflow.ensure()` to guarantee `src/` is importable. Never delete or rename it manually.

---

## 2. Branch Naming

6. **All agent branches** must follow this exact pattern:
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no spaces.
   - `subsystem_slug`: e.g. `crafted`, `cal`, `trustflow`.
   - `N`: zero-padded to 3 digits (`001`, `042`).
   - `title_slug`: lowercase, hyphen-separated, max 48 characters.

   Example: `forge-agent/build/eng-017/crafted/pr-003-add-gate-card-ui`

7. The prefix `forge-agent` is **intentional and locked** for tooling compatibility. Do not rename to `forge-bot` or similar.

---

## 3. Class and Function Naming

8. **Python classes**: `PascalCase`. One primary class per module; the file name is the snake_case form of the class name.
   ```python
   # src/build_ledger.py
   class BuildLedger:
       ...
   ```

9. **Python functions and methods**: `snake_case`. Verbs first.
   ```python
   def claim_build(self, build_id: str) -> bool:
   def release_lock(self, lock_id: str) -> None:
   def retrieve_chunks(self, query: str) -> list[Chunk]:
   ```

10. **Constants**: `UPPER_SNAKE_CASE`. Defined at module top level, after imports.
    ```python
    GENERATION_SYSTEM = "..."
    SWIFT_GENERATION_SYSTEM = "..."
    UI_ADDENDUM = "..."
    ```

11. **Swift accessibility identifiers** follow the `axIdentifier` convention strictly:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All lowercase, hyphen-separated.
    - Set via `.accessibilityIdentifier()` on every interactive element.
    - Dynamic context values are appended with a hyphen:
    ```swift
    // Static
    "auth-touchid-button"
    "auth-passcode-button"
    "settings-anthropic-key-field"
    "settings-anthropic-key-test-button"
    "settings-anthropic-key-reveal-button"

    // Dynamic — interpolate the ID
    "navigator-project-row-\(projectId)"
    "stream-gate-card-\(gateId)"
    "stream-gate-yes-button-\(gateId)"
    "stream-gate-skip-button-\(gateId)"
    "stream-gate-stop-button-\(gateId)"
    ```

12. **No interactive SwiftUI element** may ship without an `.accessibilityIdentifier()`. CI accessibility audits rely on this.

---

## 4. Error and Exception Patterns

13. **Custom exceptions** inherit from a single subsystem base:
    ```python
    class CraftedError(Exception):
        """Base for all Crafted subsystem errors."""

    class PathTraversalError(CraftedError): ...
    class BuildClaimError(CraftedError): ...
    class GateTimeoutError(CraftedError): ...
    ```

14. **Never catch bare `Exception`** except at top-level entry points (CLI main, webhook handler). Always catch the narrowest type.

15. **Path validation is mandatory before every write operation.** No exceptions, no shortcuts:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt; raises PathTraversalError on violation
    ```
    Any code that writes to disk without calling `validate_write_path` first is a blocking review finding.

---

## 5. Import and Module Organisation

16. **Import order** (enforced by linter, each group separated by a blank line):
    1. Standard library
    2. Third-party packages
    3. Forge/Crafted internal (`src/...`)

    ```python
    import os
    from pathlib import Path

    import httpx

    from src.build_ledger import BuildLedger
    from src.consensus import GENERATION_SYSTEM
    ```

17. **No wildcard imports** (`from module import *`) anywhere in the codebase.

18. **No circular imports.** If module A needs a type from module B and vice versa, extract the shared type into a third module or use `TYPE_CHECKING`:
    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from src.build_ledger import BuildLedger
    ```

19. **`src/` is the import root.** All internal imports start with `src.` (guaranteed by the auto-committed `conftest.py`).

---

## 6. Comment and Documentation Rules

20. **Every module** has a one-line docstring immediately after the module-level `"""..."""` that states its primary responsibility:
    ```python
    """BuildLedger — claim/release tracking with heartbeat for concurrent builds."""
    ```

21. **Every public class and function** has a docstring. Use imperative mood, first line ≤ 79 characters:
    ```python
    def claim_build(self, build_id: str) -> bool:
        """Claim exclusive ownership of a build. Return False if already claimed."""
    ```

22. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

23. **TODO comments** must include an engineer ID and a tracking reference:
    ```python
    # TODO(eng-017): replace polling with webhook — see TRD-3 §4.2
    ```

24. **No commented-out code** in main branches. Use version control history instead.

---

## 7. Crafted-Specific Patterns

25. **PR-type routing** in `build_director.py` uses explicit `pr_type` string matching. Recognised types: `"build"`, `"docs"`, `"fix"`, `"refactor"`. Unknown types must raise `CraftedError`, never silently default.

26. **Confidence gate calls** are synchronous and blocking. The gate result (`yes`, `skip`, `stop`) maps directly to the `stream-gate-{action}-button-{gateId}` accessibility identifiers in the UI