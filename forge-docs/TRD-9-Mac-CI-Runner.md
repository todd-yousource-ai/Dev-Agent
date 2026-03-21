# TRD-9-Mac-CI-Runner

_Source: `TRD-9-Mac-CI-Runner.docx` — extracted 2026-03-21 21:32 UTC_

---

TRD-9

Mac CI Runner Infrastructure

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-9: Mac CI Runner Infrastructure
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Hardware | Developer MacBook (existing machine — no additional hardware required)
Depends on | TRD-1 (App Shell — Xcode project being built), TRD-5 (GitHub — webhook for CI results)
Required by | TRD-1 and TRD-8 implementation — agent cannot validate Swift without this
Setup time | One afternoon (3–5 hours including certificate setup)
Ongoing cost | Electricity only — GitHub self-hosted runners are free

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Mac CI Runner Infrastructure — a self-hosted GitHub Actions runner on the developer's MacBook that gives the Consensus Dev Agent a real macOS build environment.

Without this infrastructure, the agent can write Swift but cannot validate it. With it, the agent operates against a real Xcode toolchain on real Apple hardware — the same machine that will eventually ship the product. The loop becomes: agent PRs Swift, Mac runner builds and tests it, CI result returns to agent via webhook, agent fixes and re-PRs. The same autonomous loop that works for Python now works for Swift.

SCOPE | TRD-9 specifies the CI runner setup, the macOS GitHub Actions workflow, code signing infrastructure, and monitoring. It does not specify what the agent builds — that is TRD-1 through TRD-8. It specifies the build environment those TRDs are validated in.

This TRD owns:

Self-hosted runner installation, configuration, and auto-start

Xcode version pinning and toolchain setup

Developer ID code signing — certificate, Keychain unlock in CI

forge-ci-macos.yml — the complete macOS GitHub Actions workflow

Build job — xcodebuild, universal2, DerivedData caching

Test job — XCTest targets, parallel execution, xcresult parsing

XPC integration test — the critical Swift-Python bridge test

Python bundling in CI — pre-built binaries, .so signing

Notarization job — App Store Connect API, staple, .dmg creation

Artifact management — PR vs release artifact strategy

Runner security — fork PR protection, secret hygiene, Keychain

Monitoring — runner offline detection, certificate expiry, disk

forge-ci.yml update — job routing between Ubuntu and Mac runners

# 2. Design Decisions

Decision | Choice | Rationale
Hardware | Developer's existing MacBook | No additional cost. The MacBook is already the development machine. Running it as a CI runner is additive, not disruptive.
Runner isolation | Same user account as developer | Simpler setup. Acceptable for a private repository with no untrusted contributors. If external contributors are added later, migrate to a dedicated account.
Python CI | Stays on ubuntu-latest | Ubuntu runners are faster, cheaper (GitHub-hosted = free for public repos), and sufficient for Python. Mac time is reserved for Swift jobs only.
Separate workflow file | forge-ci-macos.yml, not merged into forge-ci.yml | Separate files for separate runners prevents a Mac runner offline state from blocking Python CI. Each workflow is independently required.
Signing approach | Developer ID Application (not App Store) | Matches the distribution model: direct download, not App Store. No sandbox review required. Developer ID is what Gatekeeper validates on install.
Notarization trigger | Tags and main branch only, not every PR | Notarization takes 2–10 minutes and costs Apple ID API calls. PRs get a signed-but-not-notarized .app for inspection. Releases get the full notarized .dmg.
DerivedData caching | actions/cache keyed on project file hash | DerivedData is ~500MB and takes 5+ minutes to rebuild from scratch. Caching reduces cold build to ~90 seconds on re-runs with only Swift changes.
Notarization credentials | App Store Connect API key | Avoids 2FA complications with Apple ID + app-specific password. API key is a JSON file stored as a GitHub secret.

# 3. Runner Installation and Configuration

## 3.1 Installation Procedure

# Step 1: Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Step 2: Download runner (get current URL from GitHub)
# GitHub → repo → Settings → Actions → Runners → New self-hosted runner
# Select: macOS, ARM64 (Apple Silicon) or x64 (Intel)
curl -o actions-runner-osx-arm64-2.x.x.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.x.x/\
  actions-runner-osx-arm64-2.x.x.tar.gz
tar xzf ./actions-runner-osx-arm64-2.x.x.tar.gz

# Step 3: Configure (token from GitHub Settings page)
./config.sh \
  --url https://github.com/{owner}/{repo} \
  --token {REGISTRATION_TOKEN} \
  --name "macbook-forge-runner" \
  --labels "self-hosted,macos,xcode,arm64" \
  --work "_work" \
  --replace

# Step 4: Install as LaunchAgent (auto-starts on login)
./svc.sh install
./svc.sh start

# Verify running:
./svc.sh status
# Should show: active (running)

## 3.2 Runner Labels

Label | Purpose | Used in workflow as
self-hosted | Identifies as self-hosted (not GitHub-hosted) | runs-on: [self-hosted, macos]
macos | Distinguishes from Linux self-hosted runners | Required — prevents job routing to Ubuntu runners
xcode | Confirms Xcode is installed | Documentation only — not programmatically checked
arm64 | Distinguishes Apple Silicon from Intel | Useful if multiple runners added later

## 3.3 Environment Variables Available to Jobs

# Set in ~/.zshenv so they are available to the runner LaunchAgent
# (LaunchAgent does not source .zshrc or .bash_profile)

export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export LANG="en_US.UTF-8"

# After editing ~/.zshenv: restart the runner service
~/actions-runner/svc.sh stop
~/actions-runner/svc.sh start

# Verify the runner picks up the environment:
# Trigger a test workflow that runs: echo $DEVELOPER_DIR

## 3.4 GitHub Secrets Required

Secret Name | Value | Used For
APPLE_TEAM_ID | 10-character Team ID from developer.apple.com | CODE_SIGN_TEAM in xcodebuild
APPLE_SIGNING_IDENTITY | "Developer ID Application: {Name} ({TeamID})" | codesign -s argument
ASC_API_KEY_ID | Key ID from App Store Connect API key | xcrun notarytool --key-id
ASC_API_KEY_ISSUER | Issuer ID from App Store Connect | xcrun notarytool --issuer-id
ASC_API_KEY_BASE64 | Base64-encoded .p8 private key file content | Decoded and written to temp file in CI
ANTHROPIC_API_KEY_TEST | Test API key for integration tests | ConsensusEngine integration tests only
OPENAI_API_KEY_TEST | Test API key for integration tests | ConsensusEngine integration tests only

