# TRD-5-GitHub-Integration-Crafted

_Source: `TRD-5-GitHub-Integration-Crafted.docx` — extracted 2026-03-25 19:25 UTC_

---

TRD-5: GitHub Integration Layer

Technical Requirements Document — v1.1

Field | Value
Product | Crafted
Document | TRD-5: GitHub Integration Layer
Version | 1.1
Status | Updated — PR Type Lifecycle Notes (March 2026)
Author | YouSource.ai
Previous Version | v1.0 (2026-03-19)
Depends on | TRD-1 (Keychain — token storage), TRD-3 (path_security — commit path validation)
Required by | TRD-3 (pipeline uses GitHubTool for all repo ops), TRD-4 (ledger uses commit_file + get_file)
Language | Python 3.12
Auth (v1) | Personal Access Token stored in macOS Keychain
Auth (v2) | GitHub App — JWT + installation token (upgrade path, not shipped in v1)

# 1. Purpose and Scope

This document specifies the complete technical requirements for the GitHub Integration Layer — all communication between the Crafted Dev Agent and GitHub repositories.

The Layer owns: authentication (PAT v1, GitHub App v2), GitHubTool (single Python class through which all GitHub operations flow), file commit protocol, branch namespace, PR lifecycle, rate limiting with exponential backoff, CI gate polling, CI workflow management (crafted-ci.yml), PR review ingestion, and repository bootstrap.

Scope boundary: TRD-5 specifies the GitHub interface only. Build state management is TRD-3. Ledger coordination is TRD-4. Secret storage is TRD-1. Path security for commit paths delegates to path_security.py.

# 2. Design Decisions

Decision | Choice | Rationale
Auth in v1 | Personal Access Token (PAT) from Keychain | Already implemented and working. GitHub App migration is a clean upgrade path — same API, different token source.
Auth in v2 | GitHub App with JWT + installation tokens | Apps have scoped per-repo permissions, auto-expiring tokens, and audit trails showing 'Crafted Agent' not a username.
REST vs GraphQL | REST for all writes; GraphQL optional for rich reads | GitHub's GraphQL API does not support mutations for most write operations. REST required for commits, PRs, merges.
PyGithub vs raw requests | PyGithub for v1 | PyGithub is well-tested and handles pagination, retries, and rate limits.
Rate limit strategy | Exponential backoff on 403/429; Retry-After header honored | Secondary rate limits fire on bursts of write operations. Backoff prevents agent from getting blocked.
CI polling vs webhook | Poll as primary, webhook as enhancement | Polling works without webhook infrastructure. Webhook reduces CI wait time from 30s average to < 5s.

# 3. Authentication

## 3.1 v1 — Personal Access Token

PAT is stored in macOS Keychain (TRD-1 §5). Retrieved at backend startup via XPC credential delivery. Passed to GitHubTool at construction time — never re-fetched during a session.

class GitHubTool:

def __init__(self, config: AgentConfig) -> None:

self._config = config

self._client = Github(auth=Auth.Token(config.github_token))

self._repo: Optional[Repository] = None

# PAT scopes required:

# repo     — full repository access (read + write code, PRs, branches)

# workflow — required to commit .github/workflows/ files (CI workflow)

# PAT scopes NOT required (do not request):

# admin:org, delete_repo, admin:repo_hook

## 3.2 v2 — GitHub App (Upgrade Path)

GitHub App authentication replaces PAT in v2. The app is registered once by YouSource.ai. Users install the app to their org/repo via GitHub UI. JWT generation flow:

# 1. Generate JWT using App private key (from Keychain)

# 2. GET /app/installations → find installation_id for this repo

# 3. POST /app/installations/{installation_id}/access_tokens

# 4. Response: {"token": "ghs_...", "expires_at": "2026-03-19T16:00:00Z"}

# 5. Use token as Bearer auth for all API calls

# 6. Refresh when expires_at - now < 5 minutes

TOKEN_REFRESH_BUFFER_SEC = 300  # Refresh 5 minutes before expiry

# 4. GitHubTool Public API

## 4.1 File Operations

Method | Signature | Description
get_file | get_file(path, branch=None) → str | Read a file from the repo. ref defaults to config.default_branch. Returns decoded UTF-8 content. Raises GitHubToolError if not found.
commit_file | commit_file(branch, path, content, message) → None | Create or update a file on a branch. Detects create vs update via existing SHA. All inputs validated before API call.
download_file | download_file(repo_path, local_path, branch=None) → bool | Download a repo file to local disk. Creates parent directories. Returns False on failure (non-fatal).
list_files | list_files(directory='', branch=None) → list[str] | List files in a directory (non-recursive). Returns file path strings.
list_files_recursive | list_files_recursive(directory='', branch=None) → list[str] | Recursively list all file paths under a directory. Sorted. Used by repo context fetcher.

## 4.2 Branch Operations

Method | Signature | Description
create_branch | create_branch(branch_name) → None | Create a new branch off default_branch. Idempotent — if branch already exists, logs and returns. All branch names validated via validate_branch_name().

