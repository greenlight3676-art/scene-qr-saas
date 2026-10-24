---
name: inclusive-responsive-frontend
description: Improve accessibility, inclusive UX, mobile-first responsiveness, internationalization, input modes, performance, and robust browser behavior when building or reviewing web and SaaS interfaces.
---
# Inclusive Responsive Frontend

## Baseline
Adapt Apple HIG inclusive-design principles to web semantics and WCAG 2.2 AA. Do not pretend native accessibility APIs alone make a website accessible.

## Checklist
- Semantics: landmark structure, one meaningful H1, coherent heading order, real buttons/links/labels, aria only when necessary.
- Keyboard: complete tab order, visible focus, Escape/back behavior, modal focus trap and restoration, no keyboard traps, skip link.
- Screen readers: accurate accessible names, status announcements via appropriate live regions, decorative images hidden, meaningful images described.
- Contrast: >=4.5:1 normal text and >=3:1 large text and essential controls where WCAG applies. Test on imagery and translucent materials at light/dark extremes.
- Targets: WCAG 2.2 AA minimum 24x24 CSS pixels (with allowable exceptions/spacing); aim for 44x44 or larger where practical. Apple 44-point guidance is native-platform specific, not a web standard.
- Motion: prefers-reduced-motion, stop/pause for repeating animated content; no flashing; never make effects essential to understanding.
- Text/resizing: 200% text zoom without loss of content, 400% browser zoom/reflow, dynamic container widths, no clipped dialogs or sticky headers.
- Forms: visible persistent labels, clear errors, input autocomplete, sensible mobile keyboards, correct locale/date/number treatment, prevent duplicate writes.
- Internationalization: text expansion and wrapping, English/Spanish when relevant, date/time/currency localization, bidi-friendly layout, avoid hard-coded direction.
- Multiple senses: caption meaningful video; no sound-only or color-only status; icon+text labels; alternate control methods where appropriate.
- Adaptivity: touch, mouse, keyboard, orientation changes, tablet split-screen and common viewport widths; no hover-only actions.
- Network and content: skeleton or progress state, offline/error/retry behavior, efficient image sizes, lazy-load below-fold assets, support low data modes where possible.
- Performance: measure Core Web Vitals under representative conditions; preserve LCP/INP/CLS and low-end devices, avoid claims without measurements.
- Privacy: minimize collection, accessible consent language, never disclose cross-tenant content.

## Verification
Test real or emulated small-phone, large-phone, tablet and desktop widths; keyboard only; VoiceOver or NVDA when available; light and dark; reduced-motion; 200%/400% zoom; high contrast and slow network. Record manual tests actually performed vs recommended. Fix blockers before decorative refinements.

## References
- https://developer.apple.com/videos/play/wwdc2025/316/
- https://developer.apple.com/design/human-interface-guidelines/
- https://www.w3.org/TR/WCAG22/
- https://web.dev/vitals/
