# Code Conventions

## File and Directory Naming

1. **Use `snake_case` for all Python file and directory names.**
   - Required for backend modules under `src/`.
   - Example: `src/build_director.py`, `src/consensus.py`.

2. **Name Python modules after their primary responsibility, not after generic helpers.**
   - Use role-based names such as `build_director.py` for `BuildPipeline` and `consensus.py` for `ConsensusEngine`.
   - Do not create vague module names like `utils.py`, `helpers.py`, or `common.py` in this subsystem.

3. **Place importable Python source under `src/`.**
   - New CraftedDevAgent Python modules must live in `src/` unless the file is one of the repo-root exceptions listed below.

4. **Keep these files at repository root with no directory prefix when present.**
   - `README.md`
   - `CODEOWNERS`
   - `LICENSE`
   - `.gitignore`
   - `.editorconfig`
   - `VERSION`
   - `Makefile`
   - `pyproject.toml`

5. **Do not relocate root-required files into subdirectories.**
   - If code generates, updates, or validates any of the files in Rule 4, it must target the basename at repo root.

6. **Use the mandated CI workflow filenames exactly.**
   - Ubuntu workflow: `crafted-ci.yml`
   - macOS Swift workflow: `crafted-ci-macos.yml`

7. **Treat `conftest.py` as a repository-level CI support file when created by workflow setup.**
   - Do not manually rename the file created by `ci_workflow.ensure()`.
   - Preserve its role for enabling `src/` imports in tests.

8. **Use branch names in this exact format.**
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example: `forge-agent/build/e17/crafted-dev-agent/pr-042-add-path-validation`

9. **Keep the literal prefix `forge-agent/build/` unchanged.**
   - Do not substitute `crafted-agent`, `crafteddevagent`, or any other prefix.

10. **Use lowercase, hyphen-separated slugs for `{subsystem_slug}` and `{title_slug}` in branch names.**
    - Example: `crafted-dev-agent`, `add-ci-validation`.

11. **Zero-pad pull request numbers to 3 digits in branch names.**
    - Example: `pr-007-fix-import-order`, not `pr-7-fix-import-order`.

12. **Use macOS accessibility identifiers in this exact shape for interactive UI elements.**
    - Format: `{module}-{component}-{role}-{context?}`
    - Apply with `.accessibilityIdentifier(...)`.

13. **Use lowercase, hyphen-separated accessibility identifier segments.**
    - Examples:
      - `auth-touchid-button`
      - `settings-anthropic-key-field`
      - `navigator-project-row-{projectId}`

14. **When an accessibility identifier references a runtime entity, append the entity identifier as the trailing segment.**
    - Examples:
      - `navigator-project-row-{projectId}`
      - `stream-gate-yes-button-{gateId}`

---

## Class and Function Naming

1. **Use `PascalCase` for classes.**
   - Examples: `ConsensusEngine`, `BuildPipeline`.

2. **Use `snake_case` for functions and methods.**
   - Example: `validate_write_path(...)`.

3. **Name classes after concrete subsystem roles.**
   - Preferred patterns: `*Engine`, `*Pipeline`, `*Director`.
   - Match the module responsibility.
   - Example: `BuildPipeline` in `build_director.py`.

4. **Name functions with an imperative verb that describes the side effect or computation.**
   - Examples: `validate_write_path`, `ensure`, `is_docs_pr`.

5. **Prefix boolean-returning helper functions with `is_`, `has_`, or `should_` when the return value is a predicate.**
   - Example: `is_docs_pr`.

6. **Name constants in `UPPER_SNAKE_CASE`.**
   - Examples: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

