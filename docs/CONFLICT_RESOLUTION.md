docs/CONFLICT_RESOLUTION.md:

# Cross-TRD Conflict Resolution Hierarchy

**Document Status:** Canonical Source of Truth -- Normative  
**Version:** 1.0  
**Author:** ConsensusDevAgent / YouSource.ai  
**Date:** 2026-03-20  
**Authority:** PRD-001 (Product Foundation, Repository Bootstrap, and Cross-TRD Contract Baseline)  
**Scope:** All 16 TRDs governing the Consensus Dev Agent platform  

---

## Purpose

This document is the **single authoritative source** for resolving conflicts, ambiguities, and overlapping concerns across the 16 Technical Requirements Documents (TRDs) that govern the Forge platform. When two or more TRDs specify contradictory behavior, this document determines which specification prevails.

**All implementers, reviewers, and AI agents MUST consult this document when a cross-TRD ambiguity is encountered.** Guessing or inferring precedence without reference to this document is a process violation.

---

## Precedence Hierarchy

The Forge platform enforces a strict 4-tier precedence hierarchy. When specifications conflict, the higher tier wins unconditionally within its defined scope.

### Tier 1 -- Security Override (TRD-11)

**TRD-11 (Security Architecture) overrides ALL other TRDs on any matter classified as security-relevant** per the Security Conflict Classification criteria defined below.

