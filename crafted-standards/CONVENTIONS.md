# Code Conventions

## File and Directory Naming

1. **Name Python backend modules exactly by responsibility using `snake_case.py`.**
   - Use names aligned with the architecture context:
     - `src/consensus.py` for `ConsensusEngine` and generation-system constants.
     - `src/build_director.py` for `BuildPipeline`.
   - Do not introduce alternate names like `consensus_engine.py` or `pipeline_builder.py` for those responsibilities.

2. **Place Python implementation modules under `src/`.**
   - New backend code for the CraftedDevAgent subsystem must live in `src/` unless the file is one of the repo-root required files listed below.

3. **Keep required repository-level files at repo root with no directory prefix.**
   - The following files must be committed at the repository root:
     - `README.md`
     - `CODEOWNERS`
     - `LICENSE`
     - `.gitignore`
     - `.editorconfig`
     - `VERSION`
     - `Makefile`
     - `pyproject.toml`
   - Do not place duplicates of these files under subdirectories for primary project use.

4. **Name CI workflow files exactly as required.**
   - Ubuntu workflow file: `crafted-ci.yml`
   - macOS Swift workflow file: `crafted-ci-macos.yml`
   - Do not create renamed variants for the main workflows.

5. **Do not manually relocate or rename `conftest.py` created by CI setup.**
   - Treat `conftest.py` as an expected root-level support file when auto-committed by `ci_workflow.ensure()` for `src/` imports.

6. **Use stable, slug-style path segments for subsystem and branch-related identifiers.**
   - When a directory, branch segment, or generated slug represents a subsystem, use lowercase words separated by hyphens, for example: `crafted-dev-agent`.

7. **Use `snake_case` for Python filenames and directories that are not explicitly required to use another format.**
   - Examples:
     - `src/path_security.py`
     - `src/github_integration.py`

## Class and Function Naming

1. **Name Python classes in `PascalCase`.**
   - Examples:
     - `ConsensusEngine`
     - `BuildPipeline`

2. **Name Python functions and methods in `snake_case`.**
   - Example:
     - `validate_write_path(...)`
     - `ensure_ci_workflow(...)`

3. **Use verbs for functions that perform actions and nouns for classes that encapsulate systems or workflows.**
   - Action function examples:
     - `validate_write_path`
     - `ensure`
   - System class examples:
     - `ConsensusEngine`
     - `BuildPipeline`

4. **Preserve TRD-defined API names exactly when referenced by subsystem code.**
   - Do not rename:
     - `validate_write_path`
     - `ConsensusEngine`
     - `BuildPipeline`

5. **Name constants in `UPPER_SNAKE_CASE`.**
   - Examples from the architecture context:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

6. **Use descriptive suffixes for UI accessibility identifiers based on role.**
   - Build identifiers using:
     - `{module}-{component}-{role}`
     - `{module}-{component}-{role}-{context}`
   - Valid examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`

## Error and Exception Patterns

1. **Validate paths before every write operation without exception.**
   - Before writing any file derived from user input, agent input, PR metadata, or generated relative paths, call:
   - `validate_write_path(user_supplied_path)`

2. **Use the validated path result for the write, never the original input path.**
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - All subsequent file writes must target `safe_path`.

3. **Apply path validation before creating, overwriting, appending, or moving files.**
   - This includes:
     - direct file writes
     - generated artifacts
     - workflow files
     - documentation files
     - temporary output promoted into the repo

4. **Assume traversal defense is handled by `validate_write_path` and do not bypass it with manual normalization alone.**
   - Do not replace required validation with only `os.path.abspath`, `Path.resolve()`, or string prefix checks.

5. **Treat the validator’s returned safe default as authoritative when traversal is detected.**
   - Do not retry the write using the original path after validation returns a different path.

## Import and Module Organisation

1. **Import `validate_write_path` directly from `path_security` in any module that performs writes.**
   - Required import form:
   ```python
   from path_security import validate_write_path
   ```

2. **Keep module imports aligned with `src/` layout.**
   - Backend imports should resolve against modules under `src/`, supported by the CI-managed `conftest.py`.

3. **Define architecture-critical classes and constants in the canonical modules from the TRD.**
   - `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` belong in `src/consensus.py`.
   - `BuildPipeline` belongs in `src/build_director.py`.

4. **Do not split canonical TRD-owned symbols into alternate modules unless the TRD is updated first.**
   - If code needs `BuildPipeline`, import it from `src/build_director.py` rather than creating a parallel pipeline module.

5. **Keep workflow-related logic aware of the canonical workflow filenames.**
   - Any module that provisions or validates CI workflows must reference:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`

