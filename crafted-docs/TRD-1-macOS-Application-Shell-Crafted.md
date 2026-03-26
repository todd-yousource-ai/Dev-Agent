# TRD-1-macOS-Application-Shell-Crafted

_Source: `TRD-1-macOS-Application-Shell-Crafted.docx` — extracted 2026-03-26 21:47 UTC_

---

TRD-1

macOS Application Shell

Technical Requirements Document  •  v1.1

Field | Value
Product | Crafted
Document | TRD-1: macOS Application Shell
Version | 1.1 — Complete Specification
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Min macOS | 13.0 (Ventura)
Language | Swift 5.9+, SwiftUI, Python 3.12 (bundled)
Depends on | None — foundational TRD
Required by | TRD-2, TRD-3, TRD-4, TRD-5, TRD-8 (all reference this)

# 1. Purpose and Scope

This document specifies the complete technical requirements for the macOS Application Shell — the native Swift/SwiftUI container that packages, installs, authenticates, and orchestrates all subsystems of the Crafted.

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

SCOPE | This TRD covers the Swift shell and its interfaces only. Visual design is in TRD-6. The Python consensus backend is in TRD-2 and TRD-3.

# 2. System Architecture

## 2.1 Two-Process Model

The application has a strict two-process architecture. The Swift process owns the UI, authentication, and secret management. The Python process owns all build intelligence.

┌─────────────────────────────────────────────────────────┐
│                   Crafted.app Bundle                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Swift UI Process  (main)            │  │
│  │                                                  │  │
│  │  AppShell module    AuthKit module               │  │
│  │  BuildStream module KeychainKit module           │  │
│  │  Settings module    XPCBridge module             │  │
│  │  DocImport module   ProcessManager module        │  │
│  └─────────────────────┬────────────────────────────┘  │
│                        │  Authenticated Unix socket     │
│                        │  Line-delimited JSON           │
│  ┌─────────────────────▼────────────────────────────┐  │
│  │           Python Backend Process (child)         │  │
│  │                                                  │  │
│  │  build_director   consensus     github_tools     │  │
│  │  prd_planner      document_store  thread_state   │  │
│  │  build_ledger     test_runner   audit            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Resources/                                             │
│  ├── python3.12          (CPython 3.12, standalone)     │
│  ├── site-packages/      (all deps, pre-built wheels)   │
│  └── agent/              (Python source)                │
└─────────────────────────────────────────────────────────┘

## 2.2 Swift Module Breakdown

The Swift layer is organized into eight discrete modules. Each module is a Swift Package target with explicit product and dependency declarations.

Module | Responsibility | Imports | Public API Surface
AppShell | Root app entry, scene management, window lifecycle | AuthKit, BuildStream, Settings | AppShellApp (entry point)
AuthKit | LocalAuthentication gate, session state machine, timeout | KeychainKit | AuthManager, SessionState, AuthError
KeychainKit | Keychain CRUD, secret delivery protocol | — | KeychainManager, SecretKey, KeychainError
XPCBridge | Unix socket channel, message encode/decode, peer auth | KeychainKit | XPCChannel, XPCMessage, XPCError
ProcessManager | Backend launch, health monitoring, restart policy | XPCBridge, KeychainKit | BackendProcess, ProcessState, ProcessError
BuildStream | Build card stream, gate rendering, progress tracking | XPCBridge | BuildStreamView, CardModel, GateModel
Settings | UserDefaults schema, onboarding flow, settings validation | KeychainKit, AuthKit | SettingsStore, OnboardingState, SettingsView
DocImport | Document drag-drop, NSOpenPanel, format extraction, embedding status | — | DocumentImporter, ProjectDocument, DocImportError

## 2.3 Module Dependency Graph

AppShell
  ├── AuthKit
  │   └── KeychainKit
  ├── BuildStream
  │   └── XPCBridge
  │       └── KeychainKit
  ├── Settings
  │   ├── KeychainKit
  │   └── AuthKit
  ├── DocImport          (no internal deps)
  └── ProcessManager
      ├── XPCBridge
      └── KeychainKit

Rule: No circular dependencies. KeychainKit is a leaf — it imports nothing internal.
Rule: BuildStream must not import AuthKit or KeychainKit directly.
Rule: ProcessManager is the only module that launches subprocesses.

## 2.4 Concurrency Model

All SwiftUI views and @ObservableObject updates run on MainActor. All backend I/O, file operations, and subprocess communication run on background actors. The rule is: never block MainActor.

// MainActor: all UI state mutations
@MainActor class AppState: ObservableObject { ... }
@MainActor class BuildStreamModel: ObservableObject { ... }
@MainActor class SettingsStore: ObservableObject { ... }

// Background actor: I/O and subprocess
actor XPCChannel { ... }
actor BackendProcess { ... }
actor KeychainManager { ... }

// Bridge pattern: actor → MainActor update
Task { @MainActor in
    appState.session = .active
}

// PROHIBITED: Never call MainActor code synchronously from background actor
// PROHIBITED: Never do file I/O or network on MainActor
// PROHIBITED: Never use DispatchQueue.main.async — use Task { @MainActor in }

# 3. SwiftUI View Hierarchy

## 3.1 Scene Architecture

@main struct CraftedApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(AppState.shared)
                .environmentObject(BuildStreamModel.shared)
                .environmentObject(SettingsStore.shared)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1280, height: 800)
        .windowResizability(.contentMinSize)

        // Settings window — separate scene, biometric-gated
        Settings {
            SettingsView()
                .environmentObject(SettingsStore.shared)
        }
    }
}

// Minimum window size: 1024 × 680
// Maximum: unconstrained (resizable)

## 3.2 Root View Decision Tree

RootView
  ├─ OnboardingState != .complete  →  OnboardingContainerView
  │   ├─ .notStarted              →  WelcomeView
  │   ├─ .apiKeys                 →  APIKeysView
  │   ├─ .githubAuth              →  GitHubAuthView
  │   ├─ .engineerProfile         →  EngineerProfileView
  │   └─ .biometricSetup          →  BiometricSetupView
  │
  └─ OnboardingState == .complete
      ├─ session == .locked       →  AuthGateView
      │   (full-screen Touch ID prompt)
      └─ session == .active       →  MainView
          (three-panel layout)

## 3.3 MainView — Three-Panel Layout

MainView
└── NavigationSplitView (columnVisibility: .all)
    ├── sidebar: NavigatorView  [240px, fixed]
    │   ├── ProjectsSection
    │   │   └── ProjectRow (ForEach projects)
    │   ├── BuildsSection
    │   │   └── BuildHistoryRow (ForEach completedBuilds)
    │   ├── EngineersSection  (visible if multiEngineer)
    │   │   └── EngineerStatusRow
    │   └── DocumentsSection
    │       └── DocumentRow (ForEach project.documents)
    │
    ├── content: BuildStreamView  [flex]
    │   ├── StageHeaderBar
    │   ├── ScrollView (cards)
    │   │   └── ForEach cards: CardView (typed switch)
    │   │       ├── ScopeCard
    │   │       ├── PRDGeneratedCard
    │   │       ├── ReviewPassCard
    │   │       ├── GateCard  ← blocks scroll until resolved
    │   │       ├── ErrorCard
    │   │       └── BuildCompleteCard
    │   └── BuildIntentBar  (shown when no active build)
    │
    └── detail: ContextPanelView  [320px, fixed]
        └── TabView (selection: contextTab)
            ├── .prd    →  PRDDetailView
            ├── .pr     →  PRDetailView
            ├── .tests  →  TestResultsView
            ├── .ci     →  CIStatusView
            └── .cost   →  CostTrackerView

