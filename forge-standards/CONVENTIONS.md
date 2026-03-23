# Code Conventions - Forge Platform

## File and Directory Naming

1. Place Python application code under `src/`. Do not create top-level runtime packages outside `src/`.

2. Use `snake_case.py` for all Python filenames.

3. Keep the following canonical filenames and responsibilities unchanged:
   - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
   - `src/build_director.py` — build pipeline orchestration, confidence gate, PR type routing
   - `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
   - `src/build_ledger.py` — `BuildLedger`, claim/release, heartbeat
   - `src/document_store.py` — `DocumentStore`, `chunk()`, `embed()`, `retrieve()`
   - `src/ci_workflow.py` — CI workflow generation and maintenance for `crafted-ci.yml` and `crafted-ci-macos.yml`

4. Use these exact subsystem directories when adding new platform code:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — cryptographic machine identity
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

5. Mirror source structure exactly in tests. For any source file `src/<path>/module.py`, place tests under `tests/<path>/test_module.py`.

6. Do not collapse unrelated subsystems into shared directories such as `src/utils/` or `src/helpers/` unless the code is reused by at least two existing subsystems and the name reflects the domain.

7. Name workflow files exactly:
   - `crafted-ci.yml` for Ubuntu CI
   - `crafted-ci-macos.yml` for macOS/Swift CI

8. Do not manually add or rename `conftest.py` files created by `ci_workflow.ensure()`. Treat auto-committed `conftest.py` as managed infrastructure for `src/` imports.

9. Use lowercase, hyphenated slugs for subsystem identifiers in branch names and automation metadata.

10. Branch names must use this exact format:
    `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

11. In branch names:
    - `{engineer_id}` must be lowercase alphanumeric or hyphenated
    - `{subsystem_slug}` must match the owning subsystem directory or canonical subsystem slug
    - `{N:03d}` must be zero-padded to 3 digits
    - `{title_slug}` must be lowercase words separated by hyphens

12. Do not introduce new documentation/PR routing based on the removed v5.0 `_docs_keywords` list. Do not recreate `_docs_keywords` or any title-keyword docs classifier.

## Class and Function Naming

1. Use `PascalCase` for classes.

2. Use `snake_case` for functions, methods, and module-level variables.

3. Use `UPPER_SNAKE_CASE` for constants, prompt templates, and immutable system strings such as `GENERATION_SYSTEM` and `UI_ADDENDUM`.

4. Name classes after their concrete role, not generic suffixes. Prefer `BuildLedger`, `DocumentStore`, `ConsensusEngine`; avoid names like `Manager`, `Helper`, or `Processor` unless the module already defines that domain term.

5. Name public functions with a verb phrase that describes the side effect or return value:
   - `claim_build()`
   - `release_build()`
   - `validate_write_path()`
   - `ensure_workflow()`

6. Prefix boolean-returning functions and properties with `is_`, `has_`, `can_`, or `should_` when the return type is a predicate.

7. Use domain nouns in subsystem APIs. Examples:
   - `embed()` and `retrieve()` in document storage
   - `claim()` and `heartbeat()` in build ledger
   - `receive_webhook()` or `handle_webhook()` in GitHub integration

8. Keep Swift/macOS accessibility identifiers in this exact format:
   `{module}-{component}-{role}-{context?}`

9. Apply `.accessibilityIdentifier()` to every interactive SwiftUI/AppKit/UIKit element.

10. Build accessibility identifiers from stable domain values, not display text. Use IDs such as project IDs or gate IDs where required.

11. Follow these identifier patterns exactly when applicable:
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

12. Do not abbreviate accessibility roles. Use `button`, `field`, `row`, `card`; do not use `btn`, `fld`, or `rw`.

## Error and Exception Patterns

1. Validate paths before any write operation that uses a user-supplied or externally-derived path.

2. Use this exact pattern before writes:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

3. Call `validate_write_path()` before:
   - file creation
   - file overwrite
   - appending to files
   - archive extraction targets
   - generated workflow writes
   - test fixture writes when the path is not hardcoded

4. Use the validated path variable for the actual write. Do not validate and then write to the original untrusted path.

5. If a function writes to disk, perform path validation in the same function or in a clearly named wrapper directly above it in the call chain.

6. Raise specific exceptions for domain failures. Do not raise bare `Exception`.

7. When translating lower-level exceptions, preserve the original exception with `raise ... from exc`.

8. Include actionable context in error messages:
   - include subsystem name
   - include operation
   - include sanitized identifier or path
   - do not include secrets, tokens, or raw key material

9. For CI workflow generation errors, include the workflow filename (`crafted-ci.yml` or `crafted-ci-macos.yml`) in the exception message.

10. For GitHub or webhook failures, include repository, PR number, or delivery identifier when available.

11. Return explicit failure objects or raise explicit exceptions; do not signal errors with `None` when the caller cannot distinguish failure from absence.

12. Do not catch and suppress exceptions without logging or converting them into a domain-specific result.

## Import and Module Organisation

1. Use absolute imports rooted at `src` package resolution conventions; do not rely on relative imports across sibling subsystems.

2. Group imports in this order, with one blank line between groups:
   - standard library
   - third-party packages
   - local application imports

3. Within each group, sort imports alphabetically by module path.

4. Import concrete symbols only when they are used directly more than once or are the module’s main contract. Otherwise import the module and qualify usage.

5. Do not use wildcard imports.

6. Keep one primary domain per module. If a file contains code for multiple subsystems, split it into subsystem-owned modules.

7. Keep orchestration code in top-level canonical modules such as `build_director.py`; keep subsystem logic inside subsystem directories.

8. Put CI workflow file creation and maintenance logic in `src/ci_workflow.py`. Do not duplicate workflow-generation logic in unrelated modules.

9. Keep GitHub integration code in `src/github_tools.py` or a dedicated `src/github_tools/` package if the module is being split intentionally.

10. When adding test imports that depend on `src/`, rely on the managed `conftest.py` created by `ci_workflow.ensure()` instead of local path hacks.

11. Do not mutate `sys.path` inside tests or runtime modules to compensate for missing import structure.

12. When a module exports a single dominant class or function, name the file after that domain concept in `snake_case`.

## Comment and Documentation Rules

1. Write comments only for non-obvious intent, invariants, security constraints, or cross-system coupling.

2. Do not add comments that restate the code literally.

3. Document every public class and public function with a concise docstring describing:
   - what it does
   - the key input(s)
   - the key output or side effect

4. For any function that writes to disk, mention path validation expectations in the docstring if the path can originate outside the module.

5. For security-sensitive code, add an inline comment directly above the guard or validation, not at the top of the file.

6. When code depends on a managed convention from TRDs, reference the concrete rule in the comment text. Example: `# Validate path before write per agent path security rule.`

7. Keep TODO comments actionable and scoped:
   - include the exact change needed
   - include the owner subsystem
   - do not leave generic `TODO: refactor`

8. When documenting CI behavior, use the exact workflow filenames `crafted-ci.yml` and `crafted-ci-macos.yml`.

9. Do not document the removed v5.0 docs keyword classifier as active behavior.

10. In Swift UI code, keep accessibility identifier comments adjacent to the element declaration if the identifier contains dynamic context.

11. Use examples in docs only when they match real project naming patterns and file locations.

12. Update documentation in the same change when renaming a subsystem, canonical module, workflow filename, or branch naming component.

## CraftedDevAgent-Specific Patterns

1. Every agent-driven write path must be validated before the write occurs.

2. In agent code, treat all of the following as untrusted paths until validated:
   - user prompts
   - issue content
   - PR metadata
   - branch-derived filenames
   - webhook payload fields
   - generated output targets

3. Use `validate_write_path()` even when the path appears to be repo-relative if any portion originated outside the current function.

4. When generating or repairing CI, only target these workflow filenames:
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

5. Use `ci_workflow.ensure()` as the single entry point for ensuring workflow files and managed `conftest.py` state.

6. Do not hand-roll `conftest.py` bootstrap logic in agent tasks. Let `ci_workflow.ensure()` create or update it.

7. When an agent creates a branch, format it exactly as:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

8. Derive `{subsystem_slug}` from the owning Forge subsystem when possible:
   - `cal`
   - `dtl`
   - `trustflow`
   - `vtz`
   - `trustlock`
   - `mcp`
   - `rewind`
   - `connector`

9. Normalize branch slugs before branch creation:
   - lowercase all text
   - replace spaces with hyphens
   - remove characters outside `[a-z0-9-]`
   - zero-pad PR numbers to 3 digits

10. Do not use PR-title keyword heuristics from the removed v5.0 docs classifier to decide routing, CI, or behavior.

11. When generating macOS UI automation targets, assign `.accessibilityIdentifier()` during element creation rather than in a later modifier chain block elsewhere.

12. For dynamic Swift/macOS lists and cards, include the stable domain ID in the accessibility identifier.

13. In agent-authored tests, assert exact accessibility identifiers for critical interactive controls.

14. In agent-authored tests, mirror `src/` structure exactly under `tests/` and keep test filenames in `test_<module>.py` form.

15. When an agent touches canonical modules such as `src/build_director.py` or `src/ci_workflow.py`, keep changes narrowly scoped to that module’s documented responsibility. Do not move unrelated subsystem logic into them.

16. When an agent introduces a new subsystem module, place it under the correct subsystem directory on first commit rather than creating a temporary miscellaneous module for later cleanup.