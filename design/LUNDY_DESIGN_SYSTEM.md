# LUNDY DESIGN SYSTEM — Web Product Standard
Version 1.0 · October 2026 · Foundational specification

## Goal and scope
Make Scene QR and future Lundy-built client experiences feel distinctive, trustworthy, cinematic and genuinely easy to use. Adapt principles from Apple's Human Interface Guidelines and WWDC design sessions to the **web**; this is not an Apple asset library, certification or instruction to imitate Apple branding. Preserve each client's identity and production functionality.

This document defines cross-project rules. Each application must implement its own token values and interaction choices; never copy business/customer data, auth, or server components between projects.

## Design principles in order
1. **Reality before aesthetics**: real functionality, truthful state, saved data and safe authorization precede polish.
2. **Purpose and hierarchy**: one clear primary task per view; headings, grouping and spacing explain what matters.
3. **Agency and responsibility**: consent, undo where appropriate, transparent permissions, visible errors, no dark patterns.
4. **Familiarity and flexibility**: predictable tabs, labels and gestures, responsive layouts, localization-ready copy.
5. **Craft and delight**: consistent details, meaningful feedback, subtle transitions, no animation as camouflage.
6. **Inclusion**: interaction with touch, pointer, keyboard, assistive technology and reduced motion.
7. **Performance is design**: fast input response, stable geometry, compressed assets, no gratuitous main-thread work.

## Token architecture (semantic values; tune per brand)
Use semantic CSS variables or equivalent, not untracked literal values throughout components:
- Color: `--color-canvas`, `--color-surface`, `--color-surface-raised`, `--color-ink`, `--color-ink-muted`, `--color-border`, `--color-brand`, `--color-on-brand`, `--color-focus`, `--color-positive`, `--color-warning`, `--color-danger`.
- Typography: `--font-body`, `--font-display`; type scale 12/14/16/20/24/32/48/64 px as a **starting vocabulary**, not a mandate. Primary mobile body copy should be ~16px, scalable with browser zoom and user settings; use `clamp()` for responsive display text. Headings communicate meaning, not only visual size.
- Spacing: 4/8/12/16/24/32/48/64 px; use consistent rhythms and optical balance. Large expressive marketing spacing must not crowd task workflows.
- Radius: 8/12/16/24 px; overlay and nested surfaces should use coordinated rather than arbitrary radii.
- Elevation: border → low shadow → raised popover → modal; avoid unnecessary layered shadows and blur.
- Motion: micro 120–180ms; transitions 180–300ms; larger deliberate reveal 350–600ms, adjustable by context. Prefer opacity + transform; avoid animating dimensions on busy screens.
- Density: `comfortable` for guests and onboarding, `productive` for owner dashboard tables. Preserve minimum text and target readability in dense views.
- Theme: semantic color mappings for dark and light if implemented; test text and indicators for high contrast; never use color alone to communicate state.

## Brand adapters
- **Scene QR**: midnight graphite canvas, warm ivory text, plum/bronze highlights, selective teal success, elegant forms, fast scan experience. Avoid forcing immersive intro before each guest action.
- **RVC Window Tinting**: cinematic high-contrast automotive photography, black/off-white/electric-lime, deliberate scroll choreography; booking and pricing still first-class.
- **Ghostline AI**: dark command-center atmosphere, clear data provenance, explainable AI states, disciplined information density and role boundaries.
- **Other clients**: infer visual language from real business audience and current brand; do not reuse the same palette or hero template universally.

## Layout and navigation
- Mobile-first; test 320, 375, 390, 768, 1024 and 1440 CSS px. Avoid horizontal scroll except deliberate tables/carousels.
- Include safe-area insets where needed, keyboard-open behavior, 200% zoom, long translations, device rotation and touch ergonomics.
- Primary navigation remains understandable across device sizes; preserve orientation during route/filter changes.
- Critical controls remain available without hover. Touch targets generally >=44x44 CSS px where practical; where WCAG 2.2 AA minimum differs, satisfy applicable criteria and preserve adequate spacing.
- Avoid interruptive intros. If intro exists, allow skip, persist preference as appropriate, do not block deep links or reduced-motion visitors.

