I'll implement all four artifacts: the canonical naming conventions document, the glossary, the Python naming module, and tests.

```python
# forge-standards/naming/__init__.py
"""
Forge canonical naming package.

Security: This package exports only frozen (immutable) constants and pure lookup
functions. No I/O, no secrets, no mutable state. All allocations are small
fixed-size frozen dataclasses -- no caches or buffers.
"""
```

```python
# forge-standards/naming/naming.py
"""
Canonical naming constants and normalization helpers for the Consensus Dev Agent.

Security assumptions:
- All inputs to lookup/normalization functions are treated as untrusted external input.
- No eval, exec, or dynamic code execution.
- No secrets stored or logged.
- All functions are pure (no I/O, no side effects, no mutable state).
- Fail closed: unrecognized names raise ValueError with context, never silently degrade.

Failure behavior:
- normalize_term() raises ValueError for empty, oversized, or unrecognized input.
- lookup_entity() raises KeyError for unknown canonical names.
- All error messages include the invalid input (truncated) for debugging -- never secrets.

Memory: All allocations are frozen dataclasses with fixed small field counts.
No caches, no buffers, no dynamic growth structures. OI-13 compliant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from typing import Dict, FrozenSet, Optional, Tuple

# --- OI-13: Maximum input length for any external string passed to normalization.
# Explicit allocation bound: 512 chars is well above any realistic term length.
_MAX_INPUT_LENGTH: int = 512  # OI-13: hard cap on input size to prevent allocation abuse


@dataclass(frozen=True)
class EntityNames:
    """Canonical entity names used across all TRDs.

    OI-13: 12 string fields, each < 64 bytes. Total < 1 KiB.
    """
    PR_SPEC: str = "PRSpec"
    PR_PLAN_ENTRY: str = "PRPlanEntry"
    BUILD_THREAD: str = "BuildThread"
    BUILD_LEDGER: str = "BuildLedger"
    CONSENSUS_ENGINE: str = "ConsensusEngine"
    BUILD_PIPELINE: str = "BuildPipeline"
    DOCUMENT_STORE: str = "DocumentStore"
    GITHUB_TOOL: str = "GitHubTool"
    WEBHOOK_RECEIVER: str = "WebhookReceiver"
    REVIEW_CYCLE: str = "ReviewCycle"
    OPERATOR_GATE: str = "OperatorGate"
    SECURITY_GATE: str = "SecurityGate"


@dataclass(frozen=True)
class StatusNames:
    """Canonical status/enum values for build and review states.

    Convention: UPPER_SNAKE_CASE for enum members, lowercase_snake for serialized form.

    OI-13: 14 string fields. Total < 1 KiB.
    """
    PENDING: str = "pending"
    CLAIMED: str = "claimed"
    IN_PROGRESS: str = "in_progress"
    GENERATING: str = "generating"
    REVIEWING: str = "reviewing"
    AWAITING_CI: str = "awaiting_ci"
    AWAITING_APPROVAL: str = "awaiting_approval"
    APPROVED: str = "approved"
    MERGED: str = "merged"
    FAILED: str = "failed"
    REJECTED: str = "rejected"
    CANCELLED: str = "cancelled"
    STALE: str = "stale"
    SECURITY_REFUSED: str = "security_refused"


@dataclass(frozen=True)
class IdentifierPrefixes:
    """Canonical prefixes for identifiers across the system.

    Convention: Identifiers are '{prefix}-{uuid4}' or '{prefix}-{sequential}'.

    OI-13: 8 string fields. Total < 512 bytes.
    """
    BUILD: str = "build"
    PR: str = "pr"
    THREAD: str = "thread"
    REVIEW: str = "review"
    GATE: str = "gate"
    CONSENSUS: str = "consensus"
    DOCUMENT: str = "doc"
    WEBHOOK: str = "webhook"


@dataclass(frozen=True)
class IPCMessageTypes:
    """Canonical IPC/XPC message type strings.

    Security: Unknown message types MUST be discarded and logged per Forge invariant.
    These are the ONLY valid types.

    OI-13: 10 string fields. Total < 512 bytes.
    """
    BUILD_START: str = "build.start"
    BUILD_PROGRESS: str = "build.progress"
    BUILD_COMPLETE: str = "build.complete"
    BUILD_FAILED: str = "build.failed"
    REVIEW_REQUEST: str = "review.request"
    REVIEW_RESULT: str = "review.result"
    GATE_PROMPT: str = "gate.prompt"
    GATE_RESPONSE: str = "gate.response"
    CONSENSUS_REQUEST: str = "consensus.request"
    CONSENSUS_RESULT: str = "consensus.result"


@dataclass(frozen=True)
class FileConventions:
    """Canonical file and path naming patterns.

    Convention: Python files use snake_case. Swift files use PascalCase.
    Test files mirror source with 'test_' prefix (Python) or 'Tests' suffix (Swift).

    OI-13: 6 string fields. Total < 256 bytes.
    """
    PYTHON_SOURCE_PATTERN: str = r"^[a-z][a-z0-9_]*\.py$"
    SWIFT_SOURCE_PATTERN: str = r"^[A-Z][A-Za-z0-9]*\.swift$"
    PYTHON_TEST_PREFIX: str = "test_"
    SWIFT_TEST_SUFFIX: str = "Tests"
    CONFIG_EXTENSION: str = ".json"
    MARKDOWN_EXTENSION: str = ".md"


@dataclass(frozen=True)
class ProcessBoundaryTerms:
    """Canonical terms for process-boundary concepts.

    These resolve ambiguities identified during TRD review:
    - 'generation' (not 'synthesis' or 'creation') for LLM code output
    - 'arbitration' (not 'adjudication' or 'voting') for consensus resolution
    - 'gate' (not 'checkpoint' or 'approval_step') for operator hold points

    OI-13: 8 string fields. Total < 512 bytes.
    """
    GENERATION: str = "generation"
    ARBITRATION: str = "arbitration"
    GATE: str = "gate"
    REVIEW_PASS: str = "review_pass"
    CI_EXECUTION: str = "ci_execution"
    MERGE: str = "merge"
    DECOMPOSITION: str = "decomposition"
    CLAIM: str = "claim"


# --- Singleton canonical instances ---
# OI-13: One instance each, frozen, module-level. No dynamic allocation.
ENTITIES: EntityNames = EntityNames()
STATUSES: StatusNames = StatusNames()
PREFIXES: IdentifierPrefixes = IdentifierPrefixes()
IPC_MESSAGES: IPCMessageTypes = IPCMessageTypes()
FILE_CONVENTIONS: FileConventions = FileConventions()
PROCESS_TERMS: ProcessBoundaryTerms = ProcessBoundaryTerms()


def _build_alias_map() -> Dict[str, str]:
    """Build a static map from known aliases/misspellings to canonical terms.

    OI-13: Fixed-size dict, ~60 entries, < 4 KiB total. Built once at import.
    No dynamic growth.

    Returns:
        Mapping from lowercase alias to canonical term string.
    """
    # Alias -> canonical name. Each alias is a known historical variant
    # found in TRDs or codebase that should normalize to the canonical form.
    aliases: Dict[str, str] = {
        # Entity aliases
        "prspec": ENTITIES.PR_SPEC,
        "pr_spec": ENTITIES.PR_SPEC,
        "pr spec": ENTITIES.PR_SPEC,
        "spec": ENTITIES.PR_SPEC,
        "prplanentry": ENTITIES.PR_PLAN_ENTRY,
        "pr_plan_entry": ENTITIES.PR_PLAN_ENTRY,
        "pr plan entry": ENTITIES.PR_PLAN_ENTRY,
        "plan_entry": ENTITIES.PR_PLAN_ENTRY,
        "planentry": ENTITIES.PR_PLAN_ENTRY,
        "buildthread": ENTITIES.BUILD_THREAD,
        "build_thread": ENTITIES.BUILD_THREAD,
        "build thread": ENTITIES.BUILD_THREAD,
        "thread": ENTITIES.BUILD_THREAD,
        "buildledger": ENTITIES.BUILD_LEDGER,
        "build_ledger": ENTITIES.BUILD_LEDGER,
        "build ledger": ENTITIES.BUILD_LEDGER,
        "ledger": ENTITIES.BUILD_LEDGER,
        "consensusengine": ENTITIES.CONSENSUS_ENGINE,
        "consensus_engine": ENTITIES.CONSENSUS_ENGINE,
        "consensus engine": ENTITIES.CONSENSUS_ENGINE,
        "consensus": ENTITIES.CONSENSUS_ENGINE,
        "buildpipeline": ENTITIES.BUILD_PIPELINE,
        "build_pipeline": ENTITIES.BUILD_PIPELINE,
        "build pipeline": ENTITIES.BUILD_PIPELINE,
        "pipeline": ENTITIES.BUILD_PIPELINE,
        "documentstore": ENTITIES.DOCUMENT_STORE,
        "document_store": ENTITIES.DOCUMENT_STORE,
        "document store": ENTITIES.DOCUMENT_STORE,
        "docstore": ENTITIES.DOCUMENT_STORE,
        "doc_store": ENTITIES.DOCUMENT_STORE,
        "githubtool": ENTITIES.GITHUB_TOOL,
        "github_tool": ENTITIES.GITHUB_TOOL,
        "github tool": ENTITIES.GITHUB_TOOL,
        "webhookreceiver": ENTITIES.WEBHOOK_RECEIVER,
        "webhook_receiver": ENTITIES.WEBHOOK_RECEIVER,
        "webhook receiver": ENTITIES.WEBHOOK_RECEIVER,
        "reviewcycle": ENTITIES.REVIEW_CYCLE,
        "review_cycle": ENTITIES.REVIEW_CYCLE,
        "review cycle": ENTITIES.REVIEW_CYCLE,
        "review": ENTITIES.REVIEW_CYCLE,
        "operatorgate": ENTITIES.OPERATOR_GATE,
        "operator_gate": ENTITIES.OPERATOR_GATE,
        "operator gate": ENTITIES.OPERATOR_GATE,
        "securitygate": ENTITIES.SECURITY_GATE,
        "security_gate": ENTITIES.SECURITY_GATE,
        "security gate": ENTITIES.SECURITY_GATE,
        # Process-boundary aliases
        "synthesis": PROCESS_TERMS.GENERATION,
        "creation": PROCESS_TERMS.GENERATION,
        "code_generation": PROCESS_TERMS.GENERATION,
        "adjudication": PROCESS_TERMS.ARBITRATION,
        "voting": PROCESS_TERMS.ARBITRATION,
        "checkpoint": PROCESS_TERMS.GATE,
        "approval_step": PROCESS_TERMS.GATE,
        "approval step": PROCESS_TERMS.GATE,
        "review pass": PROCESS_TERMS.REVIEW_PASS,
        "ci execution": PROCESS_TERMS.CI_EXECUTION,
        "ci_run": PROCESS_TERMS.CI_EXECUTION,
    }
    return aliases


# OI-13: Fixed alias map, built once. ~60 entries, < 4 KiB.
_ALIAS_MAP: Dict[str, str] = _build_alias_map()

# OI-13: Frozen set of all valid IPC message types for O(1) membership checks. ~10 entries.
_VALID_IPC_TYPES: FrozenSet[str] = frozenset(
    getattr(IPC_MESSAGES, f.name) for f in fields(IPC_MESSAGES)
)

# OI-13: Frozen set of all valid statuses. ~14 entries.
_VALID_STATUSES: FrozenSet[str] = frozenset(
    getattr(STATUSES, f.name) for f in fields(StatusNames)
)


def normalize_term(raw_input: str) -> str:
    """Normalize a potentially ambiguous term to its canonical form.

    Security:
    - Input is treated as untrusted external data.
    - Length-capped to prevent allocation abuse (OI-13).
    - Fails closed with ValueError on unrecognized input -- never returns a guess.

    Args:
        raw_input: The term to normalize. Must be a non-empty string <= 512 chars.

    Returns:
        The canonical term string.

    Raises:
        TypeError: If raw_input is not a string.
        ValueError: If raw_input is empty, too long, or not a recognized term/alias.
    """
    if not isinstance(raw_input, str):
        raise TypeError(
            f"normalize_term requires str, got {type(raw_input).__name__}"
        )

    if not raw_input or not raw_input.strip():
        raise ValueError("normalize_term: input must be non-empty")

    if len(raw_input) > _MAX_INPUT_LENGTH:
        # OI-13: Reject oversized input. Show truncated preview for debugging.
        preview = raw_input[:40]
        raise ValueError(
            f"normalize_term: input exceeds {_MAX_INPUT_LENGTH} chars "
            f"(got {len(raw_input)}). Preview: '{preview}...'"
        )

    # Normalize: strip, lowercase, collapse whitespace
    cleaned = re.sub(r"\s+", " ", raw_input.strip().lower())

    if cleaned in _ALIAS_MAP:
        return _ALIAS_MAP[cleaned]

    # Check if it's already a canonical value (case-insensitive match against known canonical terms)
    # OI-13: iterate alias values -- set is small (~20 unique values)
    canonical_values_lower = {v.lower(): v for v in _ALIAS_MAP.values()}
    if cleaned in canonical_values_lower:
        return canonical_values_lower[cleaned]

    raise ValueError(
        f"normalize_term: unrecognized term '{cleaned}'. "
        f"No alias or canonical match found. "
        f"Check GLOSSARY.md for valid terms."
    )


def lookup_entity(canonical_name: str) -> Optional[str]:
    """Look up an entity's canonical name, validating it exists.

    Security:
    - Input validated for type and length.
    - Fails closed with KeyError if the name is not a known canonical entity.

    Args:
        canonical_name: The exact canonical entity name (e.g., 'PRSpec').

    Returns:
        The canonical name string (identity, confirming validity).

    Raises:
        TypeError: If canonical_name is not a string.
        KeyError: If canonical_name is not a known canonical entity.
    """
    if not isinstance(canonical_name, str):
        raise TypeError(
            f"lookup_entity requires str, got {type(canonical_name).__name__}"
        )

    # OI-13: Small iteration over frozen dataclass fields (~12 fields)
    known_entities = {
        getattr(ENTITIES, f.name): f.name for f in fields(EntityNames)
    }

    if canonical_name in known_entities:
        return canonical_name

    raise KeyError(
        f"lookup_entity: '{canonical_name}' is not a canonical entity name. "
        f"Known entities: {sorted(known_entities.keys())}"
    )


def is_valid_ipc_type(message_type: str) -> bool:
    """Check whether a message type is a recognized IPC message type.

    Security:
    - Per Forge invariant, unknown XPC/IPC message types must be discarded and logged.
    - This function enables that check. Callers MUST discard and log if False.
    - Input validated for type; non-strings return False (fail closed).

    Args:
        message_type: The IPC message type string to validate.

    Returns:
        True if the message type is in the canonical set, False otherwise.
    """
    if not isinstance(message_type
