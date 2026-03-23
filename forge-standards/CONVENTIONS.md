# Code Conventions - Forge Platform

## File and Directory Naming

1. Put Python application code under `src/` only. Do not place production Python modules at repository root.

2. Use `snake_case.py` for every Python file name.
   - Valid: `build_director.py`, `document_store.py`
   - Invalid: `BuildDirector.py`, `build-director.py`

3. Name modules after the primary responsibility they implement.
   - `src/consensus.py` for `ConsensusEngine`
   - `src/build_director.py` for build orchestration and PR routing
   - `src/github_tools.py` for GitHub integration
   - `src/build_ledger.py` for claim/release/heartbeat state
   - `src/document_store.py` for chunk/embed/retrieve logic
   - `src/ci_workflow.py` for CI workflow generation and maintenance

4. Use these subsystem directories exactly when adding code in those domains:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — TPM-anchored machine identity
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

5. Mirror `src/` structure exactly under `tests/`.
   - `src/mcp/policy_engine.py` → `tests/mcp/test_policy_engine.py`
   - `src/build_director.py` → `tests/test_build_director.py`

6. Name test files `test_<module>.py` only.

7. Keep CI workflow filenames fixed:
   - `crafted-ci.yml` for Ubuntu workflow
   - `crafted-ci-macos.yml` for macOS/Swift workflow

8. Do not introduce alternate workflow filenames for the same purpose.

9. Treat `conftest.py` as CI-managed when created by `ci_workflow.ensure()` for `src/` imports. Do not replace its import-path behavior with ad hoc test bootstrap files.

10. For generated or compatibility-sensitive names, preserve existing external contracts even if they are awkward. Example: branch names must keep `forge-agent` as the prefix.

11. Create branch names using this exact format:
    ```text
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    Rules:
    - `engineer_id` must be lowercase kebab-case or lowercase alphanumeric identifier used by the system.
    - `subsystem_slug` must be lowercase kebab-case.
    - `N` must be zero-padded to 3 digits.
    - `title_slug` must be lowercase kebab-case.
    - No underscores, spaces, or uppercase letters.

12. Do not use the removed v5.0 docs keyword list pattern for PR classification.
    - Do not add `_docs_keywords = {...}`
    - Do not infer docs PRs from title keyword matching alone

## Class and Function Naming

1. Name Python classes in `PascalCase`.

2. Name functions, methods, variables, and module-level helpers in `snake_case`.

3. Name constants in `UPPER_SNAKE_CASE`.

4. Match exported class names to their owning module’s responsibility.
   - `src/consensus.py` → `ConsensusEngine`
   - `src/build_ledger.py` → `BuildLedger`
   - `src/document_store.py` → `DocumentStore`
   - `src/github_tools.py` → `GitHubTool`, `WebhookReceiver`

5. Use verb-first names for functions that perform actions.
   - `validate_write_path`
   - `ensure_workflow`
   - `claim_build`
   - `release_claim`

6. Use noun-based names for objects that hold state or coordinate behavior.
   - `BuildLedger`
   - `DocumentStore`
   - `ConsensusEngine`

7. For boolean-returning functions and properties, use one of these prefixes:
   - `is_`
   - `has_`
   - `can_`
   - `should_`

8. In Swift UI code, assign an accessibility identifier to every interactive element using this exact structure:
    ```text
    {module}-{component}-{role}-{context?}
    ```

9. Set Swift accessibility identifiers with `.accessibilityIdentifier()` only.

10. Use lowercase kebab-case in every accessibility identifier.

11. Include a stable context suffix when the element is tied to a specific entity instance.
    - `navigator-project-row-{projectId}`
    - `stream-gate-card-{gateId}`
    - `stream-gate-yes-button-{gateId}`

12. Follow these identifier examples exactly when implementing matching UI:
    - `auth-touchid-button`
    - `auth-passcode-button`
    - `settings-anthropic-key-field`
    - `settings-anthropic-key-test-button`
    - `settings-anthropic-key-reveal-button`

13. Do not abbreviate `button`, `field`, `row`, or `card` inside accessibility identifiers.

14. Do not use generated UUIDs as accessibility identifiers when a deterministic business identifier is available.

## Error and Exception Patterns

1. Validate every user-supplied or externally-derived write path before any filesystem write.

2. Use `validate_write_path` from `path_security` for all write destinations derived from input, task payloads, config, branch metadata, PR metadata, or webhook data.

3. Apply path validation immediately before the write target is used, not only at input parsing time.

4. Use this exact pattern for write-path validation:
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```

5. Write only to `safe_path` returned by `validate_write_path`. Do not continue using the original path variable for file operations.

6. If a function receives a path parameter and performs a write, rename the validated result to `safe_path` or another explicit validated name before opening, creating, replacing, or deleting files.

7. Raise specific exceptions instead of generic `Exception`.
   - Prefer `ValueError`, `KeyError`, `FileNotFoundError`, `RuntimeError`, or a subsystem-specific custom exception.

8. When wrapping exceptions, preserve the original exception with `raise ... from exc`.

9. Include actionable context in exception messages:
   - include subsystem
   - include operation
   - include stable identifier
   - do not include secrets or tokens

10. Do not swallow filesystem, CI generation, GitHub API, or ledger coordination errors silently.

11. Return structured failure data only at system boundaries that require it; inside modules, prefer raising exceptions over returning ambiguous tuples like `(False, None)`.

12. When fallback behavior is expected by contract, make the fallback explicit in code and tests. Example: `validate_write_path()` returning a safe default on traversal must be covered by tests for that caller.

## Import and Module Organisation

1. Group imports in this order:
   1. Python standard library
   2. Third-party packages
   3. Local project imports

2. Separate each import group with a single blank line.

3. Import modules from `src/` using package/module imports compatible with the repository’s `conftest.py` and CI setup. Do not add one-off `sys.path` mutations inside tests or production modules.

4. Import only the symbols actually used in the file.

5. Do not use wildcard imports.

6. Keep one primary responsibility per module. If a file starts handling unrelated concerns, split it.

7. Place tightly related helper functions in the same module only when they are private implementation details of that module.

8. Prefix private helpers and internal constants with `_`.

9. Keep external integration code isolated in clearly named modules, such as `github_tools.py` or `ci_workflow.py`, instead of scattering API calls across orchestration modules.

10. Keep orchestration logic in coordinator modules and pure transformation logic in helper modules.
    - Example: `build_director.py` should coordinate routing and confidence gates
    - Example: text chunking or embedding transforms belong in `document_store.py` or dedicated helper modules

11. Do not duplicate workflow file generation logic outside `src/ci_workflow.py`.

12. When a module owns a compatibility-sensitive artifact, centralize that artifact’s creation there.
    - CI workflows in `ci_workflow.py`
    - import bootstrap handling via `ci_workflow.ensure()` and managed `conftest.py`

## Comment and Documentation Rules

1. Write comments only when they add information not obvious from the code.

2. Use comments to document:
   - compatibility constraints
   - security constraints
   - external contracts
   - non-obvious fallback behavior
   - rationale for preserving legacy naming

3. Do not restate the next line of code in comments.

4. When documenting compatibility-sensitive behavior, name the exact contract being preserved.
   - Example: branch prefix remains `forge-agent` for compatibility

5. In docstrings and comments, reference exact filenames and identifiers when behavior depends on them.
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`
   - `ci_workflow.ensure()`
   - `validate_write_path`

6. If a module enforces a TRD-defined convention, include a short docstring or comment that cites the enforced format directly.
   - Example: accessibility identifier format `{module}-{component}-{role}-{context?}`

7. Keep docstrings imperative and specific.
   - Good: `Validate and normalize a write target before creating the workflow file.`
   - Bad: `This function is used to handle paths.`

8. Do not document removed behavior as active behavior.
   - Do not describe v5.0 docs keyword PR detection as current logic.

9. When adding examples in documentation, use project-realistic names from Forge and CraftedDevAgent rather than placeholder domains.

## CraftedDevAgent-Specific Patterns

1. Any CraftedDevAgent code that creates, updates, or overwrites files must validate the destination path before the write.

2. In agent task handlers, treat all incoming paths as untrusted, including:
   - repo-relative paths
   - artifact paths
   - patch output paths
   - generated workflow paths
   - test fixture paths from payloads

3. For any write flow, structure code in this order:
   1. derive candidate path
   2. call `validate_write_path(...)`
   3. assign validated result to `safe_path`
   4. write using `safe_path`
   5. report or return `safe_path` if needed

4. When creating branches for agent work, generate the name once and pass the exact string through all Git and GitHub operations without local reformats.

5. Branch creation code must enforce the mandatory branch format:
    ```text
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```

6. Reject or normalize branch-name inputs before branch creation if they contain uppercase letters, spaces, or underscores.

7. If a subsystem slug maps to a source directory, keep naming aligned.
   - Branch slug `mcp-policy` should correspond to code in `src/mcp/` or that subsystem’s documented module area.

8. Use `ci_workflow.ensure()` as the single entry point for making sure CI workflow files and import bootstrap files exist.

9. Do not hand-edit generated CI workflow content in unrelated modules. Update generation logic in `src/ci_workflow.py` instead.

10. When ensuring CI support for Python tests, preserve the auto-committed `conftest.py` behavior required for `src/` imports.

11. When ensuring CI support for Swift/macOS work, write to `crafted-ci-macos.yml`; do not overload `crafted-ci.yml` with macOS-specific Swift steps.

12. In macOS Swift UI produced by CraftedDevAgent, add `.accessibilityIdentifier()` on every interactive control during initial implementation, not as a later QA pass.

13. For repeated interactive Swift UI elements, include the stable entity identifier in the accessibility identifier.
    - rows, cards, and per-item action buttons must carry `{projectId}`, `{gateId}`, or equivalent stable IDs

14. Do not use title-based keyword heuristics to decide whether an agent PR is “docs-only”. If PR type routing is needed, implement it from explicit metadata or current build-director rules.

15. Keep CraftedDevAgent compatibility behavior local and explicit. If preserving a legacy name, filename, or branch prefix, add a targeted comment near the code that enforces it.

16. Add tests for every convention-enforcing helper introduced in CraftedDevAgent code:
    - branch name builders
    - path validation wrappers
    - accessibility identifier formatters
    - CI workflow ensure logic

17. When testing convention helpers, include at least one invalid-input case and assert the enforced normalized or rejected result.

18. Never bypass `validate_write_path` in tests “for convenience” when the production path is user-controlled. Test the real validation flow instead.