## 4.3 Pull Request Operations

Method | Signature | Description
create_pr | create_pr(branch, title, body) → PRResult | Open a draft PR from branch → default_branch. Returns PRResult with pr_number, pr_url, branch, title. On 422 (PR already exists), finds and returns the existing open PR (idempotent).

## 4.4 PRResult Dataclass

@dataclass

class PRResult:

pr_number: int     # GitHub PR number

pr_url:    str     # Full PR URL (html_url)

branch:    str     # Source branch

title:     str     # PR title

# 5. Rate Limiting

## 5.1 Primary Rate Limits

GitHub's primary rate limit is 5,000 requests/hour for authenticated users. The agent's typical build makes 200–400 API calls (most are file commits and PR status checks). Primary limits are rarely hit in practice.

## 5.2 Secondary Rate Limits

GitHub fires secondary rate limits when many write requests arrive in a short window. This is the most common source of 403 errors during active builds. All mutating GitHub calls go through _gh_retry():

_GH_RETRY_MAX     = 6          # max attempts

_GH_RETRY_BASE    = 2.0        # seconds; doubles each attempt (2 4 8 16 32 64)

_GH_RETRY_CODES   = {403, 429} # HTTP status codes that warrant a retry

# Retry-After header honored first if present.

# Falls back to exponential backoff: 2s → 4s → 8s → 16s → 32s → 64s

All write operations (commit_file, create_branch, create_pr) go through _gh_retry(). Read operations do not — they are low-risk and retry handling adds latency.

# 6. Input Validation

## 6.1 Path Validation

All file paths passed to commit_file() and get_file() are validated via path_security.validate_commit_path() before any API call. Validation rejects: path traversal (../), absolute paths, null bytes, control characters, and paths outside allowed directories. On rejection, raises GitHubToolError.

## 6.2 Branch Name Validation

All branch names passed to create_branch(), commit_file(), and create_pr() are validated via path_security.validate_branch_name() before any API call. Validation rejects: empty strings, spaces, colons, semicolons, shell metacharacters, and names exceeding 250 characters. Long names are truncated by the validator.

## 6.3 Commit Message Validation

commit_file() rejects empty commit messages with a GitHubToolError. PR titles are also validated as non-empty. Neither field has length caps — GitHub itself imposes reasonable limits.

# 7. PR Lifecycle

## 7.1 Standard Lifecycle

Step | GitHub Operation | Notes
1 | create_branch(branch_name) | Idempotent — reuses existing branch if present
2 | commit_file() — implementation | Impl file committed to feature branch
3 | commit_file() — test file | Test file committed to feature branch
4 | create_pr(branch, title, body) | Draft PR opened; returns PRResult with pr_number
5 | ci_checker.wait_for_ci(branch, pr_number) | Polls CI until pass, fail, or timeout (15 min default)
6 | mark_ready_for_review() (via PR update) | Draft → ready after CI passes

## 7.2 422 Recovery

If create_pr() receives HTTP 422 (PR already exists for this branch), the agent recovers by searching for the existing open PR on that branch and using its pr_number. This is transparent idempotency — resume behaves identically to first run regardless of whether the PR was already opened in a prior session.

# 8. CI Gate — CIChecker

## 8.1 Overview

CIChecker polls the GitHub Checks API until all required checks complete. Implemented in ci_checker.py. Uses exponential backoff to avoid hammering the API.

Parameter | Value | Description
CI_TIMEOUT_SEC | 900 (15 min) | Default timeout for CI completion
CI_POLL_START_SEC | 10 | Initial poll interval
CI_POLL_MAX_SEC | 60 | Maximum poll interval (caps the backoff)
Backoff | 10s → 20s → 40s → 60s (cap) | Doubles until cap is reached

## 8.2 CIResult Dataclass

@dataclass

class CIResult:

passed:         bool

branch:         str

checks_passed:  list[str]   # Names of passed checks

checks_failed:  list[str]   # Names of failed checks

checks_pending: list[str]   # Names of still-running checks

duration_sec:   float

timed_out:      bool = False

error:          Optional[str] = None

## 8.3 Check Evaluation

The checker skips checks that are queued or in_progress (keeps waiting). Returns True only when all checks are completed and passed. If any check fails, returns False with the failed check names for diagnosis. If timeout is reached before all checks complete, returns False with timed_out=True.

# 9. CI Workflow Management

## 9.1 crafted-ci.yml

ci_workflow.py manages the GitHub Actions workflow files. crafted-ci.yml is created on the default branch when the first build starts. It runs pytest on ubuntu-latest for all Python/Go/TypeScript PRs.

The workflow uses paths-ignore to skip non-code files (documentation PRs). See TRD-14 §5b for the complete paths-ignore configuration. Key CI hardening features:

PYTHONPATH set at job level for all steps

Concurrency: cancel-in-progress=true (prevents stale CI from older pushes)

