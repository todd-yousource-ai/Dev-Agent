# CONVENTIONS.md — CraftedDevAgent Subsystem

---

## 1. File and Directory Naming

1. **Python source files** live under `src/` and use `snake_case.py`.
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — `BuildPipeline`
   - New modules follow the same pattern: `src/{domain}_{purpose}.py`.

2. **CI workflow files** are named exactly:
   - `crafted-ci.yml` (Ubuntu runners)
   - `crafted-ci-macos.yml` (macOS / Swift runners)
   - No other naming variants are permitted.

3. **Repo-root files** — the following files must always be committed at the repository root with no directory prefix:
   `README.md`, `CODEOWNERS`, `LICENSE`, `.gitignore`, `.editorconfig`, `VERSION`, `Makefile`, `pyproject.toml`.
   Validation checks basename membership in this known set, not parent directory.

4. **`conftest.py`** is auto-committed by `ci_workflow.ensure()` to enable `src/` imports in tests. Never hand-edit or delete this file; the pipeline owns it.

5. **Test files** mirror source layout: `tests/test_{module}.py` maps to `src/{module}.py`.

---

## 2. Class and Function Naming

6. **Classes** use `PascalCase`: `ConsensusEngine`, `BuildPipeline`, `CraftedDevAgent`.

7. **Functions and methods** use `snake_case`: `validate_write_path`, `ensure`, `run_build`.

8. **Constants** use `UPPER_SNAKE_CASE`: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

9. **Private helpers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.  
   Double-underscore name-mangling is not used unless strictly required for inheritance safety.

10. **Branch names** follow the mandatory format (kept as `forge-agent` for compatibility):
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id` — lowercase alphanumeric, no spaces.
    - `subsystem_slug` — lowercase hyphen-separated (e.g., `crafted-dev-agent`).
    - `N` — zero-padded to three digits.
    - `title_slug` — lowercase, hyphens only, max 48 characters.

---

## 3. Error and Exception Patterns

11. **Path validation before every write.** No file-system write may occur without calling `validate_write_path` first:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    Any code path that skips this call is a blocking review finding.

12. **Custom exceptions** inherit from a project-level base: `class CraftedError(Exception)`.  
    Subsystem exceptions extend it: `class PathTraversalError(CraftedError)`.

13. **Never catch bare `Exception` or `BaseException`** in agent logic. Catch the narrowest type, log context, and re-raise or return a structured error.

14. **Error messages** include the operation attempted and the offending value:
    ```python
    raise PathTraversalError(f"Write blocked: resolved path '{resolved}' escapes workspace '{workspace}'")
    ```

---

## 4. Import and Module Organisation

15. **Import order** (enforced by `isort` profile `black`):
    1. Standard library
    2. Third-party packages
    3. Project-local (`src.*`)
    4. Relative imports (only within the same package)

    Each group separated by a blank line.

16. **No wildcard imports.** `from module import *` is prohibited.

17. **Lazy imports** are permitted only inside functions when needed to break circular dependencies; add a `# lazy import: circular` comment.

18. **`conftest.py` sys-path injection** is the sole mechanism for making `src/` importable in tests. Do not add manual `sys.path` hacks in test files.

---

## 5. Comment and Documentation Rules

19. **Module docstrings** are mandatory. First line states the single responsibility; second paragraph (if needed) lists key public symbols.

20. **Public functions and classes** require a docstring with `Args:`, `Returns:`, and `Raises:` sections (Google style).

21. **Inline comments** explain *why*, not *what*. If a comment restates the code, delete it.

22. **TODO comments** must include an engineer ID and issue reference:
    ```python
    # TODO(jdoe): handle retry logic — see #142
    ```

23. **Keyword-based doc detection** (used in CI for PR classification) is deprecated as of pipeline v6.0. Do not add to or rely on `_docs_keywords` sets.

---

## 6. CraftedDevAgent-Specific Patterns

### 6.1 Accessibility Identifiers (axIdentifier)

24. **Every interactive SwiftUI element** must set `.accessibilityIdentifier()` using the convention:
    ```
    {module}-{component}-{role}-{context?}
    ```
    All segments are lowercase, hyphen-separated.

25. **Reference examples** (canonical — copy the pattern, not the literal strings):
    | Identifier | Breakdown |
    |---|---|
    | `auth-touchid-button` | module `auth`, component `touchid`, role `button` |
    | `settings-anthropic-key-field` | module `settings`, component `anthropic-key`, role `field` |
    | `settings-anthropic-key-test-button` | module `settings`, component `anthropic-key-test`, role `button` |
    | `settings-anthropic-key-reveal-button` | module `settings`, component `anthropic-key-reveal`, role `button` |
    | `navigator-project-row-{projectId}` | module `navigator`, component `project`, role `row`, context = dynamic ID |
    | `stream-gate-card-{gateId}` | module `stream`, component `gate`, role `card`, context = dynamic ID |
    | `stream-gate-yes-button-{gateId}` | module `stream`, component `gate-yes`, role `button`, context = dynamic ID |
    | `stream-gate-skip-button-{gateId}` | module `stream`, component `gate-skip`, role `button`, context = dynamic ID |
    | `stream-gate-stop-button-{gateId}` | module `stream`, component `gate-stop`, role `button`, context = dynamic ID |

26. **Dynamic context** (e.g., `{projectId}`, `{gateId}`) is appended with a hyphen after the role segment. Use the model's stable ID, never an array index.

### 6.2 Path Security

27. **Rule restatement for agents:** The CraftedDevAgent must call `validate_write_path` on every user-supplied or LLM-generated path *before* any `open()`, `shutil`, or subprocess write. This is the single most critical security invariant in the subsystem.

### 6.3 CI Pipeline Integration

28. **`ci_workflow.ensure()`** is the entry point for pipeline setup. It is idempotent and must be called at the start of every build invocation. It creates or updates `conftest.py` and validates workflow file presence.

29. **PR title classification** for docs-only PRs must not use keyword matching (removed in v6.0). Use file-path heuristics instead (e.g., changes only under `docs/`).

### 6.4 Consensus and Generation

30. **`ConsensusEngine`** is the single source of truth for prompt assembly. Agent code must never inline system prompts; instead reference `GENERATION_SYSTEM`,