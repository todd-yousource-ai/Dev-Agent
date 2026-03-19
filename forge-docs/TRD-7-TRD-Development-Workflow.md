# TRD-7-TRD-Development-Workflow

_Source: `TRD-7-TRD-Development-Workflow.docx` — extracted 2026-03-19 22:01 UTC_

---

TRD-7

TRD Development Workflow

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-7: TRD Development Workflow
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-2 (Consensus Engine — generates TRD content), TRD-5 (GitHub — commits TRDs)
Required by | Nothing — independent feature module triggered by /trd start
Language | Python 3.12
Trigger | User command: /trd start
Output | Structured TRD documents (.docx + .md), PRODUCT_CONTEXT.md, committed to GitHub

# 1. Purpose and Scope

This document specifies the complete technical requirements for the TRD Development Workflow — a structured, AI-facilitated process that guides a person from a raw product idea to a complete set of implementation-ready Technical Requirements Documents.

The core problem this workflow solves: most people who want to build software have an idea, not a specification. They think in features and use cases, not interfaces and error contracts. They skip dependencies, leave security implicit, and do not know what they do not know. An AI that simply asks "what do you want to build?" produces vague outputs.

This workflow is a design facilitator. It knows what questions to ask, in what order, and when enough has been said to write a section. It surfaces gaps, resolves contradictions, and produces TRDs that an AI agent — or a human engineer — can build from without ambiguity.

WHAT THIS IS NOT | TRD-7 is not a code generator. It does not build software. It builds the specifications that TRD-3's build pipeline uses to build software. The output of TRD-7 is the input to the rest of the system.

The workflow owns:

Eight structured phases from product vision through TRD generation

Dynamic question generation — Claude asks the right follow-up questions based on what has been said, not a fixed script

Question taxonomy — a coverage map ensuring every TRD domain is addressed for every component

Completion signals — knowing when enough information has been gathered to write a section

Gap detection — identifying missing interfaces, error contracts, and ownership ambiguities before writing

TRD outline for operator review before full generation begins

TRD generation using the Consensus Engine with the session transcript as context

Per-TRD iterative refinement — targeted correction without full regeneration

PRODUCT_CONTEXT.md synthesis — the platform context document loaded into every future build

Session persistence — sessions span hours or days with full resume support

# 2. Design Decisions

Decision | Choice | Rationale
Question generation | Dynamic — Claude generates questions from context | A fixed questionnaire cannot adapt to what has already been said. A fintech product needs different questions than a developer tool. Dynamic generation with taxonomy coverage checking gives the best of both.
One question at a time | Strictly enforced | Multiple questions in one message overwhelm operators. They answer the last one. One question per message forces the operator to think about each domain.
TRD outline before generation | Required — operator must approve | Writing full TRDs before the operator has confirmed the structure wastes significant API cost. The outline catches misaligned scope early.
Consensus Engine for TRD content | Claude + GPT-4o, Claude arbitrates | Same pattern as TRD-3. TRD generation benefits from two perspectives — one might catch gaps the other misses. Claude arbitrates for consistency.
Per-TRD approval gate | Operator approves each TRD before the next starts | Surfacing a full TRD set at once is overwhelming. Per-TRD approval keeps the operator engaged and catches issues while the context is fresh.
Session transcript as primary context | Full transcript included in generation prompt | The transcript contains the rationale behind every decision. Summarising it loses the "why" that makes TRDs useful. Token cost is justified.
PRODUCT_CONTEXT.md as first deliverable | Generated before any TRD | This one-page summary is the most reusable artifact. It feeds every subsequent build and is immediately valuable to the operator.
Targeted correction vs full regeneration | Section-level correction by default | Full TRD regeneration on every correction is expensive and disruptive. Targeted section regeneration preserves approved content.

# 3. Session Phases

## 3.1 Phase Overview

TRD DEVELOPMENT SESSION — 8 PHASES

/trd start
    │
    ▼
Phase 1: Product Vision (15–30 min)
    What are you building? Who uses it? What problem does it solve?
    What does success look like? What are the non-negotiables?
    Output: product_vision (dict)
    │
    ▼
Phase 2: Architecture Discovery (20–40 min)
    What are the technical layers? What external systems are involved?
    Where does data come from and where does it go?
    What runs where? Who authenticates?
    Output: architecture_sketch (dict)
    │
    ▼
Phase 3: TRD Boundary Definition (15–25 min)
    Based on what we know: what are the natural component boundaries?
    Claude proposes TRD list. Operator approves, merges, splits, removes.
    Output: trd_boundaries (list[TRDBoundary])
    │
    ▼
Phase 4: Per-TRD Deep Dive (30–60 min per TRD)
    For each boundary: structured questions covering all 9 taxonomy domains.
    Claude tracks coverage, asks follow-up questions, flags thin areas.
    Output: per-TRD notes (dict per boundary)
    │
    ▼
Phase 5: Gap Detection (10–20 min)
    Claude analyses the collected notes for gaps:
    missing interfaces, error contracts, ownership ambiguities.
    Each gap surfaced as one specific question.
    Output: gap_resolutions (dict)
    │
    ▼
Phase 6: TRD Outline Review (15–20 min)
    Claude synthesises one-paragraph scope summary per TRD.
    Shows dependency graph. Operator approves, corrects, removes.
    Output: approved_outlines (list[TRDOutline])
    │
    ▼
Phase 7: PRODUCT_CONTEXT.md Generation
    Synthesise product summary, TRD index, architecture overview.
    Commit to GitHub. Load into doc store.
    Output: PRODUCT_CONTEXT.md committed
    │
    ▼
Phase 8: TRD Generation (variable — per TRD)
    Generate each TRD via Consensus Engine.
    Export .docx + .md. Commit to GitHub.
    Per-TRD approval gate before next TRD starts.
    Iterative refinement on corrections.
    Output: complete TRD set committed to GitHub
    │
    ▼
SESSION COMPLETE
    Summary: N TRDs generated, total pages, total cost, GitHub links.

## 3.2 TRDSession Dataclass

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class SessionPhase(str, Enum):
    VISION        = "vision"
    ARCHITECTURE  = "architecture"
    BOUNDARIES    = "boundaries"
    DEEP_DIVE     = "deep_dive"
    GAP_DETECTION = "gap_detection"
    OUTLINE       = "outline"
    CONTEXT_DOC   = "context_doc"
    GENERATION    = "generation"
    COMPLETE      = "complete"

