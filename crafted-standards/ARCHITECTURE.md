# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry subsystem defined by the SwiftUI app shell.

It is implemented as the `@main` application type:

```swift
@main struct CraftedApp: App
```

Its responsibilities are:

- Define the primary application scene graph for the macOS app.
- Construct the main window via a `WindowGroup`.
- Mount `RootView()` as the primary content view.
- Inject shared application-wide state into the main scene through SwiftUI environment objects:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configure main window presentation and sizing behavior:
  - `.hiddenTitleBar`
  - default size `1280 × 800`
  - `.contentMinSize` resizability
- Define a separate `Settings` scene.
- Mount `SettingsView()` into the settings scene.
- Inject `SettingsStore.shared` into the settings scene.

This subsystem is the application shell boundary for the Crafted macOS UI. It owns scene declaration and top-level environment wiring, not feature-specific business logic.

## Component Boundaries

### In Scope

The subsystem includes:

- The `CraftedApp` SwiftUI `App` entrypoint.
- Main scene declaration using `WindowGroup`.
- Settings scene declaration using `Settings`.
- Top-level environment object provisioning for shared state stores/models.
- Window style and size configuration for the main application window.

### Out of Scope

The subsystem does **not** define or own:

- Internal behavior of `RootView()`.
- Internal behavior of `SettingsView()`.
- Business logic inside:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- CI, telemetry, or health-registry execution logic.
- GitHub write-path validation logic.
- Failure-recovery orchestration outside of the app-shell role.

### Repository / Target Boundary Notes

The broader system documents identify a CamelCase Swift/Xcode project pattern and explicitly call out roots such as `CraftedApp`, `CraftedTests`, and `ForgeAgent`. A prior failure pattern records:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection`

From this, the relevant architectural boundary is:

- This subsystem belongs to the Crafted app shell domain.
- It must remain compatible with repository tooling that accepts CamelCase root directories via smart root detection (`^[A-Za-z][A-Za-z0-9_-]*$`), rather than relying on a static allowlist.

The health registry identifies the corresponding shell subsystem as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

## Data Flow

### 1. Application Launch

On process start, SwiftUI initializes `CraftedApp` as the app entrypoint.

### 2. Main Scene Construction

`CraftedApp.body` creates a `WindowGroup` scene containing:

```swift
RootView()
    .environmentObject(AppState.shared)
    .environmentObject(BuildStreamModel.shared)
    .environmentObject(SettingsStore.shared)
