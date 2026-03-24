# TRD-6-Holistic-Code-Review-Crafted

_Source: `TRD-6-Holistic-Code-Review-Crafted.docx` — extracted 2026-03-24 15:39 UTC_

---

TRD-6

Holistic Code Review

Technical Requirements Document  •  v1.0

Field | Value
Product | Crafted
Document | TRD-6: Holistic Code Review
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-2 (Consensus Engine — generate_single()), TRD-5 (GitHubTool — file reads and PR creation)
Independent of | TRD-3 (Build Pipeline), TRD-4 (Multi-Agent Ledger) — separate workflow
Language | Python 3.12
Trigger | REPL command: /review start <branch> [--scope <dir>] [--lenses <list>]
Output | Review report (.md), fix PR per-lens or combined, full audit trail

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Holistic Code Review capability — a standalone workflow that points the Crafted at an existing codebase branch, runs five structured review passes, produces a documented review report, and executes targeted fix pull requests.

This is a different workflow from the build pipeline (TRD-3). Where TRD-3 builds new software from specifications, TRD-6 reviews and improves existing software. The two workflows share infrastructure (Consensus Engine, GitHubTool) but have separate state objects, orchestration, and output formats.

The Holistic Code Review owns:

ReviewDirector — orchestration of the full review workflow

Five review lenses — lint/correctness, security/cyber hygiene, performance, test quality, architecture

Consensus integration — both Claude and GPT-4o review each file independently per lens

Issue aggregation — deduplication, severity ranking, fixability classification

Review report — structured markdown document committed to GitHub before any PR

Operator gate — exclusion of files/issues, fix scope selection, cost confirmation

Fix execution — applying fixable issues per-file with one commit per file

PR creation — per-lens or combined PR with full documentation

Review manifest — persistence for incremental and diff-mode re-reviews

PRINCIPLE | The review report is always produced and committed before any fix PR is opened. The operator reads the report and decides what to fix. The agent never auto-commits fixes to a branch without operator approval of the review findings.

# 2. Design Decisions

Decision | Choice | Rationale
Five lenses vs three passes | Five distinct lenses (lint, security, performance, tests, architecture) | Each lens requires different reviewer attention. Merging them into three generic passes loses specificity. Five focused lenses produce more actionable findings.
Per-lens PRs vs single PR | Operator choice — default: per-lens | Per-lens PRs are independently reviewable and revertible. A lint fix can be merged without the architectural changes. Single PR is simpler for small codebases.
Review before fix | Report committed first, fix PR opened second | Operator must understand the findings before the agent touches code. No surprise rewrites.
Fixable vs needs-review classification | Built into issue schema | Automatically fixable: lint, style, unused imports, simple security patterns. Needs-review: architectural changes, performance refactors, test additions. Prevents over-automation.
Consensus per-file | Both providers review each file independently per lens | Cross-contamination risk: if both providers see the same output, they converge. Independent review catches issues the other misses.
Diff mode | Review only changed files on re-run | Dramatically reduces cost on a codebase that changes incrementally. Full re-review is an option but rarely needed.
Cost gate | Pre-review estimate + operator confirmation | Reviewing a large codebase across five lenses is expensive. The operator must know the cost before committing.

# 3. Review Workflow — End-to-End Sequence

HOLISTIC CODE REVIEW WORKFLOW

/review start <branch> [--scope <dir>] [--lenses <l1,l2,...>] [--diff]
    │
    ▼
Phase 1: SCOPE
  ├── Fetch file list from branch (GitHubTool.list_files_recursive)
  ├── Apply file type filter (source only, skip vendored/generated)
  ├── Apply --scope directory filter if provided
  ├── Apply diff filter if --diff (only files changed since last review)
  ├── Chunk files into review batches (max tokens per batch)
  ├── Compute pre-review cost estimate
  └── GATE: Show file count, estimated cost, selected lenses
           → Operator: approve / adjust scope / cancel
    │
    ▼
Phase 2: REVIEW (per file, per lens)
  For each file in scope:
    For each selected lens (1–5):
      ├── Build review prompt with file content + lens focus
      ├── Claude reviews independently → structured JSON
      ├── GPT-4o reviews independently → structured JSON
      ├── Merge issues: dedup, severity-rank, fixability classify
      └── Accumulate into ReviewSession.issues[]
    Emit progress card: file N of M, issues found so far
    │
    ▼
Phase 3: REPORT
  ├── Aggregate all issues across files and lenses
  ├── Build structured markdown report:
  │     Executive summary, findings by lens, findings by file,
  │     severity breakdown, recommended fix order
  ├── Commit report to: crafted-docs/reviews/{branch_slug}-{timestamp}.md
  ├── Emit report summary card to build stream
  └── GATE: "Review report committed. Proceed to fix phase?"
           → Operator: yes / no (report only) / adjust (exclude files/issues)
    │
    ▼
Phase 4: FIX SCOPE SELECTION
  ├── Show fixable issue count by lens
  ├── GATE: Which lenses to auto-fix?
  │         → Operator selects: lint / security / performance / tests / arch / all / none
  ├── Show needs-review issue count (not auto-fixed — documented in PR for human review)
  └── Compute fix PR cost estimate
    │
    ▼
Phase 5: FIX EXECUTION
  For each selected lens:
    For each file with fixable issues in this lens:
      ├── Read current file from branch
      ├── Build fix prompt: file content + fixable issues for this lens
      ├── Claude applies fixes (single provider — no arbitration needed)
      ├── Run local lint/syntax check on result
      ├── Commit fixed file to review branch
      └── Record fix in ReviewSession
    │
    ▼
Phase 6: PR CREATION
  For each lens with fixes (or combined if single-PR mode):
    ├── open_draft_pr with structured description
    │     Links to review report, lists files changed,
    │     issue count by severity, needs-review items for human attention
    └── Emit PR card to build stream
    │
    ▼
Phase 7: MANIFEST
  ├── Write ReviewManifest to crafted-docs/reviews/{branch_slug}-manifest.json
  └── Emit completion summary card

Total gates: 3 (scope confirm, proceed to fix, lens selection)
Operator can stop after the report — no fixes required.

# 4. ReviewSession State Object

from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class ReviewIssue:
    """A single issue found during review."""
    file:          str              # Relative path from repo root
    line_start:    Optional[int]    # None if whole-file issue
    line_end:      Optional[int]
    lens:          str              # "lint"|"security"|"performance"|"tests"|"architecture"
    severity:      str              # "critical"|"major"|"minor"|"info"
    title:         str              # Short one-line description
    description:   str              # Full issue description
    fix_suggestion: str             # Concrete fix instruction
    fixable:       bool             # True = agent can auto-fix; False = needs-review
    providers:     list[str]        # Which providers flagged this: ["claude"], ["openai"], ["claude","openai"]
    fixed:         bool   = False   # True after fix applied
    dismissed:     bool   = False   # True if operator excluded
    fix_commit:    Optional[str] = None   # SHA of fix commit


@dataclass
class ReviewFileResult:
    """All issues found in a single file across all lenses."""
    path:          str
    language:      str              # "python"|"go"|"typescript"|etc
    line_count:    int
    issues:        list[ReviewIssue] = field(default_factory=list)
    reviewed_at:   float = field(default_factory=time.time)
    review_cost:   float = 0.0     # Total provider cost for this file


