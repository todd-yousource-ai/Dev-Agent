# TRD-8-UIUX-Design-System

_Source: `TRD-8-UIUX-Design-System.docx` — extracted 2026-03-21 21:32 UTC_

---

# TRD-8: UI/UX Design System

Technical Requirements Document — v2.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-8: UI/UX Design System
Version | 2.0
Status | Updated — Figma Pipeline and Multi-Modal Input (March 2026)
Author | YouSource.ai
Previous Version | v1.0 (2026-03-19)
Depends on | TRD-1, TRD-3, TRD-6, TRD-7 v2, TRD-5 (GitHub)
New dependency | Figma REST API, Figma MCP Server

## What Changed from v1.0

v1.0 specified the complete macOS SwiftUI UI for the build pipeline and TRD workflow. This version adds three new input pathways that change how users enter the design-to-code pipeline:

Major additions in v2.0: - Sketch and image input — napkin drawings, whiteboard photos, rough wireframes interpreted by vision model and converted to Figma designs (§6.5 — updated) - Figma pipeline UI — the full design-to-code flow with Figma as source of truth for all UI decisions (§24 — new) - TRD Session UI updated for three operator modes — FOUNDER, ENGINEER, CONSULTANT (§17 — updated) - CONSULTANT mode meeting UI — client summary preview, compliance capture indicators, deployment target selector (§25 — new)

Sections 1–16, 18–23 are unchanged from v1.0. Only the sections below are new or updated.

## 6.4 Build Intent Bar — Updated (v2.0)

The Build Intent Bar gains two new input modes alongside the existing text field: image upload and Figma import.

### 6.4.1 Updated Input Bar Structure

┌────────────────────────────────────────────────────────────────┐
│  [📎] [🎨]  Describe what to build...                    [↑]  │
└────────────────────────────────────────────────────────────────┘

The two new icons: - 📎 — Upload image (napkin sketch, whiteboard photo, wireframe screenshot) - 🎨 — Import from Figma (paste Figma file URL or connect via OAuth)

struct BuildIntentBar: View {
    @State private var intent = ""
    @State private var attachedImage: NSImage? = nil
    @State private var figmaURL: String? = nil
    @State private var showImagePicker = false
    @State private var showFigmaImport = false

    var body: some View {
        VStack(spacing: 8) {
            // Attached image preview (shown when image is attached)
            if let image = attachedImage {
                AttachedImagePreview(image: image) {
                    attachedImage = nil
                }
            }

            // Figma URL preview (shown when Figma URL is attached)
            if let url = figmaURL {
                FigmaURLPreview(url: url) {
                    figmaURL = nil
                }
            }

            HStack(spacing: 12) {
                // Image upload button
                Button(action: { showImagePicker = true }) {
                    Image(systemName: "paperclip")
                        .font(.system(size: 16))
                        .foregroundColor(
                            attachedImage != nil
                                ? Color("accent")
                                : Color("text-tertiary")
                        )
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("attach-image-button")
                .help("Upload sketch, wireframe, or design image")

                // Figma import button
                Button(action: { showFigmaImport = true }) {
                    Image(systemName: "paintpalette")
                        .font(.system(size: 16))
                        .foregroundColor(
                            figmaURL != nil
                                ? Color("accent")
                                : Color("text-tertiary")
                        )
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("figma-import-button")
                .help("Import design from Figma")

                // Divider
                Rectangle()
                    .frame(width: 1, height: 20)
                    .foregroundColor(Color("border"))

                // Text input
                TextField("Describe what to build...", text: $intent, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(.custom("SF Pro Text", size: 15))
                    .foregroundColor(Color("text-primary"))
                    .lineLimit(1...4)
                    .accessibilityIdentifier("build-intent-field")

                // Send button — active when any input is present
                Button(action: startBuild) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(
                            (intent.isEmpty && attachedImage == nil && figmaURL == nil)
                                ? Color("text-tertiary")
                                : Color("accent")
                        )
                }
                .disabled(intent.isEmpty && attachedImage == nil && figmaURL == nil)
                .keyboardShortcut(.return, modifiers: .command)
                .accessibilityIdentifier("build-start-button")
            }
            .padding(16)
        }
        .background(Color("surface"))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color("border"), lineWidth: 1)
        )
        .padding(.horizontal, 16)
        .padding(.bottom, 16)
        .sheet(isPresented: $showImagePicker) {
            ImagePickerSheet(onSelect: { image in
                attachedImage = image
                showImagePicker = false
            })
        }
        .sheet(isPresented: $showFigmaImport) {
            FigmaImportSheet(onImport: { url in
                figmaURL = url
                showFigmaImport = false
            })
        }
    }
}