permissions: {} at workflow level, contents: read at job level (least privilege)

pip caching keyed on requirements.txt

Exit code 5 (no tests collected) treated as success for test-only PRs

## 9.2 crafted-ci-macos.yml

When Swift is detected in the build, a separate macOS workflow is created. It uses the self-hosted Mac runner (TRD-9) and runs xcodebuild to build and test Swift code. Triggered only on paths: ["Crafted/**", ...] rather than paths-ignore.

## 9.3 Workflow Lifecycle

ensure() writes the workflow only when it does not already exist. force_update() unconditionally rewrites it (used after major CI fixes). Both methods call _ensure_conftest() to commit conftest.py for src/ import resolution. validate_and_repair() detects and repairs placeholder corruption (literal {setup_block} in committed YAML).

# 10. Repository Bootstrap

## 10.1 Purpose

RepoBootstrap runs once on first use to set up the repository structure for the agent. It is not called during normal builds — only when the repo is freshly created or the /bootstrap command is issued.

## 10.2 Bootstrap Steps

Step | Operation | Description
1 | Upload source documents | All .docx TRD/PRD files from Mac-Docs/ committed to forge-docs/ on main
2 | Generate supporting docs | Forge engineering standards, architecture context documents generated and committed
3 | Generate CLAUDE.md / AGENTS.md | Repo-level agent context files generated using consensus AI
4 | Generate README.md | Project README generated from loaded TRD content

Bootstrap is idempotent — it checks a hash of the uploaded documents and skips the upload if unchanged. Each subsequent sync only re-uploads documents that have changed.

# 11. PR Review Ingestion

After CI passes, the agent scans open PR review comments for feedback from human reviewers. Implemented in pr_review_ingester.py. If blocking feedback is found, it is fed into the failure handler as a special failure type, which triggers a targeted fix without running the full test suite again.

This enables async human-in-the-loop review: the agent continues building other PRs while CI runs, then handles reviewer feedback if present when it checks back in.

# §5a. PR Lifecycle Routing by Type (New in v1.1)

## Overview

PRSpec now carries a pr_type field ("implementation", "documentation", or "test") that determines which GitHub operations are performed. GitHubTool itself is not aware of pr_type — it executes whatever operations are requested. The routing logic lives in build_director.py. This section documents the operational consequences for each type.

## Operation Matrix by PR Type

GitHub Operation | implementation | documentation | test
create_branch() | Yes
commit_file() — impl | Yes | Yes (markdown/yaml/json) | No (impl IS test)
commit_file() — test | Yes | No | Yes
create_pr() (draft) | Yes
CI gate wait (ci_checker) | Yes — blocks on pass/fail | No — skipped entirely | Yes — waits after deps merge
mark_ready_for_review() | Yes — after CI passes | Yes — immediately after commit | Yes — after CI passes

## Documentation PRs and CI

Documentation PRs commit only non-code files (.md, .yaml, .json, etc.). The CI workflow (crafted-ci.yml) uses paths-ignore to exclude these file types from triggering the test job. A PR that only changes non-code files never triggers CI — it passes automatically. The agent marks them ready immediately after the commit succeeds.

## Test-only PRs and CI

Test-only PRs contain test files that import from other PRs' code. Those dependencies don't exist on the test PR's branch until the dependency PRs are merged to main. The agent commits the test file, opens the PR, and skips the local test loop. CI runs automatically after the PR is opened — it will fail until dependency PRs are merged. This is expected and correct. The PR is marked ready for review immediately; merging is a manual operator decision after dependencies are confirmed merged.

## 422 Recovery (from TRD-13 §8.4)

When create_pr() returns 422 (PR already exists for this branch), the agent recovers by searching for the existing open PR on that branch and using its number. This applies to all three pr_type values. The result is transparent idempotency — resume behaves identically to first run regardless of whether the PR was already opened in a prior session.

# 12. Acceptance Criteria

All mutating GitHub operations go through _gh_retry() with exponential backoff

Retry-After header honored on rate limit responses before falling back to backoff

All file paths validated via path_security.validate_commit_path() before API call

All branch names validated via path_security.validate_branch_name() before API call

create_branch() is idempotent — reuses existing branch without error

create_pr() is idempotent on 422 — finds and returns existing PR

CIChecker polls with exponential backoff up to 15 minute timeout

crafted-ci.yml created only when not already present (ensure is idempotent)

validate_and_repair() detects and fixes placeholder corruption in committed YAML

Repository bootstrap is idempotent — skips unchanged documents

# Appendix: Document Change Log

Version | Date | Changes
1.0 | 2026-03-19 | Initial specification — GitHubTool API, authentication (PAT v1, App v2), branch namespace, PR lifecycle, rate limiting, CI workflow, webhook receiver, repository bootstrap
1.1 | 2026-03-22 | PR lifecycle routing by type (§5a) — documents how spec.pr_type affects GitHub operation sequencing for implementation, documentation, and test-only PRs.