# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the ForgeAgent TRD documents and Forge Architecture Context. Every item is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Snake-case for all Python files.** No hyphens, no camelCase.
   `build_director.py`, `ci_workflow.py`, `document_store.py` — never `buildDirector.py`.

2. **Source directories use short, lowercase abbreviations matching the subsystem slug.**

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

3. **Tests mirror `src/` exactly.** A module at `src/vtz/enforcer.py` has its tests at `tests/vtz/test_enforcer.py`. No exceptions.

4. **CI workflow files use the exact canonical names:**
   - `crafted-ci.yml` — Ubuntu pipeline.
   - `crafted-ci-macos.yml` — macOS Swift pipeline.

5. **`conftest.py` is auto-committed by `ci_workflow.ensure()`** to enable `src/` imports. Never hand-edit or delete the auto-generated `conftest.py`.

6. **Branch names follow this exact pattern:**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no dots.
   - `subsystem_slug`: matches the `src/` directory name (e.g., `vtz`, `cal`, `trustflow`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase, hyphens only, max 48 characters.
   - Example: `forge-agent/build/agent07/trustflow/pr-012-add-heartbeat-retry`

   The prefix `forge-agent` is kept intentionally for compatibility — do not change to `forgeagent` or any variant.

---

## 2. Class and Function Naming

7. **Classes use PascalCase.** One primary class per module; the class name matches the module name in PascalCase.
   - `src/build_ledger.py` → `class BuildLedger`
   - `src/consensus.py` → `class ConsensusEngine`
   - `src/github_tools.py` → `class GitHubTool`, `class WebhookReceiver`

8. **Functions and methods use snake_case.** No abbreviations unless they match an established subsystem slug (`vtz`, `dtl`, `mcp`, `cal`).

9. **Private helpers are single-underscore prefixed.** Double-underscore name-mangling is prohibited unless required for descriptor protocol.
   ```python
   def _validate_claim(self, claim_id: str) -> bool:  # correct
   ```

10. **Constants are UPPER_SNAKE_CASE and defined at module level.**
    ```python
    GENERATION_SYSTEM = "..."
    SWIFT_GENERATION_SYSTEM = "..."
    UI_ADDENDUM = "..."
    ```

11. **axIdentifier strings (Swift UI)** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element.
    ```
    auth-touchid-button
    settings-anthropic-key-field
    navigator-project-row-{projectId}
    stream-gate-card-{gateId}
    stream-gate-yes-button-{gateId}
    ```
    - All segments are lowercase, hyphen-separated.
    - Context suffix is optional but required when the element is parameterised (e.g., by `gateId` or `projectId`).

---

## 3. Error and Exception Patterns

12. **Define one custom exception base class per subsystem module.**
    ```python
    # src/vtz/exceptions.py
    class VTZError(Exception):
        """Base for all Virtual Trust Zone errors."""

    class PathTraversalError(VTZError):
        """Raised when a write path fails validation."""
    ```

13. **Never catch bare `Exception` or `BaseException` in agent code.** Catch the narrowest subsystem exception. If a broad catch is temporarily required, add a `# TODO(forge): narrow exception` comment with an engineer ID.

14. **All path-write operations must validate before writing.** This is a security-critical rule:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Any write that bypasses `validate_write_path` is a blocking review finding.

15. **Failed validations return safe defaults, not exceptions, at the boundary layer.** Internal functions raise; boundary/agent-facing functions degrade gracefully and log.

---

## 4. Import and Module Organisation

16. **Import order (enforced by isort `profile = black`):**
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules — always use absolute imports from `src`.
    4. Local relative imports (only within the same subsystem package).

    Blank line between each group.

17. **No star imports.** `from module import *` is unconditionally banned.

18. **Canonical module-to-class mapping is fixed.** Do not move these responsibilities:

    | Module | Owns |
    |---|---|
    | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
    | `src/build_director.py` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
    | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
    | `src/build_ledger.py` | `BuildLedger`, `claim()`, `release()`, `heartbeat()` |
    | `src/document_store.py` | `DocumentStore`, `chunk()`, `embed()`, `retrieve()` |
    | `src/ci_workflow.py` | CI YAML generation, `ensure()`, auto-`conftest.py` |

19. **`path_security` must be importable at the top level.** It is a hard dependency for every module that performs file I/O. If it is missing from the environment, the agent must fail at import time, not at runtime.

---

## 5. Comment and Documentation Rules

20. **Every module has a module-level docstring** (first line after imports) naming the TRD it implements:
    ```python
    """BuildLedger — claim/release coordination.

    Implements: TRD-3-Build-Pipeline-Crafted §4.2
    """
    ```

21. **Public functions and classes require Google-style docstrings** with `Args:`, `Returns:`, and `Raises:` sections.

22. **Inline comments explain *why*, not *what*.** Code that needs a *what* comment should be refactored.

23. **TODO format is strict:** `# TODO(engineer_id): description — YYYY-MM-DD`. TODOs without a date are flagged in CI.

24. **Removed/deprecated features are recorded with a version tag:**
    ```python
    # REMOVED v6.0: keyword-list docs-PR detection (_docs_keywords).
    # Replaced by label-based routing in build_director.pr_type().
    ```

---

## 6. ForgeAgent-Specific Patterns

25. **Confidence-gated execution.** Every `BuildPipeline` step that may produce a PR