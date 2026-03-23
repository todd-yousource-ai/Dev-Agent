# Code Conventions - Forge Platform

## File and Directory Naming

1. Put Python application code under `src/` only. Do not add production Python modules at repository root.

2. Use `snake_case.py` for every Python file name.
   - Correct: `src/build_director.py`
   - Incorrect: `src/BuildDirector.py`, `src/build-director.py`

3. Use the established subsystem directories exactly as named:
   - `src/cal/`
   - `src/dtl/`
   - `src/trustflow/`
   - `src/vtz/`
   - `src/trustlock/`
   - `src/mcp/`
   - `src/rewind/`
   - `sdk/connector/`

4. Place tests under `tests/<subsystem>/` and mirror the `src/` structure exactly.
   - If code is in `src/mcp/policy_engine.py`, the test file must be in `tests/mcp/test_policy_engine.py`.

5. Keep canonical platform modules at their defined file paths. Do not rename or duplicate them:
   - `src/consensus.py`
   - `src/build_director.py`
   - `src/github_tools.py`
   - `src/build_ledger.py`
   - `src/document_store.py`
   - `src/ci_workflow.py`

6. Keep CI workflow file names exactly:
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`

7. Do not create alternate CI workflow names such as `ci.yml`, `macos.yml`, or `github-actions.yml` for the crafted pipeline.

8. Treat `conftest.py` as CI-managed when added by `ci_workflow.ensure()` for `src/` imports. Do not hand-edit generated import-bootstrapping content unless the generator is being changed in the same PR.

9. Name new directories in lowercase `snake_case`, except for externally mandated names already defined by the project.

10. Name non-test support files by function, not by ticket or temporary purpose.
    - Correct: `src/trustflow/audit_writer.py`
    - Incorrect: `src/trustflow/fix_final_v2.py`

11. When writing any file from code using a path that can be influenced externally, validate the path before the write.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    ```
    Apply this before opening, overwriting, appending, copying, moving, or generating files.

12. Never write directly to a user-supplied path string without `validate_write_path(...)`, even for temp files, exported reports, workflow files, or generated docs.

13. Branch names must use this exact format:
    `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

14. Keep `{subsystem_slug}` aligned with the actual subsystem directory or logical component name, using lowercase hyphenated slug form in the branch even if the code directory uses underscores.

---

## Class and Function Naming

1. Name classes in `PascalCase`.
   - Correct: `ConsensusEngine`, `BuildPipeline`, `GitHubTool`, `BuildLedger`, `DocumentStore`

2. Name functions and methods in `snake_case`.
   - Correct: `claim_build()`, `release_lock()`, `retrieve_chunks()`

3. Name module-level constants in `UPPER_SNAKE_CASE`.
   - Correct: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`

4. Prefix private helpers with a single leading underscore.
   - Correct: `_load_policy()`
   - Incorrect: `loadPolicyInternal()`, `__load_policy()` unless name mangling is specifically required

5. Name boolean-returning functions and variables as predicates or state flags.
   - Preferred: `is_docs_pr`, `has_claim`, `should_retry`, `can_write`

6. Preserve the existing docs-PR detector naming pattern for compatibility when implementing similar logic.
   - Use names like `_docs_keywords` for keyword sets
   - Use names like `_is_docs_pr(...)` or `is_docs_pr(...)` for detectors

7. Use noun names for stateful service classes and verb names for action functions.
   - Class: `WebhookReceiver`
   - Function: `receive_webhook()`

8. Name exception classes with the `Error` suffix.
   - Correct: `BuildLedgerError`, `PathValidationError`

9. Name test files as `test_<module>.py`.

10. Name test functions as `test_<behavior>()`.
    - Correct: `test_validate_write_path_blocks_traversal()`

11. For Swift/macOS accessibility identifiers, use this exact shape:
    `{module}-{component}-{role}-{context?}`

12. Set `.accessibilityIdentifier(...)` on all interactive SwiftUI/AppKit/UIKit elements.

