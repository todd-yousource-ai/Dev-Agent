# Crafted Dev Agent -- Canonical Naming Conventions and Identifier Registry

> **Document ID:** CONV-1  
> **Version:** 1.0.0  
> **Status:** Normative  
> **Created:** 2025-01-15  
> **Last Amended:** 2025-01-15  
> **Authority:** FR-1.1 -- Single Authoritative Naming Registry  
> **Scope:** All runtime identifiers, coordination namespaces, and CI infrastructure across the Crafted Dev Agent system  

---

## 1. Purpose and Authority

This document is the **single authoritative naming registry** for the Crafted Dev Agent system, as required by FR-1.1. It serves three functions:

1. **Consolidation** -- Collects every identifier decision made across the 16 TRDs in `forge-docs/` into one reference.
2. **Gap-fill** -- Provides best-practice rulings for namespaces where TRDs are silent. These gap-fill decisions are clearly marked and distinguished from normative TRD requirements.
3. **Collision prevention** -- Establishes deterministic resolution rules when two subsystems claim the same namespace slot.

### 1.1 Authority Chain

The authority chain for naming decisions is strictly ordered:

| Precedence | Source | Scope |
|---|---|---|
| 1 (highest) | Individual TRDs in `forge-docs/` | Normative requirements for their subsystem |
| 2 | This document (`CONVENTIONS.md`) | Consolidation, gap-fill, and cross-cutting conventions |
| 3 | Code-level comments | Implementation notes only; never override (1) or (2) |

**This document does not override any TRD.** Where a TRD specifies an identifier, this document records that decision and cites the source. Where no TRD speaks, this document fills the gap and marks the entry as `Gap-fill`.

### 1.2 Versioning Policy

The version header at the top of this document uses semantic versioning:

- **Major** -- Incompatible changes to canonical identifiers (rename, removal)
- **Minor** -- New namespace entries or new gap-fill decisions
- **Patch** -- Clarifications, typo fixes, rationale updates

Every version bump requires a PR review. The version header and `Last Amended` date must be updated in the same commit.

---

## 2. Core Naming Policy

### 2.1 Product Prefix

**`Crafted`** is the canonical product name and the required prefix for all new identifiers. The legacy name `Forge` or prefix `forge-` **must not** be used in any new runtime identifier without an explicit exception recorded in §4 of this document.

### 2.2 Casing Rules by Namespace Type

| Namespace Type | Casing Convention | Prefix Form | Example |
|---|---|---|---|
| Swift modules and targets | PascalCase | `Crafted` | `CraftedXPCBridge` |
| Swift types (structs, classes, enums) | PascalCase | `Crafted` | `CraftedAuthManager` |
| Bundle identifiers | Reverse-DNS lowercase | `com.crafted.` | `com.crafted.dev-agent` |
| `os_log` subsystems | Reverse-DNS lowercase | `com.crafted.` | `com.crafted.dev-agent` |
| `os_log` categories | lowercase kebab-free | (none) | `auth`, `xpc`, `pipeline` |
| Keychain service names | Reverse-DNS lowercase | `com.crafted.` | `com.crafted.dev-agent` |
| Keychain item keys | lowercase dot-separated | `com.crafted.` | `com.crafted.dev-agent.github-pat` |
| XPC service identifiers | Reverse-DNS lowercase | `com.crafted.` | `com.crafted.dev-agent.xpc-helper` |
| Unix socket paths | lowercase with dots | `crafted` | `crafted.agent.sock` |
| Environment variables | SCREAMING_SNAKE_CASE | `CRAFTED_` | `CRAFTED_BACKEND_PID` |
| GitHub branch prefixes | lowercase with slashes | See §4.1 for legacy exception | `forge-agent/build/` |
| CI workflow filenames | lowercase kebab-case | `crafted-` | `crafted-ci-macos.yml` |
| Coordination directories | lowercase | `crafted` | `~/.crafted/` |
| Application display name | Title Case | `Crafted` | `Crafted` |
| Python IPC markers | SCREAMING_SNAKE_CASE | `CRAFTED_` | `CRAFTED_READY` |
| Accessibility identifiers | lowercase kebab-case | (module prefix) | `auth-touchid-button` |