NOTE | NavigationSplitView on macOS 13 has a known issue where sidebar column width resets on window resize. Workaround: persist columnWidth in UserDefaults and restore via .navigationSplitViewColumnWidth(_:) modifier.

## 3.4 View Model Specifications

### 3.4.1 AppState

@MainActor class AppState: ObservableObject {
    static let shared = AppState()

    @Published var session: SessionState = .locked
    @Published var onboardingState: OnboardingState = .notStarted
    @Published var activeProject: Project? = nil
    @Published var backendState: BackendState = .stopped
    @Published var errorBanner: AppError? = nil
}

enum SessionState  { case locked, unlocking, active, timedOut }
enum BackendState  { case stopped, starting, ready, unhealthy, crashed }
enum OnboardingState: String {
    case notStarted, apiKeys, githubAuth, engineerProfile,
         biometricSetup, complete
}

### 3.4.2 BuildStreamModel

@MainActor class BuildStreamModel: ObservableObject {
    static let shared = BuildStreamModel()

    @Published var cards: [CardModel] = []
    @Published var activeGate: GateModel? = nil
    @Published var progress: BuildProgress = .idle
    @Published var sessionCost: Double = 0.0
}

struct BuildProgress {
    var stage: BuildStage         // .scoping, .prdPlan, .prdGen, .prPipeline, .done
    var stageNumber: Int          // 1–8
    var totalStages: Int          // 8
    var prdNumber: Int            // current PRD
    var totalPRDs: Int
    var prNumber: Int             // current PR
    var estimatedCostRemaining: Double
    static let idle = BuildProgress(stage:.scoping, stageNumber:0,
        totalStages:8, prdNumber:0, totalPRDs:0, prNumber:0,
        estimatedCostRemaining:0)
}

### 3.4.3 SettingsStore

@MainActor class SettingsStore: ObservableObject {
    static let shared = SettingsStore()

    // Non-sensitive — UserDefaults backed
    @AppStorage("display_name")       var displayName: String = ""
    @AppStorage("default_repo_owner") var repoOwner: String = ""
    @AppStorage("default_repo_name")  var repoName: String = ""
    @AppStorage("pr_batch_size")      var prBatchSize: Int = 5
    @AppStorage("auto_approve_batches") var autoApproveBatches: Int = 0
    @AppStorage("cost_warn_threshold") var costWarnThreshold: Double = 0.50
    @AppStorage("cost_stop_threshold") var costStopThreshold: Double = 2.00
    @AppStorage("biometric_timeout_sec") var biometricTimeout: Int = 300
    @AppStorage("onboarding_state")   var onboardingRaw: String = "notStarted"
    @AppStorage("biometric_enrolled") var biometricEnrolled: Bool = false
    @AppStorage("settings_schema_version") var schemaVersion: Int = 0

    // Sensitive — Keychain backed (read-only from here, written via KeychainManager)
    var anthropicKeyStored: Bool { KeychainManager.shared.exists(.anthropicAPIKey) }
    var openAIKeyStored: Bool    { KeychainManager.shared.exists(.openAIAPIKey) }
    var githubTokenStored: Bool  { KeychainManager.shared.exists(.githubToken) }
}

## 3.5 Card Model Schema

CardType | Required Fields | Optional Fields | Gate?
scope | subsystem, scopeSummary, branch, docs[] | ambiguities[] | No
prdGenerated | prdId, title, winner, scores, durationSec | docxPath, preview | No
reviewPass | passNumber, passName, claudeFeedback, gptFeedback | changesApplied | No
gate | gateId, gateType, title, body, options[] | correctionHint | YES — blocks
error | errorType, message, recoverable | retryAction | No
prOpened | prNumber, title, branch, url |  | No
testResult | prNumber, passed, totalTests, failedTests | stdout, stderr | No
buildComplete | prdCount, prCount, totalCost, pullsUrl |  | No

## 3.6 Sheet and Modal Presentation Model

// All modals are sheets (not separate windows) unless noted

MainView
  .sheet(isPresented: $showDocumentPicker)   { DocumentPickerView() }
  .sheet(isPresented: $showDocumentPreview)  { DocumentPreviewView(doc: selectedDoc) }
  .sheet(isPresented: $showBuildHistory)     { BuildHistoryView() }
  .alert(item: $appState.errorBanner)        { AlertView(error: $0) }

GateCard
  // Inline expansion — NOT a sheet
  // Correction text field expands in-card on "Correction" tap
  // No navigation away from the stream view

AuthGateView
  // Full-screen overlay — NOT a sheet
  // Presented via ZStack overlay on RootView
  // z-index above everything including error alerts

# 4. Authentication and Session Management

## 4.1 SessionState Machine

┌──────────┐  launch+enrolled   ┌────────────┐
│  locked  │ ─────────────────▶ │ unlocking  │
│ (initial)│                    │(LAContext) │
└──────────┘                    └─────┬──────┘
     ▲                                │ success
     │ timeout/bg/lock                ▼
     │                          ┌──────────┐
     └────────────────────────── │  active  │
                                 └──────────┘
                                      │ 3 failures
                                      ▼
                                 ┌──────────┐
                                 │ timedOut │
                                 └──────────┘

Transitions:
  locked → unlocking:  app foregrounded with biometric_enrolled = true
  unlocking → active:  LAContext.evaluatePolicy succeeds
  unlocking → locked:  LAContext.evaluatePolicy fails (user cancels)
  active → timedOut:   backgrounded > biometric_timeout_sec
  active → locked:     Cmd+L, lock button, screen sleep
  timedOut → unlocking: user foregrounds app
  any → locked:        applicationWillTerminate

## 4.2 LocalAuthentication Implementation

import LocalAuthentication

actor AuthManager {
    private var context = LAContext()

    func authenticate(reason: String) async throws -> Bool {
        let ctx = LAContext()
        var nsError: NSError?

        guard ctx.canEvaluatePolicy(
            .deviceOwnerAuthenticationWithBiometrics, error: &nsError) else {
            throw AuthError.biometricUnavailable(
                nsError?.localizedDescription ?? "Touch ID not available")
        }

        do {
            return try await ctx.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: reason
            )
        } catch let error as LAError {
            switch error.code {
            case .userCancel:    throw AuthError.cancelled
            case .biometryLockout: throw AuthError.lockedOut
            case .biometryNotEnrolled: throw AuthError.notEnrolled
            default: throw AuthError.failed(error.localizedDescription)
            }
        }
    }

    // Separate context per auth — do NOT reuse LAContext across calls
    // LAContext is single-use after evaluatePolicy succeeds
}