## Comment and Documentation Rules

1. **Document naming conventions using the exact phrase `naming convention` when the text is intended to be discoverable as docs-related content.**
   - This aligns with the historical docs keyword matching that included `naming convention`.

2. **Use exact documentation terms when categorising docs-only changes.**
   - Prefer titles or labels containing known docs keywords such as:
     - `naming convention`
     - `glossary`
     - `changelog`
   - Use these exact lower-case phrases when you want tooling or reviewers to classify a change as documentation-oriented.

3. **Do not use comments as a substitute for required enforcement code.**
   - A comment like “validate path here” is insufficient; the actual `validate_write_path(...)` call must be present before the write.

4. **When documenting accessibility identifiers, show examples in the exact TRD format.**
   - Use examples like:
     - `auth-passcode-button`
     - `settings-anthropic-key-test-button`
     - `stream-gate-yes-button-{gateId}`

5. **Keep inline comments concrete and tied to subsystem rules.**
   - Good:
     - `# Validate before any write to prevent traversal fallback bypass`
   - Bad:
     - `# safety stuff`

## CraftedDevAgent-Specific Patterns

1. **Use the mandatory branch naming format exactly as specified.**
   - Required format:
   ```text
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```
   - Keep the `forge-agent` prefix exactly for compatibility.
   - Do not substitute `crafted-agent`, `crafted-dev-agent`, or other prefixes.

2. **Populate branch naming placeholders with the required formatting.**
   - `{engineer_id}`: stable engineer identifier.
   - `{subsystem_slug}`: lowercase hyphenated subsystem slug.
   - `{N:03d}`: zero-padded PR number to 3 digits.
   - `{title_slug}`: lowercase hyphenated title slug.

3. **Use `crafted-dev-agent` as the subsystem slug format when referring to this subsystem in branch names or slug fields.**
   - Example:
   ```text
   forge-agent/build/alex/crafted-dev-agent/pr-042-add-path-validation
   ```

4. **Assign `.accessibilityIdentifier()` to all interactive macOS Swift UI elements.**
   - No interactive control should be added without an accessibility identifier.

5. **Construct every accessibility identifier using the TRD pattern.**
   - Required pattern:
   ```text
   {module}-{component}-{role}-{context?}
   ```

6. **Use approved accessibility identifier role names consistently.**
   - Preferred role suffixes from TRD examples include:
     - `button`
     - `field`
     - `row`
     - `card`

7. **Append dynamic context values at the end of accessibility identifiers.**
   - Examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-stop-button-{gateId}`

8. **Keep module and component segments in accessibility identifiers lowercase and hyphen-separated.**
   - Do not use camelCase or underscores in identifier segments.

9. **When generating or modifying CI support, preserve the expected auto-managed behavior of `ci_workflow.ensure()`.**
   - Do not add code that conflicts with `conftest.py` auto-commit behavior for `src/` imports.

10. **When code writes workflow or root-level files, combine file-placement rules with write-path validation.**
    - Example sequence:
    ```python
    from path_security import validate_write_path

    workflow_path = validate_write_path(".github/workflows/crafted-ci.yml")
    ```
    - Apply the same pattern for repo-root required files such as `README.md` or `pyproject.toml`.

11. **When implementing docs PR classification or related heuristics, use the exact keyword set terminology from the TRD source where applicable.**
    - Preserve doc classification phrases such as:
      - `naming convention`
      - `glossary`
      - `changelog`

12. **Do not infer that a file is validly placed only from its basename unless it is one of the explicitly allowed repo-root files.**
    - Basename-only root validation applies to the known set:
      - `README.md`
      - `CODEOWNERS`
      - `LICENSE`
      - `.gitignore`
      - `.editorconfig`
      - `VERSION`
      - `Makefile`
      - `pyproject.toml`