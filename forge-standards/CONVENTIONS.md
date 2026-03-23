# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place Python runtime code under `src/` only.**
   - Valid examples:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`

2. **Use the prescribed subsystem directories exactly as named. Do not invent alternates.**
   - Required directory names:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`

3. **Mirror `src/` structure under `tests/` exactly.**
   - If implementation file is `src/trustflow/audit_stream.py`, the test file must be under `tests/trustflow/`.
   - Example:
     - `src/mcp/policy_engine.py`
     - `tests/mcp/test_policy_engine.py`

4. **Name Python files in `snake_case`.**
   - Use lowercase letters, numbers, and underscores only.
   - Do not use hyphens or CamelCase in Python filenames.
   - Correct: `build_director.py`
   - Incorrect: `BuildDirector.py`, `build-director.py`

5. **Name test files `test_<module>.py`.**
   - Example:
     - `src/document_store.py` → `tests/test_document_store.py`
     - `src/cal/session_router.py` → `tests/cal/test_session_router.py`

6. **Use the exact CI workflow filenames below.**
   - Ubuntu workflow: `crafted-ci.yml`
   - macOS Swift workflow: `crafted-ci-macos.yml`
   - Do not create alternative names such as `ci.yml`, `macos.yml`, or `github-actions.yml`.

7. **Do not manually add or remove `conftest.py` files used for `src/` imports when they are managed by CI automation.**
   - `conftest.py` is auto-committed by `ci_workflow.ensure()`.
   - If import support is missing, update `src/ci_workflow.py`; do not create a one-off local convention.

