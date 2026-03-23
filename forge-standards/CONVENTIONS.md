# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place Python backend modules under `src/` only.**
   - Use flat top-level backend filenames for core orchestrators:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`

2. **Use the mandated subsystem directories exactly as defined.**
   - Allowed subsystem roots:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`

3. **Mirror `src/` structure exactly under `tests/`.**
   - If implementation file is `src/mcp/policy_engine.py`, test file must be `tests/mcp/test_policy_engine.py`.
   - Do not place tests in ad hoc folders such as `tests/unit/` or `tests/misc/` for mirrored source modules.

4. **Name Python files in `snake_case`.**
   - Valid: `build_director.py`, `document_store.py`
   - Invalid: `BuildDirector.py`, `build-director.py`

5. **Name package directories in lowercase.**
   - Valid: `src/trustflow/`, `src/cal/`
   - Invalid: `src/TrustFlow/`, `src/ConversationAbstractionLayer/`

6. **Keep CI workflow filenames fixed.**
   - Ubuntu workflow file must be named `crafted-ci.yml`.
   - macOS Swift workflow file must be named `crafted-ci-macos.yml`.
   - Do not introduce alternate names such as `ci.yml`, `macos.yml`, or `swift-ci.yml`.

7. **Do not manually add or remove `conftest.py` used for `src/` imports if it is managed by CI setup.**
   - Treat the file created by `ci_workflow.ensure()` as generated project infrastructure.
   - Only modify it when changing `ci_workflow.ensure()` behavior.

8. **Validate every user-influenced write path before writing files.**
   - Before any filesystem write, call:
     ```python
     from path_security import validate_write_path
     safe_path = validate_write_path(user_supplied_path)
     ```
   - Use `safe_path` for the write operation.
   - Never write directly to a raw user-supplied path.

9. **Apply path validation to all write operations, not only uploads.**
   - Required for:
     - generated files
     - exports
     - cache writes
     - workflow file creation
     - document snapshots
     - logs written from request parameters
     - replay artifacts

10. **Use branch names in the mandatory compatibility format.**
    - Format:
      ```text
      forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
      ```
    - Example:
      ```text
      forge-agent/build/e17/fullplatform/pr-042-ledger-heartbeat-fix
      ```

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Valid: `ConsensusEngine`, `BuildPipeline`, `GitHubTool`, `WebhookReceiver`, `BuildLedger`, `DocumentStore`
   - Invalid: `consensusEngine`, `build_pipeline`

2. **Name functions and methods in `snake_case`.**
   - Valid: `claim_work()`, `release_claim()`, `embed()`, `retrieve()`, `ensure()`
   - Invalid: `claimWork()`, `ReleaseClaim()`

3. **Name constants in `UPPER_SNAKE_CASE`.**
   - Valid: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - Invalid: `generationSystem`, `SwiftGenerationSystem`

4. **Use noun-based names for stateful service classes.**
   - Prefer `BuildLedger`, `DocumentStore`, `GitHubTool`.
   - Do not use verb phrases like `ManageBuilds` or `HandleDocuments` for core service classes.

5. **Use verb-based names for functions that perform actions.**
   - Prefer `chunk()`, `embed()`, `retrieve()`, `claim()`, `release()`, `ensure()`.
   - Do not use vague names such as `do_task()` or `process_thing()`.

6. **Use suffixes consistently for specialized roles.**
   - `*Engine` for decision/generation engines.
   - `*Store` for persistence/retrieval components.
   - `*Ledger` for claim/heartbeat/ownership tracking.
   - `*Receiver` for inbound webhook/event handlers.
   - `*Tool` for GitHub/API utility wrappers.
   - `*Workflow` only for workflow configuration/build helpers.

7. **Name boolean-returning functions as predicates when practical.**
   - Prefer `is_docs_pr()`, `has_claim()`, `should_route_macos()`.
   - Avoid ambiguous names like `docs_pr()` for booleans.

8. **When implementing docs PR detection from legacy pipeline logic, keep keyword collections private and lowercase-prefixed.**
   - Use `_docs_keywords` for the keyword set.
   - Use `title_lower` or similar normalized variables before matching.
   - Do not expose legacy keyword sets as public module constants unless required by API.

