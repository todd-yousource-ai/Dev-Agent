# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the ForgeAgent TRD documents. Every convention is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1. **Source directories use lowercase abbreviated names** matching the canonical subsystem slugs:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

2. **Python source files use `snake_case.py`** with no abbreviations beyond the canonical subsystem slug:
   - `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/build_ledger.py`, `src/document_store.py`, `src/ci_workflow.py`.

3. **Test directories mirror `src/` structure exactly.** A source file at `src/vtz/enforcer.py` has its tests at `tests/vtz/test_enforcer.py`. No exceptions.

4. **CI workflow files use the exact names:**
   - `crafted-ci.yml` — Ubuntu pipeline.
   - `crafted-ci-macos.yml` — macOS Swift pipeline.
   - No other naming variants are permitted.

5. **`conftest.py` at repo root is auto-committed by `ci_workflow.ensure()`** to guarantee `src/` is importable. Never hand-edit this file; regenerate it through the CI workflow module.

---

## 2. Branch Naming

6. **All ForgeAgent branches follow this exact pattern:**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — lowercase alphanumeric identifier of the assigned engineer.
   - `subsystem_slug` — one of the canonical directory slugs (e.g., `cal`, `dtl`, `vtz`).
   - `N` — zero-padded three-digit PR sequence number (e.g., `001`, `042`).
   - `title_slug` — lowercase-kebab-case summary, max 48 characters.
   - The prefix `forge-agent` is intentionally kept (not `forge_agent`) for backward compatibility.

7. **Example:**
   ```
   forge-agent/build/jdoe/trustflow/pr-017-add-heartbeat-timeout
   ```

---

## 3. Class and Function Naming

8. **Classes use `PascalCase`** matching the module's domain noun: `ConsensusEngine`, `BuildPipeline`, `GitHubTool`, `WebhookReceiver`, `BuildLedger`, `DocumentStore`.

9. **Public functions and methods use `snake_case`.** Verb-first naming is required: `validate_write_path()`, `ensure()`, `claim()`, `release()`, `chunk()`, `embed()`, `retrieve()`.

10. **Private/internal helpers are prefixed with a single underscore:** `_is_docs_pr`, `_docs_keywords`.

11. **Module-level constants use `UPPER_SNAKE_CASE`:** `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

12. **Accessibility identifiers (axIdentifier) follow the pattern:**
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase kebab-case.
    - The optional `{context}` segment carries a dynamic ID when the element is repeated.
    - Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.
    - Examples:
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

---

## 4. Error and Exception Patterns

13. **Validate every file-system path before any write operation.** Use the `path_security` module — no inline path validation:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    `validate_write_path` returns a safe default on directory-traversal attempts. Never catch and silence its exceptions.

14. **Custom exceptions inherit from a single `ForgeAgentError` base class** defined in `src/exceptions.py`. Name exceptions as `{Domain}Error`: `PathTraversalError`, `LedgerClaimError`, `CIWorkflowError`.

15. **Never use bare `except:` or `except Exception:` without re-raising.** Every catch block must either:
    - Handle a specific named exception, **or**
    - Log the error with full traceback and re-raise.

---

## 5. Import and Module Organisation

16. **Import order (enforced by linter):**
    1. Standard library.
    2. Third-party packages.
    3. `src/` project modules — always imported by their `src.` qualified path.
    4. Local relative imports (only inside the same subsystem package).

17. **Each blank line separates one import group.** Example:
    ```python
    import os
    import json

    import httpx

    from src.build_ledger import BuildLedger
    from src.consensus import ConsensusEngine

    from .helpers import format_payload
    ```

18. **Circular imports are forbidden.** If module A needs a type from module B and vice versa, extract the shared type into a third module under the same subsystem directory.

19. **Wildcard imports (`from x import *`) are never used** anywhere in the codebase.

---

## 6. Comment and Documentation Rules

20. **Every module has a one-line module docstring** stating its TRD-derived purpose. Example:
    ```python
    """BuildLedger — claim/release tracking with heartbeat for concurrent ForgeAgent builds."""
    ```

21. **Public classes and functions require Google-style docstrings** with `Args:`, `Returns:`, and `Raises:` sections.

22. **Inline comments explain *why*, not *what*.** A comment restating the code is a defect; remove it.

23. **TRD cross-references use the format `# ref: TRD-{N}-{ShortTitle} §{section}`** when a code block implements a specific TRD requirement:
    ```python
    # ref: TRD-1-macOS-Application-Shell-Crafted §13.1
    identifier = f"stream-gate-yes-button-{gate_id}"
    ```

24. **No commented-out code is committed.** Dead code must be deleted, not commented. Version history is in Git.

---

## 7. ForgeAgent-Specific Patterns

25. **PR-type routing lives exclusively in `src/build_director.py`.** The `BuildPipeline` class owns the confidence gate and `pr_type` routing logic. No other module may duplicate this decision tree.

26. **Document retrieval follows the three-step contract:** `chunk()` → `embed()` → `retrieve()`, all defined on `DocumentStore`. Callers must not skip steps or combine them.

27. **The consensus module exposes exactly three prompt constants:** `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM`. All LLM system prompts for code generation must reference one of these constants — never inline a system prompt string.

28. **Heartbeat and claim lifecycle:** `BuildLedger.claim()` must be called