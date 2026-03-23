# Canonical Naming Conventions and Identifier Registry

> **Document ID:** CONVENTIONS.md
> **Authority:** PRD-001 §FR-1.1 -- Single Authoritative Naming Registry
> **Status:** Active
> **Last Updated:** 2025-01-15
> **Scope:** All identifier namespaces in the Crafted Dev Agent codebase

---

## 1. Document Purpose and Authority

This document is the **single authoritative naming registry** for the Crafted Dev Agent platform, as mandated by PRD-001 §FR-1.1. Every identifier -- across Swift modules, macOS subsystems, Python packages, CI infrastructure, and IPC boundaries -- is governed by the conventions and canonical values recorded here.

**Binding effect:** All TRDs, all PRs, and all generated code MUST conform to this document. When a TRD specifies a concrete identifier, that TRD takes precedence (see §17 Collision Resolution Rules). When a TRD is silent, the conventions and best-practice decisions in this document govern. No new identifier namespace may be introduced without first amending this document via PR.

**Security note:** Identifier naming is security-relevant. Inconsistent bundle identifiers, Keychain service names, or entitlement strings can create privilege-escalation vectors, sandbox escapes, or credential leakage. Treat naming decisions as security decisions.

---

## 2. Canonical Prefix Policy

**`Crafted` is the canonical prefix for all new identifiers** unless a specification explicitly mandates legacy compatibility.

| Context | Canonical Prefix | Format |
|---|---|---|
| Swift modules | `Crafted` | PascalCase: `Crafted` + capability name |
| Bundle identifiers | `dev.crafted.agent` | Reverse-DNS |
| os_log subsystems | `dev.crafted.agent` | Reverse-DNS with dot-separated categories |
| Keychain service names | `dev.crafted.agent` | Reverse-DNS |
| Environment variables | `CRAFTED_` | SCREAMING_SNAKE_CASE |
| Python internal refs | `crafted_` | snake_case |
| CI workflow files | `crafted-` | kebab-case |
| Coordination directories | `Crafted/` | PascalCase directory name |
| Temporary files | `crafted-tmp-` | kebab-case prefix |
| User defaults suite | `dev.crafted.agent` | Reverse-DNS |
| Application display name | `Crafted` | Plain English |

The only permitted departure from `Crafted` naming is enumerated in §15 (Legacy Exception Registry). All other uses of the retired `forge` prefix are prohibited in new code.

---

## 3. Canonical Identifier Registry -- Summary

| Namespace | Canonical Pattern | Example | Authorizing Reference |
|---|---|---|---|
| Swift module names | `Crafted` + PascalCase | `CraftedAppShell` | PRD-001 §FR-1.1 |
| macOS bundle identifiers | `dev.crafted.agent[.component]` | `dev.crafted.agent.xpc-bridge` | TRD-1 §2.1 |
| os_log subsystems | `dev.crafted.agent[.module]` | `dev.crafted.agent.auth` | Best-practice (§18) |
| Keychain service names | `dev.crafted.agent.keychain` | `dev.crafted.agent.keychain` | TRD-11 |
| Unix socket paths | `~/Library/Application Support/Crafted/*.sock` | `crafted-agent.sock` | TRD-1 §6 |
| Environment variables | `CRAFTED_` + SCREAMING_SNAKE | `CRAFTED_BACKEND_READY` | PRD-001 |
| Python package/module | `src/` top-level; `crafted_` internal prefix | `crafted_consensus` | PRD-001 |
| GitHub branch prefixes | `forge-agent/build/` | `forge-agent/build/pr-7` | TRD-5 §6.2, AGENTS.md **(legacy exception)** |
| CI workflow filenames | `crafted-` + kebab-case | `crafted-ci-macos.yml` | TRD-5 §9 |
| Coordination directories | `~/Library/Application Support/Crafted/` | -- | TRD-1 §2.1 |
| Application display name | `Crafted` | -- | PRD-001 |
| Python bootstrap signals | `CRAFTED_` + SCREAMING_SNAKE | `CRAFTED_BACKEND_PID` | TRD-1 §6 |

Each namespace is detailed in its own section below.

---

## 4. Swift Module Names