8. **Use branch names in the mandatory compatibility format below.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/e123/fullplatform/pr-042-add-ledger-heartbeat`
   - Keep the literal prefix `forge-agent/build/`.

9. **Keep subsystem slugs short, lowercase, and filesystem-safe.**
   - Use lowercase letters, numbers, and hyphens only.
   - Example:
     - `fullplatform`
     - `trustflow`
     - `macos-shell`

10. **Use filename scope to reflect responsibility, not implementation detail.**
    - Prefer:
      - `policy_engine.py`
      - `audit_stream.py`
      - `replay_engine.py`
    - Avoid:
      - `helpers2.py`
      - `misc.py`
      - `new_code.py`

## Class and Function Naming

1. **Name classes in `PascalCase`.**
   - Examples from the platform:
     - `ConsensusEngine`
     - `BuildPipeline`
     - `GitHubTool`
     - `WebhookReceiver`
     - `BuildLedger`
     - `DocumentStore`

2. **Name functions and methods in `snake_case`.**
   - Examples:
     - `claim_build()`
     - `release_build()`
     - `validate_write_path()`
     - `retrieve_documents()`

3. **Name constants in `UPPER_SNAKE_CASE`.**
   - Examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

4. **Use nouns for service/state classes and verbs for actions.**
   - Class examples:
     - `DocumentStore`
     - `BuildLedger`
   - Function examples:
     - `embed()`
     - `chunk()`
     - `retrieve()`

5. **Name boolean-returning functions and flags with explicit predicates.**
   - Prefer:
     - `is_docs_pr`
     - `has_active_claim`
     - `should_route_to_swift`
   - Avoid:
     - `docs_pr`
     - `active`
     - `route_swift`

6. **When implementing docs-PR detection logic, use the `_docs_keywords` identifier for the v5.0 compatibility keyword set.**
   - Example:
     - `_docs_keywords = {"naming convention", "glossary", "changelog"}`
   - Use `title_lower` or similarly explicit normalized names for case-folded title comparisons.

7. **Use descriptive suffixes that encode role when multiple related symbols exist.**
   - Approved suffixes:
     - `_engine`
     - `_store`
     - `_receiver`
     - `_ledger`
     - `_workflow`
     - `_director`
   - Example:
     - `policy_engine`
     - `webhook_receiver`

8. **For macOS UI accessibility identifiers, use the exact pattern `{module}-{component}-{role}-{context?}`.**
   - Apply via `.accessibilityIdentifier(...)` on all interactive elements.
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

9. **Include stable domain IDs in dynamic accessibility identifiers.**
   - Use `{projectId}`, `{gateId}`, or equivalent stable identifiers from the model.
   - Do not use array indexes, random UUIDs generated in the view, or transient display text.

10. **Do not abbreviate public class names unless the subsystem standard already uses the abbreviation.**
    - Allowed because they are standard in this codebase:
      - `MCP`
      - `VTZ`
    - Avoid introducing new unclear abbreviations in public APIs.

## Error and Exception Patterns

1. **Validate every user-supplied write path before any filesystem write.**
   - Required pattern:
     ```python
     from path_security import validate_write_path

     safe_path = validate_write_path(user_supplied_path)
     ```
   - Apply before:
     - `open(..., "w")`
     - `Path.write_text()`
     - `Path.write_bytes()`
     - file copy/move operations
     - archive extraction targets
     - generated CI/workflow file writes

2. **Use the validated path for the write operation, never the original user input.**
   - Correct:
     ```python
     safe_path = validate_write_path(user_supplied_path)
     safe_path.write_text(content)
     ```
   - Incorrect:
     ```python
     safe_path = validate_write_path(user_supplied_path)
     Path(user_supplied_path).write_text(content)
     ```

3. **Perform path validation immediately before the write, not once earlier in an unrelated layer.**
   - Do not assume an upstream layer sanitized the path.
   - Re-validate at the write boundary.

4. **Raise specific exceptions; do not use bare `except:`.**
   - Catch concrete exception types only.
   - If translation is needed, raise a domain exception with the original exception chained:
     ```python
     except OSError as exc:
         raise LedgerWriteError("failed to persist build ledger") from exc
     ```

5. **Use domain-specific exception names ending in `Error`.**
   - Examples:
     - `LedgerWriteError`
     - `PolicyEvaluationError`
     - `WorkflowGenerationError`

6. **Include the operation and subject in exception messages.**
   - Prefer:
     - `"failed to persist build ledger heartbeat for build_id={build_id}"`
   - Avoid:
     - `"write failed"`

7. **Do not swallow failed validation or write errors in CI/workflow generation.**
   - If `crafted-ci.yml` or `crafted-ci-macos.yml` generation fails, surface the failure as an explicit exception.

8. **Return explicit safe defaults only where the security utility defines that behavior.**
   - For path traversal handling, rely on `validate_write_path()`’s contract.
   - Do not invent alternate fallback behavior in individual modules.

## Import and Module Organisation

1. **Group imports in this order: standard library, third-party, local application imports.**
   - Separate each group with one blank line.

2. **Use absolute imports from `src/` packages; do not use relative imports across subsystem boundaries.**
   - Prefer:
     ```python
     from trustflow.audit_stream import AuditStream
     ```
   - Avoid:
     ```python
     from ..trustflow.audit_stream import AuditStream
     ```

3. **Import `validate_write_path` directly from `path_security` in every writer module that accepts external paths.**
   - Do not wrap it in subsystem-specific aliases.

4. **Keep one primary responsibility per module.**
   - Examples:
     - `src/build_ledger.py` contains ledger claim/release/heartbeat logic.
     - `src/document_store.py` contains chunk/embed/retrieve logic.
   - Move unrelated utilities into a dedicated module rather than accumulating mixed concerns.

5. **Keep CI workflow generation logic in `src/ci_workflow.py`.**
   - Do not duplicate workflow file creation code in other modules.

6. **Place GitHub integration concerns in `src/github_tools.py`.**
   - `GitHubTool` and `WebhookReceiver` belong there unless a new module replaces the entire integration boundary.

7. **When introducing a new subsystem package under `src/`, add the mirrored test package under `tests/` in the same change.**
   - Example:
     - `src/rewind/replay_engine.py`
     - `tests/rewind/test_replay_engine.py`

8. **Do not create catch-all utility modules such as `utils.py`, `common.py`, or `helpers.py` at subsystem root.**
   - Name the module after the concrete responsibility:
     - `path_security.py`
     - `policy_parser.py`
     - `heartbeat_scheduler.py`

## Comment and Documentation Rules

1. **Document only non-obvious constraints, invariants, or compatibility requirements.**
   - Required comment targets:
     - security boundaries
     - branch naming compatibility
     - workflow filename compatibility
     - docs-PR keyword compatibility behavior
     - accessibility identifier structure

2. **When a convention is required for compatibility, state the exact external dependency in the comment.**
   - Example:
     ```python
     # Keep prefix as forge-agent/build for downstream compatibility.
     ```

3. **Do not add comments that merely restate the code.**
   - Avoid:
     ```python
     # Increment counter
     counter += 1
     ```

4. **When implementing legacy docs-PR behavior, label it with the version boundary.**
   - Example:
     ```python
     # v5.0 compatibility: docs keyword list removed in v6.0 but retained for old PR routing.
     ```

5. **Use docstrings on public classes and public functions that form subsystem entry points.**
   - Minimum content:
     - purpose
     - key inputs
     - side effects or outputs
   - Apply especially to:
     - pipeline orchestration
     - ledger persistence
     - workflow generation
     - policy evaluation
     - replay/audit components

6. **In Swift UI code, do not omit comments when an `accessibilityIdentifier` format is generated dynamically.**
   - Add a short comment naming the required pattern:
     ```swift
     // axIdentifier: {module}-{component}-{role}-{context?}
     ```

7. **Keep markdown documentation examples aligned to actual filenames and branch formats used by the codebase.**
   - Use `crafted-ci.yml`, `crafted-ci-macos.yml`, and `forge-agent/build/...` in examples.

## FullPlatform-Specific Patterns

1. **Preserve the architecture-defined filenames for core platform modules.**
   - Use:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`
   - Extend these modules only when the new code matches the module’s stated responsibility.

