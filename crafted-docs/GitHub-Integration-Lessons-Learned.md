# GitHub-Integration-Lessons-Learned

_Source: `GitHub-Integration-Lessons-Learned.docx` — extracted 2026-03-25 20:37 UTC_

---

GitHub API Integration

Lessons Learned — Crafted Dev Agent Build Pipeline

YouSource.ai  ·  March 2026  ·  v38.209

This document captures every GitHub API behaviour discovered while building the Crafted Dev Agent automated build pipeline. Each lesson was uncovered by a real failure in production. The fixes are implemented in v38.x of the agent; the underlying GitHub behaviour applies to any automation that touches the GitHub REST or GraphQL APIs.

# 1.  Draft PR Lifecycle and Merge Behaviour

The agent opens every PR as a draft so CI can run before the operator sees it. This creates a specific lifecycle that differs from regular PRs in several non-obvious ways.

## 1.1  Converting Draft → Ready for Review

✗ REST PATCH /repos/{owner}/{repo}/pulls/{number} with body {"draft": false} does NOT work. GitHub silently ignores the field — the PR stays as draft and the call returns 200 with no error.

✓ Use the GraphQL markPullRequestReadyForReview mutation. This is the only officially supported conversion path.

mutation MarkReady($prId: ID!) {

markPullRequestReadyForReview(input: {pullRequestId: $prId}) {

pullRequest { isDraft }

}

}

The PR's node_id (not number) is required as the mutation input. Fetch it with repo.get_pull(number).node_id via PyGithub.

⚠ Add a 1–2 second sleep after the mutation before reading PR state. GitHub's API reflects the update asynchronously.

## 1.2  Merging a Draft PR Returns 405

✗ Calling pr.merge() on a draft PR returns HTTP 405 with message 'Pull Request is still a draft'. There is no way to merge a draft — it must be converted first.

✓ Always check pr.draft before attempting merge. If draft, call the GraphQL mutation first, wait 1–2 seconds, refresh the PR object, then merge.

## 1.3  CI Checks on Draft PRs

✗ By default, GitHub Actions workflows do NOT fire on draft PRs unless the workflow explicitly includes ready_for_review in its pull_request types filter.

Default pull_request trigger fires on: opened, synchronize, reopened — but NOT ready_for_review.

✓ Always declare types explicitly in workflows that must fire when a draft is converted:

on:

pull_request:

types: [opened, synchronize, reopened, ready_for_review]

Without ready_for_review in the types list, converting a draft to ready does not trigger checks, the PR has no green check, and merging fails branch protection rules.

# 2.  Documentation-Only PRs and CI Requirements

Any project built by Crafted will produce PRs that contain only non-code files: markdown documents, .gitkeep sentinels, YAML config, JSON schemas, LICENSE, .gitignore. These PRs should not run the full test suite — there is nothing to test. However GitHub's branch protection requires all required checks to pass before merging.

## 2.1  The Problem: Required Checks Block Docs Merges

✗ If ci.yml is the only required check and it is skipped (because the PR contains no code), the check appears as 'Pending' not 'Passed'. GitHub treats Pending as a block — the PR cannot be merged.

✓ The solution is two complementary workflows with mirrored path filters:

### ci.yml — skips for docs, runs for code

on:

pull_request:

types: [opened, synchronize, reopened, ready_for_review]

paths-ignore:

- '**/*.md'

- '**/*.gitkeep'

- 'VERSION'

- '**/*.toml'

- '**/*.json'

- '**/*.yaml'

- '**/*.yml'

- 'LICENSE'

- '.gitignore'

- '.editorconfig'

### docs-check.yml — runs for docs, produces instant green

on:

pull_request:

types: [opened, synchronize, reopened, ready_for_review]

paths:

- '**/*.md'

- '**/*.gitkeep'  # ... same list as ci.yml paths-ignore

jobs:

docs-ok:

runs-on: ubuntu-latest

steps:

- run: echo "Documentation-only PR. CI tests not required."

## 2.2  Branch Protection Configuration

Register BOTH 'CI Tests' and 'Docs OK' as required status checks in the branch protection rule. For any given PR exactly one will fire — either the code suite or the instant docs check — and the other will be absent (not pending, not failed, just not present for that PR).