### 6.4.2 Attached Image Preview

struct AttachedImagePreview: View {
    let image: NSImage
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Image(nsImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(maxHeight: 120)
                .cornerRadius(6)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(Color("border"), lineWidth: 1)
                )

            VStack(alignment: .leading, spacing: 4) {
                Text("Sketch attached")
                    .font(.custom("SF Pro Text", size: 13))
                    .fontWeight(.medium)
                    .foregroundColor(Color("text-primary"))
                Text("Vision model will interpret this design")
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("text-secondary"))
                Button("Remove", action: onRemove)
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("danger"))
                    .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(12)
        .background(Color("surface-raised"))
        .cornerRadius(8)
    }
}

### 6.4.3 Drag-and-Drop onto Build Stream

Images can be dragged directly onto the BuildStreamView when idle. The drop target activates with an accent-colored overlay:

// Drop target on BuildStreamView
.onDrop(of: [.image, .fileURL], isTargeted: $isDragTarget) { providers in
    // Handle dropped image — same pipeline as image picker
    handleImageDrop(providers)
    return true
}
.overlay(
    isDragTarget ? DropTargetOverlay() : nil
)

struct DropTargetOverlay: View {
    var body: some View {
        RoundedRectangle(cornerRadius: 12)
            .stroke(Color("accent"), lineWidth: 2)
            .background(
                Color("accent-dim")
                    .cornerRadius(12)
                    .opacity(0.3)
            )
            .overlay(
                VStack(spacing: 8) {
                    Image(systemName: "photo.badge.plus")
                        .font(.system(size: 32))
                        .foregroundColor(Color("accent"))
                    Text("Drop sketch or wireframe to interpret")
                        .font(.custom("SF Pro Text", size: 15))
                        .foregroundColor(Color("accent-text"))
                }
            )
    }
}

## 6.5 Sketch Interpretation Card (New in v2.0)

When an image is submitted, a new card type appears in the build stream showing the interpretation in progress, then the result.

┌─────────────────────────────────────────────────────────────────┐
│ SKETCH INTERPRETATION                              12:34:05      │
│ ─────────────────────────────────────────────────────────────── │
│  [thumbnail]  Interpreting your design...                       │
│               ████████████░░░░░░░░  Analyzing layout           │
└─────────────────────────────────────────────────────────────────┘

After interpretation:

┌─────────────────────────────────────────────────────────────────┐
│ SKETCH INTERPRETATION                              12:34:12      │
│ ─────────────────────────────────────────────────────────────── │
│  [thumbnail]  Layout identified: Dashboard with sidebar nav,    │
│               main content area, 3 data cards, header bar       │
│                                                                  │
│  Components detected:                                            │
│    NavigationSidebar  ·  DataCard × 3  ·  HeaderBar             │
│    UserAvatar  ·  SearchField  ·  ActionButton × 2              │
│                                                                  │
│  [ Generate Figma Design ]    [ Correct interpretation ]        │
└─────────────────────────────────────────────────────────────────┘

struct SketchInterpretationCard: View {
    let card: SketchInterpretationCardModel

    var body: some View {
        CardContainer(cardType: "SKETCH INTERPRETATION",
                      timestamp: card.timestamp) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    // Thumbnail
                    Image(nsImage: card.image)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 80, height: 60)
                        .cornerRadius(4)
                        .overlay(
                            RoundedRectangle(cornerRadius: 4)
                                .stroke(Color("border"), lineWidth: 1)
                        )

                    // Interpretation status or result
                    if card.isInterpreting {
                        InterpretationProgress(stage: card.progressStage)
                    } else {
                        InterpretationResult(result: card.result)
                    }
                }

                // Action buttons (shown after interpretation)
                if !card.isInterpreting, let result = card.result {
                    HStack(spacing: 8) {
                        Button("Generate Figma Design") {
                            generateFigmaDesign(from: result)
                        }
                        .buttonStyle(PrimaryActionButtonStyle())

                        Button("Correct interpretation") {
                            showCorrectionSheet = true
                        }
                        .buttonStyle(SecondaryActionButtonStyle())
                    }
                }
            }
        }
    }
}

## 17. TRD Session UI — Updated (v2.0)

v1.0 specified a single TRD session UI. v2.0 adds mode-specific visual treatments for FOUNDER, ENGINEER, and CONSULTANT modes defined in TRD-7 v2.

### 17.1 Mode Indicator

All three modes show a persistent mode badge in the TRD session stage header:

┌─────────────────────────────────────────────────────────────────┐
│ ● TRD SESSION · Phase 2: Architecture Discovery    [FOUNDER]    │
│ ████████░░░░░░░░  3 of 7 domains covered    Est. $4.20 total   │
└─────────────────────────────────────────────────────────────────┘

Mode badge colors: - [FOUNDER] — accent background (#6B5ECD), white text - [ENGINEER] — surface-raised background, text-secondary text - [CONSULTANT] — #F59E0B (warning color) background, dark text — signals live meeting context

struct ModeBadge: View {
    let mode: OperatorMode

    var body: some View {
        Text(mode.displayLabel)
            .font(.custom("SF Pro Text", size: 11))
            .fontWeight(.medium)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(mode.badgeColor)
            .foregroundColor(mode.badgeTextColor)
            .cornerRadius(4)
    }
}

extension OperatorMode {
    var displayLabel: String {
        switch self {
        case .founder:    return "FOUNDER"
        case .engineer:   return "ENGINEER"
        case .consultant: return "CONSULTANT"
        case .unknown:    return "DETECTING"
        }
    }

    var badgeColor: Color {
        switch self {
        case .founder:    return Color("accent")
        case .engineer:   return Color("surface-raised")
        case .consultant: return Color("warning")
        case .unknown:    return Color("border")
        }
    }
}

### 17.2 FOUNDER Mode Question Display

In FOUNDER mode, questions are displayed with a conversational visual treatment — not the dense technical format used in ENGINEER mode.

┌─────────────────────────────────────────────────────────────────┐
│ TRD SESSION QUESTION                               12:41:03     │
│ ─────────────────────────────────────────────────────────────── │
│                                                                  │
│  When someone uses your product for the first time,             │
│  what information do they give you?                             │
│                                                                  │
│  Domain: Understanding your data  [2 of 7 covered]             │
└─────────────────────────────────────────────────────────────────┘

Domain progress shown in plain language, not domain IDs: - “Understanding your data” (not “D3: Data Model”) - “How people log in” (not “D4: Authentication”) - “What happens when things go wrong” (not “D5: Error Handling”)

### 17.3 CONSULTANT Mode UI

CONSULTANT mode adds three UI elements not present in other modes:

1. Meeting timer — shown in the stage header bar:

┌─────────────────────────────────────────────────────────────────┐
│ ● TRD SESSION · Phase 3: Component Boundaries   [CONSULTANT]   │
│ ████████████░░░░░░░  52 of 90 min elapsed   ⏸ Pause meeting   │
└─────────────────────────────────────────────────────────────────┘

The pause button calls /trd pause — saves state immediately and shows a “Meeting paused” card.

2. Compliance indicator — shown in Context Panel when compliance requirements are detected:

struct ComplianceIndicatorView: View {
    let frameworks: [String]  // ["HIPAA", "SOC 2"]

    var body: some View {
        if !frameworks.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text("COMPLIANCE REQUIREMENTS")
                    .font(.custom("SF Pro Text", size: 11))
                    .fontWeight(.medium)
                    .foregroundColor(Color("text-tertiary"))
                    .kerning(0.5)

                ForEach(frameworks, id: \.self) { framework in
                    HStack(spacing: 6) {
                        Image(systemName: "checkmark.shield.fill")
                            .font(.system(size: 12))
                            .foregroundColor(Color("warning"))
                        Text(framework)
                            .font(.custom("SF Pro Text", size: 13))
                            .foregroundColor(Color("text-primary"))
                        Text("controls applied")
                            .font(.custom("SF Pro Text", size: 11))
                            .foregroundColor(Color("text-secondary"))
                    }
                }
            }
            .padding(12)
            .background(Color("warning-bg"))
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color("warning").opacity(0.3), lineWidth: 1)
            )
        }
    }
}

