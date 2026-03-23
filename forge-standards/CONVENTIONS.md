# Code Conventions — Forge Platform

> Canonical reference for naming, structure, and code patterns across every Forge subsystem.
> Every rule is **mandatory** unless marked *(recommended)*.

---

## 1. File and Directory Naming

1. **Python modules** use `snake_case.py` — no hyphens, no capitals.
2. **Subsystem directories** live directly under `src/` and use short, lowercase slugs:

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

3. **Top-level orchestration modules** stay in `src/` root:

   ```
   src/consensus.py        — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM+UI_ADDENDUM
   src/build_director.py   — BuildPipeline orchestration, confidence gate, pr_type routing
   src/github_tools.py     — GitHubTool, WebhookReceiver
   src/build_ledger.py     — BuildLedger, claim/release, heartbeat
   src/document_store.py   — DocumentStore, chunk(), embed(), retrieve()
   src/ci_workflow.py      — CI workflow generation & conftest auto-commit
   ```

4. **Test directories mirror `src/` exactly**: a module at `src/vtz/enforcer.py` has tests at `tests/vtz/test_enforcer.py`.
5. **CI workflow files** are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other names are accepted.
6. **conftest.py** at the repo root is auto-committed by `ci_workflow.ensure()` to add `src/` to the import path. Never hand-edit it without verifying `ci_workflow.py` compatibility.

---

## 2. Branch Naming

7. **All agent-created branches** follow this exact template:

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — lowercase alphanumeric, no dots.
   - `subsystem_slug` — matches the `src/` directory name (e.g., `vtz`, `cal`, `trustflow`).
   - `N` — zero-padded to three digits (`001`, `042`).
   - `title_slug` — lowercase, hyphens only, max 48 chars.

   Example: `forge-agent/build/adeel/trustflow/pr-007-add-heartbeat-timeout`

8. The prefix `forge-agent` is **kept intentionally for compatibility** — do not rename to `forge-bot` or similar.

---

## 3. Class and Function Naming

9. **Classes** — `PascalCase`, noun-first. Suffix with the role when ambiguous:

   ```python
   class BuildLedger:       # data store
   class ConsensusEngine:   # processing engine
   class WebhookReceiver:   # I/O adapter
   ```

10. **Public functions** — `snake_case`, verb-first: `validate_write_path()`, `claim_build()`, `retrieve_chunks()`.
11. **Private/internal helpers** — single leading underscore: `_compute_confidence()`.
12. **Constants** — `UPPER_SNAKE_CASE`, defined at module top after imports:

    ```python
    GENERATION_SYSTEM = "..."
    MAX_RETRY_ATTEMPTS = 3
    ```

13. **Boolean variables and parameters** — prefix with `is_`, `has_`, `should_`, or `can_`:

    ```python
    is_docs_pr = title.startswith("[docs]")
    has_valid_claim = ledger.check(build_id)
    ```

14. **Dataclass / model fields** — `snake_case`, no abbreviations beyond the project glossary (`pr`, `ci`, `trd`, `ax`, `mcp`).

---

## 4. Error and Exception Patterns

15. **Custom exceptions** inherit from a single base per subsystem:

    ```python
    # src/vtz/exceptions.py
    class VTZError(Exception):
        """Base for all VTZ errors."""

    class ZoneViolationError(VTZError):
        """Raised when a write crosses zone boundaries."""
    ```

16. **Exception class names** end in `Error` (not `Exception`), and use `PascalCase`.
17. **Never use bare `except:`**. At minimum catch `Exception`; prefer the narrowest type.
18. **Log before re-raising**. Every `except` block that re-raises must emit a structured log line first:

    ```python
    except ZoneViolationError as exc:
        logger.error("zone_violation", path=target, detail=str(exc))
        raise
    ```

19. **Return early on validation failure** instead of nesting. Prefer guard clauses:

    ```python
    def process(payload: dict) -> Result:
        if "build_id" not in payload:
            raise ValueError("missing build_id in payload")
        # happy path continues un-indented
    ```

---

## 5. Import and Module Organisation

20. **Import order** (enforced by `isort` with `profile=black`):

    1. Standard library
    2. Third-party packages
    3. Forge `src/` modules (absolute imports from `src`)
    4. Local relative imports (same package only)

    Separate each group with a blank line.

21. **Always use absolute imports from `src/`** in application code:

    ```python
    from build_ledger import BuildLedger
    from vtz.enforcer import enforce_zone
    ```

22. **Relative imports** are allowed only inside a subsystem package for intra-package references:

    ```python
    # Inside src/vtz/enforcer.py
    from .exceptions import ZoneViolationError
    ```

23. **No wildcard imports** (`from module import *`) anywhere — no exceptions.
24. **Lazy imports** are permitted only when a dependency is optional or heavy; add a comment explaining why:

    ```python
    def embed(text: str) -> list[float]:
        # Lazy: torch is 2 GB, only needed at embed time
        import torch
        ...
    ```

---

## 6. Comment and Documentation Rules

25. **Every public class and function** has a docstring. Use the imperative mood for the first line:

    ```python
    def claim_build(build_id: str) -> Claim:
        """Claim exclusive ownership of a build slot."""
    ```

26. **Inline comments** explain *why*, not *what*. If the code needs a comment to explain *what*, refactor first.
27. **TODO format** — always include an engineer ID and optional ticket:

    ```python
    # TODO(adeel): handle token refresh on 401 — FORGE-228
    ```

28. **No commented-out code** in `main` or any PR-ready branch. Use version control history instead.

---

## 7. FullPlatform-Specific Patterns

### 7.1 Path Security — Validate Before Every Write

29. **Every file-system write** must pass through `validate_write_path` before opening:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # returns safe default on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```

30. Never construct write paths via string concatenation. Use `pathlib.Path` and then validate.

### 7.2 macOS Accessibility Identifiers