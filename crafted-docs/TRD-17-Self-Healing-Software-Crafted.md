# TRD-17-Self-Healing-Software-Crafted

_Source: `TRD-17-Self-Healing-Software-Crafted.docx` — extracted 2026-03-26 21:48 UTC_

---

TRD-17: Self-Healing Software — Autonomous Observability and Remediation

Technical Requirements Document — v1.0

Field | Value
Product | Crafted Dev Agent + all products and agents it builds
Document | TRD-17: Self-Healing Software — Autonomous Observability and Remediation
Version | 1.0
Status | Active — Initial Release (March 2026)
Author | YouSource.ai
Scope | Crafted Dev Agent itself, every app it builds, every agent it deploys
Depends on | TRD-3 (Build Pipeline), TRD-5 (GitHub), TRD-11 (Security), TRD-13 (Recovery), TRD-14 (CI), TRD-16 (Testing)

# §1 Purpose and Scope

This document specifies the self-healing capability of the Crafted platform. Self-healing means Crafted continuously monitors, detects, classifies, and remediates bugs and security issues — not only in its own pipeline code, but in every application and agent it produces.

Core principle: a build is not complete when the last PR merges. A build is complete when the continuous health loop is running and the product can maintain itself.

The self-healing loop applies universally across three target classes:

Target class | Examples | Who initiates remediation
Crafted itself | build_director.py, failure_handler.py, self_correction.py | Crafted monitors its own pipeline logs and test suite
Apps Crafted builds | Crafted macOS shell, any Swift/Python app produced by the pipeline | Crafted monitors CI, crash telemetry, and security scans for each app
Agents Crafted deploys | Future AI agents built on the same pipeline | Crafted monitors agent logs, LLM trace outputs, and safety signals

The same four-stage loop — Observe → Detect → Classify → Remediate — runs for all three target classes. The target is a parameter, not a hardcoded assumption.

# §2 Design Decisions

## §2.1 Autonomous-first with human escalation gates

Crafted acts autonomously on high-confidence, low-risk issues. Human review is required for security-critical changes and low-confidence classifications. The escalation policy is explicit and operator-configurable — there are no silent auto-merges on security issues.

## §2.2 PR-based remediation

All fixes are delivered as GitHub PRs, identical to feature PRs. This means every fix has a full audit trail: what was detected, what was generated, what tests passed, what CI ran. No hotfixes applied directly to main.

## §2.3 Target-parameterized

The health loop is not specific to any one codebase. It takes a target (repo, subsystem, agent ID) and applies the same observe/detect/classify/remediate pipeline. Adding a new app or agent to the health loop requires only registering it as a target.

## §2.4 Build memory as institutional knowledge

Every remediation outcome is written to build_memory.json for that target. Patterns that cause repeated fixes become build rules that prevent the same issue from appearing in future builds of similar systems. The system learns across both the initial build and the maintenance lifecycle.

# §3 The Self-Healing Loop

Observe → Detect → Classify → Remediate → Validate → Learn

## §3.1 Observe

Crafted maintains continuous visibility into the health of each registered target through four signal sources:

Signal source | What it captures | Polling / trigger
CI check runs | Test failures, lint errors, type errors on every push | GitHub webhook or polling on open PRs and main
LLM trace log | Self-correction oscillation, generation quality drift, context bleed | Parsed after each build run
Runtime telemetry | Crash reports, exception rates, performance regressions from deployed apps | Continuous (streamed or batched)
Security scans | Dependency vulnerabilities (CVEs), static analysis findings, secret detection | Scheduled daily + on each dependency change
Build memory patterns | Recurring fix_attempts, failure_type clusters, CI failure rates across PRs | Analyzed after each completed build run

## §3.2 Detect

Detection thresholds determine when a signal becomes an actionable issue. Thresholds are configurable per target.

Condition | Default threshold | Signal source
CI failure on main | Any failure | CI check runs
Test coverage drop | > 5% decrease from baseline | CI check runs
CVE in dependency | CVSS ≥ 7.0 (high/critical) | Security scan
Secret in code | Any match | Security scan
Self-correction oscillation | Alternating pattern over 6 passes OR 4 consecutive identical | LLM trace log
Recurring failure type | Same failure_type in ≥ 3 PRs in a build run | Build memory
Runtime exception rate | > 1% of requests over 5 min window | Runtime telemetry
Generation quality drift | Claude win delta < 2 for ≥ 3 consecutive PRs | LLM trace log

## §3.3 Classify

Every detected issue is classified before remediation begins. Classification determines the remediation path and the required confidence for autonomous action.