9. **Use descriptive subsystem slugs in identifiers and branch names.**
   - Valid slugs: `fullplatform`, `trustflow`, `rewind`, `mcp`
   - Avoid abbreviations unless the directory name is already standardized, such as `cal`, `dtl`, or `vtz`.

## Error and Exception Patterns

1. **Raise specific exceptions, never bare `Exception`, for expected failure modes.**
   - Use `ValueError`, `FileNotFoundError`, `PermissionError`, or a subsystem-specific custom exception.
   - Do not write:
     ```python
     raise Exception("failed")
     ```

2. **Convert path validation failures into safe writes using the validated path returned by `validate_write_path()`.**
   - Do not reimplement traversal sanitization in each module.
   - Do not concatenate fallback directories manually before validation.

3. **Include the operation and target context in exception messages.**
   - Valid: `"failed to write crafted-ci.yml to validated workflow path"`
   - Invalid: `"write failed"`

4. **Fail fast when required workflow filenames are wrong.**
   - If code is about to emit a workflow file with a nonstandard name, raise an error before writing.

5. **Raise on source/test structure mismatches in automation code.**
   - If a generator creates `src/...` without corresponding `tests/...`, either create the mirrored test path or raise with the missing expected location.

6. **Do not swallow GitHub, ledger, document store, or workflow errors silently.**
   - Catch exceptions only to add subsystem context or convert to a more specific type.
   - Re-raise after adding context.

7. **Use custom exception classes for subsystem policy violations.**
   - Examples:
     - `BranchNameViolation`
     - `WorkflowNameViolation`
     - `AccessibilityIdentifierViolation`
     - `UnsafeWritePathError`
   - Place shared exceptions in a module named for the subsystem, such as `src/fullplatform/exceptions.py` or the relevant package exception module.

8. **When handling legacy docs PR keyword logic, treat missing title text as a non-match, not as an exception.**
   - Normalize missing values to empty strings before keyword matching.

## Import and Module Organisation

1. **Group imports in this exact order:**
   1. Python standard library
   2. Third-party packages
   3. Project-local imports

2. **Separate each import group with a single blank line.**
   - Do not combine standard library and project imports in one block.

3. **Use absolute imports from `src` package roots where possible.**
   - Prefer:
     ```python
     from path_security import validate_write_path
     from mcp.policy_engine import PolicyEngine
     ```
   - Avoid deep relative imports like:
     ```python
     from ..mcp.policy_engine import PolicyEngine
     ```

4. **Import only what a module uses.**
   - Do not leave unused imports from neighboring subsystems.

5. **Keep one primary responsibility per module.**
   - `src/build_ledger.py` handles claim/release/heartbeat concerns.
   - `src/document_store.py` handles chunk/embed/retrieve concerns.
   - Do not merge unrelated responsibilities into orchestration files.

6. **Place generated-system prompt constants in the module that owns generation behavior.**
   - Keep `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` in `src/consensus.py` unless the owning architecture changes.

7. **Keep workflow creation logic in `src/ci_workflow.py`.**
   - Do not duplicate `crafted-ci.yml` or `crafted-ci-macos.yml` generation logic in unrelated modules.

8. **Keep GitHub integration code in `src/github_tools.py`.**
   - Do not embed webhook parsing or GitHub API clients directly inside orchestration modules unless they are thin wrappers over `github_tools`.

9. **Expose only stable module-level APIs.**
   - Prefix internal helpers with `_` when they are not intended for import by other modules.

## Comment and Documentation Rules

1. **Write comments only when they convey non-obvious intent, constraints, or required compatibility behavior.**
   - Good: explain why branch prefix must remain `forge-agent`.
   - Bad: restate code mechanics line by line.

2. **Document mandatory compatibility constraints inline at the point of enforcement.**
   - Example: when enforcing branch names, include a comment noting compatibility with existing Forge agents.

3. **Use docstrings on public classes and public functions.**
   - State:
     - what the unit does
     - required inputs
     - important side effects
     - validation or naming constraints if applicable