3. Deployment target selector — shown in Context Panel after deployment target is determined:

struct DeploymentTargetView: View {
    @Binding var target: DeploymentTarget

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("DEPLOYMENT TARGET")
                .font(.custom("SF Pro Text", size: 11))
                .fontWeight(.medium)
                .foregroundColor(Color("text-tertiary"))
                .kerning(0.5)

            Picker("", selection: $target) {
                Label("Windows App", systemImage: "pc")
                    .tag(DeploymentTarget.windowsApp)
                Label("Mac App", systemImage: "laptopcomputer")
                    .tag(DeploymentTarget.macApp)
                Label("Linux Service", systemImage: "server.rack")
                    .tag(DeploymentTarget.linuxService)
                Label("Cloud Service", systemImage: "cloud")
                    .tag(DeploymentTarget.cloudService)
                Label("Hybrid", systemImage: "square.stack.3d.up")
                    .tag(DeploymentTarget.hybrid)
            }
            .pickerStyle(.menu)
        }
    }
}

## 24. Figma Design Pipeline UI (New in v2.0)

### 24.1 Overview

The Figma pipeline is a new execution path that sits between design and code generation. It activates when: - A Figma file URL is submitted via the Build Intent Bar - The sketch interpretation card’s “Generate Figma Design” button is pressed - A completed Figma design is detected in a connected Figma account

### 24.2 Figma Import Sheet

struct FigmaImportSheet: View {
    @State private var figmaURL = ""
    @State private var connectionStatus: FigmaConnectionStatus = .disconnected
    let onImport: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Import from Figma")
                .font(.custom("SF Pro Text", size: 17))
                .fontWeight(.semibold)
                .foregroundColor(Color("text-primary"))

            // Connection status
            FigmaConnectionStatusView(status: connectionStatus)

            // URL input
            VStack(alignment: .leading, spacing: 6) {
                Text("Figma file URL")
                    .font(.custom("SF Pro Text", size: 13))
                    .foregroundColor(Color("text-secondary"))
                TextField(
                    "https://www.figma.com/design/...",
                    text: $figmaURL
                )
                .textFieldStyle(.plain)
                .font(.custom("SF Mono", size: 13))
                .foregroundColor(Color("code-text"))
                .padding(10)
                .background(Color("code-bg"))
                .cornerRadius(6)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(
                            figmaURL.isEmpty
                                ? Color("border")
                                : Color("accent"),
                            lineWidth: 1
                        )
                )
            }

            Text("The agent will read your Figma design and generate code that matches it exactly.")
                .font(.custom("SF Pro Text", size: 13))
                .foregroundColor(Color("text-secondary"))

            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                    .buttonStyle(SecondaryActionButtonStyle())
                Button("Import Design") {
                    onImport(figmaURL)
                }
                .buttonStyle(PrimaryActionButtonStyle())
                .disabled(figmaURL.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 480)
    }
}

### 24.3 Figma Pipeline Card Sequence

When a Figma URL is submitted, a sequence of cards appears in the build stream:

Card 1: Figma Reading

┌─────────────────────────────────────────────────────────────────┐
│ FIGMA DESIGN                                       12:45:01     │
│ ─────────────────────────────────────────────────────────────── │
│  🎨  Reading design from Figma...                               │
│      payment-dashboard.fig · 12 frames · 47 components         │
│      ████████████░░░░░░░  Parsing component tree               │
└─────────────────────────────────────────────────────────────────┘

Card 2: Design Summary (gate card)

┌─────────────────────────────────────────────────────────────────┐
│ FIGMA DESIGN REVIEW                                12:45:08     │
│ ─────────────────────────────────────────────────────────────── │
│  Design read successfully.                                       │
│                                                                  │
│  Screens: 12   Components: 47   Color tokens: 18                │
│  Typography: 6 styles   Breakpoints: Desktop, Tablet, Mobile   │
│                                                                  │
│  Components to generate:                                         │
│    DashboardLayout  ·  SidebarNav  ·  DataCard × 4             │
│    TransactionTable  ·  UserAvatar  ·  SearchBar               │
│    NotificationBadge  ·  StatusChip  ·  ActionMenu             │
│                                                                  │
│  [ Build from this design ]    [ Update design first ]          │
└─────────────────────────────────────────────────────────────────┘

Card 3: Code Generation Progress

┌─────────────────────────────────────────────────────────────────┐
│ FIGMA → CODE                                       12:45:22     │
│ ─────────────────────────────────────────────────────────────── │
│  Generating components from design...                           │
│                                                                  │
│  ✓  DashboardLayout.tsx                                         │
│  ✓  SidebarNav.tsx                                              │
│  ●  DataCard.tsx  (generating...)                               │
│  ○  TransactionTable.tsx                                        │
│  ○  UserAvatar.tsx                                              │
└─────────────────────────────────────────────────────────────────┘

### 24.4 Figma Design Preview in Context Panel

When a Figma design is active, the Context Panel’s fifth tab switches from “Settings” to “Design”:

// Tab bar in ContextPanelView — updated for Figma
enum ContextTab: String {
    case prd      = "PRD"
    case pr       = "PR"
    case ci       = "CI"
    case cost     = "Cost"
    case design   = "Design"   // New — replaces Settings when Figma active
    case settings = "Settings"
}

struct FigmaDesignTab: View {
    let figmaFile: FigmaFileModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // File info
                HStack {
                    Image(systemName: "paintpalette.fill")
                        .foregroundColor(Color("accent"))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(figmaFile.name)
                            .font(.custom("SF Pro Text", size: 13))
                            .fontWeight(.medium)
                            .foregroundColor(Color("text-primary"))
                        Text("Last updated \(figmaFile.lastModified)")
                            .font(.custom("SF Pro Text", size: 11))
                            .foregroundColor(Color("text-secondary"))
                    }
                    Spacer()
                    Button("Open in Figma") {
                        NSWorkspace.shared.open(figmaFile.url)
                    }
                    .buttonStyle(.plain)
                    .font(.custom("SF Pro Text", size: 11))
                    .foregroundColor(Color("accent-text"))
                }

                Divider().background(Color("border-subtle"))

                // Component list
                Text("COMPONENTS")
                    .font(.custom("SF Pro Text", size: 11))
                    .fontWeight(.medium)
                    .foregroundColor(Color("text-tertiary"))
                    .kerning(0.5)

                ForEach(figmaFile.components) { component in
                    FigmaComponentRow(component: component)
                }
            }
            .padding(16)
        }
    }
}

### 24.5 Sketch-to-Figma Progress Card

When a napkin sketch triggers Figma design generation:

