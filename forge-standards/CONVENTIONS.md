# Code Conventions

## File and Directory Naming

1. **Place all Python implementation code for ForgeAgent under `src/`.**
   - Use `src/consensus.py` for `ConsensusEngine` and related generation-system constants.
   - Use `src/build_director.py` for `BuildPipeline`.
   - Do not place backend Python modules at repository root.

2. **Use the subsystem directories defined by the architecture context exactly as named.**
   - Valid directory names from the TRDs:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`
   - Do not invent alternate spellings or abbreviations for these directories.

3. **Mirror `src/` structure exactly under `tests/`.**
   - For every module under `src/<subsystem>/...`, create tests under `tests/<subsystem>/...`.
   - Example:
     - Source: `src/trustflow/audit_stream.py`
     - Test: `tests/trustflow/test_audit_stream.py`

4. **Keep required repository-root files at the repo root with no directory prefix.**
   - The following filenames must exist only by basename at root when present:
     - `README.md`
     - `CODEOWNERS`
     - `LICENSE`
     - `.gitignore`
     - `.editorconfig`
     - `VERSION`
     - `Makefile`
     - `pyproject.toml`
   - Do not move these into `docs/`, `config/`, or any other folder.

5. **Use the mandated CI workflow filenames exactly.**
   - Ubuntu workflow: `crafted-ci.yml`
   - macOS Swift workflow: `crafted-ci-macos.yml`
   - Do not create renamed variants for the primary CI workflows.

6. **Do not manually duplicate `conftest.py` bootstrap logic that is auto-managed by CI.**
   - `conftest.py` for `src/` imports is auto-committed by `ci_workflow.ensure()`.
   - If test import setup is needed, extend the managed file rather than creating parallel import bootstraps elsewhere.

7. **Name Python source files in `snake_case.py`.**
   - Examples derived from the TRDs:
     - `build_director.py`
     - `consensus.py`
     - `audit_stream.py`
   - Match the dominant naming already specified in the architecture documents.

8. **Name test files `test_<module>.py`.**
   - The test filename must correspond to the source module it covers.
   - Example:
     - `src/cal/session_state.py` → `tests/cal/test_session_state.py`

9. **Use branch names in the exact required compatibility format.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/alex/trustflow/pr-007-audit-stream-fix`
   - Do not substitute another prefix for `forge-agent`.

---

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Required examples from TRDs:
     - `ConsensusEngine`
     - `BuildPipeline`

2. **Name functions and methods in `snake_case`.**
   - Example from TRD usage:
     - `validate_write_path(...)`

3. **Name module-level constants in `UPPER_SNAKE_CASE`.**
   - Required examples from TRDs:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

4. **Use subsystem-specific names that match the architecture vocabulary.**
   - Prefer names that preserve the canonical subsystem term:
     - `TrustFlow...` for trustflow components
     - `VirtualTrustZone...` or `VTZ...` for `vtz`
     - `TrustLock...` for `trustlock`
   - Do not replace canonical subsystem names with unrelated synonyms.

5. **When a file is explicitly assigned a primary class in the TRD, keep that class in that file.**
   - `src/consensus.py` must contain `ConsensusEngine`.
   - `src/build_director.py` must contain `BuildPipeline`.

6. **Use accessibility identifier values in the exact hyphenated convention for interactive macOS UI elements.**
   - Format:
     - `{module}-{component}-{role}-{context?}`
   - Apply via `.accessibilityIdentifier(...)` on all interactive elements.

7. **Use lowercase, hyphen-separated accessibility identifier segments.**
   - Valid examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`

8. **Append dynamic identifiers at the end of accessibility identifiers when the UI element represents a specific entity.**
   - Examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-yes-button-{gateId}`
     - `stream-gate-skip-button-{gateId}`
     - `stream-gate-stop-button-{gateId}`

9. **Include a role segment in every accessibility identifier for interactive controls.**
   - Use explicit role words such as:
     - `button`
     - `field`
     - `row`
     - `card`

---

## Error and Exception Patterns

1. **Validate paths before any write operation, without exception.**
   - Before writing any user-supplied or derived path, call:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Perform the write only against `safe_path`.

2. **Never write directly to a raw user-supplied path.**
   - Disallowed:
   ```python
   with open(user_supplied_path, "w") as f:
       ...
   ```
   - Required:
   ```python
   safe_path = validate_write_path(user_supplied_path)
   with open(safe_path, "w") as f:
       ...
   ```

3. **Apply path validation even when the path is only partially user-controlled.**
   - If any segment originates from external input, validate the final write target with `validate_write_path(...)`.

4. **Treat path traversal protection as mandatory behavior, not best-effort behavior.**
   - The TRD specifies that `validate_write_path(...)` returns a safe default on traversal.
   - Code must use that returned value rather than attempting to recover the original path manually.

5. **Do not implement ad hoc path sanitizers in place of `validate_write_path(...)`.**
   - Use the shared function from `path_security`.
   - Do not replace it with manual checks like string prefix matching or `".."` filtering.

---

## Import and Module Organisation

1. **Import `validate_write_path` directly from `path_security` wherever a write path is validated.**
   - Required import form:
   ```python
   from path_security import validate_write_path
   ```

2. **Organize modules so subsystem code lives under its canonical subsystem package.**
   - Examples:
     - CAL code under `src/cal/`
     - TrustFlow code under `src/trustflow/`
     - MCP policy code under `src/mcp/`

3. **Keep SDK code separate from backend runtime code.**
   - Place Forge Connector SDK code under `sdk/connector/`.
   - Do not mix SDK modules into `src/`.

4. **Keep tests structurally aligned with source packages.**
   - Imports in tests should target the corresponding `src/` module mirrored by the test path.
   - Do not create flat test directories that break source-to-test mapping.

5. **Rely on the repository `conftest.py` managed by CI for `src/` import setup.**
   - Do not add duplicate path injection helpers in individual test files unless extending the managed convention is unavoidable.

---

## Comment and Documentation Rules

1. **Document naming-sensitive conventions exactly as specified in the TRDs when they are encoded in code.**
   - For example, if a UI component sets accessibility identifiers, include the exact pattern:
     - `{module}-{component}-{role}-{context?}`

2. **When code classifies documentation-related PRs, match the documented keyword style from the TRD source.**
   - Use lowercase keyword matching against normalized PR titles where this behavior exists.
   - The TRD example uses values such as:
     - `"naming convention"`
     - `"glossary"`
     - `"changelog"`

3. **Preserve exact filenames and branch-format strings in comments and docs when referring to operational conventions.**
   - Use:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

4. **Do not describe root-required files as merely “recommended.”**
   - Documentation and code comments must refer to them as required root-level files when enforcing repository layout.

5. **Use comments to explain deviations from canonical subsystem placement only when a TRD-required file forces a special location.**
   - Example: root files such as `README.md` or workflow files.
   - Do not add comments justifying arbitrary file placement.

---

## ForgeAgent-Specific Patterns

1. **Use the exact branch naming pattern for all ForgeAgent work branches.**
   - Required format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

2. **Use zero-padded 3-digit PR numbers in branch names.**
   - Valid: `pr-001-...`, `pr-042-...`, `pr-257-...`
   - Invalid: `pr-1-...`, `pr-42-...`

3. **Keep `forge-agent` as the branch prefix for compatibility.**
   - Do not rename the prefix to `forge`, `forgeagent`, or any other variant.

4. **For Swift/macOS interactive UI code, assign `.accessibilityIdentifier()` to every interactive element.**
   - This is mandatory for buttons, fields, rows, cards, and similar controls.

5. **Construct accessibility identifiers from semantic segments, not screen coordinates or presentation text.**
   - Use stable identifiers like:
     - `settings-anthropic-key-reveal-button`
   - Do not use labels that are likely to change with copy updates.

6. **When rendering entity-backed UI collections, include the entity ID in the accessibility identifier suffix.**
   - Example:
   ```swift
   .accessibilityIdentifier("navigator-project-row-\(projectId)")
   ```

7. **Use Forge architecture subsystem names consistently in file paths, test paths, and branch `subsystem_slug` values.**
   - Example valid slugs:
     - `cal`
     - `dtl`
     - `trustflow`
     - `vtz`
     - `trustlock`
     - `mcp`
     - `rewind`

8. **Treat documentation-PR detection logic as title-keyword based when implementing legacy v5.0 behavior.**
   - Normalize the PR title to lowercase before checking keywords.
   - Compare against keyword strings in the same lowercase form.

9. **Keep legacy docs-keyword detection isolated to code paths that explicitly implement the v5.0 behavior.**
   - The TRD notes the keyword list was removed in v6.0.
   - Do not introduce this keyword classification into unrelated current logic unless the feature explicitly targets the legacy behavior.

10. **When adding write-capable ForgeAgent features, include path validation at the first boundary where an external path enters the system.**
    - Validate before file creation, overwrite, append, temp export, artifact emission, or generated output writes.