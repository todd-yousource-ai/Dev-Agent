

Looking at the improvements needed:

1. **Remove rejected alternatives as first-class constants** - they should only appear in the rejection mapping
2. **Add a rejected-alternatives normalization map** - already partially done but needs cleanup
3. **Separate enum member values into typed constant groups** - already partially done but needs proper typing
4. **Replace `_Frozen` with frozen dataclasses** - simplify the immutability pattern

Let me analyze the code carefully and apply these fixes:

```python
"""
Canonical naming constants for the Consensus Dev Agent codebase.

Security assumptions:
    - All values are frozen, immutable string constants defined at module level.
    - No external input is accepted or processed by this module.
    - No secrets, credentials, or PII are stored in any constant.
    - This module is safe to import from any security context.
    - No eval, exec, or dynamic code generation is used.

Failure behavior:
    - AttributeError on access of undefined constant (fail-closed, no fallback).
    - TypeError on any attempt to mutate frozen containers.
    - Import fails loudly if Python version lacks required features.

OI-13 allocation note:
    - All allocations are module-level frozensets/strings created once at import.
    - Total memory: ~4KB of interned string constants. No caches or buffers.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final


# ---------------------------------------------------------------------------
# Section: Entity Names
# Canonical names for core domain objects across all 12 TRDs.
# OI-13: Frozen dataclass, single instance, ~500 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Entities:
    """Canonical PascalCase names for core domain objects."""
    PR_SPEC: str = "PRSpec"
    BUILD_PLAN: str = "BuildPlan"
    BUILD_STEP: str = "BuildStep"
    CONSENSUS_RESULT: str = "ConsensusResult"
    ARBITRATION_RECORD: str = "ArbitrationRecord"
    REVIEW_CYCLE: str = "ReviewCycle"
    GATE_DECISION: str = "GateDecision"
    BUILD_LEDGER: str = "BuildLedger"
    CONSENSUS_ENGINE: str = "ConsensusEngine"
    BUILD_PIPELINE: str = "BuildPipeline"
    DOCUMENT_STORE: str = "DocumentStore"
    GITHUB_TOOL: str = "GitHubTool"
    WEBHOOK_RECEIVER: str = "WebhookReceiver"


ENTITIES: Final[_Entities] = _Entities()

# ---------------------------------------------------------------------------
# Section: Status Enum Type Names
# Canonical PascalCase names for status enumerations.
# OI-13: Frozen dataclass, single instance, ~200 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Statuses:
    """Canonical PascalCase names for status enum types."""
    BUILD_STATUS: str = "BuildStatus"
    STEP_STATUS: str = "StepStatus"
    CONSENSUS_OUTCOME: str = "ConsensusOutcome"
    GATE_VERDICT: str = "GateVerdict"
    REVIEW_PASS_RESULT: str = "ReviewPassResult"


STATUSES: Final[_Statuses] = _Statuses()

# ---------------------------------------------------------------------------
# Section: BuildStatus Values
# Canonical snake_case string values for BuildStatus enum members.
# Ref: TRD-3 build lifecycle states.
# OI-13: Frozen dataclass, single instance, ~240 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _BuildStatusValues:
    """Canonical member values for the BuildStatus enum."""
    PENDING: str = "pending"
    IN_PROGRESS: str = "in_progress"
    AWAITING_GATE: str = "awaiting_gate"
    APPROVED: str = "approved"
    REJECTED: str = "rejected"
    FAILED: str = "failed"


BUILD_STATUS_VALUES: Final[_BuildStatusValues] = _BuildStatusValues()

# ---------------------------------------------------------------------------
# Section: StepStatus Values
# Canonical snake_case string values for StepStatus enum members.
# Ref: TRD-3 step lifecycle states.
# OI-13: Frozen dataclass, single instance, ~200 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _StepStatusValues:
    """Canonical member values for the StepStatus enum."""
    PENDING: str = "pending"
    GENERATING: str = "generating"
    REVIEWING: str = "reviewing"
    COMPLETE: str = "complete"
    FAILED: str = "failed"


STEP_STATUS_VALUES: Final[_StepStatusValues] = _StepStatusValues()

# ---------------------------------------------------------------------------
# Section: ConsensusOutcome Values
# Canonical snake_case string values for ConsensusOutcome enum members.
# Ref: TRD-2 consensus resolution.
# OI-13: Frozen dataclass, single instance, ~160 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _ConsensusOutcomeValues:
    """Canonical member values for the ConsensusOutcome enum."""
    PROVIDER_A_SELECTED: str = "provider_a_selected"
    PROVIDER_B_SELECTED: str = "provider_b_selected"
    MERGED: str = "merged"
    FAILED: str = "failed"


CONSENSUS_OUTCOME_VALUES: Final[_ConsensusOutcomeValues] = _ConsensusOutcomeValues()

# ---------------------------------------------------------------------------
# Section: GateVerdict Values
# Canonical snake_case string values for GateVerdict enum members.
# These are operator-facing. Gates wait indefinitely; no auto-approve ever.
# Ref: TRD-3 operator gates.
# OI-13: Frozen dataclass, single instance, ~120 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _GateVerdictValues:
    """Canonical member values for the GateVerdict enum."""
    APPROVED: str = "approved"
    REJECTED: str = "rejected"
    PENDING: str = "pending"


GATE_VERDICT_VALUES: Final[_GateVerdictValues] = _GateVerdictValues()

# ---------------------------------------------------------------------------
# Section: ReviewPassResult Values
# Canonical snake_case string values for ReviewPassResult enum members.
# Ref: TRD-2 review cycle outcomes.
# OI-13: Frozen dataclass, single instance, ~120 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _ReviewPassResultValues:
    """Canonical member values for the ReviewPassResult enum."""
    PASS: str = "pass"
    FAIL: str = "fail"
    NEEDS_REVISION: str = "needs_revision"


REVIEW_PASS_RESULT_VALUES: Final[_ReviewPassResultValues] = _ReviewPassResultValues()

# ---------------------------------------------------------------------------
# Section: Identifier Names
# Canonical field/column/key names for identifiers.
# OI-13: Frozen dataclass, single instance, ~200 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Identifiers:
    """Canonical snake_case names for identifier fields."""
    BUILD_ID: str = "build_id"
    STEP_ID: str = "step_id"
    PR_NUMBER: str = "pr_number"
    CONSENSUS_RUN_ID: str = "consensus_run_id"
    SESSION_ID: str = "session_id"


IDENTIFIERS: Final[_Identifiers] = _Identifiers()

# ---------------------------------------------------------------------------
# Section: File / Path Naming Patterns
# Canonical module basenames and config file names.
# OI-13: Frozen dataclass, single instance, ~400 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Files:
    """Canonical file and path naming patterns."""
    CONSENSUS_MODULE: str = "consensus.py"
    BUILD_DIRECTOR_MODULE: str = "build_director.py"
    GITHUB_TOOLS_MODULE: str = "github_tools.py"
    BUILD_LEDGER_MODULE: str = "build_ledger.py"
    DOCUMENT_STORE_MODULE: str = "document_store.py"
    NAMING_MODULE: str = "naming.py"
    CONFIG_YAML: str = "config.yaml"
    SCHEMA_SUFFIX: str = "_schema.json"
    TEST_PREFIX: str = "test_"
    MIGRATION_PREFIX: str = "migrate_"


FILES: Final[_Files] = _Files()

# ---------------------------------------------------------------------------
# Section: Process-Boundary Terms
# Canonical names for inter-process / XPC / IPC concepts.
# OI-13: Frozen dataclass, single instance, ~240 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _ProcessBoundary:
    """Canonical names for inter-process communication concepts."""
    XPC_MESSAGE: str = "XPCMessage"
    XPC_CONNECTION: str = "XPCConnection"
    AGENT_REQUEST: str = "AgentRequest"
    AGENT_RESPONSE: str = "AgentResponse"
    GATE_PROMPT: str = "GatePrompt"
    OPERATOR_INPUT: str = "OperatorInput"


PROCESS_BOUNDARY: Final[_ProcessBoundary] = _ProcessBoundary()

# ---------------------------------------------------------------------------
# Section: LLM Provider Terms
# Canonical names for provider-related concepts per TRD-2.
# OI-13: Frozen dataclass, single instance, ~240 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _LLMProviders:
    """Canonical names for LLM provider concepts."""
    PROVIDER_A: str = "provider_a"
    PROVIDER_B: str = "provider_b"
    ARBITRATOR: str = "arbitrator"
    GENERATION_SYSTEM: str = "GENERATION_SYSTEM"
    SWIFT_GENERATION_SYSTEM: str = "SWIFT_GENERATION_SYSTEM"
    REVIEW_SYSTEM: str = "REVIEW_SYSTEM"


LLM_PROVIDERS: Final[_LLMProviders] = _LLMProviders()

# ---------------------------------------------------------------------------
# Section: Security-Critical Terms
# Canonical names per TRD-11. These terms have precise security meanings.
# OI-13: Frozen dataclass, single instance, ~200 bytes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Security:
    """Canonical names for security-critical concepts."""
    SECURITY_REFUSAL: str = "SECURITY_REFUSAL"
    PATH_VALIDATION: str = "validate_write_path"
    UNTRUSTED_INPUT: str = "untrusted_input"
    OPERATOR_GATE: str = "operator_gate"
    AUDIT_LOG_ENTRY: str = "AuditLogEntry"


SECURITY: Final[_Security] = _Security()

# ---------------------------------------------------------------------------
# Section: Rejected Alternatives → Canonical Mapping
# Maps ambiguous/rejected term strings to their canonical forms.
# Only canonical entity/status *type* names appear as values — rejected
# alternatives are keys only and are NOT first-class constants.
#
# Use resolve_term() for programmatic normalization of untrusted input.
# OI-13: MappingProxyType wrapping a dict of ~20 entries, ~800 bytes.
# ---------------------------------------------------------------------------

REJECTED_TO_CANONICAL: Final[MappingProxyType] = MappingProxyType({
    # Entity name ambiguities — values reference ENTITIES members
    "PRPlanEntry": ENTITIES.PR_SPEC,
    "PrSpec": ENTITIES.PR_SPEC,
    "pr_spec": ENTITIES.PR_SPEC,
    "BuildThread": ENTITIES.BUILD_LEDGER,
    "build_thread": ENTITIES.BUILD_LEDGER,
    "BuildRecord": ENTITIES.BUILD_LEDGER,
    "ConsensusOutput": ENTITIES.CONSENSUS_RESULT,
    "consensus_output": ENTITIES.CONSENSUS_RESULT,
    "ArbitrationResult": ENTITIES.ARBITRATION_RECORD,
    "arbitration_result": ENTITIES.ARBITRATION_RECORD,
    "ReviewPass": ENTITIES.REVIEW_CYCLE,
    "review_pass": ENTITIES.REVIEW_CYCLE,
    "GateResult": ENTITIES.GATE_DECISION,
    "gate_result": ENTITIES.GATE_DECISION,
    # Status enum type name ambiguities — values reference STATUSES members
    "build_state": STATUSES.BUILD_STATUS,
    "BuildState": STATUSES.BUILD_STATUS,
    "step_state": STATUSES.STEP_STATUS,
    "StepState": STATUSES.STEP_STATUS,
    "consensus_status": STATUSES.CONSENSUS_OUTCOME,
    "ConsensusStatus": STATUSES.CONSENSUS_OUTCOME,
    "gate_status": STATUSES.GATE_VERDICT,
    "GateStatus": STATUSES.GATE_VERDICT,
    "review_result": STATUSES.REVIEW_PASS_RESULT,
    "ReviewResult": STATUSES.REVIEW_PASS_RESULT,
})

# ---------------------------------------------------------------------------
# Convenience alias so callers can write: from naming import CANONICAL
# OI-13: No additional allocation — just a module-level reference.
# ---------------------------------------------------------------------------

CANONICAL: Final[_Entities] = ENTITIES


def _build_canonical_values() -> frozenset:
    """
    Collect all canonical string values from frozen dataclass instances.

    OI-13: Called once at module level. Result is a frozenset for O(1) lookup.
    """
    values: set = set()
    for container in (
        ENTITIES, STATUSES, IDENTIFIERS, PROCESS_BOUNDARY,
        LLM_PROVIDERS, SECURITY, FILES,
        BUILD_STATUS_VALUES, STEP_STATUS_VALUES,
        CONSENSUS_OUTCOME_VALUES, GATE_VERDICT_VALUES,
        REVIEW_PASS_RESULT_VALUES,
    ):
        for field in container.__dataclass_fields__:
            values.add(getattr(container, field))
    return frozenset(values)


# OI-13: Single frozenset allocation at module level, ~800 bytes.
# Contains all canonical values for O(1) membership testing.
_canonical_values: Final[frozenset] = _build_canonical_values()


def resolve_term(term: str) -> str:
    """
    Resolve an ambiguous or rejected domain term to its canonical form.

    This is the primary API for programmatic normalization of terms that
    may appear in LLM output, external documents, or legacy code.

    Security:
        - Input is treated as untrusted (may come from LLM output or external docs).
        - Only exact string matches against known canonical values and the
          rejection map are accepted.
        - No regex, no eval, no dynamic dispatch.
        - Returns canonical form or raises ValueError (fail-closed).

    Args:
        term: A domain term string to resolve.

    Returns:
        The canonical form of the term.

    Raises:
        ValueError: If the term is not recognized as either canonical or
                    a known rejected alternative. Includes the rejected term
                    in the error message for debugging (term is not a secret).
        TypeError: If term is not a string.
    """
    if not isinstance(term, str):
        raise TypeError(
            f"Term must be a string, got {type(term).__name__}. "
            "Canonical naming resolution requires string input."
        )

    # Fast path: already canonical
    if term in _canonical_values:
        return term

    # Check if it's a known rejected alternative
    canonical = REJECTED_TO_CANONICAL.get(term)
    if canonical is not None:
        return canonical

    raise ValueError(
        f"Unrecognized domain term '{term}'. "
        "Not found in canonical names or rejected alternatives. "
        "See GLOSSARY.md for authoritative definitions."
    )