⚠ A PR with mixed content (one .py + one .md) routes to ci.yml since the paths-ignore filter doesn't match when any code file is present. This is correct behaviour.

## 2.3  Timing: Commit Workflow Files Before the First PR

✗ If the workflow files do not exist on the default branch when a PR is opened, no check fires. The PR is permanently stuck with no checks — neither pending nor passing.

✓ Commit ci.yml and docs-check.yml to main during repo bootstrap, before any PR is created. In Crafted, _ensure_ci_workflows() is called at the start of every build session as a self-healing check — it commits the files if they are missing and no-ops if they already exist.

# 3.  File Path Handling in the GitHub API

## 3.1  Allowed Root Directories

✗ Committing to unexpected root directories fails silently or is rejected by path security guards. The agent maintains an allowlist of valid repo roots.

Roots that must be explicitly allowed for a standard project:

src, tests, docs, scripts — standard project layout

.github — CI workflow files. Dot-prefixed roots require explicit allowlisting because most path validators reject dots in leading position.

tools, schemas, contracts, configs — common project infrastructure

CamelCase roots — auto-detected for Swift/Xcode projects (CraftedApp, CraftedTests, ForgeAgent, etc.)

✓ Implement smart root detection: allow any root matching ^[A-Za-z][A-Za-z0-9_-]*$ (CamelCase or lowercase single word) rather than maintaining an exhaustive allowlist. Apply strict rules (traversal, absolute paths, control characters) first, smart detection as fallback.

## 3.2  Files That Must Live at Repo Root

Some files must be committed without a directory prefix: README.md, CODEOWNERS, LICENSE, .gitignore, .editorconfig, VERSION, Makefile, pyproject.toml. These are validated by basename against a known set rather than by root directory.

## 3.3  Branch-Protected Files

✗ CLAUDE.md and AGENTS.md exist on the default branch and must never be committed to feature branches. Doing so causes merge conflicts on every PR that touches those paths.

✓ Maintain a BRANCH_PROTECTED frozenset and skip those filenames in any branch commit loop, regardless of content.

# 4.  CI Check Status Interpretation

## 4.1  Check Conclusions That Count as Passing

GitHub check conclusions: success | failure | neutral | cancelled | skipped | action_required | timed_out.

✓ Treat success, neutral, and skipped as passing. skipped is the conclusion when a workflow's path filter doesn't match — this is correct for docs-only PRs where ci.yml is skipped and docs-check.yml passes.

## 4.2  No Checks Configured

✓ If no check runs exist on a branch (e.g. a fresh branch with no CI configuration yet), treat it as passed rather than blocking indefinitely. Log a warning and proceed.

## 4.3  CI Log Retrieval for Fix Loop

When CI fails, the agent needs the failure output to generate a fix. Three strategies in descending priority:

Full job log: GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs — returns a redirect to a presigned URL. Follow the redirect to get complete output.

Annotations: GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations — structured error entries, useful for parse errors.

Summary: check_run.output.summary — brief, often incomplete, last resort.

⚠ Job log URLs expire after ~1 minute. Download immediately after retrieving the redirect, do not cache the URL.

# 5.  PR Scope and Size Constraints

## 5.1  Why Large PRs Fail Disproportionately

An LLM-generated build pipeline operating on a single impl_code string cannot handle PRs with many files. The LLM either concatenates all files into one Python string (invalid), returns a generator script that creates the files (wrong format), or oscillates in self-correction between two broken states.

Empirical limits discovered through production failures:

Max impl_files per PR | 8 — above this, LLM output quality degrades severely

Max acceptance criteria | 10 — above this, self-correction loop oscillates

Multi-file threshold | > 1 impl_file triggers --- path --- delimiter format

## 5.2  Multi-File Output Format

✗ Asking an LLM to write multiple files in a single response always produces concatenation or generator scripts unless the output format is explicitly specified.

✓ Inject this instruction into the generation context whenever impl_files has more than one entry:

MULTI-FILE OUTPUT REQUIRED: This PR creates N files.

Output each file using this format:

--- path/to/file.ext ---

<complete file content>

--- path/to/other.ext ---

<complete file content>

Do NOT concatenate. Do NOT return a generator script.

## 5.3  PR Scoping Rules for LLM Prompts

