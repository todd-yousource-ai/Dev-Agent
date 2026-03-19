# TRD-5-GitHub-Integration

_Source: `TRD-5-GitHub-Integration.docx` — extracted 2026-03-19 23:49 UTC_

---

TRD-5

GitHub Integration Layer

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-5: GitHub Integration Layer
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (Keychain — token storage), TRD-3 (path_security — commit path validation)
Required by | TRD-3 (pipeline uses GitHubTool for all repo ops), TRD-4 (ledger uses commit_file + get_file_with_sha)
Language | Python 3.12
Auth (v1) | Personal Access Token stored in macOS Keychain
Auth (v2) | GitHub App — JWT + installation token (upgrade path, not shipped in v1)

# 1. Purpose and Scope

This document specifies the complete technical requirements for the GitHub Integration Layer — all communication between the Consensus Dev Agent and GitHub repositories.

The Layer owns:

Authentication — PAT (v1) and GitHub App JWT/installation tokens (v2 upgrade path)

GitHubTool — the single Python class through which all GitHub operations flow

File commit protocol — path validation, encoding, size limits, SHA-based updates

Branch namespace — naming convention, validation, creation, deletion

PR lifecycle — open draft, commit files, CI gate, mark ready, merge

Rate limiting — primary and secondary limit handling, backoff, ETag caching

GraphQL API — rich PR status queries (v2, available in v1 as optional enhancement)

Webhook receiver — check_run, pull_request, push events from GitHub

CI workflow — forge-ci.yml management, language detection, force_update

PR review ingestion — scan comments, feed to failure handler

Repository bootstrap — first-use setup of forge-docs/, AGENTS.md, CI

SCOPE | TRD-5 specifies the GitHub interface only. Build state management is TRD-3. Ledger coordination is TRD-4. Secret storage is TRD-1. Path security for commit paths delegates to path_security.py.

# 2. Design Decisions

Decision | Choice | Rationale
Auth in v1 | Personal Access Token (PAT) from Keychain | Already implemented and working. GitHub App migration is a clean upgrade path — same API, different token source.
Auth in v2 | GitHub App with JWT + installation tokens | Apps have scoped per-repo permissions, auto-expiring tokens, and audit trails showing "Forge Agent" not a username.
REST vs GraphQL | REST for all writes; GraphQL optional for rich reads | GitHub's GraphQL API does not support mutations for most write operations. REST is required for commits, PRs, merges. GraphQL is additive for status queries.
PyGithub vs raw requests | PyGithub for v1; migrate to raw httpx in v2 | PyGithub is well-tested and handles pagination, retries, and rate limits. Raw requests give more control for GitHub App JWT flows.
Webhook delivery | ngrok (dev) or GitHub App webhook URL (prod) | No inbound ports on the developer machine. ngrok tunnels the webhook to localhost. GitHub App provides a stable webhook URL.
CI polling vs webhook | Poll as primary, webhook as enhancement | Polling works without webhook infrastructure. Webhook reduces CI wait time from 30s average to < 5s.

# 3. Authentication

## 3.1 v1 — Personal Access Token

# PAT is stored in macOS Keychain (TRD-1 Section 5)
# Retrieved at backend startup via XPC credential delivery
# Passed to GitHubTool at construction time — never re-fetched

class GitHubTool:
    def __init__(
        self,
        token:         str,    # PAT from Keychain via XPC delivery
        owner:         str,    # Repository owner (org or user)
        repo:          str,    # Repository name
        default_branch: str = "main",
    ) -> None:
        from github import Github
        self._gh      = Github(token)
        self._repo    = self._gh.get_repo(f"{owner}/{repo}")
        self._owner   = owner
        self._repo_name = repo
        self._default_branch = default_branch
        self._token   = token   # Kept for raw API calls not in PyGithub

# PAT scopes required:
#   repo        — full repository access (read + write code, PRs, branches)
#   workflow    — required to commit .github/workflows/ files (CI workflow)

# PAT scopes NOT required (do not request):
#   admin:org, delete_repo, admin:repo_hook

## 3.2 v2 — GitHub App (Upgrade Path)

# GitHub App authentication replaces PAT in v2.
# The app is registered once by YouSource.ai.
# Users install the app to their org/repo via GitHub UI.
# No personal tokens — users never handle credentials.

# JWT generation (used to get installation tokens):
import jwt, time