4. **When documenting accessibility identifiers, include the exact token format.**
   - Required format:
     ```text
     {module}-{component}-{role}-{context?}
     ```

5. **Keep examples in docs and comments aligned with real identifiers used by the platform.**
   - Prefer examples such as:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`

6. **Do not document removed behavior as active behavior.**
   - If referencing the v5.0 docs PR keyword list, label it clearly as legacy or compatibility logic.
   - Do not present removed v6.0 behavior as current default policy without that label.

7. **Use changelog, glossary, and naming references consistently when implementing docs classification logic.**
   - If code checks for docs PRs using keywords, keep the keyword list centralized and documented as legacy-compatible detection.

8. **Do not leave placeholder comments such as `TODO`, `FIXME`, or `later` without an owner or trigger condition.**
   - Required format:
     ```python
     # TODO(e17): remove legacy docs keyword fallback after v6 migration lands
     ```

## FullPlatform-Specific Patterns

1. **Set `.accessibilityIdentifier()` on every interactive macOS SwiftUI element.**
   - Required for buttons, text fields, secure fields, toggles, pickers, rows with actions, and test-triggering controls.

2. **Use the exact accessibility identifier format for interactive elements.**
   - Format:
     ```text
     {module}-{component}-{role}-{context?}
     ```

3. **Keep accessibility identifier segments lowercase and hyphen-separated.**
   - Valid: `settings-anthropic-key-test-button`
   - Invalid: `Settings-AnthropicKey-TestButton`

4. **Use stable domain nouns for identifier segments.**
   - `module`: feature area such as `auth`, `settings`, `navigator`, `stream`
   - `component`: domain object such as `touchid`, `passcode`, `anthropic-key`, `project`, `gate`
   - `role`: control role such as `button`, `field`, `row`, `card`

5. **Append context as the final segment when the control is tied to a specific entity.**
   - Valid:
     - `navigator-project-row-{projectId}`
     - `stream-gate-yes-button-{gateId}`
   - Do not place IDs in the middle of the identifier.

6. **Use the exact identifier strings from the TRD when implementing those controls.**
   - Required examples:
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

7. **Validate generated or user-derived file destinations before FullPlatform writes artifacts.**
   - This includes:
     - project export bundles
     - replay outputs
     - CI workflow files
     - generated source files
     - local credential test artifacts

8. **Route CI workflow generation through `ci_workflow.ensure()`.**
   - Do not handcraft workflow files in feature code.
   - Rely on `ci_workflow.ensure()` to manage workflow presence and related `conftest.py` setup.

9. **Keep macOS-specific CI behavior in `crafted-ci-macos.yml` only.**
   - Do not place Swift/macOS-only build steps in `crafted-ci.yml`.

10. **Keep Ubuntu/general backend CI behavior in `crafted-ci.yml` only.**
    - Do not duplicate generic Python backend checks into the macOS workflow unless they are required there as well.

11. **When implementing PR classification for FullPlatform automation, preserve legacy docs PR keyword matching only as compatibility behavior.**
    - Store the keyword set in `_docs_keywords`.
    - Match against normalized lowercase title text.
    - Keep the implementation isolated so it can be removed without affecting non-docs routing.

12. **Keep orchestration boundaries explicit in FullPlatform.**
    - `consensus.py`: generation systems and consensus engine behavior
    - `build_director.py`: pipeline orchestration, confidence gates, PR-type routing
    - `github_tools.py`: GitHub operations and webhook handling
    - `build_ledger.py`: claim/release/heartbeat ownership tracking
    - `document_store.py`: chunking, embedding, retrieval
    - `ci_workflow.py`: CI workflow and related bootstrap files

13. **Do not move subsystem responsibilities across these boundary files without renaming and updating all mirrored tests.**
    - If responsibility changes, update both source filenames and `tests/` mirror structure in the same change.

14. **When generating code or config from PR metadata, sanitize title-derived slugs before using them in branch names or filenames.**
    - Apply branch naming rules strictly.
    - Validate any resulting write path before persisting artifacts.