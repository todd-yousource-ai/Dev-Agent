# Code Conventions

## File and Directory Naming

1. **Place required root-level files at repository root with no directory prefix.**  
   Commit these files exactly by basename at the repo root:
   - `README.md`
   - `CODEOWNERS`
   - `LICENSE`
   - `.gitignore`
   - `.editorconfig`
   - `VERSION`
   - `Makefile`
   - `pyproject.toml`

2. **Use the mandated CI workflow filenames exactly.**  
   Store CI workflows with these exact names:
   - `crafted-ci.yml` for Ubuntu
   - `crafted-ci-macos.yml` for macOS Swift

3. **Keep Python backend modules in `src/` using snake_case filenames.**  
   Follow the established patterns from the TRDs:
   - `src/consensus.py`
   - `src/build_director.py`

4. **Name Python source files after the primary module responsibility, not after temporary tasks or tickets.**  
   Examples:
   - `consensus.py` for `ConsensusEngine`
   - `build_director.py` for `BuildPipeline`

5. **Do not rename or remove `conftest.py` when it is created by CI bootstrap logic.**  
   `conftest.py` is auto-committed by `ci_workflow.ensure()` to support `src/` imports and must remain compatible with that workflow.

6. **Use the mandatory branch naming format exactly.**  
   All CraftedAgent branches must be named:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

7. **Keep the `forge-agent` prefix unchanged for branch names.**  
   Do not substitute `crafted-agent` or any other variant; compatibility depends on the literal `forge-agent` prefix.

---

## Class and Function Naming

1. **Use PascalCase for Python classes.**  
   Follow the documented class naming style:
   - `ConsensusEngine`
   - `BuildPipeline`

2. **Use snake_case for Python functions and module-level helpers.**  
   Example:
   - `validate_write_path(...)`

3. **Use UPPER_SNAKE_CASE for module-level constants.**  
   Follow the documented constant style:
   - `GENERATION_SYSTEM`
   - `SWIFT_GENERATION_SYSTEM`
   - `UI_ADDENDUM`

4. **Name functions by the action they perform, not by vague intent.**  
   Prefer names like:
   - `validate_write_path`
   - `ensure`
   
   Avoid generic names such as:
   - `handle_data`
   - `process_item`

5. **Name accessibility identifiers using the exact four-part convention when applicable.**  
   Format:
   `{module}-{component}-{role}-{context?}`

6. **Apply `.accessibilityIdentifier()` to all interactive Swift UI elements.**  
   Do not leave buttons, fields, rows, or interactive cards without an accessibility identifier.

7. **Construct Swift accessibility identifiers from stable semantic parts.**  
   Use identifiers like:
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

8. **When including dynamic context in accessibility identifiers, append it as the final dash-separated segment.**  
   Use:
   - `navigator-project-row-{projectId}`
   
   Not:
   - `{projectId}-navigator-project-row`

---

## Error and Exception Patterns

1. **Validate every user-supplied write path before any filesystem write.**  
   This is mandatory for all CraftedAgent write operations.

2. **Use `validate_write_path` from `path_security` for write-path validation.**  
   Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

3. **Perform path validation immediately before the write target is used.**  
   Do not validate early and then mutate or reconstruct the path later.

4. **Write only to the validated path returned by `validate_write_path`.**  
   Never write to the original untrusted path after validation.

5. **Rely on the validator’s safe-default behavior for traversal attempts instead of manually bypassing it.**  
   The TRD specifies that `validate_write_path(...)` returns a safe default on traversal.

6. **Do not implement alternative ad hoc path traversal checks for write operations.**  
   Use the shared validator, not local string checks such as `".." in path"`.

---

## Import and Module Organisation

1. **Import `validate_write_path` directly from `path_security` in any module that performs writes.**  
   Use:
   ```python
   from path_security import validate_write_path
   ```

2. **Keep Python application modules importable from `src/`.**  
   Do not reorganize backend modules in ways that break the `src/` import model supported by `conftest.py`.

3. **Organize modules around subsystem responsibilities reflected in filenames.**  
   Examples from the TRD:
   - `src/consensus.py` contains `ConsensusEngine` and related generation constants
   - `src/build_director.py` contains `BuildPipeline`

4. **Keep closely related classes and constants in the module named for that subsystem responsibility.**  
   For example, keep `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, and `UI_ADDENDUM` in `src/consensus.py`.

5. **Do not split documented canonical modules without updating the subsystem contract.**  
   `src/consensus.py` and `src/build_director.py` are referenced architectural locations and should remain stable unless the architecture documentation is updated.

---

## Comment and Documentation Rules

1. **Document naming conventions in code and docs using the exact terminology from the TRDs.**  
   Use phrases like:
   - `naming convention`
   - `glossary`
   - `changelog`

2. **When implementing docs-related PR detection or classification, match against the documented docs keyword list behavior.**  
   Use lowercase title matching behavior consistent with:
   ```python
   _is_docs_pr = any(kw in title_lower for kw in _docs_keywords) or ...
   ```

3. **Preserve the phrase `naming convention` verbatim in documentation when referring to identifier schemes.**  
   Do not replace it with looser alternatives like `naming style` where behavior depends on keyword matching.

4. **Use code comments to state the required identifier schema directly above the implementation when assigning accessibility identifiers.**  
   Preferred comment form:
   ```swift
   // Convention: {module}-{component}-{role}-{context?}
   ```

5. **Keep examples in documentation aligned with actual enforced names and formats.**  
   If documenting branch names, workflow files, root files, or accessibility identifiers, use the exact strings specified in these conventions.

---

## CraftedAgent-Specific Patterns

1. **Treat path validation as a required precondition for all agent-generated file writes.**  
   Any CraftedAgent code that creates, edits, patches, or regenerates files must validate the destination path first.

2. **Use the canonical safe-write pattern for all write operations.**  
   Required pattern:
   ```python
   from path_security import validate_write_path

   safe_path = validate_write_path(user_supplied_path)
   ```

3. **Preserve compatibility branch naming for all automation and agent-created branches.**  
   CraftedAgent automation must emit branches in this exact form:
   `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

4. **Use zero-padded three-digit PR numbers in branch names.**  
   Examples:
   - `pr-001-fix-import-paths`
   - `pr-027-add-stream-controls`

5. **Use subsystem-specific slugs in branch names.**  
   The `{subsystem_slug}` segment must describe the subsystem being changed, such as:
   - `craftedagent`
   - `build-pipeline`
   - `macos-shell`

6. **For macOS Swift UI in CraftedAgent-owned surfaces, assign accessibility identifiers to every interactive control at creation time.**  
   Do not defer identifier assignment to later refactors or test-only wrappers.

7. **Use semantic, test-stable identifiers for dynamic UI collections.**  
   Include the stable entity identifier in the final segment:
   - `navigator-project-row-{projectId}`
   - `stream-gate-card-{gateId}`

8. **Keep CI integration compatible with the expected workflow inventory.**  
   If CraftedAgent updates CI, it must continue to use `crafted-ci.yml` and `crafted-ci-macos.yml` rather than introducing alternate workflow filenames for the same roles.

9. **Preserve `src/` backend module layout expected by test bootstrap and automation.**  
   CraftedAgent changes must not break the `src/` import approach supported by auto-managed `conftest.py`.

10. **Use documented canonical module ownership when adding functionality.**  
    Add consensus-related functionality to `src/consensus.py` and build-pipeline-related functionality to `src/build_director.py` unless the architecture documentation explicitly changes.