@dataclass
class TRDSession:
    session_id:         str
    product_name:       str
    phase:              SessionPhase

    # Accumulated conversation (full transcript)
    transcript:         list[dict]    = field(default_factory=list)
    # { "role": "user"|"agent", "content": str, "timestamp": float }

    # Phase outputs
    product_vision:     dict          = field(default_factory=dict)
    architecture_sketch: dict         = field(default_factory=dict)
    trd_boundaries:     list          = field(default_factory=list)
    trd_notes:          dict          = field(default_factory=dict)
    gap_resolutions:    dict          = field(default_factory=dict)
    approved_outlines:  list          = field(default_factory=list)

    # Generation tracking
    generated_trds:     list          = field(default_factory=list)
    active_trd_index:   int           = 0

    # Economics
    total_cost_usd:     float         = 0.0

    # GitHub context
    github_owner:       str           = ""
    github_repo:        str           = ""
    context_doc_path:   Optional[str] = None

    # Lifecycle
    started_at:         float         = 0.0
    updated_at:         float         = 0.0

# 4. Phase 1: Product Vision Interview

## 4.1 Purpose

Establish shared understanding of what is being built before any technical discussion. The agent must resist moving to architecture too early — operators with technical backgrounds instinctively skip to "how" before "what" and "why" are fully resolved.

## 4.2 Opening

# Opening message from the agent when /trd start is called:

OPENING = """
Let's build your technical specification from the ground up.

I'll guide you through a structured process — asking one question at a time,
building up the full picture before we write anything.
At the end, you'll have a complete set of TRDs ready to load into the build system.

This usually takes 2–4 hours depending on product complexity.
You can stop and resume any time with /trd resume.

To start: in one or two sentences, what are you building?
"""

## 4.3 Vision Domain Coverage

Domain | Questions Claude Must Cover | Completion Signal
Problem | What specific problem does this solve? Who has this problem today? How do they solve it now? | Operator has described a clear pain point with a current-state comparison
Users | Who are the primary users? What is their technical level? What environment do they work in? | Primary user persona is clear with at least one concrete example
Product | What does the product do in one sentence? What does it NOT do? What makes it different from existing solutions? | Product boundary is crisp — what is in and what is out
Success | What does success look like in 6 months? What is the single most important metric? | At least one measurable success criterion stated
Non-negotiables | What must never be compromised — security, cost, speed, privacy, uptime? | At least one non-negotiable stated; Claude probes for others
Deployment context | Where does this run — cloud, on-prem, edge, desktop, mobile? | Deployment environment clear enough to inform architecture

## 4.4 Product Vision Output Schema

# product_vision is synthesised by Claude after Phase 1 is complete.
# It is NOT extracted turn-by-turn — Claude synthesises at phase end.

product_vision = {
    "product_name":    str,   # What to call it
    "one_liner":       str,   # One sentence: what it does
    "problem":         str,   # Problem being solved
    "primary_users":   list[str],  # Who uses it
    "differentiator":  str,   # What makes it distinct
    "success_metric":  str,   # How success is measured
    "non_negotiables": list[str],  # Must-haves
    "deployment":      str,   # Where it runs
    "out_of_scope":    list[str],  # Explicit exclusions
}

# 5. Phase 2: Architecture Discovery

## 5.1 Purpose

Map the technical landscape without locking in decisions. The goal is to understand the data flows, external systems, processing boundaries, and auth model well enough to propose TRD boundaries. Architecture Discovery does not define the solution — it surfaces the constraints.

## 5.2 Architecture Domain Coverage

Domain | Questions Claude Must Cover | Completion Signal
Data | What data exists at the start? Where does it come from? What data does the system produce? Who consumes it? | Primary data entities named; flow direction clear
External systems | What APIs, databases, message queues, or services does this connect to? Which are read-only vs read-write? | All external dependencies named; read/write intent stated
Processing model | Is this request-response, event-driven, batch, streaming, or a mix? Where are the long-running operations? | Primary processing pattern identified
State | What must be persisted? Where? For how long? What can be lost if the system crashes? | Persistence requirements and durability expectations stated
Auth | How do users authenticate? How do services authenticate to each other? What is the trust model? | Auth mechanism named; service-to-service trust described
Scale | How many users concurrently? What is the throughput in operations per second? What is the latency requirement? | At least one concrete scale number stated; latency class identified
Operating environment | What platform — cloud provider, on-prem, laptop? Managed services or self-hosted? CI/CD approach? | Enough to make infrastructure decisions

## 5.3 Architecture Sketch Output

architecture_sketch = {
    "data_entities":     list[str],   # Named data objects
    "data_flow":         str,         # Description of how data moves
    "external_systems":  list[dict],  # [{name, type, read_write}]
    "processing_model":  str,         # "request-response" | "event-driven" | ...
    "persistence":       list[dict],  # [{what, where, durability}]
    "auth_model":        str,         # How auth works
    "scale_targets":     dict,        # {concurrent_users, ops_per_sec, latency_ms}
    "platform":          str,         # Deployment platform
    "ascii_diagram":     str,         # ASCII architecture diagram
}

# ascii_diagram is generated by Claude at phase end:
# A simple box-and-arrow diagram showing components and data flow.
# Not exhaustive — just enough to confirm shared understanding.

EXAMPLE_DIAGRAM = """
┌──────────┐    REST    ┌──────────────┐    SQL    ┌──────────┐
│  Mobile  │──────────▶│  API Server  │──────────▶│ Postgres │
│   App    │           │   (Python)   │           │    DB    │
└──────────┘           └──────┬───────┘           └──────────┘
                              │ Events
                              ▼
                       ┌──────────────┐
                       │  Job Queue   │
                       │  (Redis)     │
                       └──────────────┘
"""

# 6. Phase 3: TRD Boundary Definition

## 6.1 Claude Proposes Boundaries

# After Architecture Discovery, Claude proposes TRD boundaries.
# The proposal is based on the principle: one TRD per cohesive technical concern.

