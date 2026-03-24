# CONVENTIONS.md — ForgeAgent Subsystem

> All rules derived from project TRDs. Every rule is mandatory unless explicitly marked *recommended*.

---

## 1. File and Directory Naming

1.1. Python source files use **snake_case**, no hyphens, no capitals.
```
src/build_director.py    ✅
src/BuildDirector.py     ❌
src/build-director.py    ❌
```

1.2. Source directories map one-to-one with subsystem abbreviations. Never invent ad-hoc directory names.
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

1.3. Test directories **mirror `src/` structure exactly**. A source file at `src/cal/session.py` must have tests at `tests/cal/test_session.py`.

1.4. CI workflow files use these exact names — do not rename or duplicate:
| Platform | Filename |
|----------|----------|
| Ubuntu   | `crafted-ci.yml` |
| macOS Swift | `crafted-ci-macos.yml` |

1.5. `conftest.py` at repo root is **auto-committed** by `ci_workflow.ensure()` to enable `src/` imports. Never hand-edit this file; if changes are needed, modify `ci_workflow.ensure()` instead.

1.6. Canonical backend source files — use these exact names:
```
src/consensus.py        # ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM+UI_ADDENDUM
src/build_director.py   # BuildPipeline orchestration, confidence gate, pr_type routing
src/github_tools.py     # GitHubTool, WebhookReceiver
src/build_ledger.py     # BuildLedger, claim/release, heartbeat
src/document_store.py   # DocumentStore, chunk(), embed(), retrieve()
src/ci_workflow.py      # CI workflow generation and conftest management
```

---

## 2. Branch Naming

2.1. All ForgeAgent branches **must** follow this pattern exactly:
```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

2.2. Tokens:
| Token | Format | Example |
|-------|--------|---------|
| `engineer_id` | lowercase alphanumeric + hyphens | `alice-7` |
| `subsystem_slug` | lowercase, hyphen-separated, matching a known subsystem | `trust-flow` |
| `N` | zero-padded to 3 digits | `007` |
| `title_slug` | lowercase, hyphen-separated, max 48 chars | `add-heartbeat-timeout` |

2.3. The prefix `forge-agent` is **intentionally kept** (not `forgeagent`, not `forge_agent`) for backward compatibility. Do not change it.

---

## 3. Class and Function Naming

3.1. Classes use **PascalCase**. Acronyms of 3+ letters are title-cased; 2-letter acronyms stay uppercase.
```python
class BuildLedger:       # ✅
class ConsensusEngine:   # ✅
class MCP PolicyEngine:  # ❌ (space)
class MCPPolicyEngine:   # ✅
class CIWorkflow:        # ✅ (2-letter acronym stays upper)
```

3.2. Functions and methods use **snake_case**. Prefix private helpers with a single underscore.
```python
def claim_build():       # ✅ public
def _resolve_conflict(): # ✅ private
def ClaimBuild():        # ❌
```

3.3. Constants use **UPPER_SNAKE_CASE**. Place them at module top, after imports.
```python
GENERATION_SYSTEM = "..."
SWIFT_GENERATION_SYSTEM = "..."
UI_ADDENDUM = "..."
```

3.4. Internal/deprecated keyword collections prefix with underscore and use lowercase:
```python
_docs_keywords = {"naming convention", "glossary", "changelog"}
```

---

## 4. Accessibility Identifier Naming (macOS / Swift UI)

4.1. Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.

4.2. Identifiers follow the pattern:
```
{module}-{component}-{role}-{context?}
```
All segments are **lowercase**, separated by **hyphens**.

4.3. When an element is associated with a dynamic entity, append the entity ID after a hyphen:
```
navigator-project-row-{projectId}
stream-gate-card-{gateId}
stream-gate-yes-button-{gateId}
```

4.4. Reference examples (canonical — match these patterns):
```
auth-touchid-button
auth-passcode-button
settings-anthropic-key-field
settings-anthropic-key-test-button
settings-anthropic-key-reveal-button
stream-gate-skip-button-{gateId}
stream-gate-stop-button-{gateId}
```

4.5. Never use camelCase, underscores, or dots inside an `axIdentifier`.

---

## 5. Error and Exception Patterns

5.1. Define custom exceptions per subsystem in a file named `exceptions.py` inside the subsystem directory (e.g., `src/cal/exceptions.py`).

5.2. All custom exceptions inherit from a single project base:
```python
class ForgeAgentError(Exception):
    """Root exception for every ForgeAgent subsystem."""

class PathTraversalError(ForgeAgentError):
    """Raised when a write path fails security validation."""

class BuildClaimError(ForgeAgentError):
    """Raised when ledger claim/release fails."""
```

5.3. Never catch bare `Exception` in agent-facing code. Catch the narrowest `ForgeAgentError` subclass possible.

5.4. Every `except` block must either **log and re-raise** or **return a well-defined error object**. Silent swallowing is forbidden:
```python
# ✅
except BuildClaimError as e:
    logger.error("Claim failed: %s", e)
    raise

# ❌
except Exception:
    pass
```

---

## 6. Path Security

6.1. **Validate paths before ANY write.** No exceptions.
```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)
# Returns a safe default on traversal attempt — never raises silently
```

6.2. Never construct file paths via string concatenation. Use `pathlib.Path` and then pass through `validate_write_path` before any `open(..., "w")`, `shutil.copy`, or equivalent.

6.3. Unit tests for every function that writes to disk must include at least one traversal-attack input (`../../etc/passwd`, absolute path outside workspace, symlink escape).

---

## 7. Import and Module Organisation

7.1. Imports appear in this order, separated by blank lines:
```
1. stdlib
2. third-party
3. project-level (`src.*`)
4. subsystem-relative
```

7.2. Always import from `src/` using the full dotted path:
```python
from src.build_ledger import BuildLedger        # ✅
from build_ledger import BuildLedger             # ❌
```

7.3. Do not use wildcard imports (`from module import *`) anywhere in the codebase.

7.4. Circular imports are treated as bugs. If two subsystem modules need each other, extract shared types into a `_types.py` file in the higher-level package.

---

## 8. Comment and Documentation Rules

8.1