SECURITY | Never print secrets in workflow logs. Use ${{ secrets.SECRET_NAME }} syntax — GitHub automatically masks these values in logs. Never store secrets in the repository or in the runner environment permanently.

# 4. Xcode and Toolchain Setup

## 4.1 Xcode Version Pinning

# Pin Xcode version to prevent unexpected breaking changes.
# Xcode is NOT auto-updated — update manually and test before updating pin.

# Current pin: Xcode 15.x (required for Swift 5.9+ and macOS 13 SDK)
# Minimum: Xcode 15.0

# Verify active Xcode version in workflow:
- name: Verify Xcode version
  run: |
    xcode-select -p
    xcodebuild -version
    swift --version
  # Expected output:
  # /Applications/Xcode.app/Contents/Developer
  # Xcode 15.x
  # Build version 15Axxxx

# If multiple Xcode versions installed, set active:
sudo xcode-select -s /Applications/Xcode_15.x.app/Contents/Developer

## 4.2 Required Tools

Tool | Install Method | Purpose | Version Requirement
Xcode | Mac App Store or developer.apple.com | Build, test, sign | 15.0 minimum
Command Line Tools | xcode-select --install | Included with Xcode | Matches Xcode version
xcbeautify | brew install xcbeautify | Human-readable xcodebuild output in logs | Latest
create-dmg | brew install create-dmg | Build .dmg installer for releases | Latest
Python 3.12 | python.org standalone binary | Bundle into .app for XPC integration test | 3.12.x exactly
pip-audit | pip install pip-audit | Dependency vulnerability scanning | Latest

# Install Homebrew tools (one-time, on the MacBook):
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install xcbeautify create-dmg

# Verify all tools accessible from runner:
# Trigger test workflow: which xcbeautify create-dmg

# 5. Code Signing Infrastructure

## 5.1 Certificate Setup

# Developer ID Application certificate must be in the login Keychain.
# Obtain from: developer.apple.com → Certificates → Developer ID Application

# Verify certificate is present and trusted:
security find-identity -v -p codesigning
# Expected output includes:
# "Developer ID Application: YouSource.ai ({TEAM_ID})"

# Certificate validity:
#   Developer ID certificates are valid for 5 years
#   Set a calendar reminder 60 days before expiry
#   See Appendix C for the automated check script

# If certificate is missing or expired:
#   1. Revoke old certificate at developer.apple.com
#   2. Create new Developer ID Application certificate
#   3. Download and double-click to install
#   4. Update APPLE_SIGNING_IDENTITY secret in GitHub

## 5.2 Keychain Unlock in CI

# CI jobs run as the current user but the login Keychain may be locked.
# Unlock it before signing steps.

- name: Unlock Keychain
  run: |
    security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
    # Set keychain lock timeout to 3600s (covers the CI job duration)
    security set-keychain-settings -lut 3600 ~/Library/Keychains/login.keychain-db
  env:
    KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}

# KEYCHAIN_PASSWORD is the macOS login password.
# Store as a GitHub secret. Never hardcode.

# Re-lock after signing to minimize exposure window:
- name: Lock Keychain
  if: always()  # runs even if build fails
  run: security lock-keychain ~/Library/Keychains/login.keychain-db

## 5.3 Entitlements File

# ForgeAgent.entitlements — required for code signing
# Location: ForgeAgent/ForgeAgent.entitlements in Xcode project

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-only</key>
    <true/>
    <key>keychain-access-groups</key>
    <array>
        <string>$(AppIdentifierPrefix)ai.yousource.forgeagent</string>
    </array>
</dict>
</plist>

# Hardened Runtime is enabled via Xcode build settings:
# ENABLE_HARDENED_RUNTIME = YES

# 6. forge-ci-macos.yml — Workflow Overview

## 6.1 Trigger Specification

name: Forge CI — macOS

on:
  push:
    branches:
      - main
      - "forge-agent/build/**"
    paths:
      - "ForgeAgent/**"        # Swift source
      - "ForgeAgentTests/**"   # Swift tests
      - "*.xcodeproj/**"       # Xcode project
      - "Package.swift"
      - ".github/workflows/forge-ci-macos.yml"
    paths-ignore:
      - "prds/**"
      - "forge-docs/**"
      - "**.md"
      - "**.docx"
      - "src/**"               # Python source — handled by forge-ci.yml
      - "tests/**"             # Python tests
  pull_request:
    branches:
      - main
    paths:
      - "ForgeAgent/**"
      - "ForgeAgentTests/**"
      - "*.xcodeproj/**"
      - "Package.swift"

# Only runs when Swift files change.
# Python-only PRs never touch the Mac runner.

## 6.2 Job Dependency Graph

Jobs and their dependencies:

setup ──────────────────────────────────────────────────────────┐
  (verify Xcode, tools, certificate)                            │
         │                                                       │
         ▼                                                       │
build ──────────────────────────────────────────────────────────┤
  (xcodebuild Release, universal2)                              │
  needs: [setup]                                                │
         │                                                       │
         ├──────────────────────┐                               │
         ▼                      ▼                               │
unit-test              xpc-integration-test                     │
  (XCTest suite)         (Swift-Python bridge)                  │
  needs: [build]         needs: [build]                        │
         │                      │                               │
         └──────────┬───────────┘                               │
                    ▼                                           │
                  sign                                          │
               (codesign .app)                                  │
               needs: [unit-test, xpc-integration-test]         │
                    │                                           │
                    ▼                                           │
                 artifact                                        │
             (upload signed .app)                               │
             needs: [sign]                                      │
                    │                                           │
         (on tag or main only)                                  │
                    ▼                                           │
               notarize                                         │
           (notarytool + staple + dmg)                         │
           needs: [artifact]                                    │
                                                               ─┘

# All jobs run on: [self-hosted, macos]

# 7. Build Job

## 7.1 DerivedData Caching

- name: Cache DerivedData
  uses: actions/cache@v4
  with:
    path: ~/Library/Developer/Xcode/DerivedData
    key: ${{ runner.os }}-deriveddata-${{ hashFiles('**/*.xcodeproj/project.pbxproj', 'Package.swift') }}
    restore-keys: |
      ${{ runner.os }}-deriveddata-

