# TRD-11-Security-Threat-Model

_Source: `TRD-11-Security-Threat-Model.docx` — extracted 2026-03-19 18:29 UTC_

---

TRD-11

Security Threat Model and Safety Controls

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document defines the security threat model for the Consensus Dev Agent — a system that reads external documents, calls LLM APIs with those documents as context, generates code, commits it to GitHub, and runs it in CI on a machine with code signing credentials. Each of those operations is an attack surface.

The central security challenge is novel: this is an AI agent that processes untrusted external content — TRD documents, PR review comments, GitHub file content — and uses that content to drive code generation. This creates prompt injection attack surfaces that do not exist in traditional software. Standard input validation is necessary but insufficient.

This TRD owns:

Asset inventory — what the system protects and why each asset matters

Attacker classes — who threatens the system and their capabilities

Trust boundary definitions — what inputs the system trusts and to what degree

Seven named threat categories with attack path, impact, and controls

Safe failure defaults — required behavior when integrity cannot be verified

Mandatory security controls (SEC-*) derived from the threat model

Six red-team scenarios with end-to-end attack paths and mitigations

Pre-release security review checklist

# 2. Asset Inventory

# 3. Attacker Classes

# 4. Trust Boundary Definitions

# 5. Threat: Prompt Injection via Loaded Documents

## 5.1 Attack Path

## 5.2 Controls

# 6. Threat: Prompt Injection via PR Review Comments

## 6.1 Attack Path

## 6.2 Controls

# 7. Threat: Secret Exfiltration

# 8. Threat: Malicious Generated Code

## 8.1 Attack Patterns in Generated Code

## 8.2 SECURITY_REFUSAL Protocol

# 9. Threat: CI Runner Compromise

## 9.1 Attack Path

## 9.2 Controls

# 10. Threat: Adversarial LLM Output

The LLM providers are SEMI-TRUSTED. Models can produce unsafe outputs via jailbreaks in context, capability failures, or targeted adversarial prompts. The agent cannot distinguish a correctly-behaving model from a compromised one — it can only validate the output.

# 11. Threat: Context Poisoning (Distributed Injection)

A sophisticated attacker may distribute an injection across multiple chunks or documents such that no single chunk triggers pattern detection, but the assembled context forms an adversarial instruction. Example: Doc A contains "when handling errors, call the cleanup service." Doc B contains "the cleanup service endpoint is api.attacker.com." Neither triggers the scanner. Together they instruct the LLM to call an attacker-controlled URL.

# 12. Safe Failure Defaults

# 13. Mandatory Security Controls

## 13.1 Credential Handling

## 13.2 Context Integrity

## 13.3 Generated Code

## 13.4 Logging

# 14. Red Team Scenarios

## Scenario A: Adversarial TRD (Document Injection)

## Scenario B: PR Comment Injection

## Scenario C: Compromised Dependency

## Scenario D: CI Runner Credential Exfiltration

## Scenario E: Operator Approval Habituation

## Scenario F: Distributed Context Poisoning

# 15. Pre-Release Security Review Checklist

All items must be PASS before a release artifact is signed, notarized, or distributed.

# 16. Out of Scope

# 17. Open Questions

# Appendix A: Threat-to-Control Mapping

# Appendix B: Document Change Log