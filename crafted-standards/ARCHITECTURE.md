# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry-point scene for the Crafted application shell.

It defines the top-level SwiftUI scene configuration:

- Creates the primary application window using `WindowGroup`
- Instantiates `RootView()` as the main window content
- Injects shared application models into the root view environment:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configures primary window behavior:
  - `.windowStyle(.hiddenTitleBar)`
  - `.defaultSize(width: 1280, height: 800)`
  - `.windowResizability(.contentMinSize)`
- Declares a separate `Settings` scene
  - Hosts `SettingsView()`
  - Injects `SettingsStore.shared`
  - Documented as biometric-gated

This subsystem is part of the application shell identified in the health registry as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

## Component Boundaries

`CraftedApp` is a scene-composition boundary, not a business-logic or persistence boundary.

Inside this subsystem:

- SwiftUI `App` declaration: `@main struct CraftedApp: App`
- Primary scene declaration via `WindowGroup`
- Settings scene declaration via `Settings`
- Environment object wiring for shared singleton-backed state
- Window presentation configuration for the main application shell

Outside this subsystem:

- `RootView` implementation and its internal UI behavior
- `SettingsView` implementation and settings UI logic
- Internal behavior of:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Biometric enforcement implementation for the settings window
- Telemetry production and transport, though the application shell is registered with:
  - `telemetry_endpoint`: `logs/telemetry.jsonl`
- CI orchestration, though the registered workflow is:
  - `.github/workflows/crafted-ci.yml`

Repository boundary implications from the source TRDs:

- The subsystem exists under a CamelCase root naming pattern consistent with Swift/Xcode targets.
- CamelCase roots must be accepted by root detection using:
  - `^[A-Za-z][A-Za-z0-9_-]*$`
- This avoids path rejection for roots such as `CraftedApp` and related targets.

## Data Flow

### Startup and Scene Initialization

1. The process enters through `@main struct CraftedApp: App`.
2. SwiftUI evaluates `body`.
3. The primary `WindowGroup` is created.
4. `RootView()` is constructed as the main scene content.
5. Shared state is injected into the main view hierarchy via environment objects:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`

### Settings Scene Flow

1. The `Settings` scene is declared alongside the primary window scene.
2. `SettingsView()` is created when the settings window is opened.
3. `SettingsStore.shared` is injected into the settings view hierarchy.
4. The settings window is documented as biometric-gated before access.

### Shell-Level Window Constraints

Main window configuration is applied at scene definition time:

- Default size: `1280 × 800`
- Minimum content-constrained size via `.windowResizability(.contentMinSize)`
- Documented minimum window size: `1024 × 680`
- Maximum size: unconstrained
- Title bar style: hidden

## Key Invariants

From the provided TRDs and architecture context, `CraftedApp` must preserve the following invariants.

### Scene Wiring Invariants

- The main application scene must render `RootView()`.
- The main scene must provide all three shared environment objects:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- The settings scene must provide `SettingsStore.shared` to `SettingsView()`.

### Windowing Invariants

- The primary window uses `.hiddenTitleBar`.
- The primary window defaults to `1280 × 800`.
- Minimum supported window size is `1024 × 680`.
- Window maximum size is unconstrained.
- Resizability is content-min-size constrained.

### Security and Trust Invariants

Applicable repository-wide Forge invariants constrain this subsystem as part of the application shell:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.

### Settings Access Invariant

- The settings window is a separate scene and is documented as biometric-gated.
- `CraftedApp` may declare the settings scene, but must not weaken that gating contract.

### Repository Path Invariant

Because this subsystem uses a CamelCase target/root naming convention:

- Repository tooling must permit CamelCase roots matching `^[A-Za-z][A-Za-z0-9_-]*$`.
- Dot-prefixed roots such as `.github` require explicit allowlisting.
- Path validation must occur before any write operation.

## Failure Modes

### Missing or Incorrect Root Allowlisting

Observed failure pattern:

- `Path rejected: CraftedAppShell/`
- Root cause: new Swift target not present in `_ALLOWED_ROOTS`
- Class: `Pipeline`
- Fix: CamelCase root auto-detection

Impact on this subsystem:

- Changes to `CraftedApp` or adjacent Swift targets may be silently blocked or rejected if repository tooling does not recognize CamelCase roots.
- This is a pipeline/tooling failure, not a runtime SwiftUI failure.

### Silent or Context-Free Error Handling

Repository-level architecture forbids silent failures. Violations would include:

- scene initialization failures not surfaced with context
- settings access failures that degrade silently
- auth/identity-related failures that continue without explicit handling

These are architectural violations even where the exact implementation is outside `CraftedApp`.

### Settings Access Contract Drift

If the settings scene remains declared but biometric gating is omitted or bypassed in the associated implementation, the subsystem would violate the documented settings-window contract.

### Window Constraint Drift

Changes to scene configuration can break shell expectations if they alter:

- hidden title bar behavior
- default window size
- minimum content sizing behavior
- unconstrained maximum resizing behavior

### Pipeline Retry / Attempt Exhaustion

Relevant repository failure controls:

- Never retry indefinitely
- Maximum 20 local attempts before moving on

This matters when changes to `CraftedApp` are being repaired or scaffolded by automation; repeated failures are capped and escalated rather than retried without bound.

## Dependencies

Direct architectural dependencies named in the TRDs:

- SwiftUI `App` scene system
- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

Registered subsystem metadata dependencies:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`

Repository/process dependencies that constrain work on this subsystem:

- GitHub operations must go through `GitHubTool`
- Paths must be validated before any write
- CamelCase root detection must be supported for Swift/Xcode targets
- Dot-prefixed roots such as `.github` require explicit allowlisting

This subsystem does not, based on the provided sources, define its own persistence layer, networking layer, or domain-specific business logic. Its role is application-shell scene composition and shared environment injection.