# Cache hit: builds in ~90 seconds (incremental)
# Cache miss: builds in ~5–8 minutes (full)
# Cache size: ~500MB for a Swift app of this complexity
# Cache eviction: GitHub evicts after 7 days of no use

## 7.2 xcodebuild Command

- name: Build
  run: |
    set -o pipefail
    xcodebuild \
      -project ForgeAgent.xcodeproj \
      -scheme ForgeAgent \
      -configuration Release \
      -destination "generic/platform=macOS" \
      ONLY_ACTIVE_ARCH=NO \
      ARCHS="arm64 x86_64" \
      BUILD_DIR="$GITHUB_WORKSPACE/build" \
      ENABLE_HARDENED_RUNTIME=YES \
      CODE_SIGN_STYLE=Manual \
      CODE_SIGN_IDENTITY="${{ secrets.APPLE_SIGNING_IDENTITY }}" \
      CODE_SIGN_TEAM="${{ secrets.APPLE_TEAM_ID }}" \
      build \
    | xcbeautify --renderer github-actions

  env:
    NSUnbufferedIO: YES

# ONLY_ACTIVE_ARCH=NO + ARCHS="arm64 x86_64" = universal2 binary
# BUILD_DIR: explicit path so artifact steps know where to find output
# xcbeautify --renderer github-actions: folds build output, highlights errors
# set -o pipefail: ensures xcbeautify exit code does not mask xcodebuild failure

# Exit codes:
# 0: success
# 65: build failed (compilation errors, linker errors)
# 70: internal build system error (usually Xcode corruption — re-run)
# Any other: unexpected — check raw xcodebuild output

## 7.3 Build Output Location

# After build, the .app is at:
# $GITHUB_WORKSPACE/build/Release/ForgeAgent.app

# Verify build output exists:
- name: Verify build output
  run: |
    if [ ! -d "$GITHUB_WORKSPACE/build/Release/ForgeAgent.app" ]; then
      echo "ERROR: ForgeAgent.app not found after build"
      exit 1
    fi
    echo "Build output: $(du -sh build/Release/ForgeAgent.app | cut -f1)"
    # Print bundle structure for debugging
    find build/Release/ForgeAgent.app -type f | head -30

# 8. Test Job

## 8.1 XCTest Targets

Test Target | Module Tested | Critical Tests | Est. Duration
AuthKitTests | AuthKit (TRD-1 S4) | All SessionState transitions; timeout fires; key cleared on lock; LAError mapping (mock LAContext) | 30s
KeychainKitTests | KeychainKit (TRD-1 S5) | Write/read/delete round-trip; read fails when session inactive; exists() on missing item | 20s
XPCBridgeTests | XPCBridge (TRD-1 S6) | Handshake message schema; nonce validation; max message size rejection; malformed JSON discarded | 30s
ProcessManagerTests | ProcessManager (TRD-1 S7) | Launch sequence mock; crash detection; restart with backoff; credential re-delivery sequence | 40s
SettingsTests | Settings (TRD-1 S8) | All validation rules; schema migration; no secret in UserDefaults assertion | 20s
DocImportTests | DocImport (TRD-1 S11) | File size rejection; duplicate hash detection; corrupt file error; UTType matching | 20s

## 8.2 xcodebuild test Command

- name: Run tests
  run: |
    set -o pipefail
    xcodebuild \
      -project ForgeAgent.xcodeproj \
      -scheme ForgeAgent \
      -destination "platform=macOS,arch=arm64" \
      -resultBundlePath "$GITHUB_WORKSPACE/test-results/results.xcresult" \
      -parallel-testing-enabled YES \
      -maximum-parallel-testing-worker-count 4 \
      test \
    | xcbeautify --renderer github-actions

- name: Upload test results
  if: always()   # Upload even on failure
  uses: actions/upload-artifact@v4
  with:
    name: test-results-${{ github.run_id }}
    path: test-results/results.xcresult
    retention-days: 7

# xcresult bundle contains:
#   Per-test pass/fail with timing
#   Failure messages with file/line references
#   Code coverage report (if enabled)
#   Crash logs

## 8.3 Touch ID Mocking in Tests

// AuthKitTests cannot trigger real Touch ID in CI.
// LAContext is injected as a dependency so tests can mock it.

// Production code:
actor AuthManager {
    private let contextProvider: () -> LAContext
    init(contextProvider: @escaping () -> LAContext = { LAContext() }) {
        self.contextProvider = contextProvider
    }
    func authenticate(reason: String) async throws -> Bool {
        let context = contextProvider()
        // ... LAContext.evaluatePolicy()
    }
}

// Test code:
class MockLAContext: LAContext {
    var shouldSucceed = true
    var errorToThrow: LAError? = nil
    override func evaluatePolicy(_ policy: LAPolicy,
                                 localizedReason: String) async throws -> Bool {
        if let error = errorToThrow { throw error }
        return shouldSucceed
    }
}

// Test:
func testAuthSucceeds() async throws {
    let mock = MockLAContext()
    mock.shouldSucceed = true
    let auth = AuthManager(contextProvider: { mock })
    let result = try await auth.authenticate(reason: "test")
    XCTAssertTrue(result)
}

# 9. XPC Integration Test

## 9.1 Why This Test Matters

The XPC integration test is the single most valuable test in the entire CI suite. It verifies that the Swift shell and the Python backend can actually communicate — that the socket is established, the handshake completes, credentials are delivered, and a ping-pong round-trip succeeds. If this test is green, the two halves of the app are talking to each other on real Apple hardware.

## 9.2 Test Structure

// XPCIntegrationTests/XPCIntegrationTest.swift
// This test is in a separate target so it can be run independently
// and excluded from unit test runs if the Python bundle is not present.

class XPCIntegrationTest: XCTestCase {

    var backendProcess: Process?
    var channel: XPCChannelClient?