2. **Implement build orchestration in `BuildPipeline` within `src/build_director.py`.**
   - Put confidence gates and PR type routing there.
   - Do not scatter routing logic across webhook, ledger, and workflow modules.

3. **Implement claim/release/heartbeat lifecycle in `BuildLedger` within `src/build_ledger.py`.**
   - Do not duplicate lease state handling in orchestration code.

4. **Implement document chunking, embedding, and retrieval in `DocumentStore` within `src/document_store.py`.**
   - Keep retrieval logic co-located with storage/indexing logic.

5. **Generate and maintain both workflow files through `ci_workflow.ensure()`.**
   - Required outputs:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
   - If `conftest.py` support for `src/` imports is required, manage it through this same path.

6. **For FullPlatform code that writes generated files, always combine generation with path validation.**
   - Example pattern:
     ```python
     from path_security import validate_write_path

     workflow_path = validate_write_path(target_path)
     workflow_path.write_text(rendered_workflow)
     ```

7. **When handling PR classification, keep legacy docs-keyword detection isolated and clearly named.**
   - Use `_docs_keywords` for the keyword set.
   - Compute a boolean such as `is_docs_pr`.
   - Do not inline repeated keyword checks across multiple methods.

8. **Apply accessibility identifiers to every interactive macOS shell element in the Crafted application shell.**
   - Required element types include:
     - buttons
     - text fields
     - secure fields
     - rows/cards that receive interaction
   - Use `.accessibilityIdentifier(...)` on the view declaration itself.

9. **Keep accessibility identifier segments semantic and ordered.**
   - Segment order is fixed:
     - `module`
     - `component`
     - `role`
     - optional `context`
   - Do not swap role and component.
   - Correct:
     - `settings-anthropic-key-test-button`
   - Incorrect:
     - `settings-button-anthropic-key-test`

10. **Use stable domain context in stream and navigator identifiers.**
    - Examples:
      - `navigator-project-row-{projectId}`
      - `stream-gate-yes-button-{gateId}`
    - Do not use presentation-only values such as row number or localized title.

11. **When extending subsystem packages such as `cal`, `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, or `rewind`, keep package names lowercase exactly as defined.**
    - Do not rename or alias package directories to expanded forms in the filesystem.

12. **Do not introduce alternate CI naming, branch naming, or accessibility identifier formats inside FullPlatform code.**
    - FullPlatform must emit and consume the canonical forms only:
      - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
      - `crafted-ci.yml`
      - `crafted-ci-macos.yml`
      - `{module}-{component}-{role}-{context?}`