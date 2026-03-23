# Code Conventions - Forge Platform

## File and Directory Naming

1. **Place source files under the canonical Forge subsystem directories only.**
   - Use these top-level paths exactly:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`
     - `tests/<subsystem>/`
   - Do not create alternate subsystem spellings or aliases.

2. **Mirror `src/` structure exactly under `tests/`.**
   - If implementation file is `src/mcp/policy_engine.py`, test file must live under `tests/mcp/`.
   - Preserve nested directories when present.

3. **Use `snake_case` for all Python filenames.**
   - Correct: `build_director.py`, `document_store.py`
   - Incorrect: `BuildDirector.py`, `document-store.py`

4. **Keep architecture-defined filenames unchanged when implementing their primary responsibility.**
   - Use these names for these responsibilities:
     - `src/consensus.py` — `ConsensusEngine`, generation system constants
     - `src/build_director.py` — build orchestration, confidence gate, PR routing
     - `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
     - `src/build_ledger.py` — claim/release/heartbeat ledger logic
     - `src/document_store.py` — chunk/embed/retrieve document logic
     - `src/ci_workflow.py` — CI workflow generation/ensure logic

5. **Name test files `test_<module>.py`.**
   - For `src/build_ledger.py`, use `tests/.../test_build_ledger.py`.

6. **Keep CI workflow filenames fixed.**
   - Ubuntu workflow file must be named `crafted-ci.yml`.
   - macOS Swift workflow file must be named `crafted-ci-macos.yml`.
   - Do not introduce variant names such as `ci.yml`, `forge-ci.yml`, or `macos.yml`.

7. **Do not manually rename or remove `conftest.py` created by `ci_workflow.ensure()`.**
   - Treat it as required bootstrap for `src/` imports in CI-managed test environments.

8. **Validate every user-supplied or derived write path before any filesystem write.**
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```
   - Apply this before opening files, creating directories, writing artifacts, exporting logs, or generating workflows.

9. **Validate paths even when the path originated from PR metadata, branch names, config files, or generated slugs.**
   - Do not assume internal provenance makes a path safe.

10. **Use branch names in the mandatory compatibility format.**
    - Format:
    ```text
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - Example:
    ```text
    forge-agent/build/e123/fullplatform/pr-017-add-ledger-heartbeat
    ```

## Class and Function Naming

1. **Use `PascalCase` for classes.**
   - Correct: `ConsensusEngine`, `BuildPipeline`, `DocumentStore`, `WebhookReceiver`

2. **Use `snake_case` for functions and methods.**
   - Correct: `claim_build()`, `release_claim()`, `ensure_workflow()`, `retrieve_chunks()`

3. **Name boolean-returning functions with an explicit predicate prefix.**
   - Use prefixes such as `is_`, `has_`, `should_`, `can_`.
   - Correct: `is_docs_pr()`, `has_active_claim()`, `should_route_to_swift()`