    override func setUp() async throws {
        // Locate bundled Python in the built .app
        let appPath = ProcessInfo.processInfo.environment["APP_PATH"]
            ?? "\(FileManager.default.currentDirectoryPath)/build/Release/ForgeAgent.app"
        let pythonPath = "\(appPath)/Contents/Resources/python3.12"
        let mainPath   = "\(appPath)/Contents/Resources/agent/main.py"

        guard FileManager.default.fileExists(atPath: pythonPath) else {
            throw XCTSkip("Python binary not present — run build job first")
        }

        // Generate per-test socket path and nonce
        let socketPath = NSTemporaryDirectory() + "xpc-test-\(UUID().uuidString).sock"
        let nonce      = UUID().uuidString

        // Start Python backend
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments     = [mainPath]
        process.environment   = [
            "FORGE_XPC_SOCKET": socketPath,
            "FORGE_XPC_NONCE":  nonce,
            "FORGE_WORKSPACE":  NSTemporaryDirectory() + "forge-test",
            "FORGE_LOG_DIR":    NSTemporaryDirectory() + "forge-test-logs",
        ]
        try process.run()
        self.backendProcess = process

        // Connect XPC channel
        let ch = try await XPCChannelClient.connect(
            socketPath: socketPath,
            nonce: nonce,
            timeout: 30
        )
        self.channel = ch
    }

    override func tearDown() async throws {
        backendProcess?.terminate()
        backendProcess?.waitUntilExit()
        channel?.disconnect()
    }

    func testHandshakeCompletes() async throws {
        // Handshake is completed in setUp — if we reach here, it worked
        XCTAssertNotNil(channel)
    }

    func testPingPong() async throws {
        let channel = try XCTUnwrap(self.channel)
        let pong = try await channel.send(type: "ping", payload: [:])
        XCTAssertEqual(pong["type"] as? String, "pong")
    }

    func testCredentialDelivery() async throws {
        let channel = try XCTUnwrap(self.channel)
        // Deliver test credentials
        let response = try await channel.send(type: "credentials", payload: [
            "anthropic_api_key": "test-key-anthropic",
            "openai_api_key":    "test-key-openai",
            "github_token":      "test-token",
            "engineer_id":       "ci-test-engineer",
        ])
        // Backend should acknowledge credentials
        XCTAssertEqual(response["type"] as? String, "credentials_ack")
    }

    func testBackendReportsVersion() async throws {
        let channel = try XCTUnwrap(self.channel)
        // The ready message includes version
        // (received during handshake — check stored on channel)
        XCTAssertFalse(channel.backendVersion.isEmpty)
    }
}

## 9.3 Running the Integration Test in CI

- name: Run XPC integration test
  run: |
    set -o pipefail
    xcodebuild \
      -project ForgeAgent.xcodeproj \
      -scheme XPCIntegrationTests \
      -destination "platform=macOS,arch=arm64" \
      test \
    | xcbeautify --renderer github-actions
  env:
    APP_PATH: ${{ github.workspace }}/build/Release/ForgeAgent.app
  timeout-minutes: 5

# Timeout: 5 minutes.
# If the Python backend fails to start in 30 seconds,
# the setUp() throws and the test fails with a clear message.

# This test requires the build job to have completed successfully.
# The Python .app must be present at APP_PATH.

# 10. Python Bundling in CI

## 10.1 Bundle Strategy

The XPC integration test requires the bundled Python binary to be present inside the built .app. The Python standalone binary and all site-packages must be built for the correct architecture and signed before the integration test runs.

Approach | Cold Build Time | Cache Hit Time | Maintenance
Pre-built binary in repo (git LFS) | N/A (always cached) | ~10s download | Update manually when Python version changes
Download from python.org per run | ~3 min download + extract | N/A — no cache | Zero maintenance — always fresh
Build from source | ~20 min | N/A — impractical to cache | High — requires build dependencies
GitHub Actions cache (recommended) | ~8 min on miss | ~45s restore | Low — cache invalidates on requirements change

RECOMMENDATION | Use GitHub Actions cache keyed on Python version + requirements.txt hash. Cache hit takes 45 seconds. Cache miss (first run or dependency change) takes 8 minutes. This is the best balance of speed and maintenance.

## 10.2 Python Caching Steps

- name: Cache Python bundle
  id: cache-python
  uses: actions/cache@v4
  with:
    path: forge-python-bundle
    key: python-bundle-${{ runner.os }}-${{ runner.arch }}-\
         ${{ hashFiles('requirements.txt') }}-3.12

- name: Build Python bundle (cache miss only)
  if: steps.cache-python.outputs.cache-hit != 'true'
  run: |
    # Download Python 3.12 standalone from python.org
    PYTHON_VERSION=3.12.8
    ARCH=$(uname -m)   # arm64 or x86_64
    curl -Lo python.pkg \
      "https://www.python.org/ftp/python/${PYTHON_VERSION}/\
       python-${PYTHON_VERSION}-macos11.pkg"
    sudo installer -pkg python.pkg -target /
    
    # Create standalone binary (not framework)
    PYTHON=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
    mkdir -p forge-python-bundle/site-packages

    # Install dependencies to bundle
    $PYTHON -m pip install \
      --target forge-python-bundle/site-packages \
      -r requirements.txt \
      --platform macosx_11_0_universal2 \
      --only-binary=:all:
    
    # Copy Python binary
    cp $PYTHON forge-python-bundle/python3.12

- name: Sign Python bundle
  run: |
    # Sign Python binary
    codesign --force --deep --sign "${{ secrets.APPLE_SIGNING_IDENTITY }}" \
      forge-python-bundle/python3.12
    
    # Sign all .so binary extensions
    find forge-python-bundle/site-packages -name "*.so" -exec \
      codesign --force --sign "${{ secrets.APPLE_SIGNING_IDENTITY }}" {} \;

    # Verify signing
    codesign -dv forge-python-bundle/python3.12

- name: Inject Python bundle into .app
  run: |
    RESOURCES="build/Release/ForgeAgent.app/Contents/Resources"
    cp forge-python-bundle/python3.12 "$RESOURCES/"
    cp -r forge-python-bundle/site-packages "$RESOURCES/"

# 11. Notarization Job

## 11.1 Trigger Conditions

# Notarization only runs on:
#   1. Pushes to main branch
#   2. Tagged releases (v*.*.* pattern)

notarize:
  needs: [artifact]
  if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
  runs-on: [self-hosted, macos]

## 11.2 Notarization Steps

- name: Set up App Store Connect API key
  run: |
    mkdir -p ~/.appstoreconnect/private_keys
    echo "${{ secrets.ASC_API_KEY_BASE64 }}" | base64 --decode \
      > ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8