### 2.3 Rules for New Identifiers

1. **All new identifiers** across every namespace must use the `Crafted`/`crafted`/`CRAFTED_` prefix form appropriate to their namespace type as defined in §2.2.
2. **No new `forge-` prefixed runtime identifiers** are permitted. The sole legacy exception is documented in §4.1.
3. **Repository-level directory names** such as `forge-docs/` and `forge-standards/` are directory paths, not runtime identifiers. They are outside the scope of this naming policy but are noted here for clarity.
4. **Any deviation** from this policy requires an explicit exception entry in §4, added in the same PR that introduces the deviation.

### 2.4 Accessibility Identifier Convention

Per TRD-1 §13.1, accessibility identifiers use the pattern:

```
{module}-{component}-{role}-{context?}
```

These identifiers do not carry the `Crafted` prefix because they are scoped within the application bundle and follow Apple UI testing conventions. Examples: `auth-touchid-button`, `settings-anthropic-key-field`, `navigator-project-row-{projectId}`.

---

## 3. Identifier Registry

Each subsection below covers one of the 11 canonical identifier namespaces. Every entry includes four required columns:

- **Identifier** -- The logical name or slot
- **Canonical Value** -- The exact string to use in code and configuration
- **Source** -- TRD reference (section number) or `Gap-fill` if no TRD speaks to this identifier
- **Rationale** -- Why this value was chosen

Additional **Notes** are provided where helpful.

---

### 3.1 Swift Modules and Targets

These are the Xcode targets and Swift module names derived from the two-process architecture (TRD-1 §2.1).

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Main application target | `Crafted` | TRD-1 §2.1 | Product name is Crafted; the primary macOS app target carries the product name | Entry point for the Swift shell process |
| XPC bridge module | `CraftedXPCBridge` | TRD-1 §6 | Encapsulates all XPC communication between Swift shell and Python backend | May be a framework target or Swift package |
| Auth manager module | `CraftedAuthManager` | TRD-1 §5, TRD-11 | Manages Keychain access, Touch ID, and credential lifecycle | Fail-closed on all auth errors per Forge standards |
| Settings module | `CraftedSettings` | Gap-fill | Encapsulates user preferences and API key management UI | Derived from TRD-1 §13.1 settings-related ax identifiers |
| Navigator module | `CraftedNavigator` | Gap-fill | Project navigation and file tree management | Derived from TRD-1 §13.1 navigator-related ax identifiers |
| Stream UI module | `CraftedStreamUI` | Gap-fill | Streaming output display and gate card rendering | Derived from TRD-1 §13.1 stream-related ax identifiers |
| Shared types package | `CraftedShared` | Gap-fill | Types, protocols, and constants shared across modules | Prevents circular dependencies between modules |

---

### 3.2 Bundle Identifiers

Apple reverse-DNS bundle identifiers per TRD-1.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Main application bundle | `com.crafted.dev-agent` | TRD-1 §2.1 | Reverse-DNS per Apple convention; `dev-agent` reflects the product's function | Used in Info.plist, entitlements, provisioning |
| XPC helper bundle | `com.crafted.dev-agent.xpc-helper` | TRD-1 §6 | Sub-identifier under main bundle for the XPC service | Must match XPC service plist configuration |
| App group identifier | `group.com.crafted.dev-agent` | Gap-fill | Required if app and XPC helper share Keychain access or container data | Apple convention: `group.` prefix on the bundle ID |

---

### 3.3 os_log Subsystems and Categories

Structured logging identifiers per TRD-1 and TRD-11.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Primary log subsystem | `com.crafted.dev-agent` | TRD-1, TRD-11 | Matches bundle ID; Apple best practice for os_log subsystem naming | All Swift-side logging uses this subsystem |
| Category: authentication | `auth` | TRD-11 | Groups all auth-related log messages (Touch ID, Keychain, credential validation) | Fail-closed events logged at `.error` level |
| Category: XPC communication | `xpc` | TRD-1 §6 | Groups XPC bridge lifecycle, message serialization, and error events | Unknown message types logged and discarded per Forge invariants |
| Category: user interface | `ui` | Gap-fill | Groups UI lifecycle, view state transitions, and accessibility events | Keeps UI noise separated from backend signal |
| Category: pipeline | `pipeline` | Gap-fill | Groups build pipeline orchestration events from the Swift shell perspective | Correlates with Python-side pipeline logging |
| Category: settings | `settings` | Gap-fill | Groups preferences and API key management events | Secrets must never appear in log messages |
| Category: network | `network` | Gap-fill | Groups HTTP client, webhook, and connectivity events | Redact tokens and URLs containing credentials |

