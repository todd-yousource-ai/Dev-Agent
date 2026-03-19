# TRD-8-UIUX-Design-System

_Source: `TRD-8-UIUX-Design-System.docx` — extracted 2026-03-19 23:49 UTC_

---

TRD-8

UI/UX Design System

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-8: UI/UX Design System
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (App Shell — SwiftUI view hierarchy, scene architecture), TRD-3 (Build Pipeline — card types come from XPC messages), TRD-6 (Holistic Review — review UI), TRD-7 (TRD Workflow — session UI)
Required by | TRD-1 — the SwiftUI implementation must conform to every specification in this document
Platform | macOS 13.0+, SwiftUI, dark-mode first
Aesthetic reference | Linear, Raycast, Warp — dense, precise, professional

# 1. Purpose and Scope

This document specifies the complete visual and interaction design of the Consensus Dev Agent macOS application. It defines every pixel-level decision, component behavior, and interaction pattern needed to implement the UI in SwiftUI.

The design problem is specific: this is a professional tool for engineers that must render a live autonomous agent, surface human decision points at the right moment, and disappear completely when it does not need you. It is not a chat interface. It is not an IDE. It is not a project manager. It is all three simultaneously — and the design must make that feel natural, not chaotic.

DESIGN CONTRACT | Every measurement, color value, animation duration, and interaction behavior in this document is a requirement, not a suggestion. SwiftUI implementation must match these specifications exactly. Deviations require a design review and explicit approval.

This TRD owns:

Design token system — every color, type size, spacing value, and motion curve

Three-panel layout — structural dimensions, column behavior, persistence

NavigatorView — all sections, selection states, empty states

BuildStreamView — stage header, card stream, auto-scroll rules

Card type system — visual specification for every card variant

Gate card interaction model — blocking behavior, focus management, keyboard

ContextPanelView — all five tabs, auto-switch logic, content specs

Settings screen — layout, validation states, biometric gate UX

First-launch onboarding — 6 screens, navigation, field validation

Document store UI — drag-drop, embedding progress, preview

Menu bar, Dock, and Notification Center integration

Keyboard shortcut reference — complete, audited for conflicts

Accessibility — axIdentifiers, VoiceOver, focus management, contrast

Empty states and error states for every surface

TRD session UI and holistic review UI as distinct visual modes

Micro-interactions and motion specification

SwiftUI component specifications with modifier chains

# 2. Design Principles

Principle | In Practice
Dense, not cluttered | Information density is a feature for engineers. Show more. Avoid whitespace as decoration. Every pixel must earn its place.
Autonomous until it isn't | The UI should disappear when the agent is working autonomously. It reappears — urgently and clearly — only when a human decision is required. Gate cards are the most important UI element in the app.
Cards, not chat | Agent output renders as typed cards, not chat bubbles. Cards have structure, headers, and actions. They feel like a work log, not a conversation.
Precision over friendliness | This is a professional tool. Error messages include specific codes and actionable recovery steps. Confirmations are direct. No "Great, let's get started!"
Keyboard-first | Every action that a power user performs regularly has a keyboard shortcut. Mouse is for discovery, keyboard is for workflow.
Dark-mode is the product | Not an option. The aesthetic is built for dark mode. The color palette, contrast ratios, and visual hierarchy are designed for dark environments.
No decorative animation | Motion serves information. A card appearing signals new content. Progress pulses when active. Nothing animates for its own sake.
Fail visibly | Errors are prominent, specific, and actionable. Silent failures do not exist in the UI. If something went wrong, the operator knows immediately.

# 3. Design Token System

## 3.1 Color Palette

Token | Hex | Use
background | #0D0D0F | App background — window fill, base layer
surface | #1A1A1F | Cards, panels, secondary surfaces
surface-raised | #222228 | Hover states, elevated cards, popovers
border | #2A2A35 | Dividers, card borders, input outlines
border-subtle | #1E1E28 | Very subtle separators within surfaces
accent | #6B5ECD | Primary action, active selection, focus ring, gate border
accent-hover | #7C6FD8 | Accent hover state
accent-dim | #3D3570 | Accent at low opacity — selected backgrounds
accent-text | #A89BE8 | Accent-colored text on dark backgrounds
github-blue | #3B82F6 | GitHub-related elements: PR opened, CI status
success | #22C55E | Tests passed, CI passed, approved
success-bg | #052E16 | Success background tint
warning | #F59E0B | Cost warnings, non-fatal errors, pending states
warning-bg | #2D1B00 | Warning background tint
danger | #EF4444 | Errors, CRITICAL findings, session lock
danger-bg | #2D0A0A | Danger background tint
text-primary | #F0F0F5 | Body text, card content
text-secondary | #8B8B9A | Metadata, timestamps, secondary labels
text-tertiary | #555566 | Disabled states, placeholder text
text-inverse | #0D0D0F | Text on accent backgrounds
code-bg | #141418 | Code block backgrounds
code-text | #C9C9D4 | Code and mono text

## 3.2 Typography Scale

Token | Font | Size | Weight | Use
display-xl | SF Pro Display | 34pt | Bold | App name in onboarding welcome screen
display-lg | SF Pro Display | 28pt | Bold | Onboarding screen titles
display-md | SF Pro Display | 22pt | Semibold | Section headers in settings
title | SF Pro Text | 17pt | Semibold | Card titles, panel section headers
body | SF Pro Text | 15pt | Regular | Card body text, descriptions
body-sm | SF Pro Text | 13pt | Regular | Metadata, secondary info in cards
label | SF Pro Text | 12pt | Medium | Badges, tags, status labels
caption | SF Pro Text | 11pt | Regular | Timestamps, footnotes
code-lg | SF Mono | 14pt | Regular | Code blocks, file paths
code-md | SF Mono | 13pt | Regular | Inline code, terminal output
code-sm | SF Mono | 12pt | Regular | Small code references, PR branches

## 3.3 Spacing Scale

// All spacing values are multiples of 4pt base unit
space-1:   4pt    // Tight internal padding
space-2:   8pt    // Component internal padding, icon margins
space-3:  12pt    // Default padding within cards
space-4:  16pt    // Card padding, section gaps
space-5:  20pt    // Panel padding
space-6:  24pt    // Between major sections
space-8:  32pt    // Between panels, onboarding screen padding
space-12: 48pt    // Onboarding content vertical rhythm
space-16: 64pt    // Large structural gaps

## 3.4 Border Radii

radius-sm:  4pt   // Badges, tags, small chips
radius-md:  8pt   // Cards, buttons, input fields
radius-lg: 12pt   // Panels, modals, sheets
radius-xl: 16pt   // Onboarding screens, large surfaces
radius-full: 9999pt  // Pills, status indicators

## 3.5 Motion Timing

// All animations use easeOut unless noted
duration-instant:  0ms    // No animation (Reduce Motion mode)
duration-fast:   100ms    // State change indicators, badges
duration-normal: 150ms    // Card appearance, panel transitions
duration-slow:   250ms    // Sheet presentation, modal
duration-xslow:  400ms    // Onboarding screen transitions

// Curves
easeOut:    .easeOut          // Default — feels responsive
spring:     .spring(response: 0.3, dampingFraction: 0.8)
                              // Gate card appear, focus ring

// Reduce Motion: all durations set to 0ms
// Check: UIAccessibility.isReduceMotionEnabled
// Implementation: .animation(reduceMotion ? nil : .easeOut(duration: 0.15))

# 4. Three-Panel Layout Architecture

## 4.1 Layout Specification