┌─────────────────────────────────────────────────────────────────┐
│ GENERATING FIGMA DESIGN                            12:52:14     │
│ ─────────────────────────────────────────────────────────────── │
│  Creating your design in Figma from sketch...                   │
│                                                                  │
│  ✓  Layout structure created                                    │
│  ✓  Navigation components placed                                │
│  ●  Data display cards  (placing...)                            │
│  ○  Typography styles                                           │
│  ○  Color tokens applied                                        │
│  ○  Component library attached                                  │
│                                                                  │
│  [ Open Figma to review ]  (available after generation)         │
└─────────────────────────────────────────────────────────────────┘

The “Open Figma to review” button becomes active when generation is complete. It opens the generated Figma file directly in the Figma desktop app or browser via the file URL returned by the API.

## 25. Client Summary Preview UI — CONSULTANT Mode (New in v2.0)

### 25.1 Overview

At the end of a CONSULTANT mode TRD session, the client summary document is generated and previewed inside the agent before export. This gives the consultant a final review step before sharing with the client.

### 25.2 Client Summary Review Card

┌─────────────────────────────────────────────────────────────────┐
│ CLIENT SUMMARY READY                               14:32:01     │
│ ─────────────────────────────────────────────────────────────── │
│  Payment Automation Platform                                     │
│  ─────────────────────────────────────────────────────────────  │
│  What We're Building                                             │
│  A platform that automatically matches incoming payments to      │
│  open invoices, reducing manual reconciliation from 4 hours     │
│  to under 15 minutes per day.                                    │
│                                                                  │
│  Who It's For                                                    │
│  Accounts payable teams at mid-sized manufacturing companies     │
│                                                                  │
│  ★  SOC 2 controls applied  ·  Windows deployment               │
│  ─────────────────────────────────────────────────────────────  │
│  [ Export .docx ]   [ Email to client ]   [ Start building ]   │
└─────────────────────────────────────────────────────────────────┘

struct ClientSummaryCard: View {
    let summary: ClientSummaryModel

    var body: some View {
        CardContainer(cardType: "CLIENT SUMMARY READY",
                      timestamp: summary.timestamp) {
            VStack(alignment: .leading, spacing: 12) {
                // Product name
                Text(summary.productName)
                    .font(.custom("SF Pro Text", size: 15))
                    .fontWeight(.semibold)
                    .foregroundColor(Color("text-primary"))

                Divider().background(Color("border-subtle"))

                // Preview of first two sections
                SummarySection(
                    title: "What We're Building",
                    content: summary.whatWeAreBuilding
                )
                SummarySection(
                    title: "Who It's For",
                    content: summary.whoItsFor
                )

                // Compliance and deployment badges
                HStack(spacing: 8) {
                    ForEach(summary.complianceFrameworks, id: \.self) { fw in
                        ComplianceBadge(framework: fw)
                    }
                    DeploymentBadge(target: summary.deploymentTarget)
                }

                Divider().background(Color("border-subtle"))

                // Action buttons
                HStack(spacing: 8) {
                    Button("Export .docx") {
                        exportClientSummary()
                    }
                    .buttonStyle(SecondaryActionButtonStyle())

                    Button("Email to client") {
                        emailClientSummary()
                    }
                    .buttonStyle(SecondaryActionButtonStyle())

                    Spacer()

                    Button("Start building") {
                        startBuildPipeline()
                    }
                    .buttonStyle(PrimaryActionButtonStyle())
                }
            }
        }
    }
}

### 25.3 Sign-Off State

After the consultant sends the summary and the client approves, the card updates to show sign-off state:

┌─────────────────────────────────────────────────────────────────┐
│ CLIENT SUMMARY — APPROVED                          14:47:22     │
│ ─────────────────────────────────────────────────────────────── │
│  ✓  Payment Automation Platform                                  │
│     Client approved · Ready to build                            │
│                                                                  │
│  [ Begin build pipeline ]                                       │
└─────────────────────────────────────────────────────────────────┘

## Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Complete macOS SwiftUI UI specification
2.0 | 2026-03-20 | YouSource.ai | Figma pipeline UI, sketch/image input, drag-and-drop, three TRD session modes (FOUNDER/ENGINEER/CONSULTANT), compliance indicators, deployment target selector, client summary preview card