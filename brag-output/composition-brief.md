# Hyperframes Composition Brief: PCCS

## Objective
Create a short launch-style film for PCCS, the Packaged Commodity Compliance System. Built
from the product's copy, tokens, fonts, chip system and ward geometry. Not a screen
recording; it must not claim to be one.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 25 s

## Source Material
- Project root: `/home/abhi/26034-demo`
- Primary files read: `fnt/src/index.css` (tokens, fonts), `fnt/src/consumer/plainLanguage.ts`
  (field labels, state and verdict sentences), `fnt/src/officer/components/FieldStateChip.tsx`
  (tick / ring chip semantics), `fnt/src/officer/VerdictDetail.tsx` (ledger row layout),
  `fnt/src/officer/dashboard/ghmcWards.ts` (145 ward paths), `bck/app/pipeline/
  measurement_findings.py` (the Table-I reason), `demo/pccs-demo-*-index.md` (recorded values).
- Product name: PCCS — Packaged Commodity Compliance System
- Tagline / strongest claim: "which side of the requirement this package falls on is not
  established at the measurement's own precision."
- Key UI to recreate: the verdict ledger row (label, state chip, Measured / Required pair,
  Rule, reason) and the GHMC choropleth.
- Copy that must appear verbatim:
  - Officers cannot inspect every package by hand.
  - Legal Metrology (Packaged Commodities) Rules, 2011
  - Check this label
  - Found on the label.
  - Could not be read from this photograph. That is not a finding that it is absent.
  - Net quantity, letter height · REVIEW REQUIRED · Measured 2.61 mm · Required 1.5 mm to 2.5 mm · Rule 7(2), Table-I
  - which side of the requirement this package falls on is not established at the measurement's own precision.
  - Confirm and re-evaluate
  - Ward 121 Kukatpally · Ward 91 Khairatabad

## Creative Direction
- Tone preset: polished
- Creative direction: a quiet compliance film; the product speaks in its own sentences
- Interpretation: long holds, soft crossfades, restrained motion; the refusal sentence gets
  the longest hold in the film
- Angle: the most impressive moment is a refusal — two named uncertainties and a system that
  will not print a verdict it cannot support
- Hook: "Officers cannot inspect every package by hand." over a drifting queue ledger
- Outro / punchline: the real ward map, then "It recommends. An officer confirms."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Any verdict word other than PASS, REVIEW, POTENTIAL VIOLATION; any field state other than
    PASS, REVIEW REQUIRED, INSUFFICIENT EVIDENCE; the word "fail"
  - Any statistic, rate, count or accuracy figure; any claim that the system decides

## Visual Identity
- Background: rgb(243 244 241) paper; rgb(255 255 255) surface
- Text: rgb(14 22 32) ink; rgb(74 85 96) mute
- Accent: rgb(35 72 155); attest rgb(20 96 60); query rgb(125 80 4); seal rgb(163 42 30)
- Display font: Bricolage Grotesque (shipped, `assets/fonts/BricolageGrotesque-Variable.woff2`)
- Body font: IBM Plex Sans; data: IBM Plex Mono (shipped)
- Visual references: ledger row, FieldStateChip glyphs, choropleth heat ramp, `.card` surfaces

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook — 0.00–3.70 — the line, the Rules citation, the drifting ledger
2. Photograph the label — 3.70–8.96 — phone frame, capture screen, tap
3. Every finding names its rule — 8.96–14.50 — three rows on beats, held
4. The refusal — 14.50–20.50 — Table-I row; closing clause locked to 17.91, held
5. An officer confirms — 20.50–22.65 — disposition panel
6. The ward map — 22.65–25.00 — 145 wards draw, two lit, wordmark

## Audio
- Audio role: warm bed, sparse professional accents
- Audio arc: fade in under the hook; duck under the refusal; return; out on the wordmark
- Music: `assets/music/happy-beats-business-moves-vol-11-by-ende-dot-app.mp3`
- Music treatment: baseline 0.55; volume lane fade-in 0–0.8 s, duck to 0.3 from 14.5 to
  20.5, fade-out 23.5–25
- Music cue guidance: preset `brag-output/happy-beats-business-moves-vol-11-by-ende-dot-app.music-cues.json`;
  strong cues 1.60, 3.70, 5.80, 8.96, 12.65, 17.91, 22.65; beat grid 9.50, 10.54, 11.60
- Audio-reactive treatment: subtle; bass band → 2–4 % breathe on the paper glow and the lit
  wards, from `assets/audio-data.js` (pre-extracted, 30 fps, 16 bands)
- Audio-coupled moments:
  - hook line — strong cue 1.60, soft impact
  - tap — beat 7.02, click
  - rows — beat grid, card slides
  - refusal chip — soft impact at 14.9; sentence at 17.91 in silence over the ducked bed
  - wordmark — 23.2, bong
- SFX selection guidance: low high-frequency-risk files only, see the brag sfx-analysis
- Exact SFX choice: `impact/impactSoft_medium_001.ogg`, `impact/impactSoft_medium_004.ogg`,
  `interface/click_003.ogg`, `casino/card-slide-1.ogg`, `interface/bong_001.ogg`, copied to
  `assets/sfx/`
- Audio files: in `brag-output/composition/assets/`

## Hyperframes Instructions
Domain skills loaded: hyperframes-core, hyperframes-animation, hyperframes-creative,
hyperframes-keyframes, hyperframes-cli. Standalone root, one paused GSAP timeline, no
network, no clocks, no randomness, fonts by in-file `@font-face` to shipped files, audio on
`<audio id>` elements with volume lanes, `npx hyperframes check` as the gate before render.
