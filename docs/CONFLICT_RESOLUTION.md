docs/CONFLICT_RESOLUTION.md:
# Cross-TRD Conflict Resolution Hierarchy

**Canonical Source of Truth for Forge Platform Ambiguity Resolutions**

| Field          | Value                                                        |
|----------------|--------------------------------------------------------------|
| Document       | Cross-TRD Conflict Resolution Hierarchy                      |
| Version        | 1.0                                                          |
| Status         | Active -- Binding on all implementation work                  |
| Authority      | PRD-001 (Product Foundation, Repository Bootstrap)           |
| Author         | Forge ConsensusDevAgent / YouSource.ai                       |
| Date           | 2026-03-20                                                   |
| Scope          | All 16 TRDs (TRD-1 through TRD-16)                          |
| Quick Ref      | `forge-standards/decision-precedence.md`                     |

---

## 1. Purpose

This document is the **single, authoritative source of truth** for resolving conflicts, overlaps, and ambiguities across the 16 Technical Requirements Documents (TRDs) that govern the Forge platform. When two or more TRDs make contradictory or ambiguous claims about the same behavior, this document specifies which claim prevails and why.

**Normative language:** The keywords "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in this document follow RFC 2119 semantics.

All implementers -- human and AI agent alike -- MUST consult this document when encountering cross-TRD ambiguity. Guessing is never acceptable; if ambiguity is not addressed here, the Amendment Process (§7) MUST be followed before implementation proceeds.

---

## 2. Precedence Hierarchy

The Forge platform resolves cross-TRD conflicts using a strict 4-tier hierarchy. Higher tiers override lower tiers unconditionally within their defined scope.

### Tier 1 -- Security Override (TRD-11)

**TRD-11 (Security Architecture) overrides ALL other TRDs on any security-relevant matter.**

- This is the highest authority in the system.
- When a conflict involves a security concern (as defined in §3 Security Conflict Classification), TRD-11 prevails without exception.
- No other TRD, standard, or best practice may weaken, defer, or override a TRD-11 security requirement.
- Scope limitation: TRD-11 authority applies **only** to security matters as classified in §3. It does NOT have general override authority for non-security concerns (e.g., UI layout, build timing, formatting preferences).

### Tier 2 -- Domain Authority (Owning TRD)

**The TRD that owns a specific domain is authoritative for behavior within that domain.**

- Each TRD has a defined primary domain (see §4 Domain Ownership Map).
- When a conflict falls within a single TRD's primary domain and is NOT security-related, that TRD's specification prevails.
- When two TRDs have equal domain claims, escalate to Tier 3.

### Tier 3 -- Standards Tiebreak (AGENTS.md, CLAUDE.md)

**Project-wide standards documents break ties when two TRDs have equal domain claims on a non-security matter.**

- AGENTS.md and CLAUDE.md define cross-cutting conventions for the Forge project.
- If these standards address the conflict, their guidance prevails.
- If they do not address it, escalate to Tier 4.

### Tier 4 -- Best-Practice Default

**When no TRD and no standard document addresses a question, industry best practices apply.**

- The chosen best practice MUST be documented with rationale in the resolution record.
- A follow-on action SHOULD be filed to formally incorporate the resolution into the appropriate TRD.
- Best-practice defaults MUST NOT weaken any existing security posture -- when in doubt, fail closed.

### Tier Application Summary

```
┌─────────────────────────────────────────────────┐
│  TIER 1: TRD-11 Security Override               │
│  Scope: Security matters ONLY (see §3)          │
│  Authority: Absolute, no exceptions              │
├─────────────────────────────────────────────────┤
│  TIER 2: Domain Authority (Owning TRD)          │
│  Scope: Non-security matters within one domain  │
│  Authority: Owning TRD prevails in its domain   │
├─────────────────────────────────────────────────┤
│  TIER 3: Standards Tiebreak                     │
│  Scope: Equal-claim ties between TRDs           │
│  Authority: AGENTS.md / CLAUDE.md               │
├─────────────────────────────────────────────────┤
│  TIER 4: Best-Practice Default                  │
│  Scope: Unaddressed questions                   │
│  Authority: Industry norms + documented reason  │
└─────────────────────────────────────────────────┘
```

