# CONVENTIONS.md — Crafted Subsystem

> All rules derived from the Crafted TRD documents and Forge architecture context.
> Every rule is mandatory unless explicitly marked *recommended*.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively.
   ```
   src/consensus.py
   src/build_director.py
   src/github_tools.py
   src/build_ledger.py
   src/document_store.py
   src/ci_workflow.py
   ```

2. **Subsystem directories** use short lowercase slugs with no underscores or hyphens:
   ```
   src/cal/           # Conversation Abstraction Layer
   src/dtl/           # Data Trust Label
   src/trustflow/     # TrustFlow audit stream
   src/vtz/           # Virtual Trust Zone enforcement
   src/trustlock/     # Cryptographic machine identity
   src/mcp/           # MCP Policy Engine
   src/rewind/        # Forge Rewind replay engine
   sdk/connector/     # Forge Connector SDK
   ```

3. **Test directories** mirror `src/` structure exactly:
   ```
   tests/cal/
   tests/dtl/
   tests/trustflow/
   ```

4. **CI workflow files** use these exact names — no variations:
   - `crafted-ci.yml` (Ubuntu)
   - `crafted-ci-macos.yml` (macOS Swift)

5. **`conftest.py`** at the repo root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit or delete it.

6. **Branch naming** follows the mandatory pattern (kept as `forge-agent` for compatibility):
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric, no spaces.
   - `subsystem_slug`: matches the directory slug (e.g., `crafted`, `cal`, `vtz`).
   - `N`: zero-padded to 3 digits.
   - `title_slug`: lowercase, hyphens only, max 48 characters.

---

## 2. Class and Function Naming

7. **Classes**: `PascalCase`. Match the canonical names from the TRDs exactly:
   ```python
   class ConsensusEngine: ...
   class BuildPipeline: ...
   class GitHubTool: ...
   class WebhookReceiver: ...
   class BuildLedger: ...
   class DocumentStore: ...
   ```

8. **Functions and methods**: `snake_case`. Verb-first where possible:
   ```python
   def claim_build() -> ...:
   def release_lock() -> ...:
   def validate_write_path(path: str) -> Path:
   def ensure() -> None:       # ci_workflow.ensure()
   ```

9. **Module-level constants**: `UPPER_SNAKE_CASE`:
   ```python
   GENERATION_SYSTEM = "..."
   SWIFT_GENERATION_SYSTEM = "..."
   UI_ADDENDUM = "..."
   ```

10. **Private/internal symbols**: Prefix with a single underscore:
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog"}
    _is_docs_pr = ...
    ```

---

## 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a single subsystem base:
    ```python
    class CraftedError(Exception):
        """Base for all Crafted subsystem errors."""

    class PathTraversalError(CraftedError): ...
    class BuildClaimError(CraftedError): ...
    ```

12. **Never silently swallow exceptions.** Every `except` block must either:
    - Re-raise, or
    - Log at `WARNING` or above **and** return a well-defined safe default.

13. **Path validation before every write** — no exceptions:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt; never writes to the raw input.
    ```
    Any code path that writes to disk without calling `validate_write_path` is a blocking review finding.

---

## 4. Import and Module Organisation

14. **Import order** (enforced by isort-compatible tooling):
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules (absolute imports from `src`)
    4. Relative imports (only within the same subsystem package)

    Blank line between each group.

15. **No wildcard imports** (`from x import *`) anywhere in `src/` or `tests/`.

16. **Canonical module → responsibility mapping** (do not split or merge):
    | Module | Responsibility |
    |---|---|
    | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
    | `src/build_director.py` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
    | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
    | `src/build_ledger.py` | `BuildLedger`, claim/release, heartbeat |
    | `src/document_store.py` | `DocumentStore`, `chunk()`, `embed()`, `retrieve()` |
    | `src/ci_workflow.py` | CI YAML generation, `conftest.py` auto-commit |

---

## 5. Comment and Documentation Rules

17. **Every public class and function** has a docstring. Use imperative mood, first line ≤ 79 chars:
    ```python
    def claim_build(engineer_id: str) -> BuildClaim:
        """Claim an available build slot for the given engineer."""
    ```

18. **Inline comments** explain *why*, never *what*:
    ```python
    # Heartbeat interval matches the CI timeout minus 30 s buffer
    HEARTBEAT_INTERVAL = 270
    ```

19. **TODO/FIXME** comments must include an engineer ID or issue number:
    ```python
    # TODO(forge-42): replace polling with webhook push
    ```

20. **No commented-out code** in `main` or any long-lived branch. Use version control.

---

## 6. Crafted-Specific Patterns

### 6.1 Accessibility Identifiers (macOS / SwiftUI)

21. **axIdentifier format**: `{module}-{component}-{role}-{context?}`
    - All lowercase, hyphen-separated.
    - Set via `.accessibilityIdentifier()` on **every** interactive element.

22. **Canonical examples** — deviate only by extending, never by restructuring:
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

23. **Dynamic suffixes** (e.g., `{projectId}`, `{gateId}`) are appended after the role segment, separated by a hyphen. IDs must be stable, deterministic values — never random UUIDs per render.

### 6.2 PR Classification

24. **Docs-only PR detection** uses keyword membership, not regex:
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog", ...}
    _is_docs_pr = any(kw in title_lower for kw in _docs_keywords)
    ```
    This pattern was introduced in v5.0 and **removed in v6.0**. Do not reintroduce