@dataclass
class ReviewSession:
    """State object for a full Holistic Code Review run."""

    # Identity
    session_id:     str             # UUID
    branch:         str             # Target branch
    repo_owner:     str
    repo_name:      str
    engineer_id:    str

    # Scope
    scope_dirs:     list[str]       # Top-level dirs included. Empty = all
    selected_lenses: list[str]      # Which of the 5 lenses are active
    diff_mode:      bool = False    # If True: only review changed files
    base_commit:    Optional[str] = None  # For diff mode: compare against this SHA

    # File list
    files_in_scope: list[str] = field(default_factory=list)
    files_reviewed: list[str] = field(default_factory=list)
    files_excluded: list[str] = field(default_factory=list)

    # Results
    file_results:   list[ReviewFileResult] = field(default_factory=list)

    # Report
    report_path:    Optional[str] = None  # GitHub path of committed report
    report_committed: bool = False

    # Fix phase
    lenses_to_fix:  list[str] = field(default_factory=list)
    fix_branch:     Optional[str] = None
    pr_numbers:     dict = field(default_factory=dict)  # lens → pr_number

    # Economics
    total_cost_usd: float = 0.0
    estimated_cost_usd: float = 0.0

    # Lifecycle
    state:          str = "scoping"
    created_at:     float = field(default_factory=time.time)
    updated_at:     float = field(default_factory=time.time)

    # ── Computed helpers ────────────────────────────────────────
    @property
    def all_issues(self) -> list[ReviewIssue]:
        return [i for fr in self.file_results for i in fr.issues]

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.all_issues if i.severity=="critical" and not i.dismissed)

    @property
    def fixable_issues(self) -> list[ReviewIssue]:
        return [i for i in self.all_issues if i.fixable and not i.dismissed and not i.fixed]

    @property
    def needs_review_issues(self) -> list[ReviewIssue]:
        return [i for i in self.all_issues if not i.fixable and not i.dismissed]

# 5. File Selection and Chunking

## 5.1 File Type Filter

Language | Include Extensions | Always Exclude
Python | .py | __pycache__/, .pyc, *_pb2.py (protobuf generated), migrations/
Go | .go | vendor/, _test.go files (reviewed separately under tests lens)
TypeScript / JavaScript | .ts, .tsx, .js, .jsx | node_modules/, *.min.js, *.bundle.js, dist/
Rust | .rs | target/
Config / infra | .yaml, .yml, .toml (security lens only) | *.lock files, *.sum files
Always excluded | — | *.docx, *.pdf, *.png, *.jpg, crafted-docs/, prds/, .crafted/, crafted/

## 5.2 Auto-Exclude Patterns

AUTO_EXCLUDE_PATTERNS = [
    # Generated code
    r".*_pb2\.py$",          # Protobuf
    r".*\.generated\.",      # Any generated file
    r".*/migrations/.*",       # Django/Alembic migrations
    r".*schema_pb2.*",

    # Vendor / dependencies
    r".*/vendor/.*",
    r".*/node_modules/.*",
    r".*/\.venv/.*",

    # Agent files
    r".*/crafted-docs/.*",
    r".*/prds/.*",
    r".*\.crafted/.*",

    # Build artifacts
    r".*/dist/.*",
    r".*/build/.*",
    r".*/\.build/.*",

    # Test fixtures (reviewed under tests lens, not as source)
    r".*/fixtures/.*",
    r".*/testdata/.*",
]

def should_include(path: str, scope_dirs: list[str]) -> bool:
    """Return True if this file should be included in review scope."""
    import re
    # Check auto-exclude patterns
    for pattern in AUTO_EXCLUDE_PATTERNS:
        if re.search(pattern, path):
            return False
    # Check scope directory filter
    if scope_dirs:
        return any(path.startswith(d.rstrip("/") + "/") for d in scope_dirs)
    return True

## 5.3 File Chunking

# Limits for review context window:
MAX_FILE_LINES_SINGLE    = 600   # Review entire file if <= 600 lines
MAX_FILE_LINES_CHUNK     = 300   # Chunk size for larger files
CHUNK_OVERLAP_LINES      = 30    # Overlap between chunks for context
MAX_CONTEXT_CHARS        = 20_000  # Max chars of file content per lens call

def chunk_file(content: str, path: str) -> list[dict]:
    """
    Split a file into reviewable chunks.
    Returns list of: { "content", "start_line", "end_line", "is_full_file" }
    """
    lines = content.splitlines()
    total = len(lines)

    if total <= MAX_FILE_LINES_SINGLE:
        return [{"content": content, "start_line": 1,
                 "end_line": total, "is_full_file": True}]

    # Large file: chunk with overlap
    chunks = []
    start  = 0
    while start < total:
        end    = min(start + MAX_FILE_LINES_CHUNK, total)
        chunk  = "\n".join(lines[start:end])
        chunks.append({
            "content":    chunk,
            "start_line": start + 1,
            "end_line":   end,
            "is_full_file": False,
        })
        start = end - CHUNK_OVERLAP_LINES   # Overlap for context
        if start >= end:
            break
    return chunks

## 5.4 Diff Mode — Changed Files Only

def get_changed_files(
    github: GitHubTool,
    branch: str,
    base_commit: str,   # SHA from last review manifest
) -> list[str]:
    """
    Return files changed between base_commit and current HEAD of branch.
    Uses GitHub compare API: GET /repos/{owner}/{repo}/compare/{base}...{head}
    """
    head_sha = github.get_latest_commit_sha(branch)
    if head_sha == base_commit:
        return []   # No changes since last review

    comparison = github._repo.compare(base_commit, head_sha)
    return [
        f.filename for f in comparison.files
        if f.status in ("added", "modified")   # skip deleted files
        and should_include(f.filename, [])
    ]

# 6. Five Review Lenses

## 6.1 Lens Overview

# | Lens Name | ID | Focus | Auto-Fixable?
1 | Lint and Correctness | "lint" | Code style, unused imports, dead code, type hints, obvious logic errors | Mostly yes — style, imports, type hints
2 | Security and Cyber Hygiene | "security" | Injection surface, hardcoded credentials, unsafe subprocess, unvalidated input, path traversal, dependency exposure | Partly — simple patterns yes; architectural issues no
3 | Performance and Optimization | "performance" | O(N²) patterns, blocking calls in async, N+1 queries, unnecessary allocations, missing caching | Rarely — mostly needs-review
4 | Test Quality | "tests" | Missing tests, vacuous assertions, over-mocking, no edge cases, brittle fixtures, copy-paste tests | No — new tests require specification context
5 | Architecture and Maintainability | "architecture" | Complexity hotspots (high McCabe), God objects, tight coupling, naming, missing abstractions, tech debt | No — architectural changes need human judgement

## 6.2 Lens 1 — Lint and Correctness

LENS_LINT_SYSTEM = """You are a senior code reviewer performing a lint and correctness review.

Review focus — find ALL of the following:

STYLE AND STRUCTURE
  - Unused imports (flagged but not affecting runtime)
  - Dead code: unreachable branches, functions never called
  - Inconsistent naming: snake_case vs camelCase violations for the language
  - Long lines exceeding the project style guide (>100 chars typical)
  - Missing or incomplete docstrings on public functions and classes

TYPE CORRECTNESS
  - Missing type hints on public function signatures
  - Type hint inconsistencies (returning str but annotated Optional[str])
  - Unsafe type casts without validation

LOGIC
  - Obvious logic errors: always-True/False conditions, off-by-one
  - Exception swallowing: bare `except: pass` or `except Exception: pass`
  - Mutable default arguments: `def fn(x=[])`
  - Missing return statements in non-void functions

For each issue, specify:
  - Exact file location (function name or line range)
  - Whether it is auto-fixable (style/import/type hint) vs needs-review (logic)
  - Concrete fix instruction

Respond in JSON only — see issue schema in system context.
"""

