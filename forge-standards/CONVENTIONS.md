# Code Conventions - Forge Platform

## File and Directory Naming

1. Place Python application code under `src/`. Do not add production Python modules at repository root.

2. Use `snake_case.py` for all Python filenames.
   - Correct: `src/build_director.py`
   - Incorrect: `src/BuildDirector.py`, `src/build-director.py`

3. Keep the canonical subsystem filenames unchanged when implementing their primary responsibilities:
   - `src/consensus.py` — `ConsensusEngine`, generation system constants
   - `src/build_director.py` — build orchestration, confidence gate, PR routing
   - `src/github_tools.py` — GitHub integration and webhook handling
   - `src/build_ledger.py` — claim/release/heartbeat ledger logic
   - `src/document_store.py` — chunk/embed/retrieve document operations
   - `src/ci_workflow.py` — CI workflow generation and maintenance

4. Place subsystem code in the mandated directories only:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone
   - `src/trustlock/` — cryptographic machine identity
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

5. Mirror `src/` structure exactly under `tests/`.
   - If implementation file is `src/trustflow/audit_stream.py`, test file must be `tests/trustflow/test_audit_stream.py`.
   - Do not create test directories that do not correspond to a `src/` path.

6. Name test files `test_<module>.py` only. Do not use suffixes like `_spec.py` or prefixes like `spec_`.

7. Keep CI workflow filenames fixed:
   - `crafted-ci.yml` for Ubuntu workflow
   - `crafted-ci-macos.yml` for macOS/Swift workflow

8. Do not manually create or edit `conftest.py` for the `src/` import workaround if `ci_workflow.ensure()` owns it. Treat that file as generated and preserve its expected location/content pattern.

9. Use lowercase directory names with no spaces or hyphens for new Python package directories.
   - Correct: `src/fullplatform/`
   - Incorrect: `src/FullPlatform/`, `src/full-platform/`

10. Use singular module names unless the module is a collection/utility namespace already established by the architecture.
   - Keep existing pluralized canonical modules as-is, e.g. `github_tools.py`.

11. Store macOS Swift application-shell code in the subsystem path dedicated to that shell; do not mix Swift files into unrelated Python package directories.

12. When adding generated or workflow-managed files, name them exactly as produced by the managing component; do not introduce alternate spellings or environment-specific variants.

## Class and Function Naming

1. Name classes in `PascalCase`.
   - Correct: `BuildPipeline`, `BuildLedger`, `DocumentStore`
   - Incorrect: `buildPipeline`, `build_pipeline`

2. Name functions and methods in `snake_case`.
   - Correct: `claim_build()`, `retrieve_chunks()`
   - Incorrect: `claimBuild()`, `RetrieveChunks()`