## Components and required states
Every reusable control must specify normal, hover (if applicable), active, focus-visible, disabled, loading, success, invalid/error and selected states. Common primitives:
- Button/link/icon button; select, checkbox, radio, tabs, segmented control.
- Input/textarea/combobox with persistent label, help text, real error association and validation.
- App shell, responsive navigation, breadcrumb, cards, content panels.
- Status chips and progress steps with text or icon meaning.
- Toast, alert, inline notice, popover, sheet and modal with keyboard behavior/focus return.
- Tables/lists with pagination, sort/filter/search, skeleton and empty/error states.
- QR preview, download/print action, scan landing, receipt/status view.
- Charts with labelled units, comparable scales, legible legends and textual data alternatives.
- Image and video with stable sizing, compression, meaningful alt text and fallback states.

## Interaction design and motion
- Use motion to explain continuity, place, relationship or state: button acknowledgment, expanding detail, status transition, sheet navigation.
- Keep persistent animation off primary content and work areas. Animate only when interaction or storytelling earns it.
- Glass/transparency only for overlays and lightweight chrome when text contrast survives varied backgrounds. Provide solid-color fallbacks.
- `prefers-reduced-motion: reduce`: remove nonessential entrance, parallax and looping effects; preserve essential state changes without motion.
- Restore focus after modal close, communicate progress to assistive tech without repetitive announcements, avoid hover-only disclosure.
- Never label an unconfirmed request as paid/confirmed/completed or present mock integrations as active.

## UX writing and localization
- Labels name actions specifically: "Create QR code", "Send request", "Mark complete" rather than "Continue" when meaning unclear.
- State the consequence of irreversible changes and offer recovery when possible.
- Error copy: what went wrong + useful next step; avoid blaming users; avoid leaking technical details.
- Respect English/Spanish expansion, RTL possibility and culturally neutral icon meaning; do not concatenate strings for translation.
- Separate marketing copy, product status copy, and authenticated operations copy; never invent guarantees, merchants or outcomes.

## Accessibility baseline
- Target WCAG 2.2 AA; validate contrast, headings, landmarks, programmatic labels, logical order, visible focus, keyboard operability, text resize and screen-reader state announcements.
- Modal and sheet focus is contained while open and restored after closing; Escape behavior where appropriate.
- Forms have real labels, error summaries where useful and errors tied to fields; don't rely on placeholder alone.
- Charts have accessible summaries and tabular alternatives; QR images include the actual destination and textual instructions.
- Authentication and time-sensitive flows should avoid unnecessary cognitive/time barriers.

## Performance and security-facing UX
- Budget toward Core Web Vitals p75: LCP <=2.5s, INP <=200ms, CLS <=0.1 on representative devices/network. Record actual measurements; not guarantees.
- Lazy-load noncritical imagery, preload truly critical assets sparingly, dimension media, avoid enormous autoplay video on guest screens.
- Protect all private routes with server-side authorization; enforce tenant scoping on APIs and queries. The visual layer is never a permission boundary.
- Keep auth, encryption, integrations, persistent data, request statuses, and payment claims truthful to what backend really does.

## Reference reading
- https://developer.apple.com/design/human-interface-guidelines/
- https://developer.apple.com/videos/design/
- https://developer.apple.com/videos/play/wwdc2025/219/
- https://developer.apple.com/videos/play/wwdc2025/356/
- https://developer.apple.com/videos/play/wwdc2025/359/
- https://developer.apple.com/videos/play/wwdc2024/10145/
- https://developer.apple.com/videos/play/wwdc2025/404/
- https://developer.apple.com/videos/play/wwdc2025/316/
- https://developer.apple.com/videos/play/wwdc2022/110340/
- https://www.w3.org/TR/WCAG22/
- https://web.dev/articles/vitals