7. **Use descriptive field names for external service settings in UI identifiers and related code.**
   - Example naming family:
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`
     - `settings-anthropic-key-reveal-button`

8. **Do not abbreviate core subsystem concepts in public class or function names.**
   - Use `consensus`, `build`, `pipeline`, `validate`, `workflow`.
   - Avoid opaque names unless they are established product terms.

---

## Error and Exception Patterns

1. **Validate paths before every write operation with `validate_write_path`.**
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Call this before opening, writing, renaming, replacing, or generating any file from a user-influenced path.

2. **Never write directly to a user-supplied path string.**
   - Always write to the sanitized result returned by `validate_write_path(...)`.

3. **Apply path validation even when the path appears to target the repository.**
   - Do not skip validation for relative paths, generated filenames, or PR-derived filenames.

4. **Treat path validation as mandatory for workflow files, generated docs, test support files, and root files.**
   - This includes writes to:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
     - `conftest.py`
     - all root-required basenames listed above

5. **If a write path originates from branch, PR, title, or subsystem metadata, validate it before composing file output.**
   - This includes derived names influenced by `{engineer_id}`, `{subsystem_slug}`, `{title_slug}`, or PR metadata.

6. **Do not implement custom path traversal checks when writing files.**
   - Use `path_security.validate_write_path` instead of ad hoc string checks.

7. **When sanitization returns a safe fallback path, continue using the returned path rather than the original input.**
   - Do not log and then revert to the original path.

---

## Import and Module Organisation

1. **Put standard library imports first, third-party imports second, and local imports last.**
   - Keep these groups separated.

2. **Import `validate_write_path` directly from `path_security` at the call site module that performs writes.**
   - Required form:
   ```python
   from path_security import validate_write_path
   ```

3. **Keep module filenames aligned with their primary exported class or subsystem role.**
   - Examples:
     - `src/consensus.py` → `ConsensusEngine`
     - `src/build_director.py` → `BuildPipeline`

4. **Do not create a generic shared module for unrelated behavior.**
   - If logic belongs to path safety, keep it with path safety usage.
   - If logic belongs to build orchestration, keep it in the build-oriented module.

5. **Assume `src/` is the import root in tests and CI.**
   - Do not add alternate import path hacks when `conftest.py` created by `ci_workflow.ensure()` already supports `src/` imports.

6. **Do not rename or duplicate CI support imports solely to work around missing `src/` configuration.**
   - Keep the `src/` layout and rely on the ensured `conftest.py`.

---

## Comment and Documentation Rules

1. **Document naming-sensitive conventions with exact literal formats.**
   - When documenting branch names, workflow files, accessibility identifiers, or root-file requirements, include the exact required string pattern.

2. **When documenting accessibility identifiers, use the canonical format exactly.**
   - Required format:
   ```text
   {module}-{component}-{role}-{context?}
   ```

3. **When adding examples for accessibility identifiers, use lowercase hyphen-separated examples that match production style.**
   - Examples:
     - `auth-passcode-button`
     - `stream-gate-stop-button-{gateId}`

4. **Do not document outdated docs-PR keyword logic as active behavior.**
   - The `_docs_keywords` list is explicitly from v5.0 and removed in v6.0.
   - Do not introduce or rely on `_is_docs_pr` keyword matching unless a newer TRD reintroduces it.

5. **When comments mention files that must be at repo root, refer to them by basename.**
   - Do not describe them as “under config/” or another directory.

6. **Keep comments tied to enforced behavior, not aspirations.**
   - Good: “Validate all write paths with `validate_write_path` before writing.”
   - Bad: “Consider adding path safety here later.”

7. **If a module enforces a naming convention, include one canonical example in the docstring or adjacent comment.**
   - Example branch comment:
   ```text
   forge-agent/build/e17/crafted-dev-agent/pr-042-add-path-validation
   ```

---

## CraftedDevAgent-Specific Patterns

1. **Use the compatibility-preserving branch prefix exactly as specified for all automation that creates branches.**
   - Always emit:
   ```text
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

2. **Set `.accessibilityIdentifier(...)` on every interactive macOS UI element in the subsystem.**
   - Buttons, fields, rows, and similar controls must have identifiers following the required format.

3. **Use role-specific suffixes in accessibility identifiers for interactive controls.**
   - Prefer explicit roles such as:
     - `button`
     - `field`
     - `row`
     - `card`

4. **For grouped settings controls, keep the same module and component prefix across related elements.**
   - Example family:
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`
     - `settings-anthropic-key-reveal-button`

5. **For list or stream items, include the domain object identifier in the accessibility identifier.**
   - Example family:
     - `stream-gate-card-{gateId}`
     - `stream-gate-yes-button-{gateId}`
     - `stream-gate-skip-button-{gateId}`

6. **Use `crafted-ci.yml` for Ubuntu CI logic and `crafted-ci-macos.yml` for macOS Swift CI logic; do not merge them under a renamed workflow file.**

7. **When ensuring CI support for tests, allow `ci_workflow.ensure()` to create and commit `conftest.py` for `src/` imports.**
   - Do not replace this mechanism with a differently named bootstrap file.

8. **Keep backend source responsibilities aligned with the architecture context examples.**
   - `src/consensus.py` owns consensus engine concerns.
   - `src/build_director.py` owns build pipeline concerns.

9. **Do not revive removed documentation-PR detection heuristics in CraftedDevAgent code paths.**
   - Specifically, do not add title-keyword checks derived from the removed v5.0 `_docs_keywords` behavior.

10. **Whenever CraftedDevAgent writes generated files from user, PR, or automation input, perform path validation first and write only to the validated path.**
    - This rule applies to code generation, workflow generation, root file updates, and test bootstrap creation.