---

## 3. Security Conflict Classification

To prevent both **under-application** (missing a genuine security concern) and **over-application** (invoking TRD-11 override for non-security matters), the following classification criteria MUST be applied.

### 3.1 A Conflict Is Security-Related If It Involves Any Of

| # | Criterion | Examples |
|---|-----------|----------|
| S1 | **Secrets or credentials** -- generation, storage, transmission, rotation, or destruction of secrets | API keys, Keychain entries, tokens, private keys |
| S2 | **Authentication or authorization flows** -- verifying identity or granting access | OAuth token validation, session management, permission checks |
| S3 | **Cryptographic operations** -- encryption, decryption, signing, verification, hashing for integrity | TLS configuration, code signing, hash verification |
| S4 | **Access control** -- determining who or what may access a resource | File permissions, XPC entitlements, IPC authorization |
| S5 | **Data protection** -- confidentiality, integrity, or availability of sensitive data | PII handling, audit log tamper-resistance, secure deletion |
| S6 | **Keychain access** -- any interaction with the macOS Keychain or equivalent secure storage | Reading/writing Keychain items, Keychain ACLs |
| S7 | **Security logging and audit** -- requirements for security-relevant event logging | Auth failure logging, intrusion detection signals |
| S8 | **Fail-closed behavior** -- whether a component fails open or closed on error | Auth errors, crypto verification failures |
| S9 | **Input validation for injection prevention** -- validation specifically to prevent security exploits | Path traversal prevention, command injection |

### 3.2 A Conflict Is NOT Security-Related If It Involves Only

| # | Criterion | Examples |
|---|-----------|----------|
| N1 | **Performance tuning** -- timeout values, retry counts, batch sizes with no security implications | UI refresh interval, build cache TTL |
| N2 | **Code style or formatting** -- cosmetic code standards | Line length, import ordering, naming style |
| N3 | **UI/UX behavior** -- visual presentation, layout, user workflow | Window size, menu placement, status bar format |
| N4 | **Build optimization** -- CI speed, caching strategy, parallelism | Build concurrency limits, test sharding |
| N5 | **Feature scope** -- what functionality a TRD includes or excludes | Whether TRD-7 covers documentation generation |

### 3.3 Gray Zone Resolution

When a conflict could reasonably be classified either way:

1. Apply the **Forge invariant**: "Fail closed on auth, crypto, and identity errors -- never degrade silently."
2. If the conflict's resolution could create a path where a security check is weakened, bypassed, or degraded, classify it as **security-related**.
3. Document the classification reasoning in the resolution's Rationale field.
4. When genuinely uncertain, treat it as security-related and gate on operator review.

### 3.4 Classification Anti-Patterns

The following uses of TRD-11 override are **prohibited**:

- Invoking TRD-11 to win a timeout value dispute that has no security dimension.
- Claiming "everything is security" to avoid domain authority analysis.
- Using TRD-11 to override code quality thresholds that do not affect security posture.
- Applying TRD-11 to UI/UX decisions unless the UI directly handles secrets or auth flows.

---

## 4. Domain Ownership Map

Each TRD owns a primary domain. Within that domain, the owning TRD is authoritative (Tier 2). Cross-cutting concerns are listed where a TRD has legitimate interest in another domain's decisions.