```

Data flow at this boundary is top-down:

- `AppState.shared` flows from the application shell into the root content tree.
- `BuildStreamModel.shared` flows from the application shell into the root content tree.
- `SettingsStore.shared` flows from the application shell into the root content tree.

Any descendant view under `RootView()` consumes these objects through the SwiftUI environment.

### 3. Window Configuration

The main scene applies shell-level UI constraints:

- hidden title bar
- default window size `1280 × 800`
- resizability constrained by content minimum size

Documented sizing constraints for the main window are:

- minimum: `1024 × 680`
- maximum: unconstrained / resizable

### 4. Settings Scene Construction

A separate settings scene is declared:

```swift
Settings {
    SettingsView()
        .environmentObject(SettingsStore.shared)
}
```

Data flow here is isolated to settings state injection:

- `SettingsStore.shared` flows into `SettingsView()` and its descendants.

The source document labels this settings window as:

- separate scene
- biometric-gated

The scene architecture establishes the settings scene boundary, while gating semantics are part of settings access behavior rather than the shell’s internal business logic.

## Key Invariants

The following invariants are directly supported by the source documents.

### Scene Topology Is Fixed at the App Shell

`CraftedApp` always defines:

- one main `WindowGroup` scene for `RootView()`
- one separate `Settings` scene for `SettingsView()`

The shell must not collapse these into a single scene because the TRD explicitly distinguishes them.

### Shared State Is Injected at the Top Level

The main scene must provide:

- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

The settings scene must provide:

- `SettingsStore.shared`

This is a shell contract for all descendant views that rely on environment object lookup.

### Main Window Presentation Contract

The main window must preserve the declared shell configuration:

- hidden title bar
- default size `1280 × 800`
- content-minimum-size resizability behavior

The documented size constraints are:

- minimum `1024 × 680`
- maximum unconstrained

### Settings Is a Separate, Biometric-Gated Scene

The settings window is explicitly specified as:

- separate from the main scene
- biometric-gated

Any architecture change that removes the separate scene boundary or bypasses the gating model would violate the documented shell design.

### Compatibility With CamelCase Root Detection

This subsystem exists in a repository/tooling context where CamelCase Swift/Xcode roots must be accepted automatically. Repository operations affecting this subsystem must remain compatible with the smart root detection rule:

- `^[A-Za-z][A-Za-z0-9_-]*$`

This is important because a documented pipeline failure occurred when a new Swift target root was not in `_ALLOWED_ROOTS`.

### Forge-Wide Safety Invariants Apply

As part of the Forge architecture context, this subsystem operates under these system-wide invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error surfaces with context.
- Secrets never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no automatic timeout-based bypass.

These are not unique to `CraftedApp`, but they constrain how this subsystem is modified and operated within the larger system.

## Failure Modes

### Missing or Incorrect Environment Object Injection

If `RootView()` or `SettingsView()` expects environment objects that are not injected at the app shell, the scene tree will be misconfigured. At this boundary, likely faults are:

- missing `AppState.shared`
- missing `BuildStreamModel.shared`
- missing `SettingsStore.shared`
- wrong scene receiving the wrong state object set

Because the broader architecture forbids silent failure paths, such misconfiguration must surface explicitly.

### Window Configuration Drift

Changing shell-level window configuration can violate the scene contract:

- title bar no longer hidden
- default size differs from `1280 × 800`
- minimum-size behavior no longer enforced through content sizing
- documented minimum `1024 × 680` not preserved

This is an app-shell regression, not a feature-level regression.

### Settings Scene Collapse or Misrouting

Potential failures include:

- `SettingsView()` rendered inside the main `WindowGroup` instead of a separate `Settings` scene
- `SettingsStore.shared` not injected into the settings scene
- biometric-gated settings access being bypassed by architectural simplification

These violate the documented scene architecture.

### Repository Tooling Rejection for Target Paths

A documented historical failure relevant to this subsystem is:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS`

Root cause:

- new Swift target path not accepted by static path allowlist

Fix already established in the source material:

- CamelCase root auto-detection

Architectural implication:

- changes to this subsystem may fail in automation if repository tooling regresses from smart root detection back to a brittle static list.

### Pipeline Escalation and Attempt Caps

The broader system documents additional operational failure patterns that can affect work on this subsystem:

- max 20 local attempts before moving on
- docs PRs can skip CI gates if not handled correctly
- branch-protection bypass can create merge conflicts
- failure strategy depends primarily on failure type, secondarily on attempt count

These are not UI-shell runtime failures, but they are relevant maintenance and delivery failure modes for this subsystem.

## Dependencies

### Direct SwiftUI Scene Dependencies

The `CraftedApp` shell depends on:

- `SwiftUI` application model via `App`
- `WindowGroup`
- `Settings`

### View Dependencies

The shell constructs and depends on the presence of:

- `RootView`
- `SettingsView`

### Shared State Dependencies

The shell injects these singleton/shared objects:

- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

These are required to satisfy the scene environment contract.

### Repository / Pipeline Dependencies

From the health registry and repository architecture context, the subsystem is associated with:

- repository: `todd-yousource-ai/Dev-Agent`
- subsystem: `CraftedAppShell`
- target: `crafted-app-shell`
- languages: `swift`, `python`
- CI workflow: `.github/workflows/crafted-ci.yml`
- telemetry endpoint: `logs/telemetry.jsonl`

### Tooling and Governance Dependencies

Subsystem changes are constrained by the broader Forge operating model:

- all GitHub operations go through `GitHubTool`
- paths must be validated before any write
- root-directory validation must support CamelCase Swift/Xcode roots
- failure handling follows centralized escalation rules
- context, CI-log truncation, and polling behaviors are managed automatically by shared infrastructure

These are external dependencies and constraints on how the subsystem is maintained, not part of the app-shell implementation itself.