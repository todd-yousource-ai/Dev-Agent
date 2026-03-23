# Code Conventions - Forge Platform

## File and Directory Naming

1. Place Python application code under `src/`. Do not create top-level Python packages outside `src/`.

2. Mirror subsystem names exactly as defined by the platform structure:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`
   - `tests/<subsystem>/`

3. Make test directories mirror `src/` exactly. For example:
   - `src/mcp/policy_engine.py`
   - `tests/mcp/test_policy_engine.py`

4. Name Python files in `snake_case.py`. Do not use hyphens, spaces, or PascalCase in filenames.

5. Keep established platform filenames unchanged when implementing their corresponding responsibilities:
   - `src/consensus.py` — `ConsensusEngine`, generation system constants
   - `src/build_director.py` — build orchestration, confidence gate, PR routing
   - `src/github_tools.py` — GitHub tooling and webhook handling
   - `src/build_ledger.py` — claim/release and heartbeat tracking
   - `src/document_store.py` — chunk/embed/retrieve document operations
   - `src/ci_workflow.py` — CI workflow generation and maintenance

6. Name new modules after the primary domain object or service they implement. Examples:
   - `policy_engine.py`
   - `audit_stream.py`
   - `replay_session.py`

7. Use singular filenames for modules that expose one primary concept. Use plural filenames only when the module manages collections or registries.

8. Store CI workflow definitions only in:
   - `.github/workflows/crafted-ci.yml`
   - `.github/workflows/crafted-ci-macos.yml`

9. Do not introduce alternate CI workflow filenames for the standard Forge pipelines.

10. Treat `conftest.py` as CI-managed when created by `ci_workflow.ensure()` for `src/` imports. Do not hand-edit auto-generated `conftest.py` unless the generator is updated in the same change.

11. Use lowercase directory names only.

12. For Swift/macOS UI code, name files after the primary type in PascalCase, with one primary type per file when practical.

13. Keep generated, temporary, or replay artifacts out of `src/`. Place them in dedicated runtime/output locations, not alongside source modules.

14. When adding a new subsystem, create both:
   - `src/<subsystem_slug>/`
   - `tests/<subsystem_slug>/`

15. Use `subsystem_slug` values consistently across directories, branch names, and test paths.

## Class and Function Naming

1. Name Python classes in `PascalCase`.

2. Name Python functions and methods in `snake_case`.

3. Name module-level constants in `UPPER_SNAKE_CASE`.

4. Use the exact established class names when implementing architecture-defined components:
   - `ConsensusEngine`
   - `BuildPipeline`
   - `GitHubTool`
   - `WebhookReceiver`
   - `BuildLedger`
   - `DocumentStore`

5. Name classes as nouns and services. Examples:
   - `PolicyEngine`
   - `ReplayCoordinator`
   - `AuditStreamWriter`

6. Name functions as actions. Examples:
   - `validate_write_path`
   - `claim_build`
   - `retrieve_documents`

7. Prefix boolean-returning functions with `is_`, `has_`, `can_`, or `should_`.

8. Name exception classes with an `Error` suffix. Examples:
   - `PathValidationError`
   - `LedgerConflictError`

9. Name private helpers with a single leading underscore. Do not use double-leading underscores unless Python name mangling is required.

10. Name async functions the same as sync functions; do not add `_async` suffixes.

11. Use descriptive parameter names. Prefer `project_id`, `gate_id`, `engineer_id`, `subsystem_slug`, `user_supplied_path` over abbreviated names.

12. In Swift/macOS UI code, name views and controllers in PascalCase and keep accessibility identifier string segments lowercase kebab-case.

13. Set `.accessibilityIdentifier()` on every interactive SwiftUI/AppKit control.

14. Build accessibility identifiers using this exact format:
    - `{module}-{component}-{role}-{context?}`

15. Use the approved identifier patterns from the TRD. Examples:
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

16. When interpolating IDs into accessibility identifiers, keep the static segments unchanged and append the dynamic ID at the end.

## Error and Exception Patterns

1. Validate paths before any write that uses user input, PR metadata, webhook content, agent output, or generated filenames.

2. Use `validate_write_path` exactly before write operations involving non-constant paths:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

3. Always write using the validated path object/value returned by `validate_write_path`; do not continue using the original path variable.

4. Perform path validation before:
   - file creation
   - file overwrite
   - append operations
   - archive extraction targets
   - generated workflow writes
   - test fixture writes
   - replay/export writes

5. If a path is constant and repository-local, keep it as a literal or derived constant; if any portion comes from external input, run validation.

6. Raise specific exceptions, not bare `Exception`.

7. Do not silently swallow filesystem, GitHub API, ledger, or CI generation failures.

8. Catch exceptions only when the handler adds one of the following:
   - context
   - retry behavior
   - cleanup
   - conversion to a subsystem-specific error
   - user-safe response formatting

9. When re-raising with context, preserve the original exception using `raise ... from exc`.

10. Use dedicated error types for conflict and validation conditions. Examples:
    - `ValidationError`
    - `LedgerConflictError`
    - `WorkflowGenerationError`

11. Return structured failure results only in modules that already use result objects; otherwise raise typed exceptions.

12. Include the failing resource identifier in exception messages. Examples:
    - branch name
    - project ID
    - gate ID
    - workflow filename
    - document key

13. Do not include secrets, tokens, API keys, passcodes, or full credential values in exception messages or logs.

14. For branch parsing or generation failures, include the offending branch string and the expected convention.

15. For auto-generated CI files, fail fast if required workflow names differ from:
    - `crafted-ci.yml`
    - `crafted-ci-macos.yml`

## Import and Module Organisation

1. Group Python imports in this order:
   1. standard library
   2. third-party packages
   3. local project imports

2. Separate each import group with one blank line.

3. Prefer absolute imports from `src`-visible packages/modules over relative imports.

4. Import concrete functions for security-sensitive operations directly. Example:
   ```python
   from path_security import validate_write_path
   ```

5. Do not use wildcard imports.

6. Keep one logical responsibility per module. Split modules when they combine unrelated concerns such as GitHub webhook parsing and document embedding.

7. Keep orchestration in top-level service modules and place helper logic in subsystem modules. Example:
   - orchestration in `build_director.py`
   - helper policies in `src/mcp/`
   - replay logic in `src/rewind/`

8. Do not move architecture-defined responsibilities out of their canonical modules unless the same change updates all imports and tests.

9. Put test utilities in `tests/` support modules, not in production `src/` modules.

10. Do not import from test modules into production code.

11. Keep Swift/macOS UI identifiers and view constants near the view that uses them unless they are shared across multiple screens.

12. When `ci_workflow.ensure()` manages `conftest.py`, do not add manual import hacks elsewhere to compensate for missing `src/` resolution.

13. If a module depends on docs-only PR classification, isolate that logic behind a dedicated helper instead of scattering keyword checks.

14. Treat the old docs keyword list from pipeline v5.0 as legacy behavior. Do not reintroduce `_docs_keywords` inline in unrelated modules.

## Comment and Documentation Rules

1. Write comments only when they explain intent, invariants, security requirements, or non-obvious behavior.

2. Do not add comments that restate the next line of code.

3. Add a short module docstring to modules that define top-level orchestration, security boundaries, or generated-file behavior.

4. Document every function that performs path validation, workflow generation, branch parsing, ledger claim/release, or document retrieval with a concise docstring describing inputs and side effects.

5. When a function relies on a mandatory convention, name the convention explicitly in the docstring. Examples:
   - required branch format
   - required workflow filenames
   - accessibility identifier format

6. For security-sensitive writes, include a comment or docstring note that the path must be validated before writing.

7. When preserving compatibility behavior, state the exact compatibility reason in the comment. Example:
   - `forge-agent` prefix retained for compatibility

8. Keep comments current with the implemented behavior. If code changes invalidate a comment, update or remove the comment in the same change.

9. Do not leave commented-out code in committed files.

10. In tests, use comments only to mark setup conditions, fixture intent, or edge-case rationale.

11. For generated files or auto-managed files, mark them clearly in the file header and identify the generator responsible.

12. Do not document removed v5.0 docs-keyword behavior as active logic unless the code path still exists.

## CraftedDevAgent-Specific Patterns

1. Use this exact branch naming convention for all agent-created branches:
   ```text
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

