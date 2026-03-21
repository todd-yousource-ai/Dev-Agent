

# Code Conventions — Forge Platform

> **Scope:** All code in the Forge monorepo, with dedicated section for the ConsensusDevAgent subsystem.
> **Authority:** These conventions are enforced by CI. PRs that violate numbered rules will be rejected automatically.

---

## 1. File and Directory Naming

1.1. **Source layout mirrors subsystem boundaries exactly:**

```
src/cal/           # Conversation Abstraction Layer
src/dtl/           # Data Trust Label
src/trustflow/     # TrustFlow audit stream
src/vtz/           # Virtual Trust Zone enforcement
src/trustlock/     # Cryptographic machine identity (TPM-anchored)
src/mcp/           # MCP Policy Engine
src/rewind/        # Forge Rewind replay engine
sdk/connector/     # Forge Connector SDK
tests/<subsystem>/ # Tests mirror src/ structure exactly
```

1.2. Every directory under `src/` and `tests/` **must** contain an `__init__.py` (even if empty) so that the package is importable without implicit namespace hacks.

1.3. File names use **lowercase_snake_case** with no hyphens: `consensus_engine.py`, `trust_label_store.py`.

1.4. Test files mirror the source file they cover and carry a `test_` prefix: `src/cal/session.py` → `tests/cal/test_session.py`.

1.5. Schema, migration, and fixture files include a zero-padded sequence number: `001_create_trust_labels.sql`, `002_add_expiry_column.sql`.

1.6. **Branch naming (mandatory):**

```
forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
```

Example: `forge-agent/build/e-7a2f/consensus-engine/pr-004-add-vote-timeout`

---

## 2. Class and Function Naming

2.1. Classes use **PascalCase**: `ConsensusDevAgent`, `TrustLabelStore`, `GateCardView`.

2.2. Functions and methods use **lowercase_snake_case**: `fetch_build_map()`, `validate_write_path()`.

2.3. Private helpers that must not be called outside their own module use a **single leading underscore**: `_strip_code_fences()`, `_compute_quorum()`.

2.4. Constants use **UPPER_SNAKE_CASE** and are declared at module level: `MAX_RETRY_COUNT = 3`, `DEFAULT_QUORUM_THRESHOLD = 0.67`.

2.5. Boolean variables and functions that return `bool` start with `is_`, `has_`, `can_`, or `should_`: `is_quorum_met`, `has_valid_signature`.

2.6. **axIdentifier naming (macOS / SwiftUI):** All interactive elements must have an `.accessibilityIdentifier()` that follows the pattern:

```
{module}-{component}-{role}-{context?}
```

Examples:

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

Every interactive element **must** carry an identifier. Omitting it is a CI failure.

---

## 3. Error and Exception Patterns

3.1. Define one **base exception per subsystem** in `<subsystem>/exceptions.py`:

```python
class CalError(Exception):
    """Base for all CAL errors."""

class SessionExpiredError(CalError): ...
class MessageValidationError(CalError): ...
```

3.2. Never raise bare `Exception`, `RuntimeError`, or `ValueError` for domain errors. Always use a subsystem-specific subclass.

3.3. Exception class names end with **`Error`**, not `Exception`: `PathTraversalError`, not `PathTraversalException`.

3.4. Every `except` block must catch the **narrowest possible type**. Bare `except:` and `except Exception:` are banned outside top-level process supervisors.

3.5. Error messages must include the **offending value** (redacted if sensitive) and the **constraint that was violated**:

```python
raise PathTraversalError(
    f"Blocked write to '{masked_path}': resolved path escapes sandbox root"
)
```

3.6. All functions that interact with external services (LLM APIs, file I/O, network) must handle errors explicitly and **never silently swallow them**. At minimum, log at `WARNING` level before suppressing.

---

## 4. Import and Module Organisation

4.1. Imports appear in **three groups**, separated by a blank line, each group sorted alphabetically:

```python
# 1. stdlib
import hashlib
import os
from pathlib import Path

# 2. third-party
import httpx
from pydantic import BaseModel

# 3. first-party / local
from src.cal.session import Session
from src.vtz.sandbox import validate_write_path
```

4.2. **No wildcard imports** (`from x import *`) anywhere in the codebase.

4.3. **No dynamic imports** for generated code. Generated files must not use `eval()`, `exec()`, or `importlib.import_module()` to load other generated files. Every generated file must be complete and self-contained (see §6.4).

4.4. Circular imports are a build failure. If two modules need each other, extract the shared type into a third `_types.py` module.

4.5. Re-exports from `__init__.py` must be listed explicitly in `__all__`.

---

## 5. Comment and Documentation Rules

5.1. Every public class and public function has a **docstring** (Google style):

```python
def fetch_build_map(project_id: str) -> BuildMap | None:
    """Retrieve the current build map for a project.

    Args:
        project_id: The Forge project identifier.

    Returns:
        The BuildMap if one has been generated, or None if no map
        exists yet (expected for the first 5 PRs of any build).

    Raises:
        CalError: If the project metadata is corrupt.
    """
```

5.2. Inline comments explain **why**, not what. If a comment restates the code, delete it.

5.3. `# TODO` comments must include an owner and tracking reference: `# TODO(amir): fix race condition — FORGE-1042`.

5.4. No commented-out code in main branches. Use version control history instead.

5.5. Module-level docstrings are required for any file longer than 50 lines.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Validation Before Every Write

**Every** file-write operation must validate the destination path before opening a handle. No exceptions, no shortcuts.

```python
from path_security import validate_write_path

safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError
with open(safe_path, "w") as f:
    f.write(content)
```

This applies to agent-generated code, logs, artifacts, scratch files, and temporary files. If a new write call is introduced without `validate_write_path`, CI rejects the PR.

### 6.2 `_strip_code_fences()` — Canonical Implementation

The `_strip_code_fences()` function exists in **five modules**. All five copies must be **byte-identical**. The function must:

1. Accept an empty string or `None` and return it unchanged.
2. Preserve a trailing newline on non-empty output.
3. Not modify code that has no fences or Unicode characters.
4. Be synchronous (no `async`).

A CI check (`scripts/verify_strip_fences_sync.py`) diffs all five copies and fails the build if