4. **Name constants in `UPPER_SNAKE_CASE`.**
   - Correct: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`

5. **Use noun names for stateful service objects and verb names for actions.**
   - Classes: `BuildLedger`, `GitHubTool`
   - Functions: `embed()`, `retrieve()`, `chunk()`, `heartbeat()`

6. **Suffix receiver/adapter classes by role when matching architecture concepts.**
   - Use names like `WebhookReceiver`, `PolicyEngine`, `ConsensusEngine`.
   - Do not use vague suffixes like `Manager` when a domain term already exists.

7. **Use subsystem terms in names when code is subsystem-scoped.**
   - Examples:
     - `TrustFlowEvent`
     - `VTZEnforcer`
     - `RewindReplaySession`
     - `ConnectorClient`

8. **Use exact docs-PR helper naming when implementing docs classification logic.**
   - Name the keyword set `_docs_keywords`.
   - Name the predicate helper `_is_docs_pr`.
   - Keep both private unless a TRD explicitly requires public exposure.

9. **Use accessibility identifier names in the exact structured format for macOS interactive UI elements.**
   - Format:
   ```text
   {module}-{component}-{role}-{context?}
   ```
   - Examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `navigator-project-row-{projectId}`
     - `stream-gate-yes-button-{gateId}`

10. **Assign an accessibility identifier to every interactive SwiftUI/AppKit control.**
    - Apply `.accessibilityIdentifier(...)` on buttons, fields, rows, toggles, segmented controls, and actionable cards.
    - Do not leave interactive elements unnamed.

## Error and Exception Patterns

1. **Raise specific exception types; do not raise bare `Exception`.**
   - Prefer `ValueError`, `FileNotFoundError`, `PermissionError`, or subsystem-specific exceptions.

2. **Include the failing resource identifier in every raised error message.**
   - Include values such as `project_id`, `gate_id`, `workflow_name`, `branch_name`, or normalized path.

3. **Fail closed on unsafe write paths.**
   - Always use the result from `validate_write_path(...)`.
   - Do not continue with the original path after validation.

4. **Reject invalid naming inputs at construction or boundary methods.**
   - Validate branch names, workflow filenames, subsystem slugs, and accessibility identifier fragments before use.

5. **Raise on unsupported workflow filename requests.**
   - Accept only `crafted-ci.yml` and `crafted-ci-macos.yml` for generated workflow targets.

6. **When classifying docs PRs, default to non-docs if classification data is incomplete.**
   - Only return docs classification when keyword/title checks actually match.
   - Do not infer docs status from missing fields.

7. **Convert low-level filesystem errors into domain-specific errors at subsystem boundaries.**
   - Example: wrap `OSError` from workflow generation in a workflow/domain exception with the validated path included.

8. **Preserve original exceptions when re-raising.**
   - Use `raise ... from exc` to keep traceback context.

## Import and Module Organisation

1. **Group imports in this order with a single blank line between groups:**
   1. Standard library
   2. Third-party packages
   3. Local application imports

2. **Import from the canonical module that owns the behavior.**
   - Example: import CI ensure logic from `src/ci_workflow.py`, not from an unrelated helper module.

3. **Do not use wildcard imports.**
   - Never use `from module import *`.

4. **Import `validate_write_path` directly in every module that performs writes.**
   - Required:
   ```python
   from path_security import validate_write_path
   ```
   - Do not hide path validation behind unrelated utility wrappers unless that wrapper is the module’s single write boundary.

5. **Keep subsystem imports scoped to their subsystem when possible.**
   - Prefer `src/mcp/...` imports within MCP code over cross-subsystem reach-through imports.

6. **Avoid circular imports by moving shared logic into a lower-level module with a subsystem-specific name.**
   - Example: move shared trustflow event formatting into `src/trustflow/event_format.py`.

7. **Name test imports to match production module names exactly.**
   - If the module is `build_ledger`, tests should import `build_ledger`, not a renamed alias.

8. **Do not rely on ad hoc path mutation in tests.**
   - Use the `conftest.py` path setup produced by `ci_workflow.ensure()` rather than inserting custom `sys.path` edits throughout tests.

## Comment and Documentation Rules

1. **Write comments only when they add behavior, constraint, or rationale that is not obvious from the code.**
   - Do not restate the next line in prose.

2. **Document every non-obvious convention with the exact enforced format.**
   - For branch names, workflow files, and accessibility identifiers, include the literal pattern string in comments or docstrings near validators/builders.

3. **Use docstrings on public classes and public functions.**
   - State:
     - what the unit does
     - required inputs
     - return value or side effects
     - key constraints if any

4. **Keep inline examples synchronized with enforced naming formats.**
   - If a validator enforces `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`, examples in docstrings must use that same shape.

5. **When implementing docs PR classification, document that v5.0 keyword matching existed and was removed in v6.0 if legacy support remains in code.**
   - If `_docs_keywords` or `_is_docs_pr` remains for compatibility, add a short note explaining that it is legacy compatibility behavior.

6. **Do not document deprecated alternative filenames or branch formats as acceptable.**
   - Mention them only to reject them.

7. **Use code comments to mark TRD-mandated behaviors where the implementation might otherwise look arbitrary.**
   - Examples:
     - fixed workflow filenames
     - mandatory accessibility identifiers
     - path validation before writes

## FullPlatform-Specific Patterns

1. **Treat FullPlatform as an orchestration boundary, not a dumping ground for mixed responsibilities.**
   - Keep consensus, build orchestration, GitHub integration, ledgering, document retrieval, and CI generation in their designated modules.

2. **Use the architecture-defined module split for orchestration flows.**
   - Route responsibilities as follows:
     - consensus logic → `src/consensus.py`
     - build routing/orchestration → `src/build_director.py`
     - GitHub/webhook integration → `src/github_tools.py`
     - claim/release/heartbeat state → `src/build_ledger.py`
     - retrieval/chunk/embed logic → `src/document_store.py`
     - workflow ensure/generation → `src/ci_workflow.py`

3. **Implement build ledger operations as explicit lifecycle actions.**
   - Prefer methods named like `claim()`, `release()`, and `heartbeat()` over generic `update_status()` methods when handling build ownership.

4. **Implement document store APIs as retrieval pipeline verbs.**
   - Prefer method names like `chunk()`, `embed()`, and `retrieve()` to reflect the TRD vocabulary directly.

5. **Keep PR routing logic in `build_director` and not in GitHub integration classes.**
   - `github_tools` may fetch or receive events.
   - `build_director` decides build path, confidence gate handling, and PR type routing.

6. **Keep webhook transport concerns separate from domain action execution.**
   - `WebhookReceiver` parses and validates inbound webhook data.
   - Downstream orchestration classes perform the build and routing decisions.

7. **When generating CI workflows, emit only the crafted workflow filenames.**
   - Ubuntu generation target: `crafted-ci.yml`
   - macOS Swift generation target: `crafted-ci-macos.yml`

8. **Run `validate_write_path()` before creating or updating workflow files, generated test support files, replay artifacts, or exported documents.**
   - This includes writes performed by CI ensure flows.

9. **For macOS FullPlatform UI code, encode entity identifiers in accessibility identifiers when the element operates on a specific entity.**
   - Examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-stop-button-{gateId}`

10. **Use stable lowercase hyphenated segments in accessibility identifiers.**
    - Do not use spaces, underscores, camelCase, or localized text in identifier segments.

11. **Keep docs PR detection logic isolated and explicitly named when retained for backward compatibility.**
    - Store legacy keyword matching in `_docs_keywords`.
    - Implement the decision in `_is_docs_pr(...)`.
    - Do not spread title-keyword checks across unrelated modules.

12. **Do not create write paths directly from PR titles, subsystem slugs, or webhook payload fields without validation.**
    - Slug generation does not replace `validate_write_path()`.

13. **When adding a new FullPlatform subsystem module, place it under the matching Forge namespace and add mirrored tests immediately.**
    - Example: `src/trustflow/audit_stream.py` must be paired with `tests/trustflow/test_audit_stream.py`.

14. **Prefer explicit domain nouns from Forge terminology in new APIs.**
    - Use names like `audit_stream`, `policy_engine`, `replay_engine`, `trust_label`, and `connector_client` instead of generic terms like `processor`, `handler`, or `service` unless the domain term is genuinely unknown.