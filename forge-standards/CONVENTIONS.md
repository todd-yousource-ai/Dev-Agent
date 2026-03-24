# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from project TRDs and architecture documents. Every rule is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1. **Source directories use short, lowercase acronym slugs.** Each subsystem gets a dedicated directory under `src/`:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

2. **Test directories mirror `src/` exactly.** A module at `src/vtz/enforcer.py` has its tests at `tests/vtz/test_enforcer.py`. No exceptions.

3. **Python filenames are `snake_case`, no hyphens, no uppercase.** Examples:
   - `src/build_director.py`
   - `src/build_ledger.py`
   - `src/ci_workflow.py`
   - `src/consensus.py`
   - `src/document_store.py`
   - `src/github_tools.py`

4. **CI workflow files use the exact canonical names:**
   - `crafted-ci.yml` — Ubuntu pipeline
   - `crafted-ci-macos.yml` — macOS Swift pipeline
   - No other naming variants are permitted.

5. **`conftest.py` at the repo root is auto-committed by `ci_workflow.ensure()`.** Never hand-edit this file; it exists solely to make `src/` importable in test runs.

---

## 2. Branch Naming

6. **All ForgeAgent branches follow this exact pattern:**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id` — the agent or human identifier (e.g., `fa-01`, `jdoe`)
   - `subsystem_slug` — lowercase hyphenated subsystem name (e.g., `trust-flow`, `build-pipeline`)
   - `N:03d` — zero-padded three-digit PR sequence number (e.g., `001`, `042`)
   - `title_slug` — lowercase hyphenated summary, max 48 characters

7. **The prefix `forge-agent/` is mandatory and must not be changed.** It is kept intentionally for compatibility with existing CI selectors and webhook filters.

---

## 3. Class and Function Naming

8. **Classes use `PascalCase`.** Examples: `BuildPipeline`, `ConsensusEngine`, `BuildLedger`, `DocumentStore`, `GitHubTool`, `WebhookReceiver`.

9. **Functions and methods use `snake_case`.** Examples: `validate_write_path()`, `claim()`, `release()`, `heartbeat()`, `chunk()`, `embed()`, `retrieve()`.

10. **Module-level constants use `UPPER_SNAKE_CASE`.** Examples: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

11. **Private/internal module-level variables are prefixed with a single underscore.** Example: `_docs_keywords`, `_is_docs_pr`.

12. **axIdentifier strings (SwiftUI accessibility identifiers) follow this pattern:**
    ```
    {module}-{component}-{role}-{context?}
    ```
    - All segments are lowercase, hyphen-separated.
    - Dynamic context values are appended with curly-brace templates in code: `"navigator-project-row-{projectId}"`.
    - Every interactive SwiftUI element must have an `.accessibilityIdentifier()` set. No interactive element may ship without one.
    - Canonical examples:
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

13. **Define custom exception classes per subsystem.** Name them `{Subsystem}{ErrorKind}Error` in `PascalCase`. Examples: `VtzPathTraversalError`, `BuildLedgerClaimError`, `DtlValidationError`.

14. **Never catch bare `Exception` or `BaseException` in production code.** Catch the narrowest applicable type. If a broad catch is truly required, log the full traceback and re-raise.

15. **All file-write operations must validate paths before writing:**
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal attempt
    ```
    This call is non-optional. Any PR that writes to a file path without calling `validate_write_path` first will be rejected.

16. **Return structured error objects (dicts or dataclasses) from pipeline functions; do not rely on string messages for control flow.**

---

## 5. Import and Module Organisation

17. **Import order (enforced by linter):**
    1. Standard library imports
    2. Third-party imports
    3. Project imports from `src/` (absolute: `from src.build_director import BuildPipeline`)
    4. Relative intra-package imports (only within the same subsystem directory)

    Separate each group with a single blank line.

18. **Never use wildcard imports (`from module import *`).** Every imported name must be explicit.

19. **Canonical module → class/object mapping (do not split these across files):**

    | Module                  | Primary Exports                                             |
    |-------------------------|-------------------------------------------------------------|
    | `src/consensus.py`      | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
    | `src/build_director.py` | `BuildPipeline` (orchestration, confidence gate, `pr_type` routing) |
    | `src/github_tools.py`   | `GitHubTool`, `WebhookReceiver`                             |
    | `src/build_ledger.py`   | `BuildLedger` (`claim`, `release`, `heartbeat`)             |
    | `src/document_store.py` | `DocumentStore` (`chunk`, `embed`, `retrieve`)              |
    | `src/ci_workflow.py`    | CI generation logic (`crafted-ci.yml`, `crafted-ci-macos.yml`) |

20. **Circular imports are forbidden.** If two subsystem packages need shared types, extract those types into a `_types.py` module inside the lower-level package.

---

## 6. Comment and Documentation Rules

21. **Every public class and public function must have a docstring.** Use imperative mood for the summary line:
    ```python
    def validate_write_path(raw_path: str) -> Path:
        """Validate raw_path against traversal attacks and return a safe Path."""
    ```

22. **Inline comments explain *why*, not *what*.** The code itself must be readable enough to convey *what*.

23. **TODO comments must include an engineer ID and a tracking reference:**
    ```python
    # TODO(fa-01): Remove legacy keyword fallback after TRD-3 v6.0 migration — GH-142
    ```

24. **No commented-out code in `main` or release branches.** Dead code must be deleted, not commented.

25. **TRD references in code use the format `TRD-{N}` (e.g., `TR