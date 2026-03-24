# CONVENTIONS.md — ForgeAgent Subsystem

All conventions below are derived from the project TRDs and are mandatory for every contribution to the ForgeAgent subsystem.

---

## 1. File and Directory Naming

1. **Python source directories use short, lowercase slugs matching the subsystem abbreviation.**
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

2. **Test directories mirror `src/` exactly.**
   - Source at `src/vtz/policy.py` → test at `tests/vtz/test_policy.py`.
   - Never place tests in a flat `tests/` directory without the subsystem subfolder.

3. **Key backend files retain their canonical names.**
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
   - `src/build_director.py` — `BuildPipeline`.

4. **CI workflow files use exact names — no alternatives.**
   - `crafted-ci.yml` (Ubuntu pipeline).
   - `crafted-ci-macos.yml` (macOS Swift pipeline).

5. **Root-only files must never be placed inside a subdirectory.** Validate by basename against this set:
   - `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.

6. **`conftest.py` is auto-committed by `ci_workflow.ensure()` for `src/` import resolution.** Do not manually create, move, or delete it.

---

## 2. Branch Naming

7. **Every ForgeAgent branch must follow this exact pattern:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — lowercase GitHub username or numeric ID.
   - `subsystem_slug` — matches one of the `src/` directory slugs (e.g., `vtz`, `cal`, `trustflow`).
   - `N` — zero-padded to three digits (`001`, `042`).
   - `title_slug` — lowercase, hyphen-separated, no special characters.

   Example: `forge-agent/build/jdoe/vtz/pr-017-add-zone-validator`

8. **The `forge-agent` prefix is mandatory and kept as-is for compatibility.** Do not rename it to `forge_agent` or any other variant.

---

## 3. Class and Function Naming

9. **Classes use PascalCase.** Suffix with the subsystem role when the class is a primary entry point:
   - `ConsensusEngine`, `BuildPipeline`, `TrustFlowAuditor`, `RewindReplayEngine`.

10. **Functions and methods use snake_case.** Prefix private helpers with a single underscore:
    - `validate_write_path()`, `_resolve_gate_action()`.

11. **Module-level constants use UPPER_SNAKE_CASE:**
    - `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

12. **Internal keyword/config lists are prefixed with a single underscore:**
    - `_docs_keywords`, `_is_docs_pr`.
    - When a constant set is removed in a later version, delete it entirely — do not comment it out.

---

## 4. Error and Exception Patterns

13. **Validate every path before any write operation.** Use the project's `path_security` module — never write to a user-supplied path directly:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    ```

14. **Raise specific exceptions, not bare `Exception`.** Name custom exceptions with a subsystem prefix:
    - `VTZPathTraversalError`, `DTLValidationError`, `TrustFlowAuditError`.

15. **Never silently swallow exceptions in agent code.** At minimum, log at `WARNING` level before applying a fallback.

16. **When `validate_write_path` returns a safe default (traversal detected), log the original path at `ERROR` level** with enough context to identify the caller.

---

## 5. Import and Module Organisation

17. **Group imports in this order, separated by a blank line:**
    1. Standard library.
    2. Third-party packages.
    3. Project modules (`src.*`, `sdk.*`).

18. **Always use absolute imports rooted at `src/` or `sdk/`:**

    ```python
    from src.vtz.policy import enforce_zone
    from src.consensus import ConsensusEngine
    ```

19. **Do not add manual `sys.path` hacks.** Import resolution for tests is handled by the auto-committed `conftest.py`.

20. **Circular imports are forbidden.** If two subsystem packages need each other, extract shared types into a `src/<subsystem>/types.py` module.

---

## 6. Comment and Documentation Rules

21. **Every public class and function must have a docstring.** Use imperative mood in the summary line:

    ```python
    def validate_write_path(raw_path: str) -> Path:
        """Return a safe, resolved path or a secure default when traversal is detected."""
    ```

22. **Inline comments explain *why*, not *what*.** Do not restate the code:

    ```python
    # Fall back to project root to prevent symlink escape (see TRD-3 §4.2)
    safe_path = PROJECT_ROOT / "sandbox" / filename
    ```

23. **Reference TRD sections when a rule's rationale is non-obvious:** use the format `(see TRD-N §X.Y)`.

24. **Do not leave TODO/FIXME comments without an associated issue number:**

    ```python
    # TODO(#148): Replace static keyword list once semantic classifier ships.
    ```

---

## 7. ForgeAgent-Specific Patterns

### 7.1 Accessibility Identifiers (SwiftUI)

25. **Every interactive SwiftUI element must set `.accessibilityIdentifier()`.** Follow the pattern:

    ```
    {module}-{component}-{role}-{context?}
    ```

    - `module` — feature area (`auth`, `settings`, `navigator`, `stream`).
    - `component` — specific widget target (`touchid`, `anthropic-key`, `project`, `gate`).
    - `role` — element type (`button`, `field`, `row`, `card`).
    - `context` — optional dynamic suffix, always a variable ID.

26. **Canonical identifier examples (treat as the source of truth):**

    | Identifier | Element |
    |---|---|
    | `auth-touchid-button` | Touch ID authentication button |
    | `auth-passcode-button` | Passcode fallback button |
    | `settings-anthropic-key-field` | API key text field |
    | `settings-anthropic-key-test-button` | Key validation button |
    | `settings-anthropic-key-reveal-button` | Key visibility toggle |
    | `navigator-project-row-{projectId}` | Project list row |
    | `stream-gate-card-{gateId}` | Gate decision card |
    | `stream-gate-yes-button-{gateId}` | Approve gate action |
    | `stream-gate-skip-button-{gateId}` | Skip gate action |
    | `stream-gate-stop-button-{gateId}` | Stop gate action |

27. **Never hard-code a dynamic ID segment.** Always interpolate the runtime identifier:

    ```swift
    .accessibility