| TRD | Name | Primary Domain | Cross-Cutting Concerns |
|-----|------|---------------|----------------------|
| TRD-1 | macOS Application Shell | Native app lifecycle, XPC transport, Keychain integration, window management | IPC protocol definitions, startup/shutdown sequences, auth token storage |
| TRD-2 | Consensus Engine | LLM orchestration, dual-provider consensus, arbitration, response generation | Retry policies for LLM calls, output format requirements |
| TRD-3 | Build Pipeline | CI/CD stage execution, build ordering, stage gates, artifact management | Code quality gate invocation, retry on CI failure, test execution triggers |
| TRD-4 | Multi-Agent Coordination | Agent task assignment, conflict detection, ledger writes, work distribution | File locking, merge conflict prevention, parallel execution limits |
| TRD-5 | GitHub Integration | GitHub API operations, PR management, branch management, webhook handling | Repository authentication, rate limiting, file read/write via API |
| TRD-6 | Holistic Code Review | Code review orchestration, review criteria, review output format | Quality assessment overlap with TRD-14, file access via TRD-5 |
| TRD-7 | TRD Development Workflow | TRD authoring process, documentation standards, TRD lifecycle | Cross-references to all TRDs, documentation naming conventions |
| TRD-8 | LLM Integration Layer | LLM provider abstraction, prompt construction, token management, model selection | API key handling (security), response parsing, provider failover |
| TRD-9 | Prompt Engineering | Prompt templates, context assembly, system/user prompt separation, prompt security | Context injection prevention (security), prompt structure standards |
| TRD-10 | Document Store | Document indexing, retrieval, embedding, storage format, search | Document naming, metadata schema, cross-reference format |
| TRD-11 | Security Architecture | Authentication, authorization, encryption, Keychain policy, secret management, audit logging, fail-closed enforcement | **Cross-cutting authority on all security matters across all TRDs** |
| TRD-12 | Health & Diagnostics | Health checks, metrics collection, logging infrastructure, system monitoring, alerting | Logging level definitions, health check intervals, diagnostic data format |
| TRD-13 | Recovery & State Management | State persistence, crash recovery, session restoration, checkpoint management | State file format, recovery ordering, cleanup policies |
| TRD-14 | Code Quality & CI Pipeline | Static analysis, lint rules, quality thresholds, coverage requirements, quality gate definitions | Quality gate enforcement interacts with TRD-3 build stages |
| TRD-15 | Runbook & Operations | Operational procedures, incident response, deployment checklists, operator guidance | References procedures across all TRDs |
| TRD-16 | Agent Testing & Validation | Test strategy, test harness, validation criteria, mock infrastructure, acceptance testing | Test execution via TRD-3, quality assertions via TRD-14 |

### Domain Boundary Rules

1. When a concern falls clearly within one TRD's primary domain, that TRD is authoritative.
2. When a concern spans two domains, the TRD whose primary domain is **more specific** to the concern prevails.
3. When specificity is equal, Tier 3 (standards tiebreak) applies.
4. TRD-11 cross-cutting authority applies ONLY through the security classification in §3.

---

## 5. Resolved Conflicts

Each resolution follows a structured format. All resolutions are binding on implementation.

---

### CR-001: Startup Timeout Values

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-001 |
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §startup sequence) vs TRD-12 (Health & Diagnostics, §health check configuration) |
| **Description** | TRD-1 defines application startup timeout behavior for the native macOS shell (how long the app waits for subsystems to initialize before declaring failure). TRD-12 defines health check intervals and startup grace periods for the diagnostics subsystem. When both specify timeout values for "startup readiness," implementers face ambiguity over which value to use. |
| **Resolution** | **TRD-1 is authoritative for the application-level startup timeout** (the maximum time from app launch to ready state). The canonical startup timeout is **30 seconds**. TRD-12 governs the **health check startup grace period** -- the window during which health checks suppress failure alerts to allow initialization. The health check grace period MUST be ≥ the TRD-1 startup timeout and is set to **45 seconds**. After the TRD-1 startup timeout expires, the app MUST fail closed (refuse to enter ready state). After the TRD-12 grace period expires, the health system MUST begin reporting failures. |
| **Rationale** | TRD-1 owns application lifecycle (Tier 2 domain authority). TRD-12 owns health monitoring. The grace period must exceed the startup timeout to avoid false-positive health failures during normal startup. The 30s/45s split gives 15s of buffer. Fail-closed on startup timeout is consistent with Forge security invariants. |
| **Scope/Impact** | App shell initialization, health check subsystem, operator-visible startup diagnostics. |
| **Follow-on Guidance** | If any subsystem requires >30s for legitimate initialization, file a TRD-1 amendment -- do NOT silently extend the timeout. |

---

### CR-002: Code Quality Gate Thresholds

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-002 |
| **Conflicting Sources** | TRD-3 (Build Pipeline, §stage gates) vs TRD-14 (Code Quality & CI Pipeline, §quality thresholds) |
| **Description** | TRD-3 defines build pipeline stages including quality gate checkpoints. TRD-14 defines the specific quality thresholds (coverage %, lint pass rate, complexity limits) and the tools that enforce them. Both claim authority over what constitutes a "passing" quality gate. |
| **Resolution** | **TRD-14 is authoritative for defining quality thresholds and rules** (what the gates check and what values constitute pass/fail). **TRD-3 is authoritative for when and how gates execute within the pipeline** (at which stages, blocking vs. advisory, retry behavior). Specifically: TRD-14 defines the minimum coverage threshold (e.g., 80%), maximum complexity scores, required lint checks, and their pass/fail criteria. TRD-3 defines that the quality gate runs at Stage 4, that it is blocking (pipeline halts on failure), and how failures are reported upstream. If TRD-3 references a specific threshold number that differs from TRD-14, TRD-14's number prevails. |
| **Rationale** | TRD-14's primary domain is code quality definitions. TRD-3's primary domain is pipeline orchestration. This separation follows the principle of single-domain authority (Tier 2). Threshold definition is more specific to TRD-14 than to TRD-3. |
| **Scope/Impact** | Build pipeline Stage 4, CI configuration, quality reporting dashboards. |
| **Follow-on Guidance** | TRD-3 SHOULD reference TRD-14 for threshold values rather than duplicating them. Any threshold value appearing in TRD-3 that contradicts TRD-14 is superseded by TRD-14. |

---

### CR-003: Configuration Key Naming Conventions

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-003 |
| **Conflicting Sources** | TRD-1, TRD-2, TRD-3, TRD-8, TRD-12, TRD-13 (multiple TRDs define configuration keys without a unified convention) |
| **Description** | Multiple TRDs define configuration keys (timeouts, retry counts, feature flags, paths) using inconsistent naming patterns. Some use `camelCase`, some use `snake_case`, some use dot-separated hierarchies, and some use flat keys. This creates collision risk and developer confusion. |
| **Resolution** | **All configuration keys across all TRDs MUST follow the canonical convention:** `forge.<trd_domain>.<subsystem>.<key_name>` using lowercase `snake_case` throughout. Domain prefixes are: `forge.shell.*` (TRD-1), `forge.consensus.*` (TRD-2), `forge.pipeline.*` (TRD-3), `forge.agents.*` (TRD-4), `forge.github.*` (TRD-5), `forge.review.*` (TRD-6), `forge.workflow.*` (TRD-7), `forge.llm.*` (TRD-8), `forge.prompts.*` (TRD-9), `forge.docstore.*` (TRD-10), `forge.security.*` (TRD-11), `forge.health.*` (TRD-12), `forge.recovery.*` (TRD-13), `forge.quality.*` (TRD-14), `forge.runbook.*` (TRD-15), `forge.testing.*` (TRD-16). Examples: `forge.shell.startup_timeout_seconds`, `forge.consensus.retry_max_attempts`, `forge.health.check_interval_seconds`. |
| **Rationale** | No single TRD owns configuration naming as a primary domain, making this a Tier 3 concern. The dot-separated hierarchical pattern with snake_case is consistent with AGENTS.md coding standards and industry norms (Tier 4 tiebreak). The `forge.` prefix prevents collision with system or third-party configuration. |
| **Scope/Impact** | All configuration files, environment variables, defaults classes, and documentation across all 16 TRDs. |
| **Follow-on Guidance** | Each TRD SHOULD include a "Configuration Keys" appendix listing all keys it defines, using this convention. Existing non-conforming keys MUST be migrated with a deprecation period of one release cycle. |

