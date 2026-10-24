---
name: premium-product-design
description: Design or redesign polished product interfaces, dashboards, landing pages, mobile web experiences, and reusable UI systems using Apple HIG/WWDC-inspired principles adapted responsibly for the web. Use before making significant visual, layout, or navigation changes.
---
# Premium Product Design

## Mission
Create a recognizable, carefully crafted product with strong usability. Treat Apple's Human Interface Guidelines (HIG) and WWDC sessions as sources of transferable principles, NOT authorization to copy proprietary Apple assets or claim Apple certification. Respect the product's own brand. This skill applies to Scene QR, automotive businesses, client websites, and future products.

## Design workflow
1. Read the repository's AGENTS.md, product docs, current screens/styles and functional tests. Inventory page types and user roles. Do not overwrite working features.
2. Define user jobs, top three tasks per role, content hierarchy, success metrics, and entry/exit states. For QR guest flows, optimize time-to-first-action and no-signup scanning.
3. Build a small design-token map before components: semantic foreground/background, primary/secondary/muted, feedback colors, typography scale, spacing, radius, borders, elevation, motion and breakpoints. Preserve established brand palette unless change requested.
4. Make screens from reusable primitives: app shell, masthead, nav, sections, cards, buttons, controls, inputs, tables, lists, toasts, dialogs, empty states, loading states.
5. Design mobile-first at 320-390px, then tablet and wide desktop. Include safe-area handling, sticky controls, keyboard opening, long text and 200% zoom. Use breakpoint-based layout changes, never hide necessary actions.
6. Define actionable component behavior: default, hover where supported, pressed, focus-visible, disabled, loading, success, warning, error, selected, offline/empty.
7. Check real data density and edge cases: long names, zero records, errors, slow network, hundreds of rows, locale expansion, sensitive/private data, large text.
8. Explain design decisions in a concise component/flow spec; implement incrementally and verify, without adding unrelated dependencies.

## Transferable HIG/WWDC rules
- **Purpose/clarity:** content comes first; prominent primary action; no visual noise obscuring tasks.
- **Hierarchy/familiarity:** predictable primary navigation, grouped actions, meaningful headings and labels; use spatial relationships and layout before decoration.
- **Agency/trust:** reversible mistakes, clear consent, permissions explained, no deceptive funnels; do not imply payments, bookings, or production integrations that don't exist.
- **Craft/consistency:** align radii, baselines, typography, paddings, icon stroke, elevation and spacing across *every* page.
- **Adaptivity:** light/dark when useful, responsive typography and density, LTR/RTL readiness, desktop pointer and mobile touch distinctions.
- **Materials:** translucent/glass surfaces reserved for restrained navigation overlays and transient controls, with opacity fallbacks; no glass-on-glass stacks or unreadable text.
- **Delight:** feedback that communicates state; avoid forced intros, blocking loaders, endless particle effects, or motion that hides content.
- **Writing:** short action-led labels, consistent nouns, benefits before instructions, no filler and no contradictory terminology.

## Deliverables and acceptance
Provide token decisions, component inventory, screen map, state inventory, and critical-flow test matrix. Never declare polished based only on a static screenshot: inspect actual interaction, state changes and responsive layouts. Preserve existing data and security behavior.

## Research sources
- https://developer.apple.com/design/human-interface-guidelines/
- https://developer.apple.com/videos/play/wwdc2025/356/
- https://developer.apple.com/videos/play/wwdc2025/219/
- https://developer.apple.com/videos/play/wwdc2025/359/