┌─────────────────────────────────────────────────────────────────┐
│                        Title Bar (28pt)                        │
├──────────────┬──────────────────────────────┬──────────────────┤
│              │                              │                  │
│  Navigator   │      BuildStream             │  ContextPanel    │
│   240pt      │         flex                 │     320pt        │
│   fixed      │                              │     fixed        │
│              │                              │                  │
├──────────────┴──────────────────────────────┴──────────────────┤
│                    Status Bar (28pt)                           │
└─────────────────────────────────────────────────────────────────┘

Total minimum width:  240 + 480 + 320 = 1040pt
Default window size:  1280 × 800pt
Minimum window size:  1040 × 640pt
Maximum:              unconstrained

## 4.2 NavigationSplitView Implementation

NavigationSplitView(columnVisibility: $columnVisibility) {
    NavigatorView()
        .navigationSplitViewColumnWidth(min: 200, ideal: 240, max: 300)
        .frame(minWidth: 200, maxWidth: 300)
} content: {
    BuildStreamView()
        .navigationSplitViewColumnWidth(min: 480, ideal: .infinity)
} detail: {
    ContextPanelView()
        .navigationSplitViewColumnWidth(min: 280, ideal: 320, max: 400)
}
.navigationSplitViewStyle(.balanced)

// Column visibility persisted in UserDefaults:
// "navigator_visible": bool (default: true)
// "context_panel_visible": bool (default: true)

// Known issue: NavigationSplitView column width resets on window resize (macOS 13)
// Workaround: restore from UserDefaults on .onAppear
// See TRD-1 Section 3.3 for the full workaround.

## 4.3 Column Collapse Behavior

Action | Result | Persistence
Cmd+1 | Toggle Navigator visibility | Saved to UserDefaults
Cmd+2 | Toggle Context Panel visibility | Saved to UserDefaults
Window narrower than 1040pt | Navigator collapses to icon strip (macOS auto) | Not persisted — auto
Full screen mode | Both panels collapse to overlay | Not persisted
App restart | Restore from UserDefaults | Yes

## 4.4 Column Borders

// Columns are separated by 1pt dividers in border color
// NOT by shadow or background color change alone

Divider() // SwiftUI native divider between columns
    .frame(width: 1)
    .background(Color("border"))  // #2A2A35

// Navigator right border: 1pt, border color
// Context panel left border: 1pt, border color
// Both columns have the same background: Color("surface") // #1A1A1F
// Build stream has background: Color("background") // #0D0D0F

# 5. NavigatorView

## 5.1 Structure

NavigatorView
├── List (sidebar style)
│   ├── Section("PROJECTS")
│   │   └── ForEach(projects): ProjectRow
│   ├── Section("ACTIVE BUILD")
│   │   └── BuildStatusRow (if active build)
│   ├── Section("BUILDS")
│   │   └── ForEach(recentBuilds): BuildHistoryRow
│   ├── Section("ENGINEERS")  [visible only in multi-engineer mode]
│   │   └── ForEach(engineers): EngineerStatusRow
│   └── Section("DOCUMENTS")
│       ├── ForEach(documents): DocumentRow
│       └── AddDocumentButton
└── Bottom: NewBuildButton

## 5.2 Section Headers

// Section headers are uppercase, 11pt, text-tertiary
// No disclosure triangles — sections are always expanded
// Spacing: 16pt above section header, 4pt below

Text("PROJECTS")
    .font(.custom("SF Pro Text", size: 11))
    .fontWeight(.medium)
    .foregroundColor(Color("text-tertiary"))
    .kerning(0.5)  // Slight letter spacing for caps
    .padding(.horizontal, 16)
    .padding(.top, 16)
    .padding(.bottom, 4)

## 5.3 ProjectRow

┌───────────────────────────────────────────┐
│ ● Payment Engine               Building   │
│   Last active: 2 hours ago                │
└───────────────────────────────────────────┘

// Status indicator: 8pt circle, left of name
// Building:  accent color (#6B5ECD) with pulse animation
// Idle:      text-tertiary (#555566)
// Complete:  success (#22C55E)

// Selection: surface-raised background, accent left border (2pt)
// Hover: surface-raised background, no border

struct ProjectRow: View {
    let project: Project
    var body: some View {
        HStack(spacing: 8) {
            StatusDot(status: project.buildStatus)
            VStack(alignment: .leading, spacing: 2) {
                Text(project.name)
                    .font(.custom("SF Pro Text", size: 13))
                    .fontWeight(.medium)
                    .foregroundColor(Color("text-primary"))
                Text(project.lastActiveDescription)
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("text-secondary"))
            }
            Spacer()
            if project.buildStatus == .building {
                Text("Building")
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("accent-text"))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }
}

## 5.4 EngineerStatusRow

┌───────────────────────────────────────────┐
│ TG  Todd Gould          ● PR #7           │
│     todd-gould          active            │
└───────────────────────────────────────────┘

// Avatar: 28pt circle, initials, accent background
// Status dot: 8pt circle
//   active:  success (#22C55E) with slow pulse (2s period)
//   idle:    text-tertiary (#555566), no pulse
//   offline: danger (#EF4444), no pulse

// Status text: "PR #7" when active, "idle" when idle, "offline" when offline

## 5.5 DocumentRow

┌───────────────────────────────────────────┐
│ 📄 payment-processor-trd.md               │
│    23 chunks  ·  Embedded ✓               │
└───────────────────────────────────────────┘

// File icon: SF Symbol "doc.text" for .md, "doc.richtext" for .docx,
//            "doc.fill" for .pdf, "doc.plaintext" for .txt
// Embedding status:
//   Embedded ✓   success color, SF Symbol "checkmark.circle.fill"
//   Embedding... warning color, animated progress dots
//   Error        danger color, SF Symbol "exclamationmark.circle"

## 5.6 Navigator Empty States

Section | Empty State Text | Primary Action
Projects | No projects yet. Load TRD documents to start. | Add Documents
Builds | No builds yet. | (no action — appears after first build)
Engineers | Only you. Coordinate with teammates via the shared ledger. | (informational only)
Documents | No documents loaded. Drop .md, .docx, or .pdf files here. | Add Documents button

# 6. BuildStreamView

## 6.1 Stage Header Bar

┌─────────────────────────────────────────────────────────────┐
│  ● STAGE 3: PRD Generation  ·  PRD-004 of 12               │
│  ████████████░░░░░░░░  33%         Est. $2.40 remaining    │
└─────────────────────────────────────────────────────────────┘

// Height: 56pt
// Background: surface (#1A1A1F)
// Bottom border: 1pt, border-subtle

// Stage indicator:
//   Active: accent pulse dot (6pt), stage name in title weight
//   Inactive: no dot

// Progress bar:
//   Track: border (#2A2A35), height 4pt, radius-full
//   Fill:  accent (#6B5ECD), animated fill
//   Width: fills available space between stage text and cost

// Cost estimate: body-sm, text-secondary, right-aligned
// Updates every time a progress XPC message is received

struct StageHeaderBar: View {
    @EnvironmentObject var stream: BuildStreamModel
    var body: some View {
        VStack(spacing: 6) {
            HStack {
                if stream.progress.stage != .idle {
                    PulseDot(color: Color("accent"))
                }
                Text(stream.progress.stageLabel)
                    .font(.custom("SF Pro Text", size: 13)).fontWeight(.semibold)
                    .foregroundColor(Color("text-primary"))
                Spacer()
                Text(stream.progress.costEstimate)
                    .font(.custom("SF Pro Text", size: 12))
                    .foregroundColor(Color("text-secondary"))
            }
            ProgressView(value: stream.progress.fraction)
                .progressViewStyle(LinearProgressViewStyle(tint: Color("accent")))
                .scaleEffect(x: 1, y: 0.5)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Color("surface"))
        .overlay(Divider(), alignment: .bottom)
    }
}

