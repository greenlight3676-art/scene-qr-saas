---
name: cinematic-motion-and-materials
description: Build fluid, cinematic yet usable web interactions, page transitions, reveals, scroll motion, interactive simulators, and premium layered materials. Use when asked for animations, cinematic style, scroll-driven storytelling, or Liquid Glass-inspired behavior.
---
# Cinematic Motion & Materials

## Principles
Motion explains cause, destination, hierarchy, progress, selection and feedback. It is never allowed to hide controls or disrupt critical business flows. Treat Apple's Liquid Glass as an optical/behavioral design reference for native platforms; do not misrepresent plain CSS blur as native Liquid Glass.

## Implement in layers
1. Map the experience: entry, page transitions, scroll sections, controls, overlays, forms and completion. Decide what must remain instantly operable.
2. Assign choreography by meaning:
   - microinteractions: pressed/hover/focus/selected, typically 100-220ms;
   - content entrances: restrained 180-420ms, stagger only when it improves hierarchy;
   - route/detail continuity: 250-550ms as appropriate, preserving focus/scroll;
   - brand film/hero: optional, nonblocking, with clear skip and no forced repeated intro.
   Durations are web starting heuristics, not Apple specifications; tune against device performance and real users.
3. Use CSS transform/opacity for frequent animation; avoid expensive layout-triggering properties and huge blur backdrops; avoid multiple large video decoders.
4. Prefer interruptible transitions. If a user taps twice or navigates back mid-animation, state must remain correct and actions must not queue unpredictably.
5. Connect origin to destination using shared-element transitions where viable; provide straightforward fallback when unsupported. Avoid motion teleporting unrelated elements.
6. Support touch without assuming hover. Buttons and sliders respond immediately; never require touch gestures as the sole route to a function.
7. Use restrained glass-like navigation overlays: subtle translucency + backdrop sampling with solid fallback, legible text, safe hit regions. Don't stack translucent controls endlessly.
8. For scroll animation, keep content in DOM and readable if JS fails; never animate every section perpetually. Disable effects on reduced-motion or low-power/slow devices as needed.
9. For media-heavy automotive hero sections: optimized responsive video/poster, muted autoplay only when permitted, pause offscreen, support captions and fallback image. Optimize Largest Contentful Paint (LCP).
10. Test 320px iPhone-width, midrange Android, desktop; scrolling while animations run, keyboard opening, slow network, low-power and reduced-motion.

## Must-have acceptance tests
- prefers-reduced-motion removes nonessential movement; content remains available.
- Keyboard focus and screen-reader announcements remain correct during transitions.
- Controls respond during route transitions, not after waiting for animation.
- No layout shifts from late image/video sizing.
- 60fps is a target where realistic, not an unverified promise. Measure actual frame pacing and long tasks.
- Animations never mutate private state or trigger duplicate submissions.
- Print and no-JS fallbacks retain essential content.

## Inspirations
- https://developer.apple.com/videos/play/wwdc2025/219/
- https://developer.apple.com/videos/play/wwdc2024/10145/
- https://developer.apple.com/videos/play/wwdc2025/323/