### 4.2.1 Biometric Policy Table

Scenario | Policy | Fallback | Notes
App launch (enrolled) | deviceOwnerAuthenticationWithBiometrics | deviceOwnerAuthentication (passcode) | Re-auth on each cold launch
App foreground after timeout | deviceOwnerAuthenticationWithBiometrics | deviceOwnerAuthentication | Same as launch
Settings open | deviceOwnerAuthenticationWithBiometrics | No fallback — biometric required | Prevents shoulder-surf settings access
Reveal API key | deviceOwnerAuthenticationWithBiometrics | No fallback | Per-reveal, new LAContext each time
Touch ID not enrolled | — | Prompt to enroll in System Settings | Show enrollment link
3 consecutive failures | Biometric locked by OS | Passcode via deviceOwnerAuthentication | OS handles lockout, not app
Touch ID hardware absent | — | deviceOwnerAuthentication (passcode) | App usable without biometrics

## 4.3 Session Key Derivation

// Session key is derived per-session, never stored
// Used as AAD (additional authenticated data) for Keychain operations
// Cleared from memory on: timeout, lock, terminate, crash

struct SessionKey {
    let value: Data  // 32 bytes, AES-256

    init() throws {
        var bytes = [UInt8](repeating: 0, count: 32)
        let status = SecRandomCopyBytes(kSecRandomDefault, 32, &bytes)
        guard status == errSecSuccess else { throw AuthError.keyGenFailed }
        self.value = Data(bytes)
    }

    mutating func clear() {
        // Zero the backing bytes before deallocation
        value.withUnsafeMutableBytes { ptr in
            memset_s(ptr.baseAddress!, ptr.count, 0, ptr.count)
        }
    }
}

// AppState holds the session key only while session == .active
// On any transition away from .active: sessionKey.clear(); sessionKey = nil

# 5. Keychain Secret Storage

## 5.1 Secret Inventory

SecretKey enum case | kSecAttrAccount | Accessibility | Biometric Required | Notes
.anthropicAPIKey | anthropic_api_key | WhenUnlockedThisDeviceOnly | No (session required) | Delivered to backend via XPC
.openAIAPIKey | openai_api_key | WhenUnlockedThisDeviceOnly | No (session required) | Delivered to backend via XPC
.githubToken | github_token | WhenUnlockedThisDeviceOnly | No (session required) | Delivered to backend via XPC
.githubAppPrivateKey | github_app_private_key | WhenUnlockedThisDeviceOnly + BiometryAny | Yes — explicit reveal only | PEM format, used for GitHub App JWT signing
.engineerId | engineer_id | WhenUnlocked | No | Not secret per se — in Keychain for consistency

RULE | kSecAttrAccessibleWhenUnlockedThisDeviceOnly prevents iCloud Keychain sync and migration to new device. This is intentional — credentials must be re-entered on a new machine.

## 5.2 KeychainManager Actor

