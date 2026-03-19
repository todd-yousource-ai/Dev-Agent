# TRD-4-Multi-Agent-Coordination

_Source: `TRD-4-Multi-Agent-Coordination.docx` — extracted 2026-03-19 15:58 UTC_

---

TRD-4

Multi-Agent Coordination Protocol

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Multi-Agent Coordination Protocol — the system that enables multiple engineers running separate instances of the app to build against the same repository without collision.

The Protocol owns:

The Build Ledger — a GitHub-stored JSON file that is the single source of truth for build state across all engineers

Engineer registry — who is active, what they are building, their last heartbeat

Claim protocol — how an engineer atomically claims a PR using optimistic locking

Heartbeat protocol — how active work is signalled and dead agents are detected

Conflict detection — file overlap warnings before and after PR execution

Live sync — ledger refresh via GitHub webhook or polling

Knowledge notes — free-text engineer observations shared across the team

Journal entries — per-PR build journals stored as GitHub files

# 2. Design Decisions

# 3. Build Ledger v2 Schema

## 3.1 Top-Level Structure

## 3.2 engineer_registry

## 3.3 prd_plan

## 3.4 pr_entries

## 3.5 conflict_log

## 3.6 knowledge_notes

## 3.7 pr_plans_by_prd

# 4. GitHub Storage Protocol

## 4.1 File Locations

## 4.2 SHA-Based Optimistic Locking

## 4.3 Read Protocol

# 5. Ledger Initialisation

## 5.1 When Initialised

The Build Ledger is initialised by Stage 2 (PRDPlanStage) after the operator approves the PRD plan. If a ledger already exists for this repository, the existing data is preserved and the new build is merged in.

## 5.2 initialise() Method

## 5.3 PR Entry Population

# 6. Engineer Registry

## 6.1 Registration

## 6.2 Status Transitions

## 6.3 Identity Sources

# 7. Claim Protocol

## 7.1 claim_next_pr()

## 7.2 claim_specific_pr()

## 7.3 release_claim()

# 8. Heartbeat Protocol

## 8.1 Active Heartbeat

## 8.2 Dead Agent Detection

# 9. PR Entry Lifecycle

## 9.1 Status State Machine

## 9.2 mark_pr_done()

# 10. Conflict Detection

## 10.1 Pre-Start File Overlap Check

## 10.2 log_conflict()

# 11. Live Sync

## 11.1 Sync Strategy

## 11.2 Polling Loop

## 11.3 Webhook Trigger

# 12. Knowledge Notes

## 12.1 Adding a Note

## 12.2 Reading Notes for a PR

# 13. Journal Entries

## 13.1 Journal Format

## 13.2 build_journal_entry()

# 14. BuildLedger Public API

# 15. XPC Integration

## 15.1 ledger_update XPC Message

## 15.2 emit_ledger_update()

# 16. Version Compatibility

# 17. Testing Requirements

## 17.1 Concurrency Test

# 18. Performance Requirements

# 19. Out of Scope

# 20. Open Questions

# Appendix A: Full JSON Schema Reference

## PR Entry Fields

# Appendix B: Document Change Log