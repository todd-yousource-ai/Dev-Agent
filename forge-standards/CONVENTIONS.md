

# Code Conventions — Forge Platform

> Authoritative coding conventions for the Forge platform and the **ConsensusDevAgent** subsystem.
> Every rule is mandatory unless explicitly marked **(advisory)**.
> Last updated: 2025-01.

---

## 1. File and Directory Naming

1. **Source layout.** Production code lives under `src/` in subsystem directories. Each subsystem gets exactly one top-level slug:

   | Path | Subsystem |
   |---|---|
   | `src/cal/` | Conversation Abstraction Layer |
   | `src/dtl/` | Data Trust Label |
   | `src/trustflow/` | TrustFlow audit stream |
   | `src/vtz/` | Virtual Trust Zone enforcement |
   | `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
   | `src/mcp/` | MCP Policy Engine |
   | `src/rewind/` | Forge Rewind replay engine |
   | `sdk/connector/` | Forge Connector SDK |

2. **Test mirror rule.** Tests live under `tests/<subsystem>/` and mirror the `src/` tree exactly. A source file at `src/cal/session.py` has its tests at `tests/cal/test_session.py`.

3. **File names** are `snake_case`, lowercase, no hyphens. Maximum 40 characters before the extension.

4. **No single-use dispatch files.** Every file must be a complete, self-contained unit. Do not create a file whose only purpose is to import and call another file.

5. **Branch naming (mandatory):**
   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   Example: `forge-agent/build/ae7c/trustflow/pr-004-add-audit-sink`

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Suffix with the structural role when non-obvious (`…Engine`, `…Handler`, `…Policy`, `…Gate`, `…Sink`).

7. **Functions and methods:** `snake_case`. Prefix pure queries with `get_`, `fetch_`, or `is_`. Prefix mutation with `set_`, `apply_`, `update_`, or `delete_`.

8. **Constants:** `UPPER_SNAKE_CASE`, defined at module level.

9. **Private internals:** Single leading underscore (`_strip_code_fences`). Never use double underscores for name-mangling unless implementing descriptor protocol.

10. **axIdentifier naming (macOS / SwiftUI).** All interactive elements must set `.accessibilityIdentifier()` using the pattern:
    ```
    {module}-{component}-{role}-{context?}
    ```
    Examples:
    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```
    Every identifier segment is lowercase, hyphen-delimited. Dynamic suffixes use `{id}` at the end.

---

## 3. Error and Exception Patterns

11. **Custom exceptions** inherit from a single `ForgeError` base class defined in `src/errors.py`.

12. **Subsystem exceptions** are namespaced: `CalSessionError(ForgeError)`, `VtzViolationError(ForgeError)`, etc.

13. **Never swallow exceptions silently.** Every `except` block must either re-raise, log at `WARNING` or above, or convert to a documented return value (e.g., `None` with an explicit docstring contract).

14. **Graceful `None` returns.** Functions that query state which may not yet exist (e.g., `fetch_build_map()` before the first 5 PRs) must return `None` — never raise. Document this in the docstring.

15. **Validate paths before ANY write.** All user- or agent-supplied paths must pass through `validate_write_path` before any I/O:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```
    No alternative path-write pattern is permitted.

---

## 4. Import and Module Organisation

16. **Import order** (enforced by `isort` with the `black` profile):
    1. Standard library
    2. Third-party packages
    3. Forge platform (`src/`)
    4. Local relative imports

    Separate each group with one blank line.

17. **No dynamic code loading.** Do not use `eval()`, `exec()`, or `importlib.import_module()` to load generated files or subsystem modules.

18. **No runtime placeholders.** Do not generate template files containing `{{ }}` or `{placeholder}` tokens that are filled at runtime.

19. **Explicit imports only.** Do not use wildcard imports (`from module import *`) anywhere.

---

## 5. Comment and Documentation Rules

20. **Module docstring.** Every `.py` file starts with a one-line module docstring describing its purpose.

21. **Public API docstring.** Every public class and function has a Google-style docstring with `Args:`, `Returns:`, and `Raises:` sections (where applicable).

22. **Inline comments** explain *why*, not *what*. If the code needs a "what" comment, refactor the code.

23. **TODO format:** `# TODO(engineer_id): description — JIRA-XXX` or `# TODO(agent): description`. Bare `# TODO` is prohibited.

24. **No commented-out code** in any merged branch. Delete it; git has history.

---

## 6. ConsensusDevAgent-Specific Patterns

25. **Canonical `_strip_code_fences()` implementation.** This function appears in five modules. All five copies must be **character-identical**. The function must:
    - Accept an empty string or `None` and return it unchanged.
    - Preserve the trailing newline on non-empty output.
    - Not modify code that contains no fences or Unicode characters.
    - Be synchronous (no `async`).

    Any change to one copy must be applied to all five in the same commit.

26. **Generated file rules (GENERATION_SYSTEM v2.0):**
    - Every generated file must be complete and self-contained.
    - Do not generate a file whose only job is to call or dispatch to another generated file.
    - Do not use `eval()`, `exec()`, or `importlib.import_module()` inside generated code.
    - Do not generate template files with runtime placeholders.

27. **Build-map defensiveness.** `fetch_build_map()` must return `None` gracefully when no map exists yet (first ≤5 PRs of any build). It must never raise an exception. Test via `TestBuildMapLive`.

28. **Agent write safety.** Before performing any file write, the agent must:
    1. Call `validate_write_path()` (rule 15).
    2. Confirm the target directory is within the expected subsystem subtree.
    3. Never write outside `src/`, `tests/`, `sdk/`, or explicitly allow-listed paths.

29. **Consensus vote logging.** Every consensus decision (approve / reject / abstain) must emit a structured log entry containing at minimum: `timestamp`, `agent_id`, `vote`, `artifact_path`, and `rationale_hash`.

30. **Deterministic output.** Agent-generated code must not depend on wall-clock time, random seeds, or environment variables for correctness. Inject such dependencies explicitly via function parameters.

---

*Violations of any rule numbered above will block PR merge. For questions, open an issue tagged `conventions`.*