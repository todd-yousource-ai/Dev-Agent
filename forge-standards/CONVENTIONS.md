# CONVENTIONS.md — ForgeAgent Subsystem

All conventions below are derived from the ForgeAgent TRD corpus. Every rule is mandatory unless marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Snake-case for all Python files.** No hyphens, no camelCase.
   `build_director.py`, `ci_workflow.py`, `document_store.py`.

2. **Subsystem directories under `src/` use short, lowercase slugs:**

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

3. **Tests mirror `src/` exactly.** A module at `src/trustflow/emitter.py` has its test at `tests/trustflow/test_emitter.py`. No exceptions.

4. **CI workflow files use the exact names:**
   - `crafted-ci.yml` (Ubuntu)
   - `crafted-ci-macos.yml` (macOS Swift)

   Do not rename, alias, or symlink these files.

5. **`conftest.py` at repo root is auto-committed** by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit this file; regenerate it through the pipeline.

6. **Canonical backend files (do not rename or split without TRD amendment):**

   | File | Owns |
   |---|---|
   | `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
   | `src/build_director.py` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
   | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
   | `src/build_ledger.py` | `BuildLedger`, claim/release, heartbeat |
   | `src/document_store.py` | `DocumentStore`, `chunk()`, `embed()`, `retrieve()` |
   | `src/ci_workflow.py` | CI YAML generation and `conftest.py` management |

---

## 2. Branch Naming

7. **Every ForgeAgent branch MUST match this pattern exactly:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — lowercase alphanumeric, hyphens allowed.
   - `subsystem_slug` — matches a `src/` directory name or a canonical file stem (e.g., `consensus`, `trustflow`).
   - `N` — zero-padded to three digits (`001`, `042`).
   - `title_slug` — lowercase, hyphen-separated, max 48 characters.

   Example: `forge-agent/build/agent-7/trustflow/pr-012-add-heartbeat-timeout`

8. The prefix `forge-agent` (hyphenated) is kept intentionally for compatibility. Do **not** use `forgeagent`, `forge_agent`, or any other variant.

---

## 3. Class and Function Naming

9. **Classes** use PascalCase: `BuildLedger`, `ConsensusEngine`, `DocumentStore`.

10. **Public functions and methods** use snake_case: `validate_write_path()`, `claim()`, `release()`.

11. **Module-level constants** use UPPER_SNAKE_CASE: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

12. **Private/internal helpers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

13. **No double-underscore name-mangling** unless mandated by framework integration.

---

## 4. Accessibility Identifier Naming (Swift / macOS UI)

14. **All interactive SwiftUI elements MUST have `.accessibilityIdentifier()` set.**

15. **axIdentifier format:**

    ```
    {module}-{component}-{role}-{context?}
    ```

    - All segments lowercase, hyphen-separated.
    - `context` is optional; when present it is a dynamic ID appended at the end.

16. **Reference examples (canonical — match exactly where applicable):**

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

17. **Never use auto-generated or positional identifiers** (e.g., `button1`, `field_0`). Every identifier must be human-readable and semantically stable across builds.

---

## 5. Error and Exception Patterns

18. **Subsystem-specific exceptions inherit from a single base:**

    ```python
    class ForgeAgentError(Exception):
        """Base for all ForgeAgent errors."""

    class PathTraversalError(ForgeAgentError): ...
    class LedgerClaimError(ForgeAgentError): ...
    ```

19. **Never catch bare `Exception` or `BaseException`** in production code. Catch the narrowest `ForgeAgentError` subclass applicable.

20. **Path validation is mandatory before ANY write operation.** Use the canonical guard:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt — never raises silently.
    ```

    Omitting this call on any code path that writes to disk is a blocking review finding.

21. **All error messages must include the subsystem slug** so log aggregation can filter:

    ```python
    raise LedgerClaimError(f"[build_ledger] duplicate claim for task {task_id}")
    ```

---

## 6. Import and Module Organisation

22. **Import order (enforced by linter):**
    1. Standard library
    2. Third-party packages
    3. `src/` project modules (absolute imports from `src`)
    4. Relative imports within the same subsystem package

    Separate each group with a single blank line.

23. **Always use absolute imports from the `src` root:**

    ```python
    from src.build_ledger import BuildLedger
    from src.consensus import ConsensusEngine
    ```

    Do **not** rely on `sys.path` manipulation outside `conftest.py`.

24. **Circular imports are a blocking defect.** If module A needs a type from module B and vice versa, extract the shared type into a new `src/<subsystem>/types.py`.

25. **Lazy imports are permitted only for heavyweight optional dependencies** (e.g., ML model loaders). Mark them with a `# lazy: <reason>` comment.

---

## 7. Comment and Documentation Rules

26. **Every public class and public function has a docstring.** Use Google-style:

    ```python
    def claim(task_id: str, engineer_id: str) -> ClaimReceipt:
        """Claim a build task in the ledger.

        Args:
            task_id: Unique task identifier from the pipeline.
            engineer_id: The engineer or agent claiming the task.

        Returns:
            A ClaimReceipt with timestamp and TTL.

        Raises:
            LedgerClaimError: If the task is already claimed.
        """
    ```

27. **Inline