**Canonical format:** `Crafted` prefix + PascalCase capability name.

**Legacy retention decision:** All legacy `Forge` module prefixes are **retired**. New code MUST use `Crafted` prefixes exclusively.

**Authorizing reference:** PRD-001 §FR-1.1.

### 4.1 Enumerated Modules

| Module Name | Purpose | Legacy Name (retired) |
|---|---|---|
| `CraftedAppShell` | Top-level macOS application shell, menu bar, window management | `ForgeAppShell` |
| `CraftedAuthKit` | Authentication, Touch ID, API key validation | `ForgeAuthKit` |
| `CraftedKeychainKit` | Keychain Services wrapper, credential storage/retrieval | `ForgeKeychainKit` |
| `CraftedXPCBridge` | XPC and Unix socket IPC bridge between Swift host and Python backend | `ForgeXPCBridge` |
| `CraftedProcessManager` | Python backend lifecycle, process supervision, health checks | `ForgeProcessManager` |
| `CraftedBuildStream` | Build pipeline streaming UI, gate cards, progress display | `ForgeBuildStream` |
| `CraftedSettings` | Settings/preferences management, API key entry UI | `ForgeSettings` |
| `CraftedDocImport` | Document import, parsing handoff, drag-and-drop ingestion | `ForgeDocImport` |

### 4.2 Naming Rules for Future Modules

1. Prefix: Always `Crafted`.
2. Suffix: PascalCase noun or noun-phrase describing the module's capability (e.g., `CraftedNetworkKit`, `CraftedAnalytics`).
3. The word `Kit` is reserved for modules that expose reusable service interfaces. Leaf feature modules omit `Kit` (e.g., `CraftedSettings`, not `CraftedSettingsKit`).
4. Test targets append `Tests`: `CraftedAuthKitTests`.

---

## 5. macOS Bundle Identifiers

**Canonical format:** Reverse-DNS rooted at `dev.crafted.agent`.

**Legacy retention decision:** All legacy `com.forge.*` or `dev.forge.*` identifiers are **retired**.

**Authorizing reference:** TRD-1 §2.1.

### 5.1 Registered Bundle Identifiers

| Bundle Identifier | Component | Notes |
|---|---|---|
| `dev.crafted.agent` | Main application (host process) | Primary bundle; appears in Gatekeeper, code signing |
| `dev.crafted.agent.xpc-bridge` | XPC bridge service | Embedded helper; inherits parent entitlements |

### 5.2 Rules for New Bundle Identifiers

- Root: `dev.crafted.agent`
- Append a kebab-case component name: `dev.crafted.agent.{component}`
- Components with nested services append further segments: `dev.crafted.agent.{component}.{sub}`
- Maximum depth: 4 segments (root counts as 3).
- Bundle identifiers MUST be registered in this table before use.

---

## 6. os_log Subsystems and Categories

**Canonical format:** Subsystem = `dev.crafted.agent`; Category = module-aligned lowercase name.

**Legacy retention decision:** Any prior `dev.forge.*` subsystem names are **retired**.

**Authorizing reference:** Best-practice decision (TRDs are silent on os_log naming; see §18.1 for rationale).

### 6.1 Subsystem

All os_log usage across the application MUST use a single subsystem string:

```
dev.crafted.agent
```

### 6.2 Category Names

Categories are aligned 1:1 with Swift modules, using lowercase-hyphenated names:

| Category | Corresponding Module | Example Log Usage |
|---|---|---|
| `app-shell` | CraftedAppShell | Application lifecycle, window events |
| `auth` | CraftedAuthKit | Authentication attempts, Touch ID results |
| `keychain` | CraftedKeychainKit | Keychain read/write operations (never log secret values) |
| `xpc-bridge` | CraftedXPCBridge | IPC message routing, socket lifecycle |
| `process-manager` | CraftedProcessManager | Backend spawn/kill, health check outcomes |
| `build-stream` | CraftedBuildStream | Build pipeline state transitions, gate events |
| `settings` | CraftedSettings | Preference changes (never log API keys) |
| `doc-import` | CraftedDocImport | Document ingestion, parse outcomes |

### 6.3 Security Constraint