BOUNDARY_PROPOSAL_SYSTEM = """
You are defining the boundaries for a set of Technical Requirements Documents.

A good TRD boundary is:
  - A single cohesive technical concern (auth is one TRD, not mixed into everything)
  - Buildable by one engineer in one sprint without needing others to finish first
  - Testable in isolation
  - Has a clear owner (one team or one engineer)

A poor TRD boundary is:
  - Too large: covers multiple concerns that could be separated
  - Too small: one function that belongs in a larger module
  - Circular: TRD A depends on TRD B which depends on TRD A

Based on the product vision and architecture sketch provided, propose a TRD list.
For each TRD, provide:
  - title: short, clear name
  - scope: one paragraph — what this TRD owns and what it does NOT own
  - depends_on: which other TRDs must be specified first
  - build_order: integer (1 = build first)

Respond in JSON only.
"""

## 6.2 TRDBoundary Dataclass

@dataclass
class TRDBoundary:
    trd_id:      str          # "TRD-1", "TRD-2", etc.
    title:       str          # "Authentication Layer"
    scope:       str          # One-paragraph scope description
    depends_on:  list[str]    # TRD IDs that must be written first
    build_order: int          # Build sequence (1 = first)
    approved:    bool = False  # Operator approval

    # Set during Phase 4
    notes:       dict = field(default_factory=dict)  # Taxonomy domain → content
    coverage:    dict = field(default_factory=dict)  # domain → complete: bool

## 6.3 Boundary Approval Gate

# Claude presents the proposed TRD list as a gate card.
# Operator can:
#   "yes" / "approve" — accept the full list
#   "merge TRD-2 and TRD-3" — Claude merges the two boundaries
#   "split TRD-4 into auth and sessions" — Claude splits into two
#   "remove TRD-5" — remove a boundary the operator considers out of scope
#   "add a TRD for X" — Claude adds a new boundary for the described concern

# After each modification, Claude re-presents the full revised list.
# Final approval gates on "yes" — then Phase 4 begins.

# RULE: Never start Phase 4 without explicit operator approval of the boundary list.
# The boundary list determines everything that follows.

# 7. Phase 4: Per-TRD Deep Dive

## 7.1 Purpose

For each approved TRD boundary, gather enough detail to write the TRD at implementation depth. Claude works through nine taxonomy domains, asking one question at a time, tracking coverage, and probing thin areas before moving on.

## 7.2 Question Taxonomy — Nine Domains

Domain | ID | Questions to Cover | TRD Sections Informed
Ownership | D1 | What does this component exclusively own? What does it delegate? What decisions does it never make? | Section 1 (Purpose and Scope), Section 2 (Out of Scope)
Interfaces | D2 | What calls into this component? What does it call out to? What is the exact method/event/message format for each? | Section 4 (Public API), Section 5 (Integration)
Data Model | D3 | What data does this component store? In what format? With what schema? What is the retention policy? | Section 3 (Data Model), Appendix A (Schema Reference)
Authentication and Security | D4 | Who can call into this? How are callers authenticated? What is the trust model? What data must be encrypted? | Security Requirements section
Error Handling | D5 | What happens when each external dependency fails? What errors does this component surface? Retry or fail-fast? | Error Taxonomy section, Error Handling Contract
State and Lifecycle | D6 | What are the valid states? What triggers each transition? What is persisted at each checkpoint? How is state recovered after a crash? | State Machine section
Configuration | D7 | What is configurable vs hardcoded? Where is configuration stored? Who can change it at runtime? | Configuration section, Settings schema
Scale and Performance | D8 | What are the throughput requirements? What is the latency budget? What degrades gracefully under load? What breaks? | Performance Requirements section
Testing and Observability | D9 | How is this component tested in isolation? What are the critical test cases? What logs, metrics, and traces are emitted? | Testing Requirements, Logging section

## 7.3 Per-Domain Question Generation

DEEP_DIVE_SYSTEM = """
You are conducting a structured technical interview to gather information
for a Technical Requirements Document.

The TRD being specified:
  Title: {trd_title}
  Scope: {trd_scope}

You are working through nine taxonomy domains. Current domain: {domain_name}.

Coverage so far for this domain:
{coverage_summary}

Full conversation so far:
{transcript_excerpt}

RULES:
1. Ask exactly ONE question.
2. The question must address a gap in the current domain coverage.
3. If the current domain has sufficient coverage (see completion signals),
   announce moving to the next domain and ask the first question there.
4. Never ask a question that was already asked in the transcript.
5. Frame questions concretely, not abstractly.
   BAD:  "What are your security requirements?"
   GOOD: "When service A calls service B, how does B verify that A is authorised
          to make that call?"
6. If the operator says "I don't know yet" or "that's TBD":
   Accept it, note it as a gap, move on. Do NOT push for an answer
   that does not exist yet.

Ask your next question now. Nothing else.
"""

## 7.4 Coverage Tracking

# After each operator response, Claude updates coverage for the active domain.
# Coverage is tracked as a dict: domain_id → {"complete": bool, "notes": str}

COVERAGE_CHECK_SYSTEM = """
Given the conversation so far for domain {domain_name},
assess whether sufficient information exists to write the corresponding
TRD sections.

Respond in JSON:
{
    "complete": true | false,
    "missing": ["specific missing information if not complete"],
    "summary": "2-3 sentence summary of what was learned"
}
"""

# Coverage check runs after every 2-3 operator responses in a domain.
# If complete: Claude announces moving to next domain.
# If "I don't know" responses accumulate: mark as "thin — acknowledged gap",
#   flag in Phase 5 gap detection, and move on.

THIN_COVERAGE_THRESHOLD = 3  # After 3 "IDK" responses, move on and flag

## 7.5 Transition Between TRDs

# When all 9 domains are covered (or thinly covered and acknowledged)
# for the current TRD boundary, Claude:
#
# 1. Presents a one-paragraph summary of what was learned about this TRD.
# 2. Highlights any thin areas and what the TRD will say about them.
# 3. Asks: "Anything to add or correct before we move to {next_trd}?"
# 4. On approval: saves notes, starts Phase 4 for the next TRD boundary.

# TRDs are covered in build_order sequence.
# Rationale: earlier TRDs' interfaces inform later TRDs' questions.
# Example: TRD-1 (Auth) establishes the token format that TRD-2 (API) uses.

# 8. Phase 5: Gap Detection and Resolution

## 8.1 Gap Detection Analysis

GAP_DETECTION_SYSTEM = """
You have completed per-TRD deep dives for all TRD boundaries.
Now analyse the collected notes for gaps that must be resolved before
writing the TRDs.

Look for:

1. MISSING INTERFACES
   TRD-A's notes say it calls TRD-B's {method_name}, but TRD-B's notes
   do not mention that method. Someone will be surprised when building.

2. MISSING ERROR CONTRACTS
   TRD-A calls TRD-B, but neither TRD specifies what happens when TRD-B fails.
   Does TRD-A retry? Fall back? Propagate the error? Show a gate?

3. OWNERSHIP AMBIGUITY
   Two TRDs both claim to own the same data or make the same decision.
   Example: both TRD-2 and TRD-4 mention storing user preferences.

4. CIRCULAR DEPENDENCIES
   TRD-A depends on TRD-B which depends on TRD-A.
   Cannot build either without the other.

5. UNRESOLVED "IDK" AREAS
   Domains marked as "thin" where the operator said they don't know yet.
   These need a decision before the TRD can specify them.

6. IMPLICIT SECURITY ASSUMPTIONS
   A component handling sensitive data that has no auth/encryption specified.

For each gap found, produce one specific, answerable question.
Maximum 10 gaps — prioritise the highest-impact ones.

Respond in JSON:
[
  {
    "gap_type": "missing_interface | error_contract | ownership | circular | idk | security",
    "description": "Specific description of the gap",
    "affects_trds": ["TRD-1", "TRD-2"],
    "question": "The single specific question to resolve this gap"
  }
]
"""

## 8.2 Gap Resolution Protocol

# Claude presents gaps one at a time — never all at once.
# For each gap:
#   1. State the gap briefly: "I noticed a gap between TRD-2 and TRD-4..."
#   2. Ask the specific resolution question.
#   3. Record the response in gap_resolutions[gap_id].
#   4. Confirm: "Got it — {brief summary of what was decided}."
#   5. Move to next gap.

# If operator says "skip this" or "TBD": record as acknowledged gap.
# The TRD will document the gap as an Open Question.

# After all gaps resolved: proceed to Phase 6 (TRD Outline Review).

# 9. Phase 6: TRD Outline Review

## 9.1 Outline Generation

OUTLINE_SYSTEM = """
Generate a TRD outline for each approved boundary.
The outline will be reviewed by the operator before full TRD generation.

For each TRD, produce:
  - title: the TRD title
  - scope_paragraph: one paragraph — exactly what this TRD specifies and what it does not
  - key_interfaces: bullet list of the primary interfaces this TRD defines
  - depends_on: which other TRDs must be complete before this one
  - estimated_sections: list of section headings for the full TRD
  - open_questions: any acknowledged gaps that will appear as open questions

The outline must be consistent across all TRDs:
  - No two TRDs claim ownership of the same interface
  - Dependencies form a directed acyclic graph
  - Every interface mentioned in one TRD is owned by another TRD

Respond in JSON only.
"""

## 9.2 Outline Presentation Format

# Outline is presented to operator as a formatted card in the stream.
# NOT as raw JSON — formatted for human reading.

EXAMPLE OUTLINE OUTPUT:

═══ TRD OUTLINE FOR REVIEW ═══════════════════════════════

TRD-1: Authentication Layer
  Scope: Owns all user identity operations — registration, login, token
  issuance, token validation, and session lifecycle. Does NOT own
  authorisation decisions (who can do what) — that is TRD-3.
  Key interfaces:
    • POST /auth/login → {access_token, refresh_token, expires_in}
    • POST /auth/refresh → {access_token}
    • GET  /auth/verify → {user_id, claims} (internal only)
  Depends on: None
  Sections: Overview, Token Schema, Login Flow, Refresh Protocol,
            Session Expiry, Error Contract, Security Requirements,
            Testing Requirements

TRD-2: API Gateway
  Scope: Owns routing, rate limiting, and request authentication for
  all external API calls. Delegates auth token validation to TRD-1.
  ...

════════════════════════════════════════════════════════════
Dependency order: TRD-1 → TRD-3 → TRD-2 → TRD-4

Approve this outline? (yes / [corrections])

## 9.3 Outline Correction Protocol

# If operator provides corrections:
# Claude incorporates them and re-presents the affected TRDs only.
# Not the full outline again — just what changed.

# Correction types accepted:
#   "move X from TRD-2 to TRD-3" — ownership transfer
#   "TRD-4 needs a section on caching" — add section to estimated_sections
#   "the interface should return Y not Z" — interface correction
#   "merge TRD-5 and TRD-6" — boundary merge
#   "split TRD-3 into auth and RBAC" — boundary split

# After corrections, Claude shows only the changed TRDs with a summary:
# "I've updated TRD-2 and TRD-3. Here is what changed: [diff summary]."
# Then asks for approval again.

# 10. Phase 7: PRODUCT_CONTEXT.md Generation

## 10.1 Purpose

The PRODUCT_CONTEXT.md is the platform context document that the Consensus Engine (TRD-2 Section 6.3) injects into every code generation prompt. It is the single-page answer to "what system am I building?" — grounding every future AI-generated implementation in the product's architectural intent.

## 10.2 Content

CONTEXT_DOC_SYSTEM = """
Generate a PRODUCT_CONTEXT.md document.
This document will be loaded into an AI code generation system
and injected into every code generation prompt.
It must be concise, precise, and permanently useful.

Include:
  1. Product name and one-liner
  2. Problem being solved (2-3 sentences)
  3. Primary users
  4. Architecture overview (the ASCII diagram from Phase 2)
  5. Key technical decisions and their rationale
     (e.g. "We use PostgreSQL not MongoDB because X")
  6. TRD index — one line per TRD with its scope
  7. Non-negotiables that every implementation must respect
  8. What is explicitly out of scope

Length: 500-800 words. No fluff. Every sentence must be load-bearing.
Format: markdown. Use headers and bullet lists.
"""

# PRODUCT_CONTEXT.md is committed to GitHub:
# Path: forge-docs/PRODUCT_CONTEXT.md on default branch
# Also written to: ~/Library/Application Support/ForgeAgent/projects/{project_id}/docs/
# Where it is auto-loaded into the doc store for the project.

# 11. Phase 8: TRD Generation

## 11.1 Generation System Prompt

TRD_GENERATION_SYSTEM = """
You are writing a Technical Requirements Document (TRD).

A TRD specifies a software component at implementation depth.
Engineers — human or AI — must be able to build the component from
this document without making architectural decisions themselves.

A complete TRD includes:
  - Purpose and scope (what is owned and what is not)
  - All public interfaces with parameter types, return types, and errors
  - Data schemas for everything stored or transmitted
  - State machines for anything with lifecycle
  - Security requirements: auth, encryption, validation
  - Error handling: what to do when each dependency fails
  - Performance requirements: latency, throughput, memory
  - Testing requirements: what to test, critical test cases
  - Out of scope: explicit list of things this TRD does NOT cover
  - Open questions: decisions not yet made

Style rules:
  - Code examples for every interface — not just prose descriptions
  - Tables for: enums, error types, configuration, performance targets
  - Callout boxes for: critical requirements, security rules, non-negotiables
  - No vague language: "should", "may", "can" must be replaced with
    "must", "must not", or "is not supported"

Produce the TRD in structured markdown.
Use ## for major sections, ### for subsections.
Code blocks for all code, schemas, and structured data.
"""

## 11.2 Generation User Prompt

def _build_trd_generation_prompt(
    outline:      "TRDOutline",
    session:      TRDSession,
    prior_trds:   list[str],  # Content of already-generated TRDs
) -> str:
    """Build the user prompt for TRD generation."""

    # Session transcript is included in full.
    # Rationale for decisions is in the transcript.
    # Summaries lose the "why" that makes TRDs useful.
    transcript_text = _format_transcript(session.transcript)

    # Prior TRDs provide interface definitions this TRD depends on.
    prior_context = ""
    if prior_trds:
        prior_context = "Already-generated TRDs (interface reference):\n"
        for trd_content in prior_trds[-3:]:  # Last 3 — most relevant
            prior_context += trd_content[:4000] + "\n---\n"

    return f"""Write {outline.title}.

TRD Scope (approved by operator):
{outline.scope_paragraph}

Key interfaces to specify:
{chr(10).join(f"  - {i}" for i in outline.key_interfaces)}

Sections to include:
{chr(10).join(f"  {i+1}. {s}" for i,s in enumerate(outline.estimated_sections))}

Open questions to document:
{chr(10).join(f"  - {q}" for q in outline.open_questions) or "None"}

{prior_context}

Full design session transcript:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write the complete TRD now. Do not summarise — write the full specification.
Include code examples for all interfaces.
Use tables for all enumerated options, configurations, and error types."""

## 11.3 Per-TRD Approval Gate

# After each TRD is generated:
# 1. Export as .docx and .md
# 2. Commit to GitHub: trd-specs/{trd_id}-{title_slug}.md
# 3. Show operator a card: "TRD-{N}: {Title} is ready. Open to review."
# 4. Present gate:

gate = {
    "gate_type": "trd_review",
    "gate_id":   f"trd-review-{outline.trd_id}",
    "title":     f"{outline.trd_id}: {outline.title} — Review",
    "body":      f"Exported to {docx_path}\nCommitted to {github_path}",
    "options":   ["approve", "correct", "expand"],
}

# Response routing:
# "approve"  → mark TRD as complete, start next TRD
# "correct"  → operator provides correction text:
#              targeted regeneration of affected sections only
# "expand"   → operator describes what to add:
#              Claude asks clarifying questions, then adds the section

# 12. Iterative Refinement

## 12.1 Correction Protocol

# Targeted correction — not full TRD regeneration.
# Operator: "The error handling in Section 7 is wrong — it should retry, not fail-fast."

async def _apply_correction(
    trd_content: str,
    correction:  str,
    outline:     TRDOutline,
    consensus:   ConsensusEngine,
) -> str:
    """Apply a targeted correction to a generated TRD."""

    system = """You are correcting a specific section of a Technical Requirements Document.
    Apply ONLY the stated correction.
    Do not change sections not mentioned in the correction.
    Do not add new content beyond what the correction specifies.
    Output the complete corrected TRD — not just the changed section.
    """

    user = f"""Correction to apply: {correction}

Current TRD content:
{trd_content}

Apply the correction and output the complete corrected TRD."""

    result = await consensus.run(
        task=user,
        task_type="prd",
        system=system,
    )
    return result.winner_content

## 12.2 Expansion Protocol

# Expansion — adding a new section the operator identified as missing.
# Operator: "We need a section on caching strategy."

# Step 1: Claude asks clarifying questions for the new section.
# (Same per-domain question protocol as Phase 4, scoped to the new topic.)

# Step 2: After sufficient clarification, Claude writes the new section.

# Step 3: Claude presents the new section for approval.
# "Here is the new Caching Strategy section. Approve or correct?"

# Step 4: On approval, Claude inserts the section into the TRD
# in the natural position and re-exports the .docx.

# Max clarifying questions for expansion: 5.
# After 5, Claude writes the section with what it has and flags gaps
# as open questions.

# 13. Question Generation Protocol

## 13.1 One Question at a Time — Enforcement

# The one-question rule is enforced at the generation level, not by convention.

QUESTION_VALIDATION_SYSTEM = """
The following message is about to be sent to the operator.
It must contain exactly ONE question.

Count the question marks. If there is more than one question mark,
rewrite the message to ask only the most important question.
Move the other questions to a list of pending questions for later.

If the message contains no question, rewrite it to end with a question.

Message to validate:
{draft_message}

Return the validated message with exactly one question.
"""

# All agent messages pass through this validation before being sent.
# The exception: the TRD outline presentation (not a question — a gate card).

## 13.2 Question Quality Rules

# Questions must be concrete, not abstract.
# The agent is trained on these anti-patterns:

ANTI_PATTERNS = [
    ("What are your security requirements?",
     "When service A makes a call to service B, how does B verify that A is allowed?"),

    ("What is the data model?",
     "What information does the system store about each user account?"),

    ("How should errors be handled?",
     "If the payment service is unreachable, should the checkout request fail
      immediately or retry? And if retry, how many times and with what backoff?"),

    ("What are the performance requirements?",
     "What is the maximum acceptable latency for a login request in your product?"),

    ("Tell me about authentication.",
     "How do mobile app users prove their identity — username and password,
      social login, passkeys, or something else?"),
]

# The QUESTION_GENERATION_SYSTEM includes these anti-patterns
# as negative examples that Claude must not produce.

## 13.3 "I Don't Know" Handling

# When the operator says they don't know:
# 1. Accept it — never push for an answer that does not exist.
# 2. Offer the most common industry default: "The most common approach is X.
#    Would that work for your situation, or is this genuinely TBD?"
# 3. If TBD: record as acknowledged gap, mark domain as thin, move on.
# 4. The TRD will document it as an Open Question.

IDK_RESPONSES = [
    "i don't know", "idk", "tbd", "not sure", "haven't decided",
    "good question", "we haven't figured that out",
    "that's TBD", "need to think about that",
]

# Detected by substring match (case-insensitive).
# If detected: offer default, then accept if still TBD.

# 14. Completion Signals

## 14.1 Phase Completion Signals

Phase | Signal — Claude Knows Phase Is Complete When... | Minimum Threshold
Phase 1 (Vision) | All 6 vision domains have at least one concrete answer | Product name, one-liner, and primary user type are clear
Phase 2 (Architecture) | All 7 architecture domains covered; ASCII diagram generated | At least 3 external systems or components named; data flow direction clear
Phase 3 (Boundaries) | Operator explicitly approves the TRD boundary list | Boundary list has operator "yes"
Phase 4 per TRD | All 9 taxonomy domains are either complete or thin-acknowledged | At least 6 of 9 domains have substantive coverage
Phase 5 (Gaps) | All detected gaps have been asked about and answered (or acknowledged as TBD) | All gaps that affect interface compatibility are resolved
Phase 6 (Outline) | Operator explicitly approves the full TRD outline | Operator "yes" or "approve" with no outstanding corrections
Phase 7 (Context Doc) | PRODUCT_CONTEXT.md committed to GitHub and loaded into doc store | File exists at forge-docs/PRODUCT_CONTEXT.md
Phase 8 per TRD | Operator approves the generated TRD | Operator "approve" with no pending corrections

## 14.2 Domain Completion Signals

Domain | Completion Signal
D1 Ownership | Scope statement written; at least 2 things explicitly out of scope named
D2 Interfaces | At least one inbound interface and one outbound interface named with method signature; error case stated for each
D3 Data Model | Primary entity named; at least 3 fields described; storage type identified
D4 Auth/Security | Who can call in is stated; how they authenticate is stated; one sensitive data item and its protection stated
D5 Error Handling | What happens when each named external dependency fails is stated; retry vs fail-fast decision made
D6 State/Lifecycle | Either: no state (stateless component), or: at least 2 states named with one transition
D7 Configuration | At least 2 configurable items named; where they are stored stated
D8 Performance | At least one latency target stated; at least one throughput or scale number stated
D9 Testing | At least 3 critical test cases described; key mock or stub dependencies named

# 15. Product Context Document

## 15.1 PRODUCT_CONTEXT.md Template

# Generated by TRD Development Workflow — do not edit manually.
# This document is loaded into the AI code generation system
# and injected into every code generation prompt.

# {PRODUCT_NAME}

## What We're Building
{one_liner}

{problem_statement}

## Who Uses It
{primary_users}

## Architecture Overview
```
{ascii_diagram}
```

## Key Technical Decisions
{key_decisions_bullet_list}
# Example entries:
# - Authentication uses JWT RS256, not sessions, because the API must support
#   both web and mobile clients without shared session state.
# - PostgreSQL not MongoDB because the data model is relational and
#   ACID compliance is a non-negotiable for financial records.

## TRD Index
| TRD | Title | Scope |
|-----|-------|-------|
| TRD-1 | {title} | {one_line_scope} |
| TRD-2 | {title} | {one_line_scope} |

## Non-Negotiables
{non_negotiables_bullet_list}
# Example:
# - No plaintext secrets on disk — ever
# - Operator must approve all merges — never auto-merge
# - All financial operations must be idempotent

## Out of Scope
{out_of_scope_bullet_list}

## 15.2 Loading into Doc Store

# After committing PRODUCT_CONTEXT.md to GitHub:
# Load it into the project doc store automatically.

async def _load_context_doc_to_store(
    session:   TRDSession,
    doc_store: DocumentStore,
    github:    GitHubTool,
) -> None:
    """Fetch PRODUCT_CONTEXT.md from GitHub and add to doc store."""
    content = github.get_file("forge-docs/PRODUCT_CONTEXT.md")
    doc_store.add_document(
        name="PRODUCT_CONTEXT.md",
        content=content,
        metadata={"type": "platform_context", "auto_loaded": True}
    )
    logger.info("PRODUCT_CONTEXT.md loaded into doc store")
    # This becomes the PLATFORM_CONTEXT.md referenced in TRD-2 Section 6.3.
    # From this point forward, every code generation prompt includes
    # this document as platform context.

# 16. TRD Generation System Prompts

## 16.1 Section-Level Correction Prompt

# Used in Phase 8 iterative refinement.
# Operates on a single section, not the full TRD.

SECTION_CORRECTION_SYSTEM = """
You are correcting a specific section of a TRD.

Apply ONLY the stated correction.
Rules:
  1. Do not change sections not mentioned in the correction.
  2. Do not add new sections beyond what was requested.
  3. Do not alter interfaces, data schemas, or error contracts
     in other sections as a side effect.
  4. If the correction reveals a contradiction with another section:
     flag it in a callout box — do not silently resolve it.
  5. Output the complete corrected TRD, not just the changed section.
"""

## 16.2 Section Expansion Prompt

SECTION_EXPANSION_SYSTEM = """
You are adding a new section to an existing TRD.

Rules:
  1. The new section must be consistent with existing sections.
  2. If the new section defines an interface: check that no other section
     already defines the same interface with different semantics.
  3. Insert the section in the logically correct position in the document.
  4. If you need to reference something not yet specified:
     document it as an open question.
  5. Output the complete TRD with the new section inserted.
"""

# 17. CommandRouter Integration

Command | Arguments | Description
/trd start | [product name] | Begin a new TRD development session. If product name provided, uses it; otherwise asks.
/trd resume | [session_id] | Resume an incomplete session. If multiple incomplete sessions exist, lists them.
/trd status | — | Show current phase, coverage progress per TRD, cost to date.
/trd outline | — | Show the current approved TRD outline (or in-progress if not yet approved).
/trd generate | <trd-id> | Generate a specific TRD (must be in approved outline).
/trd generate all | — | Generate all approved TRDs in build_order sequence with per-TRD approval gates.
/trd export | — | Export all generated TRDs as .docx files. Opens output directory.
/trd open | <trd-id> | Open the generated .docx for a specific TRD in macOS default app.
/trd context | — | Show the current PRODUCT_CONTEXT.md content in the stream.
/trd skip | <domain> | Skip a taxonomy domain for the current TRD — mark as TBD and move on.
/trd cost | — | Show cost breakdown: per-phase, per-TRD, total.

## 17.1 _handle_trd() Handler

async def _handle_trd(self, raw: str) -> bool:
    """Handle /trd commands. Max complexity: 10."""
    parts = raw.strip().split(maxsplit=2)
    sub   = parts[1].lower() if len(parts) > 1 else "status"

    dispatch = {
        "start":    self._trd_start,
        "resume":   self._trd_resume,
        "status":   self._trd_status,
        "outline":  self._trd_outline,
        "generate": self._trd_generate,
        "export":   self._trd_export,
        "open":     self._trd_open,
        "context":  self._trd_context,
        "skip":     self._trd_skip,
        "cost":     self._trd_cost,
    }
    fn = dispatch.get(sub)
    if fn is None:
        self.ctx.emit_card({"card_type":"guidance",
            "body": "Unknown /trd subcommand. Try /trd start, resume, status, outline,",
                   " generate, export, open, context, skip, cost."})
        return False
    return await fn(parts[2] if len(parts) > 2 else "")

# 18. TRDSession Persistence

## 18.1 Storage

# TRDSession is persisted to:
# ~/Library/Application Support/ForgeAgent/trd-sessions/{session_id}.json

# The session_id is a slug derived from the product name:
# "{product_slug}-{YYYY-MM-DD}"
# Example: "payment-engine-2026-03-19"

# Persistence points:
#   - After every operator response (transcript updated)
#   - After each phase completes (phase updated)
#   - After each TRD is generated (generated_trds updated)

# Atomic write (tmp → rename) same as ThreadStateStore (TRD-3 Section 4.3)

# Session listing for /trd resume:
def list_incomplete_sessions() -> list[dict]:
    """List all TRD sessions not yet in COMPLETE phase."""
    sessions = []
    session_dir = _session_dir()
    for f in session_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("phase") != "complete":
                sessions.append({
                    "session_id":   data["session_id"],
                    "product_name": data["product_name"],
                    "phase":        data["phase"],
                    "updated_at":   data["updated_at"],
                })
        except Exception:
            continue
    return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

## 18.2 Resume Protocol

async def _trd_resume(self, args: str) -> bool:
    """Resume an incomplete TRD session."""
    sessions = list_incomplete_sessions()

    if not sessions:
        self.ctx.emit_card({"card_type":"guidance",
            "body": "No incomplete TRD sessions found. Use /trd start to begin."})
        return False

    if len(sessions) == 1:
        session_id = sessions[0]["session_id"]
    elif args:
        # Operator specified session ID
        session_id = args.strip()
    else:
        # Show list and ask
        self.ctx.emit_gate({
            "gate_type": "session_select",
            "title":     "Resume which session?",
            "body":      _format_session_list(sessions),
            "options":   [s["session_id"] for s in sessions],
        })
        return False

    session = _load_session(session_id)
    if session is None:
        self.ctx.emit_card({"card_type":"error",
            "body": f"Session {session_id!r} not found."})
        return False

    # Re-orient the operator
    self.ctx.emit_card({
        "card_type": "progress",
        "body": f"Resuming: {session.product_name}\n"
               f"Phase: {session.phase.value}\n"
               f"Last active: {_format_time(session.updated_at)}",
    })

    # Show last exchange from transcript
    if session.transcript:
        last = session.transcript[-1]
        self.ctx.emit_card({
            "card_type": "progress",
            "body": f"Last exchange:\n{last['content'][:400]}",
        })

    # Continue from current phase
    await self.trd_director.continue_session(session)
    return False

# 19. Testing Requirements

Module | Coverage Target | Critical Test Cases
TRDSession persistence | 95% | Round-trip save/load; atomic write (no .tmp after save); list_incomplete_sessions excludes complete sessions; resume loads correct phase
Question validation (one question rule) | 100% | Message with 2 questions → reduced to 1; message with 0 questions → question added; single question passes unchanged
Coverage tracking | 90% | Domain marked complete when completion signal met; thin domain acknowledged after 3 IDK responses; coverage check fires every 3 responses
Gap detection | 85% | Missing interface detected (A calls B.method, B has no method); ownership ambiguity detected (same entity in 2 TRDs); circular dependency detected; IDK gaps flagged
TRD outline generation | 90% | One paragraph per boundary; depends_on forms valid DAG; all key interfaces listed; open questions included
_apply_correction | 90% | Correction applied to target section; other sections unchanged; contradiction flagged in callout when detected
list_incomplete_sessions | 100% | Complete sessions excluded; sorted by updated_at descending; corrupt file skipped
PRODUCT_CONTEXT.md generation | 85% | All 8 required sections present; ASCII diagram from Phase 2 included; TRD index correct

## 19.1 Prompt Regression Tests

def test_trd_generation_system_requires_code_examples():
    from trd_workflow import TRD_GENERATION_SYSTEM
    assert "code examples" in TRD_GENERATION_SYSTEM.lower()
    assert "must" in TRD_GENERATION_SYSTEM  # Not "should"

def test_trd_generation_prohibits_vague_language():
    from trd_workflow import TRD_GENERATION_SYSTEM
    guidance = TRD_GENERATION_SYSTEM.lower()
    assert "should" in guidance and "must not" in guidance  # Anti-pattern documented

def test_deep_dive_system_enforces_one_question():
    from trd_workflow import DEEP_DIVE_SYSTEM
    assert "exactly ONE question" in DEEP_DIVE_SYSTEM or "one question" in DEEP_DIVE_SYSTEM.lower()

def test_gap_detection_covers_all_gap_types():
    from trd_workflow import GAP_DETECTION_SYSTEM
    required = ["missing_interface", "error_contract", "ownership", "circular"]
    for gap_type in required:
        assert gap_type in GAP_DETECTION_SYSTEM

def test_correction_system_prohibits_side_effects():
    from trd_workflow import SECTION_CORRECTION_SYSTEM
    assert "ONLY the stated correction" in SECTION_CORRECTION_SYSTEM
    assert "do not change" in SECTION_CORRECTION_SYSTEM.lower()

# 20. Performance Requirements

Metric | Target | Notes
Question generation latency | < 5 seconds | Single Claude call; operator waits for next question
Coverage check (per response) | < 3 seconds | Small assessment call; runs after every 3 responses
Gap detection analysis | < 20 seconds | Analyses all TRD notes; one Claude call
TRD outline generation | < 45 seconds | Two parallel calls + arbitration
PRODUCT_CONTEXT.md generation | < 30 seconds | Single synthesis call
TRD generation (per TRD) | < 3 minutes | Two parallel calls for full TRD; larger than code generation
TRD correction (targeted) | < 90 seconds | One call; section-level not full TRD
Session save | < 100 ms | JSON + atomic file write
Session resume | < 2 seconds | Load + format + emit card
Full session (5 TRDs) | 4–8 hours | Includes operator think time; agent time is ~30 min of that
API cost (5 TRDs, typical) | $8–20 | Depends on transcript length and TRD complexity

# 21. Out of Scope

Feature | Reason | Target
Automated interviewing without operator | The entire value is the human-AI collaboration. Fully automated TRD generation from a brief produces poor specs. | Never
Fixed questionnaire mode | Dynamic question generation is what makes this effective. A fixed questionnaire cannot adapt to what has been said. | Never — use Appendix A as reference, not as a script
Integration with Jira, Confluence, Notion | Export to GitHub is the integration point. Other tool integrations are out of scope. | v2 if requested
Multiple operators in one session | Simultaneous multi-human sessions require coordination that is not in scope. One operator per session. | v2
Video or voice input | Text-only session. Voice transcription would be a UI-layer concern. | TBD
Automatic TRD updates when product changes | TRDs are specifications at a point in time. Tracking changes over time is a separate workflow. | v2
Generating code directly from /trd start | The TRD workflow outputs specifications. Building from them is /prd start (TRD-3). | By design — separate commands
Template-based TRD generation | Templates produce generic TRDs. The interview process produces product-specific TRDs. The interview is the differentiator. | Never as primary path

# 22. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Transcript length: a full session with 5 TRDs may accumulate 15,000–30,000 tokens of transcript. Including the full transcript in every TRD generation prompt is correct but expensive. Should we summarise the transcript by phase after each phase completes? Recommendation: summarise Phase 1 and 2 after Phase 3 starts (product vision and architecture are stable by then). Keep Phase 4 onward at full fidelity. | Engineering | Sprint 1
OQ-02 | Session storage location: currently in Application Support alongside build sessions. Should TRD sessions be in a separate directory and separate from build state? Recommendation: yes — forge-trd-sessions/ in Application Support, distinct from forge-agent/ build state. | Engineering | Sprint 1
OQ-03 | Question quality: the one-question rule and concreteness rule are enforced via the QUESTION_VALIDATION_SYSTEM prompt. Should there be a human-written question bank for common domains (auth, data model, API design) as fallback examples? Recommendation: yes — a QUESTION_EXAMPLES.md loaded into the doc store at session start, giving Claude reference patterns. | Engineering | Sprint 2
OQ-04 | TRD numbering: the generated TRDs are numbered TRD-1, TRD-2, etc. within the session. If the user already has TRDs (e.g. they are adding a new module to an existing system), the numbers may conflict. Should the workflow auto-detect existing TRDs and continue numbering from the last one? Recommendation: yes — check forge-docs/trd-specs/ for existing TRDs on session start and continue the numbering sequence. | Engineering | Sprint 2
OQ-05 | Validation of generated TRDs: after TRD generation, should the workflow run the same gap detection analysis on the generated TRD to check for internal consistency? This would catch cases where the TRD generation introduced new contradictions. Recommendation: yes — run a lightweight consistency check on each generated TRD before presenting the approval gate. | Engineering | Sprint 2

# Appendix A: Question Taxonomy Reference

This taxonomy is a coverage map — not a script. Claude generates questions dynamically. This reference is used to check that all domains have been addressed, not to dictate the exact wording of questions.

Domain | ID | Core Questions | Anti-patterns to Avoid
Ownership | D1 | What does this component exclusively own? What does it delegate to other components? What decisions are explicitly not its job? | "What does this do?" (too broad). "What are the responsibilities?" (abstract)
Interfaces | D2 | What calls into this? What does it call out to? For each: what are the parameters, return values, and error conditions? | "What are the APIs?" (no depth). "How does it integrate?" (vague)
Data Model | D3 | What entities does this store? What are the fields and types? What is the primary key? What indexes are needed? What is the retention policy? | "What data does it handle?" (no schema)
Auth/Security | D4 | How are callers authenticated? What data must be encrypted at rest? At transit? What is the minimal permission set? What audit trail is required? | "What are the security requirements?" (no specifics)
Error Handling | D5 | What happens when each external dependency fails? Retry or fail-fast? Who is notified? What is the user experience of each failure mode? | "How are errors handled?" (no specifics per dependency)
State/Lifecycle | D6 | What states can this component be in? What triggers each transition? What is persisted at each checkpoint? How does it recover from a crash? | "How does state work?" (abstract)
Configuration | D7 | What is configurable? Where is configuration stored? Who can change it? What are the valid ranges and defaults? | "What can be configured?" (no location or validation)
Performance | D8 | What is the acceptable latency for the primary operation? What throughput is required? What degrades gracefully vs fails under load? | "What are the performance requirements?" (no numbers)
Testing | D9 | How is this component tested in isolation? What are the 3 most critical test cases? What dependencies must be mocked? | "How will it be tested?" (no specifics)

# Appendix B: TRD Outline Template

# The following template is the structure Claude produces for each TRD outline entry.
# This is presented to the operator for approval in Phase 6.

## {TRD-N}: {Title}

### Scope
{One paragraph: what this TRD specifies and what it does NOT specify.}

### Key Interfaces
- {Interface 1: name and one-line description}
- {Interface 2: name and one-line description}
- ...

### Depends On
- {TRD-M: what from that TRD this one relies on}
- (None if no dependencies)

### Estimated Sections
1. Purpose and Scope
2. {Section specific to this TRD}
3. {Section specific to this TRD}
...
N-3. Testing Requirements
N-2. Performance Requirements
N-1. Out of Scope
N.   Open Questions

### Open Questions
- {Any acknowledged gaps that will appear as open questions in the TRD}
- (None if all domains were fully covered)

---

## Dependency Graph
{TRD-1} → {TRD-3} → {TRD-2} → {TRD-4}
                  ↘ {TRD-5}

Build order: {TRD-1} first, then {TRD-3}, then {TRD-2} and {TRD-5} in parallel,
             then {TRD-4}.

---
Approve this outline? (yes / [corrections])

# Appendix C: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification