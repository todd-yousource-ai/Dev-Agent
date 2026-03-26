# Code Conventions

## File and Directory Naming

1. **Place all Python application modules under `src/`.**
   - Use `src/<module_name>.py` for top-level backend modules.
   - Follow the established pattern from the TRD:
     - `src/consensus.py` defines `ConsensusEngine`, `GENERATION_SYSTEM`, and `SWIFT_GENERATION_SYSTEM`.
     - `src/build_director.py` defines `BuildPipeline`.

2. **Use lowercase snake_case for Python filenames.**
   - Valid: `build_director.py`, `path_security.py`
   - Invalid: `BuildDirector.py`, `build-director.py`

3. **Commit required repository-root files with no directory prefix.**
   - These basenames must exist at repo root when present:
     - `README.md`
     - `CODEOWNERS`
     - `LICENSE`
     - `.gitignore`
     - `.editorconfig`
     - `VERSION`
     - `Makefile`
     - `pyproject.toml`
   - Do not place these files under `docs/`, `config/`, or any subdirectory.

4. **Name CI workflow files exactly as follows.**
   - Ubuntu workflow: `crafted-ci.yml`
   - macOS Swift workflow: `crafted-ci-macos.yml`
   - Do not introduce alternate names for these two workflows.

5. **Keep `conftest.py` at repository scope when used for test import setup.**
   - `conftest.py` is auto-committed by `ci_workflow.ensure()` for `src/` imports.
   - Do not rename or relocate this file if CI depends on it.

6. **Use subsystem-oriented slugs in branch names and keep the required compatibility prefix.**
   - Branch format is mandatory:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e123/craftedapp/pr-007-auth-shell`

7. **Use lowercase kebab-case for non-Python slugs embedded in branch names, identifiers, and titles.**
   - Valid: `craftedapp`, `auth-shell`, `settings-panel`
   - Invalid: `CraftedApp`, `auth_shell`

## Class and Function Naming

1. **Name Python classes in PascalCase.**
   - Valid: `ConsensusEngine`, `BuildPipeline`
   - Invalid: `consensus_engine`, `build_pipeline`

2. **Name Python functions and methods in snake_case.**
   - Valid: `validate_write_path()`, `ensure_workflow()`
   - Invalid: `validateWritePath()`, `EnsureWorkflow()`

3. **Name Python constants in UPPER_SNAKE_CASE.**
   - Valid: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - Invalid: `generationSystem`, `SwiftGenerationSystem`

4. **Use explicit noun names for classes that represent engines, pipelines, or coordinators.**
   - Prefer names ending in concrete roles already used by the subsystem:
     - `Engine`
     - `Pipeline`
     - `Director`
   - Example: `ConsensusEngine`, `BuildPipeline`

5. **Match module names to their primary exported type or responsibility.**
   - If a file defines `BuildPipeline`, name the file `build_director.py` only when the module’s responsibility is build orchestration as established by the TRD.
   - Do not create unrelated filenames for the same responsibility.

## Error and Exception Patterns

1. **Validate every user-supplied write path before any filesystem write.**
   - Always call:
     ```python
     from path_security import validate_write_path
     safe_path = validate_write_path(user_supplied_path)
     ```
   - Use `safe_path` for the write operation.
   - Never write directly to a raw user-provided path.

2. **Apply path validation to every write operation, not only file creation.**
   - Validate before:
     - creating files
     - overwriting files
     - appending to files
     - generating workflow files
     - writing docs or config files

3. **Treat path validation as mandatory even when the caller appears trusted.**
   - If the path originated outside the current function, validate it before writing.

4. **Rely on `validate_write_path()` to normalize traversal attempts to a safe default.**
   - Do not add ad hoc traversal filtering in place of the shared validator.
   - Do not bypass the validator with manual string checks like `".." not in path"`.

## Import and Module Organisation

1. **Import `validate_write_path` directly from `path_security` in any module that writes files.**
   - Required import:
     ```python
     from path_security import validate_write_path
     ```