Size limits alone are insufficient — the LLM will pad criteria to hit the limit or cram everything into one PR just short of the cap. Scoping rules must be stated explicitly:

One PR = one named thing: one module, one class, one config file, one schema.

If the PR title contains 'and', it should be two PRs.

Scaffold (empty dirs, .gitkeep) is separate from config (pyproject.toml).

Config is separate from tooling (Makefile, scripts).

Standards documents are separate from code.

Never bundle 'add X, configure Y, and write Z' into one PR.

# 6.  PR Type Routing

## 6.1  Documentation PRs

A PR is documentation-only if pr_type == 'documentation' OR all impl_files have non-code extensions (.md, .yaml, .json, .toml, .gitkeep, etc.).

Documentation PRs must bypass:

Ruff lint — ruff does not understand markdown or YAML

Stub/placeholder guard — impl_code is intentionally a short stub because real content was committed directly to GitHub

Self-correction loop — no Python to review

Local test runner — no tests to run

CI wait — docs-check.yml provides an instant green check instead

## 6.2  Scaffold PRs

A scaffold PR creates the repository skeleton: directories, __init__.py files, .gitkeep sentinels. It may have >1 impl_files.

✗ The LLM cannot reliably generate 20+ empty files in one response. It returns a generator script or a markdown table of filenames.

✓ Detect scaffold PRs by impl_files count > 1. Use --- path --- delimited parsing. Any file not found in LLM output gets an empty placeholder committed directly.

⚠ When parsing --- path --- delimiters, reject any extracted token containing | (pipe), starting with # (markdown heading), or containing spaces in non-separator characters. These indicate the LLM returned a markdown table instead of file content.

# 7.  Build State Management and Recovery

## 7.1  Clearing PR Plans Without Losing PRDs

The local state JSON (workspace/{engineer}/state/threads/{slug}.json) contains three key fields:

prd_plan | The PRD list — preserve this to skip expensive PRD re-generation

pr_plans_by_prd | The PR plan per PRD — clear this to force replanning

completed_prd_ids | Which PRDs are done — clear if a PRD was incorrectly marked complete

✓ Use Python to edit the state file — manual JSON editing is error-prone and inconsistent:

python3 - <<'EOF'

import json, pathlib

state_dir = pathlib.Path('/path/to/workspace/engineer/state/threads')

for f in state_dir.glob('*.json'):

data = json.loads(f.read_text())

data['pr_plans_by_prd'] = {}

data['completed_pr_nums_by_prd'] = {}

data['completed_prd_ids'] = []

data['in_progress_pr'] = {}

f.write_text(json.dumps(data, indent=2))

EOF

## 7.2  GitHub JSON Backup Prevents Re-planning

✗ The agent also commits PR plan JSON to the prds branch on GitHub as a recovery backup. If this file exists when the agent starts, it restores the old plan even if the local state was cleared.

✓ After clearing the local state, also delete the GitHub backup: prds/{subsystem-slug}/prd-NNN-pr-plan.json on the prds branch.

# 8.  Quick Reference — Do and Don't

Convert draft → ready | ✓  GraphQL markPullRequestReadyForReview mutation | ✗  REST PATCH {draft: false} — silently ignored

Merge a PR | ✓  Check pr.draft first; undraft via GraphQL if needed | ✗  Call pr.merge() directly on a draft — returns 405

Docs-only PR CI | ✓  docs-check.yml with paths: filter + ready_for_review type | ✗  Wait for ci.yml — it is skipped, never passes

Workflow triggers | ✓  types: [opened, synchronize, reopened, ready_for_review] | ✗  Omit ready_for_review — draft→ready won't trigger checks

CI skip interpretation | ✓  Treat 'skipped' conclusion as passing | ✗  Block on skipped checks — they are intentional

Commit .github/ | ✓  Add .github to allowed roots explicitly | ✗  Rely on generic path guard — dot-prefix is rejected

Multi-file PRs | ✓  --- path --- delimiter format with explicit instruction | ✗  Ask LLM for multiple files without format guidance

State reset | ✓  Python script editing JSON fields precisely | ✗  Manual JSON editing — inconsistent and error-prone

YouSource.ai  ·  Crafted Dev Agent  ·  March 2026