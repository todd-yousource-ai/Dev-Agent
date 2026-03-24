# Code Conventions

## File and Directory Naming

1. **Use the ForgeAgent backend file names exactly as defined by the TRDs for top-level subsystem modules.**
   - Required mappings:
     - `src/consensus.py` — `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
     - `src/build_director.py` — build pipeline orchestration, confidence gate, PR type routing
     - `src/github_tools.py` — `GitHubTool`, `WebhookReceiver`
     - `src/build_ledger.py` — `BuildLedger`, claim/release, heartbeat
     - `src/document_store.py` — `DocumentStore`, `chunk()`, `embed()`, `retrieve()`
     - `src/ci_workflow.py` — CI workflow generation and maintenance for `crafted-ci.yml` and `crafted-ci-macos.yml`

2. **Place new modules under the TRD-defined subsystem directories only.**
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
   - Example:
     - `src/trustflow/audit_stream.py`
     - `tests/trustflow/test_audit_stream.py`

4. **Name Python source files in `snake_case.py`.**
   - Match the module purpose directly in the file name.
   - Do not use CamelCase, hyphens, or generic names like `utils.py` when the module has a specific TRD-defined role.

5. **Keep CI workflow filenames exact and stable.**
   - Ubuntu workflow file must be named `crafted-ci.yml`.
   - macOS Swift workflow file must be named `crafted-ci-macos.yml`.
   - Do not introduce alternate spellings or environment-specific variants for these canonical workflow files.

6. **Do not rename or remove `conftest.py` when managed by CI setup.**
   - `conftest.py` is auto-committed by `ci_workflow.ensure()` for `src/` import support.
   - Treat it as generated project infrastructure unless the same mechanism updates it.

7. **Use branch names in the mandatory compatibility format.**
   - Format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Example:
     - `forge-agent/build/alex/trustflow/pr-007-audit-stream-heartbeat`

## Class and Function Naming

1. **Name classes in `PascalCase` and align the class name with the owning module’s TRD-defined responsibility.**
   - Required examples:
     - `ConsensusEngine` in `src/consensus.py`
     - `BuildLedger` in `src/build_ledger.py`
     - `DocumentStore` in `src/document_store.py`
     - `GitHubTool` and `WebhookReceiver` in `src/github_tools.py`

2. **Name functions and methods in `snake_case`.**
   - Required examples from TRDs:
     - `chunk()`
     - `embed()`
     - `retrieve()`
     - `ensure()`

3. **Use verbs for actions and nouns for entities.**
   - Good:
     - `claim_build()`, `release_claim()`, `validate_write_path()`
   - Bad:
     - `build_claim_thing()`, `do_retrieve()`

4. **Preserve TRD terminology in names instead of inventing synonyms.**
   - Use `ledger`, `consensus`, `document_store`, `workflow`, `trustflow`, `rewind`, `connector`.
   - Do not replace these with alternatives like `registry`, `agreement`, `docs_db`, or `plugin_api`.

5. **For constants, use `UPPER_SNAKE_CASE`.**
   - Required examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

6. **When creating accessibility identifiers in Swift UI code, use the exact TRD format.**
   - Format:
     - `{module}-{component}-{role}-{context?}`
   - Required examples:
     - `auth-touchid-button`
     - `settings-anthropic-key-field`
     - `settings-anthropic-key-test-button`
     - `navigator-project-row-{projectId}`
     - `stream-gate-yes-button-{gateId}`

7. **Apply `.accessibilityIdentifier()` to every interactive Swift UI element.**
   - Interactive elements include buttons, text fields, toggles, rows with tap actions, and gate controls.
   - Do not leave interactive controls unnamed for UI automation.

## Error and Exception Patterns

1. **Validate paths before any file write, without exception.**
   - Required pattern:
     ```python
     from path_security import validate_write_path

     safe_path = validate_write_path(user_supplied_path)
     ```
   - This rule applies to direct writes, generated files, CI files, logs, exports, caches, and any write target derived from external or user-controlled input.

2. **Always write to the validated path returned by `validate_write_path()`, not the original input path.**
   - Good:
     ```python
     safe_path = validate_write_path(target_path)
     safe_path.write_text(data)
     ```
   - Bad:
     ```python
     validate_write_path(target_path)
     Path(target_path).write_text(data)
     ```

3. **Treat path validation as mandatory even when traversal is “unlikely.”**
   - The TRD states `validate_write_path()` returns a safe default on traversal.
   - Do not replace it with ad hoc checks like string prefix tests.

4. **Centralize write-path validation at the write boundary.**
   - Validate in the method that performs the write, even if callers already validated.
   - This prevents unsafe writes when functions are reused from new call sites.

5. **Use explicit PR classification checks for docs-related pipeline logic when implementing legacy v5.0 behavior.**
   - When supporting the v5.0 keyword-list path, use `_docs_keywords`-style explicit membership checks against normalized title text.
   - Do not infer docs PRs from vague heuristics if implementing the documented v5.0 behavior.

## Import and Module Organisation

1. **Import path validation from the canonical module name only.**
   - Required import:
     ```python
     from path_security import validate_write_path
     ```
   - Do not alias or duplicate this helper in local utility modules.

2. **Keep imports aligned with the `src/` module layout.**
   - Example:
     - `src/build_director.py` should own build orchestration imports.
     - `src/ci_workflow.py` should own CI workflow file generation logic.

3. **Do not move TRD-defined responsibilities into unrelated modules.**
   - Examples:
     - Do not place `BuildLedger` logic in `github_tools.py`.
     - Do not place CI workflow generation in `build_director.py`.
     - Do not place document retrieval logic outside `document_store.py` unless it is a clearly separated subsystem module under `src/`.

4. **Keep test imports compatible with `src/`-based resolution.**
   - Since `conftest.py` is maintained for `src/` imports, write tests that import project modules from the `src`-backed package/module layout rather than duplicating path bootstrapping in each test.

5. **Organize subsystem code under the TRD namespace directories before adding new top-level folders.**
   - Prefer:
     - `src/trustflow/...`
     - `src/vtz/...`
   - Do not create new top-level `src/<name>/` directories unless the subsystem is TRD-backed.

## Comment and Documentation Rules

1. **Document code using TRD terminology exactly.**
   - Use the established subsystem names and concepts:
     - ForgeAgent
     - BuildLedger
     - confidence gate
     - PR type routing
     - TrustFlow
     - Virtual Trust Zone
     - Forge Rewind

2. **Do not add comments that contradict canonical filenames, workflow names, or branch naming formats.**
   - Comments and docs must refer to:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

3. **When documenting accessibility identifiers, include the full identifier format, not abbreviated examples only.**
   - Required format in docs/comments:
     - `{module}-{component}-{role}-{context?}`

4. **Comment write operations when path validation is not immediately adjacent.**
   - If validation occurs earlier in the function, add a brief comment indicating the path has already been normalized by `validate_write_path()`.

5. **Use comments to explain subsystem-specific constraints, not to restate syntax.**
   - Good:
     - `# macOS workflow is kept separate because Swift builds run in crafted-ci-macos.yml`
   - Bad:
     - `# call function`
     - `# write file here`

6. **If legacy docs-PR detection from pipeline v5.0 is implemented, label it as legacy behavior in comments or docstrings.**
   - Make it explicit that `_docs_keywords` handling is tied to v5.0 behavior and was removed in v6.0.

## ForgeAgent-Specific Patterns

1. **Route CI workflow generation through `ci_workflow.ensure()`.**
   - Use `ensure()` as the canonical entry point for creating or updating:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
     - supporting `conftest.py` import scaffolding

2. **Keep Ubuntu and macOS CI concerns separated by workflow file.**
   - Put Ubuntu CI logic in `crafted-ci.yml`.
   - Put macOS Swift CI logic in `crafted-ci-macos.yml`.
   - Do not merge Swift/macOS steps into the Ubuntu workflow file.

3. **Implement build orchestration in `BuildPipeline`/`build_director` using the documented responsibilities only.**
   - `build_director.py` owns:
     - orchestration
     - confidence gate
     - PR type routing

4. **Implement repository interaction logic in `github_tools.py`.**
   - `github_tools.py` owns:
     - `GitHubTool`
     - `WebhookReceiver`
   - Do not spread webhook handling across unrelated modules.

5. **Implement ledger state management in `build_ledger.py`.**
   - `build_ledger.py` owns:
     - claim
     - release
     - heartbeat
   - Keep claim lifecycle logic together in this module.

6. **Implement retrieval pipeline logic in `document_store.py`.**
   - `document_store.py` owns:
     - `chunk()`
     - `embed()`
     - `retrieve()`
   - Keep document ingestion and retrieval behaviors co-located unless split into subordinate modules under the same subsystem.

7. **Use exact subsystem slugs from the directory structure in branch names where possible.**
   - Examples:
     - `trustflow`
     - `vtz`
     - `mcp`
     - `rewind`

8. **For Swift UI gate and navigator elements, include the runtime context token at the end of the accessibility identifier when the TRD example does.**
   - Required pattern examples:
     - `navigator-project-row-{projectId}`
     - `stream-gate-card-{gateId}`
     - `stream-gate-stop-button-{gateId}`

9. **Do not omit the role segment from accessibility identifiers.**
   - Required roles include values such as:
     - `button`
     - `field`
     - `row`
     - `card`

10. **When implementing docs-PR detection compatible with TRD v5.0, normalize the title before keyword checks.**
    - Follow the documented pattern shape:
      - `title_lower = title.lower()`
      - keyword membership check against `_docs_keywords`
    - Do not perform case-sensitive matching for this legacy path.