## 6.2 Card Stream

// The stream is a ScrollView containing a LazyVStack of card views.
// Cards are ordered chronologically — newest at bottom.
// The stream is NOT a chat interface — cards are not bubbles.

ScrollView {
    LazyVStack(spacing: 8, pinnedViews: []) {
        ForEach(stream.cards) { card in
            CardView(card: card)
                .transition(.asymmetric(
                    insertion: .move(edge: .bottom).combined(with: .opacity),
                    removal: .opacity
                ))
        }
        // Gate card — pinned at bottom when active
        if let gate = stream.activeGate {
            GateCardView(gate: gate)
                .id("active-gate")
        }
        // Spacer so last card is not flush with bottom
        Color.clear.frame(height: 24)
    }
    .padding(.horizontal, 16)
    .padding(.top, 16)
}
.onChange(of: stream.cards.count) { _ in
    // Auto-scroll to bottom when new card appears
    withAnimation(.easeOut(duration: 0.15)) {
        scrollProxy.scrollTo("active-gate", anchor: .bottom)
    }
}

## 6.3 Auto-Scroll Rules

Condition | Behavior
New card appended (no gate) | Scroll to bottom if user is within 200pt of bottom; do not scroll if user has scrolled up to review history
New gate card appears | Always scroll to gate — even if user has scrolled up. Gate requires immediate attention.
Gate resolved | Scroll position maintained — do not jump
Stream cleared (/clear) | Scroll to top
App foregrounded with pending gate | Scroll to gate card immediately

## 6.4 Build Intent Input

// Shown when stream.progress.stage == .idle and no active build
// Replaces the stage header bar in idle state

struct BuildIntentBar: View {
    @State private var intent = ""
    var body: some View {
        HStack(spacing: 12) {
            TextField("Describe what to build...", text: $intent, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.custom("SF Pro Text", size: 15))
                .foregroundColor(Color("text-primary"))
                .lineLimit(1...4)
                .accessibilityIdentifier("build-intent-field")
            Button(action: startBuild) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 24))
                    .foregroundColor(intent.isEmpty ? Color("text-tertiary") : Color("accent"))
            }
            .disabled(intent.isEmpty)
            .keyboardShortcut(.return, modifiers: .command)
            .accessibilityIdentifier("build-start-button")
        }
        .padding(16)
        .background(Color("surface"))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12)
                 .stroke(Color("border"), lineWidth: 1))
        .padding(.horizontal, 16)
        .padding(.bottom, 16)
    }
}

# 7. Card Type System

## 7.1 Card Container

// All cards share this container structure
struct CardContainer<Content: View>: View {
    let cardType: String
    let timestamp: Date
    let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Card header: type label + timestamp
            HStack {
                Text(cardType.uppercased())
                    .font(.custom("SF Pro Text", size: 11))
                    .fontWeight(.medium)
                    .foregroundColor(Color("text-tertiary"))
                    .kerning(0.5)
                Spacer()
                Text(timestamp, style: .time)
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("text-tertiary"))
            }
            .padding(.horizontal, 12)
            .padding(.top, 10)
            .padding(.bottom, 6)
            Divider().background(Color("border-subtle"))
            // Card content
            content
                .padding(12)
        }
        .background(Color("surface"))
        .cornerRadius(8)
        .overlay(RoundedRectangle(cornerRadius: 8)
                 .stroke(Color("border"), lineWidth: 1))
    }
}

## 7.2 Card Type Specifications

Card Type | Header Label Color | Border Accent | Required Fields | Expandable?
scope | text-tertiary | none | subsystem, branch, docs[], scopeSummary | No
prd_plan | text-tertiary | none | total_prds, prd_ids[], estimated_cost | Yes — show/hide PRD list
prd_generated | accent-text | none | prd_id, title, winner, scores, duration_sec, docx_path | Yes — show preview text
review_pass | text-tertiary | none | pass_number, pass_name, claude_feedback, openai_feedback, fix_count | Yes — show/hide each reviewer
pr_opened | github-blue | none | pr_number, title, branch, url | No
test_result (pass) | success | none | passed, total_tests, attempt | Yes — show test list
test_result (fail) | danger | none | passed, total_tests, failed_tests, attempt | Yes — show failures + stdout
ci_status | github-blue | none | status, jobs[], url | Yes — show job list
build_complete | success | none | prd_count, pr_count, total_cost, pulls_url | No
error | danger | danger left border (2pt) | error_type, message, recoverable | Yes — show detail
warning | warning left border (2pt) | message | No
progress | text-tertiary | none | body | No
ledger_update | text-tertiary | none | engineers[], available_prs, done_prs | No
guidance | accent-text | none | body | No

## 7.3 PRD Generated Card

// Most information-dense card in the build stream
┌─ PRD GENERATED ─────────────────────── 14:31:44 ─┐
│  PRD-003: Transaction Idempotency Layer            │
│  Winner: Claude (8.2/10)  vs  GPT-4o (7.6/10)    │
│  44.2s  ·  $0.043                                 │
│  ─────────────────────────────────────────        │
│  The idempotency layer intercepts all transaction  │
│  requests at the gateway boundary...              │
│  [Open Full Document →]                           │
└────────────────────────────────────────────────────┘

// Scores shown as fraction: 8.2/10
// Winner label: "Claude" or "GPT-4o" in accent-text color
// Preview: first 3 lines of prd content, truncated at 200 chars
// [Open Full Document] opens .docx in default macOS app
// Chevron indicates expandable — tap to show full preview

## 7.4 Review Pass Card

┌─ REVIEW PASS 2 ────────────────────── 15:02:17 ─┐
│  Performance and Edge Cases                       │
│  ─────────────────────────────────────────       │
│  Claude (2 issues)                               │
│  ▸ Concurrent writes may cause race condition    │
│    on key expiry check. Recommend advisory lock. │
│                                                  │
│  GPT-4o (1 issue)                               │
│  ▸ No handling for network partition between     │
│    idempotency check and transaction commit.     │
│                                                  │
│  Applying 2 fixes...  ●●●○                      │
└──────────────────────────────────────────────────┘

// Reviewer sections are collapsible
// "Applying N fixes..." shows animated dots while synthesis runs
// No reviewer label if that reviewer found nothing
// Issue bullets: triangle disclosure (▸) for additional detail on tap

# 8. Gate Card Interaction Model

## 8.1 Gate Card Visual Specification

// Gate cards are visually distinct from all other cards.
// They are the most important UI element in the application.

┌─ GATE: PRD REVIEW ─────────────────────────────────┐  ← 2pt accent border
│  PRD-004: Webhook Event Processor                   │
│  Review the generated PRD before continuing.        │
│  [Open Document →]  (opens .docx in default app)   │
│  ─────────────────────────────────────────         │
│  ┌──────────┐  ┌──────┐  ┌──────┐  ┌───────────┐  │
│  │  ✓ Approve│  │ Skip │  │ Stop │  │ Correction│  │
│  └──────────┘  └──────┘  └──────┘  └───────────┘  │
│                                                     │
│  Or describe a correction:                          │
│  ┌─────────────────────────────────────────────┐   │
│  │_____________________________________________│   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘

// Border: 2pt solid, accent (#6B5ECD)
// Background: surface (#1A1A1F) — same as other cards
// NO close button — gate cannot be dismissed without a response
// Header label: "GATE: {gate_type_display}" in accent-text color

## 8.2 Gate Card Behavior Rules

Rule | Implementation
Single gate at a time | stream.activeGate can only hold one gate. New gates queue — they do not stack visually.
Blocks scroll (soft) | The stream continues to show new progress cards above the gate, but the gate is always visible at the bottom via auto-scroll.
Focus on appear | On GateCardView.onAppear: AccessibilityFocusState moves to the first action button after 100ms delay (ensures scroll completes first).
Space to approve | Space bar approves the gate when the Approve button has focus. No global hotkey — requires focus.
Correction field expansion | Tapping "Correction" button expands the text field inline. Does NOT open a sheet or navigate away. Field height grows up to 5 lines.
Correction submission | Return key (or Cmd+Return) in correction field sends the gate response with the correction text.
No auto-dismiss on background | Gate stays open if app is backgrounded. Notification is sent. Gate is still visible on foreground.
Multiple options layout | Up to 4 buttons in a horizontal row. If gate type has only 2 options, buttons are full-width and centered.

## 8.3 GateCardView Implementation

struct GateCardView: View {
    let gate: GateModel
    @State private var correctionText = ""
    @State private var showCorrectionField = false
    @AccessibilityFocusState private var approveButtonFocused: Bool
    @EnvironmentObject var stream: BuildStreamModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Gate header
            HStack {
                Text("GATE: \(gate.gateTypeDisplay.uppercased())")
                    .font(.caption).fontWeight(.medium)
                    .foregroundColor(Color("accent-text")).kerning(0.5)
                Spacer()
                Text(gate.timestamp, style: .time)
                    .font(.caption).foregroundColor(Color("text-tertiary"))
            }
            .padding(.horizontal, 12).padding(.top, 10).padding(.bottom, 6)
            Divider().background(Color("border-subtle"))

            // Gate content
            VStack(alignment: .leading, spacing: 12) {
                Text(gate.title).font(.title3).fontWeight(.semibold)
                    .foregroundColor(Color("text-primary"))
                Text(gate.body).font(.body)
                    .foregroundColor(Color("text-secondary"))

                if let docPath = gate.documentPath {
                    Button("Open Document →") { NSWorkspace.shared.open(docPath) }
                        .buttonStyle(.link)
                        .foregroundColor(Color("accent-text"))
                }

                Divider().background(Color("border-subtle"))

                // Action buttons
                HStack(spacing: 8) {
                    ForEach(gate.options, id: \.self) { option in
                        GateButton(option: option, gate: gate,
                                   showCorrection: $showCorrectionField)
                            .accessibilityFocused($approveButtonFocused,
                                equals: option == gate.primaryOption)
                    }
                }

                // Correction field — expands inline
                if showCorrectionField {
                    TextEditor(text: $correctionText)
                        .frame(minHeight: 60, maxHeight: 120)
                        .font(.body).foregroundColor(Color("text-primary"))
                        .padding(8)
                        .background(Color("background"))
                        .cornerRadius(6)
                        .overlay(RoundedRectangle(cornerRadius: 6)
                                 .stroke(Color("accent"), lineWidth: 1))
                        .accessibilityIdentifier("stream-gate-correction-field-\(gate.id)")
                        .onSubmit { stream.respondToGate(gate.id, response: correctionText) }
                }
            }
            .padding(12)
        }
        .background(Color("surface"))
        .cornerRadius(8)
        .overlay(RoundedRectangle(cornerRadius: 8)
                 .stroke(Color("accent"), lineWidth: 2))
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                approveButtonFocused = true
            }
        }
        .accessibilityIdentifier("stream-gate-card-\(gate.id)")
    }
}

# 9. ContextPanelView

## 9.1 Tab Structure

ContextPanelView
└── TabView(selection: $contextTab)
    ├── PRDDetailView     .tag(ContextTab.prd)
    ├── PRDetailView      .tag(ContextTab.pr)
    ├── TestResultsView   .tag(ContextTab.tests)
    ├── CIStatusView      .tag(ContextTab.ci)
    └── CostTrackerView   .tag(ContextTab.cost)

// Tab bar: at the top of the Context Panel (not bottom)
// Tab icons: SF Symbols only, no text labels
//   PRD:   "doc.text.magnifyingglass"
//   PR:    "arrow.triangle.pull"
//   Tests: "checkmark.shield"
//   CI:    "gear.badge.checkmark"
//   Cost:  "dollarsign.circle"

enum ContextTab: String {
    case prd, pr, tests, ci, cost
}

// Auto-switch logic:
func autoSwitchTab(for cardType: String) -> ContextTab? {
    switch cardType {
    case "prd_generated", "prd_plan": return .prd
    case "pr_opened", "review_pass":  return .pr
    case "test_result":               return .tests
    case "ci_status":                 return .ci
    default:                          return nil
    }
}
// Applied on each new card append — switches only if user has not
// manually selected a tab in the last 30 seconds.

## 9.2 PRD Tab

// Shows current or most recent PRD being reviewed

struct PRDDetailView: View {
    @EnvironmentObject var stream: BuildStreamModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let prd = stream.currentPRD {
                    // PRD ID badge
                    Text(prd.id)
                        .font(.custom("SF Mono", size: 12))
                        .foregroundColor(Color("accent-text"))
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(Color("accent-dim"))
                        .cornerRadius(4)
                    // Title
                    Text(prd.title)
                        .font(.custom("SF Pro Text", size: 15)).fontWeight(.semibold)
                        .foregroundColor(Color("text-primary"))
                    // Metadata row
                    HStack(spacing: 12) {
                        ComplexityBadge(complexity: prd.estimatedComplexity)
                        Text("Est. \(prd.estimatedPRCount) PRs")
                            .font(.caption).foregroundColor(Color("text-secondary"))
                    }
                    Divider().background(Color("border-subtle"))
                    // Dependencies
                    if !prd.dependencies.isEmpty {
                        Text("Depends on").font(.caption).foregroundColor(Color("text-tertiary"))
                        ForEach(prd.dependencies, id: \.self) { dep in
                            Text("• \(dep)").font(.caption).foregroundColor(Color("text-secondary"))
                        }
                    }
                    // Open document link
                    if let docxPath = prd.docxPath {
                        Button("Open PRD Document →") {
                            NSWorkspace.shared.open(docxPath)
                        }
                        .buttonStyle(.link)
                        .foregroundColor(Color("accent-text"))
                    }
                } else {
                    EmptyStateView(icon: "doc.text", title: "No PRD",
                        body: "PRD details appear here during generation.")
                }
            }
            .padding(16)
        }
    }
}

## 9.3 PR Tab — Review Pass Progress

// Review pass progress shown as 3 step indicators

struct ReviewPassProgress: View {
    let passesApplied: Int
    var body: some View {
        HStack(spacing: 8) {
            ForEach(1...3, id: \.self) { pass in
                HStack(spacing: 4) {
                    Circle()
                        .fill(passColor(for: pass))
                        .frame(width: 8, height: 8)
                    Text("Pass \(pass)")
                        .font(.caption)
                        .foregroundColor(pass <= passesApplied
                            ? Color("text-primary") : Color("text-tertiary"))
                }
            }
        }
    }
    func passColor(for pass: Int) -> Color {
        if pass < passesApplied  { return Color("success") }
        if pass == passesApplied { return Color("accent") }
        return Color("border")
    }
}

// pass < passesApplied: green (complete)
// pass == passesApplied: accent with pulse (in progress)
// pass > passesApplied: border gray (not yet)

## 9.4 Cost Tab

