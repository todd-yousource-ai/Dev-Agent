# CONVENTIONS.md — Crafted Subsystem

All conventions derived from the Crafted TRD documents. Every rule is mandatory.

---

## 1. File and Directory Naming

1. **Python source files** use `snake_case.py` and live under `src/`.
   - `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/build_ledger.py`, `src/document_store.py`, `src/ci_workflow.py`.

2. **Subsystem directories** use short lowercase slugs under `src/`:
   - `src/cal/` — Conversation Abstraction Layer.
   - `src/dtl/` — Data Trust Label.
   - `src/trustflow/` — TrustFlow audit stream.
   - `src/vtz/` — Virtual Trust Zone enforcement.
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored).
   - `src/mcp/` — MCP Policy Engine.
   - `src/rewind/` — Forge Rewind replay engine.
   - `sdk/connector/` — Forge Connector SDK.

3. **Tests mirror `src/` exactly.** A source file at `src/dtl/label.py` must have its test at `tests/dtl/test_label.py`. No exceptions.

4. **CI workflow files** are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is permitted.

5. **`conftest.py`** at the repo root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Do not manually create or delete it.

6. **Swift source files** use `PascalCase.swift` matching the primary type they declare (e.g., `StreamGateCard.swift`).

---

## 2. Branch Naming

7. **All agent branches** follow this exact pattern — no deviations:
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric identifier of the assigned engineer.
   - `subsystem_slug`: lowercase hyphenated subsystem name (e.g., `crafted`, `trustflow`).
   - `N`: zero-padded to three digits (e.g., `001`, `042`).
   - `title_slug`: lowercase hyphen-separated summary (e.g., `add-gate-card-view`).
   - The `forge-agent` prefix is **intentional for compatibility** — do not rename to `forge-agents` or any variant.

---

## 3. Class and Function Naming

8. **Python classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `GitHubTool`, `WebhookReceiver`, `BuildLedger`, `DocumentStore`.

9. **Python functions and methods** use `snake_case`: `validate_write_path()`, `claim()`, `release()`, `heartbeat()`, `chunk()`, `embed()`, `retrieve()`.

10. **Python constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

11. **Swift types** use `PascalCase`. **Swift properties and methods** use `camelCase`. Follow standard Swift API Design Guidelines.

12. **Private/internal identifiers** in Python are prefixed with a single underscore: `_docs_keywords`, `_is_docs_pr`.

---

## 4. Accessibility Identifier Naming (axIdentifier)

13. **Every interactive SwiftUI element** must have an `.accessibilityIdentifier()` set. No interactive element ships without one.

14. **axIdentifier format** is `{module}-{component}-{role}-{context?}`, all lowercase, hyphen-separated:
    - `module`: the feature area (e.g., `auth`, `settings`, `navigator`, `stream`).
    - `component`: the specific UI component (e.g., `touchid`, `anthropic-key`, `project`, `gate`).
    - `role`: the element's semantic role (e.g., `button`, `field`, `row`, `card`).
    - `context` (optional): a dynamic suffix for list items, formatted as `-{dynamicId}`.

15. **Canonical examples** — memorise these patterns:
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

16. **Dynamic IDs** in axIdentifiers (e.g., `{projectId}`, `{gateId}`) must be stable, non-nil identifiers — never array indices.

---

## 5. Path Security and Write Validation

17. **Validate every path before any file-system write.** No write operation may proceed against a user-supplied or externally-derived path without validation.

18. **Use the canonical validation call:**
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
    `validate_write_path` returns a safe default on directory-traversal attempts. Never catch and suppress its rejections.

19. **Never construct write paths via string concatenation** from untrusted input. Always pass through `validate_write_path` first.

---

## 6. Error and Exception Patterns

20. **Custom exceptions** are `PascalCase` and end with `Error`: `PathTraversalError`, `ClaimConflictError`, `EmbeddingError`.

21. **Never use bare `except:` or `except Exception:` to silently swallow errors.** Every catch block must either re-raise, log with full context, or return a well-defined error type.

22. **Path security violations** must raise or return immediately — never fall through to a default write path silently.

23. **CI failures** must surface the specific failing check name and exit code. Do not wrap CI results in generic error messages.

---

## 7. Import and Module Organisation

24. **Import order** (enforced, separated by blank lines):
    1. Standard library imports.
    2. Third-party library imports.
    3. Forge/Crafted internal imports (from `src/`).

25. **Always use explicit relative or absolute imports from `src/`.** Do not use `sys.path` hacks; rely on the auto-committed `conftest.py` for test discovery.

26. **One primary class per module.** The file name reflects the class: `build_ledger.py` → `BuildLedger`, `document_store.py` → `DocumentStore`.

27. **Subsystem `__init__.py` files** must exist but should only re-export the public API of that subsystem. No logic in `__init__.py`.

---

## 8. Comment and Documentation Rules

28. **Module-level docstring** is required in every Python file. It must state the module's single responsibility in one sentence, then list key classes/functions.

29. **Class docstrings** use triple double-quotes and state what the class *is*, not what it *does*:
    ```python
    class BuildLedger:
        """Persistent ledger tracking build claims, releases, and heartbeats."""
    ```

30. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

31. **TODO comments** must include an engineer ID or issue reference: `# TODO(engineer-id): description` or `# TODO(#123): description`. Orphan TODOs are not permitted.

32. **Swift documentation comments** use `///` for public APIs. Every public Swift type and method must have a doc comment.

---

## 9. Crafted-Specific Patterns

33. **`ci_workflow.ensure()`** is the single entry point for CI file generation