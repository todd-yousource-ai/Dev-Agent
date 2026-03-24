# CONVENTIONS.md — ForgeAgent Subsystem

All rules below are derived from the ForgeAgent TRD corpus. Every convention is mandatory unless explicitly marked optional.

---

## 1. File and Directory Naming

1. **Source directories use short, lowercase abbreviations** matching their subsystem acronym. Never abbreviate ad-hoc; use only the canonical set:
   - `src/cal/` — Conversation Abstraction Layer
   - `src/dtl/` — Data Trust Label
   - `src/trustflow/` — TrustFlow audit stream
   - `src/vtz/` — Virtual Trust Zone enforcement
   - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
   - `src/mcp/` — MCP Policy Engine
   - `src/rewind/` — Forge Rewind replay engine
   - `sdk/connector/` — Forge Connector SDK

2. **Test directories mirror `src/` exactly.** A source file at `src/vtz/enforcer.py` has its tests at `tests/vtz/test_enforcer.py`. No exceptions.

3. **Python backend filenames are `snake_case.py`**, no hyphens, no uppercase:
   - `src/consensus.py`
   - `src/build_director.py`
   - `src/github_tools.py`
   - `src/build_ledger.py`
   - `src/document_store.py`
   - `src/ci_workflow.py`

4. **CI workflow files use the exact canonical names:**
   - `crafted-ci.yml` — Ubuntu pipeline
   - `crafted-ci-macos.yml` — macOS Swift pipeline
   - No other naming variants are permitted.

5. **`conftest.py` is never manually created or edited.** It is auto-committed by `ci_workflow.ensure()` to guarantee `src/` is on the import path. If you need test fixtures, place them in a separate `fixtures.py` inside the relevant `tests/<subsystem>/` directory.

---

## 2. Branch Naming

6. **Every ForgeAgent branch must follow this exact pattern:**

   ```
   forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
   ```

   - `engineer_id` — the agent or human identifier (e.g., `fa-01`, `jdoe`).
   - `subsystem_slug` — lowercase hyphenated subsystem name (e.g., `trust-flow`, `build-pipeline`).
   - `N:03d` — zero-padded three-digit PR sequence number (e.g., `001`, `042`).
   - `title_slug` — lowercase hyphenated summary, max 48 characters.

   Example: `forge-agent/build/fa-01/trust-flow/pr-007-add-heartbeat-timeout`

7. **The prefix `forge-agent` is kept exactly as-is** (not `forge_agent`, not `forgeagent`). This is intentional for backward compatibility.

---

## 3. Class and Function Naming

8. **Classes use `PascalCase`.** Acronyms of three or fewer letters stay uppercase; longer acronyms use title-case:
   - `BuildLedger`, `GitHubTool`, `WebhookReceiver`, `DocumentStore`
   - `MCPPolicyEngine` (MCP is ≤ 3 letters → uppercase)
   - `TrustflowAuditor` (single compound word, not an acronym)

9. **Functions and methods use `snake_case`.** Verb-first for actions, noun-first for accessors:
   - `validate_write_path()`, `claim_build()`, `release_lock()`
   - `chunk()`, `embed()`, `retrieve()`

10. **Constants use `UPPER_SNAKE_CASE`** and are defined at module scope:
    - `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`

11. **Private helpers are single-underscore prefixed.** Never use double-underscore name-mangling:
    - `_is_docs_pr`, `_docs_keywords` ✅
    - `__is_docs_pr` ❌

---

## 4. Accessibility Identifier Naming (axIdentifier)

12. **Every interactive SwiftUI element must have `.accessibilityIdentifier()` set.** No interactive element ships without one.

13. **axIdentifiers follow the pattern `{module}-{component}-{role}-{context?}`**, all lowercase, hyphen-delimited:

    | Pattern | Example |
    |---|---|
    | Static button | `auth-touchid-button` |
    | Field | `settings-anthropic-key-field` |
    | Action on field | `settings-anthropic-key-reveal-button` |
    | Row with dynamic ID | `navigator-project-row-{projectId}` |
    | Gate card | `stream-gate-card-{gateId}` |
    | Gate action | `stream-gate-yes-button-{gateId}` |

14. **The `{context}` segment is required whenever the element repeats** (lists, gates, cards). It must be the entity's stable ID, not an array index.

---

## 5. Error and Exception Patterns

15. **All custom exceptions inherit from a single `ForgeAgentError` base class** defined in `src/errors.py`.

16. **Exception classes are named `{Noun}{Verb}Error`:**
    - `PathTraversalError`, `BuildClaimError`, `LedgerHeartbeatError`

17. **Never catch bare `except:` or `except Exception:` at the call site.** Catch the narrowest `ForgeAgentError` subclass possible.

18. **Path validation must occur before ANY filesystem write.** Use the canonical guard:

    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)
    # Returns a safe default on traversal attempt; never raises silently.
    ```

    Skipping this call for any write operation is a blocking review finding.

---

## 6. Import and Module Organisation

19. **Imports are grouped in this exact order, separated by a blank line:**
    1. Standard library
    2. Third-party packages
    3. `src/` internal modules (absolute imports from `src`)
    4. Relative imports (only within the same subsystem package)

20. **Always use absolute imports from `src/` for cross-subsystem references:**

    ```python
    # ✅ Correct
    from src.build_ledger import BuildLedger
    from src.vtz.enforcer import VTZEnforcer

    # ❌ Wrong — relative import across subsystem boundary
    from ..vtz.enforcer import VTZEnforcer
    ```

21. **Relative imports are permitted only within the same subsystem package** (e.g., inside `src/cal/`):

    ```python
    # Inside src/cal/session.py
    from .message import Message  # ✅ same package
    ```

22. **Never use wildcard imports (`from x import *`).**

---

## 7. Comment and Documentation Rules

23. **Every module has a one-line docstring** stating its TRD-traceable purpose:

    ```python
    """BuildLedger: claim/release and heartbeat tracking (TRD-3 §4.2)."""
    ```

24. **Every public function and class has a docstring** with at minimum: one summary line, `Args:`, `Returns:`, and `Raises:` sections (Google-style).

25. **Inline comments explain _why_, never _what_.** If a comment restates the code, delete it.

26. **TODO comments must include an engineer ID and a tracking reference:**

    ```python
    # TODO(fa-01): Switch to async heartbeat once TRD-3 §6 is finalised
    ```

---

## 8. ForgeAgent-Specific Patterns

27. **PR type routing is the responsibility of `build_director.py`.** No other module may inspect PR metadata to decide build behaviour. Confidence gates and `pr_type` classification live exclusively