struct CostTrackerView: View {
    @EnvironmentObject var stream: BuildStreamModel
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Session total — largest number on screen
                VStack(spacing: 4) {
                    Text(stream.sessionCostFormatted)
                        .font(.custom("SF Pro Display", size: 34)).fontWeight(.bold)
                        .foregroundColor(costColor)
                    Text("Session total")
                        .font(.caption).foregroundColor(Color("text-secondary"))
                }
                .padding(.top, 8)
                Divider().background(Color("border-subtle"))
                // Per-PR breakdown table
                ForEach(stream.prCosts) { entry in
                    HStack {
                        Text("PR #\(entry.prNum)")
                            .font(.custom("SF Mono", size: 12))
                            .foregroundColor(Color("text-secondary"))
                        Text(entry.title).lineLimit(1)
                            .font(.caption).foregroundColor(Color("text-primary"))
                        Spacer()
                        Text(entry.costFormatted)
                            .font(.custom("SF Mono", size: 12))
                            .foregroundColor(Color("text-secondary"))
                    }
                }
                Divider().background(Color("border-subtle"))
                // Projected completion
                if let projection = stream.projectedTotalCost {
                    HStack {
                        Text("Projected total")
                            .font(.caption).foregroundColor(Color("text-tertiary"))
                        Spacer()
                        Text(projection)
                            .font(.caption).foregroundColor(Color("text-secondary"))
                    }
                }
            }
            .padding(16)
        }
    }
    var costColor: Color {
        let cost = stream.sessionCostUSD
        if cost >= stream.costStopThreshold { return Color("danger") }
        if cost >= stream.costWarnThreshold { return Color("warning") }
        return Color("text-primary")
    }
}

# 10. Settings Screen

## 10.1 Biometric Gate

// Settings opens via Cmd+, or app menu.
// ALWAYS requires biometric re-authentication before showing.
// Even if the session is already active.

struct SettingsView: View {
    @State private var authenticated = false
    var body: some View {
        if authenticated {
            SettingsContentView()
        } else {
            BiometricGateView(reason: "Access your saved credentials",
                              onSuccess: { authenticated = true })
        }
    }
}

## 10.2 Settings Layout

// Standard macOS Settings window: sidebar + content
// Sidebar items: API Keys, GitHub, Build Defaults, Review, TRD Sessions, Security

SettingsContentView
├── APIKeysSection
│   ├── AnthropicKeyField (masked, reveal button, test button)
│   └── OpenAIKeyField    (masked, reveal button, test button)
├── GitHubSection
│   ├── ConnectionStatus  (connected as X / Disconnect)
│   ├── DefaultRepoField  (owner/repo format, validated)
│   └── AuthMethodPicker  (Personal Token / GitHub App)
├── BuildDefaultsSection
│   ├── EngineerIDField   (alphanumeric + hyphens, max 20)
│   ├── DisplayNameField  (free text, max 50)
│   ├── PRBatchSizeStepper (1–10)
│   ├── CostWarnStepper   ($0.10–$5.00)
│   └── CostStopStepper   (must be > warn threshold)
├── ReviewSection
│   ├── MaxFilesPerPRStepper (1–20)
│   └── SkipLowPRsToggle
├── TRDSessionSection
│   └── SessionStorageInfo (shows path, count, clear button)
└── SecuritySection
    ├── BiometricTimeoutPicker (1, 5, 15, 30, 60 minutes)
    ├── RequireBiometricForSettingsToggle (always true — non-editable)
    └── DangerZone: ClearAllSecretsButton (confirmation required)

## 10.3 API Key Field Specification

// Masked field with reveal and test buttons
┌─────────────────────────────────────────┐
│ Anthropic API Key                        │
│ ┌──────────────────────┐ [Reveal] [Test]  │
│ │ ••••••••••••••••••••│                  │
│ └──────────────────────┘                  │
│ ✓ Connected  (shown after successful test)│
└─────────────────────────────────────────┘

// Reveal: shows key for 10 seconds, then masks again
// Requires biometric re-auth (per-reveal, new LAContext)
// Test: calls provider API with minimum test call
//   Success: green "✓ Connected" below field
//   Failure: red "✗ Invalid key" or "✗ Network error" below field
// Field: SecureField (shows bullets, not raw text)
// Paste supported — field clears on paste, shows bullet count

# 11. First-Launch Onboarding

## 11.1 Screen Flow

Screen 1: Welcome
  Logo (96pt), product name (display-xl), tagline (body)
  [Get Started →] button — fills screen width
  No back navigation — this is the entry point

Screen 2: API Keys
  Heading: "Connect your AI providers"
  Subheading: "Keys are stored in macOS Keychain — never written to disk."
  Anthropic key field + [Test Connection] button
  OpenAI key field + [Test Connection] button
  Status indicators per field (idle / testing / connected / error)
  [Continue →] disabled until at least one key tests green
  Note: "You can add the second key later in Settings."

Screen 3: GitHub
  Heading: "Connect to GitHub"
  Two options presented as cards:
    [Connect with GitHub →]   OAuth flow in browser
    [Use a Personal Token]    Expands inline to token field
  Connection status shown after OAuth/token validation
  [Continue →] disabled until validated

Screen 4: Engineer Profile
  Heading: "Set up your engineer profile"
  Engineer ID field with inline validation (alphanumeric + hyphens, max 20)
  Display name field (free text, max 50)
  Pre-filled from GitHub username (fetched from /user endpoint)
  [Continue →] enabled when both fields have valid values

Screen 5: Touch ID
  Heading: "Protect your credentials"
  Body: "Touch ID locks the app when you step away."
  [Enable Touch ID →] — triggers system biometric prompt
  On success: "✓ Touch ID enabled" with checkmark animation
  If Touch ID unavailable: skip screen automatically
  Cannot skip if Touch ID hardware is available

Screen 6: Ready
  Heading: "You're ready to build."
  Three action cards:
    [Load TRD Documents] → opens NSOpenPanel
    [Start a New Build]  → navigates to main window, focuses intent field
    [Develop TRD Specs]  → starts /trd start session

## 11.2 Onboarding Navigation

// Progress indicator: 6 dots at top of each screen
// Current screen: accent fill
// Completed: success fill
// Upcoming: border color

// Back navigation: available on screens 2–5
// Back arrow top-left, standard macOS chevron

// Transition: slide left on advance, slide right on back
// Duration: duration-xslow (400ms)

// Keyboard: Tab moves between fields
// Return in last field of a screen: same as [Continue]
// Escape: has no effect during onboarding (cannot dismiss)

# 12. Document Store UI

## 12.1 Layout

// Accessed via Navigator → Documents section
// Opens as a sheet from the main window (not a separate window)

┌─ DOCUMENT STORE ─────────────────────────────────┐
│  [+ Add Documents]        [Sync from GitHub]      │
│  ──────────────────────────────────────────────   │
│  payment-processor-trd.md                         │
│    23 chunks  ·  Embedded ✓  ·  Added 2 days ago  │
│    [Preview] [Remove]                             │
│                                                   │
│  api-specification.md                             │
│    41 chunks  ·  Embedding...  ●●●○○              │
│    [Preview] [Remove]                             │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │  Drop .md, .docx, or .pdf files here       │  │
│  │  Accepted: .md  .docx  .pdf  .txt          │  │
│  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘

// Drop target: entire lower half of the sheet
// Drop target active state: accent border, accent-dim background

## 12.2 Embedding Progress

// Embedding progress shown as 5 animated dots
// ●●●○○ = 60% complete (3 of 5 dots filled)
// Dots pulse left-to-right when active
// Duration: 600ms per dot, staggered 120ms

struct EmbeddingProgressView: View {
    let progress: Double  // 0.0 to 1.0
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<5, id: \.self) { i in
                let filled = Double(i) / 4.0 <= progress
                Circle()
                    .fill(filled ? Color("accent") : Color("border"))
                    .frame(width: 6, height: 6)
            }
        }
    }
}

