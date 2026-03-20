

# Code Conventions — Forge Platform

> Canonical reference for all contributors and agents operating within the Forge codebase.
> Every rule is mandatory unless explicitly annotated **[RECOMMENDED]**.

---

## 1. File and Directory Naming

1. **Source layout mirrors subsystem slugs exactly.**

   ```
   src/cal/           – Conversation Abstraction Layer
   src/dtl/           – Data Trust Label
   src/trustflow/     – TrustFlow audit stream
   src/vtz/           – Virtual Trust Zone enforcement
   src/trustlock/     – Cryptographic machine identity (TPM-anchored)
   src/mcp/           – MCP Policy Engine
   src/rewind/        – Forge Rewind replay engine
   sdk/connector/     – Forge Connector SDK
   tests/<subsystem>/ – Tests mirror src/ structure exactly
   ```

2. **Python files** use `snake_case.py`. No hyphens, no uppercase.
   ```
   src/dtl/label_validator.py      ✅
   src/dtl/LabelValidator.py       ❌
   src/dtl/label-validator.py      ❌
   ```

3. **TypeScript/Swift files** use `PascalCase` for components/classes, `camelCase` for utilities.
   ```
   StreamGateCard.swift             ✅  (SwiftUI view)
   consensusSocket.ts               ✅  (utility module)
   ```

4. **Test files** are prefixed with `test_` (Python) or suffixed with `.test.ts` / `.spec.ts` (TypeScript).
   ```
   tests/dtl/test_label_validator.py
   tests/cal/session_manager.test.ts
   ```

5. **One module = one responsibility.** If a file exceeds 400 lines, split it. Name the sub-modules by the responsibility they extract (e.g., `label_parser.py`, `label_serializer.py`).

6. **Configuration and schema files** live at the repo root or in `config/` and use `kebab-case` with their format suffix: `forge-agent.toml`, `consensus-schema.json`.

---

## 2. Class and Function Naming

7. **Python classes**: `PascalCase`. No `_Impl`, no `Base` prefix; use `Abstract` prefix only for true ABCs.
   ```python
   class ConsensusRound:       ✅
   class AbstractVoter(ABC):   ✅
   class BaseVoter:            ❌
   ```

8. **Python functions and methods**: `snake_case`, verb-first.
   ```python
   def validate_trust_label(label: TrustLabel) -> bool:
   def emit_audit_event(event: AuditEvent) -> None:
   ```

9. **Constants**: `UPPER_SNAKE_CASE`, defined at module level or in a dedicated `constants.py` per subsystem.
   ```python
   MAX_CONSENSUS_ROUNDS = 5
   DEFAULT_QUORUM_THRESHOLD = 0.6
   ```

10. **TypeScript/Swift** follows the same PascalCase-for-types, camelCase-for-functions convention.

11. **Private helpers**: Prefix with a single underscore in Python (`_merge_diffs`). Never use double-underscore name mangling unless you have a documented reason.

12. **Dataclass and model field names**: `snake_case`, matching the serialized JSON key exactly. No aliasing unless interfacing with an external API.

---

## 3. Error and Exception Patterns

13. **Custom exceptions** inherit from a single subsystem base exception, which itself inherits from `ForgeError`.
    ```python
    # src/forge_errors.py
    class ForgeError(Exception):
        """Root of all Forge-specific exceptions."""

    # src/dtl/exceptions.py
    class DTLError(ForgeError): ...
    class LabelSchemaViolation(DTLError): ...
    class LabelSignatureInvalid(DTLError): ...
    ```

14. **Never catch bare `Exception` or `BaseException`** unless you re-raise. Log and wrap unknown errors into the subsystem base exception with the original as `__cause__`.
    ```python
    except SomeLibError as exc:
        raise DTLError("label store unavailable") from exc
    ```

15. **Error messages** are lowercase sentence fragments, no trailing period, and include the failing value or identifier when safe to do so.
    ```python
    raise LabelSchemaViolation(f"unknown field '{field}' in label {label_id}")
    ```

16. **Return `Result` types [RECOMMENDED]** for operations where failure is a normal branch (e.g., consensus votes that may not reach quorum). Reserve exceptions for truly exceptional conditions.

---

## 4. Import and Module Organisation

17. **Import order** (enforced by `isort` with the profile `black`):
    1. Standard library
    2. Third-party packages
    3. Forge-internal (`src.*`, `sdk.*`)
    4. Local relative imports

    Separate each group with a single blank line.

18. **Absolute imports from `src/`** are the default. Relative imports are allowed only within the same subsystem package.
    ```python
    from src.dtl.label_validator import validate_trust_label   ✅
    from .label_validator import validate_trust_label           ✅  (inside src/dtl/)
    from src.cal.session import Session                        ✅  (cross-subsystem)
    ```

19. **No wildcard imports** (`from x import *`) anywhere.

20. **Circular imports**: If two subsystems need each other, introduce a shared types module (`src/shared/types.py`) or use `TYPE_CHECKING` guards.
    ```python
    from __future__ import annotations
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.cal.session import Session
    ```

---

## 5. Comment and Documentation Rules

21. **Every public class and function** has a docstring. Use Google-style docstrings in Python.
    ```python
    def compute_quorum(votes: list[Vote], threshold: float) -> QuorumResult:
        """Determine whether votes meet the quorum threshold.

        Args:
            votes: Collected votes from the current consensus round.
            threshold: Fraction in (0, 1] required for quorum.

        Returns:
            QuorumResult with `reached` bool and `tally` breakdown.

        Raises:
            ValueError: If threshold is outside (0, 1].
        """
    ```

22. **Inline comments** explain *why*, never *what*. If the "what" is unclear, rename the variable or extract a function.
    ```python
    # Retry because the trust-lock TPM call is flaky under load  ✅
    # increment i by 1                                            ❌
    ```

23. **TODO format**: `# TODO(username): description — TICKET-123`. TODOs without a ticket number are rejected in CI.

24. **No commented-out code** in `main` or any release branch. Use version control.

---

## 6. ConsensusDevAgent-Specific Patterns

### 6.1 Path Security — Mandatory Write Validation

25. **Validate every path before any write operation.** No exceptions.
    ```python
    from path_security import validate_write_path

    safe_path = validate_write_path(user_supplied_path)  # raises on traversal
    with open(safe_path, "w") as f:
        f.write(content)
    ```
    Agents that skip this validation will have their PRs rejected by the pipeline gate.

### 6.2 Branch Naming

26. **All agent-created branches** follow this exact format:
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id`: the assigned engineer identifier (e.g., `eng-042`).
    - `subsystem_slug`: lowercase subsystem directory name (`dtl`, `cal`, `vtz`, etc.).
    - `N`: zero-padded 3