2. **Use `src/` as the import base for project modules in tests and CI.**
   - Keep imports compatible with the `conftest.py` setup that enables `src/` imports.
   - Do not restructure imports in a way that requires replacing this mechanism unless the CI setup is updated in the same change.

3. **Keep module responsibilities narrow and aligned with the TRD-defined architecture.**
   - `src/consensus.py` is reserved for consensus/generation-system concerns.
   - `src/build_director.py` is reserved for build pipeline concerns.
   - Do not mix unrelated responsibilities into these modules.

4. **Prefer direct imports of named symbols over ambiguous wildcard imports.**
   - Valid:
     ```python
     from path_security import validate_write_path
     ```
   - Invalid:
     ```python
     from path_security import *
     ```

## Comment and Documentation Rules

1. **Use the exact phrase `naming convention` in documentation that defines or explains naming rules.**
   - This phrase is part of the documented keyword set used by PR classification logic.
   - Include it verbatim when adding naming-rule documentation.

2. **Use the exact terms `glossary` and `changelog` when authoring those document types.**
   - Do not replace them with near-synonyms if the document is intended to be detected as such.

3. **When documenting accessibility identifiers, include the full structural pattern, not only examples.**
   - Required pattern:
     - `{module}-{component}-{role}-{context?}`

4. **Document interactive SwiftUI elements with their concrete `accessibilityIdentifier` values in code-adjacent comments or implementation notes when introducing new UI patterns.**
   - Include examples that match shipped identifiers, such as:
     - `auth-touchid-button`
     - `settings-anthropic-key-test-button`

5. **Do not use comments as a substitute for required path-validation code.**
   - A comment stating a path is safe is insufficient; the validator call must exist in code.

## CraftedApp-Specific Patterns

1. **Set `.accessibilityIdentifier()` on all interactive SwiftUI elements.**
   - This is mandatory for buttons, fields, rows, cards, and similar controls.
   - Do not leave interactive elements unnamed.

2. **Format every accessibility identifier as:**
   - `{module}-{component}-{role}-{context?}`
   - The optional `context` segment is required when needed to uniquely identify repeated elements.

3. **Use lowercase kebab-case for every segment in an accessibility identifier.**
   - Valid: `settings-anthropic-key-field`
   - Invalid: `settingsAnthropicKeyField`, `settings_anthropic_key_field`

4. **Use stable domain terms for identifier segments.**
   - Reuse established module/component names from the subsystem instead of inventing synonyms.
   - Preferred examples from the TRD:
     - `auth`
     - `settings`
     - `navigator`
     - `stream`
     - `touchid`
     - `passcode`
     - `project`
     - `gate`

5. **Use role names that describe the UI control type or action.**
   - Valid roles from existing patterns:
     - `button`
     - `field`
     - `row`
     - `card`

6. **Append a context segment for data-driven or repeated UI elements.**
   - Required examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-yes-button-{gateId}`
     - `stream-gate-skip-button-{gateId}`
     - `stream-gate-stop-button-{gateId}`

7. **Use the real entity identifier as the final accessibility identifier segment for repeated elements.**
   - For project-backed rows, append `{projectId}`.
   - For gate-backed controls, append `{gateId}`.
   - Do not substitute array indexes when a stable domain ID exists.

8. **Keep related controls grouped under the same module/component prefix.**
   - Example for Anthropic key settings:
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`
     - `settings-anthropic-key-reveal-button`

9. **Preserve established identifier prefixes when extending existing UI flows.**
   - Add new auth controls under `auth-*`.
   - Add new settings controls under `settings-*`.
   - Add new navigator controls under `navigator-*`.
   - Add new stream controls under `stream-*`.

10. **When creating PRs or branches for CraftedApp work, use the subsystem slug consistently as `craftedapp` unless a different slug is already defined by the owning workflow.**
    - Example:
      - `forge-agent/build/e123/craftedapp/pr-012-settings-key-ux`