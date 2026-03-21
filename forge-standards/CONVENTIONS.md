

# Code Conventions — Forge Platform

> Canonical reference for all contributors and agents operating within the Forge mono-repo.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly.**

   ```
   src/cal/           – Conversation Abstraction Layer
   src/dtl/           – Data Trust Label
   src/trustflow/     – TrustFlow audit stream
   src/vtz/           – Virtual Trust Zone enforcement
   src/trustlock/     – Cryptographic machine identity (TPM-anchored)
   src/mcp/           – MCP Policy Engine
   src/rewind/        – Forge Rewind replay engine
   sdk/connector/     – Forge Connector SDK
   tests/<subsystem>/ – Tests mirror src/ structure exactly
   ```

2. **Python files** use `snake_case.py`. Maximum 40 characters before the extension.

3. **Swift files** use `PascalCase.swift`, one primary type per file, filename matches the type name.

4. **Test files** are prefixed with `test_` (Python) or suffixed with `Tests` (Swift) and live under `tests/<subsystem>/` mirroring the source tree.  
   Example: `src/cal/session.py` → `tests/cal/test_session.py`.

5. **No spaces, no uppercase letters** in directory names. Use hyphens only in documentation filenames (`TRD-02-Consensus-Engine.md`). Use underscores in all code-adjacent filenames.

6. **Generated files** must carry the suffix `_gen` before the extension (e.g., `schema_gen.py`). Never generate a file whose only purpose is to call or dispatch to another generated file.

---

## 2. Branch Naming

7. **Mandatory pattern for all agent-created branches:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — the alphanumeric ID of the responsible engineer.
   - `subsystem_slug` — matches one of the directory slugs in rule 1 (e.g., `cal`, `vtz`).
   - `N` — zero-padded to three digits, monotonically increasing per subsystem per engineer.
   - `title_slug` — lowercase, hyphen-separated, ≤ 48 characters.

   Example: `forge-agent/build/eng042/trustflow/pr-007-add-audit-retention-policy`

---

## 3. Class and Function Naming

8. **Python classes** — `PascalCase`. No prefix/suffix indicating the module; the module path provides context.

9. **Python functions and methods** — `snake_case`. Public functions start with a verb (`compute_hash`, `validate_token`). Private helpers are prefixed with a single underscore (`_parse_header`).

10. **Swift types** — `PascalCase`. Protocols end in `-able`, `-ing`, or `-Provider` (e.g., `TrustEvaluable`, `KeyProvider`).

11. **Swift methods and properties** — `camelCase`. Boolean properties read as assertions (`isValid`, `hasExpired`).

12. **Constants** — `UPPER_SNAKE_CASE` in Python, `camelCase` static let in Swift.

13. **axIdentifier values (macOS/iOS)** follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element.

    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-yes-button-{gateId}"
    ```

    All four segments are lowercase, hyphen-separated. The optional `{context}` segment is a dynamic ID when the element repeats.

---

## 4. Error and Exception Patterns

14. **Custom exception hierarchy.** Every subsystem defines exceptions in a single `exceptions.py` file at its package root.

    ```python
    # src/cal/exceptions.py
    class CALError(Exception):
        """Base for all CAL exceptions."""

    class SessionExpiredError(CALError): ...
    class TokenValidationError(CALError): ...
    ```

15. **Never catch bare `Exception`** unless re-raising or logging at the outermost boundary.

16. **Error messages** are a single English sentence, no trailing period, starting with a lowercase letter.

    ```python
    raise TokenValidationError("token signature does not match expected key")
    ```

17. **Graceful `None` returns vs. exceptions.** Functions that query external/optional state (e.g., `fetch_build_map()`) must return `None` — never raise — when the resource does not yet exist. Document this in the docstring with `Returns None if …`.

18. **Path validation before any write.** All code paths that write to disk must call `validate_write_path` first. No exceptions.

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    ```

---

## 5. Import and Module Organisation

19. **Import order** (enforced by `isort` with the profile `black`):
    1. Standard library
    2. Third-party packages
    3. Forge-internal packages (`src.*`, `sdk.*`)
    4. Local relative imports

    Each group separated by a single blank line.

20. **No wildcard imports** (`from x import *`) anywhere in the codebase.

21. **No dynamic loading in generated code.** Generated files must never use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files.

22. **Every generated file is complete and self-contained.** It must not contain runtime placeholders or require a second generation pass.

23. **Circular import guard.** If two modules need each other, extract the shared type into a `_types.py` file in the common parent package.

---

## 6. Comment and Documentation Rules

24. **Docstrings** — Google style for Python, `///` doc comments for Swift. Every public function, class, and module has a docstring.

25. **Inline comments** explain *why*, never *what*. If a comment restates the code, delete it.

26. **TODO format** — `# TODO(engineer_id): description — YYYY-MM-DD`. TODOs without an engineer ID and date are rejected by CI.

27. **TRD references** — When implementing a TRD requirement, cite it:

    ```python
    # ref: TRD-02 §8.1 — generated files must be self-contained
    ```

28. **CHANGELOG entries** — Every PR adds a one-line entry under the appropriate subsystem heading in `CHANGELOG.md` using the format: `- [PR-NNN] Description. (engineer_id)`

---

## 7. ConsensusDevAgent-Specific Patterns

29. **`_strip_code_fences()` is canonical and identical.** The function exists in exactly five modules. All five copies must be byte-identical. Any change must be applied to all five simultaneously in the same commit. The function must:
    - Accept an empty string or `None` and return the value unchanged.
    - Preserve trailing newline on non-empty output.
    - Not modify code that has no fences or Unicode escape characters.
    - Be synchronous — no `async`.

30. **Consensus voting payloads** are frozen dataclasses (Python) or `Sendable` structs (Swift). Never use a plain dictionary for inter-agent messages.

31. **Agent write safety.** Every ConsensusDevAgent code path that touches the filesystem must:
    1. Call `validate_write_path()` (rule 18).
    2. Write to a temporary file first, then atomically rename.
    3. Log the final path and SHA-256 of the written content at `INFO` level.

32. **Build-map tolerance.** `fetch_build_map()` must return `None` without raising when no map exists (expected for the first five PRs of any build). Callers must handle the `None` case explicitly — no bare `assert`