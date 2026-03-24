# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the project TRDs and architecture context documents. Every rule is mandatory unless explicitly marked otherwise.

---

## 1. File and Directory Naming

1.1. Python source files use `snake_case.py` exclusively. No hyphens, no camelCase.

1.2. Source directories map one-to-one to subsystem abbreviations defined in the architecture context:

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

1.3. Test directories mirror `src/` structure exactly: a file at `src/vtz/enforcer.py` has its tests at `tests/vtz/test_enforcer.py`. No exceptions.

1.4. CI workflow files are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename, alias, or create alternative workflow files.

1.5. The file `conftest.py` at project root is auto-committed by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit this file; regenerate it through the CI workflow tooling.

1.6. Top-level orchestration files retain their canonical names without abbreviation:

```
src/consensus.py
src/build_director.py
src/github_tools.py
src/build_ledger.py
src/document_store.py
src/ci_workflow.py
```

---

## 2. Branch Naming

2.1. All ForgeAgent branches **must** follow this pattern exactly:

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

- `engineer_id` — lowercase alphanumeric identifier of the engineer or agent instance.
- `subsystem_slug` — lowercase, hyphen-separated subsystem name (e.g., `trust-flow`, `build-pipeline`).
- `N` — zero-padded to three digits (e.g., `001`, `042`).
- `title_slug` — lowercase, hyphen-separated summary, max 48 characters.

2.2. The prefix `forge-agent` is intentional and kept for compatibility. Do not shorten to `fa` or any other alias.

**Example:**
```
forge-agent/build/agent-7/trust-flow/pr-012-add-heartbeat-timeout
```

---

## 3. Class and Function Naming

3.1. Classes use `PascalCase`. Subsystem prefix is **not** repeated in the class name when the module path already provides context:

```python
# src/vtz/enforcer.py
class Enforcer:       # CORRECT — module path gives context
class VTZEnforcer:    # WRONG — redundant prefix
```

3.2. Functions and methods use `snake_case`. Verb-first naming is required for all public functions:

```python
def validate_write_path(path: str) -> Path: ...
def claim_build(build_id: str) -> bool: ...
def release_lock(lock_id: str) -> None: ...
```

3.3. Private helpers are prefixed with a single underscore. Double underscores are reserved for name-mangling only when subclass collision is a demonstrated risk.

3.4. Constants use `UPPER_SNAKE_CASE` and are defined at module level:

```python
GENERATION_SYSTEM = "..."
SWIFT_GENERATION_SYSTEM = "..."
UI_ADDENDUM = "..."
```

---

## 4. Accessibility Identifier Naming (macOS / Swift UI)

4.1. All interactive SwiftUI elements **must** have an `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern `{module}-{component}-{role}-{context?}`:

- Each segment is lowercase, hyphen-separated.
- `context` is optional and appended only when disambiguation is needed (e.g., a dynamic ID).

4.3. Canonical examples (exhaustive reference list):

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

4.4. Dynamic suffixes (e.g., `{projectId}`, `{gateId}`) use the entity's stable identifier, never an array index.

---

## 5. Error and Exception Patterns

5.1. Define one custom exception base class per subsystem module:

```python
# src/vtz/exceptions.py
class VTZError(Exception):
    """Base exception for the Virtual Trust Zone subsystem."""
```

5.2. All subsystem-specific exceptions inherit from the subsystem base, not from bare `Exception`:

```python
class PathTraversalError(VTZError): ...
class LockContentionError(BuildLedgerError): ...
```

5.3. Never catch bare `Exception` or `BaseException` in production code paths. Catch the narrowest applicable type.

5.4. Every `except` block must either re-raise, log at `WARNING` or above, or return a well-defined error object. Silent swallowing (`except: pass`) is forbidden.

5.5. Path validation errors must raise `PathTraversalError` (or equivalent) **before** any I/O occurs. See Rule 8.1.

---

## 6. Import and Module Organisation

6.1. Imports are grouped in this order, separated by a single blank line:

```python
# 1. Standard library
import os
from pathlib import Path

# 2. Third-party packages
import httpx

# 3. Project-internal (absolute from src/)
from src.build_ledger import BuildLedger
from src.vtz.enforcer import Enforcer
```

6.2. Relative imports are forbidden. Always use absolute imports rooted at `src/`.

6.3. Do not use wildcard imports (`from module import *`) anywhere.

6.4. Circular imports are a build-blocking defect. If module A needs a type from module B and vice versa, extract the shared type into a dedicated `types.py` inside the subsystem package.

---

## 7. Comment and Documentation Rules

7.1. Every public class and public function has a docstring. Use imperative mood in the summary line:

```python
def claim_build(build_id: str) -> bool:
    """Claim exclusive ownership of a build. Return True on success."""
```

7.2. Inline comments explain **why**, not **what**. If a comment restates the code, delete it.

7.3. TODO comments must include an engineer ID or issue reference:

```python
# TODO(agent-7): Replace polling with webhook — see PR-034
```

7.4. Module-level docstrings are required and must state the module's single responsibility in one sentence.

7.5. Do not use keyword-tagged metadata comments (the `_docs_keywords` pattern from Build Pipeline v5.0 was removed in v6.0 and must not be reintroduced).

---

## 8. ForgeAgent-Specific Patterns

### 8.1. Path Security — Validate Before Any Write

Every code path that writes to disk **must** call `validate_write_path` before performing the write. This is non-negotiable.

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
with open(safe_path, "w") as f:
    f.write(content