---

### 3.4 Keychain Service Names and Access Groups

Credential storage identifiers per TRD-1 §5 and TRD-11.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Keychain service name | `com.crafted.dev-agent` | TRD-1 §5, TRD-11 | Matches bundle ID; scopes all Keychain items to this application | Used as `kSecAttrService` value |
| Keychain access group | `group.com.crafted.dev-agent` | Gap-fill | Allows Keychain sharing between main app and XPC helper if needed | Must match entitlements; omit if sharing is unnecessary |
| GitHub PAT key | `com.crafted.dev-agent.github-pat` | TRD-11 | Stores the GitHub Personal Access Token for repository operations | Encrypted at rest by Keychain; never logged |
| Anthropic API key | `com.crafted.dev-agent.anthropic-api-key` | TRD-11 | Stores the Anthropic API key for Claude interactions | Encrypted at rest by Keychain; never logged |
| OpenAI API key | `com.crafted.dev-agent.openai-api-key` | Gap-fill | Stores the OpenAI API key if configured for dual-provider consensus | Encrypted at rest by Keychain; never logged |
| Encryption key (local) | `com.crafted.dev-agent.encryption-key` | Gap-fill | Local symmetric key for encrypting sensitive fields in document store | Derived from Keychain-stored material; never exported |

**Security note:** All Keychain operations must fail closed. If a Keychain read fails for any reason (item not found, access denied, biometric failure), the calling code must surface the error with context and must not fall back to unencrypted storage or default values.

---

### 3.5 XPC and Unix Socket Paths

Inter-process communication identifiers per TRD-1 §6.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| XPC service name | `com.crafted.dev-agent.xpc-helper` | TRD-1 §6 | Matches XPC helper bundle ID; required by launchd XPC registration | Registered in XPC service plist |
| Unix domain socket filename | `crafted.agent.sock` | Gap-fill | Well-known socket name for Swift-Python IPC | Placed inside coordination directory (see §3.9) |
| Full socket path | `~/.crafted/run/crafted.agent.sock` | Gap-fill | Absolute path combining coordination directory with socket filename | Path validated before use; must not be world-writable |
| XPC Mach service name | `com.crafted.dev-agent.mach` | Gap-fill | Used if Mach-based XPC is preferred over Unix socket | Only one IPC mechanism should be active; decided at build time |

**Security note:** Unknown XPC message types must be discarded and logged -- never raised as exceptions. Socket file permissions must be restricted to the owning user (mode `0700` on parent directory, mode `0600` on socket file).

---

### 3.6 Environment Variables

Process environment variables for coordination between Swift shell and Python backend.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Backend process ID | `CRAFTED_BACKEND_PID` | TRD-1 §6 | Swift shell stores the PID of the spawned Python backend for lifecycle management | Integer string; validated on read |
| Socket path override | `CRAFTED_SOCKET_PATH` | Gap-fill | Allows overriding the default Unix socket path for testing or non-standard deployments | Absolute path; validated via `path_security.validate_write_path()` |
| Log level | `CRAFTED_LOG_LEVEL` | TRD-15 | Controls verbosity for both Swift and Python processes | Values: `debug`, `info`, `warning`, `error`; defaults to `info` |
| Project root | `CRAFTED_PROJECT_ROOT` | Gap-fill | Absolute path to the current project being operated on | Validated; must exist and be a directory |
| Backend ready signal | `CRAFTED_BACKEND_READY` | Gap-fill | Set by Python backend to signal successful initialization to the Swift shell | Values: `1` (ready) or absent (not ready) |
| CI mode flag | `CRAFTED_CI_MODE` | TRD-9 | Indicates the process is running in CI; disables interactive prompts | Values: `1` (CI) or absent (interactive) |
| Config directory override | `CRAFTED_CONFIG_DIR` | Gap-fill | Overrides the default `~/.crafted/` configuration directory | Absolute path; validated before use |
| GitHub token (runtime) | `CRAFTED_GITHUB_TOKEN` | Gap-fill | Runtime-injected GitHub token for CI environments where Keychain is unavailable | Never logged; prefer Keychain in interactive mode |
| Anthropic token (runtime) | `CRAFTED_ANTHROPIC_TOKEN` | Gap-fill | Runtime-injected Anthropic API key for CI environments | Never logged; prefer Keychain in interactive mode |
| Build ledger path | `CRAFTED_LEDGER_PATH` | Gap-fill | Overrides default location of the build ledger database | Absolute path; validated before use |

**Security note:** Environment variables containing secrets (`CRAFTED_GITHUB_TOKEN`, `CRAFTED_ANTHROPIC_TOKEN`) must never appear in log output, error messages, or generated code. Code that reads these variables must redact them from any diagnostic context.

---

### 3.7 GitHub Branch Prefixes

Branch naming conventions for CI and agent orchestration.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Agent build branch prefix | `forge-agent/build/` | TRD-5 §6.2, AGENTS.md | **Legacy exception** -- see §4.1 for full rationale | Retained to avoid CI breakage |
| Feature branch prefix | `crafted/feature/` | Gap-fill | Human-initiated feature branches | Distinguishes human work from agent-generated PRs |
| Hotfix branch prefix | `crafted/hotfix/` | Gap-fill | Urgent fixes that bypass normal queue ordering | Follows same pattern as feature branches |
| Release branch prefix | `crafted/release/` | Gap-fill | Release preparation branches | Follows same pattern as feature branches |

---

### 3.8 CI Workflow Filenames

GitHub Actions workflow files per TRD-5 and TRD-9.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| macOS CI workflow | `crafted-ci-macos.yml` | TRD-9 §2 | Builds and tests the Swift shell on macOS runners | Triggered by pushes to `forge-agent/build/*` and `crafted/*` branches |
| Python CI workflow | `crafted-ci-python.yml` | TRD-9 §2 | Tests the Python backend (consensus engine, build director, document store) | Runs on Ubuntu and macOS runners |
| Lint gate workflow | `crafted-lint-gate.yml` | Gap-fill | Runs SwiftLint, ruff, and formatting checks | Required to pass before merge |
| Release workflow | `crafted-release.yml` | Gap-fill | Builds signed release artifacts and notarizes the macOS app | Triggered by tags matching `v*` |
| PR validation workflow | `crafted-pr-validation.yml` | Gap-fill | Validates PR metadata, branch naming compliance, and conventions co-update requirement | Lightweight check on all PR events |

---

### 3.9 Coordination Directories

Filesystem paths for runtime state, configuration, and coordination per TRD-1 and TRD-15.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Root configuration directory | `~/.crafted/` | TRD-15 | Central location for all Crafted Dev Agent runtime state | Created on first launch with mode `0700` |
| Runtime state directory | `~/.crafted/run/` | Gap-fill | Contains PID files, socket files, and lock files | Cleaned on graceful shutdown |
| Log directory | `~/.crafted/logs/` | Gap-fill | Contains rotating log files for both Swift and Python processes | Retained across restarts for debugging |
| Cache directory | `~/.crafted/cache/` | Gap-fill | Contains FAISS indices, parsed document caches, and embedding caches | Safe to delete; rebuilt on demand |
| Build ledger directory | `~/.crafted/ledger/` | Gap-fill | Contains the build ledger SQLite database and WAL files | Per-project isolation via subdirectories |
| Project state directory | `~/.crafted/projects/` | Gap-fill | Per-project configuration, checkpoints, and stage completion records | Subdirectory per project keyed by repository slug |
| Document store directory | `~/.crafted/documents/` | TRD-10 | Per-project document sets and FAISS indices | Each project has isolated document set per TRD-10 |

**Security note:** The root directory `~/.crafted/` and all subdirectories must be created with mode `0700` (owner-only access). Path traversal attacks must be prevented by validating all paths via `path_security.validate_write_path()` before any filesystem operation.

---

### 3.10 Application Display Name

The user-facing product name.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Application display name | `Crafted` | TRD-15, README, AGENTS.md | The canonical product name displayed in the macOS menu bar, Dock, About window, and all user-facing surfaces | `CFBundleDisplayName` in Info.plist |
| Application short name | `Crafted` | TRD-15 | Used in `CFBundleName` | Same as display name for this product |
| CLI tool name (if applicable) | `crafted` | Gap-fill | Lowercase for command-line invocation per Unix convention | Example: `crafted --version` |

---

### 3.11 Python Bootstrap Signals and IPC Markers

Coordination signals between the Swift shell and Python backend during startup and shutdown.

| Identifier | Canonical Value | Source | Rationale | Notes |
|---|---|---|---|---|
| Backend ready signal | `CRAFTED_READY` | TRD-1 §6 | Sent by Python backend over IPC channel when initialization is complete | Swift shell must not send commands before receiving this signal |
| Backend shutdown signal | `CRAFTED_SHUTDOWN` | TRD-1 §6 | Sent by Swift shell to Python backend to initiate graceful shutdown | Python backend must complete in-flight operations before exiting |
| Backend shutdown acknowledgment | `CRAFTED_SHUTDOWN_ACK` | Gap-fill | Sent by Python backend to confirm shutdown sequence has begun | Swift shell waits for this before sending SIGTERM |
| Heartbeat signal | `CRAFTED_HEARTBEAT` | Gap-fill | Periodic liveness check sent by Python backend to Swift shell | Absence triggers recovery procedure per TRD-1 §6 |
| Error signal | `CRAFTED_ERROR` | Gap-fill | Sent by either process to indicate a fatal error requiring operator attention | Payload includes error code and human-readable message |
| Gate request signal | `CRAFTED_GATE` | Gap-fill | Sent by Python backend to request operator approval via the Swift UI | Gates wait indefinitely per Forge invariants -- no auto-approve |

**Security note:** IPC markers are transmitted over the Unix domain socket defined in §3.5. All received markers must be validated against the known set defined in this table. Unknown markers must be logged at warning level and discarded -- never interpreted as commands.

---

## 4. Legacy Exceptions

This section documents every identifier that retains a legacy naming pattern instead of the canonical `Crafted`/`crafted` prefix. **Each exception must have an explicit entry here with rationale and migration path.**

As of version 1.0.0, there is exactly **one** legacy exception.

### 4.1 forge-agent/build/ Branch Prefix

| Field | Value |
|---|---|
| **Identifier** | GitHub branch prefix for agent-generated build PRs |
| **Retained Value** | `forge-agent/build/` |
| **Canonical Alternative** | `crafted/build/` (not yet adopted) |
| **Retained?** | Yes |
| **Authority** | TRD-5 §6.2 (branch naming conventions), AGENTS.md (operational workflows) |

#### Rationale for Retention

The `forge-agent/build/` branch prefix is retained because:

1. **CI trigger dependency** -- GitHub Actions workflows in TRD-9 and existing `.github/workflows/` configurations use `forge-agent/build/**` as a branch filter for triggering macOS and Python CI pipelines. Changing the prefix would silently break CI triggers until all workflow files are updated and validated.

2. **Existing PR references** -- Open and historical pull requests reference `forge-agent/build/` branches. Renaming would orphan these references and break traceability in the Git history.

3. **Agent orchestration dependency** -- The AGENTS.md operational instructions reference this branch prefix in workflow descriptions. The Python backend's `github_tools.py` module creates branches with this prefix as part of the automated PR generation pipeline. Changing the prefix requires coordinated updates across documentation, Python code, and CI configuration.

4. **Risk/reward** -- The branch prefix is a CI-infrastructure identifier, not a user-facing name. The cost of migration (CI breakage risk, coordination overhead, history disruption) significantly outweighs the naming-consistency benefit.

#### Migration Path

Migration to `crafted/build/` is deferred until a future release that can coordinate the following changes atomically:

