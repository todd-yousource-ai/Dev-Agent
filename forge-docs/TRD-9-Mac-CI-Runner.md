# TRD-9-Mac-CI-Runner

_Source: `TRD-9-Mac-CI-Runner.docx` — extracted 2026-03-19 18:29 UTC_

---

TRD-9

Mac CI Runner Infrastructure

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Mac CI Runner Infrastructure — a self-hosted GitHub Actions runner on the developer's MacBook that gives the Consensus Dev Agent a real macOS build environment.

Without this infrastructure, the agent can write Swift but cannot validate it. With it, the agent operates against a real Xcode toolchain on real Apple hardware — the same machine that will eventually ship the product. The loop becomes: agent PRs Swift, Mac runner builds and tests it, CI result returns to agent via webhook, agent fixes and re-PRs. The same autonomous loop that works for Python now works for Swift.

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

# 3. Runner Installation and Configuration

## 3.1 Installation Procedure

## 3.2 Runner Labels

## 3.3 Environment Variables Available to Jobs

## 3.4 GitHub Secrets Required

# 4. Xcode and Toolchain Setup

## 4.1 Xcode Version Pinning

## 4.2 Required Tools

# 5. Code Signing Infrastructure

## 5.1 Certificate Setup

## 5.2 Keychain Unlock in CI

## 5.3 Entitlements File

# 6. forge-ci-macos.yml — Workflow Overview

## 6.1 Trigger Specification

## 6.2 Job Dependency Graph

# 7. Build Job

## 7.1 DerivedData Caching

## 7.2 xcodebuild Command

## 7.3 Build Output Location

# 8. Test Job

## 8.1 XCTest Targets

## 8.2 xcodebuild test Command

## 8.3 Touch ID Mocking in Tests

# 9. XPC Integration Test

## 9.1 Why This Test Matters

The XPC integration test is the single most valuable test in the entire CI suite. It verifies that the Swift shell and the Python backend can actually communicate — that the socket is established, the handshake completes, credentials are delivered, and a ping-pong round-trip succeeds. If this test is green, the two halves of the app are talking to each other on real Apple hardware.

## 9.2 Test Structure

## 9.3 Running the Integration Test in CI

# 10. Python Bundling in CI

## 10.1 Bundle Strategy

The XPC integration test requires the bundled Python binary to be present inside the built .app. The Python standalone binary and all site-packages must be built for the correct architecture and signed before the integration test runs.

## 10.2 Python Caching Steps

# 11. Notarization Job

## 11.1 Trigger Conditions

## 11.2 Notarization Steps

# 12. Artifact Management

## 12.1 Artifact Upload Steps

# 13. Runner Security and Isolation

## 13.1 Fork PR Protection

## 13.2 Secret Hygiene Rules

# 14. Monitoring and Maintenance

## 14.1 Runner Offline Detection

## 14.2 Disk Space Management

## 14.3 Build Time Regression Detection

# 15. forge-ci.yml Update — Job Routing

## 15.1 Routing Logic

## 15.2 Required Status Checks

# 16. Testing Requirements

This TRD specifies infrastructure, not application code. Testing focuses on verifying the CI pipeline itself is correct and reliable.

# 17. Performance Requirements

# 18. Out of Scope

# 19. Open Questions

# Appendix A: Complete forge-ci-macos.yml

# Appendix B: Runner LaunchAgent plist

# Appendix C: Certificate Health Check Script

# Appendix D: Document Change Log