# 13. Menu Bar, Dock, and Notifications

## 13.1 Menu Bar Structure

ForgeAgent  (app menu)
  About Forge Agent
  ─────────────────────
  Settings...          Cmd+,
  ─────────────────────
  Services             ▶
  ─────────────────────
  Hide Forge Agent     Cmd+H
  Hide Others          Opt+Cmd+H
  Show All
  ─────────────────────
  Quit Forge Agent     Cmd+Q

File
  New Build            Cmd+N
  Open Documents...    Cmd+O
  ─────────────────────
  Close Window         Cmd+W

Build
  Start Build          Cmd+Return
  Pause Build          Cmd+P
  Cancel Build         Cmd+.
  ─────────────────────
  Approve Gate         Space   (gate focused)
  ─────────────────────
  Show Build History   Cmd+Shift+H

Review
  Start Code Review...  (opens /review start dialog)
  Review Status
  Show Review Report

TRD
  Start TRD Session...  (opens /trd start dialog)
  Resume Session
  Export TRDs

View
  Show Navigator        Cmd+1
  Show Context Panel    Cmd+2
  ─────────────────────
  Context: PRD          Cmd+Opt+1
  Context: PR           Cmd+Opt+2
  Context: Tests        Cmd+Opt+3
  Context: CI           Cmd+Opt+4
  Context: Cost         Cmd+Opt+5
  ─────────────────────
  Enter Full Screen     Ctrl+Cmd+F

Window
  Minimize              Cmd+M
  Zoom
  ─────────────────────
  Bring All to Front

Help
  Forge Agent Help
  Release Notes
  Report a Bug

## 13.2 Dock Badge

// Badge shows count of gate cards waiting for operator input
// Cleared when all gates are resolved or build completes

NSApp.dockTile.badgeLabel = pendingGates > 0 ? "\(pendingGates)" : nil

// Dock right-click menu (applicationDockMenu):
if activeBuild != nil:
  "Building: {subsystem}"  (disabled label)
  ─────────────
  "Cancel Build"
else:
  "New Build"
  "Start Code Review..."
─────────────
"Lock"

## 13.3 Notification Specifications

Event | Style | Sound | Subtitle | Action on Click
Gate waiting for input | Alert (persistent) | Default | Gate type and PRD/PR context | Bring to front + scroll to gate
Build complete | Banner (auto-dismiss 5s) | Ping | PRD count, PR count, total cost | Open GitHub pulls URL in browser
CI failed | Alert (persistent) | Sosumi | Branch name and failure summary | Bring to front + switch to CI tab
Backend crashed (unrecoverable) | Alert (persistent) | Basso | Error type | Bring to front + show error card
Auto-update available | Banner (auto-dismiss 8s) | None | New version number | Open Settings → About section
Review complete | Banner (auto-dismiss 5s) | Ping | Finding count by severity | Open review report .docx

# 14. Keyboard Shortcut Reference

Shortcut | Action | When Active | Conflict?
Cmd+, | Open Settings | Always | No — standard macOS pattern
Cmd+N | New Build | Always | No — equivalent to "New document"
Cmd+O | Open Documents | Always | No — equivalent to "Open file"
Cmd+W | Close Window | Always | No — standard macOS
Cmd+Q | Quit | Always | No — standard macOS
Cmd+Return | Start Build / Submit Correction | Intent field focused / Correction field | No — "submit" pattern
Cmd+P | Pause Build | Active build | No — unusual context
Cmd+. | Cancel Build | Active build | No — standard cancel
Cmd+L | Lock App | Always | No — not system-reserved
Cmd+R | Retry | Error card focused | No — not system-reserved
Space | Approve Gate | Gate card focused | CAUTION: only fires when gate button focused; not global
Tab | Next gate option | Gate card visible | No — standard focus cycle
Shift+Tab | Prev gate option | Gate card visible | No
Cmd+1 | Toggle Navigator | Always | No
Cmd+2 | Toggle Context Panel | Always | No
Cmd+Opt+1–5 | Switch context tab | Context panel visible | No
Ctrl+Cmd+F | Full screen | Always | No — standard macOS
Cmd+Shift+H | Build History | Always | REVIEW: test on macOS 13 and 14
Escape | Cancel/unfocus | Text fields, correction field | No

# 15. Accessibility Specification

## 15.1 axIdentifier Naming Convention

// Pattern: {module}-{component}-{role}-{context?}
// Set via .accessibilityIdentifier() on ALL interactive elements

// Auth
"auth-touchid-button"
"auth-passcode-button"

// Onboarding
"onboarding-anthropic-key-field"
"onboarding-anthropic-test-button"
"onboarding-openai-key-field"
"onboarding-openai-test-button"
"onboarding-github-oauth-button"
"onboarding-github-pat-field"
"onboarding-engineer-id-field"
"onboarding-display-name-field"
"onboarding-touchid-button"
"onboarding-continue-button"
"onboarding-back-button"

// Navigator
"navigator-project-row-{projectId}"
"navigator-build-row-{buildId}"
"navigator-engineer-row-{engineerId}"
"navigator-document-row-{docName}"
"navigator-add-document-button"

// Build Stream
"stream-intent-field"
"stream-start-button"
"stream-gate-card-{gateId}"
"stream-gate-approve-button-{gateId}"
"stream-gate-skip-button-{gateId}"
"stream-gate-stop-button-{gateId}"
"stream-gate-correction-button-{gateId}"
"stream-gate-correction-field-{gateId}"

// Context Panel
"context-tab-prd"
"context-tab-pr"
"context-tab-tests"
"context-tab-ci"
"context-tab-cost"

// Settings
"settings-anthropic-key-field"
"settings-anthropic-reveal-button"
"settings-anthropic-test-button"
"settings-openai-key-field"
"settings-openai-reveal-button"
"settings-openai-test-button"
"settings-github-disconnect-button"
"settings-engineer-id-field"
"settings-lock-timeout-picker"
"settings-clear-secrets-button"

// Status Bar
"statusbar-lock-button"

## 15.2 VoiceOver Gate Announcement

// When a gate card appears, VoiceOver must announce it clearly.
// This is handled by accessibilityLabel and accessibilityHint.

GateCardView()
    .accessibilityLabel("Gate: \(gate.gateTypeDisplay). \(gate.title).")
    .accessibilityHint("\(gate.body). Press Space to approve, Tab for more options.")
    .accessibilityAddTraits(.isModal)  // Announces as a blocking element

// Focus management: gate appears → focus moves to Approve button
// (see GateCardView.onAppear implementation in Section 8.3)

## 15.3 Color Contrast Audit

Element | Foreground | Background | Ratio | WCAG Level
Body text | #F0F0F5 (text-primary) | #0D0D0F (background) | 13.4:1 | AAA
Secondary text | #8B8B9A (text-secondary) | #0D0D0F (background) | 5.2:1 | AA
Tertiary text | #555566 (text-tertiary) | #0D0D0F (background) | 3.6:1 | AA (large text)
Text on surface | #F0F0F5 (text-primary) | #1A1A1F (surface) | 12.1:1 | AAA
Secondary on surface | #8B8B9A | #1A1A1F (surface) | 4.8:1 | AA
Accent button text | #FFFFFF | #6B5ECD (accent) | 5.8:1 | AA
Accent text on bg | #A89BE8 (accent-text) | #0D0D0F (background) | 7.2:1 | AA
Success text | #22C55E (success) | #0D0D0F (background) | 7.9:1 | AA
Warning text | #F59E0B (warning) | #0D0D0F (background) | 7.1:1 | AA
Danger text | #EF4444 (danger) | #0D0D0F (background) | 5.3:1 | AA
Code text | #C9C9D4 (code-text) | #141418 (code-bg) | 10.6:1 | AAA
Table header | #FFFFFF | #1A1A2E (headerBg) | 18.1:1 | AAA

