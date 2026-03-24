# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the ForgeAgent TRD corpus. Every rule is mandatory unless explicitly marked *recommended*.

---

## 1. File and Directory Naming

1.1. **Snake-case only** for all Python files and directories: `build_director.py`, `ci_workflow.py`, `document_store.py`.

1.2. **Subsystem directories live under `src/`** and use short, lowercase abbreviations matching the TRD module names exactly:

| Directory | Purpose |
|---|---|
| `src/cal/` | Conversation Abstraction Layer |
| `src/dtl/` | Data Trust Label components |
| `src/trustflow/` | TrustFlow audit stream |
| `src/vtz/` | Virtual Trust Zone enforcement |
| `src/trustlock/` | Cryptographic machine identity (TPM-anchored) |
| `src/mcp/` | MCP Policy Engine |
| `src/rewind/` | Forge Rewind replay engine |
| `sdk/connector/` | Forge Connector SDK |

1.3. **Tests mirror `src/` exactly.** A module at `src/cal/session.py` has its tests at `tests/cal/test_session.py`. No exceptions.

1.4. **Top-level orchestration files** retain flat placement under `src/`:

```
src/consensus.py
src/build_director.py
src/github_tools.py
src/build_ledger.py
src/document_store.py
src/ci_workflow.py
```

1.5. **CI workflow files** are named `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming variants are permitted.

1.6. **`conftest.py`** at repo root is auto-committed by `ci_workflow.ensure()` for `src/` import path setup. Never hand-edit this file; treat it as generated.

---

## 2. Branch Naming

2.1. All ForgeAgent branches **must** follow this exact pattern:

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

- `engineer_id` — lowercase alphanumeric identifier of the authoring agent or engineer.
- `subsystem_slug` — lowercase, hyphen-separated subsystem name (e.g., `trust-flow`, `build-pipeline`).
- `N:03d` — zero-padded three-digit PR sequence number (e.g., `001`, `042`).
- `title_slug` — lowercase, hyphen-separated summary (max 48 characters).

2.2. The prefix `forge-agent` is **intentionally kept** for compatibility. Do not shorten to `fa` or any other alias.

**Example:**

```
forge-agent/build/agent-7/trust-flow/pr-003-add-heartbeat-timeout
```

---

## 3. Class and Function Naming

3.1. **Classes** use PascalCase: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`, `GitHubTool`, `WebhookReceiver`, `BuildLedger`.

3.2. **Functions and methods** use snake_case: `validate_write_path()`, `claim()`, `release()`, `heartbeat()`, `chunk()`, `embed()`, `retrieve()`.

3.3. **Constants** use UPPER_SNAKE_CASE: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

3.4. **Private/internal helpers** are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

3.5. **axIdentifier strings** (SwiftUI accessibility identifiers) follow the pattern `{module}-{component}-{role}-{context?}`:

```
auth-touchid-button
auth-passcode-button
settings-anthropic-key-field
settings-anthropic-key-test-button
navigator-project-row-{projectId}
stream-gate-card-{gateId}
stream-gate-yes-button-{gateId}
stream-gate-skip-button-{gateId}
stream-gate-stop-button-{gateId}
```

- Every segment is lowercase, hyphen-separated.
- The `{context?}` segment is optional but **required** when the element is repeated (e.g., dynamic IDs).
- Set via `.accessibilityIdentifier()` on **all** interactive SwiftUI elements—no exceptions.

---

## 4. Error and Exception Patterns

4.1. **Path security validation is mandatory before any write operation.** Every code path that writes to the filesystem must call `validate_write_path()`:

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
```

4.2. `validate_write_path()` returns a safe default path when traversal is detected. Never catch or suppress this fallback—log it and proceed with the safe path.

4.3. **Never use bare `except:` or `except Exception:` without re-raising or logging.** All caught exceptions must be logged with enough context to diagnose the failure path.

4.4. Define subsystem-specific exception classes in a `_exceptions.py` file within the subsystem directory (e.g., `src/cal/_exceptions.py`). Inherit from a single `ForgeAgentError` base class defined in `src/errors.py`.

```python
# src/errors.py
class ForgeAgentError(Exception):
    """Base for all ForgeAgent exceptions."""

# src/cal/_exceptions.py
from src.errors import ForgeAgentError

class SessionTimeoutError(ForgeAgentError):
    """Raised when a CAL session exceeds its TTL."""
```

4.5. **Fail fast on configuration errors.** Missing API keys, invalid environment variables, or absent TRD references must raise immediately at startup, not at first use.

---

## 5. Import and Module Organisation

5.1. **Import order** (enforced by linter configuration):

```python
# 1. Standard library
import os
import json

# 2. Third-party packages
import httpx

# 3. ForgeAgent src/ modules — always absolute from src/
from src.build_director import BuildPipeline
from src.consensus import ConsensusEngine
from src.path_security import validate_write_path

# 4. Local relative imports (only within the same subsystem package)
from ._exceptions import SessionTimeoutError
```

5.2. **Absolute imports from `src/`** are the default for cross-subsystem references. Relative imports are permitted **only** within the same subsystem package.

5.3. **Circular imports are forbidden.** If two subsystems need each other, extract the shared type or protocol into `src/types.py` or a `_protocols.py` file.

5.4. **No wildcard imports** (`from module import *`) anywhere in the codebase.

5.5. **`conftest.py` at the repo root** (auto-generated by `ci_workflow.ensure()`) adds `src/` to `sys.path`. Test files rely on this—do not add manual `sys.path` hacks in test modules.

---

## 6. Comment and Documentation Rules

6.1. **Module-level docstring required** in every `.py` file. First line states the module's single responsibility. Reference the authoritative TRD by name if applicable:

```python
"""BuildLedger — claim/release and heartbeat tracking for concurrent agent builds.

See: TRD-3-Build-Pipeline-Crafted
"""
```

6.2. **Public functions and classes** require a docstring. Use imperative mood for the summary line:

```python
def claim(build_id: str) -> bool:
    """Claim exclusive ownership of a build slot."""
```

6.3. **Inline comments** explain *why*, not *what*. Never restate the code:

```python
# Safe default prevents directory traversal — see TRD path_security mandate
safe_path = validate_write_path(user_supplied_path)
```

6.4. **TODO/FIXME