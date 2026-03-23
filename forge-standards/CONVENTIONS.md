# Code Conventions — Forge Platform

> Authoritative coding standards for the Forge platform and **FullPlatform** subsystem.
> Every rule is numbered, actionable, and enforceable in review.

---

## 1. File and Directory Naming

1.1. Python source files use **snake_case**, no hyphens, no uppercase:
`build_director.py`, `consensus.py`, `ci_workflow.py`.

1.2. Source directories map one-to-one with subsystem abbreviations. Canonical list:

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

1.3. Tests mirror `src/` exactly: a file at `src/cal/session.py` has tests at `tests/cal/test_session.py`. No exceptions.

1.4. CI workflow files use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or duplicate.

1.5. `conftest.py` at the repo root is **auto-committed** by `ci_workflow.ensure()` to guarantee `src/` is importable. Never hand-edit the generated conftest; modify `ci_workflow.py` instead.

1.6. Branch names follow this mandatory pattern:

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

Example: `forge-agent/build/e-042/cal/pr-007-session-timeout-fix`

The prefix `forge-agent` is kept intentionally for compatibility — do not change it.

---

## 2. Class and Function Naming

2.1. Classes use **PascalCase**: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`.

2.2. Public functions and methods use **snake_case**: `claim_build()`, `release_lock()`, `retrieve_chunks()`.

2.3. Private/internal helpers are prefixed with a single underscore: `_rotate_heartbeat()`.

2.4. Constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

2.5. Boolean variables and functions that return `bool` start with `is_`, `has_`, or `should_`:
`is_docs_pr`, `has_valid_signature`, `should_skip_gate`.

2.6. Enum members use **UPPER_SNAKE_CASE** and inherit from `str, enum.Enum` when the value must serialise to JSON.

2.7. SwiftUI accessibility identifiers follow the pattern `{module}-{component}-{role}-{context?}`:

```swift
// ✅ Correct
"auth-touchid-button"
"settings-anthropic-key-field"
"navigator-project-row-\(projectId)"
"stream-gate-yes-button-\(gateId)"

// ❌ Wrong — camelCase, missing module prefix
"touchIdButton"
"gateYes"
```

Set via `.accessibilityIdentifier()` on **every** interactive element. Omit the trailing `{context}` segment only when there is exactly one instance on screen.

---

## 3. Error and Exception Patterns

3.1. Define one base exception per subsystem in the subsystem's `__init__.py`:

```python
# src/cal/__init__.py
class CALError(Exception):
    """Base for all Conversation Abstraction Layer errors."""
```

3.2. Specific exceptions subclass the base and live in the module that raises them:

```python
# src/cal/session.py
from src.cal import CALError

class SessionExpiredError(CALError):
    """Raised when a CAL session exceeds its TTL."""
```

3.3. Never catch bare `Exception` or `BaseException` in production code. Catch the narrowest type. The sole allowed exception is a top-level API boundary handler that logs and re-raises.

3.4. Every `except` block must either **log** the error or **re-raise**. Silent swallowing is forbidden:

```python
# ❌ Forbidden
except ValueError:
    pass

# ✅ Required
except ValueError:
    logger.warning("Invalid value for %s", key)
    raise
```

3.5. Use `raise ... from err` to preserve cause chains.

---

## 4. Import and Module Organisation

4.1. Import order (enforced by `isort` with `profile = black`):

1. Standard library
2. Third-party packages
3. `src.*` / `sdk.*` (local first-party)
4. Relative imports (only within the same subsystem package)

Separate each group with a blank line.

4.2. Never use wildcard imports (`from module import *`).

4.3. Prefer absolute imports (`from src.cal.session import Session`) in tests and cross-subsystem code. Relative imports (`from .session import Session`) are permitted only within the same subsystem package.

4.4. Do not import from a subsystem's internal `_`-prefixed modules outside that subsystem.

---

## 5. Comment and Documentation Rules

5.1. Every public class and public function has a docstring. Use Google-style format:

```python
def claim_build(self, build_id: str, engineer_id: str) -> bool:
    """Atomically claim a build slot in the ledger.

    Args:
        build_id: Unique identifier for the build.
        engineer_id: The engineer requesting the claim.

    Returns:
        True if the claim succeeded, False if already held.

    Raises:
        LedgerConnectionError: If the ledger backend is unreachable.
    """
```

5.2. Inline comments explain **why**, not **what**. If the code needs a "what" comment, refactor it to be self-explanatory.

5.3. TODOs must include an engineer ID or issue number: `# TODO(e-042): replace with async variant after #318`.

5.4. Do not commit commented-out code. Delete it; version control is the archive.

5.5. Module-level docstrings are required for every file in `src/`. State the module's purpose and its primary public symbols.

---

## 6. FullPlatform-Specific Patterns

### 6.1 Path Security — Mandatory Write Validation

Validate paths **before any write** operation. This is non-negotiable:

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
with open(safe_path, "w") as f:
    f.write(content)
```

Any PR that writes to the filesystem without calling `validate_write_path` will be rejected.

### 6.2 Build Pipeline Routing

6.2.1. `BuildPipeline` in `src/build_director.py` owns all orchestration. Gate decisions flow through `ConsensusEngine` — do not duplicate confidence logic elsewhere.

6.2.2. PR type routing (`pr_type`) is determined solely in `build_director.py`. Other modules receive it as a parameter; they do not infer it.

### 6.3 Build Ledger Lifecycle

6.3.1. Every build must call `BuildLedger.claim()` before work and `BuildLedger.release()` in a `finally` block.

6.3.2. Heartbeat calls (`BuildLedger.heartbeat()`) must occur at intervals no greater than half the TTL. Use the constant from `BuildLedger.HEARTBEAT_INTERVAL`.

### 6.4 Document Store Retrieval

6.4.1. Always call `DocumentStore.chunk()` → `DocumentStore.embed