2. Keep the `forge-agent` prefix exactly as written for compatibility. Do not replace it with `crafted-agent`, `forge`, or any other variant.

3. Zero-pad PR sequence numbers to 3 digits. Examples:
   - `pr-001-fix-ledger-heartbeat`
   - `pr-042-add-macos-shell`

4. Generate `title_slug` in lowercase kebab-case.

5. Generate `subsystem_slug` in lowercase kebab-case and match the corresponding source/test directory naming where applicable.

6. Validate generated branch names against the required pattern before creating or pushing the branch.

7. When parsing an agent branch, extract and validate:
   - `engineer_id`
   - `subsystem_slug`
   - `N`
   - `title_slug`

8. Reject or normalize branch names that omit zero-padding, use uppercase characters, or change the `forge-agent/build` prefix.

9. Keep CI workflow generation pinned to these filenames only:
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

10. Use `ci_workflow.ensure()` to create or reconcile standard CI workflow files rather than writing ad hoc workflow file logic in other modules.

11. Assume `ci_workflow.ensure()` may auto-commit `conftest.py` for `src/` imports; code that checks generated changes must account for that file.

12. When determining whether a PR is docs-only, isolate legacy keyword-based logic behind a single helper if compatibility with pipeline v5.0 is required.

13. Do not scatter docs-PR keyword checks such as `"naming convention"`, `"glossary"`, or `"changelog"` across multiple modules.

14. For macOS Swift UI produced by CraftedDevAgent, every interactive element must have an accessibility identifier before the change is considered complete.

15. Use the TRD accessibility identifier convention exactly:
   ```text
   {module}-{component}-{role}-{context?}
   ```

16. Prefer identifiers that are stable across visual redesigns. Base them on domain meaning, not button label text alone.

17. For project and gate rows/actions, append the domain identifier at the end of the accessibility identifier string.

18. When agent code writes any file derived from prompts, issue payloads, or repository metadata, validate the path first and write only to the validated path.

19. In generated code examples and templates, include `validate_write_path` usage whenever a file path can be influenced externally.

20. Do not mark a CraftedDevAgent task complete if it:
   - writes to an unvalidated external path
   - creates nonstandard CI workflow filenames
   - uses a noncompliant branch name
   - omits required accessibility identifiers in interactive macOS UI