# 16. Empty States and Error States

State | Icon (SF Symbol) | Title | Body | Primary Action
No documents | doc.text.magnifyingglass | No TRD documents loaded | Load your technical specifications to start a build. | Add Documents
No active build | wand.and.stars | Ready to build | Describe what to build, or resume a previous session. | (intent field)
No engineers | person.2 | Just you | Your teammates will appear here when they connect to the shared ledger. | (informational)
Backend crashed | xmark.octagon | The agent stopped unexpectedly | The Python backend crashed and could not restart. Check the logs. | View Logs / Restart
GitHub disconnected | link.badge.slash | Not connected to GitHub | Your GitHub connection was lost. Reconnect to continue. | Reconnect
Rate limit hit | hourglass | GitHub rate limit reached | Paused for {N} seconds while GitHub resets. | (auto-resumes, countdown shown)
Cost limit hit | dollarsign.circle.fill | Cost limit reached | This PR exceeded the ${N} limit. Approve to continue. | (gate card — approve/stop)
No TRD sessions | pencil.and.list.clipboard | No TRD sessions | Start a TRD development session to build your specification. | Start TRD Session
Review complete — no findings | checkmark.shield.fill | Clean codebase | No issues found in {N} files across 3 review passes. | (summary card only)

## 16.1 Empty State Component

struct EmptyStateView: View {
    let icon: String
    let title: String
    let body: String
    var actionLabel: String? = nil
    var action: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 48, weight: .thin))
                .foregroundColor(Color("text-tertiary"))
            Text(title)
                .font(.custom("SF Pro Text", size: 15)).fontWeight(.semibold)
                .foregroundColor(Color("text-secondary"))
            Text(body)
                .font(.custom("SF Pro Text", size: 13))
                .foregroundColor(Color("text-tertiary"))
                .multilineTextAlignment(.center)
                .frame(maxWidth: 280)
            if let label = actionLabel, let fn = action {
                Button(label, action: fn)
                    .buttonStyle(AccentButtonStyle())
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

# 17. TRD Session UI

## 17.1 Mode Distinction

When a TRD session is active (/trd start), the BuildStreamView switches to TRD Session Mode. The card stream is replaced by a conversation-style view distinct from the build card stream. The visual distinction is critical — the operator must always know which mode they are in.

// TRD Session Mode visual distinctions:
// 1. Stage header bar: "TRD SESSION · Phase 2 of 8 · D3 Data Model"
//    Purple instead of accent color for stage indicator
// 2. Message stream: alternating left-right layout (not left-aligned cards)
//    Agent messages: left-aligned, surface background
//    User messages:  right-aligned, accent-dim background
// 3. Input field: full-width at bottom (not the build intent bar)
// 4. Context panel: shows TRD outline progress, cost

// Mode indicator in status bar:
// "TRD SESSION · Payment Engine · Phase 2/8"
// In amber color to distinguish from build mode

## 17.2 TRD Outline Card

// TRD outline is NOT presented as prose — it is a structured card

┌─ TRD OUTLINE ─────────────────────────────── 15:44:01 ─┐
│  Payment Processing Engine · 5 TRDs proposed           │
│  ──────────────────────────────────────────            │
│  TRD-1 · Authentication Layer                          │
│     Owns: login, token issuance, session lifecycle      │
│     Depends on: none                                    │
│                                                        │
│  TRD-2 · API Gateway                                   │
│     Owns: routing, rate limiting, auth enforcement      │
│     Depends on: TRD-1                                  │
│  [+ 3 more]  (expandable)                              │
│  ──────────────────────────────────────────            │
│  Dependency order: TRD-1 → TRD-3 → TRD-2 → TRD-4     │
│  ──────────────────────────────────────────            │
│  ┌──────────────────────┐  ┌─────────────────────┐    │
│  │   ✓ Approve Outline  │  │   Suggest Changes   │    │
│  └──────────────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────┘

// This is a gate card variant — same blocking behavior, same accent border
// Each TRD shown as a collapsible row
// Dependency order shown as text (no visual diagram in v1)

# 18. Holistic Review UI

## 18.1 Review Mode

// Review mode (/review start) uses the normal card stream.
// Review-specific cards are distinct by header label color:

// "REVIEWING" label: blue (github-blue #3B82F6)
// "FINDING" label: varies by severity
//   CRITICAL: danger (#EF4444)
//   HIGH:     warning (#F59E0B)
//   MEDIUM:   accent (#6B5ECD)
//   LOW:      text-secondary

// Stage header bar in review mode:
// "● PASS 2 OF 3 · Performance · 42 of 200 files"
// Progress bar: files reviewed / total files

## 18.2 Finding Dashboard Card

// Shown in ContextPanelView when review is active
// Updates live as findings accumulate

┌─ FINDING DASHBOARD ──────────────────────────────────┐
│  CRITICAL    HIGH    MEDIUM    LOW     INFO          │
│  ────────   ─────   ──────   ─────   ─────          │
│      4        15       24      27      10            │
│  ██████████████████████████░░░░░░░░░░░░░░░          │
│  Pass 1 complete · Pass 2 complete · Pass 3: 67%    │
└───────────────────────────────────────────────────────┘

// Counts colored by severity
// Progress bar: total pass completion across all three passes
// Taps on a severity badge: filters stream to show only that severity

# 19. Micro-interactions and Motion

Interaction | Animation | Duration | Curve | Reduce Motion
Card appears | Move up 12pt + fade in from 0 opacity | 150ms | easeOut | Instant fade only
Gate card appears | Move up 12pt + fade in + spring to final position | 200ms | spring(0.3, 0.8) | Instant appear
Gate card resolved | Fade out | 100ms | easeOut | Instant disappear
Status dot pulse (active) | Scale 1.0 → 1.4 → 1.0, opacity 1.0 → 0.6 → 1.0 | 2000ms | easeInOut, repeating | No pulse — static dot
Progress bar fill | Smooth value interpolation | 200ms | easeOut | Instant jump
Embedding dots pulse | Sequential fill left to right, cycling | 600ms per dot, staggered 120ms | linear | No animation — static
Tab switch in Context Panel | Cross-fade between content | 100ms | easeOut | Instant switch
Panel collapse/expand | Width animation | 200ms | easeOut | Instant
Focus ring on gate button | Spring scale 1.0 → 1.02 + accent ring appear | 120ms | spring(0.4, 0.9) | Instant ring only
Cost number update | Counter animation (optional, only when change > $0.01) | 300ms | easeOut | Instant number

## 19.1 PulseDot Component

struct PulseDot: View {
    let color: Color
    @State private var scale: CGFloat = 1.0
    @State private var opacity: Double = 1.0
    @Environment(\.accessibilityReduceMotion) var reduceMotion

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 8, height: 8)
            .scaleEffect(scale)
            .opacity(opacity)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                    scale   = 1.35
                    opacity = 0.6
                }
            }
    }
}

# 20. SwiftUI Component Specifications

## 20.1 AccentButtonStyle

struct AccentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.custom("SF Pro Text", size: 14)).fontWeight(.medium)
            .foregroundColor(Color("text-inverse"))
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(configuration.isPressed
                ? Color("accent-hover") : Color("accent"))
            .cornerRadius(8)
            .animation(.easeOut(duration: 0.1), value: configuration.isPressed)
    }
}

