# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry-point scene shell for the Crafted application.

It defines the top-level SwiftUI scene architecture:

- Declares `@main struct CraftedApp: App`
- Creates the primary application window through a `WindowGroup`
- Hosts `RootView()` as the main content view
- Injects shared application models into the main scene environment:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configures primary window presentation:
  - `.windowStyle(.hiddenTitleBar)`
  - `.defaultSize(width: 1280, height: 800)`
  - `.windowResizability(.contentMinSize)`
- Declares a separate `Settings` scene
- Hosts `SettingsView()` in the settings scene
- Injects `SettingsStore.shared` into the settings scene
- Establishes the settings window as a separate, biometric-gated scene

Operationally, this subsystem is the application shell identified in health metadata as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`
- `language`: `["swift", "python"]`

## Component Boundaries

### Inside This Subsystem

The subsystem includes the application shell concerns explicitly defined by the scene architecture and health registry:

- Application entry point: `CraftedApp`
- Main window scene declaration
- Settings scene declaration
- Environment object wiring for shared state used by those scenes
- Window sizing and style configuration for the main scene
- Shell-level operational metadata:
  - CI workflow: `.github/workflows/crafted-ci.yml`
  - Telemetry endpoint: `logs/telemetry.jsonl`
  - Escalation policy bindings for this subsystem

### Outside This Subsystem

The subsystem does not define or own:

- Internal implementation of `RootView`
- Internal implementation of `SettingsView`
- Internal behavior of:
  - `AppState`
  - `BuildStreamModel`
  - `SettingsStore`
- Authentication, cryptography, or identity mechanisms
- Direct GitHub API interaction
- CI execution logic
- Health registry processing logic
- Telemetry ingestion or storage implementation
- Generated code execution

### Repository Boundary

This subsystem resides under a CamelCase root and must be treated as a valid repository root by path validation logic. The lessons learned explicitly require smart root detection for roots matching:

```regex
^[A-Za-z][A-Za-z0-9_-]*$
```

This exists to prevent path rejection for Swift/Xcode targets such as:

- `CraftedApp`
- `CraftedTests`
- `ForgeAgent`

This boundary matters because prior failure mode indexed for this subsystem class was:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection (v38.180)`

## Data Flow

### Application Startup Flow

1. The process enters through `@main struct CraftedApp: App`.
2. `CraftedApp.body` constructs the application scenes.
3. The primary `WindowGroup` instantiates `RootView()`.
4. The main scene injects shared singleton-backed environment objects:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
5. The main window is presented with:
   - hidden title bar
   - default size `1280 × 800`
   - content minimum-size resizability
6. A separate `Settings` scene instantiates `SettingsView()`.
7. The settings scene receives `SettingsStore.shared`.
8. Settings access is constrained by the stated biometric gate.

### Operational Data Flow

Health and operational metadata associated with this subsystem are defined as:

- CI workflow path: `.github/workflows/crafted-ci.yml`
- Telemetry sink: `logs/telemetry.jsonl`

This means the subsystem is expected to participate in:

- CI routing via the crafted CI workflow
- telemetry emission or association through the JSONL telemetry endpoint

The TRD does not define the payload schema for telemetry beyond the endpoint path, so that format is out of scope for this document.

## Key Invariants

### Scene Architecture Invariants

- The application entry point is `CraftedApp`.
- The main user-facing content is rooted at `RootView()`.
- `AppState.shared`, `BuildStreamModel.shared`, and `SettingsStore.shared` are available in the main scene environment.
- `SettingsView()` is hosted in a separate `Settings` scene.
- `SettingsStore.shared` is available in the settings scene environment.

### Windowing Invariants

- Main window style uses `.hiddenTitleBar`.
- Default main window size is `1280 × 800`.
- Main window resizability is `.contentMinSize`.
- Minimum window size is `1024 × 680`.
- Maximum window size is unconstrained.

### Security and Access Invariants

From the scene architecture TRD and Forge context:

- The settings window is biometric-gated.
- Auth, crypto, and identity failures must fail closed.
- No silent failure paths are permitted.
- All external input is untrusted and must be validated.
- Secrets must never appear in logs, error messages, or generated code.
- Generated code must never be executed by the agent.

### Repository and Path Invariants

- CamelCase roots are valid and must not be rejected by repository path guards.
- Smart root detection must allow roots matching `^[A-Za-z][A-Za-z0-9_-]*$`.
- Dot-prefixed roots such as `.github` require explicit allowlisting.
- Path validation must occur before any write.

### Process and Escalation Invariants

For the health-registered subsystem:

- Security issues escalate to `operator_review`
- Functional issues escalate to `auto_merge`
- Pipeline issues escalate to `engineer_review`

These escalation bindings are part of subsystem-level operating constraints.

## Failure Modes

### Known Indexed Failure Patterns Relevant to CraftedAppShell

#### Path rejection for new Swift target roots

- **Signal:** `Path rejected: CraftedAppShell/`
- **Root cause:** New Swift target not in `_ALLOWED_ROOTS`
- **Class:** Pipeline
- **Fix:** CamelCase root auto-detection (`v38.180`)

Impact on this subsystem:
- Writes, scaffolds, or commits targeting the subsystem root can fail if root validation is too narrow.
- The required mitigation is regex-based root acceptance for CamelCase roots instead of static enumeration.

### Single-file scaffold constraint on multi-file PRs

- **Signal:** `Self-correction 20-pass cap`
- **Root cause:** Single-file constraint on multi-file scaffold PR
- **Class:** Pipeline
- **Fix:** Scaffold multi-file commit path (`v38.185`)

Impact on this subsystem:
- Application shell changes commonly span multiple files and scenes.
- Pipeline handling must support multi-file changes rather than trapping correction loops.

### Docs PR CI gate variable initialization bug

- **Signal:** `UnboundLocalError: ci_result`
- **Root cause:** Docs PRs skip CI gate; variable never assigned
- **Class:** Pipeline
- **Fix:** `_CIResultDefault before gate` (`v38.175`)

Relevance:
- This is not specific to `CraftedApp`, but it affects the subsystem’s CI path under the registered workflow.

### Branch protection bypass leading to merge conflict

- **Signal:** `AGENTS.md merge conflict`
- **Root cause:** `markdown_strategy` bypassed branch protection
- **Class:** Pipeline
- **Fix:** Branch guard in `_commit_all` (`v38.185`)

Relevance:
- Any subsystem change, including shell changes, must respect branch protection and guarded commit paths.

### Retry and attempt ceiling

Forge operating rules impose:

- Maximum 20 local attempts before moving on
- No indefinite retry behavior
- Failure strategy chosen primarily by failure type, secondarily by attempt count

This is relevant because repeated shell integration failures must terminate or escalate rather than loop silently.

## Dependencies

### Direct Scene Dependencies

The `CraftedApp` scene shell directly depends on:

- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Platform / Framework Dependency

By construction from the scene declarations, this subsystem depends on:

- Swift
- SwiftUI application and scene model

### Operational Dependencies

From the health registry and Forge context:

- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`
- GitHub operations through `GitHubTool` only
- Path validation before any write
- Context trimming, polling, retry, and failure-handling infrastructure defined by Forge

### Dependency Constraints

- External input sources are untrusted and validated.
- Direct GitHub API usage is disallowed.
- Generated code is not executed.
- Secrets are excluded from logs and generated output.

These are not optional conventions; they are subsystem operating constraints inherited from Forge architecture context.