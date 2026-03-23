# CONVENTIONS.md — Crafted Subsystem

All conventions below are derived from the Crafted TRD documents and the Forge Architecture Context. Every rule is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py` exclusively. No hyphens, no camelCase.
   ```
   src/consensus.py
   src/build_director.py
   src/github_tools.py
   src/build_ledger.py
   src/document_store.py
   src/ci_workflow.py
   ```

2. **Subsystem directories** are short, lowercase, single-word slugs under `src/`:
   ```
   src/cal/          # Conversation Abstraction Layer
   src/dtl/          # Data Trust Label
   src/trustflow/    # TrustFlow audit stream
   src/vtz/          # Virtual Trust Zone enforcement
   src/trustlock/    # Cryptographic machine identity
   src/mcp/          # MCP Policy Engine
   src/rewind/       # Forge Rewind replay engine
   ```

3. **SDK connector code** lives under `sdk/connector/`.

4. **Test directories** mirror `src/` structure exactly:
   ```
   tests/cal/
   tests/dtl/
   tests/trustflow/
   tests/vtz/
   ```

5. **CI workflow files** are named with the `crafted-` prefix:
   - `crafted-ci.yml` — Ubuntu runner pipeline.
   - `crafted-ci-macos.yml` — macOS Swift runner pipeline.

6. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to guarantee `src/` is importable. Never hand-edit the auto-generated `conftest.py`; if custom fixtures are needed, place them in `tests/conftest_custom.py` and import from the generated one.

---

## 2. Branch Naming

7. **Every agent-created branch** must follow this exact pattern:
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - `engineer_id`: lowercase alphanumeric identifier of the build engineer.
   - `subsystem_slug`: e.g. `crafted`, `cal`, `dtl`.
   - `N`: zero-padded to three digits (`001`, `012`, `143`).
   - `title_slug`: lowercase, hyphen-separated summary (max 48 chars).

   Example:
   ```
   forge-agent/build/eng-04/crafted/pr-007-add-gate-card-view
   ```

8. The prefix `forge-agent` is **not** to be renamed for backward compatibility with existing tooling.

---

## 3. Class and Function Naming

9. **Python classes**: `PascalCase`. One public class per file when the class is the file's primary export.
   ```python
   class BuildPipeline: ...      # in build_director.py
   class ConsensusEngine: ...    # in consensus.py
   class DocumentStore: ...      # in document_store.py
   class BuildLedger: ...        # in build_ledger.py
   ```

10. **Python functions and methods**: `snake_case`. Verb-first for actions, noun-phrase for accessors.
    ```python
    def claim_build(self, build_id): ...
    def release_lock(self): ...
    def retrieve_chunks(self, query): ...
    ```

11. **Private helpers**: single leading underscore. Never use double underscore name-mangling unless preventing subclass collision is the explicit goal.
    ```python
    def _validate_confidence(self, score): ...
    ```

12. **Constants**: `UPPER_SNAKE_CASE`, defined at module top-level.
    ```python
    GENERATION_SYSTEM = "..."
    SWIFT_GENERATION_SYSTEM = "..."
    UI_ADDENDUM = "..."
    ```

13. **Swift types** (macOS Crafted app): `PascalCase` for types and protocols, `camelCase` for properties and methods. Follow standard Swift API Design Guidelines.

---

## 4. Crafted-Specific Patterns

### 4.1 axIdentifier Naming (Accessibility Identifiers)

14. Every interactive SwiftUI element **must** have an `.accessibilityIdentifier()` set.

15. The identifier follows the pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    - `module`: feature area (`auth`, `settings`, `navigator`, `stream`).
    - `component`: specific UI element (`touchid`, `anthropic-key`, `project`, `gate`).
    - `role`: semantic role (`button`, `field`, `row`, `card`).
    - `context` (optional): dynamic discriminator, typically an ID.

16. **Canonical examples** — deviate from these patterns only with PR-level justification:
    ```swift
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

17. Dynamic segments (e.g. `{projectId}`, `{gateId}`) must use the **canonical model ID**, not array indices or display names.

### 4.2 Path Security — Mandatory Write Validation

18. **Every file-write operation** must validate the target path before writing. No exceptions.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on path-traversal attempt;
    # never silently passes "../" or symlink escapes.
    ```

19. Never construct write paths with string concatenation or f-strings from user input without passing through `validate_write_path` first.

20. If `validate_write_path` returns a safe default (i.e., the input was rejected), log the attempt at `WARNING` level with the original input for audit.

### 4.3 PR-Type Routing and Confidence Gate

21. `build_director.py` routes PRs by type. The PR title and label metadata drive routing — do not embed routing logic elsewhere.

22. Documentation-only PRs are detected structurally (file-path patterns: `docs/`, `*.md`, `CHANGELOG`), **not** by keyword matching against title strings. The keyword-list approach (`_docs_keywords`) was removed in TRD-3 v6.0 and must not be reintroduced.

### 4.4 Build Ledger Lifecycle

23. Every build operation follows the **claim → heartbeat → release** lifecycle via `BuildLedger`:
    ```python
    ledger.claim(build_id)
    try:
        # ... do work, periodically call ledger.heartbeat(build_id)
    finally:
        ledger.release(build_id)
    ```

24. `release` must always be in a `finally` block or equivalent cleanup path.

---

## 5. Error and Exception Patterns

25. Define subsystem-specific exception classes in a `exceptions.py` file within the subsystem directory:
    ```
    src/cal/exceptions.py
    src/vtz/exceptions.py
    ```

26. Exception classes inherit from a single `CraftedError` base class defined in `src/exceptions.py`:
    ```python
    class CraftedError(Exception):
        """Base for all Crafted subsystem errors."""

    class PathTraversalError(CraftedError): ...
    class BuildClaimError(CraftedError): ...
    class ConsensusError(CraftedError): ...
    ```

27. Never catch bare `Exception` or `BaseException` in production code. Catch the most specific `CraftedError` subclass possible.