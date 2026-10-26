---
name: lundy-design-system
description: Apply the shared Lundy product design standard to Scene QR or other authorized projects. Use for new frontend components, page redesigns, mobile usability, animation, content hierarchy and design reviews. Build consistently while respecting product-specific branding and working functionality.
---
# Lundy Design System Skill

## Start here
1. Read repository AGENTS.md and product instructions. Then read `design/LUNDY_DESIGN_SYSTEM.md` and any project-specific design rollout document.
2. Check actual screens, CSS/JS, backend contracts, role model and existing tests. Do not assume a feature is real because marketing mentions it.
3. Choose one bounded user journey; write a state/interaction/component map before redesigning.
4. Preserve brand personality and existing functional behavior. Don't import Apple proprietary design assets or pretend Apple endorses this product.

## Method
- Reuse semantic design tokens; avoid random one-off color, size, radius and blur values.
- Build complete components including loading/error/empty/disabled/success/focus states; meet keyboard and assistive-tech needs.
- Mobile-first with safe areas, real tap targets, readable forms, stable panels and no horizontal content overflow.
- Animate meaning, not every element. Provide reduced-motion support and performance fallbacks for glass/blur/video.
- Make real status and data persistence explicit; do not fake payments, confirmed orders or realtime integrations.
- Run baseline tests, make minimal changes, run tests again, and audit business A vs B permissions where applicable.
- Compare screenshots/flow results at phone, tablet and desktop; disclose coverage gaps.

## Project-specific defaults
- Scene QR: first ship a frictionless guest scan/request/status journey, then owner dashboard consistency. Read `design/SCENE_QR_DESIGN_ROLLOUT.md`.
- RVC: preserve the actual price table, appointments, bilingual owner functionality and automotive identity; motion must not break conversions.
- Ghostline: emphasize truthfulness of AI output, safe data boundaries, actionable insights, and legible complexity.

## Deliverable
For each change provide: design goal, token/component changes, affected routes and states, before/after evidence, tests actually run, outstanding issues, and whether backend integration or deployment is still missing.

Read `premium-product-design`, `cinematic-motion-and-materials`, `business-flow-ux-and-microcopy`, `inclusive-responsive-frontend`, and `premium-release-audit` skills as needed.
