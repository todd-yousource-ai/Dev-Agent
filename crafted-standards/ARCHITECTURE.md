# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry subsystem defined as the SwiftUI `@main` app shell.

It is responsible for:

- Declaring the application’s scene structure
- Creating the primary application window via `WindowGroup`
- Installing shared environment objects required by the root UI
- Defining window presentation constraints and style
- Exposing a separate `Settings` scene for application configuration

The subsystem is implemented by:

```swift
@main struct CraftedApp: App
```

Its primary scene loads:

- `RootView()`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

Its settings scene loads:

- `SettingsView()`
- `SettingsStore.shared`

Window configuration enforced by this subsystem:

- Hidden title bar via `.windowStyle(.hiddenTitleBar)`
- Default size: `1280 × 800`
- Minimum content size enforced through `.windowResizability(.contentMinSize)`
- Documented minimum window size: `1024 × 680`
- Maximum size: unconstrained / resizable

This subsystem corresponds operationally to the shell target identified in the health registry as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

## Component Boundaries

### In Scope

`CraftedApp` owns only application-shell concerns:

- App process entrypoint
- Scene declaration
- Window configuration
- Environment object injection into top-level views
- Separation of the main application scene from the settings scene

### Out of Scope

`CraftedApp` does not own:

- Business logic inside `RootView`
- Build event production or processing inside `BuildStreamModel`
- Application state internals inside `AppState`
- Settings persistence internals inside `SettingsStore`
- Biometric enforcement mechanics for the settings window
- CI orchestration
- Telemetry transport or log writing
- Repository path validation logic
- Self-healing pipeline behavior

### Repository Boundary

For repository operations affecting this subsystem, paths must remain within valid allowed root directories. Relevant rule from repository integration lessons learned:

- Standard roots include: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, `configs`
- CamelCase roots must be accepted through smart root detection using:
  - `^[A-Za-z][A-Za-z0-9_-]*$`

This matters because Swift/Xcode targets such as `CraftedApp` must not be rejected by path security guards solely due to being a CamelCase root. A documented failure pattern specifically identified rejection of `CraftedAppShell/` when new Swift targets were not included in allowed roots.

## Data Flow

### Application Startup

1. The process enters through `@main struct CraftedApp: App`.
2. SwiftUI evaluates `body`.
3. `WindowGroup` creates the main application window.
4. `RootView()` is instantiated.
5. Shared singleton models are injected into the main scene:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
6. Window presentation policies are applied:
   - hidden title bar
   - default size `1280 × 800`
   - content-min-size resizability constraint

### Settings Flow

1. The `Settings` scene is declared separately from the main window.
2. `SettingsView()` is instantiated when the settings window is opened.
3. `SettingsStore.shared` is injected into the settings scene.

### Operational Metadata Flow

From the health registry schema, this subsystem is associated with:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`
- Languages: `swift`, `python`

This metadata informs operational ownership and monitoring boundaries for the shell subsystem, but is not itself created by the SwiftUI app shell.

## Key Invariants

### Scene and Injection Invariants

- `CraftedApp` is the single SwiftUI application entrypoint for this subsystem.
- The main application scene must provide:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- The settings scene must provide:
  - `SettingsStore.shared`

### Window Invariants

- Main window style must use `.hiddenTitleBar`.
- Default window size must be `1280 × 800`.
- Minimum supported window size is `1024 × 680`.
- Maximum size is unconstrained.

### Separation Invariants

- Main application UI and settings UI are separate scenes.
- Settings are modeled as a dedicated `Settings` scene, not embedded inside the primary `WindowGroup`.

### Security and Reliability Invariants from Forge Context

The subsystem operates within the broader Forge architecture constraints:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error must surface with context
- Secrets must never appear in logs, error messages, or generated code
- All external input is untrusted and must be validated
- Generated code is never executed by the agent
- Operator-gated waits do not auto-advance

These are system-level invariants that apply to surrounding automation and operational handling of this subsystem.

### Repository Path Invariant

- Writes affecting this subsystem must pass repository path validation.
- CamelCase target roots such as `CraftedApp` must be accepted by smart root detection rather than a brittle static allowlist.

## Failure Modes

### 1. Missing Allowed Root for Swift Target

**Signal**
- Path rejected for a CamelCase Swift target root such as `CraftedAppShell/`

**Root Cause**
- New Swift target not present in a static `_ALLOWED_ROOTS` list

**Class**
- Pipeline

**Fix**
- Use CamelCase root auto-detection with `^[A-Za-z][A-Za-z0-9_-]*$`

This failure is explicitly documented in the common failure patterns index.

### 2. Silent or Rejected Commits to Unexpected Roots

**Signal**
- Commits fail silently or are rejected by path security guards

**Root Cause**
- Root directory not explicitly allowed or not matched by smart root detection

**Class**
- Pipeline / repository integration

**Effect on CraftedApp**
- Changes to app-shell files may not land even when generated correctly

### 3. Missing Environment Object Injection

**Signal**
- Top-level views cannot resolve required shared models

**Root Cause**
- `RootView()` or `SettingsView()` instantiated without the required `.environmentObject(...)` bindings declared in scene architecture

**Class**
- Functional

**Effect**
- Main or settings UI becomes improperly configured relative to the declared shell architecture

### 4. Window Contract Drift

**Signal**
- Window style or sizing differs from specified shell behavior

**Root Cause**
- Changes to `WindowGroup` modifiers or removal of sizing constraints

**Class**
- Functional

**Effect**
- Application shell no longer matches the documented scene architecture

### 5. Settings Access Contract Violation

**Signal**
- Settings window behavior diverges from “separate scene, biometric-gated”

**Root Cause**
- Architectural change removing separate settings scene or bypassing intended gating boundary

**Class**
- Security / functional

**Effect**
- Settings access semantics no longer match the shell design contract

### 6. Operational Escalation Triggers

Per health registry escalation policy for the shell subsystem:

- `security` failures escalate to `operator_review`
- `functional` failures escalate to `auto_merge`
- `pipeline` failures escalate to `engineer_review`

## Dependencies

### Direct UI Dependencies

- `SwiftUI` application model via `App`, `Scene`, `WindowGroup`, and `Settings`
- `RootView`
- `SettingsView`

### Shared State Dependencies

- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Operational Dependencies

- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`

### Repository / Tooling Dependencies

Within the broader Forge architecture:

- All GitHub operations must go through `GitHubTool`
- Paths must be validated before any write
- Error handling escalation is governed by failure type first, then attempt count
- Retry behavior is bounded; no indefinite local retry loops
- Context and CI log truncation are automatic system behaviors

These dependencies are external to the SwiftUI shell implementation but constrain how the subsystem is changed, validated, and operated.