Secrets, API keys, tokens, and credential material MUST NEVER appear in os_log output at any log level, including `.debug`. Log the operation outcome (success/failure) and a non-sensitive context identifier (e.g., Keychain account label), never the value.

---

## 7. Keychain Service and Access Group Names

**Canonical format:** Service name = `dev.crafted.agent.keychain`; individual credentials distinguished by account name.

**Legacy retention decision:** Any prior `dev.forge.*` or `forge-agent` Keychain service entries are **retired**. A migration path must clear old entries on first launch (see §16 Retired Identifiers).

**Authorizing reference:** TRD-11 (Security Model).

### 7.1 Registered Keychain Identifiers

| Attribute | Value |
|---|---|
| **Service name** | `dev.crafted.agent.keychain` |
| **Access group** | `dev.crafted.agent` (matches App ID prefix + bundle ID) |

### 7.2 Account Names

Account names within the service identify distinct credentials:

| Account | Contents | Notes |
|---|---|---|
| `anthropic-api-key` | Anthropic API key | Encrypted at rest by Keychain Services |
| `openai-api-key` | OpenAI API key | Encrypted at rest by Keychain Services |
| `github-pat` | GitHub Personal Access Token | Encrypted at rest by Keychain Services |

### 7.3 Disambiguation: Access Group vs. Service Name

- **Access group** (`dev.crafted.agent`): Controls which applications/extensions can access the items. Set in entitlements. Matches the bundle ID root so only the main app and its embedded helpers have access.
- **Service name** (`dev.crafted.agent.keychain`): A logical grouping key within the Keychain. The `.keychain` suffix distinguishes it from other uses of the `dev.crafted.agent` namespace (e.g., User Defaults suite).

This distinction is a best-practice decision; see §18.2 for rationale.

---

## 8. Unix Socket and IPC Paths

**Canonical format:** Paths under `~/Library/Application Support/Crafted/`.

**Legacy retention decision:** Any prior paths using `Forge/` directory names are **retired**.

**Authorizing reference:** TRD-1 §6 (wire protocol).

### 8.1 Registered Paths

| Path | Purpose |
|---|---|
| `~/Library/Application Support/Crafted/crafted-agent.sock` | Primary IPC Unix domain socket between Swift host and Python backend |

### 8.2 Path Rules

- All runtime IPC endpoints live under the coordination directory (`~/Library/Application Support/Crafted/`).
- Socket filenames use kebab-case with `crafted-` prefix.
- No XPC Mach service names are used; Unix sockets are the sole IPC transport per TRD-1 §6. See §18.3 for rationale on this best-practice decision.

---

## 9. Environment Variables

**Canonical format:** `CRAFTED_` prefix + SCREAMING_SNAKE_CASE.

**Legacy retention decision:** Any prior `FORGE_*` environment variables are **retired**.

**Authorizing reference:** PRD-001 §FR-1.1.

### 9.1 Registered Environment Variables

| Variable | Purpose | Set By | Consumed By |
|---|---|---|---|
| `CRAFTED_BACKEND_READY` | Signal that the Python backend has completed initialization and is accepting IPC | Python backend | Swift host (CraftedProcessManager) |
| `CRAFTED_BACKEND_PID` | PID of the running Python backend process | Python backend | Swift host (CraftedProcessManager) |
| `CRAFTED_LOG_LEVEL` | Override log verbosity (`debug`, `info`, `warning`, `error`) | Operator / CI | Both processes |
| `CRAFTED_SOCKET_PATH` | Override default Unix socket path (for testing) | Test harness | Both processes |
| `CRAFTED_ENV` | Runtime environment identifier (`development`, `staging`, `production`) | Operator / CI | Both processes |
| `CRAFTED_CI` | Set to `1` when running inside CI; disables interactive gates | CI workflow | Python backend |
| `CRAFTED_FEATURE_FLAGS` | Comma-separated list of enabled feature flags | Operator | Both processes |

### 9.2 Rules for New Environment Variables

1. MUST begin with `CRAFTED_`.
2. MUST use SCREAMING_SNAKE_CASE.
3. MUST be registered in this table before use.
4. Boolean flags use `1` / `0` (not `true` / `false`).
5. All environment variable values are **untrusted external input** and MUST be validated before use. Never pass environment variable content to shell execution or string interpolation without sanitization.

