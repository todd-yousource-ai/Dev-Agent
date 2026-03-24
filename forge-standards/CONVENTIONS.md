# Code Conventions

## File and Directory Naming

1. **Place ForgeAgent backend Python modules under `src/`.**
   - Use the existing subsystem layout defined by the TRDs.
   - Valid examples:
     - `src/consensus.py`
     - `src/build_director.py`
     - `src/github_tools.py`
     - `src/build_ledger.py`
     - `src/document_store.py`
     - `src/ci_workflow.py`

2. **Use the TRD-defined subsystem directories exactly as named.**
   - Allowed directory names from the architecture standard:
     - `src/cal/`
     - `src/dtl/`
     - `src/trustflow/`
     - `src/vtz/`
     - `src/trustlock/`
     - `src/mcp/`
     - `src/rewind/`
     - `sdk/connector/`

3. **Mirror `src/` exactly under `tests/`.**
   - For every source module or package, create tests in the matching relative path under `tests/<subsystem>/` or equivalent mirrored structure.
   - Example:
     - `src/trustflow/audit_stream.py`
     - `tests/trustflow/audit_stream_test.py` or the project’s matching mirrored test file for that module
   - Do not place tests in flat, unrelated directories when a matching `src/` path exists.

4. **Use lowercase snake_case for all Python file names.**
   - Examples:
     - `build_director.py`
     - `document_store.py`
     - `path_security.py`

5. **Keep workflow file names fixed to the CI names defined in the TRDs.**
   - Ubuntu workflow file: `crafted-ci.yml`
   - macOS Swift workflow file: `crafted-ci-macos.yml`
   - Do not introduce renamed variants for the same workflow purpose.

6. **Do not rename compatibility-sensitive ForgeAgent identifiers.**
   - The branch prefix must remain `forge-agent` exactly.
   - This is mandatory for compatibility.

7. **Name branches using the exact mandatory format.**
   - Required format:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Requirements:
     1. Keep `forge-agent/build` literal.
     2. Use a zero-padded 3-digit PR number segment: `pr-001`, `pr-042`, `pr-317`.
     3. Use lowercase slug values for `{subsystem_slug}` and `{title_slug}`.
   - Example:
     - `forge-agent/build/e17/trustflow/pr-042-add-ledger-heartbeat`

8. **Use TRD-defined names for canonical modules when implementing their documented responsibilities.**
   - Map responsibilities to filenames as follows:
     - `src/consensus.py` → `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`
     - `src/build_director.py` → build pipeline orchestration, confidence gate, PR type routing
     - `src/github_tools.py` → `GitHubTool`, `WebhookReceiver`
     - `src/build_ledger.py` → `BuildLedger`, claim/release, heartbeat
     - `src/document_store.py` → `DocumentStore`, `chunk()`, `embed()`, `retrieve()`
     - `src/ci_workflow.py` → management of `crafted-ci.yml` and related CI generation behavior

## Class and Function Naming

1. **Name Python classes in PascalCase.**
   - Use the TRD canonical names where specified.
   - Examples:
     - `ConsensusEngine`
     - `BuildLedger`
     - `DocumentStore`
     - `GitHubTool`
     - `WebhookReceiver`

2. **Name Python functions and methods in snake_case.**
   - Examples from TRD-aligned behavior:
     - `validate_write_path`
     - `chunk`
     - `embed`
     - `retrieve`
     - `ensure`

3. **Use verbs for side-effecting functions.**
   - Functions that write files, claim resources, release resources, generate workflows, or route builds must use action names.
   - Preferred examples:
     - `claim_job()`
     - `release_job()`
     - `ensure()`
     - `route_pr_type()`
     - `write_workflow()`

4. **Use nouns for stateful service classes.**
   - Examples:
     - `BuildLedger`
     - `DocumentStore`
     - `ConsensusEngine`

5. **Use uppercase snake_case for module-level constants and system prompts.**
   - Examples:
     - `GENERATION_SYSTEM`
     - `SWIFT_GENERATION_SYSTEM`
     - `UI_ADDENDUM`

6. **For Swift accessibility identifiers, use the exact TRD naming shape.**
   - Convention:
     - `{module}-{component}-{role}-{context?}`
   - Apply via `.accessibilityIdentifier()` on all interactive elements.
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

7. **Treat the final identifier segment as contextual only when needed.**
   - Use the optional `{context}` suffix only for disambiguation with runtime IDs or repeated elements.
   - Do not append arbitrary trailing segments when a stable identifier without context is sufficient.

## Error and Exception Patterns

1. **Validate paths before any write operation, without exception.**
   - Every write derived from user input, PR content, webhook payloads, generated filenames, or external configuration must call `validate_write_path()` first.
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

2. **Write only to the validated path returned by `validate_write_path()`.**
   - Do not continue using the original untrusted path variable after validation.
   - Required:
   ```python
   safe_path = validate_write_path(target_path)
   with open(safe_path, "w", encoding="utf-8") as f:
       f.write(content)
   ```

3. **Never inline write calls against raw external path input.**
   - Forbidden pattern:
   ```python
   with open(user_supplied_path, "w") as f:
       ...
   ```

4. **Apply path validation to workflow generation and CI file creation.**
   - This includes writes for:
     - `crafted-ci.yml`
     - `crafted-ci-macos.yml`
     - any generated support files
     - any file emitted by `ci_workflow.ensure()`

5. **Use deterministic safe fallback behavior when traversal is detected.**
   - The TRD states that `validate_write_path()` returns a safe default on traversal.
   - Code must rely on that return value instead of attempting custom traversal repair logic in each caller.

6. **Do not implement parallel custom path-sanitizing helpers when `validate_write_path()` applies.**
   - Use the shared function from `path_security` so all write protection follows one mechanism.

## Import and Module Organisation

1. **Import shared path validation directly from `path_security`.**
   - Required import:
   ```python
   from path_security import validate_write_path
   ```

2. **Keep module responsibilities aligned with the TRD file map.**
   - Do not place `BuildLedger` in `document_store.py` or CI workflow generation in `github_tools.py`.
   - If a responsibility is documented under a canonical file, implement it there.

3. **Keep CI workflow generation logic in `src/ci_workflow.py`.**
   - `ci_workflow.ensure()` is the canonical entry point for ensuring workflow files and the auto-committed `conftest.py` support.

4. **Assume `conftest.py` is managed by `ci_workflow.ensure()` for `src/` imports.**
   - Do not add duplicate manual bootstrap logic elsewhere for the same purpose.
   - If test import support is needed through CI setup, update `ci_workflow.ensure()` rather than scattering alternate setup code.

5. **Group code by subsystem package when implementing TRD-defined domains.**
   - Place subsystem-specific code under its matching package:
     - TrustFlow code in `src/trustflow/`
     - VTZ code in `src/vtz/`
     - MCP policy code in `src/mcp/`
     - Rewind code in `src/rewind/`

6. **Keep SDK connector code under `sdk/connector/` only.**
   - Do not place connector SDK implementation inside backend `src/` packages unless it is backend-only adapter logic.

## Comment and Documentation Rules

1. **Document only behavior that is mandated by TRDs or not obvious from the code shape.**
   - Comments should capture enforced conventions, compatibility constraints, or non-obvious routing logic.

2. **When a compatibility constraint exists, state the exact preserved identifier in comments.**
   - Example: if code references branch formatting, note that `forge-agent` is intentionally retained for compatibility.

3. **When adding docs-related PR detection logic derived from historical behavior, use the v5.0 keyword list only where that compatibility is explicitly required.**
   - The TRD notes `_docs_keywords` existed in v5.0 and was removed in v6.0.
   - Do not add new generic docs keyword heuristics unless implementing legacy-compatible behavior intentionally.

4. **If legacy docs PR classification is implemented, keep the keyword container named clearly and scoped to compatibility behavior.**
   - Example:
   ```python
   LEGACY_DOCS_PR_KEYWORDS = {"naming convention", "glossary", "changelog"}
   ```
   - Do not present it as current universal routing logic when the TRD marks it as removed in v6.0.

5. **For Swift UI code, add accessibility identifiers instead of explanatory comments about interactive elements.**
   - The required convention is executable metadata:
   ```swift
   .accessibilityIdentifier("settings-anthropic-key-test-button")
   ```
   - Do not replace identifier coverage with comments.

## ForgeAgent-Specific Patterns

1. **Use `ci_workflow.ensure()` as the single entry point for CI workflow presence and bootstrap support.**
   - It is responsible for ensuring workflow files and auto-committing `conftest.py` for `src/` import behavior.

2. **Generate both CI workflow variants only under their canonical names.**
   - Ubuntu:
     - `crafted-ci.yml`
   - macOS Swift:
     - `crafted-ci-macos.yml`

3. **When writing CI or support files, validate the destination path before the write.**
   - Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(workflow_path)
   ```

4. **Route build orchestration logic through `src/build_director.py`.**
   - Confidence gates and PR type routing belong in the build director layer, not in unrelated utility modules.

5. **Implement GitHub integration code in `src/github_tools.py`.**
   - Webhook receiving and GitHub tool operations belong there.
   - Do not embed webhook receiver classes inside CI modules or ledger modules.

6. **Implement claim/release/heartbeat state tracking in `src/build_ledger.py`.**
   - Use `BuildLedger` as the stateful coordination point for these operations.

7. **Implement retrieval pipeline storage behavior in `src/document_store.py`.**
   - `DocumentStore` owns `chunk()`, `embed()`, and `retrieve()` responsibilities.

8. **Use the canonical branch naming template in any branch creation automation.**
   - Required template:
     - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`
   - Do not emit alternate prefixes such as `forgeagent/`, `forge_agent/`, or `agent-forge/`.

9. **Apply Swift accessibility identifiers to every interactive element in the macOS application shell.**
   - Buttons, fields, rows, cards, and other interactive controls must each receive a `.accessibilityIdentifier()` using the TRD format.

10. **Build accessibility identifiers from semantic UI roles, not visual labels.**
    - Use `button`, `field`, `row`, `card` as role segments.
    - Include the module and component first.
    - Example:
      - `settings-anthropic-key-field`
      - not `blue-secret-input`

11. **For repeated Swift UI elements, append stable runtime context at the end.**
    - Examples:
      - `navigator-project-row-{projectId}`
      - `stream-gate-yes-button-{gateId}`

12. **Preserve TRD example identifiers exactly when implementing the same controls.**
    - If the UI contains the documented Anthropic key controls or stream gate actions, use the exact identifier strings from the TRD examples.

13. **Do not reintroduce removed v5.0 docs-keyword routing as default behavior.**
    - If legacy handling is needed, isolate it behind explicit compatibility code rather than making it the standard PR classification path.