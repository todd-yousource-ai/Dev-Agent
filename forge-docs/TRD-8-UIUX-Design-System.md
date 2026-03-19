# TRD-8-UIUX-Design-System

_Source: `TRD-8-UIUX-Design-System.docx` — extracted 2026-03-19 15:59 UTC_

---

TRD-8

UI/UX Design System

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies the complete visual and interaction design of the Consensus Dev Agent macOS application. It defines every pixel-level decision, component behavior, and interaction pattern needed to implement the UI in SwiftUI.

The design problem is specific: this is a professional tool for engineers that must render a live autonomous agent, surface human decision points at the right moment, and disappear completely when it does not need you. It is not a chat interface. It is not an IDE. It is not a project manager. It is all three simultaneously — and the design must make that feel natural, not chaotic.

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

# 3. Design Token System

## 3.1 Color Palette

## 3.2 Typography Scale

## 3.3 Spacing Scale

## 3.4 Border Radii

## 3.5 Motion Timing

# 4. Three-Panel Layout Architecture

## 4.1 Layout Specification

## 4.2 NavigationSplitView Implementation

## 4.3 Column Collapse Behavior

## 4.4 Column Borders

# 5. NavigatorView

## 5.1 Structure

## 5.2 Section Headers

## 5.3 ProjectRow

## 5.4 EngineerStatusRow

## 5.5 DocumentRow

## 5.6 Navigator Empty States

# 6. BuildStreamView

## 6.1 Stage Header Bar

## 6.2 Card Stream

## 6.3 Auto-Scroll Rules

## 6.4 Build Intent Input

# 7. Card Type System

## 7.1 Card Container

## 7.2 Card Type Specifications

## 7.3 PRD Generated Card

## 7.4 Review Pass Card

# 8. Gate Card Interaction Model

## 8.1 Gate Card Visual Specification

## 8.2 Gate Card Behavior Rules

## 8.3 GateCardView Implementation

# 9. ContextPanelView

## 9.1 Tab Structure

## 9.2 PRD Tab

## 9.3 PR Tab — Review Pass Progress

## 9.4 Cost Tab

# 10. Settings Screen

## 10.1 Biometric Gate

## 10.2 Settings Layout

## 10.3 API Key Field Specification

# 11. First-Launch Onboarding

## 11.1 Screen Flow

## 11.2 Onboarding Navigation

# 12. Document Store UI

## 12.1 Layout

## 12.2 Embedding Progress

# 13. Menu Bar, Dock, and Notifications

## 13.1 Menu Bar Structure

## 13.2 Dock Badge

## 13.3 Notification Specifications

# 14. Keyboard Shortcut Reference

# 15. Accessibility Specification

## 15.1 axIdentifier Naming Convention

## 15.2 VoiceOver Gate Announcement

## 15.3 Color Contrast Audit

# 16. Empty States and Error States

## 16.1 Empty State Component

# 17. TRD Session UI

## 17.1 Mode Distinction

When a TRD session is active (/trd start), the BuildStreamView switches to TRD Session Mode. The card stream is replaced by a conversation-style view distinct from the build card stream. The visual distinction is critical — the operator must always know which mode they are in.

## 17.2 TRD Outline Card

# 18. Holistic Review UI

## 18.1 Review Mode

## 18.2 Finding Dashboard Card

# 19. Micro-interactions and Motion

## 19.1 PulseDot Component

# 20. SwiftUI Component Specifications

## 20.1 AccentButtonStyle

## 20.2 DestructiveButtonStyle

## 20.3 GhostButtonStyle

## 20.4 Badge Component

## 20.5 Status Bar Component

# 21. Testing Requirements

# 22. Out of Scope

# 23. Open Questions

# Appendix A: axIdentifier Naming Convention

The complete axIdentifier list is specified in Section 15.1. The naming convention is:

{module}-{component}-{role}-{context?}

module: auth, onboarding, navigator, stream, context, settings, statusbar

component: specific element name (touchid, anthropic-key, gate-card, etc.)

role: button, field, picker, card, row, tab

context: dynamic identifier appended with dash (gateId, projectId, docName)

# Appendix B: Color Contrast Audit

All ratios verified against WCAG 2.1 guidelines. Minimum required: 4.5:1 for normal text (AA), 3:1 for large text (18pt+ or 14pt+ bold) and UI components. The complete audit is in Section 15.3.

# Appendix C: Document Change Log