

# Code Conventions — Forge Platform

**Subsystem scope:** All Forge platform code, with dedicated section for the ConsensusDevAgent build pipeline.

**Last updated:** 2025-01-15
**Owner:** Forge Platform Engineering

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem boundaries exactly.**
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

2. **Test directories mirror `src/` exactly.** A source file at `src/dtl/label_validator.py` must have its tests at `tests/dtl/test_label_validator.py`.

3. **All filenames use `snake_case`.** No hyphens, no camelCase, no uppercase letters in file or directory names.
   ```
   # ✅ correct
   src/cal/session_manager.py
   tests/cal/test_session_manager.py

   # ❌ wrong
   src/cal/SessionManager.py
   src/cal/session-manager.py
   ```

4. **Config and schema files** use snake_case with a clear suffix: `consensus_config.toml`, `pipeline_schema.json`, `gate_definitions.yaml`.

5. **One module = one responsibility.** If a file exceeds 400 lines, split it. Extract helpers into a `_helpers.py` or a sub-package.

---

## 2. Class and Function Naming

6. **Classes:** `PascalCase`. Suffix with role when the role is not obvious from context.
   ```python
   class ConsensusOrchestrator:      # role is the name
   class GateEvaluator:
   class TrustFlowAuditWriter:
   ```

7. **Functions and methods:** `snake_case`, verb-first.
   ```python
   def validate_write_path(path: str) -> Path: ...
   def evaluate_gate(gate_id: str, context: GateContext) -> GateResult: ...
   def build_prd_plan(intent: Intent) -> PRDPlan: ...
   ```

8. **Private helpers:** Prefix with a single underscore. Never use double-underscore name mangling unless explicitly preventing subclass collision.
   ```python
   def _parse_raw_intent(raw: str) -> str: ...
   ```

9. **Constants:** `UPPER_SNAKE_CASE`, defined at module top after imports.
   ```python
   MAX_CONSENSUS_ROUNDS = 5
   DEFAULT_GATE_TIMEOUT_SEC = 30
   TEST_GENERATION_SYSTEM = """..."""
   ```

10. **Type aliases and dataclasses:** `PascalCase`. Dataclasses are always `frozen=True` unless mutation is explicitly required and documented.
    ```python
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class BuildEntity:
        intent: str
        subsystem: str
        scope_statement: str
        branch_prefix: str
        relevant_docs: list[str]
    ```

11. **Accessibility identifiers (macOS shell):** Follow the pattern `{module}-{component}-{role}-{context?}`, set via `.accessibilityIdentifier()` on every interactive element.
    ```
    "auth-touchid-button"
    "settings-anthropic-key-field"
    "navigator-project-row-{projectId}"
    "stream-gate-card-{gateId}"
    "stream-gate-yes-button-{gateId}"
    ```

---

## 3. Error and Exception Patterns

12. **Custom exceptions inherit from a single `ForgeError` base.**
    ```python
    class ForgeError(Exception):
        """Base for all Forge-raised exceptions."""

    class PathTraversalError(ForgeError): ...
    class ConsensusTimeoutError(ForgeError): ...
    class GateRejectedError(ForgeError): ...
    ```

13. **Never catch bare `Exception` or `BaseException`** except at the outermost boundary (CLI entry point, HTTP handler). Catch the narrowest type possible.

14. **Every `except` block must either re-raise, log at `WARNING`+, or return a typed error object.** Silent swallowing is forbidden.

15. **Path validation before every write — no exceptions.**
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises PathTraversalError
    safe_path.write_text(content)
    ```
    This applies to agent-generated code, test harnesses, build artefacts — any code path that touches the filesystem for writing.

16. **Error messages must include context.** Minimum: the operation attempted, the value that failed, and why.
    ```python
    raise ConsensusTimeoutError(
        f"Gate '{gate_id}' did not reach consensus after {MAX_CONSENSUS_ROUNDS} rounds; "
        f"last vote distribution: {vote_summary}"
    )
    ```

---

## 4. Import and Module Organisation

17. **Import order** (enforced by `isort` with `profile=black`):
    1. Standard library
    2. Third-party packages
    3. Forge platform packages (`src/...`)
    4. Local/relative imports

    Separate each group with a single blank line.

18. **Absolute imports only** from outside the current package. Relative imports (single dot) are permitted only within the same sub-package.
    ```python
    # ✅ from another subsystem — absolute
    from src.cal.session_manager import SessionManager

    # ✅ within the same sub-package — relative OK
    from ._helpers import parse_gate_config
    ```

19. **No wildcard imports.** `from module import *` is banned everywhere.

20. **Lazy imports** are permitted only when a dependency is expensive to load and not always needed. Annotate with a comment:
    ```python
    def render_audit_trail():
        import pandas as pd  # lazy: only needed for export paths
    ```

---

## 5. Comment and Documentation Rules

21. **Every public class, function, and method must have a docstring.** Use Google-style docstrings.
    ```python
    def evaluate_gate(gate_id: str, context: GateContext) -> GateResult:
        """Run consensus evaluation for a single gate.

        Args:
            gate_id: Unique gate identifier from the stream definition.
            context: Snapshot of current build state and agent votes.

        Returns:
            GateResult with verdict (PASS | FAIL | ABSTAIN) and reasoning.

        Raises:
            ConsensusTimeoutError: If no quorum is reached within MAX_CONSENSUS_ROUNDS.
        """
    ```

22. **Inline comments explain *why*, not *what*.** If the code needs a *what* comment, refactor it until it doesn't.
    ```python
    # ✅
    # Retry once because the MCP endpoint occasionally returns 503 during deploys
    response = _call_mcp_with_retry(payload, retries=1)

    # ❌
    # Call the MCP endpoint
    response = _call_mcp(payload)
    ```

23. **TODO format:** `# TODO(username): description — YYYY-MM-DD`. TODOs without a date and owner are rejected in review.

24. **No commented-out code in `main` or release branches.** Remove it or gate it behind a feature flag.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Branch Naming (Mandatory)

25. **Every agent-created branch must follow this exact pattern:**
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    Examples:
    ```