3. Name constants in `UPPER_SNAKE_CASE`.
   - Correct: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`

4. Prefix internal helper functions with a single leading underscore.
   - Correct: `_load_claim_state()`
   - Do not use double underscore name-mangling for ordinary helpers.

5. Use verb-first names for methods that perform actions.
   - Correct: `claim()`, `release()`, `embed()`, `retrieve()`, `ensure()`
   - Incorrect: `ledger_claim()`, `document_retrieval()`

6. Use noun-based names for classes representing services, engines, stores, and controllers.
   - Correct: `ConsensusEngine`, `WebhookReceiver`, `GitHubTool`

7. Name boolean-returning functions and properties with `is_`, `has_`, `can_`, or `should_`.
   - Correct: `is_docs_pr()`, `has_claim()`, `should_route_to_swift()`

8. Use explicit subsystem prefixes in cross-cutting utility names when the scope would otherwise be ambiguous.
   - Correct: `trustflow_event_encoder()`, `vtz_policy_loader()`

9. For macOS accessibility identifiers, use this exact format on every interactive UI element:
   - `{module}-{component}-{role}`
   - `{module}-{component}-{role}-{context}` when context is required

10. Apply `.accessibilityIdentifier()` to all interactive SwiftUI/AppKit/UIKit elements. Do not leave buttons, fields, toggles, rows, or actionable cards unnamed.

11. Build accessibility identifiers using lowercase kebab-case segments only.
   - Correct: `settings-anthropic-key-test-button`
   - Incorrect: `settingsAnthropicKeyTestButton`, `settings_anthropic_key_test_button`

12. For identifiers tied to a runtime entity, append the entity identifier as the final segment.
   - Correct: `navigator-project-row-<projectId>`
   - Correct: `stream-gate-yes-button-<gateId>`

13. Use stable semantic names in accessibility identifiers; do not include presentation-only terms like color, position, or temporary copy text.
   - Correct: `auth-touchid-button`
   - Incorrect: `blue-left-button`

## Error and Exception Patterns

1. Validate paths before any write that uses user-supplied or externally-derived paths.
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

2. Perform path validation immediately before the write target is opened, created, moved, or overwritten. Do not validate once and reuse the unchecked original path later.

3. Always write using the validated path returned by `validate_write_path(...)`. Never write using the raw user-supplied path after validation has occurred.

4. Apply path validation to all write-like operations, including:
   - file creation
   - file overwrite
   - append operations
   - archive extraction targets
   - workflow/config generation
   - temp-file promotion into repository paths

5. Raise specific exceptions rather than `Exception`.
   - Correct: `ValueError`, `RuntimeError`, `FileNotFoundError`
   - Prefer project-specific exception classes when a failure mode is domain-specific.

6. Include the subsystem object and failed action in exception messages.
   - Correct: `"build_ledger claim failed for build_id=123"`
   - Incorrect: `"something went wrong"`

7. Do not swallow exceptions with bare `except:` blocks.

8. When catching an exception to add context, re-raise with `from`.
   ```python
   try:
       ledger.claim(build_id)
   except OSError as exc:
       raise RuntimeError(f"build_ledger claim failed for build_id={build_id}") from exc
   ```

9. Use guard clauses for invalid inputs at the top of functions.
   ```python
   if not pr_number:
       raise ValueError("build_director requires pr_number")
   ```

10. Return normal values for expected negative outcomes; raise exceptions only for actual failure states.
   - Example: return `False` for "claim not acquired"
   - Example: raise for "ledger file unreadable"

11. Do not encode control flow in exception-string matching. If behavior branches by error type, branch on exception class.

12. When handling docs PR classification logic from legacy keyword matching, keep the keyword list isolated in a dedicated constant and name the predicate clearly.
   - Correct: `_DOCS_KEYWORDS`, `is_docs_pr_title()`
   - Do not scatter inline keyword checks across multiple modules.

## Import and Module Organisation

1. Use absolute imports rooted from `src` packages; avoid relative imports between top-level subsystems unless there is a strong package-local reason.

2. Group imports in this order, with one blank line between groups:
   1. standard library
   2. third-party packages
   3. local project imports

3. Sort imports alphabetically within each group.

4. Import modules or top-level symbols directly from their owning module; do not create deep circular dependency chains through re-export files.

5. Keep one primary responsibility per module. If a file name matches a core architecture component, keep unrelated logic out of it.
   - Example: do not put webhook parsing into `document_store.py`

6. Avoid wildcard imports.

7. If a module is workflow-owned or generated, import from its stable public API only; do not depend on internal helper symbols that may be regenerated.

8. Place module-level constants above class and function definitions.

9. Keep environment/platform-specific code in platform-specific modules instead of branching repeatedly inside generic modules.
   - Example: CI workflow generation for macOS belongs in the workflow module or platform-targeted helper, not spread through unrelated build orchestration code.

10. If `conftest.py` is auto-committed by `ci_workflow.ensure()` for `src/` import behavior, tests must rely on that standard setup rather than introducing duplicate path-munging in each test file.

11. Do not manipulate `sys.path` inside production modules.

12. Keep Swift/macOS shell accessibility and UI wiring code separated from backend orchestration modules; communicate through explicit interfaces or generated artifacts, not shared global state.

## Comment and Documentation Rules

1. Write comments that explain intent, invariant, or non-obvious constraint. Do not comment restatements of the next line of code.

2. Use complete sentences for module-level and function-level comments.

3. Document every public class and public function with a concise docstring stating what it does and its key inputs/outputs.

4. When a rule is mandated by a TRD or workflow contract, name the contract directly in the comment or docstring.
   - Example: `# TRD: all interactive elements require accessibility identifiers.`

5. Keep legacy behavior notes explicit.
   - Example: document that branch naming remains `forge-agent/...` for compatibility.

6. For generated files or generated sections, mark them clearly.
   - Example: `# Generated by ci_workflow.ensure(); do not edit manually.`

7. Do not leave TODO comments without an owner or trigger condition.
   - Correct: `TODO(build-pipeline): remove v5 docs keyword fallback after v6 migration completes.`
   - Incorrect: `TODO: clean this up`

8. If docs-PR detection uses the legacy v5 keyword fallback, annotate it as legacy behavior and keep the comment adjacent to the constant/predicate that implements it.

9. Use examples in documentation only when they match actual project conventions.
   - Example branch: `forge-agent/build/e123/fullplatform/pr-042-shell-bootstrap`

10. Keep markdown documentation terminology aligned with code and directory names.
   - Use `FullPlatform`, `BuildLedger`, `crafted-ci.yml`
   - Do not invent alternate labels for the same component.

11. When documenting accessibility identifiers, show exact identifier strings in backticks.

12. Do not describe path validation as optional. Any documentation for write paths must state that validation occurs before every write.

## FullPlatform-Specific Patterns

1. Use this exact branch naming convention for all agent-created branches:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

2. Keep the `forge-agent` prefix unchanged even if another prefix seems more descriptive. This is a compatibility requirement.

3. Format PR numbers in branch names as three digits minimum, zero-padded.
   - Correct: `pr-003-fix-ledger-race`
   - Incorrect: `pr-3-fix-ledger-race`

4. Build `subsystem_slug` in lowercase kebab-case.
   - Correct: `fullplatform`, `macos-shell`, `trustflow-audit`

5. Build `title_slug` in lowercase kebab-case with only stable descriptive words. Remove punctuation and do not include ticket delimiters or transient status words.
   - Correct: `shell-bootstrap`
   - Incorrect: `WIP_shell-bootstrap!!!`

6. For FullPlatform workflow generation, update only the canonical CI workflow files:
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

7. When ensuring CI support for `src/` imports, use `ci_workflow.ensure()` as the source of truth. Do not duplicate its `conftest.py` creation logic elsewhere.

8. In PR classification code that still supports the removed v5 docs-keyword behavior, isolate the fallback in a dedicated constant and predicate.
   ```python
   _DOCS_KEYWORDS = {"naming convention", "glossary", "changelog"}

   def is_docs_pr_title(title: str) -> bool:
       title_lower = title.lower()
       return any(keyword in title_lower for keyword in _DOCS_KEYWORDS)
   ```

9. Treat the v5 docs-keyword logic as fallback compatibility only. New routing or classification logic must not depend exclusively on keyword matching.

10. In macOS application-shell code, every interactive control must set `.accessibilityIdentifier(...)` inline with creation or in the immediate modifier chain; do not defer identifier assignment to distant helper code unless the helper exclusively constructs that control.

11. Use the TRD accessibility naming pattern consistently across related controls:
   - `auth-touchid-button`
   - `auth-passcode-button`
   - `settings-anthropic-key-field`
   - `settings-anthropic-key-test-button`
   - `settings-anthropic-key-reveal-button`

12. For repeated dynamic UI items in FullPlatform shell views, include the backing entity ID in the identifier.
   - `navigator-project-row-<projectId>`
   - `stream-gate-card-<gateId>`
   - `stream-gate-yes-button-<gateId>`
   - `stream-gate-skip-button-<gateId>`
   - `stream-gate-stop-button-<gateId>`

13. Do not truncate or vary action role names in accessibility identifiers for sibling controls. Use the full action word consistently across the set.
   - Use `yes-button`, `skip-button`, `stop-button`
   - Do not mix `yes-btn` and `stop-button`

14. In FullPlatform code that writes generated artifacts, workflow files, logs, exports, or replay outputs, call `validate_write_path()` before the write even when the path appears to come from internal metadata if any portion originated outside the current process.

15. When adding tests for FullPlatform modules, mirror both subsystem and platform boundaries.
   - Example: `src/fullplatform/macos_shell/auth_view.py` → `tests/fullplatform/macos_shell/test_auth_view.py`

16. Keep orchestration concerns in coordinator modules and storage concerns in store/ledger modules.
   - Build routing belongs in `build_director.py`
   - Claim/release/heartbeat belongs in `build_ledger.py`
   - Document chunk/embed/retrieve belongs in `document_store.py`

17. If a change affects CI generation, add or update tests that assert the exact canonical workflow filenames and any generated `conftest.py` expectations.

18. If a change affects branch generation, add or update tests that assert the exact branch string format, including `forge-agent`, subsystem slug, and zero-padded PR number.