1. Update all GitHub Actions workflow files to trigger on both `forge-agent/build/**` and `crafted/build/**` (dual-trigger transition period)
2. Update `github_tools.py` to generate branches with `crafted/build/` prefix
3. Update AGENTS.md operational instructions
4. Update TRD-5 §6.2 via TRD amendment process
5. After transition period with no `forge-agent/build/` branches in flight, remove the legacy trigger pattern

**Until this migration is executed, `forge-agent/build/` is the only authorized branch prefix for agent-generated build PRs.**

### 4.2 Repository-Level Directory Names (Non-Exception)

The directory names `forge-docs/` and `forge-standards/` appear in the repository tree but are **not runtime identifiers**. They are repository organizational paths and are explicitly outside the scope of this naming policy. They are noted here to prevent confusion -- their retention does not constitute a legacy exception and does not authorize the use of `forge-` in any runtime identifier.

---

## 5. Collision Resolution Rules

When two subsystems or PRs claim the same identifier namespace slot, the following deterministic procedure applies. Execute each step in order; stop at the first step that resolves the collision.

### Step 1: Check TRD Authority

If a TRD explicitly assigns a canonical value to the contested identifier, that TRD's assignment takes precedence. If two TRDs make conflicting assignments, escalate to Step 4.

### Step 2: Check This Registry

If no TRD speaks but this document (`CONVENTIONS.md`) has a registered canonical value, the registered value takes precedence. The later claimant must choose an alternative identifier and register it via a PR that updates this document.

### Step 3: Namespace Owner Priority

If neither a TRD nor this registry has a prior claim, resolve by **alphabetical namespace owner priority**:

1. Identify the subsystem (Swift module, Python module, CI component) that each claimant belongs to.
2. The subsystem whose canonical name comes first alphabetically wins the contested identifier.
3. The losing claimant must choose an alternative, typically by appending a disambiguating suffix.

Example: If both `CraftedAuthManager` and `CraftedStreamUI` contest the os_log category `session`, `CraftedAuthManager` wins because "Auth" < "Stream" alphabetically. `CraftedStreamUI` would use `stream-session` instead.

### Step 4: Escalate to TRD Amendment

If Steps 1-3 cannot resolve the collision (e.g., two TRDs conflict, or the alphabetical rule produces an unreasonable result), the collision must be escalated:

1. File a TRD amendment request identifying the conflicting assignments.
2. The amendment must be resolved before either claimant merges their PR.
3. The resolution is recorded in both the amended TRD and this document.
4. No PR may merge with an unresolved identifier collision.

**There is no "first come, first served" implicit rule.** All identifiers must be explicitly registered in this document or a TRD.

---

## 6. Gap-Fill Decisions and Rationale

The following table summarizes all entries in §3 that are marked `Gap-fill` -- meaning no TRD explicitly specifies them. These are best-practice conventions established by this document. They carry the authority of this document (Precedence 2 in §1.1) and may be overridden by future TRD amendments.

| Namespace | Identifier | Gap-Fill Value | Rationale |
|---|---|---|---|
| Swift Modules | `CraftedSettings` | Module name | Inferred from TRD-1 §13.1 accessibility identifiers referencing settings components |
| Swift Modules | `CraftedNavigator` | Module name | Inferred from TRD-1 §13.1 accessibility identifiers referencing navigator components |
| Swift Modules | `CraftedStreamUI` | Module name | Inferred from TRD-1 §13.1 accessibility identifiers referencing stream components |
| Swift Modules | `CraftedShared` | Module name | Standard practice to avoid circular dependencies in multi-module Swift projects |
| Bundle IDs | `group.com.crafted.dev-agent` | App group ID | Required by Apple for Keychain sharing between app and XPC helper; follows Apple `group.` prefix convention |
| os_log Categories | `ui`, `pipeline`, `settings`, `network` | Category names | Logical groupings following the module structure; short lowercase names per Apple convention |
| Keychain | `com.crafted.dev-agent.openai-api-key` | Keychain key | Dual-provider consensus architecture (TRD-1 §2.1) implies a second LLM provider key |
| Keychain | `com.crafted.dev-agent.encryption-key` | Keychain key | Document store (TRD-10) encryption needs imply a local key |
| XPC/Socket | `crafted.agent.sock` | Socket filename | Short, descriptive, follows Unix socket naming conventions |
| XPC/Socket | `~/.crafted/run/crafted.agent.sock` | Full socket path | Places socket in runtime directory consistent with §3.9 coordination directories |
| XPC/Socket | `com.crafted.dev-agent.mach` | Mach service name | Standard Mach service naming if XPC uses Mach transport |
| Environment | `CRAFTED_SOCKET_PATH` | Env var | Allows test and non-standard deployments to override socket location |
| Environment | `CRAFTED_PROJECT_ROOT` | Env var | Build pipeline needs to know the target project location |
| Environment | `CRAFTED_BACKEND_READY` | Env var | Alternative to IPC-based readiness for simple deployment scenarios |
| Environment | `CRAFTED_CONFIG_DIR` | Env var | Standard override pattern for configuration directory |
| Environment | `CRAFTED_GITHUB_TOKEN` | Env var | CI environments cannot use macOS Keychain; env var injection is standard |
| Environment | `CRAFTED_ANTHROPIC_TOKEN` | Env var | Same rationale as `CRAFTED_GITHUB_TOKEN` |
| Environment | `CRAFTED_LEDGER_PATH` | Env var | Allows test isolation and non-standard deployment of build ledger |
| Branch Prefixes | `crafted/feature/`, `crafted/hotfix/`, `crafted/release/` | Branch prefixes | Standard branching model prefixes adapted to the Crafted naming convention |
| CI Workflows | `crafted-lint-gate.yml` | Workflow file | Lint gating is a Forge engineering standard; needs a dedicated workflow |
| CI Workflows | `crafted-release.yml` | Workflow file | Release automation is standard for macOS app distribution |
| CI Workflows | `crafted-pr-validation.yml` | Workflow file | Enforces conventions co-update requirement from §7 |
| Directories | `~/.crafted/run/` | Runtime directory | Separates ephemeral runtime state from persistent configuration |
| Directories | `~/.crafted/logs/` | Log directory | Standard log directory placement |
| Directories | `~/.crafted/cache/` | Cache directory | Separates rebuildable cache from authoritative state |
| Directories | `~/.crafted/ledger/` | Ledger directory | Isolates build ledger database for backup and migration |
| Directories | `~/.crafted/projects/` | Project state directory | Per-project isolation pattern |
| Display Name | `crafted` (CLI) | CLI tool name | Unix convention: lowercase for command-line tools |
| IPC Markers | `CRAFTED_SHUTDOWN_ACK` | Signal | Ensures clean shutdown coordination; prevents premature SIGTERM |
| IPC Markers | `CRAFTED_HEARTBEAT` | Signal | Liveness detection for two-process model recovery |
| IPC Markers | `CRAFTED_ERROR` | Signal | Structured error reporting across process boundary |
| IPC Markers | `CRAFTED_GATE` | Signal | Gate mechanism must cross from Python backend to Swift UI |

### Distinguishing Gap-Fill from Normative Requirements

To avoid ambiguity when reading §3:

- **Source = TRD reference** → This identifier is a normative requirement. Changing it requires a TRD amendment.
- **Source = Gap-fill** → This identifier is a convention established by this document. Changing it requires updating this document. No TRD amendment is needed unless a TRD later adopts the identifier.

Downstream PRs that implement code using gap-fill identifiers should cite this document as the authority. If a gap-fill decision proves problematic, it can be amended via the process in §7 without the overhead of a TRD amendment.

---

## 7. Change Control and Amendment Policy

### 7.1 Document Version Management

Every change to this document must:

1. Update the `Version` field in the document header following semantic versioning (§1.2).
2. Update the `Last Amended` date.
3. Be submitted as a PR and reviewed by at least one engineer familiar with the affected namespace(s).

### 7.2 Co-Update Requirement

**Any PR that introduces a new identifier namespace, registers a new canonical identifier, or creates a new legacy exception MUST update this document in the same PR.** This is a merge-blocking requirement.

Rationale: If identifiers are introduced without updating the registry, the registry becomes st