13. Build accessibility identifiers from stable domain tokens, not user-facing text.
    - Correct: `"settings-anthropic-key-test-button"`
    - Incorrect: `"Test API Key Button"`

14. Include entity IDs in accessibility identifiers where row/card/button instances repeat in a list.
    - Correct: `"navigator-project-row-\(projectId)"`
    - Correct: `"stream-gate-yes-button-\(gateId)"`

15. Use the role token consistently in accessibility identifiers:
    - `button`
    - `field`
    - `row`
    - `card`

16. Do not abbreviate accessibility identifier segments unless the abbreviation is already a subsystem term.

---

## Error and Exception Patterns

1. Raise specific exceptions. Do not use bare `Exception` for domain failures.

2. Define domain exceptions in the module that owns the domain behavior unless multiple modules share them; in that case, place them in a dedicated subsystem exceptions module.

3. Include actionable context in every raised exception message.
   - Correct: `raise BuildLedgerError(f"claim already held for build_id={build_id}")`
   - Incorrect: `raise BuildLedgerError("ledger failed")`

4. When rejecting or repairing a file write target, validate first with `validate_write_path(...)` and operate only on the returned safe path.

5. Do not catch path validation issues and then continue using the original path.

6. Convert external library errors into Forge-domain exceptions at module boundaries where the rest of the subsystem expects domain semantics.

7. In webhook, build, CI, and ledger flows, log or raise with the identifiers needed for traceability:
   - `build_id`
   - `pr_number`
   - `workflow_name`
   - `job_id`
   - `project_id`
   Include whichever identifiers are available in that code path.

8. Re-raise exceptions with preserved cause when wrapping:
   ```python
   try:
       ...
   except SomeLibraryError as exc:
       raise BuildPipelineError(f"failed to enqueue workflow for pr_number={pr_number}") from exc
   ```

9. Do not silently swallow exceptions in orchestration code such as `build_director`, `ci_workflow`, `github_tools`, or `build_ledger`.

10. Return structured failure values only when the API explicitly uses result objects; otherwise, raise exceptions.

11. In tests, assert the exception type and a meaningful fragment of the message.

---

## Import and Module Organisation

1. Group imports in this order:
   1. Python standard library
   2. Third-party packages
   3. Local project imports from `src` packages/modules

2. Separate each import group with one blank line.

3. Prefer absolute imports from `src` modules/packages over relative imports when importing across subsystem boundaries.
   - Preferred: `from src.build_ledger import BuildLedger`
   - Avoid: `from ..build_ledger import BuildLedger`

4. Use relative imports only for tightly coupled modules within the same package when absolute imports would reduce clarity.

5. Import concrete symbols when a module uses only a small, explicit surface.
   - Preferred: `from path_security import validate_write_path`

6. Do not use wildcard imports.

7. Keep one import per line except when importing multiple symbols from the same module and the line remains readable.

8. If a module’s main purpose maps to one primary class, keep that class in the same-named file when possible.
   - `src/document_store.py` contains `DocumentStore`

9. Keep orchestration logic in orchestration modules and do not move it into utility modules.
   - `src/build_director.py` owns build pipeline orchestration
   - `src/ci_workflow.py` owns crafted CI workflow generation/ensuring

10. Do not place GitHub webhook receiver logic outside `src/github_tools.py` unless the subsystem is being intentionally refactored in the same change.

11. Keep generated workflow file handling in `src/ci_workflow.py`, including logic related to `crafted-ci.yml` and `crafted-ci-macos.yml`.

12. Keep constants near the top of the module, below imports.

13. Order module contents as:
   1. Imports
   2. Constants
   3. Exceptions
   4. Data structures/types
   5. Main classes/functions
   6. Private helpers

14. Avoid circular imports by extracting shared types/helpers into a lower-level subsystem module rather than importing orchestration modules into each other.

---

## Comment and Documentation Rules

1. Write comments only when they convey behavior, constraints, or rationale that is not obvious from the code.

2. Do not restate the code in comments.
   - Avoid:
     ```python
     # Increment counter
     counter += 1
     ```

