# Code Conventions - Forge Platform

## File and Directory Naming

1. Place Python backend modules under `src/` using `snake_case.py` filenames only.
   - Required examples:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`

2. Use the established subsystem directories exactly as named. Do not invent alternate spellings.
   - Required directories:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`

3. Mirror `src/` structure exactly under `tests/`.
   - If implementation is `src/mcp/policy_engine.py`, the test file must be `tests/mcp/test_policy_engine.py`.
   - Do not place subsystem tests in a shared top-level `tests/test_*.py` file when a matching subsystem directory exists.

4. Prefix Python test files with `test_`.
   - Valid: `tests/trustflow/test_audit_stream.py`
   - Invalid: `tests/trustflow/audit_stream_test.py`

5. Keep CI workflow filenames fixed.
   - Ubuntu workflow file must be `crafted-ci.yml`.
   - macOS Swift workflow file must be `crafted-ci-macos.yml`.
   - Do not add renamed duplicates such as `ci.yml` or `macos.yml`.

6. Do not manually add or remove `conftest.py` files created by CI import setup.
   - Treat `conftest.py` under test roots as managed by `ci_workflow.ensure()` when used for `src/` imports.

7. Name branch heads using this exact format:
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example: `forge-agent/build/e17/fullplatform/pr-042-accessibility-id-audit`

8. Use lowercase directory and file names for all new Forge modules.
   - Separate words with underscores in filenames and with hyphens only in branch names and workflow identifiers.

9. For Swift/macOS shell files, keep filenames aligned to the primary type name.
   - If the main type is `SettingsView`, the file must be `SettingsView.swift`.
   - Do not use abbreviated filenames like `Settings.swift` when the declared top-level type is `SettingsView`.

10. When adding subsystem-specific code, place it in the subsystem directory rather than a generic utility file.
    - Put Virtual Trust Zone logic in `src/vtz/`, not `src/utils.py`.
    - Put replay logic in `src/rewind/`, not `src/helpers/`.

11. Validate paths before any write using `validate_write_path`.
    - Required pattern:
      ```python
      from path_security import validate_write_path

      safe_path = validate_write_path(user_supplied_path)
      ```
    - Apply this before writing files, creating files, overwriting files, or generating workflow/config outputs from user or PR-derived paths.

## Class and Function Naming

1. Name Python classes in `PascalCase`.
   - Required examples:
     - `ConsensusEngine`
     - `BuildPipeline`
     - `GitHubTool`
     - `WebhookReceiver`
     - `BuildLedger`
     - `DocumentStore`

2. Name Python functions and methods in `snake_case`.
   - Valid: `claim_build()`, `release_claim()`, `retrieve_chunks()`
   - Invalid: `claimBuild()`, `ReleaseClaim()`

3. Name module-level constants in `UPPER_SNAKE_CASE`.
   - Required examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

4. Use noun-based names for service/coordinator classes and verb-based names for free functions.
   - Valid class names: `BuildLedger`, `DocumentStore`
   - Valid function names: `chunk()`, `embed()`, `retrieve()`

5. Match filenames to their primary class or responsibility.
   - `src/build_ledger.py` must contain `BuildLedger`.
   - `src/github_tools.py` must contain `GitHubTool` and/or `WebhookReceiver`.
   - Do not place unrelated top-level classes in these modules.

6. Name Boolean-returning functions and properties with explicit intent.
   - Prefer `is_docs_pr`, `has_claim`, `can_release`
   - Do not use ambiguous names like `docs()` or `ready()` for Boolean checks.

7. Preserve the historical docs-PR detector naming when touching v5 compatibility logic.
   - Use `_docs_keywords` for the keyword set.
   - Use `_is_docs_pr` for the derived Boolean.
   - Do not rename these to `docs_terms` or `matches_docs_pr` in compatibility code.

8. For accessibility identifiers, build values using this exact token order:
   - `{module}-{component}-{role}-{context?}`
   - Use lowercase kebab-case tokens.

9. In Swift UI code, assign `.accessibilityIdentifier()` to every interactive element.
   - Interactive means buttons, text fields, secure fields, toggles, rows with tap actions, and actionable cards.

10. Follow the approved accessibility identifier patterns exactly.
    - Valid examples:
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

