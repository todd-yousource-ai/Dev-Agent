# Code Conventions

## File and Directory Naming

1. **Place all Python implementation modules for CraftedDevAgent under `src/`.**
   - Use flat, descriptive module names that match the primary responsibility.
   - Follow the established backend pattern from the TRDs:
     - `src/consensus.py`
     - `src/build_director.py`

2. **Name Python files in `snake_case.py` only.**
   - Allowed: `build_director.py`, `path_security.py`
   - Not allowed: `BuildDirector.py`, `build-director.py`

3. **Keep repository-root files at the repository root with no directory prefix when they are in the required root-file set.**
   - The following filenames must be committed at repo root:
     - `README.md`
     - `CODEOWNERS`
     - `LICENSE`
     - `.gitignore`
     - `.editorconfig`
     - `VERSION`
     - `Makefile`
     - `pyproject.toml`

4. **Do not relocate required root files into subdirectories.**
   - Invalid: `docs/README.md` as the canonical repo README
   - Invalid: `config/pyproject.toml`
   - If supplemental copies exist, the canonical required file must still exist at root.

5. **Use the exact CI workflow filenames defined by the TRDs.**
   - Ubuntu workflow: `crafted-ci.yml`
   - macOS Swift workflow: `crafted-ci-macos.yml`

6. **When generating or ensuring CI support files, preserve `conftest.py` as an auto-committed file created by `ci_workflow.ensure()` for `src/` imports.**
   - Do not rename it.
   - Do not move it outside the location expected by the CI setup.

7. **Name branch refs using the exact mandatory compatibility format.**
   - Format:
     `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     `forge-agent/build/e123/crafted-dev-agent/pr-014-path-validation`

8. **Use lowercase kebab-case for `subsystem_slug` and `title_slug` inside branch names.**
   - Allowed: `crafted-dev-agent`, `path-validation`
   - Not allowed: `CraftedDevAgent`, `path_validation`

9. **Zero-pad PR numbers in branch names to exactly three digits.**
   - Allowed: `pr-001-fix-imports`
   - Not allowed: `pr-1-fix-imports`, `pr-0001-fix-imports`

10. **For Swift accessibility identifiers, use the exact naming structure `{module}-{component}-{role}-{context?}`.**
    - Set every interactive UI element with `.accessibilityIdentifier(...)`.
    - Examples:
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

11. **When an accessibility identifier includes a runtime identifier, append it as the final hyphen-separated segment.**
    - Use: `navigator-project-row-{projectId}`
    - Do not use: `navigator-{projectId}-project-row`

---

## Class and Function Naming

1. **Name Python classes in `PascalCase`.**
   - Use names that reflect the module responsibility.
   - TRD-aligned examples:
     - `ConsensusEngine`
     - `BuildPipeline`

2. **Name Python functions and methods in `snake_case`.**
   - Examples:
     - `validate_write_path`
     - `ensure()`
     - `is_docs_pr()`

3. **Name module-level constants in `UPPER_SNAKE_CASE`.**
   - TRD-aligned examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

4. **If a file has one primary class, name the file after the responsibility, not the class suffix.**
   - Prefer `build_director.py` containing `BuildPipeline`
   - Prefer `consensus.py` containing `ConsensusEngine`

5. **Use boolean helper names that read as predicates.**
   - Preferred patterns:
     - `is_docs_pr`
     - `has_root_file`
     - `should_commit_conftest`

6. **Use `ensure_*` names only for functions that create or reconcile required project state.**
   - Allowed: `ensure_ci_workflow()`, `ensure_conftest()`
   - Do not use `ensure_*` for read-only validation.

7. **Use `validate_*` names only for functions that check input or normalize unsafe values into safe ones.**
   - Required pattern for write-path handling:
     - `validate_write_path(user_supplied_path)`

8. **Name slugs and identifiers explicitly with `_slug`, `_id`, or `_identifier` suffixes.**
   - Examples:
     - `subsystem_slug`
     - `engineer_id`
     - `ax_identifier`

9. **When representing doc-PR keyword sets, use a plural or collection-oriented constant name.**
   - Preferred:
     - `DOCS_PR_KEYWORDS`
   - Legacy TRD reference:
     - `_docs_keywords`

---

## Error and Exception Patterns

1. **Validate paths before any write operation without exception.**
   - Every file write, overwrite, move, or generated-output path derived from external or user-controlled input must pass through `validate_write_path(...)` first.

2. **Use the exact path-validation pattern from the TRD before writing.**
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

3. **Write only to the validated path returned by `validate_write_path(...)`.**
   - Do not continue using the original untrusted path variable after validation.

4. **Treat all user-supplied, agent-generated, PR-derived, and branch-derived paths as untrusted inputs.**
   - This includes filenames assembled from PR titles, branch names, issue titles, or subsystem slugs.

5. **Do not implement ad hoc traversal checks inline when `validate_write_path(...)` is available.**
   - Do not duplicate logic with manual `..` checks.
   - Centralize write-path safety through `path_security.validate_write_path`.

6. **When a validation API returns a safe default on traversal, continue with the returned safe path rather than reconstructing the path manually.**
   - The TRD-defined contract for `validate_write_path(...)` is that it returns a safe default on traversal.

7. **Raise exceptions for invariant violations, not for normal classification logic.**
   - Example: use boolean logic for docs-PR detection.
   - Do not use exceptions to signal “this is a docs PR”.

8. **Keep docs-PR detection keyword-based and side-effect free.**
   - Pattern:
     ```python
     is_docs_pr = any(kw in title_lower for kw in DOCS_PR_KEYWORDS)
     ```

9. **Use basename-based validation when checking membership in the required root-file set.**
   - Validate the filename against the known root-required basenames.
   - Do not infer validity solely from directory placement checks.

---

## Import and Module Organisation

1. **Import path-validation helpers directly from `path_security`.**
   - Required import form:
     ```python
     from path_security import validate_write_path
     ```

2. **Keep module imports aligned with `src/`-based project imports.**
   - Do not introduce alternate import roots for the same module set.

3. **Rely on the CI-managed `conftest.py` for `src/` import support instead of custom per-test import hacks.**
   - Do not add duplicate import-path bootstrapping if `ci_workflow.ensure()` already manages it.

4. **Group imports by standard library, third-party, then local modules.**
   - Place `from path_security import validate_write_path` in the local-module section.

5. **Import only the symbols used by the module.**
   - If only `validate_write_path` is needed, do not import the entire `path_security` module.

6. **Keep module responsibilities narrow and reflected in the filename.**
   - `consensus.py` should host consensus-generation concerns.
   - `build_director.py` should host build-pipeline orchestration concerns.

7. **Do not split a single convention-driven responsibility across multiple ambiguously named modules.**
   - Prefer one clearly named module over multiple generic files such as `helpers.py`, `misc.py`, or `utils.py` for subsystem-critical logic.

---

## Comment and Documentation Rules

1. **Document naming formats inline where they are enforced.**
   - When code validates or constructs branch names, include the exact required format string in code comments or docstrings:
     `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

2. **Document accessibility identifier formats at the point of UI construction or helper creation.**
   - Include the exact convention:
     `{module}-{component}-{role}-{context?}`

3. **When a keyword list exists for docs-PR detection, document that it is a classification list and keep the check readable.**
   - Preferred comment style:
     - `# Keywords that classify a PR as documentation-only`

4. **Do not add comments that restate obvious syntax.**
   - Required comments must explain enforced conventions, contracts, or compatibility requirements.

5. **When preserving a legacy-compatible name or format, state the compatibility reason in the comment.**
   - Example:
     - `# Keep forge-agent prefix for compatibility with existing automation`

6. **Add docstrings to helpers that normalize unsafe inputs.**
   - `validate_*` helpers must describe:
     - what input is considered untrusted
     - what safe value is returned
     - whether normalization occurs

7. **When documenting required root files, list the exact basenames rather than describing them generically.**
   - Use the canonical set from the TRD.

8. **Keep examples in documentation aligned with TRD-approved examples.**
   - For accessibility identifiers, reuse the established examples rather than inventing alternate word order.

---

## CraftedDevAgent-Specific Patterns

1. **Before CraftedDevAgent writes any generated file, validate the destination path with `validate_write_path(...)`.**
   - This applies to code generation, workflow generation, config generation, and patch output.

2. **When CraftedDevAgent creates or updates CI workflow files, use only the approved workflow filenames.**
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

3. **When CraftedDevAgent ensures CI support, allow `ci_workflow.ensure()` to auto-commit `conftest.py` for `src/` imports.**
   - Do not replace this mechanism with manual import bootstrapping.

4. **When CraftedDevAgent emits or validates branch names, preserve the literal `forge-agent` prefix.**
   - Do not rename the prefix to match the subsystem name.
   - This is mandatory for compatibility.

5. **When CraftedDevAgent derives branch names from PR metadata, normalize only the variable segments.**
   - Keep these literal segments unchanged:
     - `forge-agent`
     - `build`
     - `pr-`
   - Normalize only:
     - `{engineer_id}`
     - `{subsystem_slug}`
     - `{title_slug}`

6. **When CraftedDevAgent determines whether a PR is documentation-only, use keyword matching against a dedicated keyword set.**
   - Seed the set with TRD-derived terms such as:
     - `naming convention`
     - `glossary`
     - `changelog`

7. **Store docs-PR keywords in a dedicated constant collection, not inline in the condition.**
   - Preferred:
     ```python
     DOCS_PR_KEYWORDS = {"naming convention", "glossary", "changelog"}
     ```

8. **Implement docs-PR classification with `any(...)` over the normalized lowercase title or equivalent normalized text.**
   - Pattern:
     ```python
     title_lower = title.lower()
     is_docs_pr = any(kw in title_lower for kw in DOCS_PR_KEYWORDS)
     ```

9. **When CraftedDevAgent generates Swift UI code, assign `.accessibilityIdentifier(...)` to every interactive element.**
   - Buttons, fields, rows, cards, and action controls must all have identifiers.

10. **When CraftedDevAgent generates Swift accessibility identifiers, build them in the exact TRD order: module, component, role, optional context.**
    - Do not reorder the segments.

11. **When CraftedDevAgent generates dynamic accessibility identifiers, place the runtime token at the end.**
    - Use:
      - `stream-gate-yes-button-{gateId}`
    - Do not use:
      - `stream-{gateId}-gate-yes-button`

12. **When CraftedDevAgent validates repository structure, check required root-file presence by basename against the known canonical set.**
    - Do not fail a file solely because a validator expected a root-directory path match instead of the required basename match.

13. **Use established canonical module/class pairings when extending the backend architecture.**
    - `src/consensus.py` → `ConsensusEngine`
    - `src/build_director.py` → `BuildPipeline`

14. **Do not introduce alternate naming schemes that conflict with TRD-established examples.**
    - If a new name overlaps an existing convention area, match the nearest TRD pattern instead of inventing a new one.