## 6.3 Lens 2 — Security and Cyber Hygiene

LENS_SECURITY_SYSTEM = """You are a senior security engineer performing a cyber hygiene review.

Review focus — find ALL of the following:

INJECTION AND INPUT VALIDATION
  - SQL injection: string-concatenated queries without parameterization
  - Command injection: subprocess with shell=True and user-controlled input
  - Path traversal: file operations using user-supplied paths without validation
  - SSRF: HTTP requests to URLs derived from user input without allowlist
  - Template injection: user input passed to template engines

CREDENTIAL AND SECRET EXPOSURE
  - Hardcoded credentials, API keys, passwords, or tokens in source
  - Credentials in log statements (even at DEBUG level)
  - Secrets in exception messages that may surface to callers
  - Environment variable reads without defaults that would reveal secret names

AUTHENTICATION AND AUTHORIZATION
  - Missing authentication checks on sensitive operations
  - Authorization checks that can be bypassed (e.g. client-supplied role)
  - JWT validation missing signature check or expiry check

CRYPTOGRAPHY
  - Weak algorithms: MD5 or SHA1 for security-sensitive hashing
  - Predictable random: random.random() for tokens or nonces (use secrets module)
  - Hardcoded IVs or salts
  - Missing TLS verification: verify=False in requests calls

DEPENDENCY EXPOSURE
  - Note any import of packages with known CVEs if identifiable from imports
  - Direct use of deprecated security-sensitive APIs

SEVERITY CALIBRATION:
  critical = exploitable without authentication, direct data exposure
  major    = exploitable with access, high-confidence vulnerability pattern
  minor    = defence-in-depth improvement, best practice violation
  info     = informational — no direct exploitability

Auto-fixable: hardcoded secrets removal, shell=True → shell=False,
  random → secrets, verify=False → verify=True, MD5/SHA1 → SHA256.
Needs-review: SQL parameterization (requires query structure change),
  auth missing (requires understanding of auth model),
  path traversal (requires understanding of intended access scope).

Respond in JSON only — see issue schema.
"""

## 6.4 Lens 3 — Performance and Optimization

LENS_PERFORMANCE_SYSTEM = """You are a senior engineer performing a performance review.

Review focus — find ALL of the following:

ALGORITHMIC COMPLEXITY
  - O(N²) or worse patterns in loops: nested loops over the same collection
  - Repeated list searches: using `x in list` inside a loop (use set)
  - Sorting inside a loop when sort could be done once outside
  - Repeated expensive computations that could be memoized

ASYNC AND CONCURRENCY
  - Blocking I/O calls inside async functions: time.sleep(), sync file reads
  - Sequential awaits that could be parallelised with asyncio.gather()
  - Missing async for database or network operations
  - Threading/locking patterns that serialise unnecessarily

MEMORY
  - Loading entire file or dataset into memory when streaming would suffice
  - Accumulating results in a list when a generator would suffice
  - String concatenation in loops (use join)
  - Large intermediate collections not released

DATABASE AND I/O
  - N+1 query patterns: query inside a loop over query results
  - Missing select_related / prefetch_related (ORM patterns)
  - Repeated reads of the same file or URL without caching
  - Missing database indexes (only flaggable from ORM model definitions)

UNNECESSARY WORK
  - Computing values that are immediately discarded
  - Redundant function calls with identical arguments
  - Deep copy where shallow copy would suffice

All performance issues are severity "major" or "minor" — never "critical".
Most are needs-review: performance fixes require benchmarking to confirm.
Auto-fixable: string concatenation in loops, `x in list` → `x in set`,
  sequential awaits with no data dependency → asyncio.gather().

Respond in JSON only — see issue schema.
"""

## 6.5 Lens 4 — Test Quality

LENS_TESTS_SYSTEM = """You are a senior engineer performing a test quality review.
You are reviewing test files AND source files to assess test coverage.

Review focus — find ALL of the following:

MISSING COVERAGE
  - Public functions in source files with no corresponding test
  - Error paths and exception cases not tested
  - Edge cases: empty input, zero, None, maximum values, concurrent access
  - Integration points (API calls, DB calls) with no integration or mock test

TEST QUALITY ISSUES
  - Vacuous assertions: assert True, assert response is not None (no value)
  - Tests that pass even if the implementation is completely broken
  - Over-mocking: mocking so much that the test tests only the mock
  - Copy-paste tests: identical test bodies with slightly different data
    (should use parametrize)
  - Tests with no assertions at all
  - Test names that do not describe what they test

TEST ISOLATION
  - Tests that depend on execution order (shared mutable state)
  - Tests that write to disk without cleanup
  - Tests that make real network calls
  - Fixtures with side effects that persist across tests

All test quality issues are needs-review — new test cases require
understanding of the intended behaviour, which requires specification context.
The agent will document what tests should be added but will NOT write them
without being given a specification.

Respond in JSON only — see issue schema.
"""

## 6.6 Lens 5 — Architecture and Maintainability

LENS_ARCH_SYSTEM = """You are a senior architect performing an architecture review.

Review focus — find ALL of the following:

COMPLEXITY
  - Functions with estimated McCabe complexity > 15 (count branches)
  - Classes with > 15 public methods (God object pattern)
  - Files > 500 lines that should be split
  - Deeply nested conditionals (> 4 levels)

COUPLING AND COHESION
  - Classes that import from 10+ other modules (high afferent coupling)
  - Circular imports (A imports B which imports A)
  - Business logic in data layer or I/O layer
  - Multiple responsibilities in one class (violates SRP)

NAMING AND CLARITY
  - Variable names that are single letters outside comprehensions
  - Function names that do not describe what the function does
  - Class names that end in Manager, Handler, Processor (vague abstractions)
  - Boolean parameters that invert function meaning (use two functions)

TECHNICAL DEBT
  - TODO/FIXME/HACK comments without issue references
  - Commented-out code blocks > 5 lines
  - Hardcoded magic numbers without named constants
  - Feature flags that are always True or always False

MISSING ABSTRACTIONS
  - Repeated code blocks > 10 lines that should be extracted
  - Direct instantiation of concrete classes where an interface would decouple
  - String constants that are repeated > 3 times without a defined constant

All architecture issues are needs-review.
Severity: major = high complexity that impedes change; minor = style/naming.

Respond in JSON only — see issue schema.
"""

# 7. Consensus Integration — Per-File, Per-Lens Protocol

## 7.1 Review Call Structure

# For each file + lens combination:
# 1. Fetch file content from GitHub
# 2. Chunk if large
# 3. For each chunk: call both providers independently
# 4. Merge issues from Claude and GPT-4o
# 5. Accumulate into file_result.issues

