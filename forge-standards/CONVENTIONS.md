# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place Python backend modules under `src/` using lowercase snake_case filenames only.**
   - Required examples:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`
   - Do not use hyphens, spaces, or PascalCase in Python filenames.

2. **Use the mandated Forge subsystem directories exactly as defined; do not invent alternate top-level names.**
   - Required directory names:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`

3. **Mirror `src/` structure exactly under `tests/`.**
   - If implementation file is `src/trustflow/audit_stream.py`, the test file must be under `tests/trustflow/`.
   - If implementation file is `src/build_director.py`, place tests in `tests/build_director/` or `tests/` only if the project already uses flat top-level test files for root modules. Prefer mirrored directories for new code.

4. **Name test files `test_<module>.py`.**
   - Examples:
     - `tests/trustflow/test_audit_stream.py`
     - `tests/test_build_director.py`

5. **Keep CI workflow filenames fixed.**
   - Ubuntu workflow file must be named `crafted-ci.yml`.
   - macOS Swift workflow file must be named `crafted-ci-macos.yml`.
   - Do not introduce renamed variants such as `ci.yml`, `macos.yml`, or `crafted_ci.yml`.

6. **Do not manually remove or rename `conftest.py` when it is created by `ci_workflow.ensure()`.**
   - Treat that file as managed infrastructure required for `src/` imports in CI.

7. **Use branch names in the exact mandatory format below.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e17/trustflow/pr-042-add-audit-heartbeat`
   - Keep the literal prefix `forge-agent/build/` unchanged for compatibility.

8. **Use subsystem slugs in paths and branch names that match the actual source directory name.**
   - Example:
     - code in `src/trustlock/` must use `trustlock`, not `trust-lock` or `crypto-identity`.

## Class and Function Naming

1. **Name Python classes in PascalCase and align the class name with the file’s responsibility.**
   - Required examples:
     - `ConsensusEngine` in `src/consensus.py`
     - `BuildPipeline` in `src/build_director.py`
     - `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`
     - `BuildLedger` in `src/build_ledger.py`
     - `DocumentStore` in `src/document_store.py`

2. **Name Python functions and methods in snake_case.**
   - Required examples:
     - `chunk()`
     - `embed()`
     - `retrieve()`
     - `claim()`
     - `release()`

3. **Use noun-based class names for services and engines; use verb-based function names for actions.**
   - Good:
     - `BuildLedger.claim()`
     - `DocumentStore.retrieve()`
   - Avoid:
     - `DoBuild`
     - `HandleDocs`

4. **Name module-level constants in UPPER_SNAKE_CASE only.**
   - Required examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

5. **Use explicit suffixes for GitHub-facing classes.**
   - Classes that wrap GitHub operations must end in `Tool`, `Receiver`, `Client`, or another concrete integration suffix already used in the module.
   - Prefer existing names over introducing synonyms.

6. **For Swift/macOS interactive UI elements, set an accessibility identifier on every interactive control.**
   - Apply via `.accessibilityIdentifier()`.

7. **Format every accessibility identifier as: `{module}-{component}-{role}-{context?}`.**
   - Required pattern examples:
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

8. **Use lowercase kebab-case segments in accessibility identifiers.**
   - Do not use spaces, underscores, or camelCase.
   - Dynamic identifiers must append the dynamic value at the end.

9. **Use stable domain IDs in dynamic accessibility identifiers.**
   - Prefer `projectId`, `gateId`, or persisted identifiers.
   - Do not use array indexes or transient ordering values.

## Error and Exception Patterns

1. **Validate paths before any filesystem write when a path can be influenced by user, agent, webhook, PR, or external input.**
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Call `validate_write_path(...)` immediately before opening, creating, overwriting, moving, or deleting files.

2. **Use the validated path returned by `validate_write_path()` for the write operation.**
   - Do not validate and then continue using the original untrusted path variable.

3. **Treat path validation as mandatory for generated files, checked-out artifacts, workflow files, patches, and agent-authored outputs.**
   - This includes writes performed by CraftedDevAgent on behalf of a user or PR.

4. **Raise specific exceptions instead of broad `Exception` when signaling domain failures.**
   - Use built-in specific exceptions where sufficient.
   - Introduce a subsystem-specific exception class only when callers need to distinguish the failure type programmatically.

5. **Do not suppress filesystem, import, network, or CI generation errors with bare `except:`.**
   - Catch only expected exception types.
   - Re-raise after adding context if the caller cannot recover.

6. **When adding context to an exception, preserve the original exception with `raise ... from exc`.**
   - Required pattern:
   ```python
   try:
       ...
   except OSError as exc:
       raise RuntimeError(f"failed to write workflow: {safe_path}") from exc
   ```

7. **Include the subsystem or artifact name in error messages.**
   - Good:
     - `failed to write trustflow audit stream snapshot`
     - `crafted-ci.yml generation failed`
   - Avoid:
     - `write failed`
     - `something went wrong`

8. **Do not classify PRs using the removed v5.0 docs keyword list.**
   - Do not add or restore `_docs_keywords`.
   - Do not implement `_is_docs_pr` using title keyword matching from the removed list.

## Import and Module Organisation

1. **Group imports in this exact order: standard library, third-party, local project imports.**
   - Separate each group with one blank line.

2. **Use absolute imports from `src`-rooted modules; do not use relative imports between backend modules unless the package already requires them.**
   - Prefer:
   ```python
   from path_security import validate_write_path
   from build_ledger import BuildLedger
   ```
   - Avoid:
   ```python
   from .build_ledger import BuildLedger
   ```

3. **Import only the symbols used in the file.**
   - Remove unused imports before commit.
   - Do not import whole modules just to access one constant unless doing so prevents circular imports.

4. **Keep one primary responsibility per module.**
   - Examples:
     - `src/build_director.py` owns build pipeline orchestration, confidence gate, and PR-type routing.
     - `src/document_store.py` owns chunking, embedding, and retrieval behavior.
   - Do not place unrelated GitHub webhook parsing into `document_store.py`.

5. **Keep CI workflow generation logic in `src/ci_workflow.py`.**
   - Generate and manage `crafted-ci.yml`, `crafted-ci-macos.yml`, and any required CI support files from there.
   - Do not duplicate workflow emission logic across other modules.

6. **Keep GitHub integration logic in `src/github_tools.py`.**
   - Webhook receiving, GitHub API wrappers, and related request handling belong there unless a new dedicated module is necessary for scale.

7. **Keep orchestration logic in `src/build_director.py`, not in CLI wrappers or webhook handlers.**
   - CLI and webhook entrypoints may parse inputs and call orchestration services, but they must not embed pipeline decision trees.

## Comment and Documentation Rules

1. **Write comments only for non-obvious constraints, invariants, compatibility requirements, or security-sensitive behavior.**
   - Good comment targets:
     - why `forge-agent` branch prefix must remain unchanged
     - why `conftest.py` is auto-managed
     - why path validation must precede writes
   - Do not comment code that is already self-evident.

2. **When documenting a compatibility constraint, name the exact artifact or integration affected.**
   - Good:
     - `Keep forge-agent prefix for downstream branch parser compatibility.`
   - Avoid:
     - `Needed for compatibility.`

3. **Document any file or function that writes to disk with its path validation expectation if the requirement is not obvious from the call site.**
   - Example:
     - docstring states that all destination paths must pass through `validate_write_path()`.

4. **Use docstrings to describe externally callable classes and functions; keep internal helper docstrings optional unless behavior is subtle.**
   - Public entrypoints in orchestration, GitHub, CI, and storage modules must have docstrings.

5. **When referencing removed behavior from older TRDs, mark it as removed and do not present it as active logic.**
   - Example:
     - `Docs-keyword PR detection was removed in v6.0; do not reintroduce title-keyword classification.`

6. **Do not store policy or naming rules only in comments when the code can enforce them.**
   - If a branch name, accessibility identifier, or path rule is required, implement validation or construction helpers instead of relying solely on prose.

## CraftedDevAgent-Specific Patterns

1. **Before CraftedDevAgent writes any file derived from user or PR input, validate the destination path with `validate_write_path()`.**
   - This applies to generated source files, workflow files, patch outputs, temp artifacts promoted into the repo, and documentation updates.

2. **Construct branch names with a dedicated formatter that emits the exact required pattern.**
   - Required format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Zero-pad PR number to three digits.
   - Sanitize `title_slug` into lowercase kebab-case.

3. **Preserve the literal `forge-agent` branch prefix in all agent-created branches.**
   - Do not rename it to `crafted-agent`, `forge`, or any other variant.

4. **Use subsystem-aware routing based on actual Forge directory slugs.**
   - CraftedDevAgent outputs for `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, `rewind`, and `connector` must target their matching directories and branch `subsystem_slug`.