actor KeychainManager {
    static let shared = KeychainManager()
    private let service = "ai.yousource.crafted"

    enum SecretKey: String {
        case anthropicAPIKey  = "anthropic_api_key"
        case openAIAPIKey     = "openai_api_key"
        case githubToken      = "github_token"
        case githubAppPrivKey = "github_app_private_key"
        case engineerId       = "engineer_id"
    }

    func store(_ value: String, for key: SecretKey) throws {
        let data = value.data(using: .utf8)!
        let query: CFDictionary = [
            kSecClass:       kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: key.rawValue,
            kSecValueData:   data,
            kSecAttrAccessible: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ] as CFDictionary
        var status = SecItemAdd(query, nil)
        if status == errSecDuplicateItem {
            status = SecItemUpdate([kSecClass:kSecClassGenericPassword,
                kSecAttrService:service, kSecAttrAccount:key.rawValue] as CFDictionary,
                [kSecValueData:data] as CFDictionary)
        }
        guard status == errSecSuccess else { throw KeychainError.write(status) }
    }

    func read(_ key: SecretKey) throws -> String {
        guard await AppState.shared.session == .active else {
            throw AuthError.sessionNotActive
        }
        let query: CFDictionary = [
            kSecClass:kSecClassGenericPassword, kSecAttrService:service,
            kSecAttrAccount:key.rawValue, kSecReturnData:true,
            kSecMatchLimit:kSecMatchLimitOne,
        ] as CFDictionary
        var result: AnyObject?
        let status = SecItemCopyMatching(query, &result)
        guard status == errSecSuccess,
              let data = result as? Data,
              let str = String(data:data, encoding:.utf8)
        else { throw KeychainError.read(status) }
        return str
    }

    func exists(_ key: SecretKey) -> Bool {
        let query: CFDictionary = [kSecClass:kSecClassGenericPassword,
            kSecAttrService:service, kSecAttrAccount:key.rawValue,
            kSecMatchLimit:kSecMatchLimitOne, kSecReturnAttributes:true,
        ] as CFDictionary
        return SecItemCopyMatching(query, nil) == errSecSuccess
    }

    func delete(_ key: SecretKey) throws {
        let status = SecItemDelete([kSecClass:kSecClassGenericPassword,
            kSecAttrService:service, kSecAttrAccount:key.rawValue] as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound
        else { throw KeychainError.delete(status) }
    }
}

## 5.3 Credential Delivery to Python Backend

// Credentials sent via XPC once after successful auth and backend ready signal
// Never sent as command-line args (visible in ps) or written to temp files

struct CredentialsMessage: Codable {
    let type = "credentials"
    let id: String         // UUID
    let timestamp: Int64   // Unix ms
    let anthropicAPIKey: String
    let openAIAPIKey: String
    let githubToken: String
    let engineerId: String
}

// Delivery sequence:
// 1. Backend sends { "type": "ready" }
// 2. Swift reads each secret from Keychain (session must be .active)
// 3. Swift sends CredentialsMessage over XPC channel
// 4. Backend holds in memory — never writes to disk
// 5. On backend restart: Swift re-delivers credentials automatically
// 6. On session lock: credentials in Python backend are NOT cleared
//    (backend holds until process terminates or new credentials delivered)

# 6. XPC Communication Channel

## 6.1 Transport

Communication uses a Unix domain socket (AF_UNIX). The socket is created by the Swift process, placed at a unique per-instance path, and passed to the Python backend via environment variable. Line-delimited JSON (one JSON object per line, terminated by \n) is the wire format.

// Socket path — unique per instance to prevent collision
let socketPath = FileManager.default
    .temporaryDirectory
    .appendingPathComponent("crafted-\(ProcessInfo.processInfo.processIdentifier).sock")
    .path

// Passed to Python via environment:
env["CRAFTED_XPC_SOCKET"] = socketPath

// Python backend connects as client after startup:
// import socket; s = socket.socket(socket.AF_UNIX); s.connect(CRAFTED_XPC_SOCKET)

## 6.2 Peer Authentication

The socket must authenticate the Python backend before accepting messages. Authentication uses a challenge-nonce exchange on first connection.

// Swift generates nonce at backend launch time, passes via env var
let nonce = UUID().uuidString  // 36-char UUID
env["CRAFTED_XPC_NONCE"] = nonce

// Handshake protocol:
// 1. Python connects to socket
// 2. Python sends:  { "type": "handshake", "nonce": "<CRAFTED_XPC_NONCE value>" }
// 3. Swift verifies nonce matches what it generated
// 4. Swift sends:   { "type": "handshake_ack", "session_id": "<uuid>" }
// 5. Both sides now use session_id in all subsequent messages for correlation
// 6. If nonce mismatch: Swift closes connection immediately

// Nonce is one-time — connection refused if already used
// Timeout: if handshake not received within 10 seconds of connect, close

## 6.3 Message Schema

Field | Type | Required | Description
type | String | Yes | Message type — see Section 6.4
id | String (UUID) | Yes | Unique message ID for request/response correlation
session_id | String (UUID) | Yes | Session ID from handshake_ack — validates peer
timestamp | Int64 | Yes | Unix epoch milliseconds
payload | Object | Conditional | Type-specific data — see Section 6.4

## 6.4 Message Type Reference

### Swift → Python

type | payload fields | Description
credentials | anthropicAPIKey, openAIAPIKey, githubToken, engineerId | Deliver secrets post-auth
build_intent | intent: String, projectId: String | Start a build
gate_response | gateId: String, response: String ("yes"|"skip"|"stop"|correction) | Operator gate answer
cancel | reason: String | Cancel active build
ping | (empty) | Health check
settings_update | key: String, value: Any | Config change without restart
shutdown | reason: String | Graceful backend shutdown request

### Python → Swift

type | payload fields | Description
ready | version: String, pythonVersion: String | Backend initialized and ready
handshake | nonce: String | Peer auth (first message)
build_card | cardType, title, body, timestamp | Agent output for stream UI
gate_card | gateId, gateType, title, body, options[] | Gate requiring operator input
error_card | errorType, message, recoverable: Bool, retryAction? | Error for display
progress | stage, stageNum, totalStages, prdNum, totalPrds, prNum, costSoFar, estRemaining | Progress update
pong | uptimeSec: Int | Health check response
build_complete | prdCount, prCount, totalCost, pullsUrl | Build finished

## 6.5 Channel Hardening Rules

Rule | Implementation
Max message size | 16 MB. Messages larger than 16 MB are rejected; connection closed.
Rate limit | Max 100 messages/second from backend. Excess messages discarded with error_card sent back.
Nonce reuse | Once a handshake nonce is used, the same nonce is rejected if the process tries to reconnect.
session_id validation | Every message after handshake must include matching session_id. Mismatch closes connection.
Reconnection | If connection drops mid-build: Swift waits 2s, restarts backend, re-delivers credentials, sends build state for resume.
Malformed JSON | Log and discard. Do not crash. Increment malformed message counter; close connection if > 10 consecutive.

# 7. Python Backend Process Management

## 7.1 Sandboxing Decision

v1 of the app is NOT sandboxed. The Python backend requires subprocess execution (for test running), unrestricted filesystem access (for workspace/log directories), and network access to multiple API endpoints. Full sandbox entitlements for all of these would require App Store review and significant architectural changes.

Capability | Sandboxed? | Mitigation if not sandboxed
File system access | No | Scoped to ~/Library/Application Support/Crafted/ by code convention, not by OS enforcement
Subprocess execution (pytest) | No | Subprocess paths validated before execution; shell=True never used
Network access | No | Outbound only; no inbound ports opened; API keys required for all calls
Inter-process communication | No | XPC socket on loopback only; per-instance nonce authentication

DECISION | NOT sandboxed in v1. App Store (sandboxed) version is v2. Before v2, an entitlement audit must be conducted to determine minimum entitlements for sandboxed operation.

## 7.2 Python Runtime Bundling

Decision | Choice | Rationale
Runtime type | Standalone CPython binary (not .framework) | ~15 MB vs ~80 MB for framework; no dylib management required
Architecture | Universal2 (arm64 + x86_64 in one binary) | Single .app supports both Apple Silicon and Intel Macs
Python version | 3.12.x (latest patch) | LTS-equivalent; numpy/faiss wheels available
Binary extensions | Pre-built universal2 wheels from PyPI or cibuildwheel | Avoids compile-at-install; must be signed as part of bundle
Signing | All .so and .dylib files in site-packages must be signed | Hardened Runtime requires all loaded code to be signed
PYTHONPATH injection | Set via environment variable before Process.run() | Allowed without special entitlement for child processes

CRITICAL | All .so binary extensions (numpy, faiss-cpu, etc.) must be individually code-signed with the Developer ID Application certificate before bundling. Unsigned .so files will be blocked by Gatekeeper on first import, causing a silent backend crash.

## 7.3 Launch Sequence

actor BackendProcess {
    private var process: Process?
    private var channel: XPCChannel?
    private var restartCount = 0
    private var lastRestartTime: Date?

    func launch() async throws {
        let bundle = Bundle.main
        let python = bundle.url(forResource:"python3.12", withExtension:nil,
                                subdirectory:"Resources")!
        let main   = bundle.url(forResource:"main", withExtension:"py",
                                subdirectory:"Resources/agent")!
        let resources = bundle.url(forResource:".", withExtension:nil)!.path

        // Generate per-instance socket path and nonce
        let socketPath = NSTemporaryDirectory() +
            "crafted-\(ProcessInfo.processInfo.processIdentifier).sock"
        let nonce = UUID().uuidString

        let p = Process()
        p.executableURL = python
        p.arguments     = [main.path]
        p.environment   = [
            "PYTHONPATH":       resources + "/site-packages",
            "CRAFTED_XPC_SOCKET": socketPath,
            "CRAFTED_XPC_NONCE":  nonce,
            "CRAFTED_WORKSPACE":  appSupportPath,
            "CRAFTED_LOG_DIR":    logsPath,
            // No secrets in environment
        ]
        p.terminationHandler = { [weak self] _ in
            Task { await self?.handleTermination($0.terminationStatus) }
        }
        try p.run()
        self.process = p

        // Open XPC channel and perform handshake
        let ch = try await XPCChannel.accept(socketPath: socketPath, nonce: nonce)
        self.channel = ch

        // Wait for ready message (30s timeout)
        try await withTimeout(30) {
            for await msg in ch.messages where msg.type == "ready" { return }
        }
        // Deliver credentials
        try await deliverCredentials(via: ch)
    }
}

## 7.4 Health Monitoring

Check | Interval | Failure Threshold | Action
Ping/pong | 10 seconds | 3 missed pongs (30s) | Mark unhealthy, trigger restart
process.isRunning | 5 seconds | process not running | Trigger restart immediately
Message queue depth | Continuous | > 500 items backlogged | Warn in UI; if > 2000, restart
Backend memory (RSS) | 60 seconds | > 2 GB | Show warning card in stream

## 7.5 Restart Policy

Condition | Restart? | Max Attempts | Backoff | User Notification
Clean exit (code 0) | No | — | None
Non-zero exit | Yes | 3 per 60s window | 1s, 5s, 15s | Error card after 1st
SIGKILL (OOM) | Yes | 2 total | 5s, 30s | Error card immediately
>3 crashes in 60s | No | — | Fatal error UI, manual restart required
Handshake timeout | Yes — re-launch | 3 | 5s each | Startup error card

# 8. Auto-Update (Sparkle)

## 8.1 Sparkle Configuration

Setting | Value | Notes
Framework | Sparkle 2.x | Integrated via Swift Package Manager
Signature scheme | EdDSA (ed25519) | Never DSA — deprecated and insecure
Appcast URL | https://updates.yousource.ai/crafted/appcast.xml | Served over HTTPS only
Update check interval | 4 hours | Configurable; background check on launch
Delta updates | Enabled if >= 2 consecutive versions | Reduces download size by ~60%
Minimum system version | Enforced in appcast per release | Prevents update to incompatible version

## 8.2 EdDSA Key Management

// One-time key generation (done once by build team, private key stored in secure vault)
// generate_keys tool ships with Sparkle:
$ ./bin/generate_keys
// Outputs:
//   Private key: (store in 1Password/Vault — never in source control)
//   Public key:  (embed in Info.plist as SUPublicEDKey)

// Info.plist entry:
<key>SUPublicEDKey</key>
<string>YOUR_BASE64_ED25519_PUBLIC_KEY</string>

// Signing a release:
$ ./bin/sign_update Crafted-1.1.0.zip
// Outputs: edSignature="..." length=12345678
// Place in appcast.xml sparkle:edSignature attribute

## 8.3 Appcast Schema

<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <title>Crafted Updates</title>
    <link>https://updates.yousource.ai/crafted/appcast.xml</link>
    <item>
      <title>Version 1.1.0</title>
      <sparkle:version>110</sparkle:version>
      <sparkle:shortVersionString>1.1.0</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>13.0</sparkle:minimumSystemVersion>
      <sparkle:releaseNotesLink>
          https://updates.yousource.ai/crafted/release-1.1.0.html
      </sparkle:releaseNotesLink>
      <pubDate>Wed, 19 Mar 2026 12:00:00 +0000</pubDate>
      <enclosure
          url="https://updates.yousource.ai/crafted/Crafted-1.1.0.zip"
          sparkle:edSignature="BASE64_ED_SIGNATURE_HERE"
          length="12345678"
          type="application/octet-stream"
      />
    </item>
  </channel>
</rss>

## 8.4 Required Entitlements for Sparkle

Entitlement | Value | Reason
com.apple.security.network.client | true | Required for update check and download
com.apple.security.files.user-selected.read-write | true | Required for writing downloaded update

ROLLBACK | If a bad update is distributed: immediately update appcast.xml to remove the bad version and add a hotfix. Users who received the bad update will be prompted to update again on next launch check.

# 9. Logging and Observability

## 9.1 os_log Subsystem and Category Definitions

// All Swift logging uses os_log with declared subsystem and category
// Never use print() or NSLog() in production code

import OSLog

extension Logger {
    static let auth    = Logger(subsystem:"ai.yousource.crafted", category:"auth")
    static let keychain = Logger(subsystem:"ai.yousource.crafted", category:"keychain")
    static let xpc     = Logger(subsystem:"ai.yousource.crafted", category:"xpc")
    static let process = Logger(subsystem:"ai.yousource.crafted", category:"process")
    static let settings = Logger(subsystem:"ai.yousource.crafted", category:"settings")
    static let docimport = Logger(subsystem:"ai.yousource.crafted", category:"docimport")
    static let ui      = Logger(subsystem:"ai.yousource.crafted", category:"ui")
    static let update  = Logger(subsystem:"ai.yousource.crafted", category:"update")
}

// Usage:
Logger.auth.info("Biometric authentication succeeded")
Logger.auth.error("Biometric failed: \(error.localizedDescription, privacy: .public)")

## 9.2 Privacy Annotations

All os_log calls must include privacy annotations. The default is .private — secrets and user data are automatically redacted in system logs. Only information safe for external viewing should be .public.

Data Category | Privacy Annotation | Examples
API keys, tokens, nonces | Never logged | If needed for debugging: log last 4 chars only with .public
File paths | privacy: .sensitive | Redacted by default, visible to user in Console.app
Engineer ID | privacy: .public | Safe to include in logs
Error codes, status codes | privacy: .public | errSecItemNotFound, HTTP 422
Build intent text | privacy: .private | Contains user's project description
Message types (XPC) | privacy: .public | type: "build_card", "gate_card"
Process IDs | privacy: .public | Safe

// CORRECT — sensitive data annotated
Logger.keychain.debug("Reading secret for account \(account, privacy: .public)")
Logger.auth.error("Auth failed: \(errorCode, privacy: .public) — \(description, privacy: .sensitive)")

// WRONG — never log secrets even at .debug level
Logger.keychain.debug("Secret value: \(secretValue)")  // PROHIBITED
Logger.xpc.debug("Credentials: \(credMessage)")        // PROHIBITED

## 9.3 Log Levels

Level | When to Use | Examples
.debug | Detailed flow, disabled in release builds by default | Message received, view appeared, timer fired
.info | Notable events, always captured | Auth succeeded, backend launched, document imported
.notice | Significant state changes | Session locked, build started, build complete
.error | Recoverable errors | Keychain read failed, backend pong missed, document parse error
.fault | Unrecoverable errors, programming mistakes | Invariant violated, unexpected nil, force unwrap triggered

## 9.4 dSYM and Crash Symbolication

// Build settings — required for crash symbolication
DEBUG_INFORMATION_FORMAT = dwarf-with-dsym
ENABLE_BITCODE = NO  // Not required for macOS

// Archive and export dSYMs:
// Xcode → Product → Archive → Export → Export dSYMs
// Or: find ~/Library/Developer/Xcode/Archives -name "*.dSYM"

// Store dSYMs alongside each release build in version control or artifact store
// dSYMs must match the UUID of the shipped binary exactly

// To symbolicate a crash report manually:
$ xcrun atos -arch arm64 -o Crafted.app.dSYM/Contents/Resources/DWARF/Crafted \
         -l 0xLOAD_ADDRESS 0xCRASH_ADDRESS

# 10. Menu Bar, Dock, and Notifications

## 10.1 Application Menu Structure

Crafted  (app menu)
  About Crafted
  ─────────────────
  Settings...        Cmd+,
  ─────────────────
  Services           ▶
  ─────────────────
  Hide Crafted   Cmd+H
  Hide Others        Opt+Cmd+H
  Show All
  ─────────────────
  Quit Crafted   Cmd+Q

File
  New Build          Cmd+N
  Open Documents...  Cmd+O
  ─────────────────
  Close Window       Cmd+W

Build
  Start Build        Cmd+Return  (when intent field focused)
  Pause Build        Cmd+P
  Cancel Build       Cmd+.
  ─────────────────
  Approve Gate       Space       (when gate focused)
  ─────────────────
  Show Build History Cmd+Shift+H

View
  Show Navigator     Cmd+1
  Show Context Panel Cmd+2
  ─────────────────
  Context: PRD       Cmd+Opt+1
  Context: PR        Cmd+Opt+2
  Context: Tests     Cmd+Opt+3
  Context: CI        Cmd+Opt+4
  Context: Cost      Cmd+Opt+5
  ─────────────────
  Enter Full Screen  Ctrl+Cmd+F

Window
  Minimize           Cmd+M
  Zoom
  ─────────────────
  Bring All to Front

Help
  Crafted Help
  Release Notes
  Report a Bug       → opens GitHub Issues

## 10.2 Keyboard Shortcut Conflict Audit

Shortcut | Our Use | System Use | Conflict?
Cmd+, | Settings | System Preferences shortcut in some apps | No — standard pattern for app settings
Cmd+N | New Build | New document | No — semantically equivalent
Cmd+O | Open Documents | Open file | No — semantically equivalent
Cmd+L | Lock App | (none in system) | No
Cmd+R | Retry | Reload in browsers | No — not a browser
Space | Approve gate | Scroll in many contexts | CAUTION — only active when gate card has focus; must not fire during text input
Cmd+Return | Start Build | (varies by app) | No — consistent with "submit" pattern
Cmd+. | Cancel Build | Cancel operations (system-wide) | No — semantically equivalent
Cmd+Shift+H | Build History | Hide all apps in some contexts | REVIEW — test on macOS 13 and 14

## 10.3 Dock Integration

// Dock right-click menu (NSApplicationDelegate.applicationDockMenu)
func applicationDockMenu(_ sender: NSApplication) -> NSMenu? {
    let menu = NSMenu()

    if let build = BuildStreamModel.shared.activeBuild {
        menu.addItem(withTitle: "Building: \(build.subsystem)",
                     action: nil, keyEquivalent: "")
        menu.addItem(.separator())
        menu.addItem(withTitle: "Cancel Build",
                     action: #selector(cancelBuild), keyEquivalent: "")
    } else {
        menu.addItem(withTitle: "New Build",
                     action: #selector(newBuild), keyEquivalent: "")
    }

    menu.addItem(.separator())
    menu.addItem(withTitle: "Lock", action: #selector(lock), keyEquivalent: "")
    return menu
}

// Dock badge: number of gates waiting for operator input
// Cleared when all gates are resolved or build completes
NSApp.dockTile.badgeLabel = pendingGates > 0 ? "\(pendingGates)" : nil

## 10.4 Notification Center Integration

Event | Notification Style | Sound | Action on Click
Gate waiting for input | Alert (persistent, user must dismiss) | Default | Bring app to front, scroll to gate
Build complete | Banner (auto-dismisses) | Ping | Open GitHub pulls URL in browser
CI failed | Alert (persistent) | Sosumi | Bring app to front, switch to CI tab
Backend crashed (non-recoverable) | Alert (persistent) | Basso | Bring app to front, show error
Auto-update available | Banner | None | Open Settings → update prompt

// Request notification permission at first build (not at launch)
UNUserNotificationCenter.current().requestAuthorization(
    options: [.alert, .sound, .badge]) { granted, error in ... }

// Post a notification:
let content = UNMutableNotificationContent()
content.title = "Gate Waiting"
content.body  = "PRD-003: Webhook Event Processor — review required"
content.sound = .default
content.userInfo = ["gate_id": gateId, "action": "show_gate"]

let request = UNNotificationRequest(identifier: gateId,
    content: content, trigger: nil)
UNUserNotificationCenter.current().add(request)

# 11. Document Import

## 11.1 UTType Declarations

// Info.plist — declare supported document types
<key>CFBundleDocumentTypes</key>
<array>
  <dict>
    <key>CFBundleTypeName</key>      <string>Markdown Document</string>
    <key>LSItemContentTypes</key>
    <array><string>net.daringfireball.markdown</string></array>
    <key>CFBundleTypeRole</key>      <string>Viewer</string>
  </dict>
  <dict>
    <key>CFBundleTypeName</key>      <string>Word Document</string>
    <key>LSItemContentTypes</key>
    <array><string>org.openxmlformats.wordprocessingml.document</string></array>
    <key>CFBundleTypeRole</key>      <string>Viewer</string>
  </dict>
  <dict>
    <key>CFBundleTypeName</key>      <string>PDF Document</string>
    <key>LSItemContentTypes</key>
    <array><string>com.adobe.pdf</string></array>
    <key>CFBundleTypeRole</key>      <string>Viewer</string>
  </dict>
  <dict>
    <key>CFBundleTypeName</key>      <string>Plain Text</string>
    <key>LSItemContentTypes</key>
    <array><string>public.plain-text</string></array>
    <key>CFBundleTypeRole</key>      <string>Viewer</string>
  </dict>
</array>

## 11.2 NSOpenPanel Configuration

func openDocumentPanel() async -> [URL] {
    let panel = NSOpenPanel()
    panel.allowsMultipleSelection = true
    panel.canChooseDirectories    = false
    panel.canChooseFiles          = true
    panel.allowedContentTypes     = [
        .init(filenameExtension: "md")!,
        .init(filenameExtension: "docx")!,
        .init(filenameExtension: "pdf")!,
        .init(filenameExtension: "txt")!,
    ]
    panel.title   = "Add TRD Documents"
    panel.message = "Select your technical specification documents"
    panel.prompt  = "Add"

    let result = await panel.begin()
    guard result == .OK else { return [] }
    return panel.urls
}

## 11.3 Import Validation Rules

Validation | Rule | Error Message
File size | Max 20 MB per file | File too large (max 20 MB). Consider splitting the document.
File count | Max 20 documents per project | Project already has 20 documents. Remove one before adding more.
Duplicate detection | SHA-256 hash of file contents; reject if hash already in project | This document is already in the project (exact duplicate).
Password-protected .docx | Attempt to open; catch decryption error | This document is password-protected. Remove protection before importing.
Corrupt/truncated file | Attempt to parse; catch any exception | Could not read this document. It may be corrupt or in an unsupported format.
Empty file | File size == 0 bytes | This document appears to be empty.
Binary disguised as text | Check for non-UTF-8 content in .txt/.md | This file does not appear to be a text document.

## 11.4 Drag-Drop Handling

// SwiftUI drop target for document area
DocumentStoreView()
    .onDrop(of: [.fileURL], isTargeted: $isDragTargeted) { providers in
        Task {
            var urls: [URL] = []
            for provider in providers {
                if let url = try? await provider.loadItem(
                    forTypeIdentifier: UTType.fileURL.identifier) as? URL {
                    urls.append(url)
                }
            }
            await DocImporter.shared.importDocuments(urls)
        }
        return true
    }

// Security-scoped resource access for Finder drag-drop:
url.startAccessingSecurityScopedResource()
defer { url.stopAccessingSecurityScopedResource() }

## 11.5 Document Preview

Document preview opens as a sheet. Format rendering:

Format | Rendering Approach
.md | AttributedString from Markdown, rendered in ScrollView with SF Mono for code blocks
.docx | Extract plain text via python-docx (subprocess call to bundled Python), display as AttributedString
.pdf | PDFKit PDFView embedded in NSViewRepresentable
.txt | Plain text in ScrollView with SF Mono

# 12. Multi-Instance Prevention

## 12.1 Single-Instance Enforcement

// In AppDelegate.applicationWillFinishLaunching:
let running = NSWorkspace.shared.runningApplications
    .filter { $0.bundleIdentifier == Bundle.main.bundleIdentifier
              && $0.processIdentifier != ProcessInfo.processInfo.processIdentifier }

if !running.isEmpty {
    // Bring existing instance to front
    running.first?.activate(options: .activateIgnoringOtherApps)
    // Terminate this new instance
    NSApp.terminate(nil)
}

Multi-instance prevention is enforced because:

Two instances share the same Application Support directory — concurrent writes to thread state JSON files corrupt build state

Two instances sharing the same XPC socket path cause connection conflicts

Two instances of the same engineer would confuse the build ledger

# 13. Accessibility

## 13.1 axIdentifier Naming Convention

// Convention: {module}-{component}-{role}-{context?}
// Set via .accessibilityIdentifier() modifier on all interactive elements

// Examples:
"auth-touchid-button"
"auth-passcode-button"
"settings-anthropic-key-field"
"settings-anthropic-key-test-button"
"settings-anthropic-key-reveal-button"
"navigator-project-row-{projectId}"
"stream-gate-card-{gateId}"
"stream-gate-yes-button-{gateId}"
"stream-gate-skip-button-{gateId}"
"stream-gate-stop-button-{gateId}"
"stream-gate-correction-field-{gateId}"
"context-tab-prd"
"context-tab-pr"
"context-tab-tests"
"context-tab-ci"
"context-tab-cost"
"statusbar-lock-button"
"build-intent-field"
"build-start-button"

## 13.2 Focus Management

// When a gate card appears in the stream:
// 1. Scroll stream to bottom (gate is always most recent card)
// 2. Move keyboard focus to first action button of gate card
// 3. VoiceOver announces: "Gate: {gateType}. {title}. {body}.
//    Press Space to approve, Tab to reach other options."

GateCard(model: gate)
    .onAppear {
        // Small delay to ensure scroll completes first
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            AccessibilityFocusState.focusedElement = "stream-gate-yes-button-\(gate.id)"
        }
    }
    .accessibilityLabel("Gate: \(gate.gateType). \(gate.title)")
    .accessibilityHint("Press Space to approve, or Tab for more options")

## 13.3 Color Contrast Requirements

Element | Foreground | Background | Contrast Ratio | WCAG Level
Body text | #F0F0F5 on #1A1A1F | — | 13.4:1 | AAA
Secondary text | #555566 on #1A1A1F | — | 5.1:1 | AA
Accent button text | #FFFFFF on #6B5ECD | — | 5.8:1 | AA
Table header text | #FFFFFF on #1A1A2E | — | 16.1:1 | AAA
Error text | #991B1B on #FEE2E2 | — | 6.3:1 | AA
Warning text | #92400E on #FEF3C7 | — | 6.1:1 | AA
Code text | #2D2D3A on #F4F4F8 | — | 9.8:1 | AAA

REQUIREMENT | All interactive elements must meet WCAG 2.1 AA minimum contrast ratio of 4.5:1 for normal text and 3:1 for large text and UI components. The above palette meets or exceeds AA across all text elements.

# 14. Privacy Manifest

## 14.1 PrivacyInfo.xcprivacy

Required by Apple for all distributed apps since 2024. Must be included in the app bundle at Contents/PrivacyInfo.xcprivacy.

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array><string>CA92.1</string></array>
            <!-- CA92.1: Access user defaults to read/write app settings -->
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryFileTimestamp</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array><string>C617.1</string></array>
            <!-- C617.1: Access file timestamps for document management -->
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryDiskSpace</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array><string>E174.1</string></array>
            <!-- E174.1: Check available space before writing build artifacts -->
        </dict>
    </array>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <!-- No data collected — all API keys and build content stay on device -->
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>

# 15. Settings Schema and Migration

## 15.1 Schema Versioning

// Current schema version: 1
// Stored in UserDefaults as "settings_schema_version" (Int)

// Migration handler — runs on every launch before app initializes
class SettingsMigrator {
    static func migrateIfNeeded() {
        let current = UserDefaults.standard.integer(forKey: "settings_schema_version")
        let target  = 1  // Increment with each schema change

        guard current < target else { return }

        if current < 1 {
            migrateToV1()
        }
        // Future: if current < 2 { migrateToV2() }

        UserDefaults.standard.set(target, forKey: "settings_schema_version")
    }

    private static func migrateToV1() {
        // v0 → v1: rename "notify_email" key to "display_name"
        // (notify_email was a hardcoded field in early builds)
        if let old = UserDefaults.standard.string(forKey: "notify_email"),
           UserDefaults.standard.string(forKey: "display_name") == nil {
            UserDefaults.standard.set(old, forKey: "display_name")
            UserDefaults.standard.removeObject(forKey: "notify_email")
        }
    }
}

## 15.2 Keychain Migration

If the bundle ID changes (e.g. from development ai.yousource.crafted.debug to production ai.yousource.crafted), Keychain items are not automatically migrated. The user must re-enter credentials. The onboarding flow handles this gracefully: if Keychain items for the current bundle ID are not found, the relevant onboarding step is re-shown.

# 16. Localization Infrastructure

## 16.1 String Extraction Setup

English-only in v1. However, all user-visible strings must use NSLocalizedString from the start. This enables localization in v2 without touching every callsite.

// ALL user-visible strings must use this pattern, even in v1:
Text("auth.biometric.reason",
     bundle: .main,
     comment: "Reason string shown in Touch ID prompt")

// Or for programmatic use:
let reason = NSLocalizedString("auth.biometric.reason",
    bundle: .main,
    comment: "Reason string shown in Touch ID prompt")

// String catalog: use Xcode String Catalogs (.xcstrings)
// Single Localizable.xcstrings file at the app target root
// Xcode auto-extracts strings during build if SWIFT_EMIT_LOC_STRINGS = YES

// File structure:
Crafted/
  └── Localizable.xcstrings   // Single source of truth
      // en: strings (v1)
      // Other locales: added in v2

# 17. Security Requirements

## 17.1 Hardened Runtime Entitlements (Complete)

Entitlement | Value | Justification
com.apple.security.network.client | true | Required for Sparkle update checks from Swift layer
com.apple.security.files.user-selected.read-write | true | Required for document import via NSOpenPanel and drag-drop
com.apple.security.files.downloads.read-only | true | Required for importing documents from Downloads folder
keychain-access-groups | $(AppIdentifierPrefix)ai.yousource.crafted | Required for Keychain access
com.apple.security.cs.allow-dyld-environment-variables | false | Not required — Python launched as subprocess, not dylib
com.apple.security.cs.disable-library-validation | false | Not required — explicitly denied
com.apple.security.cs.allow-unsigned-executable-memory | false | Not required — explicitly denied
com.apple.security.automation.apple-events | false | Not required — no AppleScript/Automator support

PYTHON SUBPROCESS NOTE | The Python backend inherits the app's network client entitlement through the child process relationship. The subprocess does NOT need a separate entitlement for outbound network calls. However, all binary extensions (.so files) must be individually signed or Hardened Runtime will block their import.

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

Metric | Target | Measurement
Cold launch to auth prompt | < 1.5 seconds | process start → LAContext.evaluatePolicy call
Auth success to backend ready | < 8 seconds | auth success → "ready" XPC message received
Auth success to UI interactive | < 10 seconds | auth success → MainView fully rendered (no spinner)
Gate card appear to focus | < 150 ms | gate_card received → keyboard focus on first button
XPC message latency (p95) | < 50 ms | send → receipt measured on loopback socket
Settings sheet open | < 200 ms | Cmd+, → sheet visible
Document import (1 MB .docx) | < 5 seconds | drop → "Embedded ✓" status shown
Memory — Swift process (idle) | < 150 MB RSS | Activity Monitor after 10 min idle
Memory — Python (idle) | < 500 MB RSS | Activity Monitor after 10 min idle
Memory — Python (active build) | < 2 GB RSS | Alert shown to user if exceeded
App bundle size (.zip) | < 120 MB | Python standalone + all deps + Swift binary
First launch (cold, no cache) | < 15 seconds | First run after download, including Python warmup

# 19. Testing Requirements

## 19.1 Unit Tests

Module | Coverage Target | Critical Test Cases
AuthKit / AuthManager | 100% | All SessionState transitions; timeout fires at correct interval; key cleared on lock; LAError cases mapped correctly
KeychainKit / KeychainManager | 100% | Write/read/delete round-trip; read fails when session != .active; exists() correct for missing item; no plaintext in UserDefaults
XPCBridge / XPCChannel | 90% | Handshake happy path; nonce mismatch closes connection; max message size enforced; reconnection after drop; malformed JSON discarded
ProcessManager / BackendProcess | 90% | Launch → ready sequence; crash restart with backoff; > 3 crashes/60s triggers fatal error; credential re-delivery on restart
Settings / SettingsStore | 100% | All validation rules; schema migration v0→v1; no secret written to UserDefaults; cost thresholds reject invalid combinations
DocImport | 85% | Happy path all four file types; duplicate detection; file size rejection; password-protected .docx error; corrupt file error
SettingsMigrator | 100% | v0→v1 migration; already-migrated is no-op; missing old key is no-op

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

codesign --verify --deep --strict Crafted.app — must exit 0

xcrun notarytool submit Crafted.app.zip --wait — must succeed

xcrun stapler validate Crafted.app — must confirm stapled

spctl --assess --type exec Crafted.app — must show: accepted

All .so files in site-packages signed: codesign -dv site-packages/**/*.so

PrivacyInfo.xcprivacy present: ls Crafted.app/Contents/PrivacyInfo.xcprivacy

Sparkle SUPublicEDKey present in Info.plist

VERSION file matches CFBundleShortVersionString

# 20. Build System Requirements

Requirement | Spec
Xcode version | 15.0 or later
macOS build machine | 13.0 or later (Ventura+)
Swift version | 5.9+
Python version (bundled) | 3.12.x — exact patch version pinned in Makefile
Architecture | Universal2 (arm64 + x86_64)
Code signing identity | Developer ID Application: YouSource, Inc. (TEAMID)
Notarization | Required for all external builds; xcrun notarytool
dSYMs | Generated and archived for every release build
Sparkle signing | EdDSA signature generated and placed in appcast.xml
Python deps | Built via cibuildwheel for universal2; all .so files signed

# 21. Out of Scope

Feature | Reason Excluded | Target
App Store distribution | Requires full sandbox entitlement audit and review | v2
iOS / iPadOS | Different interaction model | TBD
Windows / Linux | No LocalAuthentication or Keychain equivalent | Never
Light mode | Dark-mode first per TRD-8 | v2
iCloud settings sync | Security risk — Keychain items must not reach iCloud | Never
Multiple GitHub accounts per install | Single account in v1 | v2
GitHub Enterprise | Same API, different base URL | v2
Automatic merge without operator approval | Core product principle | Never
Analytics / telemetry | Opt-in only; not in v1 scope | v1.1 if approved
Localization (non-English) | Infrastructure in place; strings in v2 | v2

# 22. Open Questions

ID | Question | Owner | Needed By
OQ-01 | XPC service (formal Apple XPC) vs Unix domain socket. XPC service gives stronger isolation and OS-managed lifecycle. Tradeoff: more complex setup, requires different entitlements. Recommendation: Unix socket for v1, migrate to XPC service in v2 if isolation issues arise. | Engineering | Sprint 1
OQ-02 | Python framework (~80 MB) vs standalone binary (~15 MB). Framework gives cleaner dylib management; standalone is simpler to sign and bundle. Recommendation: standalone, confirmed working with Hardened Runtime on M1 and Intel. | Engineering | Sprint 1
OQ-03 | GitHub App client_id and OAuth callback URI. Requires GitHub App registration under YouSource org. Who registers it? | Product | Before GitHub auth sprint
OQ-04 | Sparkle private key storage. EdDSA private key must be secured (1Password, AWS Secrets Manager, or CI secret). Procedure not yet defined. | Infra | Before first external release
OQ-05 | Crash reporting opt-in. If approved: Sentry or custom crash aggregation. Must confirm no secrets in crash reports via automated test before enabling. | Product | v1.1 planning
OQ-06 | Menu bar status item (persistent icon in macOS menu bar showing build status). Useful for long builds. Adds complexity to app lifecycle. Defer to v1.1? | Product | Sprint 2

# Appendix A: Error Type Reference

enum AuthError: Error {
    case biometricUnavailable(String)
    case cancelled
    case lockedOut
    case notEnrolled
    case failed(String)
    case sessionNotActive
    case keyGenFailed
}

enum KeychainError: Error {
    case write(OSStatus)
    case read(OSStatus)
    case delete(OSStatus)
    case notFound
}

enum XPCError: Error {
    case connectionFailed(String)
    case handshakeFailed
    case nonceMismatch
    case messageTooLarge(Int)
    case malformedJSON
    case sessionMismatch
    case timeout
}

enum ProcessError: Error {
    case launchFailed(String)
    case readyTimeout
    case maxRestartsExceeded
    case credentialDeliveryFailed
}

enum DocImportError: Error {
    case tooLarge(Int)       // bytes
    case duplicate(String)   // existing document name
    case passwordProtected
    case corrupt
    case empty
    case projectFull         // max 20 docs
}

# Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial draft
1.1 | 2026-03-19 | YouSource.ai | Added: Swift module architecture, SwiftUI view hierarchy, state management specs, XPC peer auth, Sparkle EdDSA, menu bar spec, document import UTTypes, sandboxing decision, os_log definitions, multi-instance prevention, axIdentifier convention, color contrast, privacy manifest, settings migration, localization infrastructure, build validation checklist