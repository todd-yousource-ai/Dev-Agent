# TRD-7-TRD-Development-Workflow-Crafted

_Source: `TRD-7-TRD-Development-Workflow-Crafted.docx` — extracted 2026-03-26 16:30 UTC_

---

TRD-7: TRD Development Workflow

Technical Requirements Document — v2.0

Field | Value
Product | Crafted
Document | TRD-7: TRD Development Workflow
Version | 2.0
Status | Updated — Product Vision Expansion (March 2026)
Author | YouSource.ai
Previous Version | v1.0 (2026-03-19)
Depends on | TRD-2 (Consensus Engine), TRD-5 (GitHub), TRD-10 (Document Store)
Required by | Nothing — independent feature module triggered by /trd start

# What Changed from v1.0

v1.0 specified the TRD workflow for a technical operator — someone who understands interfaces, error contracts, and processing models. This version adds the adaptive language layer that makes the same workflow accessible to any person with an idea, regardless of technical background.

The product vision driving this change: The TRD creation workflow is the front door of the entire system. Once TRDs are produced, the agent handles everything — PRD decomposition, PR generation, CI, and deployment. This makes the TRD interview the single most important user experience in the product. A non-technical founder who can complete the interview successfully gets a production-grade deployed application at the end. That is the product.

Major additions in v2.0:

Technical literacy detection — Phase 0 (new)

Adaptive language layer — all phases translate to/from business language for non-technical users (§3)

Business-to-technical translation engine — how business answers become technical specifications (§4)

Non-technical question register — complete rewrite of Phase 2 for business-language users (§6)

Pipeline handoff — explicit connection from TRD completion to deployment (§17)

Operator mode labels — FOUNDER mode vs ENGINEER mode (§3.2)

CONSULTANT mode — professional services context (§21)

Sections unchanged from v1.0:

§7 (Phase 3 — Boundary Definition), §8 (Phase 4 — Deep Dive taxonomy), §9 (Phase 5 — Gap Detection), §10 (Phase 6 — Outline Review), §11 (Phase 7 — PRODUCT_CONTEXT.md), §12 (Phase 8 — TRD Generation), §13 (Iterative Refinement), §14 (Question Generation Protocol), §15 (Completion Signals), §18 (Session Persistence).

# 1. Purpose and Scope

This document specifies the complete technical requirements for the TRD Development Workflow — a structured, AI-facilitated process that guides any person from a raw product idea to a complete set of implementation-ready Technical Requirements Documents.

The core problem this workflow solves: Most people who want to build software have an idea, not a specification. Technical founders skip to "how" before "what" and "why" are resolved. Non-technical founders don't know that "how" is even a question they need to answer. Both produce vague outputs when asked directly. This workflow is a design facilitator for both.

What makes this different from all existing tools: Every other AI coding tool starts from a technical user who knows what they want to build at a specification level. This workflow starts from anyone with an idea. The agent conducts a structured conversation that extracts the full technical picture from business-language answers, then produces TRDs that a build agent — or a human engineer — can implement without ambiguity. The user never needs to know what a TRD is.

The workflow owns:

Phase 0: Technical literacy detection (new in v2.0)

Eight structured phases from product vision through TRD generation

Adaptive language layer — all questions and responses in the operator's register

Business-to-technical translation — converting business answers to technical specifications

Dynamic question generation — one question at a time, adapted to what has been said

Question taxonomy — coverage map ensuring all TRD domains are addressed

Completion signals, gap detection, outline review

PRODUCT_CONTEXT.md synthesis

Pipeline handoff to /prd start (new in v2.0)

Session persistence with full resume support

WHAT THIS IS NOT: TRD-7 does not build software. It builds the specifications that TRD-3's build pipeline uses to build software. The output of TRD-7 is the input to the rest of the system. From the non-technical user's perspective, completing /trd start is the only thing they do — the agent handles everything after.

# 2. Design Decisions

Decision | Choice | Rationale
Technical literacy detection | Automatic, in Phase 0 | The question register must be set before the interview begins. Wrong register in Phase 1 loses the user.
Language modes | FOUNDER mode / ENGINEER mode | Binary is cleaner than a spectrum. Most people are clearly one or the other in the first 3 exchanges.
Business-to-technical translation | Agent-internal, never shown to user | The user answers in their language. They should never see the technical interpretation until TRD review. Showing intermediate translation breaks the conversational flow.
TRD quality target | Identical regardless of mode | A FOUNDER-mode session and an ENGINEER-mode session must produce TRDs of equal implementation depth. The language of the interview changes; the output does not.
Pipeline handoff | Automatic offer after session complete | Non-technical users do not know /prd start exists. After TRDs are generated, the agent offers to proceed to build immediately.
Deployment connection | Shown in opening | Non-technical users must understand what the end state is before they invest 2–4 hours in an interview. Opening message explains: 'At the end of this, your application will be built and deployed.'
One question at a time | Strictly enforced — both modes | Multiple questions overwhelm all users. Non-technical users in particular will answer only the last one.
TRD outline review | Required — both modes | Non-technical users see the outline in business language (component names, not TRD IDs).

# 3. Adaptive Language Layer

## 3.1 The Two Modes

ENGINEER mode (v1.0 behavior, unchanged): Operator uses technical vocabulary. Questions use terms like "API", "database schema", "authentication", "processing model". Completion signals are the same as v1.0.

FOUNDER mode (new in v2.0): Operator answers in business language. The agent translates all business answers into technical specifications internally. Questions never use jargon. Technical concepts are introduced only when necessary, and always with a plain-language explanation alongside.

## 3.2 Mode Labels in Code

class OperatorMode(str, Enum):

ENGINEER = "engineer"  # Technical vocabulary, v1.0 behavior

FOUNDER  = "founder"   # Business language, translation layer active

UNKNOWN  = "unknown"   # Phase 0 not yet complete

Mode is stored on TRDSession and affects: all question generation prompts (DEEP_DIVE_SYSTEM, GAP_DETECTION_SYSTEM), outline presentation format, TRD review gate language, and completion signal thresholds (FOUNDER mode has slightly lower thresholds — more 'I don't know' answers are acceptable and expected).

## 3.3 Translation Layer Architecture

The translation layer runs after every FOUNDER-mode response. It is a fast, internal Claude call (not shown to the user) that converts the business answer to a structured technical note stored in the session.

TRANSLATION_SYSTEM = """

You are translating a non-technical founder's answer into a structured

technical note for a software specification.

The founder does not use technical vocabulary. Your job is to infer the

correct technical interpretation from context and common patterns.

Rules:

1. Never show this translation to the founder.

2. If the answer is ambiguous between two technical interpretations,

record BOTH and flag for gap detection.

3. If the answer implies a common industry pattern (e.g. 'users log in

with Google' → OAuth2 with Google as identity provider), state the

full technical implication.

4. If the answer is genuinely underspecified, record what is known and

mark the gap explicitly.

Output JSON:

{

"technical_note": "The technical interpretation of the answer",

"pattern_applied": "Industry pattern inferred, if any",

"ambiguities": ["List of ambiguous points if any"],

"gaps": ["Missing technical decisions that must be resolved"]

}

"""

Translation notes are stored in trd_notes[trd_id][domain_id]["translation_log"] and are included in TRD generation prompts but never surfaced to the user during the interview.

# 4. Business-to-Technical Translation Reference

This table shows how common FOUNDER-mode answers map to technical specifications. The agent uses these patterns as defaults when the answer implies a standard approach.

Founder says | Technical interpretation
"Users log in with Google / Apple" | OAuth2/OIDC with that provider as identity provider; JWT access tokens; refresh token rotation
"People upload photos / files" | Object storage (S3-compatible); pre-signed URLs for upload; CDN for serving; file size and type validation
"It sends emails / notifications" | Transactional email service (SendGrid/Postmark pattern); notification queue; delivery status tracking
"Users pay for things" | Payment processor integration (Stripe pattern); webhook handling; idempotent payment records; PCI scope isolation
"It needs to be fast" | p95 latency target; CDN for static assets; database query optimization; caching layer evaluation
"Multiple companies use it" | Multi-tenancy model; tenant isolation at data layer; per-tenant configuration; billing per tenant
"People work together on it" | Real-time sync or optimistic locking; conflict resolution strategy; activity feed; permissions model
"It needs to work on phones" | Responsive web or native app decision; offline capability evaluation; push notification infrastructure
"We need to know what's happening" | Analytics events; audit log; admin dashboard; alerting thresholds
"It should remember preferences" | User profile storage; preference schema; sync across devices
"Only certain people can see certain things" | Role-based access control (RBAC); permission model; row-level security if database
"We'll have a lot of users" | Horizontal scaling strategy; database read replicas; queue-based load leveling; rate limiting

# 5. Phase 0: Technical Literacy Detection (New in v2.0)

## 5.1 Purpose

Detect whether the operator is in ENGINEER mode or FOUNDER mode before asking any product questions. The opening message and all subsequent questions depend on this.

## 5.2 Detection Method

Phase 0 runs silently during the first 1–3 exchanges. The agent asks a single neutral opening question and scores the response.

DETECTION_OPENING = """

Before we start — are you the technical person building this,

or are you the person with the idea who needs someone else

(or an AI) to build it?

"""

This is the only direct question about technical background. The agent does not ask 'are you a developer?' — that framing is exclusionary. The question is about role, not skill.

Scoring:

DETECTION_SIGNALS = {

"engineer": [

"developer", "engineer", "architect", "technical", "code",

"api", "database", "backend", "frontend", "stack", "deploy",

"aws", "gcp", "azure", "docker", "kubernetes", "python",

"typescript", "i'll build", "i'm building it myself",

],

"founder": [

"idea", "concept", "business", "product", "customers",

"users", "market", "revenue", "problem", "solution",

"i don't code", "not technical", "need someone to build",

"someone else will build", "you'll build", "the ai will build",

"i have an idea",

],

}

If the response contains 2+ engineer signals and 0 founder signals → ENGINEER mode. If the response contains 1+ founder signals → FOUNDER mode. If ambiguous → ask one clarifying question, then decide.

## 5.3 Mode Confirmation Openings

ENGINEER mode opening:

Got it — let's build your technical specification from the ground up.

I'll guide you through a structured process, one question at a time.

At the end you'll have a complete TRD set ready to load into the

build system.

To start: in one or two sentences, what are you building?

FOUNDER mode opening:

Perfect — think of me as a senior engineer on your team. My job is

to ask you the right questions about your product so I can write

the complete technical blueprint. You don't need to know anything

about software development. Just tell me about the product and the

people who will use it.

At the end of this conversation — usually 2 to 4 hours — I'll have

a full specification ready, and we can start building immediately.

Your application will be built and deployed automatically from

what we create here.

To start: tell me about the product you want to build. What does

it do, and who uses it?

# 6. Phase 2 (FOUNDER Mode): Business-Language Architecture Discovery

## 6.1 Overview

Phase 2 in ENGINEER mode (v1.0) asks about processing models, service-to-service authentication, and message queues. FOUNDER mode asks the same questions in business language. The agent extracts the same technical picture from fundamentally different answers.

## 6.2 FOUNDER Mode Architecture Questions

The same seven architecture domains are covered. The question framing is completely different.

### Domain: Data

ENGINEER: "What data exists at the start? Where does it come from?"

FOUNDER: "When someone uses your product for the first time, what information do they give you? And what information does your product create or track about them over time?"

### Domain: External Systems

ENGINEER: "What APIs, databases, or message queues does this connect to?"

FOUNDER: "Does your product connect to anything that already exists? For example — does it send emails, accept payments, connect to Google or social media, pull data from another service?"

### Domain: Processing Model

ENGINEER: "Is this request-response, event-driven, batch, or streaming?"

FOUNDER: "When a user does something in your product — like clicking a button or submitting a form — does something happen immediately on screen, or does something happen in the background that might take a while? For example, if a user requests a report, do they wait for it, or does it arrive later?"

### Domain: State and Persistence

ENGINEER: "What must be persisted? Where? For how long?"

FOUNDER: "If your product crashed and restarted right now, what would users be upset to have lost? And what could you recreate or they could re-enter without much trouble?"

### Domain: Authentication

ENGINEER: "How do users authenticate? How do services authenticate to each other?"

FOUNDER: "How do people prove it's them when they come back to your product? Do they create an account with a password, log in with Google or Apple, or something else?"

### Domain: Scale

ENGINEER: "How many concurrent users? What throughput in ops/second?"

FOUNDER: "How many people do you expect to be using this at the same time once it's launched? And what does a big success look like — is this 1,000 users, 100,000 users, or something else?"

### Domain: Operating Environment

ENGINEER: "What platform — cloud provider, on-prem? Managed services or self-hosted?"

FOUNDER: "Is this something people use in a browser, a phone app, a desktop app, or all of those? And do you have any preference for where it runs, or should we pick what makes the most sense?"

## 6.3 Architecture Translation Output

After Phase 2 in FOUNDER mode, the agent synthesizes the architecture sketch internally using the translation layer. The output format is identical to ENGINEER mode — the same architecture_sketch dict, the same ASCII diagram. The user sees only a plain-language description and is asked to confirm it matches their intent.

The full ASCII diagram and technical architecture_sketch are generated internally and used for TRD generation, not shown to the FOUNDER user at this stage. They will see the technical detail in the TRD outline review, where it is presented in context.

# 7. Phase 3: TRD Boundary Definition

Unchanged from v1.0 for ENGINEER mode.

FOUNDER mode adaptation:

TRD boundaries are presented to the user as "components" not "TRDs." The naming is in plain language.

ENGINEER mode: "TRD-1: Authentication Layer, TRD-2: API Gateway..."

FOUNDER mode:

Here are the main building blocks I'd propose for your product:

1. User Accounts — how people sign up, log in, and manage their profile

2. Core Product Engine — [the main thing the product does]

3. Data Storage — where everything is saved and how it's organized

4. Notifications — emails, alerts, and messages your product sends

5. Admin Dashboard — how you manage the product and see what's happening

Does this look right, or would you change anything?

The internal TRD IDs (TRD-1, TRD-2 etc.) are generated from these business names automatically. The PRODUCT_CONTEXT.md uses the business names in the TRD index alongside the technical IDs.

# 17. Pipeline Handoff (New in v2.0)

## 17.1 The Full Pipeline Connection

TRD-7 is the front door. When a session completes, the agent explicitly connects the output to the build pipeline. For FOUNDER mode users especially, they need to understand what happens next and that they don't need to do anything technical.

## 17.2 Session Completion Message

ENGINEER mode:

═══════════════════════════════════════════════════════

SESSION COMPLETE — {N} TRDs generated

Committed to GitHub: trd-specs/

PRODUCT_CONTEXT.md: crafted-docs/PRODUCT_CONTEXT.md

Total cost: ${cost:.2f}

Ready to build. Run /prd start to begin the build pipeline.

═══════════════════════════════════════════════════════

FOUNDER mode:

═══════════════════════════════════════════════════════

YOUR PRODUCT BLUEPRINT IS COMPLETE

{N} technical specifications written

Saved and ready to build

What happens next:

The agent will read your specifications and build your

application automatically. This includes writing all the

code, running tests, and deploying to the cloud.

You'll be able to watch it happen in real time and

approve each major section before it's built.

Estimated build time: {estimated_hours} hours

Ready to start building now?

═══════════════════════════════════════════════════════

## 17.3 Automatic Pipeline Offer

For FOUNDER mode sessions, after the completion message, the agent automatically offers to proceed. If the user selects "Start building", the agent calls _handle_prd("start") internally, loading the just-generated TRDs as context. The user never types /prd start.

## 17.4 Cost and Time Transparency

Both modes receive a cost and time estimate at session start:

This session usually takes 2–4 hours depending on product complexity.

- Your time: answering questions (the hard part)

- Agent time: ~30 minutes of actual API calls

After this session, building your application takes 4–8 hours

of automated work. You can close your laptop while it runs.

Cost to generate specifications: approximately $8–20.

Cost to build the application: approximately $50–150.

# 18. TRDSession Updates (v2.0)

The TRDSession dataclass gains two new fields:

@dataclass

class TRDSession:

# ... all v1.0 fields unchanged ...

# New in v2.0

operator_mode: OperatorMode = OperatorMode.UNKNOWN

translation_log: list[dict] = field(default_factory=list)

# { "phase": str, "domain": str, "raw_answer": str,

#   "technical_note": str, "gaps": list[str] }

The translation_log is included in TRD generation prompts for FOUNDER mode sessions, giving the generation model full context on the business intent behind each technical decision.

# 19. Testing Requirements (Updated)

All v1.0 tests apply. Additional tests for v2.0:

Module | Coverage Target | Critical Test Cases
Technical literacy detection | 100% | Engineer signals → ENGINEER mode; founder signals → FOUNDER mode; ambiguous → clarifying question asked
Translation layer | 90% | "Users log in with Google" → OAuth2 inferred; "accept payments" → Stripe pattern inferred; ambiguous answer → both interpretations recorded
FOUNDER mode questions | 95% | All 7 architecture domains covered using business-language questions; no technical jargon in question text
Pipeline handoff | 100% | FOUNDER mode completion triggers pipeline offer; "Start building" calls _handle_prd; ENGINEER mode shows /prd start command
Mode persistence | 100% | operator_mode survives session save/load; FOUNDER mode resumes in FOUNDER mode
Translation log in generation | 90% | TRD generation prompt for FOUNDER session includes translation_log; technical notes from translations appear in generated TRD

# 20. Out of Scope (Updated)

Feature | Reason | Target
Voice or video input | Text-only. Voice would be a UI-layer concern handled by the macOS app shell. | TBD — high value for FOUNDER mode
Automatic TRD updates when requirements change | Point-in-time specifications. Change tracking is a separate workflow. | v3.0
Multiple operators in one session | One operator per session. | v2.0
Hybrid mode (technical + non-technical operators) | Session mode is set at Phase 0 and does not change. | v3.0
Generating code directly from /trd start | TRD workflow outputs specifications. Building is /prd start (TRD-3). This is by design — the TRD is the product artifact, not the code. | Never

# 21. CONSULTANT Mode (New in v2.0)

## 21.1 Overview

CONSULTANT mode is the third operator mode, alongside FOUNDER and ENGINEER. It is designed for a professional services context — a consultant running a live client meeting, extracting product requirements from a client who may or may not be in the room.

The fundamental difference from FOUNDER and ENGINEER mode: the person operating the agent is not the person with the idea. The consultant asks the questions. The client answers them. The agent captures everything and produces two distinct outputs — a client-facing deliverable and a technical specification for the build system.

## 21.2 Detection

CONSULTANT mode is detected in Phase 0 by explicit signal, not inference. The detection opening adds a third option to the standard question:

DETECTION_OPENING = """

Before we start — are you the technical person building this,

the person with the idea who needs someone else to build it,

or are you a consultant or service provider working on behalf

of a client?

"""

CONSULTANT mode signals: "consultant", "consulting", "client", "on behalf", "service provider", "agency", "working with a client", "my client", "customer", "for a customer", "professional services", "systems integrator". One or more signals → CONSULTANT mode confirmed.

## 21.3 CONSULTANT Mode Opening

Got it — I'll help you run this client session efficiently.

Here's how this works:

- I'll ask one question at a time, phrased for a live meeting

- You relay the client's answers (or type them yourself if

the client is with you)

- I'll build the complete technical specification in the background

- At the end, you get two things:

1. A one-page client summary — plain language, ready to

share or leave behind

2. A full technical specification — ready to build from

This usually takes 60–90 minutes in a meeting.

You can pause and resume any time with /trd resume.

To start: what is your client's business, and what problem

are they trying to solve?

## 21.4 Meeting Pace Optimization

CONSULTANT mode questions are shorter and faster than FOUNDER or ENGINEER mode. In a live meeting, long questions break conversational flow and make the client feel like they're filling out a form.

CONSULTANT_QUESTION_RULES = """

You are generating questions for a consultant running a live

client meeting. Rules:

1. Maximum 15 words per question.

2. No technical jargon — the client is a business person.

3. One question. No preamble. No explanation.

4. If context is needed, one sentence maximum before the question.

5. Questions should feel like natural conversation, not an interview.

BAD: "Can you describe the authentication and authorization

requirements for the system, including how different user roles

will interact with the platform?"

GOOD: "Who are the different types of people who will use this,

and do they need different levels of access?"

"""

## 21.5 Two-Layer Output

Layer 1 — Client Summary (business-readable)

A one-page document the consultant can leave with the client, email immediately after the meeting, or use as a sign-off document before the build begins. Sections: What We're Building, Who It's For, What It Does, What It Doesn't Do, How It's Secured, Deployment, Next Steps. Style: no acronyms, no technical terms, 400–600 words maximum, includes sign-off line.

Layer 2 — Technical Specification (build-ready)

Identical to FOUNDER mode output — full TRD set at implementation depth, committed to GitHub, loaded into the doc store. The client never sees this layer.

## 21.6 Deployment Artifact Specification

CONSULTANT mode captures the deployment target, which determines what the build pipeline produces:

class DeploymentTarget(str, Enum):

WINDOWS_APP    = "windows_app"     # .exe installer, runs on Windows

MAC_APP        = "mac_app"         # .app bundle, runs on macOS

LINUX_SERVICE  = "linux_service"   # systemd service, runs on Linux server

CLOUD_SERVICE  = "cloud_service"   # Container, deploys to GCP/AWS/Azure

HYBRID         = "hybrid"          # Multiple targets

TBD            = "tbd"             # Not yet decided

Deployment target question in CONSULTANT mode: "Does your client need this to run on their own computers and servers — inside their building or on their own cloud account — or is a hosted web service acceptable?"

Client answer | Deployment target
"On our computers" / "On our servers" | WINDOWS_APP or LINUX_SERVICE
"On our laptops, some Windows some Mac" | HYBRID (Windows + Mac)
"In our own AWS/Azure/GCP account" | CLOUD_SERVICE (client-owned)
"Anywhere, just needs to work" | CLOUD_SERVICE (agent-managed)
"Air-gapped / no internet" | WINDOWS_APP or LINUX_SERVICE
"Our IT department needs to manage it" | LINUX_SERVICE or CLOUD_SERVICE

## 21.7 Security and Compliance Capture

CONSULTANT mode includes a dedicated security pass. Enterprise clients have compliance requirements that must be captured before the build begins. Compliance frameworks detected automatically apply corresponding controls:

Framework detected | Controls applied
HIPAA | PHI encryption at rest and in transit, audit log, BAA language in client summary
SOC 2 | Access controls, audit trail, incident response section
FedRAMP | FedRAMP-authorized services only, FIPS 140-2 encryption
PCI-DSS | Cardholder data isolation, tokenization, network segmentation

## 21.8 Meeting Management Features

CONSULTANT mode adds two commands not available in other modes:

/trd pause    — Pause the session mid-meeting. Saves state immediately.

Agent confirms: "Session paused. Resume with /trd resume."

/trd summary  — Show a running summary of what has been captured so far.

Formatted for the consultant, not the client.

Useful for confirming understanding mid-meeting.

## 21.9 Session Completion — CONSULTANT Mode

At session end, CONSULTANT mode produces three outputs in sequence:

Client Summary document (.docx) — Generated first. Formatted for business stakeholders. Includes sign-off section ("Approved by: _____________ Date: _____________").

Technical TRD set — Same as FOUNDER mode — full specification committed to GitHub.

Consultant Handoff Card — Shown in the agent stream for the consultant's use only: client summary path, GitHub URL, deployment target, compliance profile, estimated build time and cost, /prd start and /trd export client-summary commands.

## 21.10 TRDSession Updates for CONSULTANT Mode

@dataclass

class TRDSession:

# ... all v1.0 and v2.0 fields ...

# CONSULTANT mode fields (new in v2.0)

client_name:          str              = ""

deployment_target:    DeploymentTarget = DeploymentTarget.TBD

compliance_framework: list[str]        = field(default_factory=list)

client_summary_path:  Optional[str]    = None

meeting_pauses:       list[float]      = field(default_factory=list)

# timestamps of each /trd pause call — for session time tracking

## 21.11 Business Model Note

CONSULTANT mode is the highest-value licensing tier. A consultant running 3–4 client engagements per month, each replacing 15–20 hours of requirements documentation work, recovers $9,000–$24,000 in billable time per month per consultant. Licensing at $500–2,000/month per consultant seat produces strong unit economics for both parties.

The client summary document and sign-off workflow also give the consultant a professional artifact that elevates their engagement quality — the deliverable is better than what most firms produce manually.

# Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification — 8-phase workflow, question taxonomy, gap detection, session persistence
2.0 | 2026-03-20 | YouSource.ai | Adaptive language layer: Phase 0 (technical literacy detection), FOUNDER mode, business-to-technical translation engine, FOUNDER-mode Phase 2 question register, pipeline handoff to build system, automatic /prd start offer, cost and time transparency, CONSULTANT mode (§21)