---

### CR-004: Error Taxonomy and Code Ranges

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-004 |
| **Conflicting Sources** | TRD-1, TRD-2, TRD-3, TRD-4, TRD-5, TRD-8, TRD-11, TRD-12, TRD-13 (multiple TRDs define error codes/categories that can collide) |
| **Description** | Several TRDs define their own error codes and categories. Without coordinated ranges, two TRDs may use the same numeric code for different errors, making error handling and logging ambiguous. |
| **Resolution** | **Each TRD is assigned a non-overlapping error code range.** All error codes follow the format `FXXYYY` where `XX` is the TRD number (zero-padded) and `YYY` is the subsystem-specific code (000-999). Assigned ranges: |

| TRD | Range | Example |
|-----|-------|---------|
| TRD-1 | F01000-F01999 | F01001: XPC connection timeout |
| TRD-2 | F02000-F02999 | F02001: Consensus quorum failure |
| TRD-3 | F03000-F03999 | F03001: Pipeline stage gate failure |
| TRD-4 | F04000-F04999 | F04001: Agent coordination deadlock |
| TRD-5 | F05000-F05999 | F05001: GitHub API rate limit exceeded |
| TRD-6 | F06000-F06999 | F06001: Review pass incomplete |
| TRD-7 | F07000-F07999 | F07001: TRD validation failure |
| TRD-8 | F08000-F08999 | F08001: LLM provider unreachable |
| TRD-9 | F09000-F09999 | F09001: Prompt template missing |
| TRD-10 | F10000-F10999 | F10001: Document index corrupt |
| TRD-11 | F11000-F11999 | F11001: Authentication failure |
| TRD-12 | F12000-F12999 | F12001: Health check timeout |
| TRD-13 | F13000-F13999 | F13001: State recovery failure |
| TRD-14 | F14000-F14999 | F14001: Quality threshold not met |
| TRD-15 | F15000-F15999 | F15001: Runbook step failure |
| TRD-16 | F16000-F16999 | F16001: Test harness initialization failure |

| Field | Value (continued) |
|-------|-------|
| **Rationale** | No single TRD owns error taxonomy globally. The TRD-numbered range scheme guarantees zero collisions, is self-documenting (the TRD number is embedded in the code), and scales to 1000 codes per subsystem. This is a Tier 3/4 resolution combining standards guidance with industry best practice. |
| **Scope/Impact** | All error handling, logging, monitoring, alerting, and operator-facing error messages across the platform. |
| **Follow-on Guidance** | Each TRD MUST maintain an error code registry in its own document. Cross-TRD error wrapping MUST preserve the original error code. Security-related errors (F11xxx) MUST NOT expose internal details in user-facing messages (per TRD-11). |

---

### CR-005: Logging Level Definitions

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-005 |
| **Conflicting Sources** | TRD-12 (Health & Diagnostics, §logging infrastructure) vs TRD-2, TRD-3, TRD-8, TRD-11 (various TRDs referencing log levels with inconsistent semantics) |
| **Description** | TRD-12 defines the logging infrastructure and level hierarchy. Other TRDs reference logging levels (e.g., "log at DEBUG level," "ERROR-level alert") but use level names inconsistently -- some use Python logging semantics, some use syslog semantics, and some use custom level names. |
| **Resolution** | **TRD-12 is the sole authority for logging level definitions.** The canonical logging levels, in ascending severity, are: |

| Level | Numeric | Semantics | Use When |
|-------|---------|-----------|----------|
| `TRACE` | 5 | Fine-grained diagnostic detail | Debugging individual function calls, IPC message contents (never secrets) |
| `DEBUG` | 10 | Developer-oriented diagnostic information | Internal state transitions, configuration values loaded (never secrets) |
| `INFO` | 20 | Normal operational events | Startup complete, stage transitions, PR created |
| `WARNING` | 30 | Unexpected but recoverable conditions | Retry triggered, degraded mode entered, threshold approaching |
| `ERROR` | 40 | Failure requiring attention, operation did not complete | Stage gate failure, LLM provider down, state recovery invoked |
| `CRITICAL` | 50 | System-level failure, immediate operator attention required | Security violation, unrecoverable state, data corruption detected |

