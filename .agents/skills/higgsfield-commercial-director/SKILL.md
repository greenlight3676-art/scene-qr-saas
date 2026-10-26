---
name: higgsfield-commercial-director
description: Plan and direct persuasive, photorealistic AI video ads for Higgsfield, especially 15-second mobile-first SaaS commercials. Use official Higgsfield tools and references. Prioritize a visible product demonstration, concrete actions, continuity and production preflight over aesthetic adjectives.
---

# Higgsfield Commercial Director — Sales-First Skill v1.0

## Goal
Produce videos that communicate a real offer in seconds and feel plausibly shot by a commercial crew. Make the audience understand **who benefits, what action happens, and what to do next**. Never guarantee views, conversions, virality, or revenue.

## Source of truth
- Official upstream skills: https://github.com/higgsfield-ai/skills
- Production: https://higgsfield.ai/enterprise-help-center/platform/tools-creative-workflow
- Official prompt notes: https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md
- Always verify current availability, model parameters, prices, subscription limitations, and consent before actually generating.

## Routing
1. **Advertising, commercial, product demonstration, UGC, TV spot** -> Higgsfield Marketing Studio. Its `tv_spot` and `product_showcase` modes may be suitable for non-UGC commercials; verify live model settings first. Brand/product URL or reference imagery helps ground the source.
2. **Precise lenses, dolly/orbit/POV, production-style direction, stable characters and locations** -> Cinema Studio. Use Elements and reusable references when available. Do not assume every Cinema Studio control exists on a user's plan.
3. **Image-to-video motion from a controlled hero keyframe** -> DoP or supported image-to-video model, with motion-centric short prompt; don't redescribe the still.
4. **Review a finished video** -> Virality Predictor when available; interpret its score as a heuristic, not a guarantee of business results.
5. **One-time limited trial** -> prefer a preflight plan and single well-grounded render. No paid generation, trial spend, or bulk variants without explicit authorization.

## Required intake (derive from context; ask only if essential)
- Product, customer, buyer, and ONE main commercial promise.
- Distribution format (default mobile 9:16), duration (default 15 sec), desired action (CTA).
- Correct product mechanics; real interface/screenshots/brand assets if possible.
- Available generation count and model/plan constraints.

## Creative architecture
Produce these BEFORE the final render prompt:
1. **One-line proposition**: 'Customer can [action] -> business gets [result]'.
2. **Time-coded shot plan**: every shot has its own setting, subject, physical action, camera direction, visible proof, audio and transition.
3. **Reference plan**: the fewest characters, scenes, device screens and props that clearly communicate the promise.
4. **Continuity**: clothing, hands, phone model, business signage, location layout and screen state stay consistent within each shot. Changes are cuts, not morphs.
5. **Conversion test**: could a stranger accurately explain the product after a silent 15-second watch?
6. **Feasibility check**: too many cuts, hands, interactions or screen transitions in a single generation are a failure risk; simplify before rendering.

## Prompt rules
- Write **short model-facing prompts** with concrete sensory detail, purposeful verbs and camera grammar. Prefer roughly 80–200 tokens per shot where supported; keep long scripts as separate planning notes.
- Explicitly state subject + setting + action + camera position/movement + lighting + endpoint. Example: 'A restaurant guest scans a tabletop QR card with a smartphone. Medium over-shoulder 35mm shot, steady three-foot push-in; employee glances at tablet and approaches the correct table. Natural noon window light. End on the employee arriving.'
- Name camera path, duration/speed, starting and ending composition; avoid 'epic cinematic camera' alone.
- Keep technical requirements realistic; use positively specified goals ('readable, sharp phone interface', 'physically coherent gestures') rather than piling on negatives.
- **Do not trust AI-generated precise logos, tiny interface text, exact QR payloads or URLs.** Prepare clean phone-screen replacement/overlay and brand title card in post, ideally from actual product screenshots. Do not claim the generated interactions prove the app's backend works.
- Make the result visually striking through deliberate edit rhythm, contrast, staging and business payoff, not random effects.

## 15-second ad construction
- **0.0–2.5 sec Hook:** show a customer problem or satisfying visual immediately. No five-second logo intro.
- **2.5–10.5 sec Proof:** show someone perform the key action, and a relevant employee react or fulfill it. If multiple industries are essential, use 2–3 short distinct examples tied together by one repeated interaction motif.
- **10.5–13.0 sec Benefit:** express concrete business benefit as a short editorial text overlay or very short line.
- **13.0–15.0 sec CTA:** large brand + simple instruction, added in editor for legibility.
- Make the edit work **with sound off**; deliver an alternate VO/audio plan if needed.
- Keep each cut sufficiently long to understand a single action; each additional action or scene is a trade-off.

## Scene QR-specific truthfulness
- Product concept: customers scan a QR code at a business, send a contextual request, and staff can see/respond/fulfill that request. Only claim features verified in the actual build.
- Automotive: scan QR by service desk; request a quote -> service adviser sees request.
- Restaurant: scan tabletop QR; request help -> server sees table/request and responds.
- Retail: scan QR near item; ask a product question -> associate gets request and helps.
- A static example screen may be composited in post. Do not invent an automated action the product cannot actually perform or imply autonomous fulfillment without proof.

## Limited-credit generation preflight — PASS ALL
- [ ] Buyer knows what product does in <=5 seconds.
- [ ] Customer and staff actions are visible, not just phones, lights and transitions.
- [ ] Single clear CTA and correct public URL.
- [ ] Timings add up to requested duration.
- [ ] References prepared; product/device screens can be composited.
- [ ] Across-cut characters/locations are consistent by design.
- [ ] Avoid text-heavy generations; editorial overlays are planned.
- [ ] Suitable 9:16 composition with top/bottom safe areas for platform UI.
- [ ] Music/VO and sound-off captions have a plan.
- [ ] Verify user's model/trial cost and ask before burning a limited or billable generation.

## Quality review after render
Score 1–5 each: first-two-second hook; product clarity; natural hands/phones; continuity; genuine UI/action; sound-off comprehension; CTA legibility; 9:16 framing; brand recall; buyer desire. Record concrete broken seconds and the cheapest way to correct (edit/overlay/crop versus regeneration). Only iterate after reviewing this evidence and any usage cost.

## Delivery format
Provide (a) concept + promise, (b) timecoded shot list, (c) exact short render prompt(s) tailored to the selected model, (d) needed source assets, (e) edit/overlay and audio plan, (f) realistic limitations and cost preflight. For a one-shot request, prefer ONE winning concept over a menu of variants.