- name: Download signed app artifact
  uses: actions/download-artifact@v4
  with:
    name: forge-agent-signed-${{ github.run_id }}

- name: Notarize
  run: |
    # Zip the .app for submission
    ditto -c -k --keepParent ForgeAgent.app ForgeAgent.zip

    # Submit to Apple Notary Service
    xcrun notarytool submit ForgeAgent.zip \
      --key ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8 \
      --key-id ${{ secrets.ASC_API_KEY_ID }} \
      --issuer ${{ secrets.ASC_API_KEY_ISSUER }} \
      --wait \
      --timeout 15m

- name: Staple
  run: xcrun stapler staple ForgeAgent.app

- name: Verify notarization
  run: |
    xcrun stapler validate ForgeAgent.app
    spctl --assess --type exec ForgeAgent.app
    echo "Notarization verified"

- name: Create .dmg
  run: |
    create-dmg \
      --volname "Forge Agent" \
      --window-pos 200 120 \
      --window-size 800 400 \
      --icon-size 100 \
      --icon "ForgeAgent.app" 200 190 \
      --hide-extension "ForgeAgent.app" \
      --app-drop-link 600 185 \
      "ForgeAgent-${{ github.ref_name }}.dmg" \
      "ForgeAgent.app"

- name: Notarize .dmg
  run: |
    xcrun notarytool submit "ForgeAgent-${{ github.ref_name }}.dmg" \
      --key ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8 \
      --key-id ${{ secrets.ASC_API_KEY_ID }} \
      --issuer ${{ secrets.ASC_API_KEY_ISSUER }} \
      --wait --timeout 15m
    xcrun stapler staple "ForgeAgent-${{ github.ref_name }}.dmg"

- name: Cleanup API key
  if: always()
  run: rm -f ~/.appstoreconnect/private_keys/AuthKey_*.p8

# 12. Artifact Management

