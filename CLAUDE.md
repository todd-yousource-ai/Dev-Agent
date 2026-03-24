# CLAUDE.md

Crafted Dev Agent is a native macOS AI coding agent that decomposes build intents into ordered pull requests, generates code via dual-LLM consensus, enforces security policy at every stage, and gates on human operator approval before merging — all governed by Forge engineering standards including CTX-ID identity, VTZ policy boundaries, TrustFlow audit, and DTL data classification.

## Critical Rules — Read Before Writing Any Code

1. **Fail closed on all trust, identity, policy, cryptographic, credential, and generated-code safety errors** — reject the action, log the event, surface to the caller; never degrade silently into insecure behavior.
2. **CTX-ID must be validated FIRST at every enforcement entry point** — before any parsing, routing, policy lookup, tool call, or side effect. Validation failure results in immediate rejection with no partial processing. Missing CTX-ID means `UNTRUSTED` — never infer identity from session state, UI context, transport metadata, or prior requests.
3. **VTZ policy must be checked BEFORE execution of any agent action** — cross-VTZ tool calls require explicit policy authorization; implicit access is denied; VTZ boundaries are structural, not advisory.
4. **Every action outcome (allow, restrict, block) must emit a TrustFlow event synchronously in the enforcement path** — each event must include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`. Async buffering is not permitted. Failed emission is a WARN-level audit event, never a silent skip.
5. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as `CONFIDENTIAL`; label stripping is a security event that must be audited.
6. **Secrets, keys, tokens, and credentials must never appear in logs, error messages, generated code, or prompt content** — protect in memory, at rest, and in transit; never hardcode.
7. **All external input (documents, PR comments, CI output, XPC messages, user-supplied paths) is untrusted** — validate strictly before use; all file writes must pass `path_security.validate_write_path()` before execution.
8. **Generated code is never executed by the agent** — no `eval`, no `exec`, no subprocess of generated content under any circumstances.
9. **Gates wait indefinitely for operator input** — no auto-approve ever; `gate_card` blocks until the human responds.
10. **Context from external documents goes in the USER prompt, never the SYSTEM prompt** — `SECURITY_REFUSAL` output is never bypassed by rephrasing, retrying, or moving content into the system prompt. Stop, gate, log.
11. **XPC unknown message types are discarded and logged** — never raised as exceptions; wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.
12. **Fix arbitration uses `_score_fix()` based on assertion token overlap** — length-based fix arbitration (`max(..., key=len)`) is BANNED; fix loop strategy is failure-type-aware via `_choose_strategy(failure_type, attempt, records)`.

## Architecture Overview

Crafted Dev Agent is a **two-process architecture**: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub).

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **App Shell (TRD-1)** | `Crafted/` | UI, native macOS auth, Keychain, XPC boundary handling | Implement backend consensus, policy shortcuts, or trust inference |
| **Shell Tests** | `CraftedTests/` | XCTest coverage for Swift shell contracts | Replace backend negative-path enforcement tests |
| **Agent Entry (TRD-2)** | `src/agent.py` | Request routing through enforcement and pipeline stages | Bypass validation or stage checkpoints |
| **Build Director (TRD-3)** | `src/build_director.py` | Pipeline orchestration, confidence gate, `pr_type` routing, ordered stage execution, operator gates | Auto-approve, skip completed-stage checkpoints |
| **Consensus Engine (TRD-4)** | `src/consensus.py` | `ConsensusEngine` parallel generation and arbitration; must call `_consensus.run(..., language=spec.language)` with explicit language | Use length-based fix arbitration |
| **Providers (TRD-5)** | `src/providers.py` | Provider integrations for Claude and OpenAI; isolate provider-specific behavior | Leak credentials, secrets, or raw sensitive context |
| **Build Ledger (TRD-6)** | `src/build_ledger.py` | Multi-engineer coordination; preserve durable coordination state | Clear persistent build memory or build rules automatically |
| **Path Security** | `src/path_security.py` | `validate_write_path()` on every file write | Allow path traversal or writes outside approved directories |
| **TrustFlow Audit** | `src/trustflow.py` | Synchronous emission of audit events with required fields | Buffer events asynchronously or silently drop failures |

## CTX-ID Identity Contract

- Every request entering the enforcement boundary must carry a `CTX-ID` header or field.
- `CTX-ID` is validated against the identity store before any downstream processing.
- Validation checks: format conformance, existence in registry, non-revoked status.
- On validation failure: immediately return rejection; emit TrustFlow event with `event_type: "ctx_id_validation_failure"`; perform zero partial processing.
- `CTX-ID` is propagated through every internal call chain and recorded on every TrustFlow event.

## VTZ Policy Boundaries

- Each agent action is scoped to a Virtual Trust Zone.
- Before execution, the enforcement layer must resolve the action's target VTZ and confirm the caller's `CTX-ID` holds an explicit grant for that zone.
- Cross-VTZ tool calls require an explicit policy entry; absence of a grant means DENY.
- VTZ boundaries are structural and enforced in code — they are never advisory or documentation-only.
- VTZ violations emit a TrustFlow event with `event_type: "vtz_violation"` and halt the action.

## TrustFlow Audit Protocol

Every enforcement decision emits a TrustFlow event with these required fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID)` | Unique identifier for this event |
| `session_id` | `string` | Session scope for correlation |
| `ctx_id` | `string` | CTX-ID of the acting principal |
| `ts` | `string (ISO 8601)` | Timestamp at point of emission |
| `event_type` | `string` | Canonical event type (e.g., `action_allowed`, `action_blocked`, `ctx_id_validation_failure`, `vtz_violation`, `dtl_label_strip_attempt`) |
| `payload_hash` | `string (SHA-256)` | Integrity hash of the event payload |

