# CONVENTIONS.md — Crafted Subsystem

All rules derived from TRD-1-macOS-Application-Shell-Crafted, TRD-3-Build-Pipeline-Crafted, and forge_architecture_context.

---

## 1. Code Conventions

### 1.1 Language Boundaries

1. All backend orchestration, CI tooling, and build-pipeline code is **Python 3.11+**.
2. All macOS application UI code is **Swift 5.9+ / SwiftUI**.
3. No cross-language mixing in a single source file.

### 1.2 Line Length and Formatting

4. Python: maximum **99 characters** per line. Format with `black --line-length 99`.
5. Swift: maximum **120 characters** per line. Format with `swiftformat`.
6. Indent Python with **4 spaces**; indent Swift with **4 spaces**. No tabs anywhere.

---

## 2. File and Directory Naming

7. Python source files use **snake_case**: `build_director.py`, `ci_workflow.py`, `document_store.py`.
8. Swift source files use **PascalCase**: `StreamGateCard.swift`, `AuthTouchIDView.swift`.
9. Tests mirror `src/` structure exactly — a source file `src/build_ledger.py` has its tests at `tests/build_ledger/test_build_ledger.py`.
10. CI workflow files are named exactly `crafted-ci.yml` (Ubuntu) and `crafted-ci-macos.yml` (macOS Swift). No other naming is accepted.
11. The `conftest.py` required for `src/` imports is **auto-committed** by `ci_workflow.ensure()`; never hand-edit it.
12. Subsystem directories under `src/` use the canonical short names:

| Directory | Purpose |
|---|---|
| `src/cal/` | Conversation Abstraction Layer |
| `src/dtl/` | Data Trust Label components |
| `src/trustflow/` | TrustFlow audit stream |
| `src/vtz/` | Virtual Trust Zone enforcement |
| `src/trustlock/` | Cryptographic machine identity |
| `src/mcp/` | MCP Policy Engine |
| `src/rewind/` | Forge Rewind replay engine |
| `sdk/connector/` | Forge Connector SDK |

13. Canonical backend files and their owners:

| File | Contents |
|---|---|
| `src/consensus.py` | `ConsensusEngine`, `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM` |
| `src/build_director.py` | `BuildPipeline` orchestration, confidence gate, `pr_type` routing |
| `src/github_tools.py` | `GitHubTool`, `WebhookReceiver` |
| `src/build_ledger.py` | `BuildLedger`, claim/release, heartbeat |
| `src/document_store.py` | `DocumentStore`, `chunk()`, `embed()`, `retrieve()` |
| `src/ci_workflow.py` | CI YAML generation for `crafted-ci.yml` and `crafted-ci-macos.yml` |

---

## 3. Branch Naming

14. All agent-created branches **must** follow this exact pattern:
    ```
    forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}
    ```
    - `engineer_id`: lowercase alphanumeric identifier of the build engineer.
    - `subsystem_slug`: e.g., `crafted`, `trustflow`, `cal`.
    - `N`: zero-padded to 3 digits (e.g., `001`, `042`).
    - `title_slug`: lowercase, hyphen-separated summary (no underscores).

15. The prefix `forge-agent` is **mandatory and intentional** — do not rename it for "consistency" with other schemes.

---

## 4. Class and Function Naming

16. Python classes: **PascalCase** — `BuildLedger`, `ConsensusEngine`, `DocumentStore`.
17. Python functions and methods: **snake_case** — `validate_write_path()`, `ensure()`, `claim_build()`.
18. Python constants: **UPPER_SNAKE_CASE** — `GENERATION_SYSTEM`, `SWIFT_GENERATION_SYSTEM`, `UI_ADDENDUM`.
19. Swift types (structs, classes, enums, protocols): **PascalCase** — `StreamGateCard`, `NavigatorProjectRow`.
20. Swift functions and properties: **camelCase** — `authenticateUser()`, `projectId`.
21. Swift constants: **camelCase** prefixed with `let` at the call site; module-level constants use **camelCase** — never `UPPER_SNAKE`.

---

## 5. Accessibility Identifier Convention (axIdentifier)

22. Every interactive SwiftUI element **must** have `.accessibilityIdentifier()` set.
23. Identifiers follow the pattern: `{module}-{component}-{role}-{context?}`
    - All segments are **lowercase**, separated by **hyphens**.
    - `context` is optional and appended only when disambiguation is needed (e.g., a dynamic ID).

24. Canonical examples (memorise the pattern, not just the list):

| Identifier | Breakdown |
|---|---|
| `auth-touchid-button` | module=auth, component=touchid, role=button |
| `auth-passcode-button` | module=auth, component=passcode, role=button |
| `settings-anthropic-key-field` | module=settings, component=anthropic-key, role=field |
| `settings-anthropic-key-test-button` | module=settings, component=anthropic-key-test, role=button |
| `settings-anthropic-key-reveal-button` | module=settings, component=anthropic-key-reveal, role=button |
| `navigator-project-row-{projectId}` | module=navigator, component=project, role=row, context=projectId |
| `stream-gate-card-{gateId}` | module=stream, component=gate, role=card, context=gateId |
| `stream-gate-yes-button-{gateId}` | module=stream, component=gate-yes, role=button, context=gateId |
| `stream-gate-skip-button-{gateId}` | module=stream, component=gate-skip, role=button, context=gateId |
| `stream-gate-stop-button-{gateId}` | module=stream, component=gate-stop, role=button, context=gateId |

25. Dynamic context values (e.g., `{projectId}`, `{gateId}`) are interpolated at runtime; the template string in code must use Swift string interpolation: `"navigator-project-row-\(projectId)"`.

---

## 6. Error and Exception Patterns

26. Define custom exceptions in the module that raises them, not in a shared `exceptions.py`.
27. Custom Python exceptions inherit from a single **subsystem base**: `class CraftedError(Exception): pass`.
28. Name exceptions with a **descriptive noun + `Error`** suffix: `BuildClaimError`, `PathTraversalError`, `EmbeddingDimensionError`.
29. Never catch bare `except:` or `except Exception:` at the call site unless re-raising. Catch the narrowest type.
30. Swift errors conform to a `CraftedError` protocol (or enum) scoped per module:
    ```swift
    enum AuthError: Error, LocalizedError {
        case biometricUnavailable
        case keychainWriteFailed(status: OSStatus)
    }
    ```

---

## 7. Path Security

31. **Before every file-system write**, validate the target path:
    ```python
    from path_security import validate_write_path
    safe_path = validate_write_path(user_supplied_path)
    ```
32. `validate_write_path` returns a **safe default** on directory-traversal attempts; it does **not** raise. Always use its return value —