async def review_file_for_lens(
    self,
    path:    str,
    content: str,
    lens_id: str,
    github:  GitHubTool,
) -> list[ReviewIssue]:
    """Review a single file for a single lens. Returns list of issues."""

    chunks    = chunk_file(content, path)
    all_issues: list[ReviewIssue] = []
    system    = _lens_system_prompt(lens_id)

    for chunk in chunks:
        user = _build_review_user(path, chunk, lens_id)

        # Both providers review independently — no arbitration
        claude_result = await self._consensus.generate_single(
            provider_id="claude",
            system=system,
            user=user,
            max_tokens=4096,
        )
        openai_result = await self._consensus.generate_single(
            provider_id="openai",
            system=system,
            user=user,
            max_tokens=4096,
        )

        claude_issues = _parse_review_json(claude_result.content, path, lens_id,
                                            provider="claude")
        openai_issues = _parse_review_json(openai_result.content, path, lens_id,
                                            provider="openai")

        # Adjust line numbers for chunk offset
        if not chunk["is_full_file"]:",
            offset = chunk["start_line"] - 1
            claude_issues = _offset_lines(claude_issues, offset)
            openai_issues = _offset_lines(openai_issues, offset)

        merged = _merge_issues(claude_issues, openai_issues)
        all_issues.extend(merged)

        # Record cost
        self._session.total_cost_usd += (
            claude_result.cost_usd + openai_result.cost_usd
        )

    return all_issues

## 7.2 Review User Prompt

def _build_review_user(path: str, chunk: dict, lens_id: str) -> str:
    location = (
        f"Lines {chunk['start_line']}–{chunk['end_line']}"
        if not chunk["is_full_file"]
        else "Full file"
    )
    return f"""File: {path}
{location}

```
{chunk["content"]}
```

Review this code for the specific issues listed in your instructions.
Report only real, concrete issues — not theoretical concerns.
For each issue, provide the exact function name or line range.

If this is a chunk of a larger file, report issues only within this chunk.
Do not speculate about code outside this chunk.

Respond with JSON only:
{{
  "issues": [
    {{
      "line_start": 42,
      "line_end": 45,
      "title": "Brief one-line description",
      "description": "Full explanation of the issue",
      "fix_suggestion": "Concrete fix instruction",
      "severity": "critical|major|minor|info",
      "fixable": true|false
    }}
  ]
}}

Return an empty issues list if no issues found for this file.
"""

# 8. Issue Aggregation — Deduplication, Ranking, Fixability

## 8.1 Deduplication

# Same logic as TRD-3 _merge_issues(), extended for holistic review context.

SEVERITY_RANK = {"critical": 4, "major": 3, "minor": 2, "info": 1}

def _merge_issues(
    claude_issues: list[dict],
    openai_issues: list[dict],
) -> list[ReviewIssue]:
    """
    Merge issues from both providers.
    Dedup by proximity: issues within 3 lines of each other targeting
    the same concern are considered the same issue.
    Critical/major: always included from either provider.
    Minor/info: only included if both providers flagged it.
    """
    all_raw = [
        {**i, "_provider": "claude"} for i in claude_issues
    ] + [
        {**i, "_provider": "openai"} for i in openai_issues
    ]

    # Group by proximity (line_start within 3 lines)
    groups: list[list[dict]] = []
    used = set()

    for i, issue_a in enumerate(all_raw):
        if i in used:
            continue
        group = [issue_a]
        used.add(i)
        for j, issue_b in enumerate(all_raw):
            if j in used or i == j:
                continue
            a_line = issue_a.get("line_start") or 0
            b_line = issue_b.get("line_start") or 0
            if abs(a_line - b_line) <= 3:
                group.append(issue_b)
                used.add(j)
        groups.append(group)

    result = []
    for group in groups:
        providers  = list({g["_provider"] for g in group})
        # Pick highest severity representative
        best = max(group, key=lambda g: SEVERITY_RANK.get(g["severity"], 0))
        severity   = best["severity"]
        both_agree = len(providers) == 2

        # Inclusion rules
        if severity in ("critical", "major"):
            pass   # Always include
        elif severity == "minor" and not both_agree:
            continue  # Minor: only if both flagged
        elif severity == "info" and not both_agree:
            continue  # Info: only if both flagged

        result.append(ReviewIssue(
            file=best.get("file", ""),
            line_start=best.get("line_start"),
            line_end=best.get("line_end"),
            lens=best.get("lens", ""),
            severity=severity,
            title=best["title"],
            description=best["description"],
            fix_suggestion=best["fix_suggestion"],
            fixable=best.get("fixable", False),
            providers=providers,
        ))

    return result

## 8.2 Severity Model

Severity | Definition | Examples | Auto-Fix Eligible?
critical | Direct exploitability, data loss risk, or system compromise | Hardcoded API key, SQL injection, auth bypass | Some (secret removal, shell=False)
major | Significant defect, high-confidence vulnerability, performance killer | Missing input validation, O(N²) in hot path, God object > 20 methods, bare except | Rarely
minor | Best practice violation, code quality issue | Missing type hint, dead code, inconsistent naming, TODO without ticket | Mostly yes
info | Observation, improvement opportunity, documentation gap | Missing docstring, magic number, could use named constant | Yes

## 8.3 Fixability Classification

Lens | Auto-Fixable Issues | Needs-Review Issues
Lint | Unused imports, type hints on simple functions, bare except → specific exception, string concat in loop | Logic errors, missing return values, mutable defaults with complex implications
Security | shell=True → list args, verify=False → True, random.random() → secrets.token_hex(), MD5 → hashlib.sha256 | SQL injection (requires query restructure), missing auth (requires auth model), path traversal fix
Performance | String join in loop, `x in list` → `x in set`, sequential awaits → asyncio.gather() when no data dep | N+1 queries (requires ORM restructure), blocking I/O in async (requires async rewrite), memory streaming
Tests | None — new tests require specification context | All test quality issues: new test cases, fixing vacuous assertions, parametrize
Architecture | None — architectural changes require human design decisions | All architecture issues: complexity reduction, decoupling, extraction of abstractions

# 9. Review Report

## 9.1 Report Location

# Committed to GitHub (default branch or review branch — see OQ-01)
# Path: crafted-docs/reviews/{branch_slug}-{timestamp}.md
# Example: crafted-docs/reviews/main-20260319-143022.md

REVIEWS_PATH = "crafted-docs/reviews"

def report_path(branch: str, timestamp: float) -> str:
    import datetime
    slug = re.sub(r"[^a-z0-9]+", "-", branch.lower())[:40]
    ts   = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y%m%d-%H%M%S")
    return f"{REVIEWS_PATH}/{slug}-{ts}.md"

## 9.2 Report Structure

# ─────────────────────────────────────────────────────
# crafted-docs/reviews/main-20260319-143022.md
# ─────────────────────────────────────────────────────

# Holistic Code Review Report

**Branch:** `main`
**Reviewed:** 2026-03-19 14:30 UTC
**Engineer:** todd-gould
**Files reviewed:** 42
**Lenses active:** Lint, Security, Performance, Tests, Architecture
**Total cost:** $18.40

---

## Executive Summary

42 files reviewed across 5 lenses. 127 issues found.
3 critical (security), 18 major, 89 minor, 17 info.
61 issues are auto-fixable. 66 require human review.

**Top priority:** 3 critical security issues in `src/payments/validator.py`
and `src/auth/session.py` — see Security section.

**Most complex file:** `src/payments/processor.py`
(McCabe complexity 42, God object with 23 methods).

---

## Severity Breakdown

