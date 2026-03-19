# TRD-5-GitHub-Integration

_Source: `TRD-5-GitHub-Integration.docx` — extracted 2026-03-19 15:58 UTC_

---

TRD-5

GitHub Integration Layer

Technical Requirements Document  •  v1.0

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

# 2. Design Decisions

# 3. Authentication

## 3.1 v1 — Personal Access Token

## 3.2 v2 — GitHub App (Upgrade Path)

## 3.3 Auth Mode Detection

# 4. GitHubTool Public API

## 4.1 File Operations

## 4.2 Branch Operations

## 4.3 Pull Request Operations

## 4.4 CI Operations

## 4.5 Repository Operations

# 5. File Commit Protocol

## 5.1 Path Validation

## 5.2 Content Encoding

## 5.3 File Size Limits

## 5.4 Commit Message Format

## 5.5 SHA-Based Update Protocol

# 6. Branch Namespace Protocol

## 6.1 Naming Convention

## 6.2 Slug Generation

## 6.3 Protected Branch Detection

## 6.4 Branch Deletion

# 7. PR Lifecycle

## 7.1 Sequence

## 7.2 Draft PR Requirement

# 8. PR Description Format

# 9. Rate Limiting and Retry

## 9.1 GitHub Rate Limit Types

## 9.2 Retry Implementation

## 9.3 Conditional Requests (ETag Caching)

# 10. GraphQL API

## 10.1 Scope

GraphQL is used for rich read queries only — specifically to fetch PR status (reviews + check runs + mergeable state) in a single API call instead of three REST calls. All writes remain on the REST API.

## 10.2 PR Status Query

## 10.3 GraphQL Error Handling

# 11. Webhook Receiver

## 11.1 Architecture

## 11.2 HMAC Verification

## 11.3 Event Routing

## 11.4 WebhookReceiver

# 12. CI Workflow Management

## 12.1 Workflow File Location

## 12.2 Language Detection

## 12.3 forge-ci.yml Template

## 12.4 force_update()

# 13. PR Review Ingestion

## 13.1 Scan Protocol

# 14. Error Taxonomy

## 14.1 Error Hierarchy

## 14.2 Error Handling by Caller

# 15. Repository Bootstrap

## 15.1 When Bootstrap Runs

RepoBootstrap.run() is called on the first build start for a repository — before Stage 1 (ScopeStage). It ensures the repository has the minimum infrastructure for the agent to operate.

## 15.2 Bootstrap Operations

# 16. Testing Requirements

## 16.1 Unit Tests

## 16.2 Mock GitHub for Testing

# 17. Performance Requirements

# 18. Out of Scope

# 19. Open Questions

# Appendix A: GitHubTool Method Reference

# Appendix B: Document Change Log