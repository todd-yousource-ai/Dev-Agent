# CONVENTIONS.md — ForgeAgent Subsystem

> Authoritative coding conventions derived from ForgeAgent TRD documents.
> Every rule is mandatory unless explicitly marked **(advisory)**.

---

## 1. File and Directory Naming

1.1. Python source files use **snake_case**, no hyphens, no uppercase.
Good: `build_director.py`, `ci_workflow.py`. Bad: `buildDirector.py`, `ci-workflow.py`.

1.2. Source files live under `src/` in subsystem directories that match the canonical list exactly:

```
src/cal/           # Conversation Abstraction Layer
src/dtl/           # Data Trust Label
src/trustflow/     # TrustFlow audit stream
src/vtz/           # Virtual Trust Zone enforcement
src/trustlock/     # Cryptographic machine identity (TPM-anchored)
src/mcp/           # MCP Policy Engine
src/rewind/        # Forge Rewind replay engine
sdk/connector/     # Forge Connector SDK
```

1.3. Top-level orchestration files remain directly under `src/`:

| File | Responsibility |
|---|---|
| `src/consensus.py` | ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM+UI_ADDENDUM |
| `src/build_director.py` | BuildPipeline orchestration, confidence gate, pr_type routing |
| `src/github_tools.py` | GitHubTool, WebhookReceiver |
| `src/build_ledger.py` | BuildLedger, claim/release, heartbeat |
| `src/document_store.py` | DocumentStore, chunk(), embed(), retrieve() |
| `src/ci_workflow.py` | CI YAML generation and conftest management |

1.4. Tests **mirror `src/` structure exactly**: a file at `src/vtz/enforce.py` has tests at `tests/vtz/test_enforce.py`.

1.5. CI workflow files use the fixed names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). Do not rename or add variant copies.

1.6. `conftest.py` at the repository root is **auto-committed** by `ci_workflow.ensure()` to guarantee `src/` is importable. Never hand-edit this file.

---

## 2. Branch Naming

2.1. All ForgeAgent branches **must** follow this pattern (no exceptions):

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

| Token | Format | Example |
|---|---|---|
| `engineer_id` | lowercase alphanumeric or hyphen | `alice`, `bot-7` |
| `subsystem_slug` | lowercase, hyphen-separated | `trust-flow`, `build-pipeline` |
| `N` | zero-padded to 3 digits | `001`, `042` |
| `title_slug` | lowercase, hyphen-separated, max 48 chars | `add-heartbeat-timeout` |

2.2. The prefix `forge-agent` is **intentionally kept** (not `forgeagent`) for backward compatibility. Do not change it.

---

## 3. Class and Function Naming

3.1. Classes use **PascalCase**: `BuildLedger`, `ConsensusEngine`, `DocumentStore`.

3.2. Functions and methods use **snake_case**: `validate_write_path`, `ensure_ci_workflow`.

3.3. Module-level constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

3.4. Private helpers are prefixed with a single underscore: `_is_docs_pr`, `_docs_keywords`.

3.5. Boolean variables and functions that return booleans start with `is_`, `has_`, or `should_`: `_is_docs_pr`, `has_heartbeat`, `should_skip_gate`.

---

## 4. Accessibility Identifier Naming (Swift / macOS UI)

4.1. Every interactive SwiftUI element **must** have an `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern:

```
{module}-{component}-{role}-{context?}
```

All segments are **lowercase**, separated by **hyphens**.

4.3. Reference examples (canonical — match these patterns exactly):

```swift
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

4.4. Dynamic context values (e.g., `{projectId}`, `{gateId}`) are appended as the final segment. Use the entity's stable identifier, never a display name or index.

---

## 5. Error and Exception Patterns

5.1. Define custom exceptions in `src/<subsystem>/errors.py`. Each subsystem gets its own file — never dump all exceptions into a shared module.

5.2. Exception classes inherit from a single subsystem base:

```python
class TrustFlowError(Exception):
    """Base for all TrustFlow exceptions."""

class HeartbeatTimeoutError(TrustFlowError):
    """Raised when a ledger heartbeat exceeds its TTL."""
```

5.3. Never catch bare `except Exception` in production paths. Catch the narrowest type; let unexpected errors propagate.

5.4. All exceptions **must** carry a human-readable message **and** structured context:

```python
raise ClaimConflictError(
    f"Engineer {engineer_id} cannot claim {subsystem}: already held by {holder}",
    engineer_id=engineer_id,
    subsystem=subsystem,
    holder=holder,
)
```

5.5. Path-related failures from `validate_write_path` (see §7) must raise or log with the original unsanitised path redacted — never echo a traversal attempt into logs.

---

## 6. Import and Module Organisation

6.1. Imports are grouped in this order, separated by a blank line:

```python
# 1. stdlib
import os
from pathlib import Path

# 2. Third-party
import anthropic

# 3. Local – absolute from src/
from src.build_ledger import BuildLedger
from src.vtz.enforce import validate_zone
```

6.2. **Never use relative imports** (`from . import foo`). Always use absolute imports anchored at `src/`.

6.3. Do not import entire subsystem packages (`import src.cal`). Import the specific module or symbol.

6.4. Circular imports are a build-blocking defect. If two modules need each other, extract the shared type into a third module under the same subsystem directory.

---

## 7. ForgeAgent-Specific Patterns

### 7.1 Path Security — Validate Before Any Write

Every file-write operation **must** call `validate_write_path` before touching the filesystem. No exceptions, no shortcuts.

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
with open(safe_path, "w") as f:
    f.write(content)
```

7.1.1. If `validate_write_path` returns a safe default (meaning the original path failed validation), the agent **must** log a warning with event type `PATH_TRAVERSAL_BLOCKED` but **must not** include the raw malicious path in the log message.

7.1.2. Unit tests for any function that writes files must include at least one traversal-attack input (e.g., `../../etc/passwd`).

### 7.2 CI Workflow Integrity

7.2.1. `ci_workflow.ensure()` is the **sole** mechanism for creating or updating `crafted