11. When interpolating context into an accessibility identifier, append it as the final token.
    - Valid: `navigator-project-row-1234`
    - Invalid: `navigator-1234-project-row`

12. Do not abbreviate subsystem names in identifiers unless the directory name is already the standard abbreviation.
    - Use `settings`, not `sett`
    - Use `navigator`, not `nav`
    - Keep `vtz`, `dtl`, and `mcp` only where those abbreviations are the canonical subsystem names

## Error and Exception Patterns

1. Validate the destination path before every write operation.
   - This includes writes triggered by CLI input, PR metadata, webhook payloads, generated filenames, and test fixtures.
   - Required pattern:
     ```python
     from path_security import validate_write_path

     safe_path = validate_write_path(target_path)
     with open(safe_path, "w", encoding="utf-8") as f:
         ...
     ```

2. Use one validation step per write target, immediately before the write.
   - Do not validate a parent directory once and assume all derived child paths are safe.
   - Re-run `validate_write_path()` after any path concatenation or filename substitution.

3. Raise exceptions with concrete operational context.
   - Include the subsystem, operation, and identifier involved.
   - Valid: `raise RuntimeError(f"build_ledger release failed for claim {claim_id}")`
   - Invalid: `raise RuntimeError("operation failed")`

4. Do not swallow exceptions from path validation, CI workflow generation, or ledger claim/release operations.
   - Either let the exception propagate or wrap it with added context and re-raise.

5. When wrapping exceptions, preserve the original exception with `from`.
   - Required:
     ```python
     try:
         workflow.ensure()
     except Exception as exc:
         raise RuntimeError("ci_workflow ensure failed for crafted-ci.yml") from exc
     ```

6. Return explicit Boolean values from classification helpers.
   - `_is_docs_pr` must evaluate to a `bool`.
   - Do not return keyword matches, collections, or nullable values from helpers used as gates.

7. Fail closed on invalid or missing accessibility identifiers in testable interactive views.
   - If an interactive SwiftUI element cannot be assigned a stable identifier, block the change until a stable identifier is defined.

8. Use deterministic error messages for CI-related failures.
   - Include the exact workflow filename:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`

## Import and Module Organisation

1. Group imports in this order with one blank line between groups:
   1. Standard library
   2. Third-party packages
   3. Local project imports

2. Import path validation directly from `path_security` at the module where the write occurs.
   - Required:
     ```python
     from path_security import validate_write_path
     ```
   - Do not hide write-path validation only inside a distant helper if the module performs direct writes.

3. Keep subsystem imports within their subsystem boundary unless the dependency is intentionally shared.
   - Example: `src/trustflow/...` may import shared infrastructure from `src/...`, but do not import `src/rewind/...` into `src/trustlock/...` for convenience without a declared shared interface.

4. Prefer direct module imports that reflect file ownership.
   - Valid: `from src.build_ledger import BuildLedger`
   - Avoid re-export chains that hide the source module.

5. Keep one primary responsibility per module.
   - `src/document_store.py` contains document storage and retrieval behavior.
   - Do not add unrelated GitHub webhook parsing into `src/document_store.py`.

6. Co-locate tests with the module shape they verify.
   - If a module is moved from `src/github_tools.py` to `src/cal/github_tools.py`, move tests from `tests/test_github_tools.py` to `tests/cal/test_github_tools.py`.

7. Do not create catch-all modules such as `misc.py`, `helpers.py`, or `common.py` in subsystem directories.
   - Name the module after the concrete behavior: `policy_eval.py`, `audit_stream.py`, `replay_store.py`.

8. In Swift/macOS shell code, keep view, model, and coordinator types in separate files when they are top-level reusable types.
   - Do not define multiple unrelated top-level views in a single file solely for convenience.

## Comment and Documentation Rules

1. Write comments only when they encode project-specific intent, protocol, or constraint that is not obvious from code.
   - Valid: why `_docs_keywords` must remain for v5 compatibility
   - Invalid: `# increment i`

2. When documenting compatibility behavior, name the exact version boundary.
   - Required example: `v5 keyword list retained for docs-PR compatibility; removed in v6 logic`

3. Keep inline comments adjacent to the constrained code path they describe.
   - Do not place compatibility comments in module headers if they only apply to one helper.