3. When a rule is compatibility-driven, state the compatibility target explicitly in the comment.
   - Example: branch naming retained as `forge-agent` for compatibility

4. Document any write-path security boundary directly above the write logic if the source path can be externally influenced.
   - Example:
     ```python
     # Validate externally influenced path before write to prevent traversal.
     safe_path = validate_write_path(target_path)
     ```

5. When code depends on CI-managed side effects, note the source of truth.
   - Example: `conftest.py` is auto-committed by `ci_workflow.ensure()`

6. Keep docstrings imperative or descriptive and specific.
   - Good: `"""Generate crafted CI workflow files for the repository."""`
   - Bad: `"""This function does stuff."""`

7. For public classes and functions, document inputs and outputs when they are not obvious from type signatures.

8. Include exact required external filenames and identifier formats in docs/comments when the code depends on them.
   - `crafted-ci.yml`
   - `crafted-ci-macos.yml`
   - `forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

9. When implementing docs-PR detection logic derived from legacy behavior, note that the v5.0 keyword list was removed in v6.0 if that distinction affects behavior.

10. Do not leave TODO comments without an owner or a concrete trigger condition.
    - Required form: `TODO(<owner>): <action> when <condition>`

11. Keep markdown docs and code examples aligned with actual file names and module names in the repository.

---

## FullPlatform-Specific Patterns

1. In FullPlatform code that routes builds, keep PR-type routing logic in `src/build_director.py` or a directly associated module imported by it.

2. Keep confidence gate logic with build pipeline orchestration, not in unrelated utility modules.

3. Put GitHub integration entry points in `src/github_tools.py`, including tool wrappers and webhook receiver behavior.

4. Put claim/release/heartbeat ledger behavior in `src/build_ledger.py`.

5. Put chunk/embed/retrieve document operations in `src/document_store.py`.

6. Put workflow creation/ensuring behavior for `crafted-ci.yml` and `crafted-ci-macos.yml` in `src/ci_workflow.py`.

7. If FullPlatform code writes workflow files, repository support files, generated tests, or docs from externally influenced paths, call `validate_write_path(...)` immediately before the write target is resolved.

8. For CI bootstrap behavior, assume `conftest.py` may be auto-committed by `ci_workflow.ensure()` to make `src/` imports work. Code that verifies CI artifacts must treat that file as expected output, not stray noise.

9. When adding docs-PR classification behavior for legacy compatibility, keep the keyword set in a private constant such as `_docs_keywords` and the detector in a predicate such as `_is_docs_pr(...)`.

10. If implementing legacy docs-PR keyword matching, perform matching against normalized lowercase text.
    - Pattern:
      ```python
      title_lower = title.lower()
      is_docs = any(kw in title_lower for kw in _docs_keywords)
      ```

11. In Swift/macOS FullPlatform UI, every interactive control must set `.accessibilityIdentifier(...)` using the mandated token order.
    - Required examples:
      - `"auth-touchid-button"`
      - `"auth-passcode-button"`
      - `"settings-anthropic-key-field"`
      - `"settings-anthropic-key-test-button"`
      - `"settings-anthropic-key-reveal-button"`

12. In navigator and stream/gate UI lists, append the stable entity identifier at the end of the accessibility identifier.
    - Required patterns:
      - `"navigator-project-row-{projectId}"`
      - `"stream-gate-card-{gateId}"`
      - `"stream-gate-yes-button-{gateId}"`
      - `"stream-gate-skip-button-{gateId}"`
      - `"stream-gate-stop-button-{gateId}"`

13. Do not omit the final entity ID segment from repeated interactive elements in Swift/macOS views.

14. When generating or checking branch names from automation, emit exactly the mandatory branch format and zero-pad PR numbers to 3 digits.
    - Example: `pr-007-add-ledger-heartbeat`

15. When FullPlatform automation creates files on behalf of an agent, validate destination paths before any write and persist only to the validated path returned by `validate_write_path(...)`.