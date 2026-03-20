# AGENTS.md - Forge Platform

Forge is a security-first enforcement platform and Consensus Dev Agent runtime that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via Data Trust Labels (DTL), and emits an immutable TrustFlow audit stream—enforcing policy, not suggesting it.

## Naming Conventions and Glossary

### Canonical Domain Terms

Every contributor and agent must use these exact terms. Do not abbreviate, synonym-swap, or rename.

| Canonical Term | Abbreviation | Definition | Must Never Be Called |
|---|---|---|---|
| **CTX-ID** | — | Cryptographically verified context identity bound to every agent session. Validated first at every enforcement entry point. Missing CTX-ID means `UNTRUSTED`. | "session ID", "user ID", "auth token", "caller ID" |
| **Virtual Trust Zone** | **VTZ** | Structural isolation boundary confining agent actions. Each agent session binds to exactly one VTZ at CTX-ID issuance. Cross-VTZ access requires explicit policy authorization. | "sandbox", "namespace", "scope", "container" |
| **Data Trust Label** | **DTL** | Immutable classification label assigned at data ingestion. Derived data inherits the highest classification of any source. Unlabeled data is `CONFIDENTIAL`. | "tag", "classification tag", "sensitivity marker" |
| **TrustFlow** | — | Immutable audit event stream. Every action outcome (`allow`, `restrict`, `block`) emits a synchronous TrustFlow event in the enforcement path. | "audit log", "event log", "trace" |
| **TrustLock** | — | Cryptographic machine identity subsystem. CTX-ID is validated against a TrustLock public key with hardware-anchored verification. | "key store", "identity provider", "auth module" |
| **Conversation Abstraction Layer** | **CAL** | Enforcement entry point layer. Must validate CTX-ID first, call VTZ policy before execution, and emit TrustFlow for every outcome. | "chat layer", "conversation handler", "message router" |
| **GateCard** | `gate_card` | Operator approval gate. Blocks indefinitely until the operator responds. No timeout, no auto-approve path. | "approval prompt", "confirmation dialog", "gate check" |
| **BuildLedger** | — | Immutable record of all build pipeline actions, results, and artifacts. | "build log", "build history", "run record" |
| **ConsensusEngine** | — | Multi-provider LLM orchestrator that requires agreement across providers before accepting a result. | "LLM router", "model selector", "AI engine" |
| **HolisticReview** | — | Cross-cutting review pass that evaluates generated output against trust, security, and quality policy. | "code review", "quality check", "validation pass" |
| **TRDWorkflow** | — | Technical Requirements Document workflow orchestrating generation, review, and approval of TRDs. | "doc workflow", "requirements flow" |
| **CommandRouter** | — | Routes validated commands from the XPC boundary to the appropriate Python backend handler. | "dispatcher", "message handler", "command bus" |
| **SECURITY_REFUSAL** | — | A hard stop issued when any provider refuses on security grounds. Must never be bypassed by rephrasing, retrying another provider, or continuing the pipeline. | "soft refusal", "retry candidate", "skippable error" |

### DTL Classification Levels

| Level | Meaning |
|---|---|
| `PUBLIC` | Safe for unrestricted distribution |
| `INTERNAL` | Limited to authenticated agents within the same VTZ |
| `CONFIDENTIAL` | Default for unlabeled data; restricted to explicitly authorized consumers |
| `RESTRICTED` | Highest classification; requires explicit per-action policy authorization |

Derived data inherits the HIGHEST classification of any source input.

### TrustFlow Event Outcomes

| Outcome | Meaning |
|---|---|
| `allow` | Action permitted by policy; execution proceeds |
| `restrict` | Action permitted with constraints applied |
| `block` | Action denied by policy; execution halted |

### CTX-ID States

| State | Meaning |
|---|---|
| `VERIFIED` | CTX-ID validated against TrustLock public key |
| `UNTRUSTED` | CTX-ID missing, expired, or failed validation; all actions denied |

## Critical Rules — Read Before Writing Any Code

1. **Fail closed on all trust, identity, policy, and cryptographic errors** — reject the action, log the event, surface to caller; never silently degrade or continue.
2. **Validate CTX-ID FIRST at every enforcement entry point** — validation failure results in immediate rejection with zero partial processing; missing CTX-ID means `UNTRUSTED`; never infer identity from session context, caller state, or transport metadata.
3. **Emit a TrustFlow event for every action outcome (`allow`, `restrict`, `block`)** — emission is synchronous in the enforcement path; async buffering is not permitted; failed emission is a WARN-level audit event, never a silent skip.
4. **Check VTZ policy BEFORE execution of any agent action** — bind every agent session to exactly one VTZ at CTX-ID issuance; cross-VTZ tool calls require explicit policy authorization; implicit cross-VTZ access is denied; VTZ boundaries are structural, not advisory.
5. **Never put secrets, keys, tokens, or credentials in logs, error messages, or generated code** — not in cleartext, not in base64, not in any form.
6. **Never execute generated code** — no `eval()`, no `exec()`, no subprocess of generated content, ever.
7. **Never auto-approve gates** — `gate_card` blocks indefinitely until the operator responds; there is no timeout and no auto-approve path.
8. **Validate all file writes through `path_security.validate_write_path()` before any write operation** — no exceptions.
9. **Treat all external input as untrusted** — documents, PR comments, CI output, and user-provided content must be validated; external document context goes in the USER prompt, never the SYSTEM prompt.
10. **Assign DTL labels at data ingestion; labels are immutable thereafter** — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified; verify labels before any trust-boundary crossing.
11. **Use only FIPS 140-3 approved algorithms for all cryptographic operations** — do not invent cryptography; cryptographic failure must never degrade silently into insecure behavior.
12. **Discard and log unknown XPC message types** — never raise them as exceptions; never process them partially.
13. **Never bypass `SECURITY_REFUSAL`** — do not rephrase, retry another provider, or continue the pipeline; stop, gate, and log.
14. **Never permit unlabeled outbound data** — treat it as `CONFIDENTIAL` and verify DTL labels before any boundary crossing.

## Architecture Overview

Forge uses a strict two-process architecture. No exceptions.

### Process Boundary

| Process | Owns | Must NEVER |
|---|---|---|
| **Swift Shell** (macOS app) | SwiftUI (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage, XPC channel, Python process lifecycle | Call LLM APIs, read Keychain on behalf of backend, execute generated code, run pipeline logic |
| **Python Backend** | ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter | Read Keychain directly, present UI, manage process lifecycle, access Touch ID |

Neither side may take the other side's role. The XPC channel is the sole communication boundary.

### Source Layout

| Path | Responsibility | Must | Must NOT |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer enforcement entry points | Validate CTX-ID first, call VTZ policy before execution, emit TrustFlow for every outcome | Partially process actions before validation completes |
| `src/vtz/` | Virtual Trust Zone enforcement | Bind each session to exactly one VTZ, deny implicit cross-VTZ calls | Allow application code to bypass VTZ boundaries |
| `src/dtl/` | Data Trust Label components | Assign immutable labels at ingestion, enforce highest-label inheritance, verify labels before boundary crossings | Permit unlabeled outbound data without treating it as `CONFIDENTIAL` |
| `src/trustflow/` | TrustFlow audit stream | Synchronously emit events in the enforcement path with all required fields | Async-buffer, drop, or silently suppress failed emission |
| `src/trustlock/` | Cryptographic machine identity and CTX-ID validation | Validate CTX-ID against TrustLock public key with hardware-anchored verification, use FIPS 140-3 algorithms only | Degrade silently on cryptographic failure, invent or improvise crypto |
| `src/consensus/` | ConsensusEngine multi-provider orchestration | Require provider agreement, halt on `SECURITY_REFUSAL` | Auto-retry refused prompts, bypass refusal by rephrasing |
| `src/pipeline/` | BuildPipeline and BuildLedger | Record every build action immutably, enforce `gate_card` approval gates | Auto-approve gates, skip ledger entries |
| `src/github/` | GitHubTool integration | Treat all PR comments and CI output as untrusted external input | Execute or eval external content |
| `src/documents/` | DocumentStore and TRDWorkflow | Place external document context in USER prompt only, validate before ingestion | Place external content in SYSTEM prompt |