5. **When ensuring CI support, call the central workflow manager instead of writing workflow files ad hoc.**
   - `ci_workflow.ensure()` is the canonical entrypoint.
   - Rely on it to manage `conftest.py` for `src/` imports.

6. **Do not reintroduce PR classification logic based on the removed v5.0 docs keyword list.**
   - Do not add `_docs_keywords`.
   - Do not infer docs-only PRs from title substrings like “naming convention”, “glossary”, or “changelog”.

7. **For macOS Swift work generated or modified by CraftedDevAgent, attach `.accessibilityIdentifier()` to every interactive control in the same change.**
   - A new button, field, toggle, row action, or interactive card is incomplete until it has an identifier.

8. **Generate accessibility identifiers using the canonical pattern, not ad hoc strings.**
   - Pattern:
     - `{module}-{component}-{role}-{context?}`
   - Prefer helper builders for repeated dynamic forms such as project rows and gate actions.

9. **Use stable IDs when CraftedDevAgent generates list-based Swift UI.**
   - Example:
     - `navigator-project-row-{projectId}`
   - Do not generate identifiers from loop indexes.

10. **When updating CI or build orchestration code, keep platform-specific workflow separation intact.**
    - Ubuntu logic belongs to `crafted-ci.yml`.
    - macOS Swift logic belongs to `crafted-ci-macos.yml`.
    - Do not merge both into a single workflow file unless the TRD explicitly changes this rule.