4. For accessibility identifier declarations in Swift, prefer self-explanatory literals and avoid explanatory comments unless the context token is non-obvious.
   - Valid:
     ```swift
     .accessibilityIdentifier("settings-anthropic-key-test-button")
     ```
   - Add a comment only if the final context token comes from a non-UI domain identifier.

5. Use docstrings on public classes and functions that define subsystem contracts.
   - Include what the component owns or orchestrates.
   - Example: `BuildLedger` docstring should state claim/release/heartbeat responsibilities.

6. Do not use comments to excuse missing validation or missing identifiers.
   - Fix the code instead of writing comments like `# trusted path` or `# identifier added later`.

7. If a module writes files, include a brief comment or docstring note where appropriate stating that write targets are path-validated.
   - This rule does not replace the required runtime call to `validate_write_path()`.

8. Keep terminology aligned with Forge naming already in use.
   - Use `FullPlatform`, `BuildPipeline`, `TrustFlow`, `Virtual Trust Zone`, and `Forge Rewind` exactly as written in project docs.
   - Do not rename them in comments to ad hoc variants.

## FullPlatform-Specific Patterns

1. Treat `FullPlatform` as an orchestration layer, not a dumping ground for subsystem logic.
   - Put reusable implementation in the owning subsystem module.
   - Keep FullPlatform code focused on wiring, routing, and coordination.

2. In FullPlatform build orchestration, keep build routing logic inside the build director flow.
   - PR-type routing belongs in `src/build_director.py`.
   - Do not duplicate routing logic in webhook handlers or document store modules.

3. Keep confidence gate behavior in the build orchestration path, not in leaf subsystem code.
   - Leaf modules may report signals; they must not decide platform-wide build admission.

4. Store GitHub integration behavior in `src/github_tools.py`.
   - `GitHubTool` and `WebhookReceiver` remain the owning types for GitHub-side operations.
   - Do not move webhook parsing into `build_director.py`.

5. Keep ledger ownership in `src/build_ledger.py`.
   - Claim, release, and heartbeat operations must be implemented there or in tightly related ledger modules.
   - Do not implement ad hoc claim files in CI or webhook code.

6. Keep document chunking, embedding, and retrieval in `src/document_store.py`.
   - Do not duplicate chunking logic in consensus or build orchestration modules.

7. When generating or ensuring CI workflows, use the canonical workflow names only.
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

8. Treat `ci_workflow.ensure()` as the authority for managed CI setup.
   - If `conftest.py` is needed for `src/` imports, let `ci_workflow.ensure()` create or update it.
   - Do not hand-maintain a conflicting version in the same path.

9. For docs-PR classification in compatibility code, use the historical keyword gate only where that compatibility is required.
   - Required pattern:
     ```python
     _docs_keywords = {...}
     _is_docs_pr = any(kw in title_lower for kw in _docs_keywords)
     ```
   - Do not spread separate, drifting docs-keyword lists across modules.

10. In macOS FullPlatform UI shell code, every interactive control must have a stable accessibility identifier before merge.
    - Use the `{module}-{component}-{role}-{context?}` convention.
    - Verify IDs are deterministic across launches for the same logical entity.

11. For row- and card-based interactive UI in FullPlatform, include the domain identifier as the final token.
    - Required:
      - `navigator-project-row-{projectId}`
      - `stream-gate-card-{gateId}`
    - Use the persisted model identifier, not a display index.

12. Do not use array positions or transient UUIDs for accessibility identifier context.
    - Invalid: `navigator-project-row-0`
    - Invalid: `stream-gate-card-\(UUID())`
    - Valid: `navigator-project-row-\(project.id)`

13. Before writing generated FullPlatform artifacts derived from PR metadata, validate the final path after slug construction.
    - This applies to generated logs, workflow edits, temporary specs, and exported reports.

14. When FullPlatform code touches filesystem output and CI setup in the same flow, validate each file target independently.
    - Validate workflow file paths separately from test support file paths such as `conftest.py`.

15. Keep subsystem slugs in branch names lowercase and aligned with real ownership.
    - Use `fullplatform`, `mcp`, `trustflow`, `rewind`, `vtz`
    - Do not use mixed-case or alternate labels like `FullPlatform` or `trust-flow`