- Emission is synchronous — it must complete before the enforcement path continues.
- If emission fails, log a WARN-level audit event locally; never silently skip.
- TrustFlow events are append-only; retroactive modification is prohibited.

## DTL Data Classification

| Label | Handling |
|---|---|
| `PUBLIC` | No restrictions on transit or display |
| `INTERNAL` | Must not leave the agent boundary without explicit policy |
| `CONFIDENTIAL` | Default for unlabeled data; encrypted at rest; restricted display |
| `RESTRICTED` | Encrypted at rest and in transit; access requires explicit per-field grant |

- Labels are assigned at ingestion and are immutable for the lifetime of the data.
- Derived data inherits the highest classification of all source data.
- Any attempt to strip or downgrade a label emits a TrustFlow event with `event_type: "dtl_label_strip_attempt"` and is denied.

## Consensus Engine Rules

- Dual-LLM generation: both providers generate independently; results are arbitrated.
- `_consensus.run(..., language=spec.language)` — the `language` parameter must always be passed explicitly.
- Fix arbitration: `_score_fix()` scores on assertion token overlap. Length-based selection (`max(..., key=len)`) is permanently banned.
- Fix loop strategy: `_choose_strategy(failure_type, attempt, records)` selects strategy based on failure type, not attempt count alone.

## XPC Wire Format

- Line-delimited JSON over XPC.
- Every message is nonce-authenticated.
- Maximum message size: 16 MB.
- Unknown message types are discarded and logged — never raised as exceptions.
- Malformed messages are discarded and logged — never partially parsed.

## Gate Protocol

- `gate_card` blocks indefinitely until the human operator responds.
- No timeout-based auto-approve exists or may be added.
- Gate cards present the full action summary, affected files, and classification labels.
- Operator approval is recorded as a TrustFlow event before the action proceeds.

## File Write Security

- Every file write must pass `path_security.validate_write_path()` before execution.
- Path traversal patterns (`../`, symlink escapes, null bytes) must be rejected.
- Writes outside the approved project directory are denied unconditionally.
- Validation failure emits a TrustFlow event and halts the write.

## Prompt Boundary Enforcement

- External document content is placed in the USER prompt, never the SYSTEM prompt.
- `SECURITY_REFUSAL` is a terminal output state — it must not be bypassed by rephrasing, retrying, prompt restructuring, or escalation.
- On `SECURITY_REFUSAL`: stop execution, emit gate card, emit TrustFlow event, wait for operator.

## Secrets Management

- Secrets, keys, tokens, and credentials must never appear in: logs, error messages, generated code, prompt content, XPC messages, TrustFlow event payloads, or UI surfaces.
- Secrets are retrieved from Keychain at point of use and are never cached in plaintext outside secure memory.
- Secret exposure in any channel is a security event requiring immediate TrustFlow emission and operator notification.