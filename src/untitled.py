I'll implement the three artifacts specified in the plan. Let me carefully analyze the Forge context documents to ensure all domain terms are captured accurately.

```python
# This is a documentation-only task. Creating the three specified files.
# No runtime allocations. No caches. No buffers.
```

Here are the three files:

**File: forge-standards/naming/CANONICAL_NAMING.md**

```markdown
# Canonical Naming Conventions -- Consensus Dev Agent

> **Status:** Authoritative
> **Scope:** All 12 TRDs, all source files, all inter-process boundaries
> **RFC-style language:** per [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)

---

## 1. Casing Rules

| Context | Convention | Example | Enforcement |
|---|---|---|---|
| Python classes / types | PascalCase | `ConsensusEngine`, `BuildLedger` | MUST |
| Python functions / methods | snake_case | `run_consensus`, `claim_slot` | MUST |
| Python module files | snake_case | `consensus_engine.py`, `build_ledger.py` | MUST |
| Python constants | SCREAMING_SNAKE_CASE | `GENERATION_SYSTEM`, `MAX_RETRIES` | MUST |
| Swift types | PascalCase | `BuildPlanView`, `PRStatusRow` | MUST |
| Swift properties / locals | camelCase | `buildIntent`, `prSpecList` | MUST |
| Swift source files | PascalCase matching primary type | `BuildPlanView.swift` | MUST |
| Markdown / doc files | SCREAMING_SNAKE or kebab-case | `CANONICAL_NAMING.md`, `trd-02-consensus-engine.md` | SHOULD |
| JSON / YAML keys | snake_case | `"build_intent"`, `"pr_number"` | MUST |
| Environment variables | SCREAMING_SNAKE_CASE with `FORGE_` prefix | `FORGE_GITHUB_TOKEN` | MUST |
| Git branch names | kebab-case with prefix | `build/pr-03-ledger-heartbeat` | MUST |
| CLI flags | kebab-case | `--dry-run`, `--build-intent` | MUST |

### 1.1 Acronyms in Identifiers

Acronyms of three or more letters MUST be treated as words:

| ✅ Correct | ❌ Incorrect | Reason |
|---|---|---|
| `LlmProvider` | `LLMProvider` | Treat "LLM" as a word |
| `PrSpec` | `PRSpec` | Treat "PR" as a word -- **exception**: the legacy name `PRSpec` is grandfathered (see §6) |
| `CiPipeline` | `CIPipeline` | Treat "CI" as a word |
| `XpcConnection` | `XPCConnection` | Treat "XPC" as a word |

Two-letter acronyms (PR, CI) MAY remain uppercase in PascalCase contexts where the
grandfathered form already exists in the codebase, but new types SHOULD follow the
word-casing rule.

---

## 2. Entity Naming Patterns

Every domain type MUST use one of the following suffixes to communicate its role
unambiguously. No type name SHALL use a suffix from this table unless it fulfills
the described contract.

| Suffix | Semantic Contract | Examples |
|---|---|---|
| `*Spec` | Immutable specification object describing *what* to build. Created once, never mutated after construction. | `PRSpec`, `TaskSpec` |
| `*Plan` | Ordered sequence of `*Spec` objects. Represents decomposed intent. | `BuildPlan` |
| `*Entry` | A single row/record in a ledger or plan. | `BuildPlanEntry`, `LedgerEntry` |
| `*Ledger` | Persistent, append-mostly record of claims, releases, and state transitions. Source of truth for recovery. | `BuildLedger` |
| `*Thread` | A runtime execution context that processes one unit of work. Has a lifecycle (start → run → complete/fail). | `BuildThread` |
| `*Result` | Immutable output of an engine or pipeline stage. Contains the artifact plus metadata (timing, token counts, errors). | `ConsensusResult`, `ReviewResult` |
| `*Engine` | Stateless (or minimally stateful) processor. Takes a `*Spec` or prompt, returns a `*Result`. | `ConsensusEngine`, `ReviewEngine` |
| `*Pipeline` | Orchestrator that sequences multiple engine calls and gates. Owns the top-level control flow. | `BuildPipeline` |
| `*Tool` | Adapter wrapping an external API (GitHub, file system, CI). All external I/O is isolated here. | `GitHubTool` |
| `*Gate` | Synchronization point requiring operator approval. Waits indefinitely -- never auto-approves. | `MergeGate`, `ReviewGate` |
| `*Store` | Persistence adapter for documents or embeddings. Owns its own schema. | `DocumentStore` |
| `*Receiver` | Inbound webhook or event listener. All input is untrusted and validated. | `WebhookReceiver` |
| `*Config` | Validated, immutable configuration bundle. Loaded once at startup. | `ForgeConfig`, `LlmConfig` |
| `*Error` | Domain-specific exception. MUST include structured context (see §5). | `ConsensusError`, `LedgerClaimError` |

### 2.1 Disambiguation of Known Conflicts

| Ambiguous Usage | Canonical Resolution | Rationale |
|---|---|---|
| `PRSpec` vs `PRPlanEntry` | **`PRSpec`** is the specification for a single PR. **`BuildPlanEntry`** is its position within the `BuildPlan` (wraps a `PRSpec` plus ordering metadata). They are distinct types. | A spec describes *what*; an entry describes *where* in a sequence. |
| `BuildThread` vs `BuildLedger` | **`BuildThread`** is the runtime context executing a PR build. **`BuildLedger`** is the persistent record of all thread claims and state transitions. A `BuildThread` writes to the `BuildLedger`; they never substitute for each other. | Thread = runtime; Ledger = persistence. |
| `ConsensusResult` vs "consensus output" | **`ConsensusResult`** is the typed return value of `ConsensusEngine.run_consensus()`. Informal references to "consensus output" in docs SHOULD be replaced with `ConsensusResult`. | One name, one type. |
| `DocumentStore` vs "vector store" | **`DocumentStore`** is canonical. "Vector store" is an implementation detail. | Public API uses the domain name, not the storage mechanism. |

---

## 3. Namespace Boundaries

Each subsystem owns a namespace. Types MUST NOT leak across namespace boundaries
except through explicitly exported interfaces.

| Namespace | Owner Module(s) | Exported Types |
|---|---|---|
| `consensus_engine` | `src/consensus.py` | `ConsensusEngine`, `ConsensusResult`, `ConsensusError` |
| `build_pipeline` | `src/build_director.py` | `BuildPipeline`, `BuildPlan`, `BuildPlanEntry`, `PRSpec` |
| `build_ledger` | `src/build_ledger.py` | `BuildLedger`, `LedgerEntry`, `LedgerClaimError` |
| `github_ops` | `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
| `document_store` | `src/document_store.py` | `DocumentStore` |
| `review_engine` | `src/review_engine.py` (TRD-4) | `ReviewEngine`, `ReviewResult`, `ReviewGate` |
| `xpc_bridge` | `src/xpc/` | `XpcConnection`, `XpcMessage` |
| `security` | `src/security/` | `PathValidator`, `SecretRedactor`, `SecurityRefusal` |
| `config` | `src/config.py` | `ForgeConfig`, `LlmConfig` |

