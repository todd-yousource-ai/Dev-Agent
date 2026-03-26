# Code Conventions

## File and Directory Naming

1. **Name Python backend modules exactly after their primary responsibility in `snake_case`.**
   - Use filenames like:
     - `src/consensus.py` for `ConsensusEngine`
     - `src/build_director.py` for `BuildPipeline`
   - Do not use alternate names like `consensus_engine.py` or `pipeline_builder.py` when the TRD-defined canonical filename exists.

2. **Place Python application code under `src/`.**
   - New backend modules for the CraftedDevAgent subsystem must live in `src/` unless they are repository-root exceptions defined below.

3. **Keep required repository-root files at the repo root with no directory prefix.**
   - The following files must be committed at the repository root:
     - `README.md`
     - `CODEOWNERS`
     - `LICENSE`
     - `.gitignore`
     - `.editorconfig`
     - `VERSION`
     - `Makefile`
     - `pyproject.toml`
   - Do not place these files under `docs/`, `config/`, or any other subdirectory.

4. **Name CI workflow files exactly as mandated.**
   - Ubuntu workflow file: `crafted-ci.yml`
   - macOS Swift workflow file: `crafted-ci-macos.yml`
   - Do not introduce renamed variants such as `ci.yml`, `ubuntu-ci.yml`, or `swift-macos.yml` for these canonical workflows.

5. **Preserve `conftest.py` as the import bootstrap file when ensured by CI tooling.**
   - If `ci_workflow.ensure()` creates or updates `conftest.py` for `src/` imports, do not replace it with a differently named bootstrap file.

6. **Use subsystem slugs in branch names exactly in the required branch format.**
   - Branch names must match:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/alex/crafted-dev-agent/pr-042-add-path-validation`
   - Keep the `forge-agent` prefix unchanged for compatibility.

7. **Use lowercase kebab-case for branch path segments that represent slugs.**
   - Apply this to:
     - `{subsystem_slug}`
     - `{title_slug}`
   - Do not use spaces, underscores, or camelCase in these segments.

8. **Use zero-padded three-digit PR numbers in branch names.**
   - Format PR numbers as `pr-001`, `pr-042`, `pr-120`.
   - Do not use `pr-1` or `pr-42`.

## Class and Function Naming

1. **Name Python classes in `PascalCase`.**
   - Examples derived from TRDs:
     - `ConsensusEngine`
     - `BuildPipeline`

2. **Name Python functions and methods in `snake_case`.**
   - Examples:
     - `validate_write_path`
     - `ensure()`
     - `is_docs_pr()` for logic corresponding to docs-PR detection
   - Do not use `camelCase` or `PascalCase` for functions.

3. **Name module-level constants in `UPPER_SNAKE_CASE`.**
   - Examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

4. **Use descriptive names that match the subsystem role named in the TRD.**
   - If a class implements consensus behavior, name it `ConsensusEngine`.
   - If a class coordinates the build pipeline, name it `BuildPipeline`.
   - Avoid introducing synonyms when a canonical term is already established in the TRD.

5. **Name accessibility identifiers using the exact token order below.**
   - Format:
     - `{module}-{component}-{role}-{context?}`
   - Apply this format to all interactive UI elements via `.accessibilityIdentifier()`.

6. **Use lowercase kebab-case in accessibility identifiers.**
   - Valid examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-test-button`
     - `navigator-project-row-123`
   - Do not use spaces, underscores, or camelCase inside identifiers.