Class | Definition | Autonomous threshold | Human gate required
Bug — functional | Test fails, runtime exception, wrong output | High confidence | No (auto-PR + auto-merge after CI)
Bug — regression | Worked before, broken now; diff-attributable | High confidence | No (auto-PR + auto-merge after CI)
Security — dependency | CVE in requirements.txt or Package.swift | Always | Yes (PR opened, operator approves merge)
Security — code | Hardcoded secret, shell=True, eval() on external input | Always | Yes (PR opened, operator approves merge)
Quality — generation drift | LLM consistently producing low-delta or oscillating output | High confidence | No (build rules updated, next run benefits)
Pipeline — agent code | Bug in Crafted’s own source (build_director.py etc.) | Always requires test | Yes (test-first process, engineer reviews)
Unknown | Cannot be classified with confidence | Never autonomous | Yes (logged, alerted, operator decides)

## §3.4 Remediate

Remediation is always delivered as a GitHub PR. The PR contains the fix, updated tests, and a structured description of what was detected, classified, and changed.

### Functional bug / regression fix

Scope: identify affected file(s) from CI log or telemetry stack trace

Generate fix PR using /prd start with the failure output as context

Self-correction loop runs against the fix

Tests pass locally — PR opened as draft

CI passes — PR marked ready

Auto-merge if confidence HIGH and no security flags

### Security issue fix

Scope: identify the vulnerable dependency or code pattern

Generate fix PR: dependency bump or code rewrite

PR opened with security classification in body and label

CI passes — PR marked ready for review

OPERATOR GATE: human reviews and approves merge — never auto-merged

After merge: security scan re-runs to confirm remediation

### Pipeline bug fix (Crafted itself)

Write a failing test that reproduces the bug

Apply the fix

Confirm the new test passes

Run full test suite: pytest tests/ -v

Package and patch — never skip the test suite

## §3.5 Validate

Every fix is validated before and after merge:

Pre-merge: CI passes, new test passes, no regressions in full suite

Post-merge: security scan re-runs (for security fixes), runtime telemetry monitored for 24h (for runtime fixes)

If post-merge validation fails: revert PR is opened automatically

## §3.6 Learn

Every remediation outcome is written back into the system’s institutional knowledge:

build_memory.json for the target: records fix pattern, failure type, resolution approach

build_rules.md: if the same class of bug appears ≥ 3 times, a build rule is derived and written to Mac-Docs

Next build of a similar system: the build rule prevents the same issue from being generated

The goal is that each generation of a new app or agent starts with fewer known-bad patterns than the one before it. The self-healing loop is also a self-improving generation loop.

# §4 Observability Infrastructure

These components must be present in every target registered for self-healing. They are not optional features — they are prerequisites for the health loop to function.

## §4.1 LLM Trace Log (agents only)

Every LLM call writes to logs/llm_trace.log: model, stage, task, prompt hash, response preview, duration, token estimate

File persists across restarts. Never rotated automatically.

Grep-able format for pattern analysis

Required signal for: oscillation detection, generation drift, context bleed detection

## §4.2 Structured Application Log

Named loggers per subsystem: logging.getLogger('crafted.{subsystem}')

Levels used consistently: DEBUG=trace, INFO=state change, WARNING=recoverable, ERROR=failure

Every error includes: what failed, what the input was, what the expected outcome was

No print() in production code paths

## §4.3 Stage Checkpoints

Every multi-step operation checkpoints progress to persistent storage

Checkpoint files are never auto-deleted — they are the audit trail for the health loop

Resume logic reads checkpoints before re-running any expensive operation

Checkpoint format: JSON with stage name, timestamp, and relevant state

## §4.4 Build Memory and Build Rules

build_memory.json: per-PR outcomes, failure types, fix patterns. Never deleted between runs.

build_rules.md: derived coding rules from recurring failure patterns. Loaded by DocumentStore automatically.

Both files survive clean state wipes. They are the institutional memory of the system.

## §4.5 Runtime Telemetry (apps only)

Exception handler wraps all entry points and emits structured error events

Error events include: exception type, stack trace hash, subsystem, timestamp

Telemetry endpoint is configurable — local file or remote collector

No PII in telemetry events. Stack traces are hashed, not raw.

# §5 Target Registration

A target is any codebase, app, or agent under the self-healing loop. Registering a target enables health monitoring and autonomous remediation for it.

## §5.1 Registration Requirements

To register a target, the following must be present:

GitHub repository with CI configured (crafted-ci.yml or equivalent)

At least one of: structured logs, LLM trace log (for agents), runtime telemetry (for apps)

A test suite with at least one test (empty suite disables post-fix validation)

An entry in the health registry with: target_id, repo, subsystem, escalation_policy

## §5.2 Health Registry Schema

{ "target_id": "crafted-app-shell",

"repo": "todd-yousource-ai/Dev-Agent",

"subsystem": "CraftedAppShell",

"language": ["swift", "python"],

"escalation_policy": {

"security": "operator_review",

"functional": "auto_merge",

"pipeline": "engineer_review"

},

"ci_workflow": ".github/workflows/crafted-ci.yml",

"telemetry_endpoint": "logs/telemetry.jsonl"

}

# §6 Bug Resolution Process for Pipeline Code

When the bug is in Crafted’s own pipeline (Category 2 — the agent itself), a stricter process applies because there is no automated test-and-merge. The engineer is in the loop.

Pipeline bugs require: write test first, fix second, suite clean third. No exceptions.

Step | Action | Gate
1. Identify | Locate the exact failure from agent.log and llm_trace.log | None — diagnostic only
2. Reproduce | Write a failing pytest test that reproduces the exact condition | Test must fail before fix
3. Fix | Apply the minimal code change that resolves the failure | None
4. Verify | Run the new test — must pass | Hard gate: fix not shipped if test fails
5. Regression | Run full suite: pytest tests/ -v | Hard gate: all prior tests must pass
6. Package | Bump version, zip, patch.py | None — ship only if steps 4+5 pass

## §6.1 Test File Mapping

Source file | Test file
build_director.py | tests/test_build_director.py + test_build_director_backfill.py
path_security.py | tests/test_path_security.py
self_correction.py | tests/test_self_correction.py
failure_handler.py | tests/test_failure_handler.py
markdown_strategy.py | tests/test_markdown_strategy_backfill.py
ci_checker.py | tests/test_ci_checker.py
pr_planner.py / prd_planner.py | tests/test_prd_planner.py
config.py | tests/test_build_director.py (config section)

# §7 Common Failure Patterns Index

Indexed from the first Crafted bootstrap run. This index grows with each build. Every entry reduces future debugging time for similar systems.

Signal | Root cause | Class | Fix
Self-correction 20-pass cap | Single-file constraint on multi-file scaffold PR | Pipeline | Scaffold multi-file commit path (v38.185)
UnboundLocalError: ci_result | Docs PRs skip CI gate; variable never assigned | Pipeline | _CIResultDefault before gate (v38.175)
Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection (v38.180)
AGENTS.md merge conflict | markdown_strategy bypassed branch protection | Pipeline | Branch guard in _commit_all (v38.185)
NameError: free variable 'os' | os.path in nested function, Python 3.14 strict | Pipeline | Replace with pathlib (v38.173/174)
Enriched spec 404 | Prds branch not created before commit | Pipeline | _ensure_branch before commit (v38.183)
Re-enrichment on resume | GitHub JSON saved pre-enrichment | Pipeline | Commit after enrichment (v38.181)
LLM trace log empty | Direct calls bypass consensus trace | Observability | Wire _write_trace everywhere (v38.172/177)
Oscillation A/B pattern | Alternating issues; detector only caught consecutive | Pipeline | Alternating pattern detection (v38.185)
Bail on impl syntax error | Early bail didn't check impl validity | Pipeline | ast.parse before bail (v38.185)

# §8 Acceptance Criteria

These criteria must pass before any target is considered self-healing capable.

## §8.1 Observability

LLM trace log captures all calls within 30s of build start (agents)

Agent log shows named subsystem loggers, not print() statements

Build memory persists across restarts and grows with each completed PR

Runtime telemetry endpoint receives events within 5s of an exception (apps)

## §8.2 Detection

CI failures on main trigger a detection event within 2 minutes

CVE ≥ 7.0 in any dependency triggers a security detection event within 24h

Self-correction oscillation is detected before the 20-pass cap

Recurring failure types are identified after 3 occurrences in a build run

## §8.3 Remediation

Functional bug fix PR is opened within one build cycle of detection

Security fix PR is opened with operator_review label — never auto-merged

Every fix PR includes: detection signal, classification, what changed, new test

Post-merge validation runs and revert PR is opened on failure

## §8.4 Pipeline discipline

All 35 regression tests pass: pytest tests/test_regression_taxonomy.py

Full suite passes: pytest tests/ -v exits 0

Every pipeline bug fix ships with a test written before the fix

No pipeline patch ships without the full suite running clean

TRD-17 v1.0 — Crafted Dev Agent — YouSource.ai — March 2026