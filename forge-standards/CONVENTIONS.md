# CONVENTIONS.md — ForgeAgent Subsystem

All conventions are derived from the ForgeAgent TRD corpus. Every rule is mandatory unless marked `[RECOMMENDED]`.

---

## 1. File and Directory Naming

1.1. Python source files use **snake_case**, no hyphens, no uppercase:
```
src/build_director.py    ✅
src/BuildDirector.py     ❌
src/build-director.py    ❌
```

1.2. Source directories map **one-to-one** to subsystem abbreviations. Use only these canonical directory names:

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
src/cal/engine.py        → tests/cal/test_engine.py
src/build_director.py    → tests/test_build_director.py
```

1.4. CI workflow files use these exact filenames — no alternatives:
- `crafted-ci.yml` — Ubuntu pipeline
- `crafted-ci-macos.yml` — macOS Swift pipeline

1.5. `conftest.py` at the repo root is **auto-committed** by `ci_workflow.ensure()` to guarantee `src/` is importable. Never hand-edit this file; regenerate it via the CI workflow module.

---

## 2. Branch Naming

2.1. All ForgeAgent branches follow this **exact** template (kept as `forge-agent` for compatibility — do not change to `forgeagent` or other variants):

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

| Token | Format | Example |
|---|---|---|
| `engineer_id` | lowercase alphanumeric, hyphens allowed | `alice`, `bot-7` |
| `subsystem_slug` | lowercase, hyphens, matches a `src/` directory | `build-director`, `cal` |
| `N` | zero-padded to 3 digits | `001`, `042` |
| `title_slug` | lowercase, hyphens, max 48 chars | `add-heartbeat-timeout` |

Example:
```
forge-agent/build/alice/build-director/pr-012-add-heartbeat-timeout
```

---

## 3. Class and Function Naming

3.1. Classes use **PascalCase**. Acronyms ≤ 3 letters stay uppercase; longer acronyms use title case:
```python
class BuildPipeline:       # ✅
class MCP PolicyEngine:    # ❌ (space)
class MCPPolicyEngine:     # ✅ (MCP = 3 letters, uppercase)
class TrustFlowAuditor:    # ✅
```

3.2. Functions and methods use **snake_case**. Prefix private helpers with a single underscore:
```python
def claim_build():         # ✅ public
def _rotate_heartbeat():   # ✅ private
def ClaimBuild():          # ❌
```

3.3. Constants use **UPPER_SNAKE_CASE** and are defined at module level:
```python
GENERATION_SYSTEM = "..."
SWIFT_GENERATION_SYSTEM = "..."
UI_ADDENDUM = "..."
```

3.4. Module-private collections that are not true constants use a leading underscore and **lower_snake_case**:
```python
_docs_keywords = {"naming convention", "glossary", "changelog"}
```

---

## 4. Accessibility Identifier Naming (axIdentifier)

4.1. Every interactive SwiftUI element **must** have an `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern:
```
{module}-{component}-{role}-{context?}
```

| Segment | Rules |
|---|---|
| `module` | Lowercase, matches feature area (`auth`, `settings`, `navigator`, `stream`) |
| `component` | Specific widget or entity (`touchid`, `anthropic-key`, `project-row`, `gate`) |
| `role` | UI role (`button`, `field`, `card`, `row`, `toggle`) |
| `context` | Optional. Dynamic ID appended with hyphen: `{gateId}`, `{projectId}` |

4.3. Canonical examples (treat as the reference set):
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

4.4. Never use camelCase, PascalCase, or underscores in axIdentifiers.

---

## 5. Error and Exception Patterns

5.1. Define one custom exception base class per subsystem module:
```python
class BuildDirectorError(Exception):
    """Base for all build_director failures."""
```

5.2. Specific errors subclass the base and include a machine-readable `code` attribute:
```python
class ClaimConflictError(BuildDirectorError):
    code = "CLAIM_CONFLICT"
```

5.3. Never catch bare `Exception` in production paths. Catch the narrowest subsystem error:
```python
try:
    ledger.claim(build_id)
except ClaimConflictError:
    ...
```

5.4. All exceptions raised toward the user or CI must include a single-line `message` suitable for log ingestion (no multi-line tracebacks in the message string).

---

## 6. Path Security

6.1. **Validate every path before any filesystem write.** No exceptions, no shortcuts:
```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)
```

6.2. `validate_write_path` returns a **safe default** on directory-traversal attempts — it does **not** raise. Callers must never bypass it with `os.path.join` or `pathlib` directly when the input originates from a user, webhook, or external config.

6.3. Read-only operations on user-supplied paths must still be checked when the path could later be passed to a write function. `[RECOMMENDED]` Use `validate_write_path` for reads as well to keep a single code path.

---

## 7. Import and Module Organisation

7.1. Imports are grouped in this order, separated by a blank line:
1. Standard library
2. Third-party packages
3. `src/` internal modules (absolute from `src`)

```python
import os
import json

import httpx

from src.build_ledger import BuildLedger
from src.consensus import ConsensusEngine
```

7.2. Never use relative imports (`from . import ...`) outside of `__init__.py` files.

7.3. Canonical top-level module mapping — use these exact module names when importing:

| Import path | Responsibility |
|---|---|
| `src.consensus` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
| `src.build_director` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
| `src.github_tools` | `GitHubTool`, `WebhookReceiver` |
| `src.build_ledger` | `