Artifact | Trigger | Contents | Retention | Purpose
forge-agent-unsigned-{run_id} | Every PR and push | ForgeAgent.app (unsigned) | 7 days | Download and run locally to inspect UI before merge
forge-agent-signed-{run_id} | Every push to main and forge-agent/* branches | ForgeAgent.app (signed, not notarized) | 14 days | Working app for internal testing without full notarization wait
test-results-{run_id} | Every test run (pass or fail) | results.xcresult bundle | 7 days | Debug test failures — open in Xcode for full details
forge-agent-{version}.dmg | Tags (v*.*.*) | Notarized .dmg | 90 days | Distribution artifact — ready to send to users
ForgeAgent.app.dSYM-{version} | Tags (v*.*.*) | Debug symbols for crash symbolication | 90 days | Required to symbolicate crash reports from that version

## 12.1 Artifact Upload Steps

# Upload unsigned .app (every run)
- name: Upload unsigned app
  uses: actions/upload-artifact@v4
  with:
    name: forge-agent-unsigned-${{ github.run_id }}
    path: build/Release/ForgeAgent.app
    retention-days: 7

# Upload signed .app (after signing job)
- name: Upload signed app
  uses: actions/upload-artifact@v4
  with:
    name: forge-agent-signed-${{ github.run_id }}
    path: build/Release/ForgeAgent.app
    retention-days: 14

# Upload dSYMs (release tags only)
- name: Upload dSYMs
  if: startsWith(github.ref, 'refs/tags/v')
  uses: actions/upload-artifact@v4
  with:
    name: ForgeAgent.app.dSYM-${{ github.ref_name }}
    path: build/Release/ForgeAgent.app.dSYM
    retention-days: 90

# 13. Runner Security and Isolation

## 13.1 Fork PR Protection

# CRITICAL: Self-hosted runners executing fork PRs is a security risk.
# A malicious fork PR could exfiltrate the Developer ID certificate,
# the ASC API key, or the KEYCHAIN_PASSWORD secret.

# Required setting in GitHub:
# Repository → Settings → Actions → General
# → "Fork pull request workflows from outside collaborators"
# → Select: "Require approval for all outside collaborators"

# This means: ANY PR from a fork requires manual approval before CI runs.
# This is the correct setting for a private repository.

# For this project: the repository is private.
# Only invited collaborators can open PRs.
# Fork protection is defense-in-depth, not the primary control.

## 13.2 Secret Hygiene Rules

Rule | Implementation
Never print secrets | GitHub auto-masks ${{ secrets.* }} in logs. Never construct a secret from parts in shell (circumvents masking).
No secrets in artifacts | Uploaded .app must not contain any embedded credentials. The Python backend receives credentials at runtime via XPC, not at build time.
Keychain re-lock after signing | - name: Lock Keychain with if: always() runs even on failure. Certificate window is minimized.
ASC key cleanup | API key .p8 file deleted in if: always() step after notarization. Never persists between runs.
No secrets in workflow logs | Use masking: echo "::add-mask::$SENSITIVE_VALUE" before printing anything derived from a secret.
Test credentials are test keys | ANTHROPIC_API_KEY_TEST and OPENAI_API_KEY_TEST are separate test keys with usage limits. Never the production keys.

# 14. Monitoring and Maintenance

## 14.1 Runner Offline Detection

# GitHub automatically sends an email when a self-hosted runner goes offline.
# Configure at: repo Settings → Actions → Runners → {runner} → Notifications

# Common reasons the runner goes offline:
#   MacBook lid closed without power adapter
#   macOS update requiring restart
#   LaunchAgent failed to start after login
#   Network change causing runner to lose GitHub connection

# Recovery procedure:
# 1. Ensure MacBook is awake and connected
# 2. cd ~/actions-runner && ./svc.sh status
# 3. If not running: ./svc.sh start
# 4. Check GitHub → Settings → Actions → Runners to confirm "Idle" status

# Prevent sleep during CI runs:
# The LaunchAgent plist (Appendix B) includes:
# caffeinate -i -w $PID
# This keeps the Mac awake while the runner process is active.

## 14.2 Disk Space Management

# DerivedData grows unbounded without cleanup.
# Add a weekly cron to the MacBook:

# Install crontab entry:
crontab -e
# Add:
0 3 * * 0 xcrun simctl delete unavailable 2>/dev/null; \
          rm -rf ~/Library/Developer/Xcode/DerivedData/ForgeAgent-* 2>/dev/null; \
          rm -rf ~/actions-runner/_work/_temp 2>/dev/null

# Runs every Sunday at 3am.
# ForgeAgent-* DerivedData: recreated on next CI run (cache warmup)
# _temp: GitHub Actions temporary files from completed runs

# Disk space targets:
# Keep at least 20GB free on the CI disk at all times.
# DerivedData peak: ~2GB per configuration (Debug + Release + Test)
# site-packages cache: ~800MB
# Artifacts in _work: ~500MB per recent run (pruned by GitHub after 7 days)

## 14.3 Build Time Regression Detection

# Add a step that fails if build takes too long
# (catches cases where a change accidentally triggers a full rebuild)

- name: Check build time
  run: |
    BUILD_TIME=${{ steps.build.outputs.build_duration_seconds }}
    MAX_EXPECTED=600   # 10 minutes
    if [ "$BUILD_TIME" -gt "$MAX_EXPECTED" ]; then
      echo "WARNING: Build took ${BUILD_TIME}s — exceeds ${MAX_EXPECTED}s threshold"
      echo "This may indicate a cache miss or a build regression."
      # Warn but do not fail — log for tracking
    fi

# For tracking: use GitHub Actions job summary to log build times
- name: Record build metrics
  run: |
    echo "## Build Metrics" >> $GITHUB_STEP_SUMMARY
    echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
    echo "| --- | --- |" >> $GITHUB_STEP_SUMMARY
    echo "| Build duration | ${BUILD_DURATION}s |" >> $GITHUB_STEP_SUMMARY
    echo "| DerivedData cache | ${{ steps.cache-deriveddata.outputs.cache-hit }} |" >> $GITHUB_STEP_SUMMARY
    echo "| Python bundle cache | ${{ steps.cache-python.outputs.cache-hit }} |" >> $GITHUB_STEP_SUMMARY

# 15. forge-ci.yml Update — Job Routing

## 15.1 Routing Logic

# forge-ci.yml handles Python. forge-ci-macos.yml handles Swift.
# They run independently. Both must pass for a PR to merge into main.

# Python CI triggers on Python file changes:
# forge-ci.yml paths:
#   - "src/**"
#   - "tests/**"
#   - "requirements.txt"
#   - ".github/workflows/forge-ci.yml"
#   paths-ignore: ForgeAgent/**, *.xcodeproj/**

# macOS CI triggers on Swift file changes:
# forge-ci-macos.yml paths:
#   - "ForgeAgent/**"
#   - "ForgeAgentTests/**"
#   - "*.xcodeproj/**"
#   paths-ignore: src/**, tests/**

# XPC bridge PRs touch both:
#   - ForgeAgent/XPCBridge.swift (Swift)
#   - src/xpc_server.py (Python)
# Both workflows trigger. Both must pass.

## 15.2 Required Status Checks

# Configure at: repo Settings → Branches → main → Branch protection rules

# Required status checks (both must pass before merge):
#   "Forge CI — Python / test"         (from forge-ci.yml)
#   "Forge CI — macOS / unit-test"     (from forge-ci-macos.yml)
#   "Forge CI — macOS / xpc-integration-test"

# If only Python files changed: macOS CI does not trigger.
# GitHub treats a non-triggered required check as "skipped" = passing.
# Skipped is acceptable — it means no Swift was changed.

# If only Swift files changed: Python CI does not trigger.
# Same skip-equals-pass behaviour.

# Both trigger on XPC bridge PRs. Both must be green.

# 16. Testing Requirements

This TRD specifies infrastructure, not application code. Testing focuses on verifying the CI pipeline itself is correct and reliable.

Test | Method | Verification
Runner is reachable | GitHub → Settings → Actions → Runners → status | Shows "Idle" (not "Offline")
Xcode version is correct | Workflow step: xcodebuild -version | Output matches pinned version
Certificate is valid | Appendix C script run monthly | Prints days until expiry; > 30 days
DerivedData cache works | Trigger two consecutive pushes; compare build times | Second build takes < 2 minutes (cache hit)
Python bundle signs cleanly | Workflow: codesign -dv forge-python-bundle/python3.12 | Shows valid Developer ID signature
XPC integration test passes | Workflow: xcodebuild test -scheme XPCIntegrationTests | All 4 XCTestCase methods green
Signing produces valid binary | codesign --verify --deep --strict ForgeAgent.app | Exit code 0
Notarization produces valid staple | xcrun stapler validate + spctl --assess | Both exit 0
Fork PR requires approval | Open PR from forked repo; verify CI does not run automatically | CI status shows "Waiting for approval"
Keychain re-locks after job | Manually trigger workflow; check Keychain after job completes | login.keychain-db is locked

# 17. Performance Requirements

Job | Target Duration (cache hit) | Target Duration (cache miss) | Timeout Setting
setup (verify tools) | < 1 minute | 5 minutes
build (xcodebuild Release) | < 2 minutes | < 10 minutes | 15 minutes
unit-test (all XCTest targets) | < 3 minutes | < 4 minutes | 10 minutes
xpc-integration-test | < 2 minutes | 5 minutes
sign (codesign) | < 1 minute | 3 minutes
artifact (upload) | < 2 minutes | 5 minutes
notarize + staple + dmg | < 12 minutes | 20 minutes
Total PR pipeline (no notarize) | < 12 minutes | < 22 minutes | 40 minutes
Total release pipeline (with notarize) | < 24 minutes | < 34 minutes | 60 minutes

NOTE | These targets assume the MacBook is under normal load. If the machine is actively being used for development while CI runs, build times may be 20-30% longer. For predictable CI times, start builds when the machine is idle or configure runner concurrency to 1.

# 18. Out of Scope

Feature | Reason | Target
Dedicated Mac build server | Developer MacBook is sufficient for the build volume this project generates. | Only if build volume grows significantly
Multiple Mac runners | One runner is sufficient. Parallelism is handled within jobs. | v2 if needed
Mac containers (macOS in Docker) | Apple does not license macOS virtualisation outside Apple hardware. Not legally possible on cloud. | Never
App Store distribution | Requires sandbox entitlements and App Store review. Deferred. | v2
TestFlight distribution | App Store Connect account and App Store review. Not the distribution model. | Never for this product
Performance testing in CI | Instruments requires a real device/interactive session. Automated performance regression testing is complex. | v2
UI screenshot testing | XCUITest screenshots work in CI but diffing requires a reference baseline and is fragile across macOS versions. | v2
Windows or Linux runner | No macOS frameworks on other platforms. | Never

# 19. Open Questions

ID | Question | Owner | Needed By
OQ-01 | MacBook must be awake for CI to run. If the runner goes offline (lid closed, sleep, restart), in-progress CI jobs fail. Should there be a policy that the MacBook stays on a charger and sleep is disabled? Recommendation: yes — System Settings → Battery → Prevent automatic sleeping when on Power Adapter. Document as a runner operating procedure. | Engineering | Before first Swift PR
OQ-02 | Concurrent CI runs: if two PRs are opened at the same time, both jobs queue on the single runner. The second waits. This is fine for the current team size. If concurrency becomes a problem, a second MacBook can be added as a runner in an afternoon. | Engineering | Monitor after 4 weeks
OQ-03 | Certificate renewal: Developer ID Application certificates expire after 5 years. A process for renewal before expiry must be established and documented. The Appendix C script monitors expiry. Who is responsible for acting on the alert? | Product/Engineering | Before cert approaches 30 days
OQ-04 | KEYCHAIN_PASSWORD stored as a GitHub secret: this is the macOS login password. If this secret is compromised, the attacker has Keychain access on the MacBook. Alternative: use a separate Keychain partition for CI-only secrets. Recommendation: evaluate complexity vs risk before implementing. | Engineering | Before any external collaborators added

# Appendix A: Complete forge-ci-macos.yml

name: Forge CI — macOS

on:
  push:
    branches: [main, "forge-agent/build/**"]
    paths:
      - "ForgeAgent/**"
      - "ForgeAgentTests/**"
      - "XPCIntegrationTests/**"
      - "*.xcodeproj/**"
      - "Package.swift"
      - "requirements.txt"
      - ".github/workflows/forge-ci-macos.yml"
    paths-ignore: ["prds/**", "forge-docs/**", "**.md", "**.docx", "src/**", "tests/**"]
  pull_request:
    branches: [main]
    paths: ["ForgeAgent/**", "ForgeAgentTests/**", "XPCIntegrationTests/**",
            "*.xcodeproj/**", "Package.swift"]

env:
  SCHEME: ForgeAgent
  BUILD_DIR: ${{ github.workspace }}/build

jobs:
  setup:
    name: Verify Environment
    runs-on: [self-hosted, macos]
    steps:
      - uses: actions/checkout@v4
      - name: Verify tools
        run: |
          echo "Xcode: $(xcodebuild -version | head -1)"
          echo "Swift: $(swift --version | head -1)"
          echo "xcbeautify: $(xcbeautify --version)"
          security find-identity -v -p codesigning | grep "Developer ID" || \
            { echo "ERROR: Developer ID certificate not found"; exit 1; }

  build:
    name: Build
    runs-on: [self-hosted, macos]
    needs: setup
    steps:
      - uses: actions/checkout@v4
      - name: Cache DerivedData
        uses: actions/cache@v4
        with:
          path: ~/Library/Developer/Xcode/DerivedData
          key: ${{ runner.os }}-deriveddata-${{ hashFiles('**/*.xcodeproj/project.pbxproj') }}
          restore-keys: ${{ runner.os }}-deriveddata-
      - name: Cache Python bundle
        id: cache-python
        uses: actions/cache@v4
        with:
          path: forge-python-bundle
          key: python-${{ runner.os }}-${{ runner.arch }}-${{ hashFiles('requirements.txt') }}-3.12
      - name: Build Python bundle
        if: steps.cache-python.outputs.cache-hit != 'true'
        run: scripts/build_python_bundle.sh
      - name: Sign Python bundle
        run: |
          codesign --force --sign "${{ secrets.APPLE_SIGNING_IDENTITY }}" \
            forge-python-bundle/python3.12
          find forge-python-bundle/site-packages -name "*.so" -exec \
            codesign --force --sign "${{ secrets.APPLE_SIGNING_IDENTITY }}" {} \;
      - name: Build app
        run: |
          set -o pipefail
          xcodebuild -project $SCHEME.xcodeproj -scheme $SCHEME \
            -configuration Release -destination "generic/platform=macOS" \
            ONLY_ACTIVE_ARCH=NO ARCHS="arm64 x86_64" BUILD_DIR="$BUILD_DIR" \
            ENABLE_HARDENED_RUNTIME=YES CODE_SIGN_STYLE=Manual \
            CODE_SIGN_IDENTITY="${{ secrets.APPLE_SIGNING_IDENTITY }}" \
            CODE_SIGN_TEAM="${{ secrets.APPLE_TEAM_ID }}" build \
          | xcbeautify --renderer github-actions
      - name: Inject Python bundle
        run: |
          RES="$BUILD_DIR/Release/$SCHEME.app/Contents/Resources"
          cp forge-python-bundle/python3.12 "$RES/"
          cp -r forge-python-bundle/site-packages "$RES/"
          cp -r src/agent "$RES/"
      - name: Upload unsigned app
        uses: actions/upload-artifact@v4
        with:
          name: forge-agent-unsigned-${{ github.run_id }}
          path: ${{ env.BUILD_DIR }}/Release/ForgeAgent.app
          retention-days: 7

  unit-test:
    name: Unit Tests
    runs-on: [self-hosted, macos]
    needs: build
    steps:
      - uses: actions/checkout@v4
      - name: Cache DerivedData
        uses: actions/cache@v4
        with:
          path: ~/Library/Developer/Xcode/DerivedData
          key: ${{ runner.os }}-deriveddata-${{ hashFiles('**/*.xcodeproj/project.pbxproj') }}
          restore-keys: ${{ runner.os }}-deriveddata-
      - name: Run unit tests
        run: |
          set -o pipefail
          xcodebuild -project $SCHEME.xcodeproj -scheme $SCHEME \
            -destination "platform=macOS,arch=arm64" \
            -resultBundlePath "${{ github.workspace }}/test-results/results.xcresult" \
            -parallel-testing-enabled YES \
            test | xcbeautify --renderer github-actions
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ github.run_id }}
          path: test-results/results.xcresult
          retention-days: 7

  xpc-integration-test:
    name: XPC Integration Test
    runs-on: [self-hosted, macos]
    needs: build
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - name: Download unsigned app
        uses: actions/download-artifact@v4
        with:
          name: forge-agent-unsigned-${{ github.run_id }}
          path: build/Release
      - name: Run XPC integration test
        run: |
          set -o pipefail
          xcodebuild -project $SCHEME.xcodeproj -scheme XPCIntegrationTests \
            -destination "platform=macOS,arch=arm64" test \
          | xcbeautify --renderer github-actions
        env:
          APP_PATH: ${{ github.workspace }}/build/Release/ForgeAgent.app

  sign:
    name: Sign
    runs-on: [self-hosted, macos]
    needs: [unit-test, xpc-integration-test]
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: forge-agent-unsigned-${{ github.run_id }}
          path: unsigned
      - name: Unlock Keychain
        run: security unlock-keychain -p "${{ secrets.KEYCHAIN_PASSWORD }}"
            ~/Library/Keychains/login.keychain-db
      - name: Sign app
        run: |
          codesign --force --deep --sign "${{ secrets.APPLE_SIGNING_IDENTITY }}" \
            --entitlements ForgeAgent/ForgeAgent.entitlements \
            --options runtime \
            unsigned/ForgeAgent.app
          codesign --verify --deep --strict unsigned/ForgeAgent.app
      - name: Lock Keychain
        if: always()
        run: security lock-keychain ~/Library/Keychains/login.keychain-db
      - name: Upload signed app
        uses: actions/upload-artifact@v4
        with:
          name: forge-agent-signed-${{ github.run_id }}
          path: unsigned/ForgeAgent.app
          retention-days: 14

  notarize:
    name: Notarize and Package
    runs-on: [self-hosted, macos]
    needs: sign
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: forge-agent-signed-${{ github.run_id }}
          path: signed
      - name: Set up ASC API key
        run: |
          mkdir -p ~/.appstoreconnect/private_keys
          echo "${{ secrets.ASC_API_KEY_BASE64 }}" | base64 --decode \
            > ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8
      - name: Notarize
        run: |
          ditto -c -k --keepParent signed/ForgeAgent.app ForgeAgent.zip
          xcrun notarytool submit ForgeAgent.zip \
            --key ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8 \
            --key-id ${{ secrets.ASC_API_KEY_ID }} \
            --issuer ${{ secrets.ASC_API_KEY_ISSUER }} \
            --wait --timeout 15m
          xcrun stapler staple signed/ForgeAgent.app
      - name: Create DMG
        run: |
          VERSION="${{ github.ref_name }}"
          create-dmg \
            --volname "Forge Agent" \
            --window-size 800 400 \
            --icon-size 100 \
            --icon "ForgeAgent.app" 200 190 \
            --app-drop-link 600 185 \
            "ForgeAgent-${VERSION}.dmg" "signed/ForgeAgent.app"
          xcrun notarytool submit "ForgeAgent-${VERSION}.dmg" \
            --key ~/.appstoreconnect/private_keys/AuthKey_${{ secrets.ASC_API_KEY_ID }}.p8 \
            --key-id ${{ secrets.ASC_API_KEY_ID }} \
            --issuer ${{ secrets.ASC_API_KEY_ISSUER }} \
            --wait --timeout 15m
          xcrun stapler staple "ForgeAgent-${VERSION}.dmg"
      - name: Upload DMG
        uses: actions/upload-artifact@v4
        with:
          name: ForgeAgent-${{ github.ref_name }}.dmg
          path: ForgeAgent-${{ github.ref_name }}.dmg
          retention-days: 90
      - name: Cleanup
        if: always()
        run: rm -f ~/.appstoreconnect/private_keys/AuthKey_*.p8