7. **Append dynamic context values at the end of accessibility identifiers.**
   - Examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-yes-button-{gateId}`
   - Keep the dynamic identifier as the final token.

8. **Assign an accessibility identifier to every interactive SwiftUI element.**
   - Apply `.accessibilityIdentifier("...")` to buttons, fields, rows, and other interactive controls.
   - Do not leave interactive elements unnamed.

## Error and Exception Patterns

1. **Validate every user-supplied write path before any filesystem write.**
   - Call:
     ```python
     from path_security import validate_write_path
     safe_path = validate_write_path(user_supplied_path)
     ```
   - Use `safe_path` for the write operation.
   - Never write directly to a raw user-provided path.

2. **Perform path validation before creating, modifying, or overwriting any file.**
   - This includes:
     - file creation
     - file replacement
     - appending
     - generated artifact output
     - workflow file updates
   - Path validation is required even when the caller is expected to provide a relative path.

3. **Use the validated path returned by `validate_write_path()` even when traversal is detected.**
   - The TRD specifies that `validate_write_path()` returns a safe default on traversal.
   - Do not retry writes with the original path after validation.

4. **Treat missing path validation before a write as a correctness bug.**
   - When reviewing or modifying CraftedDevAgent code, add validation at the write call site rather than documenting it as a future fix.

## Import and Module Organisation

1. **Import `validate_write_path` from `path_security` at the module that performs writes.**
   - Use:
     ```python
     from path_security import validate_write_path
     ```
   - Do not inline alternate traversal checks where this helper is required.

2. **Keep write-path validation close to the write operation.**
   - Validate the path in the same function or immediate call path that performs the write.
   - Do not defer validation to distant callers unless the validated path object is what is explicitly passed through.

3. **Organize backend implementation around the canonical TRD modules.**
   - Consensus-related implementation belongs in `src/consensus.py`.
   - Build-pipeline coordination belongs in `src/build_director.py`.

4. **Keep test import support compatible with `src/` layout.**
   - Do not remove or bypass `conftest.py` behavior added by `ci_workflow.ensure()` when tests rely on importing from `src/`.

## Comment and Documentation Rules

1. **Document docs-PR detection logic with the TRD term `docs` and keyword matching behavior when implemented.**
   - If implementing or maintaining docs-PR classification, preserve the keyword-based approach derived from:
     ```python
     _is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...
     ```
   - Keep the keyword collection in a clearly named constant or variable associated with docs classification.

2. **Use the exact phrase `naming convention` in documentation or keyword lists where docs classification depends on TRD-derived keywords.**
   - The TRD keyword set explicitly includes `naming convention`, `glossary`, and `changelog`.
   - Do not paraphrase these specific keywords if they are used for detection.

3. **Comment path-validation code only when the reason is not obvious from the helper name.**
   - Prefer:
     ```python
     safe_path = validate_write_path(user_supplied_path)
     ```
   - Add a short comment only when needed to clarify the write source or fallback behavior.

4. **When documenting UI identifiers, show examples in the exact accessibility identifier format.**
   - Use examples like:
     - `settings-anthropic-key-field`
     - `stream-gate-stop-button-{gateId}`
   - Do not document alternate ordering schemes.

5. **Do not document root-required files as directory-based rules.**
   - When writing checks or comments for root files, refer to them by basename membership in the known set, because the TRD specifies they are validated by basename.

## CraftedDevAgent-Specific Patterns

1. **Use the mandatory branch naming format for all CraftedDevAgent work branches.**
   - Required format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - This format is compatibility-sensitive; do not change `forge-agent` to `crafted-agent` or any other prefix.

2. **When adding or updating CI workflows for this subsystem, use only the two canonical workflow filenames.**
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

3. **Preserve `src/` import compatibility in test and CI setup.**
   - If workflow or test setup calls `ci_workflow.ensure()`, allow it to manage `conftest.py`.
   - Do not add parallel ad hoc import hacks when `conftest.py` is the established mechanism.

4. **Implement filesystem-writing features with path validation as the first write-preparation step.**
   - Pattern:
     ```python
     from path_security import validate_write_path

     safe_path = validate_write_path(user_supplied_path)
     with open(safe_path, "w") as f:
         f.write(content)
     ```
   - Do not compute the final output path and write first, then validate afterward.

5. **Use canonical subsystem vocabulary from the TRDs in code artifacts.**
   - Prefer names already established in the TRDs:
     - `ConsensusEngine`
     - `BuildPipeline`
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
   - Avoid introducing alternate labels for the same role in code, comments, or filenames.

6. **Apply the accessibility identifier convention uniformly across authentication, settings, navigator, and stream-gate UI.**
   - Follow the demonstrated patterns:
     - `auth-touchid-button`
     - `auth-passcode-button`
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-reveal-button`
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-skip-button-{gateId}`

7. **Keep dynamic UI context placeholders stable and human-readable.**
   - Use semantic suffixes like `{projectId}` and `{gateId}`.
   - Do not replace them with positional or opaque suffixes such as `{id}` when a more specific TRD term exists.

8. **When implementing docs-PR heuristics, store keyword strings in a dedicated collection and compare against lowercase normalized titles.**
   - Pattern:
     ```python
     title_lower = title.lower()
     is_docs_pr = any(kw in title_lower for kw in _docs_keywords)
     ```
   - Keep keyword matching logic explicit rather than embedding repeated string checks inline.