| Field | Value (continued) |
|-------|-------|
| **Rationale** | TRD-12's primary domain is logging infrastructure (Tier 2 domain authority). All other TRDs MUST use TRD-12's level names and semantics. The numeric values align with Python's `logging` module for implementation compatibility. `TRACE` is added below `DEBUG` for high-volume diagnostics. |
| **Scope/Impact** | All logging calls across all subsystems. Logger configuration. Log aggregation and alerting rules. |
| **Follow-on Guidance** | Any TRD referencing a log level MUST use the exact names from this table. Custom log levels are prohibited. Security events MUST be logged at `WARNING` or above. Secrets MUST NEVER appear at ANY log level. |

---

### CR-006: Security Enforcement Scope

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-006 |
| **Conflicting Sources** | TRD-11 (Security Architecture, cross-cutting authority) vs all other TRDs (which each define some security-adjacent behavior) |
| **Description** | TRD-11 has cross-cutting authority on security matters, but the boundary of "security matters" was not formally defined, leading to ambiguity about whether TRD-11 can override non-security decisions in other TRDs. |
| **Resolution** | **TRD-11's override authority is strictly scoped to security matters as defined in §3 of this document (Security Conflict Classification).** TRD-11 MUST NOT be invoked to override non-security decisions. Specifically: TRD-11 IS authoritative for how tokens are stored (even if TRD-1 mentions Keychain usage -- the Keychain security policy comes from TRD-11). TRD-11 IS authoritative for fail-closed behavior on authentication and cryptographic errors. TRD-11 IS NOT authoritative for build pipeline ordering (TRD-3), code review criteria (TRD-6/TRD-14), or operational procedures (TRD-15) unless those directly involve security classification criteria from §3. |
| **Rationale** | This resolution operationalizes the Tier 1 / Tier 2 boundary. Without explicit scoping, TRD-11 could be used to override any decision by claiming a tenuous security connection. The §3 criteria provide an objective test. |
| **Scope/Impact** | All cross-TRD conflict resolution. This is a meta-resolution that governs how other resolutions are classified. |
| **Follow-on Guidance** | When filing a new conflict resolution, the submitter MUST classify it using §3 criteria before determining which tier applies. |

---

### CR-007: Health Check Interval vs Startup Grace Period

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-007 |
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §lifecycle management) vs TRD-12 (Health & Diagnostics, §health check scheduling) |
| **Description** | TRD-1 defines a startup sequence with subsystem initialization phases. TRD-12 defines periodic health checks. Ambiguity exists about: (a) when health checks should begin relative to app startup, (b) what the default health check interval is, and (c) whether health check failures during startup should trigger recovery. |
| **Resolution** | **Health checks MUST NOT begin until TRD-1's startup sequence reports subsystem ready OR the TRD-12 grace period (45 seconds, per CR-001) expires -- whichever comes first.** After the grace period, health checks run at a **10-second interval** (defined by TRD-12 as domain owner of health monitoring). Health check failures during the grace period are logged at `WARNING` but do NOT trigger recovery actions. Health check failures AFTER the grace period are logged at `ERROR` and trigger the recovery flow defined in TRD-13. |
| **Rationale** | TRD-12 owns health check scheduling (Tier 2). TRD-1 owns startup lifecycle (Tier 2). The grace period mechanism from CR-001 bridges the two domains. The 10-second interval is TRD-12's domain decision. Suppressing recovery during grace period prevents thrashing during normal startup. |
| **Scope/Impact** | Health check scheduler, app startup sequence, recovery trigger logic (TRD-13). |
| **Follow-on Guidance** | If subsystem startup patterns change (e.g., lazy initialization), CR-001 and CR-007 should be reviewed together. |

---

