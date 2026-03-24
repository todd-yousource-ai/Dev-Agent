# CONVENTIONS.md — ForgeAgent Subsystem

All rules are derived from the ForgeAgent TRD corpus. Every convention is mandatory unless explicitly marked `(recommended)`.

---

## 1. File and Directory Naming

1.1. Python source files live under `src/` in subsystem directories. Each directory maps to exactly one subsystem abbreviation:

| Directory | Subsystem |
|---|---|
| `src/cal/` | Conversation Abstraction Layer |
| `src/dtl/` | Data Trust Label |
| `src/trustflow/` | TrustFlow audit stream |
| `src/vtz/` | Virtual Trust Zone enforcement |
| `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
| `src/mcp/` | MCP Policy Engine |
| `src/rewind/` | Forge Rewind replay engine |
| `sdk/connector/` | Forge Connector SDK |

1.2. Test directories mirror `src/` exactly: `tests/cal/`, `tests/dtl/`, `tests/trustflow/`, etc. No flattening.

1.3. Top-level orchestration modules keep their canonical names and must not be renamed or split without TRD amendment:

```
src/consensus.py
src/build_director.py
src/github_tools.py
src/build_ledger.py
src/document_store.py
src/ci_workflow.py
```

1.4. Python filenames use `snake_case.py`. No hyphens, no uppercase, no double underscores outside `__init__.py`.

1.5. CI workflow files use these exact names — do not rename:
- `crafted-ci.yml` (Ubuntu runners)
- `crafted-ci-macos.yml` (macOS Swift runners)

1.6. `conftest.py` at repository root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit it; regenerate via the pipeline.

---

## 2. Branch Naming

2.1. All ForgeAgent branches **must** follow this pattern exactly:

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

- `engineer_id`: GitHub username or bot identifier, lowercase.
- `subsystem_slug`: matches a `src/` directory name (e.g., `cal`, `dtl`, `trustflow`).
- `N`: zero-padded to 3 digits (e.g., `001`, `042`).
- `title_slug`: lowercase, hyphen-separated, max 48 characters.

Example: `forge-agent/build/jdoe/trustflow/pr-017-add-heartbeat-timeout`

2.2. The prefix `forge-agent` is kept intentionally for tooling compatibility — do not change to `forge_agent` or any other variant.

---

## 3. Class and Function Naming

3.1. Classes use `PascalCase`. Acronyms of three or more letters are title-cased: `McpPolicyEngine`, not `MCPPolicyEngine`. Two-letter acronyms stay uppercase: `CIWorkflow`.

3.2. Public functions and methods use `snake_case`.

3.3. Private helpers are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

3.4. Constants use `UPPER_SNAKE_CASE` and are defined at module level:

```python
GENERATION_SYSTEM = "..."
SWIFT_GENERATION_SYSTEM = "..."
UI_ADDENDUM = "..."
```

3.5. Internal keyword/data sets that have been deprecated across TRD versions must be removed, not commented out. Reference the TRD version in the removal commit message (e.g., "Removed `_docs_keywords`; deprecated in TRD-3 v6.0").

---

## 4. Accessibility Identifier Naming (axIdentifier)

4.1. Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern:

```
{module}-{component}-{role}-{context?}
```

- All segments are lowercase, hyphen-separated.
- `context` is optional and carries a dynamic id when present.

4.3. Canonical examples — deviate only by extending, not by restructuring:

```
auth-touchid-button
auth-passcode-button
settings-anthropic-key-field
settings-anthropic-key-test-button
settings-anthropic-key-reveal-button
navigator-project-row-{projectId}
stream-gate-card-{gateId}
stream-gate-yes-button-{gateId}
stream-gate-skip-button-{gateId}
stream-gate-stop-button-{gateId}
```

4.4. Never use camelCase, underscores, or dots in an axIdentifier.

---

## 5. Error and Exception Patterns

5.1. Define one custom exception base class per subsystem in `<subsystem>/__init__.py`:

```python
class TrustFlowError(Exception):
    """Base exception for the TrustFlow subsystem."""
```

5.2. Specific errors subclass the base: `class HeartbeatTimeoutError(TrustFlowError)`.

5.3. Never catch bare `Exception` in agent code. Catch the narrowest subsystem exception, or at most `OSError` / `ValueError` for I/O boundaries.

5.4. All exceptions surfaced to the build pipeline must include a machine-readable `code` attribute (string, `UPPER_SNAKE_CASE`) and a human-readable `message`:

```python
class PathTraversalError(VtzError):
    code = "PATH_TRAVERSAL"
    def __init__(self, attempted: str):
        self.message = f"Blocked write to disallowed path: {attempted}"
        super().__init__(self.message)
```

---

## 6. Path Security — Mandatory Pre-Write Validation

6.1. **Every** file-system write in ForgeAgent code must validate the target path first:

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)
```

6.2. `validate_write_path` returns a safe default on directory-traversal attempts; it never raises. The caller must use the returned `safe_path`, not the original input.

6.3. No write call (`open(…, 'w')`, `pathlib.Path.write_text`, `shutil.copy`, etc.) may appear without a preceding `validate_write_path` in the same function scope. CI linting will flag violations.

6.4. Unit tests for any function that writes to disk must include at least one traversal-attempt test case (e.g., `../../etc/passwd`).

---

## 7. Import and Module Organisation

7.1. Imports are grouped in this order, separated by a blank line:

1. Standard library
2. Third-party packages
3. `src/` internal modules (absolute from `src`)

7.2. Never use relative imports (`from . import …`). Always use absolute imports anchored at `src/`:

```python
from consensus import ConsensusEngine
from build_ledger import BuildLedger
```

7.3. Subsystem-internal imports use the subsystem package path:

```python
from trustflow.audit_stream import AuditStream
```

7.4. Circular imports are a build-breaking defect. If two modules need each other, extract the shared type into a `_types.py` inside the subsystem package.

---

## 8. Comment and Documentation Rules

8.1. Every public class and public function has a docstring. Use imperative mood for the first line ("Return the confidence score", not "Returns the confidence score").

8.2. Inline comments explain **why**, not **what**. If a comment restates the code, delete it.

8.3. TRD cross-references use the format `# See TRD-{N}, §{section}`:

```python
# See TRD-3, §5.0 — keyword list removed in v6.0
```

8.4. TODO comments must include the engineer id and a tracking reference: `# TODO