- No exceptions. No escalation path bypasses this tier.
- If TRD-11 specifies a behavior and another TRD contradicts it on a security matter, TRD-11 wins.
- This tier applies **only** to security matters. TRD-11 does not override non-security domain decisions. See [Security Conflict Classification](#security-conflict-classification) for scoping criteria.

### Tier 2 -- Domain Authority (Owning TRD)

Each TRD has a designated **primary domain**. Within that domain, the owning TRD is authoritative.

- If TRD-3 defines build pipeline stage ordering and TRD-14 references a different ordering, TRD-3 governs (because pipeline stages are TRD-3's primary domain).
- Domain ownership is defined in the [Domain Ownership Map](#domain-ownership-map) below.
- Cross-cutting concerns (where two TRDs have legitimate domain claims) are resolved by explicit entries in the [Resolved Conflicts](#resolved-conflicts) table.

### Tier 3 -- Standards Tiebreak (AGENTS.md, CLAUDE.md)

When two TRDs have **equal domain claim** over a matter and no explicit resolution exists in this document:

- AGENTS.md and CLAUDE.md serve as the tiebreaker.
- If these standards documents address the matter, their guidance prevails.
- If AGENTS.md and CLAUDE.md conflict with each other, AGENTS.md wins (it is the platform-level standard; CLAUDE.md is provider-specific).

### Tier 4 -- Best-Practice Default

When no TRD, no standards document, and no conflict resolution entry addresses a question:

- Industry best practices apply.
- The chosen practice MUST be documented with rationale in the implementing PR.
- A follow-up amendment to this document SHOULD be filed to canonicalize the decision.
- For security-adjacent matters at this tier, the **fail-closed** principle applies: choose the more restrictive option.

### Tier Summary

| Tier | Source | Scope | Override Power |
|------|--------|-------|----------------|
| 1 | TRD-11 (Security Architecture) | Security-relevant matters only | Absolute -- overrides all TRDs |
| 2 | Owning TRD | Primary domain of that TRD | Authoritative within domain |
| 3 | AGENTS.md, CLAUDE.md | Tiebreaker for equal domain claims | Advisory, normative on ties |
| 4 | Industry best practice | Unaddressed questions | Default -- must document rationale |

---

## Security Conflict Classification

TRD-11's Tier 1 override is powerful and must be scoped precisely. The following criteria determine whether a conflict is **security-relevant** (and thus governed by Tier 1) or **non-security** (governed by Tier 2+).

### A conflict is security-relevant if it involves ANY of the following

| # | Criterion | Examples |
|---|-----------|----------|
| S1 | **Secrets or credentials** -- storage, transmission, rotation, or lifecycle of any secret material | API keys, tokens, passwords, signing keys, Keychain entries |
| S2 | **Authentication or authorization flows** -- how identity is verified or access is granted/denied | OAuth flows, token validation, session management, identity binding |
| S3 | **Cryptographic operations** -- selection of algorithms, key sizes, modes, or certificate handling | TLS configuration, hashing algorithms, encryption at rest |
| S4 | **Access control boundaries** -- what subjects can access what resources under what conditions | Sandbox permissions, file system access, XPC entitlements, IPC authorization |
| S5 | **Data protection and privacy** -- handling of sensitive user/operator data, PII, or audit-sensitive information | Log redaction, data classification, retention policies |
| S6 | **Keychain and secure storage access** -- any interaction with macOS Keychain or equivalent secure enclaves | Keychain item creation, retrieval, ACL configuration |
| S7 | **Input validation for security boundaries** -- validation that prevents injection, path traversal, or privilege escalation | Path validation, command injection prevention, XPC message validation |
| S8 | **Audit and security logging** -- log entries required for security forensics or compliance | Authentication events, access denied events, secret rotation events |
| S9 | **Fail-closed behavior** -- whether a system fails open or closed on error | Auth failure handling, crypto error handling, identity verification failure |

### A conflict is NOT security-relevant if

- It concerns **performance tuning** (timeouts, intervals, batch sizes) with no security implications.
- It concerns **code style or formatting** conventions.
- It concerns **UI/UX behavior** that does not affect access control or data protection.
- It concerns **build ordering or CI stage sequencing** that does not affect security gate enforcement.
- It concerns **logging verbosity** for non-security-sensitive operational data.

### Edge Cases

When a conflict has **both security and non-security dimensions**, decompose it:

1. The security dimension is governed by Tier 1 (TRD-11).
2. The non-security dimension is governed by Tier 2 (owning TRD).
3. If the dimensions cannot be cleanly separated, Tier 1 governs the entire conflict. **When in doubt, classify as security-relevant.** This is fail-closed reasoning applied to classification itself.

### Over-Application Prevention

To prevent TRD-11 from being invoked as a blanket override for non-security matters:

- Every Tier 1 invocation MUST cite **at least one specific criterion** (S1-S9) from the table above.
- A Tier 1 invocation that cannot cite a specific criterion is invalid and defaults to Tier 2.
- The amendment process (below) is available to add new security criteria if a genuine gap is found.

---

## Domain Ownership Map

Each TRD has a **primary domain** (its authoritative scope) and may have **cross-cutting concerns** (areas where it touches another TRD's domain and defers to it, or where explicit conflict resolutions apply).

| TRD | Title | Primary Domain | Cross-Cutting Concerns |
|-----|-------|---------------|----------------------|
| TRD-1 | macOS Application Shell | Application lifecycle, XPC transport, native UI shell, Keychain integration | Security (defers to TRD-11), Health monitoring (defers to TRD-12), IPC error semantics (see CR-010) |
| TRD-2 | Consensus Engine | LLM orchestration, dual-provider consensus, arbitration, response synthesis | Retry policies (see CR-008), IPC error codes (see CR-010), Build pipeline integration (defers to TRD-3) |
| TRD-3 | Build Pipeline | CI/CD pipeline stages, build ordering, stage gates, artifact management | Code quality enforcement (see CR-002), Retry policies (see CR-008), Testing (defers to TRD-16) |
| TRD-4 | Multi-Agent Coordination | Agent task assignment, conflict detection, coordination protocol, ledger writes | State management (defers to TRD-13), Security (defers to TRD-11) |
| TRD-5 | GitHub Integration | GitHub API interactions, PR lifecycle, branch management, webhook handling | Build triggering (defers to TRD-3), Security for token handling (defers to TRD-11) |
| TRD-6 | Holistic Code Review | Code review orchestration, review pass structure, review criteria | Code quality thresholds (defers to TRD-14), Consensus generation (defers to TRD-2) |
| TRD-7 | TRD Development Workflow | TRD authoring, versioning, review, and publishing lifecycle | Document storage (defers to TRD-10), GitHub workflow (defers to TRD-5) |
| TRD-8 | LLM Provider Abstraction | Provider interface contracts, model selection, token management, rate limiting | Security for API keys (defers to TRD-11), Consensus (defers to TRD-2) |
| TRD-9 | Prompt Engineering | Prompt templates, context assembly, system/user prompt separation, prompt security | Security for prompt injection prevention (defers to TRD-11), LLM providers (defers to TRD-8) |
| TRD-10 | Document Store | Document ingestion, indexing, retrieval, embedding management | Security for document classification (defers to TRD-11), TRD workflow (defers to TRD-7) |
| TRD-11 | Security Architecture | Authentication, authorization, secrets management, crypto, Keychain ACLs, audit logging, input validation, sandboxing | **Cross-cutting authority on all security matters across all TRDs (Tier 1)** |
| TRD-12 | Health & Diagnostics | Health checks, system metrics, diagnostic logging, alerting, startup probes | Startup lifecycle (see CR-001, CR-007), Logging levels (see CR-005) |
| TRD-13 | Recovery & State Management | Crash recovery, state persistence, checkpoint/restore, session management | Build pipeline state (defers to TRD-3), Multi-agent state (defers to TRD-4) |
| TRD-14 | Code Quality & CI Pipeline | Quality gates, linting, static analysis, coverage thresholds, formatting | Build pipeline integration (see CR-002), Testing (defers to TRD-16) |
| TRD-15 | Runbook & Operations | Operational procedures, incident response, deployment checklists | Health diagnostics (defers to TRD-12), Recovery (defers to TRD-13) |
| TRD-16 | Agent Testing & Validation | Test strategy, test harness, validation criteria, test execution | Build pipeline integration (defers to TRD-3), Code quality (defers to TRD-14) |

---

## Resolved Conflicts

Each conflict resolution follows a structured format. All resolutions are **normative** -- implementers MUST follow them.

---

### CR-001: Startup Timeout Values

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §Startup Lifecycle) vs. TRD-12 (Health & Diagnostics, §Startup Probes) |
| **Description** | TRD-1 defines application startup timeout behavior for the macOS shell (e.g., maximum time for XPC service initialization). TRD-12 defines health check startup probes with their own timeout and grace period semantics. When both apply during application launch, conflicting timeout values could cause premature termination or missed health failures. |
| **Resolution** | **TRD-1 governs the application-level startup timeout (30 seconds maximum for full shell initialization).** TRD-12 governs the health subsystem's startup probe configuration, which MUST operate within TRD-1's startup window. Specifically: TRD-1 startup timeout = **30 seconds**. TRD-12 startup probe initial delay = **5 seconds**, with probe interval = **3 seconds**, failure threshold = **3 consecutive failures**. The health subsystem MUST NOT declare startup failure before TRD-1's startup sequence completes or times out. |
| **Rationale** | TRD-1 owns the application lifecycle domain (Tier 2). The startup timeout is fundamentally a lifecycle concern. TRD-12's health probes are diagnostic and MUST be subordinate to the lifecycle owner during startup. Setting TRD-12's initial delay to 5s prevents false negatives during early initialization. |
| **Scope/Impact** | Application shell startup sequence, health check initialization, XPC service readiness detection. |

---

### CR-002: Code Quality Gate Thresholds

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-3 (Build Pipeline, §Stage Gates) vs. TRD-14 (Code Quality & CI Pipeline, §Quality Gates) |
| **Description** | TRD-3 defines pipeline stage gates that include code quality checks as pass/fail criteria. TRD-14 defines detailed quality gate thresholds (coverage minimums, lint scores, complexity limits). Both claim authority over what constitutes a "passing" quality gate. |
| **Resolution** | **TRD-14 is authoritative for quality gate threshold definitions** (what the thresholds are, which tools run, what scores pass). **TRD-3 is authoritative for gate enforcement mechanics** (when gates run in the pipeline, what happens on failure, retry behavior, stage ordering). Canonical thresholds defined by TRD-14: test coverage ≥ 80%, zero critical lint violations, cyclomatic complexity ≤ 15 per function, no security-flagged findings (this last criterion defers to TRD-11 under Tier 1). TRD-3 defines that these gates execute at Stage 4 (Quality Gate) and that failure is a hard block (no bypass without operator approval). |
| **Rationale** | TRD-14's primary domain is code quality definitions. TRD-3's primary domain is pipeline orchestration. Splitting definition from enforcement respects both domains. |
| **Scope/Impact** | CI pipeline configuration, quality gate tooling, PR merge requirements, coverage reporting. |

---

### CR-003: Configuration Key Naming Conventions

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1, TRD-2, TRD-3, TRD-8, TRD-12, TRD-13 (multiple TRDs define configuration keys without unified convention) |
| **Description** | Multiple TRDs independently define configuration keys (e.g., timeout values, feature flags, thresholds) using inconsistent naming: some use `camelCase`, some use `snake_case`, some use dot-separated hierarchical keys, and some use flat keys. This creates collision risk and integration confusion. |
| **Resolution** | **All configuration keys MUST follow this canonical convention:** `<trd_domain>.<subsystem>.<parameter>` using `snake_case` throughout. Examples: `app_shell.startup.timeout_seconds`, `consensus.arbitration.max_retries`, `build_pipeline.quality_gate.coverage_minimum`, `health.probe.interval_seconds`, `security.keychain.acl_mode`. Domain prefixes map to TRD ownership per the Domain Ownership Map. No TRD may define a key under another TRD's domain prefix without explicit cross-reference. |
| **Rationale** | Tier 3 (AGENTS.md) mandates consistency and explicit naming. Dot-separated hierarchical naming with snake_case is the most unambiguous format, prevents collisions via domain namespacing, and aligns with industry practice for configuration systems. |
| **Scope/Impact** | All configuration files, environment variables (converted with `__` separator: `APP_SHELL__STARTUP__TIMEOUT_SECONDS`), default value registries, documentation. |
| **Follow-On Guidance** | Each TRD SHOULD publish its canonical key list in an appendix. A unified configuration schema registry is recommended as future work. |

---

### CR-004: Error Taxonomy and Code Ranges

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1, TRD-2, TRD-3, TRD-4, TRD-5, TRD-8, TRD-11, TRD-12, TRD-13 (multiple TRDs define error codes/categories that can collide) |
| **Description** | Several TRDs define error codes or error categories independently. Without reserved ranges, two TRDs could assign the same numeric error code to different error conditions, causing misrouted error handling and ambiguous diagnostics. |
| **Resolution** | **Each TRD is assigned a non-overlapping error code range of 1000 codes.** Error codes are integers. The ranges are: |

| TRD | Range | Domain |
|-----|-------|--------|
| TRD-1 | 1000-1999 | Application Shell |
| TRD-2 | 2000-2999 | Consensus Engine |
| TRD-3 | 3000-3999 | Build Pipeline |
| TRD-4 | 4000-4999 | Multi-Agent Coordination |
| TRD-5 | 5000-5999 | GitHub Integration |
| TRD-6 | 6000-6999 | Code Review |
| TRD-7 | 7000-7999 | TRD Workflow |
| TRD-8 | 8000-8999 | LLM Provider |
| TRD-9 | 9000-9999 | Prompt Engineering |
| TRD-10 | 10000-10999 | Document Store |
| TRD-11 | 11000-11999 | Security |
| TRD-12 | 12000-12999 | Health & Diagnostics |
| TRD-13 | 13000-13999 | Recovery & State |
| TRD-14 | 14000-14999 | Code Quality |
| TRD-15 | 15000-15999 | Runbook & Operations |
| TRD-16 | 16000-16999 | Testing & Validation |
| Reserved | 0-999 | Platform-wide / generic errors |
| Reserved | 17000-19999 | Future TRDs |
| Reserved | 20000+ | Vendor/extension codes |

| Field | Value |
|-------|-------|
| **Rationale** | Numeric ranges keyed to TRD number provide zero-collision guarantee and instant source identification. The 1000-code range per TRD provides ample room for granular error definitions. |
| **Scope/Impact** | All error handling code, error logging, diagnostic output, error documentation. All existing TRD-specific error codes MUST be migrated to their assigned range. |

---

### CR-005: Logging Level Definitions

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-12 (Health & Diagnostics, §Logging) vs. TRD-1, TRD-2, TRD-3, TRD-11 (various logging references with inconsistent level semantics) |
| **Description** | TRD-12 defines a logging framework with level semantics (DEBUG, INFO, WARN, ERROR, FATAL). Other TRDs reference logging levels but use inconsistent definitions (e.g., some treat WARN as "action may be needed" while others treat it as "informational anomaly"; some TRDs use CRITICAL instead of FATAL). |
| **Resolution** | **TRD-12 is authoritative for all logging level definitions.** The canonical levels and their semantics are: |

| Level | Numeric | Semantics | When to Use |
|-------|---------|-----------|-------------|
| `TRACE` | 5 | Fine-grained diagnostic detail | Internal loop iterations, variable dumps (never in production default) |
| `DEBUG` | 10 | Diagnostic information for developers | Function entry/exit, state transitions, decision points |
| `INFO` | 20 | Normal operational events | Startup complete, stage transitions, successful operations |
| `WARN` | 30 | Unexpected condition, operation continues | Retry triggered, fallback path taken, deprecated usage detected |
| `ERROR` | 40 | Operation failed, system continues | Request failed, stage failed, recoverable fault |
| `FATAL` | 50 | System cannot continue | Unrecoverable state, security violation requiring shutdown |

| Field | Value |
|-------|-------|
| **Rationale** | TRD-12's primary domain is diagnostics and logging (Tier 2). Unified level semantics prevent log analysis confusion. `CRITICAL` is **not** a valid level -- all TRDs using it MUST migrate to `FATAL`. The numeric values enable programmatic comparison. |
| **Scope/Impact** | All logging calls across all subsystems, log aggregation configuration, alert threshold definitions. |
| **Follow-On Guidance** | Security audit events (TRD-11) MUST be logged at `INFO` or above and MUST include the `security` log category tag regardless of level. Secrets MUST NEVER appear in log messages at any level -- this is a Tier 1 (TRD-11) constraint. |

---

### CR-006: Security Enforcement Scope

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-11 (Security Architecture) vs. all other TRDs (cross-cutting authority boundaries) |
| **Description** | TRD-11 is designated as cross-cutting for security, but without explicit scoping, implementers may either under-apply TRD-11 (missing security requirements) or over-apply it (using TRD-11 to override non-security domain decisions). |
| **Resolution** | **TRD-11's override authority (Tier 1) applies if and only if the conflict meets at least one criterion in the Security Conflict Classification (S1-S9) defined above.** For any cross-TRD conflict: (1) check if any S1-S9 criterion applies; (2) if yes, TRD-11 governs that dimension; (3) if no, Tier 2 (domain authority) governs. TRD-11 does NOT have authority over: pipeline stage ordering (TRD-3), consensus algorithm selection (TRD-2), UI layout (TRD-1), test strategy (TRD-16), or document formatting (TRD-7) -- unless a security dimension (S1-S9) is specifically implicated. |
| **Rationale** | Precise scoping of Tier 1 prevents governance creep while maintaining ironclad security. The S1-S9 criteria provide an auditable checklist. |
| **Scope/Impact** | All cross-TRD conflict resolution decisions, all code review evaluations of security requirements. |

---

### CR-007: Health Check Interval vs. Startup Grace Period

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §Lifecycle) vs. TRD-12 (Health & Diagnostics, §Health Checks) |
| **Description** | TRD-12 defines ongoing health check intervals for runtime monitoring. TRD-1 defines a startup grace period during which the application is initializing and may not be fully healthy. If health checks fire during the grace period, they generate false-negative health reports and may trigger unnecessary recovery actions (TRD-13). |
| **Resolution** | **TRD-1 defines the startup grace period: 30 seconds from process launch.** During this period, TRD-12 health checks MUST operate in **startup probe mode** (lenient): they record results but MUST NOT trigger alerts or recovery actions. After the grace period expires (or TRD-1 signals startup-complete, whichever comes first), TRD-12 transitions to **liveness probe mode** (strict) with standard intervals. Runtime health check interval (post-startup): **10 seconds**. Startup probe interval: **3 seconds** (higher frequency for faster readiness detection). Failure threshold for triggering recovery (post-startup only): **3 consecutive failures**. |
| **Rationale** | TRD-1 owns lifecycle (Tier 2) and thus defines when the application is "started." TRD-12 owns health monitoring (Tier 2) and defines how checks work. The startup-complete signal bridges the two domains cleanly. |
| **Scope/Impact** | Health check subsystem initialization, recovery trigger logic (TRD-13), startup sequence coordination. |

---

### CR-008: Retry Policy Defaults

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-2 (Consensus Engine, §Retry Behavior) vs. TRD-3 (Build Pipeline, §Stage Retry) |
| **Description** | TRD-2 defines retry policies for LLM provider calls (consensus generation, arbitration). TRD-3 defines retry policies for pipeline stage execution. The two TRDs use different default values for max retries, backoff strategy, and timeout-per-attempt, creating confusion when a pipeline stage invokes the consensus engine (nested retry context). |
| **Resolution** | **Each TRD governs retries within its own domain.** TRD-2 retry defaults (LLM provider calls): max retries = **3**, backoff = **exponential with jitter (base 2s, max 30s)**, timeout per attempt = **120 seconds**. TRD-3 retry defaults (pipeline stages): max retries = **2**, backoff = **linear (10s interval)**, timeout per stage = **300 seconds**. **Nested retry rule:** When a pipeline stage (TRD-3) invokes the consensus engine (TRD-2), retries are NOT multiplicative. The TRD-2 retry budget executes within a single TRD-3 attempt. TRD-3 counts a stage attempt as failed only after TRD-2 has exhausted its own retry budget. Maximum wall-clock time for a stage invoking consensus: TRD-3 timeout (300s) is the outer bound; TRD-2 retries must complete within this window. |
| **Rationale** | Domain authority (Tier 2) assigns each TRD control over its own retry behavior. The nested retry rule prevents retry explosion (3 TRD-2 retries × 2 TRD-3 retries = 6 attempts is acceptable; multiplicative would be 3×2 per attempt = unbounded). |
| **Scope/Impact** | Consensus engine invocations from pipeline stages, LLM API call retry logic, pipeline stage timeout configuration. |

---

### CR-009: Authentication Token Handling

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §Keychain Integration) vs. TRD-11 (Security Architecture, §Secrets Management) |
| **Description** | TRD-1 describes Keychain integration for storing authentication tokens as part of the macOS application shell. TRD-11 defines comprehensive secrets management policies including token lifecycle, rotation, and access control. Where TRD-1 specifies Keychain storage mechanics and TRD-11 specifies security policies for token handling, overlap exists. |
| **Resolution** | **This is a security matter (criteria S1: secrets/credentials, S2: authentication flows, S6: Keychain access). TRD-11 governs under Tier 1.** Specifically: TRD-11 defines token lifecycle policy (rotation frequency, expiration handling, revocation). TRD-11 defines Keychain ACL requirements (which processes may access tokens). TRD-11 defines the prohibition on token logging or inclusion in error messages. TRD-1 implements the Keychain storage mechanics (how to call Keychain APIs, where to store items) but MUST comply with TRD-11's security policies. TRD-1 MUST NOT define its own token expiration, rotation, or access policies that contradict TRD-11. |
| **Rationale** | Token handling is unambiguously security-relevant under multiple S-criteria. Tier 1 applies. TRD-1 retains implementation authority for the Keychain API integration layer, but all policy decisions are TRD-11's. |
| **Scope/Impact** | Keychain integration code, token refresh logic, authentication flows, secret rotation automation. |

---

### CR-010: IPC Protocol Error Codes

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §XPC Transport) vs. TRD-2 (Consensus Engine, §IPC Error Handling) |
| **Description** | TRD-1 defines XPC transport-level error semantics (connection failures, message encoding errors, timeout). TRD-2 defines consensus-engine-level IPC errors (provider unavailable, arbitration failure, consensus timeout). Both use the term "IPC error" and could assign overlapping error codes. Additionally, the Forge invariant states "XPC unknown message types are discarded and logged -- never raised as exceptions," which must be respected by both. |
| **Resolution** | **TRD-1 governs transport-level IPC errors (XPC layer).** TRD-2 governs application-level IPC errors (consensus protocol layer). Error code ranges from CR-004 apply: TRD-1 uses 1000-1999, TRD-2 uses 2000-2999. Semantic separation: Transport errors (TRD-1, 1000-range) = connection refused, message serialization failed, XPC timeout, unknown message type discarded. Application errors (TRD-2, 2000-range) = provider returned error, arbitration deadlock, consensus not reached, response validation failed. **Unknown XPC message types** are handled per the Forge invariant: discard and log at WARN level (per CR-005 level semantics). This is a TRD-1 transport concern. TRD-2 MUST NOT receive unknown message types -- TRD-1's transport layer filters them before they reach the consensus engine. |
| **Rationale** | Clean layering: transport errors (TRD-1) vs. application protocol errors (TRD-2). The error code ranges from CR-004 guarantee non-collision. The Forge invariant on unknown XPC messages is a security matter (S7: input validation) reinforced by Tier 1. |
| **Scope/Impact** | XPC message handling, consensus engine error paths, error code constants, diagnostic logging for IPC failures. |

---

### CR-011: Recovery Trigger Authority

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-12 (Health & Diagnostics) vs. TRD-13 (Recovery & State Management) |
| **Description** | TRD-12 detects failures via health checks. TRD-13 defines recovery procedures. Ambiguity exists about which TRD decides when to trigger recovery: TRD-12 (because it detects the failure) or TRD-13 (because it owns the recovery domain). |
| **Resolution** | **TRD-12 is authoritative for failure detection and declaring a component unhealthy.** TRD-13 is authoritative for recovery actions once a failure is declared. TRD-12 emits a health-failure event after its failure threshold is met (per CR-007: 3 consecutive failures post-startup). TRD-13 subscribes to this event and executes the appropriate recovery procedure. TRD-13 MUST NOT independently poll for health -- it relies on TRD-12's declarations. TRD-12 MUST NOT execute recovery actions -- it relies on TRD-13's handlers. |
| **Rationale** | Clean separation of detection (TRD-12 domain) from remediation (TRD-13 domain). Event-driven coupling prevents circular dependencies. |
| **Scope/Impact** | Health check failure handlers, recovery trigger events, state checkpoint decisions. |

---

### CR-012: Gate Approval Authority

| Field | Value |
|-------|-------|
| **Conflicting Sources** | TRD-3 (Build Pipeline, §Operator Gates) vs. TRD-6 (Code Review, §Review Approval) vs. TRD-11 (Security Architecture, §Security Gates) |
| **Description** | Multiple TRDs define gate/approval points. TRD-3 defines pipeline stage gates. TRD-6 defines review approval criteria. TRD-11 defines security review gates. When multiple gates apply to the same PR, the interaction is ambiguous. |
| **Resolution** | **All gates are conjunctive (AND logic): every applicable gate MUST pass.** No gate can override another. TRD-3 pipeline gates enforce build/test passing. TRD-14 quality gates (enforced by TRD-3 per CR-002) enforce code quality thresholds. TRD-6 review gates enforce review pass completion. TRD-11 security gates enforce security review passing. The Forge invariant applies: "Gates wait indefinitely for operator input -- no auto-approve ever." This is a Tier 1 security constraint (S2: authorization). |
| **Rationale** | Conjunctive gates are fail-closed by design. No single subsystem can bypass another's