# Appendix B: Runner LaunchAgent plist

<!-- ~/Library/LaunchAgents/actions.runner.{owner}-{repo}.{runner-name}.plist -->
<!-- Installed by: ./svc.sh install -->
<!-- Start: ./svc.sh start | Stop: ./svc.sh stop -->

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>actions.runner.{owner}-{repo}.macbook-forge-runner</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/{username}/actions-runner/runsvc.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/{username}/actions-runner</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/{username}</string>
        <key>DEVELOPER_DIR</key>
        <string>/Applications/Xcode.app/Contents/Developer</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>LANG</key>
        <string>en_US.UTF-8</string>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/{username}/actions-runner/_diag/Runner_log.txt</string>

    <key>StandardErrorPath</key>
    <string>/Users/{username}/actions-runner/_diag/Runner_err.txt</string>
</dict>
</plist>

# Note: ./svc.sh install generates this file automatically.
# Edit EnvironmentVariables section to add custom paths.
# After editing: launchctl unload {plist} && launchctl load {plist}

# Appendix C: Certificate Health Check Script

#!/bin/bash
# scripts/check_cert_expiry.sh
# Run monthly via cron or manually.
# Warns when Developer ID certificate approaches expiry.

set -e

WARN_DAYS=60
IDENTITY="Developer ID Application"

# Find Developer ID certificate expiry
CERT_INFO=$(security find-certificate -c "$IDENTITY" -p | \
            openssl x509 -noout -dates 2>/dev/null)

if [ -z "$CERT_INFO" ]; then
    echo "ERROR: No Developer ID Application certificate found in Keychain"
    exit 1
fi

EXPIRY_DATE=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
EXPIRY_EPOCH=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" "+%s" 2>/dev/null)
NOW_EPOCH=$(date "+%s")
DAYS_REMAINING=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

echo "Developer ID Application certificate expires: $EXPIRY_DATE"
echo "Days remaining: $DAYS_REMAINING"

if [ "$DAYS_REMAINING" -lt 0 ]; then
    echo "CRITICAL: Certificate has EXPIRED. Code signing will fail immediately."
    echo "Action: Revoke and renew at developer.apple.com immediately."
    exit 2
elif [ "$DAYS_REMAINING" -lt "$WARN_DAYS" ]; then
    echo "WARNING: Certificate expires in $DAYS_REMAINING days."
    echo "Action: Renew at developer.apple.com before it expires."
    echo "Update APPLE_SIGNING_IDENTITY secret in GitHub after renewal."
    exit 1
else
    echo "OK: Certificate is valid for $DAYS_REMAINING more days."
    exit 0
fi

# Add to crontab for monthly check:
# 0 9 1 * * /path/to/scripts/check_cert_expiry.sh >> ~/cert_check.log 2>&1

# Appendix D: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification