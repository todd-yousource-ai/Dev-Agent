# TRD-8-UIUX-Design-System-Crafted

_Source: `TRD-8-UIUX-Design-System-Crafted.docx` — extracted 2026-03-26 21:48 UTC_

---

TRD-8: UI/UX Design System

Technical Requirements Document — v3.0 (Consolidated)

Field | Value
Product | Crafted
Document | TRD-8: UI/UX Design System
Version | 3.0 (Consolidated — v1.0 + v2.0 + v3.0)
Status | Active — Health Dashboard, Remediation, Figma Pipeline, Multi-Modal Input
Author | YouSource.ai
Previous | v2.0 (Figma Pipeline); v3.0 (Health Dashboard) — both delta documents
Depends on | TRD-1 (macOS Shell), TRD-3 (Build Pipeline), TRD-5 (GitHub), TRD-6 (Holistic Review), TRD-7 v2, TRD-11 (Security), TRD-17 (Self-Healing), TRD-18 (Crafted Connect)
New deps | Figma REST API, Figma MCP Server, TRD-17, TRD-18

# Consolidated Version Summary

This document merges the three TRD-8 versions into a single complete specification. Prior documents were delta-only — this version is self-contained.

Version | Date | What Was Added
1.0 | 2026-03-19 | Complete macOS SwiftUI UI: build stream, approval gates, REPL, context panel, cost tracking, full design system (typography, color tokens, component library)
2.0 | 2026-03-20 | Figma pipeline UI (§24), sketch/image input (§6.4–6.5), drag-and-drop, three TRD session modes — FOUNDER/ENGINEER/CONSULTANT (§17), compliance indicators, deployment target selector, client summary preview (§25)
3.0 | 2026-03 | Health Dashboard (§6), Issue Reporting flow (§7), Diagnosis View (§8), Fix Review and Approval (§9), Remediation stream (§10), In-app health component spec (§11). Design philosophy extended to Builder + Maintainer profiles.

# §1  Purpose and Design Philosophy

Crafted's UI serves two distinct user profiles with different mental models:

Profile | Mental model | Primary surface
Builder | I am constructing something. I need precise control over what gets built and when. | Build stream, PRD/PR approval gates, REPL
Maintainer | Something is wrong with what I built. I need to describe it and get it fixed without becoming a developer. | Health dashboard, issue report, diagnosis view, one-tap fix

The Maintainer profile is the Everyman creator — someone who built an app or agent with Crafted and is now using it. They should never need to read a log, find a PR number, or understand a stack trace to get a fix.

Both profiles coexist in the same app. The Health Dashboard is always visible. The Build Stream activates when a build is running. Neither interrupts the other.

# §2  Application Shell

Three top-level panels, always accessible from the sidebar:

Panel | Icon | Always visible | Activates when
Health | Heart with pulse | Yes — primary home screen | Always. Shows current status of all registered apps/agents.
Build | Hammer | Yes | A build is running or available to start
Notepad | Document | Yes | Always. Persistent scratch pad.

Health is the default panel when Crafted opens — not Build. A creator who has already built something should land in the health view, not the build view.

# §3  Design System

Typography, color, spacing, and component library.

## §3.1  Typography

Primary: SF Pro Display, SF Pro Text

Code / monospace: SF Mono

Base size: 17pt body, 11pt labels, 13pt secondary

## §3.2  Color tokens

Accent (Crafted blue): #2E5B9A

Sage (success actions): #3D7A5C

Success: #34C759 (system green)

Warning: #FF9500 (system orange)

Destructive: #FF3B30 (system red)

Background: adaptive (light/dark system)

surface-raised, code-bg, border, border-subtle, text-primary, text-secondary, text-tertiary — all adaptive

## §3.3  Spacing

Base unit: 4pt. Padding: 8, 12, 16, 24. Card padding: 16pt. Section gaps: 24pt.

## §3.4  Component library

CardContainer — all build/health cards use this wrapper

PrimaryActionButtonStyle, SecondaryActionButtonStyle

ModeBadge (§17.1)

All interactive elements: minimum 44pt touch target, accessibilityLabel(), accessibilityIdentifier()

# §4  Build Stream Panel

The build stream panel activates when a /prd start command runs. It shows the pipeline output, PR approval gates, and operator commands.

Key invariants:

Gates never auto-approve — operator input always required

SECURITY_REFUSAL stops the build and gates — never bypassed

Build cards are append-only — never edited after display

Ledger, Active PRD, Notepad, Journal tabs preserved in context panel

Build Intent Bar updated in v2.0 — see §6.4

# §5  Operator Modes

FOUNDER, ENGINEER, and CONSULTANT modes apply to both Build and Health panels. Mode selection persists across sessions. FOUNDER is the default for all new users.

Mode | Health panel behavior | Fix approval behavior
FOUNDER | Plain English health summaries. No technical detail unless requested. | One-tap approve. Minimal diff shown. Plain English impact summary.
ENGINEER | Full telemetry detail available on expand. Raw logs accessible. | Full PR diff shown. Test results visible. Standard approval flow.
CONSULTANT | Client-facing summary view. Compliance indicators visible. | Client-safe approval flow. No internal implementation detail exposed.

# §6  Build Intent Bar (Updated in v2.0)

The Build Intent Bar gains two new input modes alongside the existing text field: image upload and Figma import.

## §6.1  Input bar structure

┌────────────────────────────────────────────────────────────┐

│  [📎] [🎨]  Describe what to build...              [↑]  │

└────────────────────────────────────────────────────────────┘

📎 — Upload image (napkin sketch, whiteboard photo, wireframe screenshot)

🎨 — Import from Figma (paste Figma file URL or connect via OAuth)

## §6.2  SwiftUI: BuildIntentBar

struct BuildIntentBar: View {

@State private var intent = ""

@State private var attachedImage: NSImage? = nil

@State private var figmaURL: String? = nil

@State private var showImagePicker = false

@State private var showFigmaImport = false

var body: some View {

VStack(spacing: 8) {

if let image = attachedImage {

AttachedImagePreview(image: image) { attachedImage = nil }

}

HStack(spacing: 12) {

Button(action: { showImagePicker = true }) {

Image(systemName: "paperclip")

.foregroundColor(attachedImage != nil ? Color("sage") : Color("text-tertiary"))

}

.accessibilityIdentifier("attach-image-button")

Button(action: { showFigmaImport = true }) {

Image(systemName: "paintpalette")

.foregroundColor(figmaURL != nil ? Color("sage") : Color("text-tertiary"))

}

.accessibilityIdentifier("figma-import-button")

TextField("Describe what to build...", text: $intent, axis: .vertical)

.lineLimit(1...4)

.accessibilityIdentifier("build-intent-field")

Button(action: startBuild) {

Image(systemName: "arrow.up.circle.fill").font(.system(size: 24))

}

.disabled(intent.isEmpty && attachedImage == nil && figmaURL == nil)

.keyboardShortcut(.return, modifiers: .command)

}

.padding(16)

}

}

}

## §6.3  Drag-and-drop onto Build Stream

Images can be dragged directly onto BuildStreamView when idle. Drop target activates with a sage green overlay:

.onDrop(of: [.image, .fileURL], isTargeted: $isDragTarget) { providers in

handleImageDrop(providers)

return true

}

.overlay(isDragTarget ? DropTargetOverlay() : nil)

## §6.4  Sketch Interpretation Card

When an image is submitted, a SketchInterpretationCard appears in the build stream showing interpretation in progress, then the result with two actions: "Generate Figma Design" and "That's not quite right".

After interpretation the card shows: layout type, detected components (e.g. NavigationSidebar, DataCard × 3, HeaderBar), and action buttons.

# §7  Health Dashboard Panel (New in v3.0)

The health dashboard is the first thing a creator sees when they open Crafted. It answers: are the things I built working right now?

## §7.1  Layout — three zones

Zone | Content | Size
Status bar | Overall health: All Good / Issues Found / Critical. Tap to expand. | Full width, 44pt height
Target cards | One card per registered app/agent. Scrollable list. | Full width, variable height
Active issues | Expandable list of open issues across all targets. Empty = All Good. | Full width, collapsible

## §7.2  Target card

Each registered app or agent has a card showing:

App/agent name and icon

Health indicator: green dot (healthy), orange dot (warning), red dot (issue detected)

Last checked timestamp

One-line plain English summary of most recent issue (if any): e.g. "PDF export failing since yesterday"

Two actions: "Something's wrong" (creator report) and "View details"

## §7.3  Target detail view

Current health status with last-updated timestamp

Recent issues: category (bug/security/performance), plain English description, status (investigating/fixing/resolved), age

Recent builds: last 5 PRs with CI status

"Something's wrong" button — always visible, prominent

Telemetry summary (ENGINEER mode): error rate, p95 latency, last exception

## §7.4  Health indicators

Indicator | Color | Condition
Healthy | Green | No open issues. CI passing. No telemetry alerts.
Warning | Orange | Open issue being investigated. CI passing. No user impact confirmed.
Issue | Red | CI failing on main OR confirmed user-impacting bug OR security finding.
Unknown | Grey | Crafted Connect not reporting. Last contact > 24 hours.

# §8  Issue Reporting Flow (New in v3.0)

Two entry points, one flow: creator taps "Something's wrong" whether they're in Crafted or in the app itself.

## §8.1  Entry points

From Crafted health dashboard: tap "Something's wrong" on a target card

From inside the app/agent itself: tap the "Something's wrong" component (TRD-18, generated into every app)

From Crafted via natural language: type "my invoicing app's export is broken" in the Crafted input field

## §8.2  Report sheet

A modal sheet with a single focused question:

Header: "What's happening?" in large text

Subhead: "Describe what's wrong in your own words"

Text input: large, prominent, no character limit

Voice button: tap to dictate (transcribed inline)

Target selector: pre-filled if entered from a target card, otherwise a picker

Submit button: "Let Crafted investigate"

The sheet does NOT ask: which file, which function, which error, which PR. The creator describes what they observed as a user, not as a developer.

## §8.3  Post-submit state

Status changes to orange "Investigating"

Progress indicator: Gathering context → Diagnosing → Ready

Estimated time: "Usually under 30 seconds"

Creator can dismiss and return — investigation continues in background

# §9  Diagnosis View (New in v3.0)

When Crafted completes its diagnosis, a notification appears and the target card updates. Tapping opens the diagnosis view.

## §9.1  Diagnosis card structure

Plain English summary at top: "Crafted found the likely cause"

What you described: creator's original report shown back to them

What Crafted found: 1–3 sentences in plain English

Confidence indicator: High / Medium / Low with brief explanation

Technical detail (collapsed by default, ENGINEER mode expanded): affected files, PR number, error type, stack hash

Two primary actions: "Fix it" and "Not quite right" (to refine the description)

## §9.2  Confidence levels

Confidence | Shown as | Meaning | Default action
High | Green — "Crafted is confident" | Telemetry + recent PR diff clearly correlate with the description | "Fix it" auto-progresses to fix review
Medium | Orange — "Good lead found" | Correlation found but not definitive | "Fix it" progresses with a note that this is the best diagnosis available
Low | Grey — "Needs more context" | No clear correlation found | "Describe more" offered alongside "Try fixing anyway"

## §9.3  Security findings

Red banner: "Security issue found"

Plain English impact shown

NO auto-fix offered — creator must explicitly tap "Review and fix"

Security fixes always show plain English impact summary before approval

Merge requires explicit creator approval — never auto-merged

# §10  Fix Review and Approval (New in v3.0)

The creator approves a fix the same way they'd approve something a colleague sent them — read the summary, understand the impact, say yes or no.

## §10.1  Fix review card — FOUNDER / default mode

What will change: 2–3 bullet points in plain English

Risk level: Low / Medium / High with one-line explanation

CI status: "Tests passed" or "Tests running..."

Two actions: "Approve fix" (green) and "Not right" (outline)

## §10.2  Fix review card — ENGINEER mode

All of the above plus:

Compact diff view: changed lines highlighted, file name shown

New tests added: shown explicitly

PR link: opens in GitHub

CI detail: individual check results

## §10.3  Approval states

State | UI | What happens
Pending CI | Spinner + "Running tests..." | Approval button disabled until CI passes
CI passed | Green checkmark + "Approve fix" enabled | Creator can approve
CI failed | Red + "Tests failed — Crafted is retrying" | Fix loop runs up to 3 CI cycles; creator informed of progress
Approved | Green confirmation + "Fix merged" | PR merged, target health rechecked in 60 seconds
Rejected | Creator taps "Not right" | Crafted asks for more context and re-diagnoses

# §11  Remediation Stream (New in v3.0)

The remediation stream runs continuously alongside and independently of the build stream. It shows all active remediation activity across all registered targets.

## §11.1  Stream events

Event type | Icon | Example message
Issue detected | Red circle | "Crafted detected a CI failure on My Invoice App"
Report received | Speech bubble | "You reported: PDF export isn't working"
Investigating | Magnifying glass | "Crafted is correlating telemetry with recent changes"
Diagnosis ready | Lightbulb | "Cause identified: PR #47 changed the file save method"
Fix generated | Wrench | "Fix PR opened: Update PDF export to current save API"
Awaiting approval | Checkmark circle | "Waiting for your approval to merge the fix"
Fix merged | Green checkmark | "Fix deployed. Monitoring for recurrence."
Security gate | Lock | "Security fix requires your review before merging"

## §11.2  Parallel operation

The remediation stream and build stream are independent. A build can be running while remediations are in progress on previously built apps. Neither blocks the other. Both are visible in their respective panels simultaneously.

# §12  In-App "Something's Wrong" Component (New in v3.0)

Auto-generated into every app and agent the Crafted pipeline produces. It is the in-app entry point to the remediation flow.

## §12.1  Visual design

Small, unobtrusive floating button — bottom-right corner by default, configurable

Icon: waveform or pulse icon (health metaphor, not a bug/error metaphor)

Always visible when the app is running, never hidden

In ENGINEER mode: long-press to expose quick telemetry summary

## §12.2  Tap behavior

Single tap: opens the report sheet (§8.2) as a modal over the current app

Report sheet pre-populated with current screen name and last 3 actions

Submit routes the report via CraftedConnect SDK (TRD-18) to Crafted Dev Agent

App returns to normal state immediately — no interruption to workflow

## §12.3  SwiftUI implementation contract

// Auto-generated into every Crafted-built app

struct CraftedHealthButton: View {

@StateObject private var connect = CraftedConnect.shared

@State private var showingReport = false

var body: some View {

VStack {

Spacer()

HStack {

Spacer()

Button(action: { showingReport = true }) {

Image(systemName: "waveform.path.ecg")

.padding(12)

.background(Color(.systemBackground))

.clipShape(Circle())

.shadow(radius: 4)

}

.padding()

}

}

.sheet(isPresented: $showingReport) {

IssueReportSheet(connect: connect)

}

}

}

The component is overlaid on the app's root view via a ZStack. It does not modify the app's existing view hierarchy.

# §13  TRD Session UI (Updated in v2.0)

v1.0 specified a single TRD session UI. v2.0 adds mode-specific visual treatments for FOUNDER, ENGINEER, and CONSULTANT modes. FOUNDER is the default for all new users.

## §13.1  Mode indicator badge

All three modes show a persistent mode badge in the TRD session stage header:

┌────────────────────────────────────────────────────────────────┐

│  ● TRD SESSION · Phase 2: Architecture Discovery  [FOUNDER]   │

│  ████████░░░░░░░░  3 of 7 domains covered   Est. $4.20 total  │

└────────────────────────────────────────────────────────────────┘

[FOUNDER] — sage green accent (#3D7A5C), white text

[ENGINEER] — surface-raised background, text-secondary text

[CONSULTANT] — #F59E0B (warning color) background, dark text — signals live meeting context

## §13.2  SwiftUI: ModeBadge

struct ModeBadge: View {

let mode: OperatorMode

var body: some View {

Text(mode.displayLabel)

.font(.custom("SF Pro Text", size: 11)).fontWeight(.medium)

.padding(.horizontal, 8).padding(.vertical, 3)

.background(mode.badgeColor)

.foregroundColor(mode.badgeTextColor)

.cornerRadius(4)

}

}

## §13.3  FOUNDER mode question display

In FOUNDER mode, questions are displayed conversationally. Domain progress shown in plain language, not domain IDs:

"Understanding your data" (not "D3: Data Model")

"How people log in" (not "D4: Authentication")

"What happens when things go wrong" (not "D5: Error Handling")

## §13.4  CONSULTANT mode UI additions

Three elements not present in other modes:

Meeting timer in stage header bar with Pause button that calls /trd pause

Compliance indicator in Context Panel (HIPAA, SOC 2 etc.) with warning-color treatment

Deployment target selector: Windows App / Mac App / Linux Service / Cloud Service / Hybrid

# §14  Figma Design Pipeline UI (New in v2.0)

## §14.1  Overview — activation triggers

A Figma file URL is submitted via the Build Intent Bar

The sketch interpretation card's "Generate Figma Design" button is pressed

A completed Figma design is detected in a connected Figma account

## §14.2  Figma Import Sheet

struct FigmaImportSheet: View {

@State private var figmaURL = ""

@State private var connectionStatus: FigmaConnectionStatus = .disconnected

let onImport: (String) -> Void

var body: some View {

VStack(alignment: .leading, spacing: 20) {

Text("Import from Figma")

.font(.custom("SF Pro Text", size: 17)).fontWeight(.semibold)

FigmaConnectionStatusView(status: connectionStatus)

TextField("https://www.figma.com/design/...", text: $figmaURL)

.font(.custom("SF Mono", size: 13))

.padding(10).background(Color("code-bg")).cornerRadius(6)

HStack {

Spacer()

Button("Cancel") { dismiss() }.buttonStyle(SecondaryActionButtonStyle())

Button("Import Design") { onImport(figmaURL) }

.buttonStyle(PrimaryActionButtonStyle()).disabled(figmaURL.isEmpty)

}

}

.padding(24).frame(width: 480)

}

}

## §14.3  Card sequence in build stream

Card 1 — Figma Reading: shows file name, frame count, component count, parsing progress bar.

Card 2 — Design Summary (gate card): screens, components, color tokens, typography, breakpoints. Actions: "Build from this design" / "Update design first".

Card 3 — Code Generation Progress: per-component generation status with ✓ / ● / ○ indicators.

## §14.4  Context Panel — Design tab

When a Figma design is active, the Context Panel's fifth tab switches from "Settings" to "Design", showing file name, last modified date, component list, and "Open in Figma" button.

## §14.5  Sketch-to-Figma progress card

When a napkin sketch triggers Figma generation: step-by-step progress (Layout structure → Navigation components → Data display cards → Typography → Color tokens → Component library). "Open Figma to review" button activates when generation is complete.

# §15  Client Summary Preview UI — CONSULTANT Mode (New in v2.0)

## §15.1  Overview

At the end of a CONSULTANT mode TRD session, the client summary document is generated and previewed inside the agent before export. This gives the consultant a final review step before sharing with the client.

## §15.2  Client Summary Review Card

┌──────────────────────────────────────────────────────────────┐

│  Your summary is ready                           14:32:01   │

│  ─────────────────────────────────────────────────────────  │

│  Payment Automation Platform                                │

│  ─────────────────────────────────────────────────────────  │

│  What We're Building                                        │

│  A platform that automatically matches incoming payments... │

│                                                             │

│  Who It's For                                               │

│  Accounts payable teams at mid-sized manufacturing cos.    │

│  ★ SOC 2 controls applied · Windows deployment             │

│  ─────────────────────────────────────────────────────────  │

│  [ Export .docx ]  [ Email to client ]  [ Start building ] │

└──────────────────────────────────────────────────────────────┘

## §15.3  Sign-off state

After the consultant sends the summary and the client approves, the card updates: "✓ [Product] — Client approved · Ready to build" with a single "Begin build pipeline" action.

# §16  Accessibility

All surfaces meet WCAG 2.1 AA and Apple HIG accessibility requirements:

Every interactive element has accessibilityLabel() and accessibilityIdentifier()

Health status indicators use both color and shape — never color alone

Issue report input supports dictation and VoiceOver

Approval buttons have minimum 44pt touch target

Diagnosis text meets 4.5:1 contrast ratio in both light and dark mode

Plain English summaries written at Flesch-Kincaid grade 8 or below

# §17  Acceptance Criteria

## §17.1  Health dashboard

All registered targets visible with correct health status within 5 seconds of app open

Health status updates within 60 seconds of a CI failure on main

Target cards show plain English issue summary without requiring expansion

Unknown status shown correctly when Crafted Connect has not reported in > 24 hours

## §17.2  Issue reporting

Report sheet opens within 200ms of tapping "Something's wrong"

Voice input transcribed and visible within 2 seconds

Post-submit status visible within 500ms of submission

Diagnosis available in Crafted UI within 30 seconds of report submission

## §17.3  Diagnosis and fix

Diagnosis shown in plain English at Flesch-Kincaid grade 8 or below

Technical detail available on expand in ENGINEER mode

Security fixes never show Approve button until creator reads plain English impact summary

Fix merged within 60 seconds of approval (CI already passed)

Target health rechecked and card updated within 60 seconds of merge

## §17.4  In-app component

CraftedHealthButton present in every Crafted-built app at build time

Component visible in all app states including error states

Report submitted successfully from inside the app without requiring Crafted to be open

No interference with app's existing view hierarchy or gesture recognizers

## §17.5  Figma pipeline

Figma file URL accepted and parsed within 5 seconds

Design Summary gate card shown before code generation begins

Per-component generation progress visible in real time

Sketch-to-Figma generation completes within 60 seconds for typical wireframes

## §17.6  TRD session modes

Mode badge visible in all TRD session phase headers

FOUNDER mode domain labels use plain English (never domain IDs)

CONSULTANT mode meeting timer visible and pauses correctly

Compliance indicators appear automatically when compliance requirements detected

# Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Complete macOS SwiftUI UI: build stream, approval gates, REPL, context panel, cost tracking, full design system
2.0 | 2026-03-20 | YouSource.ai | Figma pipeline UI, sketch/image input, drag-and-drop, three TRD session modes (FOUNDER/ENGINEER/CONSULTANT), compliance indicators, deployment target selector, client summary preview card
3.0 | 2026-03 | YouSource.ai | Health Dashboard, Issue Reporting flow, Diagnosis View, Fix Review and Approval, Remediation stream, In-app health component. Design philosophy extended to Builder + Maintainer profiles.
3.0 (consol.) | 2026-03-24 | YouSource.ai | Consolidated: merged all three delta documents into one complete self-contained specification.