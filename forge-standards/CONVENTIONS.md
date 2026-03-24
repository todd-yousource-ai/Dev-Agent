# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the ForgeAgent TRD documents. Every item is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1. **Source directories use short, lowercase abbreviations matching their subsystem:**
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

2. **Test directories mirror `src/` exactly.** A source file at `src/vtz/enforcer.py` must have its tests at `tests/vtz/test_enforcer.py`.

3. **Python source files use `snake_case.py`.** No hyphens, no uppercase.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`

4. **Root-anchored files must remain at repository root without any directory prefix.** The canonical set is:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validate these by basename against this known set, never by directory path.

5. **CI workflow files use the exact canonical names:**
   - `crafted-ci.yml` — Ubuntu pipeline
   - `crafted-ci-macos.yml` — macOS Swift pipeline

6. **`conftest.py` is auto-committed** by `ci_workflow.ensure()` to enable `src/` imports in tests. Never delete or manually edit this file.

---

## 2. Class and Function Naming

7. **Classes use `PascalCase`.** Suffix with role when ambiguous: `ConsensusEngine`, `BuildPipeline`, `TrustFlowAuditor`.

8. **Functions and methods use `snake_case`.** Prefix private helpers with a single underscore: `_resolve_gate_state()`.

9. **Constants use `UPPER_SNAKE_CASE`.** Module-level only: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

10. **Internal keyword/set variables use a leading underscore and lowercase:** `_docs_keywords`, `_is_docs_pr`.

11. **SwiftUI accessibility identifiers follow the pattern `{module}-{component}-{role}-{context?}`**, set via `.accessibilityIdentifier()` on every interactive element:
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
    All four segments are lowercase, hyphen-delimited. The `{context}` segment is optional and uses a dynamic ID when the element is repeated.

---

## 3. Error and Exception Patterns

12. **Validate every path before any write operation.** No exceptions:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```
    Never call `open(..., 'w')`, `Path.write_text()`, `shutil.copy()`, or any filesystem mutation without passing the target through `validate_write_path` first.

13. **Raise domain-specific exceptions**, not bare `Exception` or `RuntimeError`. Name them `<Subsystem>Error`:
    - `PathTraversalError`
    - `ConsensusError`
    - `TrustFlowError`
    - `VTZViolationError`

14. **Never silently swallow exceptions.** Every `except` block must either re-raise, log at `WARNING` or above, or return an explicit sentinel that the caller is documented to handle.

---

## 4. Import and Module Organisation

15. **Import order** (enforced by tooling, separated by blank lines):
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules (absolute imports from `src`)
    4. Local relative imports (same package)

16. **Always use absolute imports from `src/`** in application code:
    ```python
    from src.consensus import ConsensusEngine
    from src.vtz.enforcer import validate_zone
    ```

17. **Tests import via the `src` package** made available by the auto-committed `conftest.py`. Do not add `sys.path` hacks in test files.

18. **Circular imports are forbidden.** If module A needs a type from module B and vice versa, extract the shared type into a third module under the same subsystem directory.

---

## 5. Comment and Documentation Rules

19. **Every public class and function requires a docstring.** Use imperative mood for the summary line:
    ```python
    def validate_write_path(path: str) -> Path:
        """Validate and sanitise a user-supplied path against traversal attacks."""
    ```

20. **Inline comments explain *why*, not *what*.** If the code needs a *what* comment, refactor the code instead.

21. **TODO comments must include an engineer ID and ticket reference:**
    ```python
    # TODO(eng-042): Replace naive retry with exponential backoff — FORGE-1187
    ```

22. **No commented-out code in `main` or any release branch.** Delete it; Git has history.

---

## 6. ForgeAgent-Specific Patterns

23. **Branch naming is mandatory and follows this exact format:**
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id`: the assigned engineer identifier (e.g., `eng-042`)
    - `subsystem_slug`: lowercase subsystem name matching `src/` directory (e.g., `vtz`, `trustflow`)
    - `N`: zero-padded three-digit PR sequence number
    - `title_slug`: lowercase, hyphen-delimited summary (max 48 chars)

    Example: `forge-agent/build/eng-042/trustflow/pr-007-add-audit-rotation`

    The prefix `forge-agent` is kept intentionally for tooling compatibility — do not shorten to `fa` or any alias.

24. **Docs-only PR detection** uses keyword matching against the PR title (lowercase). The keyword set and detection flag are module-level private variables:
    ```python
    _docs_keywords = {"naming convention", "glossary", "changelog", ...}
    _is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...
    ```
    This pattern was present in v5.0 and removed in v6.0. Do not reintroduce inline keyword lists — route through a single canonical set if the feature is re-enabled.

25. **Root-file validation is by basename, not path prefix.** When checking whether a file belongs to the root-anchored set (rule 4), compare `Path(file).name` against the known set. Never assume the working directory or compare directory components.

26. **All interactive SwiftUI elements must have an `accessibilityIdentifier`** conforming to rule 11. CI accessibility audits will fail any PR that adds a `Button`, `TextField`, `Toggle`, or `SecureField` without one.

27. **Path security is the first gate in every ForgeAgent write flow.** Any new function that creates, moves, copies, or overwrites a file