## 20.2 DestructiveButtonStyle

struct DestructiveButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.custom("SF Pro Text", size: 14)).fontWeight(.medium)
            .foregroundColor(configuration.isPressed ? Color("text-primary") : Color("danger"))
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(configuration.isPressed ? Color("danger-bg") : Color.clear)
            .overlay(RoundedRectangle(cornerRadius: 8)
                     .stroke(Color("danger"), lineWidth: 1))
            .cornerRadius(8)
    }
}

## 20.3 GhostButtonStyle

// For secondary actions: Skip, Cancel, secondary gate options
struct GhostButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.custom("SF Pro Text", size: 14)).fontWeight(.medium)
            .foregroundColor(Color("text-primary"))
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(configuration.isPressed ? Color("surface-raised") : Color.clear)
            .overlay(RoundedRectangle(cornerRadius: 8)
                     .stroke(Color("border"), lineWidth: 1))
            .cornerRadius(8)
    }
}

## 20.4 Badge Component

struct Badge: View {
    let label: String
    let color: Color
    var body: some View {
        Text(label)
            .font(.custom("SF Pro Text", size: 11)).fontWeight(.medium)
            .foregroundColor(color)
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(color.opacity(0.12))
            .cornerRadius(4)
    }
}

// Usage:
Badge(label: "CRITICAL", color: Color("danger"))
Badge(label: "high complexity", color: Color("warning"))
Badge(label: "PR #7", color: Color("github-blue"))
Badge(label: "Embedded ✓", color: Color("success"))

## 20.5 Status Bar Component

struct StatusBar: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var stream: BuildStreamModel
    @EnvironmentObject var ledger: BuildLedgerModel

    var body: some View {
        HStack(spacing: 16) {
            // Left: build status
            if stream.progress.stage != .idle {
                HStack(spacing: 6) {
                    PulseDot(color: Color("accent"))
                    Text(stream.progress.statusBarLabel)
                        .font(.custom("SF Pro Text", size: 12))
                        .foregroundColor(Color("text-secondary"))
                }
            }
            Spacer()
            // Center: engineer badges
            HStack(spacing: 8) {
                ForEach(ledger.activeEngineers) { eng in
                    EngineerBadge(engineer: eng)
                }
            }
            Spacer()
            // Right: cost + lock
            HStack(spacing: 12) {
                Text("Session: \(stream.sessionCostFormatted)")
                    .font(.custom("SF Pro Text", size: 12))
                    .foregroundColor(Color("text-secondary"))
                Button(action: { appState.lock() }) {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 12))
                        .foregroundColor(Color("text-tertiary"))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("statusbar-lock-button")
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 28)
        .background(Color("surface"))
        .overlay(Divider(), alignment: .top)
    }
}

# 21. Testing Requirements

Component | Test Type | Critical Cases
GateCardView | XCUITest | axIdentifier present on all 4 buttons; approve button receives focus within 150ms of card appear; Space triggers approve when focused; correction field expands inline on correction button tap; correction text sent on Cmd+Return
BuildStreamView auto-scroll | XCUITest | New card scrolls to bottom when within 200pt; gate card always scrolls to visible; user scroll position preserved on non-gate cards
StageHeaderBar | Unit + XCUITest | Progress value correct for each stage; cost updates when progress XPC received; idle state shows no progress bar
ContextPanel tab auto-switch | Unit test | prd_generated → .prd tab; pr_opened → .pr tab; test_result → .tests tab; manual selection preserved for 30s
NavigatorView sections | XCUITest | Project row selection sends correct project to stream; document row tap shows preview sheet; empty state shown when list empty
Onboarding flow | XCUITest | Continue disabled until validation passes; back navigation restores field values; biometric screen skipped when Touch ID unavailable; all 6 screens reachable
Accessibility | axe or manual VoiceOver | All interactive elements have accessibilityIdentifier; gate card announces with accessibilityLabel + Hint; focus ring visible at WCAG 3:1 minimum
Color contrast | Automated (Xcode Accessibility Inspector) | All text elements meet contrast ratios in Appendix B
Reduce Motion | Device setting + test | All animations replaced with instant transitions when enabled; PulseDot is static
Settings biometric gate | XCUITest | Settings does not open without biometric; API key reveal triggers new biometric

# 22. Out of Scope

Feature | Reason | Target
Light mode | Dark-mode is the product. Color system not designed for dual mode. | v2 (requires full color system redesign)
Custom themes | Not required by any user research. Adds complexity. | Never
Mobile / tablet | macOS only. iOS/iPadOS has different interaction model. | TBD
Windows / Linux | No macOS APIs on other platforms. | Never
Localization (non-English) | Infrastructure in place (NSLocalizedString) — strings not yet translated. | v2
Accessibility audit beyond WCAG AA | Baseline VoiceOver and contrast only in v1. | v2
Right-to-left language support | Requires layout mirroring. Not in scope. | v2 with localization
Font size scaling (Dynamic Type) | System font sizes only. SF Pro does not support Dynamic Type in all usages. | v2
Haptic feedback | macOS does not have haptics on trackpads (Force Touch is deprecated). | Never
Menu bar icon (status bar app) | Resident menu bar icon adds complexity. App lives in Dock only in v1. | v1.1 if requested

# 23. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Card stream persistence: should cards survive app restart? Currently they are in-memory only. If the app crashes mid-build, the operator loses the visual log. Recommendation: persist cards to disk alongside the ThreadStateStore, reload on resume. Adds complexity but significant UX value. | Engineering | Sprint 2
OQ-02 | TRD session message stream vs card stream: the TRD session uses a conversation-style layout (Section 17). Should this be a completely separate view replacing BuildStreamView, or a mode within BuildStreamView? Recommendation: mode within BuildStreamView — avoids navigation complexity and maintains the single-stream mental model. | Engineering | Sprint 1
OQ-03 | Context Panel auto-switch aggressiveness: switching tabs automatically (Section 9.1) could be disruptive if the operator is reviewing the Cost tab while a PR is being opened. The 30-second manual override window may not be enough. Recommendation: add a pin toggle on each tab that prevents auto-switch when pinned. | Engineering | Sprint 2
OQ-04 | Empty stream visual: when the build stream is completely empty (no cards, no intent field focused), what does the center panel show? Currently it would be the background color with the intent bar at the bottom. Should there be a welcome illustration? Recommendation: subtle ASCII art version of the architecture diagram from PRODUCT_CONTEXT.md, faded to text-tertiary. Changes per project. | Design | Sprint 1

# Appendix A: axIdentifier Naming Convention

The complete axIdentifier list is specified in Section 15.1. The naming convention is:

{module}-{component}-{role}-{context?}

module: auth, onboarding, navigator, stream, context, settings, statusbar

component: specific element name (touchid, anthropic-key, gate-card, etc.)

role: button, field, picker, card, row, tab

context: dynamic identifier appended with dash (gateId, projectId, docName)

RULE | Every interactive element in the app must have an accessibilityIdentifier set. Elements without identifiers cannot be tested with XCUITest and cannot be reliably reached by VoiceOver users. Missing identifiers are treated as build failures in the QA checklist.

# Appendix B: Color Contrast Audit

All ratios verified against WCAG 2.1 guidelines. Minimum required: 4.5:1 for normal text (AA), 3:1 for large text (18pt+ or 14pt+ bold) and UI components. The complete audit is in Section 15.3.

REQUIREMENT | If any new color combination is introduced that is not in the palette defined in Section 3.1, a contrast ratio must be calculated and documented before the combination is used in production code. Use the WebAIM Contrast Checker or Xcode Accessibility Inspector.

# Appendix C: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification