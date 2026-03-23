# TRD-5-GitHub-Integration-Crafted

_Source: `TRD-5-GitHub-Integration-Crafted.docx` — extracted 2026-03-23 17:24 UTC_

---

# TRD-5: GitHub Integration Layer

Technical Requirements Document — v1.1

Product: Crafted Document: TRD-5: GitHub Integration Layer Version: 1.1 Status: Updated — PR Type Lifecycle Notes (March 2026) Author: YouSource.ai Previous Version: v1.0 (2026-03-19) Depends on: TRD-1 (Keychain), TRD-3 (path_security) Required by: TRD-3 (pipeline uses GitHubTool), TRD-4 (ledger)

## What Changed from v1.0

One targeted addition. All sections from v1.0 are unchanged.

§5a — PR lifecycle routing by type: how spec.pr_type affects GitHub operations (new)

## §5a. PR Lifecycle Routing by Type (New in v1.1)

### Overview

PRSpec now carries a pr_type field (“implementation”, “documentation”, or “test”) that determines which GitHub operations are performed. GitHubTool itself is not aware of pr_type — it executes whatever operations are requested. The routing logic lives in build_director.py. This section documents the operational consequences for each type.

### Operation Matrix by PR Type

GitHub Operation | implementation | documentation | test
create_branch() | Yes
commit_file() — impl | Yes | Yes (markdown/yaml/json) | No (impl IS test)
commit_file() — test | Yes | No | Yes
create_pr() (draft) | Yes
CI gate wait (ci_checker) | Yes — blocks on pass/fail | No — skipped entirely | Yes — waits after deps merge
mark_ready_for_review() | Yes — after CI passes | Yes — immediately after commit | Yes — after CI passes

### Documentation PRs and CI

Documentation PRs commit only non-code files (.md, .yaml, .json, etc.). The CI workflow (crafted-ci.yml) uses paths-ignore to exclude these file types from triggering the test job. A PR that only changes non-code files never triggers CI — it passes automatically. The agent does not wait for CI on documentation PRs; it marks them ready immediately after the commit succeeds.

### Test-only PRs and CI

Test-only PRs contain test files that import from other PRs’ code. Those dependencies don’t exist on the test PR’s branch until the dependency PRs are merged to main. The agent commits the test file, opens the PR, and skips the local test loop. CI runs automatically after the PR is opened — it will fail until dependency PRs are merged. This is expected and correct. The PR is marked ready for review immediately; merging is a manual operator decision after dependencies are confirmed merged.

### 422 Recovery (from TRD-13 §8.4)

When create_pr() returns 422 (PR already exists for this branch), the agent recovers by searching for the existing open PR on that branch and using its number. This applies to all three pr_type values. The result is transparent idempotency — resume behaves identically to first run regardless of whether the PR was already opened in a prior session.

## Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification — GitHubTool API, authentication (PAT v1, App v2), branch namespace, PR lifecycle, rate limiting, CI workflow, webhook receiver, repository bootstrap
1.1 | 2026-03-22 | PR lifecycle routing by type (§5a) — documents how spec.pr_type affects GitHub operation sequencing for implementation, documentation, and test-only PRs.