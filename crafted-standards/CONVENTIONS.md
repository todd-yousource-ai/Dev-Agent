# Code Conventions

## File and Directory Naming

1. **Name CraftedAgent backend Python modules in `snake_case.py` under `src/`.**  
   Use lowercase filenames with underscores only. Follow the established subsystem patterns:
   - `src/consensus.py`
   - `src/build_director.py`

2. **Place importable Python application code under `src/`.**  
   Do not create parallel top-level package directories for backend runtime code.

3. **Commit required root-level repository files by basename with no directory prefix.**  
   The following files must exist at repo root when present in the subsystem:
   - `README.md`
   - `CODEOWNERS`
   - `LICENSE`
   - `.gitignore`
   - `.editorconfig`
   - `VERSION`
   - `Makefile`
   - `pyproject.toml`

4. **Keep CI workflow filenames exactly as specified.**  
   Use only:
   - `crafted-ci.yml` for Ubuntu CI
   - `crafted-ci-macos.yml` for macOS Swift CI

5. **Do not rename or relocate `conftest.py` when it is created by CI bootstrap.**  
   `conftest.py` is auto-committed by `ci_workflow.ensure()` to support `src/` imports.

6. **Use subsystem-specific slugs in branch names and keep the compatibility prefix unchanged.**  
   Branches for CraftedAgent work must use:
   ```text
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   Example:
   ```text
   forge-agent/build/e123/crafted-agent/pr-007-path-validation
   ```

## Class and Function Naming

1. **Name Python classes in `PascalCase`.**  
   Match the existing subsystem style:
   - `ConsensusEngine`
   - `BuildPipeline`

2. **Name Python functions and methods in `snake_case`.**  
   Examples:
   - `validate_write_path`
   - `ensure_workflow_files`
   - `build_release_artifacts`

3. **Use noun-based class names for orchestrators and engines.**  
   Prefer names that describe the responsibility directly:
   - `BuildPipeline`
   - `ConsensusEngine`  
   Avoid verb phrases such as `BuildsPipeline` or vague names such as `Manager`.

4. **Name constants in `UPPER_SNAKE_CASE`.**  
   Follow the established style:
   - `GENERATION_SYSTEM`
   - `SWIFT_GENERATION_SYSTEM`
   - `UI_ADDENDUM`

5. **Name Swift accessibility identifiers using the exact hyphenated schema.**  
   Every interactive element must set `.accessibilityIdentifier()` using:
   ```text
   {module}-{component}-{role}-{context?}
   ```
   Required examples to follow:
   - `auth-touchid-button`
   - `auth-passcode-button`
   - `settings-anthropic-key-field`
   - `settings-anthropic-key-test-button`
   - `settings-anthropic-key-reveal-button`
   - `navigator-project-row-{projectId}`
   - `stream-gate-card-{gateId}`
   - `stream-gate-yes-button-{gateId}`
   - `stream-gate-skip-button-{gateId}`
   - `stream-gate-stop-button-{gateId}`

6. **Use stable dynamic suffixes for identifier context values.**  
   When an accessibility identifier includes `{projectId}` or `{gateId}`, append the actual stable domain identifier exactly once at the end. Do not insert random UUIDs, array indexes, or transient state values.

## Error and Exception Patterns

1. **Validate every user-supplied write path before any filesystem write.**  
   Always call `validate_write_path` before opening, creating, overwriting, moving, or deleting a user-directed file path.
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   Use `safe_path` for the write operation, never the original input.

2. **Do not write to a path derived from user input without reassignment to the validated path.**  
   This is required even when the path appears normalized or relative.

3. **Treat path validation as mandatory for all write-like operations, not just file creation.**  
   Apply it before:
   - file writes
   - file overwrites
   - temp-file finalization
   - renames into destination paths
   - extracted artifact output
   - generated documentation output

4. **Prefer safe fallback behavior from `validate_write_path` over custom traversal handling.**  
   Do not duplicate traversal checks in local code if `validate_write_path` is available for the write path.

## Import and Module Organisation

1. **Import path validation directly from `path_security`.**  
   Use:
   ```python
   from path_security import validate_write_path
   ```
   Do not alias this import unless required to resolve a local naming conflict.

2. **Organize Python imports so `src/` modules remain directly importable in tests.**  
   Rely on the repository `conftest.py` support for `src/` imports; do not introduce ad hoc path mutation inside individual tests unless unavoidable.

3. **Keep module responsibilities aligned with established backend file roles.**  
   Use dedicated modules for primary subsystem responsibilities:
   - `src/consensus.py` for consensus/generation engine logic
   - `src/build_director.py` for build pipeline orchestration

4. **Do not split canonical subsystem responsibilities into arbitrarily named duplicate modules.**  
   If extending consensus behavior, add to `src/consensus.py` or a clearly related supporting module rather than creating overlapping files such as `src/consensus_engine_impl.py` without necessity.

## Comment and Documentation Rules

1. **Document naming-sensitive logic with the exact convention string when enforced by code.**  
   For any code that validates or generates branch names, accessibility identifiers, or required filenames, include the literal format in comments or docstrings.

2. **When implementing docs-PR detection logic from legacy behavior, use the v5.0 keyword-based pattern only if explicitly required by the calling flow.**  
   The historical pattern was:
   ```python
   _docs_keywords = {"naming convention", "glossary", "changelog", ...}
   _is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...
   ```
   Treat this as legacy behavior reference, not a default feature to recreate everywhere.

3. **Keep comments implementation-specific and tied to subsystem rules.**  
   Examples of acceptable comments:
   - why `validate_write_path` is required before a write
   - why `crafted-ci-macos.yml` must remain named exactly
   - why an accessibility identifier uses a domain ID suffix

4. **Do not add generic placeholder comments.**  
   Avoid comments such as:
   - `# handle errors`
   - `# set identifier`
   - `# do validation`  
   Replace them with the exact rule being enforced.

## CraftedAgent-Specific Patterns

1. **Use the mandatory compatibility branch prefix `forge-agent`.**  
   Do not substitute `crafted-agent`, `forge`, or any other prefix in branch generation logic.

2. **Generate branch names with zero-padded PR numbers to three digits.**  
   Format PR numbers as:
   - `pr-001`
   - `pr-042`
   - `pr-120`

3. **Slug fields in branch names must be lowercase and hyphen-separated.**  
   Apply this to:
   - `{subsystem_slug}`
   - `{title_slug}`  
   Do not use spaces, underscores, or mixed case.

4. **Assign accessibility identifiers to all interactive Swift UI elements.**  
   Buttons, text fields, toggles, selectable rows, and equivalent controls must all set `.accessibilityIdentifier()`.

5. **Use role words in accessibility identifiers that match the actual control type.**  
   Preferred role segment values include:
   - `button`
   - `field`
   - `row`
   - `card`  
   Do not label a field as `button` or a row as `card`.

6. **For repeated interactive UI elements, include domain context in the identifier.**  
   Use identifiers such as:
   - `navigator-project-row-{projectId}`
   - `stream-gate-yes-button-{gateId}`  
   Do not rely on visual order like `row-1`, `row-2`, or `button-first`.

7. **Preserve canonical CI workflow names in automation, references, and documentation.**  
   Any code that creates, checks, or updates CI files must reference:
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`  
   Never introduce alternate names such as `ci.yml` or `macos-ci.yml`.

8. **When generating or validating repository file manifests, treat required root files by basename.**  
   Validate `README.md` and the other required root files against the known basename set rather than by path strings containing a root prefix.

9. **If the subsystem creates files from agent output, validate destination paths before materialization.**  
   This includes generated source files, workflow files, docs files, and support files written from model-produced paths or filenames.

10. **Keep naming conventions literal and machine-checkable where possible.**  
    If code validates:
    - branch names
    - accessibility identifiers
    - workflow filenames
    - root-required files  
    implement the rule as an exact format or explicit allowed set, not as informal string matching.