---

## 10. Python Package and Module Naming

**Canonical format:** Top-level code lives in `src/`; internal references use `crafted_` prefix where namespacing is needed.

**Legacy retention decision:** Any prior `forge_` internal module prefixes are **retired** in new code.

**Authorizing reference:** PRD-001 §FR-1.1.

### 10.1 Conventions

| Convention | Rule | Example |
|---|---|---|
| Top-level directory | `src/` | `src/consensus.py` |
| Internal namespace prefix | `crafted_` + snake_case | `crafted_consensus`, `crafted_build_director` |
| Test directory | `tests/` | `tests/test_consensus.py` |
| Test file naming | `test_` + module name | `test_build_director.py` |
| Utility/shared modules | `crafted_utils_` prefix | `crafted_utils_path_security.py` |

### 10.2 Import Rules

- Relative imports within `src/` are preferred for intra-package references.
- Module-level `__all__` exports are required for public interfaces.
- No wildcard imports (`from module import *`) in production code.

---

## 11. GitHub Branch Prefixes

**Canonical format for agent-created branches:** `forge-agent/build/` **(LEGACY EXCEPTION -- see §15)**.

**Canonical format for human-created branches:** No enforced prefix; conventional prefixes `feature/`, `fix/`, `docs/` are recommended.

**Authorizing reference:** TRD-5 §6.2, AGENTS.md.

### 11.1 Agent Branch Naming

| Pattern | Example | Notes |
|---|---|---|
| `forge-agent/build/{pr-description}` | `forge-agent/build/pr-7-auth-kit` | Created by the Crafted Dev Agent for each PR |

This is the **sole legacy exception** to the `Crafted` naming policy. The `forge-agent/build/` prefix is retained because:

1. **TRD-5 §6.2** defines CI trigger patterns that match `forge-agent/build/**`.
2. **AGENTS.md** mandates this prefix for all agent-created branches.
3. Changing it would break existing CI workflow triggers and any in-flight branches.

See §15 for the full Legacy Exception Registry entry.

### 11.2 Protected Branches

| Branch | Protection Level |
|---|---|
| `main` | Requires PR, CI pass, operator approval |
| `release/*` | Requires PR, CI pass, operator approval |

---

## 12. CI Workflow Filenames

**Canonical format:** `crafted-` prefix + kebab-case descriptive name + `.yml`.

**Legacy retention decision:** Any prior `forge-*.yml` workflow files are **retired**.

**Authorizing reference:** TRD-5 §9.

### 12.1 Registered Workflow Files

| Filename | Purpose |
|---|---|
| `crafted-ci.yml` | Primary CI pipeline: lint, test, build |
| `crafted-ci-macos.yml` | macOS-specific CI: Swift build, Xcode tests, code signing validation |

### 12.2 Rules for New Workflows

1. MUST begin with `crafted-`.
2. MUST use kebab-case.
3. MUST be registered in this table before creation.

---

## 13. Coordination Directories and Runtime Paths

**Canonical format:** `~/Library/Application Support/Crafted/` as the root for all runtime state.

**Legacy retention decision:** Any prior `~/Library/Application Support/Forge/` directories are **retired**.

**Authorizing reference:** TRD-1 §2.1.

### 13.1 Directory Structure

| Path | Purpose |
|---|---|
| `~/Library/Application Support/Crafted/` | Root coordination directory |
| `~/Library/Application Support/Crafted/crafted-agent.sock` | Unix domain socket (IPC) |
| `~/Library/Application Support/Crafted/logs/` | Runtime log output (non-os_log) |
| `~/Library/Application Support/Crafted/state/` | Persistent state files (build ledger, checkpoints) |
| `~/Library/Application Support/Crafted/tmp/` | Temporary files (prefix: `crafted-tmp-`) |

### 13.2 Path Security Rules

- All paths MUST be validated via `path_security.validate_write_path()` before any file write operation.
- No symlink following into directories outside the coordination root.
- Temporary files use the `crafted-tmp-` prefix and are cleaned up on process exit.
- Permissions: directories created with `0o700`, files with `0o600`. Group and world access denied.

---

## 14. Application Display Name

**Canonical value:** `Crafted`

**Authorizing reference:** PRD-001.

### 14.1 Usage Locations

| Location | Value |
|---|---|
| Menu bar title | `Crafted` |
| Dock icon label | `Crafted` |
| About window | `Crafted` |
| `CFBundleDisplayName` | `Crafted` |
| `CFBundleName` | `Crafted` |
| Spotlight metadata | `Crafted` |

---

## 15. Legacy Exception Registry

This section exhaustively enumerates every permitted departure from the canonical `Crafted` naming policy. As of this document's creation, there is **exactly one** legacy exception.

### 15.1 Exception: `forge-agent/build/` Branch Prefix

| Attribute | Value |
|---|---|
| **Identifier** | `forge-agent/build/` |
| **Namespace** | GitHub branch prefixes |
| **Canonical alternative** | `crafted-agent/build/` (not adopted) |
| **Status** | **Retained as legacy exception** |
| **Authorizing references** | TRD-5 §6.2 (CI trigger patterns); AGENTS.md (agent branch mandate) |
| **Justification** | Three binding constraints require retention: (1) TRD-5 §6.2 specifies `forge-agent/build/**` as the glob pattern for CI workflow triggers -- changing it requires simultaneous CI workflow updates and a TRD amendment. (2) AGENTS.md mandates this prefix for all agent-created branches -- this is a repository-level policy document that governs agent behavior. (3) In-flight branches already using this prefix would become orphaned from CI if the pattern changed mid-development cycle. |
| **Conditions for retirement** | This exception may be retired only when: (a) TRD-5 is amended to specify a new branch prefix, (b) AGENTS.md is updated, (c) all CI workflow trigger patterns are migrated, and (d) no in-flight branches use the old prefix. All four conditions must be met simultaneously. |
| **Collision risk** | Low. The `forge-agent/` prefix is used exclusively by the automated agent and does not collide with any human-created branch prefix or other identifier namespace. |

### 15.2 No Other Exceptions

No other `forge`-prefixed identifiers are granted legacy exception status. Any code, configuration, or documentation introducing a `forge`-prefixed identifier outside of `forge-agent/build/` branch names MUST be rejected at code review.

---

## 16. Retired Identifiers Migration Table

The following table maps every known legacy `forge`-prefixed identifier to its canonical `Crafted` replacement. Legacy identifiers MUST NOT appear in new code. Existing occurrences are migration targets.

### 16.1 Swift Module Names

| Retired Name | Canonical Replacement |
|---|---|
| `ForgeAppShell` | `CraftedAppShell` |
| `ForgeAuthKit` | `CraftedAuthKit` |
| `ForgeKeychainKit` | `CraftedKeychainKit` |
| `ForgeXPCBridge` | `CraftedXPCBridge` |
| `ForgeProcessManager` | `CraftedProcessManager` |
| `ForgeBuildStream` | `CraftedBuildStream` |
| `ForgeSettings` | `CraftedSettings` |
| `ForgeDocImport` | `CraftedDocImport` |

### 16.2 Bundle Identifiers

| Retired Name | Canonical Replacement |
|---|---|
| `dev.forge.agent` | `dev.crafted.agent` |
| `dev.forge.agent.xpc-bridge` | `dev.crafted.agent.xpc-bridge` |
| `com.forge.agent` | `dev.crafted.agent` |

### 16.3 os_log Subsystems

| Retired Name | Canonical Replacement |
|---|---|
| `dev.forge.agent` | `dev.crafted.agent` |

### 16.4 Keychain Service Names

| Retired Name | Canonical Replacement |
|---|---|
| `dev.forge.agent.keychain` | `dev.crafted.agent.keychain` |
| `forge-agent` | `dev.crafted.agent.keychain` |

### 16.5 IPC Paths

| Retired Name | Canonical Replacement |
|---|---|
| `~/Library/Application Support/Forge/forge-agent.sock` | `~/Library/Application Support/Crafted/crafted-agent.sock` |
| `~/Library/Application Support/Forge/` | `~/Library/Application Support/Crafted/` |

### 16.6 Environment Variables

| Retired Name | Canonical Replacement |
|---|---|
| `FORGE_BACKEND_READY` | `CRAFTED_BACKEND_READY` |
| `FORGE_BACKEND_PID` | `CRAFTED_BACKEND_PID` |
| `FORGE_LOG_LEVEL` | `CRAFTED_LOG_LEVEL` |
| `FORGE_SOCKET_PATH` | `CRAFTED_SOCKET_PATH` |
| `FORGE_ENV` | `CRAFTED_ENV` |
| `FORGE_CI` | `CRAFTED_CI` |

### 16.7 Python Internal References

| Retired Name | Canonical Replacement |
|---|---|
| `forge_consensus` | `crafted_consensus` |
| `forge_build_director` | `crafted_build_director` |
| `forge_utils_*` | `crafted_utils_*` |

### 16.8 CI Workflow Files

| Retired Name | Canonical Replacement |
|---|---|
| `forge-ci.yml` | `crafted-ci.yml` |
| `forge-ci-macos.yml` | `crafted-ci-macos.yml` |

### 16.9 Coordination Directories

| Retired Name | Canonical Replacement |
|---|---|
| `~/Library/Application Support/Forge/` | `~/Library/Application Support/Crafted/` |

### 16.10 Application Display Name

| Retired Name | Canonical Replacement |
|---|---|
| `Forge` (application name) | `Crafted` |

### 16.11 Keychain Migration Note

On first launch after migration, the application MUST:

1. Check for credentials stored under the retired service name (`dev.forge.agent.keychain` or `forge-agent`).
2. If found, copy them to the canonical service name (`dev.crafted.agent.keychain`).
3. Delete the retired entries only after confirming the new entries are readable.
4. Log the migration outcome (success/failure) without logging any credential values.

---

## 17. Naming Collision Resolution Rules

When two or more sources provide conflicting guidance on an identifier's canonical form, apply the following precedence rules **in order**. The first matching rule governs.

### Precedence Order

| Priority | Source | Description |
|---|---|---|
| **1 (highest)** | Explicit TRD requirement | A specific TRD section that names a concrete identifier value. Example: TRD-5 §6.2 specifying `forge-agent/build/` as a branch prefix. |
| **2** | AGENTS.md / repository-level policy | Repository-level governance documents that mandate identifiers (e.g., AGENTS.md branch prefix requirement). |
| **3** | PRD-001 canonical `Crafted` naming | The default: all identifiers use `Crafted` prefix per PRD-001 §FR-1.1. |
| **4 (lowest)** | Best-practice decision in this document | Decisions recorded in §18 for gaps where TRDs are silent. |

### Resolution Procedure

1. **Identify the namespace.** Determine which section of this document governs the identifier in question (e.g., §5 for bundle identifiers, §9 for environment variables).
2. **Check for an explicit TRD citation.** If the relevant TRD specifies an exact identifier value, use that value. Record the TRD section reference.
3. **Check AGENTS.md and repository-level policy.** If AGENTS.md or another repository governance document mandates a specific form, use it.
4. **Apply PRD-001 canonical naming.** Use the `Crafted` prefix with the format rules defined in the namespace's section of this document.
5. **Fall back to best-practice.** If the TRDs and PRD-001 are both silent, check §18 for a recorded best-practice decision. If none exists, a new best-practice decision MUST be drafted and added to §18 via PR before the identifier may be used.
6. **Document the resolution.** Add the new identifier to the appropriate table in this document in the same PR that introduces it.

### Worked Example

> **Question:** What branch prefix should the agent use for auto-created branches?
>
> **Step 1:** Namespace = GitHub branch prefixes (§11).
> **Step 2:** TRD-5 §6.2 explicitly specifies `forge-agent/build/**` as a CI trigger pattern. **Match at Priority 1.**
> **Step 3:** AGENTS.md confirms `forge-agent/build/` prefix. **Corroborated at Priority 2.**
> **Step 4:** PRD-001 would suggest `crafted-agent/build/`. However, Priority 1 and 2 both override Priority 3.
> **Resolution:** Retain `forge-agent/build/`. Documented as legacy exception in §15.1.

---

## 18. Best-Practice Decisions for TRD Gaps

The following decisions fill gaps where no TRD provides explicit guidance. Each decision includes a rationale. These decisions have the lowest precedence in the collision resolution order (Priority 4) and may be superseded by future TRD amendments.

### 18.1 os_log Category Naming Scheme

**Decision:** os_log categories are aligned 1:1 with Swift module names, converted to lowercase-hyphenated format.

**Rationale:** Module-aligned categories enable precise log filtering in Console.app. A 1:1 mapping eliminates ambiguity about which category a log statement should use -- it is always the category corresponding to the module containing the call site. Lowercase-hyphenated format follows Apple's own os_log examples and avoids case-sensitivity issues when filtering via `log` CLI. The TRDs define the module list but do not specify os_log categories; this decision fills that gap deterministically.

### 18.2 Keychain Access Group vs. Service Name Disambiguation

**Decision:** The access group is set to the bundle ID root (`dev.crafted.agent`) and the service name appends `.keychain` (`dev.crafted.agent.keychain`).

**Rationale:** The access group controls entitlement-based access across application components and MUST match the App ID prefix for Keychain sharing between the host app and embedded helpers. Using the bare bundle ID root keeps entitlements simple. The service name needs to be distinct from other uses of the `dev.crafted.agent` string (e.g., the User Defaults suite name). Appending `.keychain` provides an unambiguous, greppable identifier. TRD-11 specifies Keychain usage but does not dictate the exact access group / service name split; this decision resolves the ambiguity.

### 18.3 XPC Mach Service Name Format (Not Used)

**Decision:** No XPC Mach service name is registered. The IPC transport is exclusively a Unix domain socket at `~/Library/Application Support/Crafted/crafted-agent.sock`.

**Rationale:** TRD-1 §6 specifies a Unix socket-based wire protocol for Swift-to-Python communication. XPC Mach services are not used because: (1) The Python backend is not an XPC service -- it is a standalone process managed by CraftedProcessManager. (2) Mach services require launchd registration, adding operational complexity. (3) Unix sockets provide cross-language compatibility (Swift and Python both have native socket APIs). If a future TRD introduces XPC Mach services, the naming format would be `dev.crafted.agent.xpc.{service-name}`, registered in this document before use.

### 18.4 Temporary File Prefix

**Decision:** All temporary files created by the application use the prefix `crafted-tmp-`.

**Rationale:** A distinctive prefix enables reliable cleanup (glob `crafted-tmp-*`) and prevents collisions with system or third-party temporary files. Files are created in `~/Library/Application Support/Crafted/tmp/` rather than `/tmp` to avoid multi-user conflicts and maintain sandbox containment. The TRDs do not address temporary file naming; this decision ensures consistency.

### 18.5 User Defaults Suite Name

**Decision:** The User Defaults suite name is `dev.crafted.agent`.

**Rationale:** Using the same reverse-DNS root as the bundle identifier keeps preference files co-located with the application's container. The suite name is intentionally identical to the bundle ID (not suffixed with `.defaults` or similar) because macOS uses the suite name directly as the plist filename, and matching the bundle ID produces a predictable path: `~/Library/Preferences/dev.crafted.agent.plist`. The Keychain service name avoids collision by using the `.keychain` suffix (§18.2).

### 18.6 Accessibility Identifier Naming

**Decision:** Accessibility identifiers follow the convention `{module}-{component}-{role}-{context?}`, using lowercase-hyphenated format.

**Rationale:** TRD-1 §13.1 defines this convention with examples (`auth-touchid-button`, `settings-anthropic-key-field`). This best-practice section reaffirms it as the governing rule for any accessibility identifier not explicitly listed in TRD-1. The module prefix ensures identifiers are globally unique across the application. The optional context segment disambiguates multiple instances of the same component (e.g., `navigator-project-row-{projectId}`).

---

## 19. Adding New Namespaces

Any identifier namespace not covered by this document MUST be added here **before** the identifier is used in code, configuration, or CI workflows. The process is:

### 19.1 Proposal Process

1. **Identify the gap.** Determine that the identifier namespace is not covered by any existing section.
2. **Draft a new section.** Following the structure of existing sections, provide:
   - Canonical format and naming pattern.
   - At least one concrete example.
   - Authorizing TRD/PRD reference (or note "Best-practice decision" if no T