### 3.1 Import Rules

- A module MUST import only from namespaces listed as dependencies in its TRD.
- Circular imports are forbidden. If two namespaces need each other's types, extract
  a shared `*Spec` or `*Result` type into a `_types.py` within the depending namespace.
- All cross-namespace imports MUST be explicit (no `from module import *`).

---

## 4. Process-Boundary Term Ownership

When terms cross XPC, webhook, or IPC boundaries, exactly one side owns the
canonical definition. The other side MUST use the same name and schema.

| Term | Owner Process | Consumer Process(es) | Serialization |
|---|---|---|---|
| `BuildPlan` | Python backend (`build_pipeline`) | Swift UI | JSON over XPC |
| `PRSpec` | Python backend (`build_pipeline`) | Swift UI, GitHub webhook handler | JSON |
| `LedgerEntry` | Python backend (`build_ledger`) | Swift UI (read-only) | JSON over XPC |
| `ConsensusResult` | Python backend (`consensus_engine`) | Build pipeline (same process) | In-memory Python object |
| `WebhookEvent` | GitHub (external) | Python backend (`github_ops`) | JSON -- **untrusted input, MUST validate** |
| `XpcMessage` | Defined in shared schema | Both Python and Swift | Binary plist -- unknown types discarded and logged per Forge invariant |
| `OperatorApproval` | Swift UI | Python backend (`review_engine`) | JSON over XPC -- **gate waits indefinitely** |

### 4.1 Serialization Naming

When a domain type is serialized to JSON:

- Field names MUST use snake_case.
- Type discriminators MUST use the canonical PascalCase type name in a `"type"` field.
- Example: `{"type": "PRSpec", "pr_number": 3, "title": "Add ledger heartbeat"}`

---

## 5. Error Naming and Context

All domain errors MUST:

1. End with the `Error` suffix.
2. Include a `context: dict` field with at minimum:
   - `"source"`: the namespace that raised the error.
   - `"operation"`: the operation that failed.
   - `"detail"`: human-readable explanation (secrets MUST be redacted).
3. Never include secrets, tokens, or credentials in any field.