### CR-008: Retry Policy Defaults

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-008 |
| **Conflicting Sources** | TRD-2 (Consensus Engine, §LLM call retry) vs TRD-3 (Build Pipeline, §stage retry policy) |
| **Description** | TRD-2 defines retry behavior for LLM provider calls (how many times to retry a failed LLM request, backoff strategy). TRD-3 defines retry behavior for build pipeline stages (how many times to retry a failed CI stage). Both use the term "retry policy" but with different defaults and different semantics. |
| **Resolution** | **Each TRD is authoritative for retry policy within its own domain.** The term "retry policy" MUST always be qualified with its domain context. Canonical defaults: |

| Domain | Owner | Max Retries | Backoff Strategy | Base Delay | Max Delay |
|--------|-------|-------------|-------------------|------------|-----------|
| LLM provider calls | TRD-2 | 3 | Exponential with jitter | 1 second | 30 seconds |
| Build pipeline stages | TRD-3 | 2 | Linear | 5 seconds | 30 seconds |
| GitHub API calls | TRD-5 | 3 | Exponential with jitter | 2 seconds | 60 seconds |
| Health check retries | TRD-12 | 1 | None (immediate) | 0 | 0 |

| Field | Value (continued) |
|-------|-------|
| **Rationale** | Retry policies are domain-specific (Tier 2). LLM calls benefit from exponential backoff due to rate limiting. Pipeline stages use linear backoff because failures are typically deterministic (retry is for transient infra issues). Configuration keys follow CR-003: `forge.consensus.retry_max_attempts`, `forge.pipeline.retry_max_attempts`, etc. |
| **Scope/Impact** | All retry logic across the platform. Monitoring dashboards showing retry rates. |
| **Follow-on Guidance** | Any new subsystem defining retry behavior MUST register its defaults in this table via the amendment process. Retry policies MUST NOT retry on authentication failures (per TRD-11 fail-closed -- see CR-009). |

---

### CR-009: Authentication Token Handling

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-009 |
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §Keychain integration) vs TRD-11 (Security Architecture, §secret management and authentication) |
| **Description** | TRD-1 specifies that the macOS Application Shell manages Keychain access for storing authentication tokens. TRD-11 specifies security policies for all secret management including token storage, rotation, and access control. Overlap exists in: (a) who defines the Keychain access policy, (b) token refresh/rotation behavior, (c) what happens on token validation failure. |
| **Resolution** | **This is a security matter (§3 criteria S1, S2, S6). TRD-11 prevails (Tier 1).** Specifically: TRD-11 defines the Keychain access policy (which entitlements, ACL requirements, access groups). TRD-11 defines token rotation requirements and refresh behavior. TRD-11 defines fail-closed behavior on token validation failure -- the system MUST deny access and surface the error; it MUST NOT fall back to cached/expired tokens. TRD-1 is responsible for the **implementation mechanism** (the Swift Keychain API calls, the XPC transport for token requests) but MUST conform to TRD-11's policy. TRD-1 MUST NOT independently define security policy for tokens. |
| **Rationale** | Token handling directly involves secrets (S1), authentication flows (S2), and Keychain access (S6) -- all security classification criteria. Tier 1 applies unambiguously. TRD-1 provides the mechanism; TRD-11 provides the policy. This separation ensures security policy is defined in one place. |
| **Scope/Impact** | Keychain access layer, authentication middleware, token refresh logic, all API-authenticated operations. |
| **Follow-on Guidance** | Any new token type (e.g., for a new LLM provider) MUST be registered with TRD-11's token inventory before implementation. Tokens MUST NEVER appear in log output at any level. |

---

### CR-010: IPC Protocol Error Codes

| Field | Value |
|-------|-------|
| **Conflict ID** | CR-010 |
| **Conflicting Sources** | TRD-1 (macOS Application Shell, §XPC protocol) vs TRD-2 (Consensus Engine, §IPC error handling) |
| **Description** | TRD-1 defines XPC-based IPC protocols including error conditions for message transport (connection lost, timeout, invalid message format). TRD-2 defines error handling for consensus engine communication which also uses IPC.
