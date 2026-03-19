# TRD-1-macOS-Application-Shell

_Source: `TRD-1-macOS-Application-Shell.docx` — extracted 2026-03-19 18:28 UTC_

---

TRD-1

macOS Application Shell

Technical Requirements Document  •  v1.1

# 1. Purpose and Scope

This document specifies the complete technical requirements for the macOS Application Shell — the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems of the Consensus Dev Agent.

The Shell owns:

Installation and distribution — .app bundle, drag-to-Applications, Sparkle auto-update

Identity and authentication — biometric gate, Keychain secret storage, session lifecycle

Swift module architecture — module boundaries, concurrency model, state ownership

SwiftUI view hierarchy — root views, navigation model, view model specs

XPC communication — authenticated channel between Swift UI and Python backend

Process management — launch, monitor, restart, credential delivery

Settings and onboarding — first-launch flow, UserDefaults schema, migration

Logging and observability — os_log definitions, privacy annotations, crash symbolication

Document import — UTType handling, file validation, NSOpenPanel, drag-drop

Menu bar, Dock, notifications — native macOS integration

# 2. System Architecture

## 2.1 Two-Process Model

The application has a strict two-process architecture. The Swift process owns the UI, authentication, and secret management. The Python process owns all build intelligence.

## 2.2 Swift Module Breakdown

The Swift layer is organized into eight discrete modules. Each module is a Swift Package target with explicit product and dependency declarations.

## 2.3 Module Dependency Graph

## 2.4 Concurrency Model

All SwiftUI views and @ObservableObject updates run on MainActor. All backend I/O, file operations, and subprocess communication run on background actors. The rule is: never block MainActor.

# 3. SwiftUI View Hierarchy

## 3.1 Scene Architecture

## 3.2 Root View Decision Tree

## 3.3 MainView — Three-Panel Layout

## 3.4 View Model Specifications

### 3.4.1 AppState

### 3.4.2 BuildStreamModel

### 3.4.3 SettingsStore

## 3.5 Card Model Schema

## 3.6 Sheet and Modal Presentation Model

# 4. Authentication and Session Management

## 4.1 SessionState Machine

## 4.2 LocalAuthentication Implementation

### 4.2.1 Biometric Policy Table

## 4.3 Session Key Derivation

# 5. Keychain Secret Storage

## 5.1 Secret Inventory

## 5.2 KeychainManager Actor

## 5.3 Credential Delivery to Python Backend

# 6. XPC Communication Channel

## 6.1 Transport

Communication uses a Unix domain socket (AF_UNIX). The socket is created by the Swift process, placed at a unique per-instance path, and passed to the Python backend via environment variable. Line-delimited JSON (one JSON object per line, terminated by \n) is the wire format.

## 6.2 Peer Authentication

The socket must authenticate the Python backend before accepting messages. Authentication uses a challenge-nonce exchange on first connection.

## 6.3 Message Schema

## 6.4 Message Type Reference

### Swift → Python

### Python → Swift

## 6.5 Channel Hardening Rules

# 7. Python Backend Process Management

## 7.1 Sandboxing Decision

v1 of the app is NOT sandboxed. The Python backend requires subprocess execution (for test running), unrestricted filesystem access (for workspace/log directories), and network access to multiple API endpoints. Full sandbox entitlements for all of these would require App Store review and significant architectural changes.

## 7.2 Python Runtime Bundling

## 7.3 Launch Sequence

## 7.4 Health Monitoring

## 7.5 Restart Policy

# 8. Auto-Update (Sparkle)

## 8.1 Sparkle Configuration

## 8.2 EdDSA Key Management

## 8.3 Appcast Schema

## 8.4 Required Entitlements for Sparkle

# 9. Logging and Observability

## 9.1 os_log Subsystem and Category Definitions

## 9.2 Privacy Annotations

All os_log calls must include privacy annotations. The default is .private — secrets and user data are automatically redacted in system logs. Only information safe for external viewing should be .public.

## 9.3 Log Levels

## 9.4 dSYM and Crash Symbolication

# 10. Menu Bar, Dock, and Notifications

## 10.1 Application Menu Structure

## 10.2 Keyboard Shortcut Conflict Audit

## 10.3 Dock Integration

## 10.4 Notification Center Integration

# 11. Document Import

## 11.1 UTType Declarations

## 11.2 NSOpenPanel Configuration

## 11.3 Import Validation Rules

## 11.4 Drag-Drop Handling

## 11.5 Document Preview

Document preview opens as a sheet. Format rendering:

# 12. Multi-Instance Prevention

## 12.1 Single-Instance Enforcement

Multi-instance prevention is enforced because:

Two instances share the same Application Support directory — concurrent writes to thread state JSON files corrupt build state

Two instances sharing the same XPC socket path cause connection conflicts

Two instances of the same engineer would confuse the build ledger

# 13. Accessibility

## 13.1 axIdentifier Naming Convention

## 13.2 Focus Management

## 13.3 Color Contrast Requirements

# 14. Privacy Manifest

## 14.1 PrivacyInfo.xcprivacy

Required by Apple for all distributed apps since 2024. Must be included in the app bundle at Contents/PrivacyInfo.xcprivacy.

# 15. Settings Schema and Migration

## 15.1 Schema Versioning

## 15.2 Keychain Migration

If the bundle ID changes (e.g. from development ai.yousource.forgeagent.debug to production ai.yousource.forgeagent), Keychain items are not automatically migrated. The user must re-enter credentials. The onboarding flow handles this gracefully: if Keychain items for the current bundle ID are not found, the relevant onboarding step is re-shown.

# 16. Localization Infrastructure

## 16.1 String Extraction Setup

English-only in v1. However, all user-visible strings must use NSLocalizedString from the start. This enables localization in v2 without touching every callsite.

# 17. Security Requirements

## 17.1 Hardened Runtime Entitlements (Complete)

## 17.2 Data Protection Rules

No secret is permitted outside Keychain — violation is a release blocker

No secret in UserDefaults, plist, NSUbiquitousKeyValueStore, or any file

No secret in log output — os_log privacy annotations enforce this

No secret in crash reports — session key cleared in NSUncaughtExceptionHandler

No secret in XPC messages beyond the single credentials delivery message

No secret in pasteboard — disable copy/paste on masked text fields

Build content (TRDs, PRD text, generated code) is not secret — unencrypted storage is acceptable

Keychain items use kSecAttrAccessibleWhenUnlockedThisDeviceOnly — no iCloud sync

# 18. Performance Requirements

# 19. Testing Requirements

## 19.1 Unit Tests

## 19.2 axIdentifier Coverage

All interactive UI elements must have an axIdentifier set. XCUITest smoke test must verify:

Onboarding flow: all fields and buttons reachable by identifier

Auth gate: Touch ID button and passcode fallback reachable

MainView: navigator, stream, context panel reachable

Gate card: all four action buttons (yes/skip/stop/correction) reachable by gate-specific identifiers

Settings: all fields and test buttons reachable

## 19.3 Security Tests

No secrets in UserDefaults: grep UserDefaults storage after onboarding for key patterns

No secrets in logs: run full session with known test keys; grep log files for those key values

No secrets in crash report: inject crash after credential delivery; verify crash report contains no key material

Session cleared on background: verify session state transitions to .timedOut after backgrounding for timeout duration

Single instance: launch second copy while first is running; verify second terminates and first is brought to front

XPC nonce reuse: attempt to reconnect with same nonce; verify connection rejected

## 19.4 Build Validation Checklist

Run before every release build:

codesign --verify --deep --strict ForgeAgent.app — must exit 0

xcrun notarytool submit ForgeAgent.app.zip --wait — must succeed

xcrun stapler validate ForgeAgent.app — must confirm stapled

spctl --assess --type exec ForgeAgent.app — must show: accepted

All .so files in site-packages signed: codesign -dv site-packages/**/*.so

PrivacyInfo.xcprivacy present: ls ForgeAgent.app/Contents/PrivacyInfo.xcprivacy

Sparkle SUPublicEDKey present in Info.plist

VERSION file matches CFBundleShortVersionString

# 20. Build System Requirements

# 21. Out of Scope

# 22. Open Questions

# Appendix A: Error Type Reference

# Appendix B: Document Change Log