| Error Type | Namespace | Raised When |
|---|---|---|
| `ConsensusError` | `consensus_engine` | LLM calls fail, arbitration cannot converge |
| `LedgerClaimError` | `build_ledger` | Slot claim conflict, heartbeat timeout |
| `GitHubToolError` | `github_ops` | API call failure, rate limit, auth failure |
| `PathValidationError` | `security` | Write path escapes allowed directory |
| `SecurityRefusal` | `security` | Agent refuses an operation on security grounds -- never bypassed |
| `XpcBridgeError` | `xpc_bridge` | Connection lost, malformed message (unknown types discarded per invariant) |
| `ConfigError` | `config` | Missing or invalid configuration at startup -- fail closed |
| `ReviewGateError` | `review_engine` | Review cycle cannot complete (never auto-approves) |

---

## 6. Alias Deprecation Policy

When a term is renamed, the old name becomes a **deprecated alias**.

### 6.1 Deprecation Lifecycle

| Phase | Duration | Behavior |
|---|---|---|
| **Active Alias** | 2 release cycles | Old name works, emits deprecation warning to logs. Import redirects to canonical name. |
| **Removed** | After 2 cycles | Old name raises `ImportError` with message pointing to canonical name. |

### 6.2 Current Deprecated Aliases

| Deprecated Name | Canonical Name | Deprecated Since | Removal Target |
|---|---|---|---|
| *(none currently)* | -- | -- | -- |

### 6.3 How to Deprecate a Name

1. Add a forwarding import in the old location with a deprecation warning.
2. Add an entry to the table in §6.2 with the deprecation date.
3. Update all internal callers to the canonical name in the same PR.
4. External consumers (Swift UI) get one release cycle notice via XPC schema changelog.

---

## 7. File Path Conventions

| Category | Pattern | Example |
|---|---|---|
| Python source | `src/<module_name>.py` | `src/consensus.py` |
| Python sub-package | `src/<package>/<module>.py` | `src/xpc/bridge.py` |
| Swift source | `<Feature>/<TypeName>.swift` | `BuildPlan/BuildPlanView.swift` |
| TRD documents | `docs/trd/trd-<NN>-<kebab-title>.md` | `docs/trd/trd-02-consensus-engine.md` |
| Forge standards | `forge-standards/<category>/<DOCUMENT>.md` | `forge-standards/naming/CANONICAL_NAMING.md` |
| Test files (Python) | `tests/test_<module_name>.py` | `tests/test_consensus.py` |
| Test files (Swift) | `<Feature>Tests/<TypeName>Tests.swift` | `BuildPlanTests/BuildPlanViewTests.swift` |
| Config files | Root or `config/` | `.forge.yaml`, `config/llm_providers.yaml` |

### 7.1 Path Security

All file write operations MUST be validated via `path_security.validate_write_path()`
before execution, per Forge invariant. Paths that escape the allowed directory tree
MUST cause a `PathValidationError` and fail closed.

---

## 8. Status and Lifecycle Naming

Status enums MUST use SCREAMING_SNAKE_CASE and follow this vocabulary:

| Domain | Statuses (in lifecycle order) | Defined In |
|---|---|---|
| PR Build | `PENDING` → `CLAIMED` → `GENERATING` → `REVIEWING` → `CI_RUNNING` → `GATED` → `MERGED` / `FAILED` | `build_ledger` |
| Consensus | `RUNNING` → `CONVERGED` / `DIVERGED` → `ARBITRATED` | `consensus_engine` |
| Review Cycle | `PASS_1` → `PASS_2` → `PASS_3` → `APPROVED` / `REJECTED` | `review_engine` |
| Gate | `WAITING` → `APPROVED` / `REJECTED` | `review_engine` |
| XPC Connection | `CONNECTING` → `CONNECTED` → `DISCONNECTED` | `xpc_bridge` |

Terminal states (`MERGED`, `FAILED`, `APPROVED`, `REJECTED`, `DISCONNECTED`) are
immutable -- once entered, the entity MUST NOT transition to any other state.

---

## 9. Identifier Formats

| Identifier | Format | Example | Uniqueness Scope |
|---|---|---|---|
| Build ID | `build-<UUID4>` | `build-a1b2c3d4-...` | Global |
| PR Spec ID | `prspec-<sequential>` | `prspec-003` | Within a BuildPlan |
| Ledger Entry ID | `le-<UUID4>` | `le-e5f6a7b8-...` | Global |
| Consensus Run ID | `cr-<UUID4>` | `cr-c9d0e1f2-...` | Global |
| Thread ID | `thread-<UUID4>` | `thread-f3a4b5c6-...` | Global |

All UUIDs MUST be generated using `uuid.uuid4()` (cryptographically random).
Sequential IDs MUST be zero-padded to 3 digits minimum.

---

## 10. How to Add a New Term

1. **Check this document and GLOSSARY.md** -- the term may already exist under a
   different name.
2. **Choose a name** following the casing rules (§1) and suffix patterns (§2).
3. **Assign a namespace** (§3). If no namespace fits, propose a new one with
   justification in the PR description.
4. **Add the term to GLOSSARY.md** with definition, owning namespace, related terms,
   and the TRD that introduced it.
5. **Add the