| Lens | Critical | Major | Minor | Info | Auto-Fixable |
|---|---|---|---|---|---|
| Lint | 0 | 2 | 34 | 8 | 44 |
| Security | 3 | 7 | 5 | 1 | 4 |
| Performance | 0 | 6 | 12 | 4 | 3 |
| Tests | 0 | 3 | 22 | 4 | 0 |
| Architecture | 0 | 0 | 16 | 0 | 0 |
| **Total** | **3** | **18** | **89** | **17** | **61** |

---

## Critical Issues (Fix First)

### SEC-001 — Hardcoded API Key
**File:** `src/payments/validator.py` · **Lines:** 42–42
**Severity:** critical · **Fixable:** Yes
**Found by:** Claude, GPT-4o

The Stripe API key is hardcoded as a string literal.
```python
stripe.api_key = "sk_live_AbCdEf123..."  # Line 42
```
**Fix:** Replace with `os.environ["STRIPE_API_KEY"]` and add to
environment configuration. Remove from source immediately.

---

## Findings by File

### `src/payments/validator.py` (12 issues)
...

## Findings by Lens
...

## Recommended Fix Order
1. Fix all 3 critical security issues immediately
2. Apply lint auto-fixes (44 issues, low risk)
3. Apply security auto-fixes (4 issues, low risk)
4. Review major performance issues with team
5. Add missing tests (requires specification context)
6. Plan architectural refactor sprint

---
*Generated by Crafted — Holistic Code Review*
*Review ID: {session_id}*

## 9.3 Report Commit Protocol

# Report is committed BEFORE any fix PR is opened.
# Non-fatal if commit fails — session continues with local report.

def commit_report(self, session: ReviewSession, report_md: str) -> None:
    path = report_path(session.branch, session.created_at)
    try:
        self._github.commit_file(
            branch=session.fix_branch or session.branch,
            path=path,
            content=report_md,
            message=f"crafted-review[{session.engineer_id}]: holistic review report",
        )
        session.report_path      = path
        session.report_committed = True
        self._emit_card({"card_type":"progress",
            "body": f"Review report committed: {path}"})
    except Exception as e:
        logger.warning(f"Report commit failed: {e}")
        self._emit_card({"card_type":"warning",
            "body": f"Could not commit report to GitHub: {e}. "
                    "Report saved locally only."})

# 10. Operator Review Gate

## 10.1 Gate 1 — Scope Confirmation

# Shown after file selection, before any LLM calls.

gate_1_body = f"""Review scope for branch: {branch}

Files selected: {len(files)} ({total_lines:,} lines)
Lenses: {", ".join(selected_lenses)}
Mode: {"Diff (changed since last review)" if diff_mode else "Full review"}

Estimated cost: ${estimated_cost:.2f}
Estimated time: ~{estimated_minutes} minutes

Top directories:
{chr(10).join(f"  {d}: {n} files" for d, n in top_dirs.items())}
"""

Gate options: ["start review", "adjust scope", "cancel"]
# "adjust scope" → operator can type directory or file exclusions

## 10.2 Gate 2 — Proceed to Fix

# Shown after review report is committed.

gate_2_body = f"""Review complete.

Issues found: {critical} critical, {major} major, {minor} minor, {info} info
Auto-fixable: {fixable_count} issues across {fixable_lenses}
Needs review: {needs_review_count} issues (documented in PR, not auto-fixed)

Review report: {report_path}

Proceed to fix phase?
"""

Gate options: ["yes — proceed to fix", "no — report only", "exclude files"]
# "exclude files" → operator lists files/issues to exclude before fixing

## 10.3 Gate 3 — Lens Selection

# Shown after operator confirms fix phase.
# Operator selects which lenses to auto-fix.

gate_3_body = f"""Select lenses to auto-fix:

Lint:         {lint_fixable} auto-fixable issues  (style, imports, type hints)
Security:     {sec_fixable} auto-fixable issues   (shell=True, hardcoded creds)
Performance:  {perf_fixable} auto-fixable issues  (string joins, set lookups)
Tests:        0 auto-fixable                       (always needs-review)
Architecture: 0 auto-fixable                       (always needs-review)

Estimated fix cost: ${fix_cost:.2f}
"""

Gate options: ["all", "lint only", "lint+security", "select lenses", "none"]
# "select lenses" → operator types comma-separated lens IDs

## 10.4 File and Issue Exclusion

# Operator can exclude specific files or issues at Gate 2.
# Exclusion syntax (typed in correction field):
#   "exclude src/legacy/" → exclude entire directory
#   "exclude src/old_api.py" → exclude specific file
#   "exclude security in src/vendor/" → exclude lens in directory

def apply_exclusions(session: ReviewSession, exclusion_text: str) -> None:
    """Parse operator exclusion text and mark issues as dismissed."""
    lines = exclusion_text.strip().splitlines()
    for line in lines:
        line = line.strip().lower()
        if not line.startswith("exclude"):
            continue
        parts = line.split(None, 3)  # ["exclude", optional_lens, "in"?, path]

        # "exclude src/legacy/"
        if len(parts) == 2:
            excluded_path = parts[1]
            for fr in session.file_results:
                if fr.path.startswith(excluded_path):
                    session.files_excluded.append(fr.path)
                    for issue in fr.issues:
                        issue.dismissed = True

        # "exclude security in src/vendor/"
        elif len(parts) >= 4 and parts[2] == "in":
            excl_lens = parts[1]
            excl_path = parts[3]
            for fr in session.file_results:
                if fr.path.startswith(excl_path):
                    for issue in fr.issues:
                        if issue.lens == excl_lens:
                            issue.dismissed = True

# 11. Fix Execution

## 11.1 Fix Branch Creation

# Fixes are applied to a dedicated review branch — never directly to the target branch.
# Branch name: crafted-review/{engineer_id}/{branch_slug}-{session_short_id}
# Example: crafted-review/todd-gould/main-a1b2c3d4

FIX_BRANCH_PREFIX = "forge-review"

def create_fix_branch(session: ReviewSession, github: GitHubTool) -> str:
    branch_slug = re.sub(r"[^a-z0-9]+", "-", session.branch.lower())[:30]
    short_id    = session.session_id[:8]
    fix_branch  = (f"{FIX_BRANCH_PREFIX}/{session.engineer_id}/"
                   f"{branch_slug}-{short_id}")
    github.create_branch_if_not_exists(fix_branch, from_ref=session.branch)
    session.fix_branch = fix_branch
    return fix_branch

## 11.2 Per-File Fix Protocol

FIX_SYSTEM = """You are applying specific, targeted code fixes.

Rules:
  - Apply ONLY the listed fixes
  - Do not restructure code not mentioned in the fix list
  - Do not change logic, add features, or refactor beyond what is listed
  - Preserve all existing function signatures, class interfaces, and module exports
  - Preserve all comments and docstrings unless the fix explicitly modifies them
  - Output the complete file — no truncation, no placeholders

Respond with ONLY the fixed code — no markdown fences, no explanation.
"""


