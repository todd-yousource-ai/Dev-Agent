# CONVENTIONS.md — ForgeAgent Subsystem

All rules are derived from the ForgeAgent TRD corpus. Every rule is mandatory unless explicitly marked `[OPTIONAL]`.

---

## 1. File and Directory Naming

1.1. Python source files live under `src/` in **snake_case**, one module per logical responsibility.

| Path pattern | Purpose |
|---|---|
| `src/consensus.py` | ConsensusEngine, generation system prompts |
| `src/build_director.py` | BuildPipeline orchestration, confidence gate, pr_type routing |
| `src/github_tools.py` | GitHubTool, WebhookReceiver |
| `src/build_ledger.py` | BuildLedger, claim/release, heartbeat |
| `src/document_store.py` | DocumentStore, chunk/embed/retrieve |
| `src/ci_workflow.py` | CI YAML generation and conftest management |

1.2. Subsystem directories use **short lowercase abbreviations**, never full words:

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

1.3. Test directories **mirror `src/` structure exactly**:

```
tests/cal/
tests/dtl/
tests/trustflow/
tests/vtz/
tests/trustlock/
tests/mcp/
tests/rewind/
```

1.4. CI workflow files use the exact names `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No alternatives.

1.5. `conftest.py` at project root is **auto-committed** by `ci_workflow.ensure()` to guarantee `src/` import resolution. Never hand-edit this file.

---

## 2. Branch Naming

2.1. Every ForgeAgent branch **must** follow this template (kept as `forge-agent` for compatibility — do not change to `forgeagent` or any variant):

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

| Segment | Format | Example |
|---|---|---|
| `engineer_id` | lowercase alphanumeric, hyphens allowed | `jdoe` |
| `subsystem_slug` | matches `src/` directory name | `trustflow` |
| `N:03d` | zero-padded 3-digit PR sequence | `007` |
| `title_slug` | lowercase, hyphens, max 48 chars | `add-heartbeat-timeout` |

2.2. Full example:

```
forge-agent/build/jdoe/trustflow/pr-007-add-heartbeat-timeout
```

---

## 3. Class and Function Naming

3.1. Classes use **PascalCase** with no underscores: `BuildPipeline`, `ConsensusEngine`, `DocumentStore`, `BuildLedger`.

3.2. Public functions and methods use **snake_case**: `validate_write_path`, `ensure`, `claim`, `release`.

3.3. Module-level constants use **UPPER_SNAKE_CASE**: `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.

3.4. Private/internal module-level variables use a **leading underscore**: `_docs_keywords`, `_is_docs_pr`.

3.5. When a variable holds a set or list of keywords used for matching, name it `_{domain}_keywords` (e.g., `_docs_keywords`).

---

## 4. Accessibility Identifier Naming (axIdentifier)

4.1. Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.

4.2. The identifier follows the pattern:

```
{module}-{component}-{role}-{context?}
```

All segments are **lowercase**, separated by **hyphens**. The `{context}` segment is optional and used for dynamic IDs.

4.3. Canonical examples (authoritative — use these as templates):

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

4.4. Dynamic suffixes (e.g., `{projectId}`, `{gateId}`) are appended with a hyphen, never a dot or slash.

---

## 5. Error and Exception Patterns

5.1. **Path validation before every write.** No file-system write may occur without calling `validate_write_path` first:

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)
# Returns a safe default on traversal attempt — never raises for traversal.
# All subsequent I/O uses safe_path, never user_supplied_path.
```

5.2. If `validate_write_path` returns a safe default (i.e., input was malicious), log a warning at `WARNING` level with the original path value for audit.

5.3. Custom exceptions are defined per subsystem in a file named `exceptions.py` inside the subsystem directory (e.g., `src/trustflow/exceptions.py`). Exception class names end with `Error`: `LedgerClaimError`, `TrustZoneViolationError`.

5.4. Never catch bare `except:` or `except Exception:` at module boundaries. Catch the narrowest exception type possible, and always re-raise or log unknown exceptions.

---

## 6. Import and Module Organisation

6.1. Import order (enforced, separated by blank lines):

```python
# 1. Standard library
import os
import json

# 2. Third-party packages
import httpx

# 3. Project-level shared modules (src/ root)
from path_security import validate_write_path
from consensus import ConsensusEngine

# 4. Subsystem-local imports (relative)
from .exceptions import LedgerClaimError
```

6.2. Never use wildcard imports (`from module import *`).

6.3. Circular imports are resolved by moving shared types to a dedicated `types.py` or `protocols.py` inside the subsystem directory.

6.4. The `conftest.py` auto-generated by `ci_workflow.ensure()` adds `src/` to `sys.path`. Do not duplicate this logic in test files; rely on the auto-committed `conftest.py`.

---

## 7. Comment and Documentation Rules

7.1. Every module file begins with a single-line docstring stating its TRD-derived responsibility:

```python
"""BuildLedger — claim/release and heartbeat tracking for concurrent builds."""
```

7.2. Public classes and public functions require a docstring. Use imperative mood for the first line:

```python
def claim(build_id: str) -> bool:
    """Claim exclusive ownership of a build slot."""
```

7.3. Inline comments explain **why**, not **what**. If a comment restates the code, delete it.

7.4. Convention markers in comments use these exact prefixes:

| Prefix | Meaning |
|---|---|
| `# Convention:` | Documents a project-wide naming or structural rule inline |
| `# TRD:` | Traces the line back to a specific TRD requirement |
| `# SECURITY:` | Marks a security-sensitive block (path validation, credential handling) |
| `# TODO(engineer_id):` | Tracked work item; must include owner |

7.5. No