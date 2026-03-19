# Forge Architecture Context
# ─────────────────────────────────────────────────────────────────────────────
# This file is injected into EVERY code generation prompt.
# Fill it in from your TRDs. The more precise this file, the better the code.
# ─────────────────────────────────────────────────────────────────────────────

## Platform Overview
Forge is a runtime policy enforcement and cryptographic identity platform for
enterprise AI agents. It enforces agent execution at runtime, below the
application stack, via cryptographic identity and operator-defined policy.

## Core Subsystems

### CAL — Conversation Abstraction Layer
- Enforcement choke point for all agent-originated action
- No tool call, data read, API invocation, or agent handoff executes without
  passing through a CAL policy evaluation
- Sits above the VTZ enforcement plane, below application orchestration
- Key components: CPF, AIR, CTX-ID, PEE, TrustFlow/SIS, CAL Verifier Cluster

### CPF — Conversation Plane Filter
- Three-tier inspection and classification engine within CAL
- Tier 1: structural validation (schema, bounds checking)
- Tier 2: semantic classification (intent, data sensitivity, policy match)
- Tier 3: behavioral analysis (anomaly detection, attack pattern recognition)
- All tiers run synchronously in the enforcement path; fail closed

### CTX-ID — Context Identity
- Per-session, per-agent signed token binding identity, VTZ, policy, permissions
- Immutable once issued; rotation creates a new CTX-ID
- Fields: agent_id, session_id, vtz_scope, policy_revision, issued_at, sig

### VTZ — Virtual Trust Zone
- Cryptographically enforced identity-scoped segmentation domain
- Each agent session is bound to exactly one VTZ at CTX-ID issuance
- VTZ defines: allowed tools, data classifications, network egress, peer agents
- Enforcement is structural — not advisory

### DTL — Data Trust Labels
- Classification schema for all data flowing through Forge-protected agents
- Levels: PUBLIC, INTERNAL, CONFIDENTIAL, SECRET
- Labels are cryptographically bound to data at ingestion, immutable thereafter
- Label inheritance rules apply to derived/aggregated data

### TrustFlow
- Audit stream protocol between CAL Verifier Cluster and Stream Ingestion Service (SIS)
- All enforcement events emitted to TrustFlow in real time
- Records are signed and append-only
- Supports Forge Rewind (deterministic replay from TrustFlow stream)

### TrustLock
- Cryptographic machine identity anchored to TPM
- Provides the key material for CTX-ID signing, VTZ enforcement, and DTL binding
- Key hierarchy: root (TPM) → operator → agent session

### GCI — Global Context Identifier
- Cross-session, cross-agent correlation identifier
- Links related sessions, delegation chains, and tool call graphs

### MCP Policy Engine
- Enforces policy at the Model Context Protocol layer
- Validates tool definitions, tool calls, and tool results against VTZ policy
- Schema: tool_id, allowed_vtx_scopes, input_schema, output_classification

### Forge Connector SDK
- Standard integration surface for connecting enterprise systems to Forge
- Transport: stdio (local) or SSE (remote)
- Every connector must register with CAL and receive a CTX-ID before operating

### Forge Agent Template
- Securely deployable agent scaffold
- Includes: CTX-ID acquisition, VTZ-scoped tool registration, TrustFlow emission

## Endpoint Memory Budget (OI-13)
# CRITICAL: Fill this in before building any endpoint components.
# Three co-located components share the endpoint memory budget:
#   - Forge Agent
#   - Forge CAL
#   - AI Model Router / Token Optimizer
# Total budget: TBD (fill in from OI-13 resolution)
# Per-component allocation: TBD
ENDPOINT_MEMORY_BUDGET_MB = None  # Set this before building endpoint components

## Key Invariants (enforce in all generated code)
- Trust is never inferred implicitly — always asserted and verified explicitly
- All failures involving trust, identity, policy, or cryptography fail closed
- No silent failure paths anywhere
- All sensitive operations are authenticated, authorized, and auditable
- Secrets never appear in logs, error messages, or generated code
- All external input is treated as untrusted and validated strictly

## Protocol References
- CTX-ID wire format: JWT-like, signed with TrustLock agent key, fields above
- TrustFlow event schema: {event_id, session_id, ctx_id, ts, event_type, payload_hash, sig}
- DTL label wire format: {label_id, classification, source_id, issued_at, sig}
- VTZ enforcement decision: {ctx_id, tool_id, verdict: allow|restrict|block, reason}

## File Naming Conventions
- CAL components:     src/cal/<component>.py (or .go)
- DTL components:     src/dtl/<component>.py
- TrustFlow:          src/trustflow/<component>.py
- VTZ enforcement:    src/vtz/<component>.py
- TrustLock/crypto:   src/trustlock/<component>.py
- MCP engine:         src/mcp/<component>.py
- Connector SDK:      sdk/connector/<component>.py
- Tests mirror src:   tests/<subsystem>/test_<component>.py