async def fix_file(
    path:           str,
    original:       str,
    fixable_issues: list[ReviewIssue],
    lens_id:        str,
    consensus:      ConsensusEngine,
    github:         GitHubTool,
    fix_branch:     str,
    session:        ReviewSession,
) -> bool:
    """Apply fixes for a single lens to a single file. Returns True on success."""

    issue_text = "\n".join(
        f"  Line {i.line_start or '?'}: [{i.severity.upper()}] {i.title}\n"
        f"  Fix: {i.fix_suggestion}"
        for i in fixable_issues
    )

    user = f"""File: {path}

```
{original}
```

Apply these specific fixes:
{issue_text}

Output the complete fixed file."""

    result = await consensus.generate_single(
        provider_id="claude",
        system=FIX_SYSTEM,
        user=user,
        max_tokens=8192,
    )

    if not result.success or len(result.content) < 20:
        logger.warning(f"Fix generation failed for {path}: {result.error}")
        return False

    # Syntax check before committing
    if not _syntax_check(path, result.content):
        logger.warning(f"Fix produced syntax error for {path} — skipping")
        return False

    # Commit to fix branch — one commit per file
    try:
        github.commit_file(
            branch=fix_branch,
            path=path,
            content=result.content,
            message=f"crafted-review[{session.engineer_id}]: fix {lens_id} issues in {path}",
        )
    except Exception as e:
        logger.warning(f"Fix commit failed for {path}: {e}")
        return False

    # Mark issues as fixed
    for issue in fixable_issues:
        issue.fixed = True

    session.total_cost_usd += result.cost_usd
    return True

## 11.3 Syntax Check

def _syntax_check(path: str, content: str) -> bool:
    """Quick syntax validation before committing a fix."""
    import ast, subprocess

    if path.endswith(".py"):
        try:
            ast.parse(content)
            return True
        except SyntaxError as e:
            logger.warning(f"Syntax error in generated fix: {e}")
            return False

    if path.endswith(".go"):
        # Write to temp file, run gofmt -e
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".go", delete=False) as f:
            f.write(content.encode("utf-8"))
            tmp = f.name
        result = subprocess.run(["gofmt", "-e", tmp], capture_output=True)
        os.unlink(tmp)
        return result.returncode == 0

    # For other languages: accept without checking (no fast parser available)
    return True

# 12. PR Creation and Structure

## 12.1 PR Mode Selection

Mode | When Used | PR Title Pattern | Merge Complexity
Per-lens (default) | Multiple lenses with fixes | crafted-review: {lens} fixes for {branch} — {N} issues | Operator can merge lenses independently
Single combined PR | Operator selects "single PR" at Gate 3, or only one lens has fixes | crafted-review: holistic fixes for {branch} — {N} issues | Single merge — simpler for small codebases

## 12.2 PR Description

def build_review_pr_description(
    session:   ReviewSession,
    lens_id:   str,          # "lint" | "security" | etc | "combined"
    issues:    list[ReviewIssue],
    report_path: str,
) -> str:
    fixed    = [i for i in issues if i.fixed]
    nr       = [i for i in issues if not i.fixable and not i.dismissed]

    files_changed = sorted(set(i.file for i in fixed))
    severity_breakdown = {
        s: sum(1 for i in fixed if i.severity == s)
        for s in ["critical","major","minor","info"]
    }

    nr_section = ""
    if nr:
        nr_section = f"""
### Issues Requiring Human Review ({len(nr)})

These issues were documented but NOT auto-fixed.
They require design decisions or additional context.

{chr(10).join(f"- [{i.severity.upper()}] {i.file}: {i.title}" for i in nr[:20])}
{"..." if len(nr) > 20 else ""}
"""

    return f"""## Holistic Code Review — {lens_id.title()} Fixes

**Branch:** `{session.branch}`
**Review report:** [{report_path}]({report_path})
**Session:** `{session.session_id}`

### Auto-Applied Fixes ({len(fixed)} issues)

| Severity | Count |
|---|---|
| Critical | {severity_breakdown["critical"]} |
| Major | {severity_breakdown["major"]} |
| Minor | {severity_breakdown["minor"]} |
| Info | {severity_breakdown["info"]} |

**Files changed ({len(files_changed)}):**
{chr(10).join(f"- `{f}`" for f in files_changed)}
{nr_section}
---
_Generated by Crafted — Holistic Code Review_
_This PR was opened as a draft. Review the changes before merging._
_Fixes are applied as-is — verify each file before approving._
"""

# 13. Review Manifest — Persistence and Incremental Mode

## 13.1 Manifest Schema

# Stored at: crafted-docs/reviews/{branch_slug}-manifest.json
# One manifest per branch. Updated after each review run.
# Used for diff mode: "which files have I already reviewed?"

{
    "schema_version":  1,
    "branch":          "main",
    "last_review_id":  "uuid-of-last-session",
    "last_review_at":  1710000000.0,
    "last_head_sha":   "abc123...",   // HEAD SHA at last review — used for diff
    "total_reviews":   3,

    "files_reviewed": {
        "src/payments/validator.py": {
            "last_reviewed_at":   1710000000.0,
            "issues_found":       12,
            "issues_fixed":       7,
            "issues_dismissed":   2,
            "issues_outstanding": 3,
            "file_sha":           "sha-of-file-at-review-time",
        }
    },

    "dismissed_issues": [
        {
            "file":      "src/legacy/old_api.py",
            "line_start": 42,
            "title":     "Missing type hint on public function",
            "dismissed_at":  1710000000.0,
            "dismissed_by":  "todd-gould",
        }
    ],

    "review_history": [
        {
            "session_id":   "uuid",
            "reviewed_at":  1710000000.0,
            "files_count":  42,
            "issues_found": 127,
            "issues_fixed": 61,
            "cost_usd":     18.40,
            "report_path":  "crafted-docs/reviews/main-20260319-143022.md",
            "pr_numbers":   {"lint": 52, "security": 53, "performance": 54},
        }
    ]
}

## 13.2 Diff Mode Logic

def compute_diff_scope(
    session:  ReviewSession,
    manifest: dict,
    github:   GitHubTool,
) -> list[str]:
    """
    For diff mode: return only files changed since last review.
    Files with outstanding (unfixed, undismissed) issues are always included.
    """
    last_sha = manifest.get("last_head_sha")
    if not last_sha:
        return session.files_in_scope  # No baseline — full review

    changed_files = get_changed_files(github, session.branch, last_sha)

    # Also include files with outstanding issues from last review
    files_with_outstanding = set()
    for path, data in manifest.get("files_reviewed", {}).items():
        if data.get("issues_outstanding", 0) > 0:
            files_with_outstanding.add(path)

    diff_scope = set(changed_files) | files_with_outstanding

    # Filter against should_include and scope_dirs
    return [
        f for f in diff_scope
        if should_include(f, session.scope_dirs)
        and f in session.files_in_scope
    ]

# 14. Cost Model

## 14.1 Pre-Review Cost Estimate

# Cost estimate shown at Gate 1 before any LLM calls.
# Estimate is approximate — actual cost depends on output tokens.

COST_PER_1K_CHARS_INPUT  = 0.003   # $3.00/M input tokens, ~4 chars/token
COST_PER_1K_CHARS_OUTPUT = 0.015   # $15.00/M output tokens (Claude)
AVG_REVIEW_OUTPUT_TOKENS = 800     # Average tokens per file×lens review
PROVIDERS_PER_LENS       = 2       # Both Claude and GPT-4o

def estimate_review_cost(
    files:           list[str],
    file_sizes_chars: dict[str, int],
    selected_lenses: list[str],
) -> float:
    """Estimate total review cost in USD."""
    total = 0.0
    for path in files:
        chars  = file_sizes_chars.get(path, 1000)
        chunks = max(1, chars // (MAX_FILE_LINES_SINGLE * 80))
        for _lens in selected_lenses:
            # Input cost (file content sent to both providers)
            input_cost = (chars / 1000) * COST_PER_1K_CHARS_INPUT * PROVIDERS_PER_LENS
            # Output cost (review JSON from both providers)
            output_cost = (AVG_REVIEW_OUTPUT_TOKENS / 1000) * 4 * COST_PER_1K_CHARS_OUTPUT * PROVIDERS_PER_LENS
            total += (input_cost + output_cost) * chunks
    return total

## 14.2 Typical Costs

Codebase Size | Files | 5 Lenses (Full) | 3 Lenses | 1 Lens | Diff Mode (20% changed)
Small (5K lines) | ~20 | $8–15 | $5–10 | $2–4
Medium (20K lines) | ~80 | $30–55 | $18–35 | $7–13
Large (100K lines) | ~400 | $150–280 | $90–170 | $35–65
Very large (500K lines) | ~2000 | $750+ | $450+ | $175+ | Scope to dirs

COST GATE | For any review estimated > $20, the Gate 1 confirmation is mandatory and cannot be bypassed with --force. The operator must explicitly type "yes" to proceed. This prevents accidental expensive reviews on large codebases.

# 15. REPL Integration — /review Commands

Command | Description | Parameters
/review start | Start a full holistic code review | <branch> [--scope <dir>] [--lenses lint,security,...] [--diff] [--single-pr]
/review status | Show status of the current review session | —
/review report | Reopen or display the last review report | [--open] (opens in default browser)
/review continue | Resume an interrupted review session | —
/review exclude | Exclude files or issues before fix phase | <path_or_pattern> [--lens <lens_id>]
/review fix | Start the fix phase if review is complete | [--lenses lint,security,...] [--single-pr]
/review cancel | Cancel the current review session | —
/review list | List recent review sessions for this repo | —
/review diff | Start a diff-mode review (changed files only) | <branch> [--scope <dir>]

# /review start examples:
/review start main
/review start feature/payments --scope src/payments --lenses lint,security
/review start main --diff
/review start release/1.2 --lenses security --single-pr

# /review exclude examples:
/review exclude src/legacy/
/review exclude src/vendor/ --lens security
/review exclude src/old_api.py

# 16. ReviewDirector — Orchestration Class

class ReviewDirector:
    """
    Orchestrates the full Holistic Code Review workflow.
    Separate from BuildDirector — different state object, no PRD/PR plan.
    """

    def __init__(
        self,
        consensus:   ConsensusEngine,
        github:      GitHubTool,
        emit_card:   Callable[[dict], None],
        emit_gate:   Callable[[dict], Awaitable[str]],
        audit:       AuditLogger,
        engineer_id: str,
    ) -> None: ...

    async def start_review(
        self,
        branch:          str,
        scope_dirs:      list[str]   = None,
        selected_lenses: list[str]   = None,   # None = all 5
        diff_mode:       bool        = False,
        single_pr:       bool        = False,
    ) -> ReviewSession:
        """Full review workflow — phases 1 through 7."""
        session = self._create_session(branch, scope_dirs,
                                        selected_lenses, diff_mode)

        # Phase 1: Scope
        files = await self._phase_scope(session)
        if not files:
            return session   # Operator cancelled or no files

        # Phase 2: Review
        await self._phase_review(session, files)

        # Phase 3: Report
        report_md = self._build_report(session)
        self.commit_report(session, report_md)
        if not await self._gate_proceed_to_fix(session):
            return session   # Report only — no fix phase

        # Phase 4: Lens selection
        lenses = await self._gate_lens_selection(session)
        if not lenses:
            return session   # Operator chose not to fix anything

        # Phase 5: Fix
        fix_branch = create_fix_branch(session, self._github)
        await self._phase_fix(session, lenses, fix_branch)

        # Phase 6: PR creation
        await self._phase_create_prs(session, lenses, single_pr)

        # Phase 7: Manifest
        self._save_manifest(session)

        self._emit_summary_card(session)
        return session

    async def _phase_review(self, session: ReviewSession, files: list[str]) -> None:
        """Run review for all files × all selected lenses."""
        total = len(files) * len(session.selected_lenses)
        done  = 0
        for path in files:
            try:
                content = self._github.get_file(path, ref=session.branch)
            except GitHubToolError:
                continue

            lang    = _detect_language(path)
            fr      = ReviewFileResult(path=path, language=lang,
                                        line_count=content.count("\n"))
            file_cost = 0.0

            for lens_id in session.selected_lenses:
                issues = await self.review_file_for_lens(
                    path, content, lens_id, self._github
                )
                for issue in issues:
                    issue.file = path
                    issue.lens = lens_id
                fr.issues.extend(issues)
                done += 1

            session.file_results.append(fr)
            session.files_reviewed.append(path)

            self._emit_card({"card_type":"progress",
                "body": f"Reviewed {path}: {len(fr.issues)} issues found",
                "completed": done, "total": total,
                "session_cost": session.total_cost_usd})

# 17. Testing Requirements

Module | Coverage Target | Critical Test Cases
should_include() | 100% | Auto-exclude patterns match correctly; scope_dirs filter works; crafted-docs/ always excluded; vendor/ always excluded
chunk_file() | 100% | File <= MAX_FILE_LINES_SINGLE returns single chunk; large file splits with overlap; line numbers correct in each chunk; no lines lost
_merge_issues() | 100% | Critical from one provider included; minor from one provider excluded; minor from both providers included; proximity dedup within 3 lines; providers list accurate
apply_exclusions() | 95% | Directory exclusion dismisses all files under it; file exclusion exact match; lens+path exclusion dismisses only that lens; malformed lines ignored
estimate_review_cost() | 90% | Zero files = zero cost; cost scales with file count and lens count; diff mode reduces scope
_syntax_check() | 95% | Valid Python passes; invalid Python caught; Go check requires gofmt present; non-Python/Go passes without check
fix_file() | 90% | Syntax error in fix → skip without commit; fix applied → issues marked fixed; generate_single failure → return False
build_report() | 85% | Executive summary correct; severity breakdown accurate; all issues present; recommended order present
_build_review_user() | 90% | Chunk location included; file path present; issue schema instructions present; no markdown in code fence
Lens system prompts regression | 100% | Each lens prompt contains its key focus areas; no prompt is empty; fixability guidance present in each

## 17.1 Lens Prompt Regression Tests

# tests/test_review.py

def test_lint_prompt_covers_all_focus_areas():
    from review import LENS_LINT_SYSTEM
    required = ["unused imports", "dead code", "type hints",
                "exception", "mutable default"]
    for r in required:
        assert r.lower() in LENS_LINT_SYSTEM.lower(), f"Missing from lint prompt: {r}"

def test_security_prompt_covers_critical_patterns():
    from review import LENS_SECURITY_SYSTEM
    required = ["injection", "hardcoded", "shell=True",
                "path traversal", "verify=False", "MD5"]
    for r in required:
        assert r.lower() in LENS_SECURITY_SYSTEM.lower()

def test_performance_prompt_covers_async_patterns():
    from review import LENS_PERFORMANCE_SYSTEM
    required = ["asyncio", "blocking", "N+1", "O(N"]
    for r in required:
        assert r.lower() in LENS_PERFORMANCE_SYSTEM.lower()

def test_fix_prompt_prohibits_restructure():
    from review import FIX_SYSTEM
    assert "ONLY the listed fixes" in FIX_SYSTEM
    assert "restructure" in FIX_SYSTEM.lower()

def test_tests_lens_is_always_needs_review():
    from review import LENS_TESTS_SYSTEM
    assert "needs-review" in LENS_TESTS_SYSTEM.lower()
    assert "NOT auto-fix" in LENS_TESTS_SYSTEM or "not auto-fix" in LENS_TESTS_SYSTEM.lower()

def test_architecture_lens_is_always_needs_review():
    from review import LENS_ARCH_SYSTEM
    assert "needs-review" in LENS_ARCH_SYSTEM.lower()

# 18. Performance Requirements

Metric | Target | Notes
File fetch from GitHub | < 2s per file | Cached after first fetch per session
Single file × single lens review (both providers) | < 45s | Two parallel generate_single() calls
Single file × all 5 lenses | < 3 minutes | Sequential lenses — parallelism is optional enhancement
10-file review × 5 lenses | < 30 minutes | Progress cards emitted per file
Report generation (100 issues) | < 5 seconds | In-memory markdown construction
Report GitHub commit | < 5 seconds | Standard commit_file() call
Fix generation per file | < 60 seconds | Single provider (Claude only) for fixes
Fix commit per file | < 5 seconds | Standard commit_file() call
Manifest read | < 3 seconds | Small JSON file from GitHub
Manifest write | < 5 seconds | Small JSON file to GitHub
Cost estimate computation | < 1 second | In-memory arithmetic — no API calls
Diff scope computation | < 10 seconds | One GitHub compare API call

# 19. Out of Scope

Feature | Reason | Target
Automated dependency CVE scanning | Requires a CVE database and package manager integration. The security lens notes suspicious imports but does not scan lockfiles. | v2 — integrate with safety or Dependabot
AST-level analysis | Review is LLM-based — not AST-based. AST would be faster and more accurate for lint, but requires language-specific parsers for every supported language. | TBD — hybrid approach
Parallel lens execution per file | Sequential by default. Parallelism would reduce wall-clock time by 5x but increases API cost unpredictably. | v2 — optional with cost gate
IDE integration | REPL and app-based only. VS Code extension is out of scope. | TBD
Automatic merge of fix PRs | Operator always merges. Review code changes are high-stakes. | Never
Review scheduling (cron) | No scheduled reviews. Always operator-triggered. | v2
Custom lens definitions | Fixed five lenses in v1. Custom lenses (e.g. domain-specific patterns) deferred. | v2
Review of binary files | Source code only. No PDF, image, or binary review. | Never
Cross-repository review | Single repository per session. | v2

# 20. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Report commit target: should the review report be committed to the default branch (always visible) or the fix branch (only visible after PR)? Recommendation: default branch — the report is valuable regardless of whether fixes are applied, and makes the review history visible to the whole team. | Engineering | Sprint 1
OQ-02 | Parallel lens execution: running all 5 lenses sequentially for a 100-file codebase takes ~2.5 hours. Running lenses in parallel per file would cut this to ~30 minutes. Tradeoff: parallel calls spike rate limits. Recommendation: implement sequential in v1; add parallelism with rate-limit-aware throttle in v2. | Engineering | v1.1
OQ-03 | Tests lens vs build pipeline: the tests lens identifies missing tests but cannot write them without specification context. Should /review start offer to load TRD documents to provide that context, enabling test generation? Recommendation: yes — if TRD documents are loaded in the session, inject them into the tests lens prompt. | Product | Sprint 2
OQ-04 | Fix branch vs target branch: should fixes be committed directly to the target branch (simpler, no PR needed) or always to a separate fix branch (always needs PR)? Recommendation: always a separate fix branch — fixes must be reviewed before merging, and direct commits to main/develop are dangerous. | Engineering | Sprint 1

# Appendix A: Review Lens Prompt Reference

Lens ID | System Constant | Focus Summary | Auto-Fixable Categories
lint | LENS_LINT_SYSTEM | Unused imports, dead code, type hints, naming, exception handling, mutable defaults | Imports, type hints on simple functions, bare except → specific, string concat in loop
security | LENS_SECURITY_SYSTEM | Injection, hardcoded secrets, unsafe subprocess, weak crypto, missing auth/TLS | shell=True removal, verify=False, MD5→SHA256, random→secrets, hardcoded secret removal
performance | LENS_PERFORMANCE_SYSTEM | O(N²), blocking async, N+1, memory, unnecessary work | String join in loops, list → set for membership, sequential awaits → gather
tests | LENS_TESTS_SYSTEM | Missing tests, vacuous assertions, over-mocking, brittle fixtures, no edge cases | None — all needs-review
architecture | LENS_ARCH_SYSTEM | High complexity, God objects, coupling, naming, tech debt, missing abstractions | None — all needs-review

# Appendix B: Issue Schema Reference

Field | Type | Required | Description
file | str | Yes | Relative path from repo root
line_start | int|null | No | Start line of the issue. null = whole-file issue
line_end | int|null | No | End line. null if single-line or whole-file
lens | str | Yes | "lint"|"security"|"performance"|"tests"|"architecture"
severity | str | Yes | "critical"|"major"|"minor"|"info"
title | str | Yes | One-line description — used in report summary
description | str | Yes | Full explanation of why this is an issue
fix_suggestion | str | Yes | Concrete, actionable fix instruction
fixable | bool | Yes | True = agent can auto-apply; False = needs-review
providers | list[str] | Yes | ["claude"], ["openai"], or ["claude","openai"]
fixed | bool | No | Set to True after fix is committed. Default: False
dismissed | bool | No | Set to True if operator excluded. Default: False
fix_commit | str|null | No | GitHub commit SHA of the fix. Set after commit.

# Appendix C: Review Report Template

The following template is used by build_report() to generate the markdown review report. All placeholders are replaced with actual session data.

# Holistic Code Review Report

**Branch:** `{branch}`
**Reviewed:** {timestamp_utc}
**Engineer:** {engineer_id}
**Session:** `{session_id}`
**Files reviewed:** {files_reviewed}
**Lenses:** {lenses_active}
**Mode:** {full_or_diff}
**Total cost:** ${total_cost:.2f}

---

## Executive Summary

{files_reviewed} files reviewed across {lens_count} lenses.
{total_issues} issues found: {critical} critical, {major} major, {minor} minor, {info} info.
{fixable_count} issues are auto-fixable. {needs_review_count} require human review.

{top_priority_note}
{most_complex_file_note}

---

## Severity Breakdown

| Lens | Critical | Major | Minor | Info | Auto-Fixable |
|---|---|---|---|---|---|
{severity_table_rows}
| **Total** | **{critical}** | **{major}** | **{minor}** | **{info}** | **{fixable}** |

---

## Critical Issues (Fix First)

{critical_issues_detail}

---

## Findings by Lens

### Lint and Correctness
{lint_findings}

### Security and Cyber Hygiene
{security_findings}

### Performance and Optimization
{performance_findings}

### Test Quality
{tests_findings}

### Architecture and Maintainability
{architecture_findings}

---

## Findings by File

{files_with_most_issues_first}

---

## Recommended Fix Order

1. Fix all {critical} critical issues immediately
2. Apply auto-fixable lint issues ({lint_fixable} issues, low risk)
3. Apply auto-fixable security issues ({security_fixable} issues, medium risk)
4. Apply auto-fixable performance issues ({perf_fixable} issues, low risk)
5. Review major issues with team and plan refactor sprint
6. Add missing tests (requires specification context)

---
*Generated by Crafted — Holistic Code Review*
*Full issue data: {manifest_path}*

# Appendix D: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification