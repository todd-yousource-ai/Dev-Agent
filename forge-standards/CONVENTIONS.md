# CONVENTIONS.md — Crafted Subsystem

All rules below are derived from the Crafted TRD documents and Forge architecture standards. Every rule is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1.1. Python source files live under `src/` with **snake_case** names: `consensus.py`, `build_director.py`, `github_tools.py`, `build_ledger.py`, `document_store.py`, `ci_workflow.py`.

1.2. Subsystem directories under `src/` use **short lowercase abbreviations** matching their TRD names exactly:
```
src/cal/           — Conversation Abstraction Layer
src/dtl/           — Data Trust Label
src/trustflow/     — TrustFlow audit stream
src/vtz/           — Virtual Trust Zone enforcement
src/trustlock/     — Cryptographic machine identity
src/mcp/           — MCP Policy Engine
src/rewind/        — Forge Rewind replay engine
sdk/connector/     — Forge Connector SDK
```

1.3. Test files mirror `src/` structure exactly under `tests/<subsystem>/`. A test for `src/build_ledger.py` lives at `tests/build_ledger/test_build_ledger.py` (or `tests/test_build_ledger.py` for top-level modules).

1.4. CI workflow files use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is permitted for Crafted CI workflows.

1.5. `conftest.py` at the repository root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Do not manually edit or delete this file.

1.6. Swift source files use **PascalCase** matching the primary type they contain: `StreamGateCard.swift`, `NavigatorProjectRow.swift`.

---

## 2. Branch Naming

2.1. All agent-created branches **must** follow this exact pattern:
```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

2.2. `{engineer_id}` is the numeric or alphanumeric engineer identifier. `{subsystem_slug}` is the lowercase hyphenated subsystem name (e.g., `crafted`, `trustflow`). `{N:03d}` is zero-padded to three digits. `{title_slug}` is lowercase-hyphenated, max 48 characters, no special characters beyond hyphens.

2.3. The prefix `forge-agent` is kept intentionally for CI compatibility. Do not rename it to any other prefix.

---

## 3. Class and Function Naming

3.1. Python classes use **PascalCase**: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`, `BuildLedger`, `GitHubTool`, `WebhookReceiver`.

3.2. Python functions and methods use **snake_case**: `validate_write_path()`, `claim_release()`, `ensure()`.

3.3. Module-level constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

3.4. Private/internal module-level variables use a single leading underscore and **lower_snake_case**: `_docs_keywords`, `_is_docs_pr`.

3.5. Swift types use **PascalCase**. Swift properties and methods use **camelCase**. Swift constants use **camelCase** (not `UPPER_SNAKE_CASE`).

---

## 4. Accessibility Identifier Convention (axIdentifier)

4.1. Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern:
```
{module}-{component}-{role}-{context?}
```
All segments are **lowercase**, separated by **hyphens**.

4.3. `{context}` is optional and used when the element is repeated or dynamic (e.g., row IDs, gate IDs).

4.4. Canonical examples — deviate from this style and the PR will be rejected:
```
"auth-touchid-button"
"auth-passcode-button"
"settings-anthropic-key-field"
"settings-anthropic-key-test-button"
"settings-anthropic-key-reveal-button"
"navigator-project-row-{projectId}"
"stream-gate-card-{gateId}"
"stream-gate-yes-button-{gateId}"
"stream-gate-skip-button-{gateId}"
"stream-gate-stop-button-{gateId}"
```

4.5. Dynamic segments (e.g., `{projectId}`, `{gateId}`) are interpolated at runtime using the entity's stable identifier. Never use array indices.

---

## 5. Path Security and Write Validation

5.1. **Every** file-write operation must validate the target path before writing. No exceptions.

5.2. Use the project's `path_security` module:
```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)
```

5.3. `validate_write_path` returns a safe default path on directory-traversal attempts. Callers must use the returned `safe_path`, never the original input.

5.4. Never construct write paths by string concatenation with user-supplied input. Always route through `validate_write_path`.

---

## 6. Error and Exception Patterns

6.1. Define custom exceptions per subsystem in a dedicated `exceptions.py` file within the subsystem directory (e.g., `src/cal/exceptions.py`).

6.2. Custom exception classes inherit from a single subsystem base exception, which itself inherits from `Exception`:
```python
class CraftedError(Exception):
    """Base for all Crafted subsystem errors."""

class BuildLedgerClaimError(CraftedError):
    """Raised when a ledger claim cannot be acquired."""
```

6.3. Never catch bare `except:` or `except Exception:` at module boundaries without re-raising or logging. Swallowed exceptions are forbidden.

6.4. Path-security violations must raise (or log-and-substitute) immediately — never silently proceed with the unsanitised path.

---

## 7. Import and Module Organisation

7.1. Imports are grouped in this order, separated by a blank line:
   1. Standard library
   2. Third-party packages
   3. Forge/Crafted internal modules

7.2. Within each group, imports are **alphabetically sorted**.

7.3. Use absolute imports rooted at `src/`:
```python
from build_ledger import BuildLedger
from consensus import ConsensusEngine, GENERATION_SYSTEM
```

7.4. Relative imports are permitted **only** within a subsystem package (e.g., inside `src/cal/`):
```python
from .exceptions import CALError
```

7.5. Circular imports are forbidden. If two modules need each other, extract the shared type into a third module.

---

## 8. Comment and Documentation Rules

8.1. Every public class and public function has a docstring. Use triple double-quotes. First line is a single imperative sentence. Additional paragraphs follow after a blank line.
```python
def claim_release(build_id: str) -> bool:
    """Release the ledger claim for the given build.

    Returns True if the claim was successfully released, False if it
    was already released or never existed.
    """
```

8.2. Inline comments explain **why**, not **what**. If the code needs a "what" comment, refactor the code to be self-explanatory.

8.3. `# TODO` comments must include an engineer ID or issue number: `# TODO(eng-042): migrate to async`.

8.4. Do not leave commented-out code in committed files. Use version control history instead.

8.5. Swift documentation uses `///` doc-comments on all public types and methods.

---

## 9. Crafted-Specific Patterns

9.1. **Consensus system prompts** (`GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`,