def _generate_app_jwt(app_id: str, private_key_pem: str) -> str:
    """Generate a GitHub App JWT valid for 10 minutes."""
    now = int(time.time())
    payload = {
        "iat": now - 60,        # Issued at (60s in past — clock skew)
        "exp": now + 600,       # Expires in 10 minutes (GitHub max)
        "iss": app_id,          # App ID from GitHub App settings
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


# Installation token flow:
# 1. Generate JWT using App private key (from Keychain)
# 2. GET /app/installations → find installation_id for this repo
# 3. POST /app/installations/{installation_id}/access_tokens
# 4. Response: {"token": "ghs_...", "expires_at": "2026-03-19T16:00:00Z"}
# 5. Use token as Bearer auth for all API calls
# 6. Refresh when expires_at - now < 5 minutes

# Token storage: in-memory only — never written to disk or Keychain.
# The App private key IS stored in Keychain (SecretKey.githubAppPrivateKey).

TOKEN_REFRESH_BUFFER_SEC = 300   # Refresh 5 minutes before expiry

## 3.3 Auth Mode Detection

# GitHubTool detects auth mode from credential delivery payload:

# PAT mode (v1):
# XPC payload has "github_token" field → use PAT

# App mode (v2):
# XPC payload has "github_app_id" + "github_app_private_key" fields → use App

# Both modes expose identical GitHubTool public API.
# Auth mode is an implementation detail — callers do not need to know.

# 4. GitHubTool Public API

## 4.1 File Operations

class GitHubTool:

    def commit_file(
        self,
        branch:  str,
        path:    str,
        content: str,
        message: str,
        sha:     Optional[str] = None,  # Required for update; None for create
    ) -> str:
        """
        Create or update a file in the repository.
        Returns the new file SHA.
        Raises GitHubToolError on failure.
        path is validated via path_security.validate_commit_path() before use.
        content is encoded as UTF-8 → base64 before API call.
        """

    def get_file(self, path: str, ref: str = None) -> str:
        """
        Read a file from the repository.
        ref: branch name, tag, or commit SHA. Defaults to default branch.
        Returns decoded UTF-8 content.
        Raises GitHubToolError if file not found.
        """

    def get_file_with_sha(self, path: str, ref: str = None) -> tuple[str, str]:
        """
        Read a file and return (content, sha).
        sha is used as optimistic lock for subsequent commit_file calls.
        """

    def get_file_sha(self, path: str, ref: str = None) -> str:
        """Return only the file SHA without fetching content."""

    def file_exists(self, path: str, ref: str = None) -> bool:
        """Return True if file exists in the repository."""

    def list_files_recursive(
        self,
        directory: str,
        ref:       str = None,
    ) -> list[str]:
        """
        List all file paths under a directory recursively.
        Returns list of relative paths from repo root.
        Returns empty list if directory does not exist.
        """

## 4.2 Branch Operations

def create_branch(self, branch: str, from_ref: str = None) -> None:
        """
        Create a branch from from_ref (default: current default branch HEAD).
        branch is validated via path_security.validate_branch_name().
        No-op if branch already exists.
        """

    def branch_exists(self, branch: str) -> bool:
        """Return True if branch exists in repository."""

    def create_branch_if_not_exists(
        self,
        branch:   str,
        from_ref: str = None,
    ) -> bool:
        """Create branch if it does not exist. Returns True if created."""

    def delete_branch(self, branch: str) -> None:
        """
        Delete a branch.
        Raises GitHubToolError if branch is protected or does not exist.
        Never deletes branches matching: main, master, develop, or default_branch.
        """

    def get_default_branch(self) -> str:
        """Return the repository default branch name."""

## 4.3 Pull Request Operations

def open_draft_pr(
        self,
        title:  str,
        body:   str,
        head:   str,         # Source branch
        base:   str = None,  # Target branch — defaults to default_branch
    ) -> tuple[int, str]:
        """
        Open a draft pull request.
        Returns (pr_number, pr_url).
        Raises GitHubToolError if branch has no commits ahead of base.
        """

    def mark_ready_for_review(self, pr_number: int) -> None:
        """Convert draft PR to ready-for-review."""

    def merge_pr(
        self,
        pr_number:     int,
        merge_method:  str = "squash",   # "squash" | "merge" | "rebase"
        commit_title:  Optional[str] = None,
    ) -> None:
        """Merge a pull request. Never called automatically — operator gates merge."""

    def get_pr_state(self, pr_number: int) -> dict:
        """
        Return PR state dict:
        { "number": N, "state": "open"|"closed"|"merged",
          "draft": bool, "mergeable": bool|null,
          "reviews": [...], "check_runs": [...] }
        """

    def get_pr_reviews(self, pr_number: int) -> list[dict]:
        """Return list of review objects for a PR."""

    def get_pr_review_comments(self, pr_number: int) -> list[dict]:
        """Return list of inline review comments (file + line + body)."""

    def submit_pr_review(
        self,
        pr_number: int,
        body:      str,
        event:     str = "COMMENT",   # "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
    ) -> None:
        """Submit a review on a PR."""

## 4.4 CI Operations

def get_check_runs(self, ref: str) -> list[dict]:
        """
        Return check runs for a commit ref (branch name or SHA).
        Each dict: { "name", "status", "conclusion", "url" }
        status: "queued" | "in_progress" | "completed"
        conclusion: "success" | "failure" | "cancelled" | "skipped" | None
        """

    def wait_for_ci(
        self,
        branch:          str,
        timeout_sec:     int = 1800,
        poll_interval:   int = 30,
        webhook_event:   Optional[asyncio.Event] = None,
    ) -> "CIResult":
        """
        Poll for CI completion on a branch.
        If webhook_event is provided: wait for webhook signal first,
        fall back to polling if no signal within 60 seconds.
        Returns CIResult(passed: bool, failure_summary: str).
        Raises GitHubToolError on timeout.
        """

## 4.5 Repository Operations

def get_repo_info(self) -> dict:
        """Return { "default_branch", "private", "language", "topics" }"""

    def get_languages(self) -> dict[str, int]:
        """Return language breakdown: {"Python": 12345, "Go": 4321, ...}"""

    def check_branch_protection(self, branch: str) -> bool:
        """Return True if branch has protection rules enabled."""

    def get_latest_commit_sha(self, branch: str) -> str:
        """Return HEAD SHA of a branch."""

# 5. File Commit Protocol

## 5.1 Path Validation

# ALL paths passed to commit_file() must be validated before the API call.
# This is enforced inside commit_file() — callers cannot bypass it.

from path_security import validate_commit_path

def commit_file(self, branch, path, content, message, sha=None):
    # Validate path FIRST — before any other processing
    safe_path = validate_commit_path(path, context="GitHubTool.commit_file")
    if not safe_path:
        raise PathSecurityError(f"Unsafe commit path rejected: {path!r}")
    # Use safe_path from here — never the original path
    ...

## 5.2 Content Encoding

# GitHub API requires base64-encoded content.
# For text files: UTF-8 → bytes → base64.
# For binary files: raw bytes → base64.

import base64

def _encode_content(content: str) -> str:
    """Encode text content for GitHub file API."""
    return base64.b64encode(content.encode("utf-8")).decode("ascii")

def _encode_binary(data: bytes) -> str:
    """Encode binary content for GitHub file API."""
    return base64.b64encode(data).decode("ascii")

## 5.3 File Size Limits

Limit | Value | Behavior on Exceed
GitHub API per-file limit | 1 MB (1,048,576 bytes) | Warn in chat; truncate to limit; log warning
Practical limit for text files | 500 KB | No truncation; advisory warning in UI
Binary files (docx) | 1 MB | Raise GitHubToolError if exceeded — binary cannot be truncated
Ledger JSON file | 500 KB target | Log warning if exceeded; no truncation (ledger integrity)

MAX_FILE_BYTES = 1_048_576   # 1 MB — GitHub API limit

def _check_size(content: str, path: str) -> str:
    """Check content size and warn/truncate if needed."""
    size = len(content.encode("utf-8"))
    if size > MAX_FILE_BYTES:
        logger.warning(f"File {path} is {size:,} bytes — truncating to {MAX_FILE_BYTES:,}")
        # Truncate at a UTF-8 boundary
        encoded = content.encode("utf-8")[:MAX_FILE_BYTES]
        return encoded.decode("utf-8", errors="ignore")
    return content

## 5.4 Commit Message Format

# All agent commits follow this format:
# "forge-agent[{engineer_id}]: {message}"

# Examples:
# "forge-agent[todd-gould]: PRD-003 — Transaction Idempotency Layer"
# "forge-agent[todd-gould]: PR007 implement idempotency key expiry"
# "forge-ledger[sara-chen]: claim PR #8"
# "forge-agent: add CI workflow"   (for bootstrap — no engineer_id yet)

# This format makes agent commits visually distinct in git log.
# The [engineer_id] bracket identifies who triggered the commit.

## 5.5 SHA-Based Update Protocol

# For commit_file updates (not creates), the file SHA is required.
# Missing SHA → GitHub creates a duplicate file (same path, different oid).
# Wrong SHA → GitHub rejects with 422 Unprocessable Entity.

# The GitHubTool resolves SHA automatically when sha=None:
def commit_file(self, branch, path, content, message, sha=None):
    safe_path = validate_commit_path(path, context="commit_file")
    if not safe_path:
        raise PathSecurityError(f"Unsafe path: {path!r}")

    encoded = _encode_content(_check_size(content, path))

    # Auto-fetch SHA if not provided
    if sha is None:
        try:
            _, sha = self.get_file_with_sha(safe_path, ref=branch)
        except GitHubToolError:
            sha = None  # File does not exist yet — create

    params = {
        "message": message,
        "content": encoded,
        "branch":  branch,
    }
    if sha:
        params["sha"] = sha

    return self._repo.create_file(safe_path, **params)

# 6. Branch Namespace Protocol

## 6.1 Naming Convention

Branch Type | Pattern | Example
Code (PR implementation) | forge-agent/build/{engineer_id}/{subsystem_slug}-pr{NNN}-{title_slug} | forge-agent/build/todd-gould/payments-pr007-add-idempotency-key-expiry
PRD storage | forge-agent/build/{engineer_id}/{subsystem_slug}/prds | forge-agent/build/todd-gould/payments/prds
Default branch | main (or repo default) | main — NEVER written by agent directly
Protected branches | main, master, develop, release/* | Agent must detect and refuse to write

## 6.2 Slug Generation

import re

def _slug(text: str, max_len: int = 40) -> str:
    """Convert text to URL-safe slug for branch names."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:max_len].strip("-")

# PR branch formula:
def pr_branch_name(
    engineer_id:    str,
    subsystem:      str,
    pr_num:         int,
    pr_title:       str,
) -> str:
    subsystem_slug = _slug(subsystem, max_len=20)
    title_slug     = _slug(pr_title,  max_len=40)
    branch = f"forge-agent/build/{engineer_id}/{subsystem_slug}-pr{pr_num:03d}-{title_slug}"
    # Validate before returning
    from path_security import validate_branch_name
    safe = validate_branch_name(branch, context="pr_branch_name")
    if not safe:
        raise ValueError(f"Generated branch name failed validation: {branch!r}")
    return safe

# Max total branch length: ~120 chars
# Git supports 255 but GitHub UI truncates at 100

## 6.3 Protected Branch Detection

PROTECTED_BRANCH_PATTERNS = [
    "main", "master", "develop", "development",
    "release", "production", "prod", "staging",
]

def _is_protected_branch(branch: str, default_branch: str) -> bool:
    """Return True if branch should never be written by the agent."""
    if branch == default_branch:
        return True
    base = branch.split("/")[0].lower()
    return base in PROTECTED_BRANCH_PATTERNS

# commit_file checks this before any write:
if _is_protected_branch(branch, self._default_branch):
    raise GitHubToolError(
        f"Cannot write to protected branch: {branch!r}. "
        "Agent branches must start with forge-agent/build/."
    )

## 6.4 Branch Deletion

# Branch deletion after PR merge is configurable:
# UserDefaults key: "delete_branch_after_merge" (bool, default: True)

# delete_branch() enforces protection:
def delete_branch(self, branch: str) -> None:
    if _is_protected_branch(branch, self._default_branch):
        raise GitHubToolError(f"Cannot delete protected branch: {branch!r}")
    if not branch.startswith("forge-agent/"):
        raise GitHubToolError(
            f"Agent will only delete branches under forge-agent/: {branch!r}"
        )
    try:
        ref = self._repo.get_git_ref(f"heads/{branch}")
        ref.delete()
    except Exception as e:
        raise GitHubToolError(f"Branch deletion failed: {e}") from e

# 7. PR Lifecycle

## 7.1 Sequence

PR LIFECYCLE

Stage 5 (CodeGenerationStage)
  │
  ├── create_branch_if_not_exists(pr_branch, from_ref=default_branch)
  ├── commit_file(pr_branch, impl_path, impl_code)
  └── commit_file(pr_branch, test_path, test_code)
       │
Stage 6 (ThreePassReviewStage)
  ├── Possibly updates impl_code after review passes
  └── commit_file(pr_branch, impl_path, reviewed_code)  ← if changed
       │
Stage 7 (TestStage)
  ├── Tests run locally — no GitHub interaction
  └── On local pass: checkpoint saved
       │
Stage 8 (CIGate)
  ├── open_draft_pr(title, body, head=pr_branch, base=default_branch)
  │     → returns (pr_number, pr_url)
  ├── CI triggers automatically from GitHub Actions
  ├── wait_for_ci(pr_branch, timeout_sec=1800)
  │     → polls get_check_runs() or waits for webhook signal
  ├── On CI pass: mark_ready_for_review(pr_number)
  └── PR ready — operator reviews and merges via GitHub UI or /merge command

Post-merge (optional):
  └── delete_branch(pr_branch)  [if delete_branch_after_merge=True]

## 7.2 Draft PR Requirement

# ALL PRs opened by the agent are drafts.
# Draft PRs do not request reviews and do not trigger auto-merge rules.
# Draft is removed only when local tests AND CI both pass.

# open_draft_pr uses GitHub's draft PR API:
# POST /repos/{owner}/{repo}/pulls
# { "title": "...", "body": "...", "head": "...", "base": "...", "draft": true }

# If repository does not support draft PRs (requires GitHub Pro/Team/Enterprise):
# Fall back to regular PR with "[DRAFT]" prefix in title.
# Log warning and continue.

# 8. PR Description Format

def build_pr_description(spec: "PRSpec", consensus: "ConsensusResult") -> str:
    """Build structured GitHub PR description."""
    criteria = chr(10).join(
        f"- [ ] {c}" for c in spec.acceptance_criteria
    ) or "- [ ] All tests pass"
    files = ", ".join(spec.impl_files)
    sec_flag = "Yes 🔒" if spec.security_critical else "No"

    return f"""## {spec.title}

{spec.description_md}

### Acceptance Criteria
{criteria}

### Implementation
**Files:** {files}
**Language:** {spec.language}  **Framework:** {spec.framework}
**Security critical:** {sec_flag}

### Test Plan
**Test files:** {", ".join(spec.test_files)}

---
_Generated by Consensus Dev Agent_
_Winner: {consensus.winner_provider.title()} ({consensus.scoring.claude_score}/10 Claude
 vs {consensus.scoring.openai_score}/10 GPT-4o)_
_Rationale: {consensus.scoring.rationale}_
_Cost: ${consensus.total_cost_usd:.3f} | Tokens: {consensus.total_input_tokens:,} | Time: {consensus.total_duration_sec:.1f}s_
_Review passes applied: {consensus_result.review_passes_applied}_
_This PR was opened as a draft. It will be marked ready once local tests pass and CI is green._
"""

# 9. Rate Limiting and Retry

## 9.1 GitHub Rate Limit Types

Type | Limit (PAT) | Limit (App) | Reset | Action on Hit
Primary (REST) | 5,000 req/hr | 15,000 req/hr | Hourly | Wait until reset + jitter; emit warning card
Primary (GraphQL) | 5,000 points/hr | 15,000 points/hr | Hourly | Same as REST
Secondary (concurrent) | Unspecified — abuse detection | Same | Immediate | Exponential backoff up to 60s
Secondary (creation) | Unspecified — burst detection | Same | Short | Exponential backoff
Search API | 30 req/min | Per minute | Wait 60s + retry

## 9.2 Retry Implementation

_GH_RETRY_MAX   = 5
_GH_RETRY_BASE  = 1.0   # seconds — doubles each retry
_GH_RETRY_MAX_WAIT = 60.0

def _with_retry(self, fn: Callable, *args, **kwargs):
    """
    Execute a GitHub API call with retry on transient errors.
    Handles: rate limits (429), server errors (5xx), connection errors.
    Does NOT retry: 4xx client errors (except 429 and 422-SHA).
    """
    import time, random
    for attempt in range(_GH_RETRY_MAX):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            error_str = str(exc)
            status = getattr(exc, "status", 0)

            # Primary rate limit (403 with rate limit message, or 429)
            if status in (403, 429) and "rate limit" in error_str.lower():
                reset_at = self._get_rate_limit_reset()
                wait = max(0, reset_at - time.time()) + random.uniform(1, 5)
                logger.warning(f"Primary rate limit — waiting {wait:.0f}s")
                self._emit_warning(f"GitHub rate limit — pausing {wait:.0f}s")
                time.sleep(wait)
                continue

            # Secondary rate limit (403 with abuse message)
            if status == 403 and "secondary" in error_str.lower():
                retry_after = self._get_retry_after_header(exc)
                wait = retry_after or (_GH_RETRY_BASE * (2 ** attempt))
                wait = min(wait, _GH_RETRY_MAX_WAIT)
                logger.warning(f"Secondary rate limit — waiting {wait:.0f}s")
                time.sleep(wait)
                continue

            # Server errors (5xx) — retry with backoff
            if 500 <= status < 600:
                wait = _GH_RETRY_BASE * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"GitHub 5xx error ({status}) — retry {attempt+1}")
                time.sleep(wait)
                continue

            # SHA conflict (422) — caller handles, do not retry here
            if status == 422:
                raise GitHubConflictError(str(exc)) from exc

            # Non-retryable — raise immediately
            raise _classify_error(exc) from exc

    raise GitHubRateLimitError(f"GitHub API failed after {_GH_RETRY_MAX} retries")

## 9.3 Conditional Requests (ETag Caching)

# Use ETag + If-None-Match to avoid counting cache hits against rate limit.
# GitHub returns 304 Not Modified when content unchanged — does not count.

_etag_cache: dict[str, tuple[str, Any]] = {}  # url → (etag, response)

def _get_with_etag(self, url: str, headers: dict = None) -> Any:
    """GET with ETag caching. Returns cached response on 304."""
    import requests
    h = dict(headers or {})
    if url in _etag_cache:
        h["If-None-Match"] = _etag_cache[url][0]

    resp = requests.get(url, headers={**self._auth_headers, **h})

    if resp.status_code == 304:
        return _etag_cache[url][1]   # Return cached data

    if "ETag" in resp.headers:
        _etag_cache[url] = (resp.headers["ETag"], resp.json())

    return resp.json()

# Used for: get_check_runs() polling (same branch ref, same CI status)
# Not used for: ledger reads (SHA changes frequently, cache would miss often)

# 10. GraphQL API

## 10.1 Scope

GraphQL is used for rich read queries only — specifically to fetch PR status (reviews + check runs + mergeable state) in a single API call instead of three REST calls. All writes remain on the REST API.

## 10.2 PR Status Query

PR_STATUS_QUERY = """
query GetPRStatus($owner: String!, $repo: String!, $prNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      number
      state
      isDraft
      mergeable
      reviews(last: 10) {
        nodes {
          state
          author { login }
          submittedAt
        }
      }
      commits(last: 1) {
        nodes {
          commit {
            statusCheckRollup {
              state
              contexts(last: 20) {
                nodes {
                  ... on CheckRun {
                    name
                    status
                    conclusion
                    detailsUrl
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

def get_pr_status_graphql(self, pr_number: int) -> dict:
    """
    Fetch PR status using GraphQL — one call instead of three REST calls.
    Falls back to REST on GraphQL error.
    """
    import requests
    resp = requests.post(
        "https://api.github.com/graphql",
        headers={**self._auth_headers, "Content-Type": "application/json"},
        json={"query": PR_STATUS_QUERY,
              "variables": {"owner": self._owner,
                            "repo": self._repo_name,
                            "prNumber": pr_number}},
    )
    data = resp.json()

    # GraphQL errors are in response body — not HTTP status
    if "errors" in data:
        logger.warning(f"GraphQL errors: {data['errors']} — falling back to REST")
        return self.get_pr_state(pr_number)   # REST fallback

    return _parse_graphql_pr_status(data)

## 10.3 GraphQL Error Handling

# GraphQL-specific error handling rules:
#
# 1. HTTP 200 with "errors" in body → log and fall back to REST
# 2. HTTP 4xx/5xx → same retry logic as REST
# 3. "NOT_FOUND" error type → PR does not exist → raise GitHubNotFoundError
# 4. "INSUFFICIENT_SCOPES" → token lacks permissions → raise GitHubPermissionError
#
# GraphQL is ALWAYS optional — if it fails, REST fallback is used.
# Never block the pipeline on a GraphQL error.

# 11. Webhook Receiver

## 11.1 Architecture

# Webhook delivery path:

GitHub → (HTTPS) → Webhook endpoint
                        │
              Development: ngrok tunnel
                   ngrok → localhost:PORT
                        │
              Production: GitHub App webhook URL
                   Cloud relay → local agent via XPC
                        │
                   WebhookReceiver (Python HTTP server)
                        │
                   Parse + verify HMAC
                        │
                   Route to handler
                   ├── push → BuildLedger.refresh()
                   ├── check_run → CIGate.signal()
                   └── pull_request → PRReviewIngester.ingest()

## 11.2 HMAC Verification

# GitHub signs all webhook payloads with HMAC-SHA256.
# The webhook secret is set when registering the webhook.
# Secret stored in Keychain as SecretKey.webhookSecret (TRD-1).

import hmac, hashlib

def _verify_webhook_signature(
    payload: bytes,
    signature_header: str,   # "sha256=abc123..."
    secret: str,
) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[7:]
    actual_sig   = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_sig, actual_sig)

# RULE: Reject any webhook with missing or invalid signature.
# RULE: Use hmac.compare_digest — never == or != for timing-safe comparison.
# RULE: Verify signature BEFORE parsing JSON payload.

## 11.3 Event Routing

GitHub Event | Delivery Condition | Handler | Action
push | Pushed to default branch and forge-docs/BUILD_LEDGER.json in changed files | BuildLedger.refresh() | Force-read ledger, emit ledger_update XPC to Swift UI
check_run | check_run.completed on a forge-agent/build/* branch | CIGate.on_check_run_completed(run) | Signal waiting wait_for_ci() via asyncio.Event
pull_request | pull_request.review_requested or review_submitted | PRReviewIngester.on_review_event(pr) | Queue PR for review ingestion on next /review command
pull_request | pull_request.closed with merged=true | BuildLedger.on_pr_merged(pr_number) | Optional: update ledger if not already marked done
ping | On webhook registration | Log and return 200 | Confirms webhook is active

## 11.4 WebhookReceiver

import asyncio
from aiohttp import web

WEBHOOK_PORT = 9742   # Local port — not exposed to internet

class WebhookReceiver:
    def __init__(self, secret: str, router: "WebhookRouter") -> None:
        self._secret = secret
        self._router = router
        self._app    = web.Application()
        self._app.router.add_post("/webhook", self._handle)

    async def _handle(self, request: web.Request) -> web.Response:
        body = await request.read()
        sig  = request.headers.get("X-Hub-Signature-256", "")
        event = request.headers.get("X-GitHub-Event", "")

        # Verify signature BEFORE any processing
        if not _verify_webhook_signature(body, sig, self._secret):
            logger.warning("Webhook signature verification failed")
            return web.Response(status=401, text="Signature mismatch")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return web.Response(status=400, text="Invalid JSON")

        # Route asynchronously — return 200 immediately
        asyncio.create_task(self._router.route(event, payload))
        return web.Response(status=200, text="ok")

    async def start(self) -> None:
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", WEBHOOK_PORT)
        await site.start()
        logger.info(f"Webhook receiver listening on 127.0.0.1:{WEBHOOK_PORT}")

# 12. CI Workflow Management

## 12.1 Workflow File Location

# Committed to: default branch
# Path: .github/workflows/forge-ci.yml
# Committed by: RepoBootstrap on first build start
# Updated by: force_update() when workflow template changes

WORKFLOW_PATH = ".github/workflows/forge-ci.yml"

## 12.2 Language Detection

def _detect_languages(self) -> list[str]:
    """Detect languages used in the repository for CI configuration."""
    lang_map = self.get_languages()   # {"Python": 12345, "Go": 4321}
    detected = []
    # Order matters: most common first
    if "Python" in lang_map:    detected.append("python")
    if "Go" in lang_map:        detected.append("go")
    if "TypeScript" in lang_map: detected.append("typescript")
    if "JavaScript" in lang_map and "typescript" not in detected:
        detected.append("javascript")
    if "Rust" in lang_map:      detected.append("rust")
    return detected or ["python"]   # Default to Python if no language detected

## 12.3 forge-ci.yml Template

def _build_workflow(languages: list[str], default_branch: str) -> str:
    """Build GitHub Actions workflow YAML."""
    has_python = "python" in languages
    has_go     = "go" in languages
    has_ts     = "typescript" in languages or "javascript" in languages
    has_rust   = "rust" in languages

    return f"""name: Forge CI

on:
  push:
    branches:
      - "{default_branch}"
      - "forge-agent/build/**"
    paths-ignore:
      - "prds/**"
      - "docs/**"
      - "forge-docs/**"
      - "**.md"
      - "**.docx"
  pull_request:
    branches:
      - "{default_branch}"
    paths-ignore:
      - "prds/**"
      - "docs/**"
      - "forge-docs/**"
      - "**.md"
      - "**.docx"

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      {_python_steps() if has_python else ""}
      {_go_steps() if has_go else ""}
      {_ts_steps() if has_ts else ""}
      {_rust_steps() if has_rust else ""}
"""

# Python steps (with graceful skip if no tests):
_PYTHON_STEPS = """
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest pytest-asyncio ruff

      - name: Run Python tests
        run: |
          if [ -d tests/ ] && find tests/ -name "test_*.py" | grep -q .; then
            pytest tests/ -v --tb=short
          else
            echo "No test files found — skipping pytest"
          fi

      - name: Lint (ruff)
        run: ruff check src/ --output-format=github
        if: always()
"""

## 12.4 force_update()

def force_update(self, languages: list[str]) -> bool:
    """
    Unconditionally update the CI workflow.
    Called when the workflow template has been updated (e.g. paths-ignore fix).
    Overwrites any existing workflow.
    Returns True if updated, False on error.
    """
    content = _build_workflow(languages, self._default_branch)
    try:
        self.commit_file(
            branch=self._default_branch,
            path=WORKFLOW_PATH,
            content=content,
            message="forge-agent: update CI workflow",
        )
        logger.info(f"CI workflow updated")
        return True
    except Exception as e:
        logger.warning(f"CI workflow update failed: {e}")
        return False

# 13. PR Review Ingestion

## 13.1 Scan Protocol

# /review command triggers PRReviewIngester.scan_open_prs()
# Scans all open forge-agent/* PRs for unresolved review comments.

class PRReviewIngester:

    def scan_open_prs(self) -> list[dict]:
        """
        Scan open forge-agent/* PRs for review comments.
        Returns list of { pr_number, pr_title, comments: [...] }.
        """
        open_prs = self._github.list_open_prs_for_prefix("forge-agent/build/")
        results  = []

        for pr in open_prs:
            comments = self._github.get_pr_review_comments(pr["number"])
            # Filter: only unresolved comments
            unresolved = [
                c for c in comments
                if not c.get("resolved", False)
                and c.get("user", {}).get("login") != self._engineer_id
            ]
            if unresolved:
                results.append({
                    "pr_number": pr["number"],
                    "pr_title":  pr["title"],
                    "branch":    pr["head"]["ref"],
                    "comments":  unresolved,
                })

        return results

    def format_for_fix_loop(self, review: dict) -> str:
        """Format review comments as context for the consensus fix loop."""
        lines = [
            f"PR #{review['pr_number']}: {review['pr_title']}",
            f"Branch: {review['branch']}",
            "",
            "Review Comments:",
        ]
        for c in review["comments"]:
            path = c.get("path", "?")  
            line = c.get("line", "?")
            body = c.get("body", "?")
            lines.append(f"  [{path}:{line}] {body}")
        return "\n".join(lines)

# 14. Error Taxonomy

## 14.1 Error Hierarchy

class GitHubToolError(Exception):
    """Base class for all GitHub integration errors."""
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status

class GitHubRateLimitError(GitHubToolError):
    """Primary or secondary rate limit hit."""
    pass

class GitHubNotFoundError(GitHubToolError):
    """Resource not found (404)."""
    pass

class GitHubConflictError(GitHubToolError):
    """SHA conflict on file update (422). Caller must re-read SHA and retry."""
    pass

class GitHubPermissionError(GitHubToolError):
    """Insufficient permissions (403, not rate limit)."""
    pass

class GitHubNetworkError(GitHubToolError):
    """Connection timeout, DNS failure, etc."""
    pass

class PathSecurityError(GitHubToolError):
    """Commit path rejected by path_security validation."""
    pass


def _classify_error(exc: Exception) -> GitHubToolError:
    """Convert a PyGithub or requests exception to a typed GitHubToolError."""
    status = getattr(exc, "status", 0)
    msg    = str(exc)
    if status == 404:                              return GitHubNotFoundError(msg, status)
    if status == 422:                              return GitHubConflictError(msg, status)
    if status == 403 and "permission" in msg.lower(): return GitHubPermissionError(msg, status)
    if status in (403, 429):                      return GitHubRateLimitError(msg, status)
    if "timeout" in msg.lower() or "connection" in msg.lower():
                                                   return GitHubNetworkError(msg)
    return GitHubToolError(msg, status)

## 14.2 Error Handling by Caller

Error Type | TRD-3 (Pipeline) Action | TRD-4 (Ledger) Action
GitHubRateLimitError | Emit warning card; wait for retry (handled in _with_retry) | Same — _write_ledger waits for retry
GitHubNotFoundError | Error card; skip this operation (non-fatal for commits) | Return None from _read_raw
GitHubConflictError | Re-read SHA + retry (auto in commit_file for regular files) | Re-read + retry in _write_ledger (up to MAX_WRITE_RETRIES)
GitHubPermissionError | Fatal error card; stop build; prompt to check PAT scopes | Same
GitHubNetworkError | Retry up to _GH_RETRY_MAX; emit warning; continue if non-fatal | Same
PathSecurityError | Fatal — path rejected; emit error card; skip this PR | Fatal — raise immediately

# 15. Repository Bootstrap

## 15.1 When Bootstrap Runs

RepoBootstrap.run() is called on the first build start for a repository — before Stage 1 (ScopeStage). It ensures the repository has the minimum infrastructure for the agent to operate.

## 15.2 Bootstrap Operations

class RepoBootstrap:

    async def run(self) -> None:
        """
        One-time repository setup. Idempotent — safe to call multiple times.
        """
        # 1. Check if already bootstrapped
        if self._github.file_exists("forge-docs/AGENTS.md"):
            logger.info("Repo already bootstrapped — skipping")
            return

        logger.info("Running repository bootstrap...")

        # 2. Create forge-docs/ directory marker
        self._github.commit_file(
            branch=self._github.default_branch,
            path="forge-docs/.gitkeep",
            content="",
            message="forge-agent: initialise forge-docs directory",
        )

        # 3. Commit AGENTS.md — AI agent context document
        self._github.commit_file(
            branch=self._github.default_branch,
            path="forge-docs/AGENTS.md",
            content=self._build_agents_md(),
            message="forge-agent: add AGENTS.md",
        )

        # 4. Commit CI workflow
        languages = self._github.get_languages()
        detected  = self._ci.detect_languages_from_map(languages)
        self._ci.ensure(detected, self._github.default_branch)

        # 5. Check branch protection (warn only)
        if not self._github.check_branch_protection(self._github.default_branch):
            self._emit_card({"card_type":"warning",
                "body": f"Branch {self._github.default_branch!r} has no protection rules. "
                        "Consider enabling required reviews and status checks."})

        logger.info("Bootstrap complete")

    def _build_agents_md(self) -> str:
        return """# Forge Dev Agent

This repository is being developed by the Consensus Dev Agent.
Branch prefix: forge-agent/build/**

Do not modify files on forge-agent/* branches directly.
All changes go through the agent PR process.
"""

# 16. Testing Requirements

## 16.1 Unit Tests

Module | Coverage Target | Critical Test Cases
commit_file | 95% | Path validation rejects unsafe paths; null-byte path rejected; SHA auto-fetched when None; size truncation at 1 MB; commit message format; SHA conflict raises GitHubConflictError
create_branch | 90% | Protected branch detection; branch slug generation; validation of generated name; no-op if exists
delete_branch | 100% | Protected branch rejected; non-forge-agent/ branch rejected; success path
_with_retry | 100% | Primary rate limit: waits for reset; secondary rate limit: exponential backoff; 5xx: retries up to max; 422 SHA: raises immediately; 404: raises immediately
_verify_webhook_signature | 100% | Valid HMAC passes; tampered payload fails; missing signature header fails; timing-safe comparison used
_build_workflow | 90% | paths-ignore present for prds/**, forge-docs/**; python steps included when python detected; graceful skip when no tests; language detection from repo stats
_classify_error | 100% | All status codes map to correct subtype; non-status exceptions map to NetworkError or base
pr_branch_name | 100% | slug truncation; special chars removed; validation passes on output; engineer_id injected
build_pr_description | 90% | All fields present; consensus attribution included; cost/token stats formatted
_detect_and_handle_dead_agents (via TRD-4) | (tested in TRD-4) | —

## 16.2 Mock GitHub for Testing

# tests/mock_github.py

class MockGitHubTool:
    """
    In-memory mock for GitHubTool.
    Used by TRD-3 and TRD-4 unit tests to avoid real GitHub API calls.
    """

    def __init__(self) -> None:
        self._files:    dict[str, tuple[str, str]] = {}  # path → (content, sha)
        self._branches: set[str] = {"main"}
        self._prs:      dict[int, dict] = {}
        self._sha_counter = 0

    def commit_file(self, branch, path, content, message, sha=None) -> str:
        from path_security import validate_commit_path
        safe = validate_commit_path(path)
        if not safe: raise PathSecurityError(f"Unsafe: {path!r}")
        if sha and self._files.get(path, (None, None))[1] != sha:
            raise GitHubConflictError("SHA mismatch")
        self._sha_counter += 1
        new_sha = f"sha-{self._sha_counter}"
        self._files[path] = (content, new_sha)
        return new_sha

    def get_file_with_sha(self, path, ref=None) -> tuple[str, str]:
        if path not in self._files:
            raise GitHubNotFoundError(f"Not found: {path}")
        return self._files[path]

    def get_file(self, path, ref=None) -> str:
        return self.get_file_with_sha(path, ref)[0]

    def file_exists(self, path, ref=None) -> bool:
        return path in self._files

    def create_branch(self, branch, from_ref=None) -> None:
        self._branches.add(branch)

    def branch_exists(self, branch) -> bool:
        return branch in self._branches

    def open_draft_pr(self, title, body, head, base=None) -> tuple[int, str]:
        pr_num = len(self._prs) + 1
        self._prs[pr_num] = {"number": pr_num, "title": title,
                              "state": "open", "draft": True}
        return pr_num, f"https://github.com/mock/repo/pull/{pr_num}"

    # ... additional mock methods as needed

# 17. Performance Requirements

Operation | Target (p50) | Target (p95) | Notes
commit_file (create) | < 2s | < 5s | GitHub API write latency
commit_file (update, no conflict) | < 2s | < 5s | Includes SHA auto-fetch
commit_file (update, 1 conflict) | < 6s | < 10s | Includes re-read + retry
get_file | < 1s | < 3s | GitHub API read
create_branch | < 2s | < 5s | 
open_draft_pr | < 3s | < 8s | 
mark_ready_for_review | < 2s | < 5s | 
get_check_runs (cached) | < 50ms | < 100ms | ETag cache hit
get_check_runs (miss) | < 1s | < 3s | 
wait_for_ci (CI takes 3 min) | 180s + polling overhead | 180s + 30s | Polling at 30s interval
wait_for_ci (with webhook) | ~5s after CI completes | ~10s | Webhook signal replaces polling
list_files_recursive | < 3s per 100 files | < 10s | Used for doc sync

# 18. Out of Scope

Feature | Reason | Target
GitHub Enterprise | Different base URL — same API. Add base_url param in v2. | v2
GitLab / Bitbucket | Different APIs entirely. Would require separate integration layer. | Never
Git operations (clone, push, pull) | All file operations go through GitHub API. No local git required. | Never
Automatic merge without approval | Core product principle. Operator always merges. | Never
PR auto-assignment to reviewers | Out of scope — agent is not a team coordinator. | v2 if requested
GitHub Projects integration | No integration with GitHub Projects/Boards. | TBD
GitHub Discussions | Not relevant to code generation workflow. | Never
Webhook secret rotation | Manual process — update in Settings and re-register webhook. | v1.1
Multiple repositories per session | Single repo per GitHubTool instance. | v2

# 19. Open Questions

ID | Question | Owner | Needed By
OQ-01 | GitHub App private key storage: the private key is a PEM file (~1.7 KB). Keychain items have an effective limit of ~4 KB, so storage is fine. But the key must be accessible only with biometric auth. Recommendation: use kSecAttrAccessibleWhenUnlockedThisDeviceOnly + SecAccessControl with biometryAny. Confirm with TRD-1 team. | Engineering | Sprint 1
OQ-02 | Webhook delivery in production: the agent runs on a developer laptop with no inbound internet access. Options: (a) ngrok permanent tunnel, (b) GitHub App with relay server (YouSource-hosted), (c) polling only. Recommendation for v1: polling only. Add webhook support in v1.1 after validating the CI gate timing matters enough to justify the infra. | Product | v1 launch decision
OQ-03 | forge-docs/ naming conflict (from TRD-4 OQ-04): if the project TRDs are also stored in forge-docs/, there is a namespace collision. Recommendation: rename agent coordination files to .forge/ — hidden directory, clearly agent-specific, cannot conflict with user TRD files named forge-docs/. Requires updating TRD-4 and bootstrap. | Engineering | Sprint 1
OQ-04 | Merge method: squash (default) vs merge commit vs rebase. Squash gives cleaner history but loses individual commit context from review passes. Recommendation: squash by default, configurable per-project in Settings. | Product | Sprint 2

# Appendix A: GitHubTool Method Reference

Method | Parameters | Returns | Raises
commit_file | branch, path, content, message, sha=None | str (new SHA) | GitHubConflictError (422), PathSecurityError, GitHubToolError
get_file | path, ref=None | str (content) | GitHubNotFoundError, GitHubToolError
get_file_with_sha | path, ref=None | tuple[str, str] | GitHubNotFoundError, GitHubToolError
get_file_sha | path, ref=None | str | GitHubNotFoundError, GitHubToolError
file_exists | path, ref=None | bool | GitHubToolError
list_files_recursive | directory, ref=None | list[str] | GitHubToolError
create_branch | branch, from_ref=None | None | GitHubToolError
branch_exists | branch | bool | GitHubToolError
create_branch_if_not_exists | branch, from_ref=None | bool (created) | GitHubToolError
delete_branch | branch | None | GitHubToolError (protected branch)
get_default_branch | — | str | GitHubToolError
open_draft_pr | title, body, head, base=None | tuple[int, str] | GitHubToolError
mark_ready_for_review | pr_number | None | GitHubToolError
merge_pr | pr_number, merge_method="squash", commit_title=None | None | GitHubToolError
get_pr_state | pr_number | dict | GitHubNotFoundError, GitHubToolError
get_pr_reviews | pr_number | list[dict] | GitHubToolError
get_pr_review_comments | pr_number | list[dict] | GitHubToolError
submit_pr_review | pr_number, body, event="COMMENT" | None | GitHubToolError
get_check_runs | ref | list[dict] | GitHubToolError
wait_for_ci | branch, timeout_sec=1800, poll_interval=30, webhook_event=None | CIResult | GitHubToolError (timeout)
get_repo_info | — | dict | GitHubToolError
get_languages | — | dict[str, int] | GitHubToolError
check_branch_protection | branch | bool | GitHubToolError
get_latest_commit_sha | branch | str | GitHubNotFoundError, GitHubToolError

# Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification