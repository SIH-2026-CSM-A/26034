# Brag Plan: PCCS — Packaged Commodity Compliance System

## What is this app?
Compliance decision support for packaged commodities under the Legal Metrology (Packaged
Commodities) Rules, 2011: a shopper or vendor photographs a label, the system reads it, cites
the rule behind every finding, refuses what the photograph cannot establish, and a Legal
Metrology officer confirms before any enforcement act. This video is a launch film built from
the product's own copy and screens. It is not a screen recording and never claims to be one.

## The angle
A compliance tool whose most impressive moment is a refusal. Every other label reader would
print a verdict; PCCS prints, verbatim, "which side of the requirement this package falls on
is not established at the measurement's own precision." The film builds to that sentence.

## Hook (first 3.7 seconds)
Paper canvas. One display line, large: "Officers cannot inspect every package by hand." A
faint scrolling column of review-queue rows behind it, the ledger nobody can finish. The
rules citation under it in mono: "Legal Metrology (Packaged Commodities) Rules, 2011".

## Key moments (the middle)
- A phone frame with the real `/consumer` capture screen: the photo tile, the "Barcode" line,
  and the "Check this label" button, tapped.
- Three findings rows arriving one by one, each with its clause reference and a state chip
  taken from the product's chip system (tick = PASS, hollow ring = INSUFFICIENT EVIDENCE),
  with the product's own sentence "Could not be read from this photograph. That is not a
  finding that it is absent."
- The Table-I ledger row: REVIEW REQUIRED, Measured 2.61 mm, Required 1.5 mm to 2.5 mm, the
  two named uncertainties, and the closing clause held long enough to read twice.

## Outro / punchline
An officer's disposition panel: "Confirm and re-evaluate". Then the real GHMC ward map draws
in, two wards lit, and the wordmark: PCCS. "It recommends. An officer confirms."

## User flow worth showing
Photograph a label → findings with rules and refusals → officer confirms → ward map. The
centrepiece is the findings-to-refusal run, screens 3 and 4.

## Tone
- Preset: polished
- Creative direction: a quiet compliance film; the product speaks in its own sentences
- Interpretation: long holds, soft crossfades, nothing shouted; the only emphasis is time
  spent on the refusal sentence

## Format: landscape — 1920x1080
## Duration: 25 s

## Visual identity (from the project)
- Background: rgb(243 244 241) (`--c-paper`), surface rgb(255 255 255)
- Text: rgb(14 22 32) (`--c-ink`), muted rgb(74 85 96)
- Accent: rgb(35 72 155) (`--c-accent`); attest green rgb(20 96 60); query amber
  rgb(125 80 4); seal red rgb(163 42 30); choropleth ramp 246 236 204 → 232 170 52 →
  176 52 32 → 98 22 14
- Display font: Bricolage Grotesque (variable, shipped in `fnt/public/fonts`)
- Body font: IBM Plex Sans; data in IBM Plex Mono
- Strongest visual element: the ledger row with the state chip, and the GHMC ward map
  (145 real ward boundaries from `fnt/src/officer/dashboard/ghmcWards.ts`)

## Hard limits on generated content
- Verdict words are PASS, REVIEW and POTENTIAL VIOLATION only. Field states shown are PASS,
  REVIEW REQUIRED and INSUFFICIENT EVIDENCE. The word "fail" does not appear.
- No accuracy, false-positive, tamper or throughput figure. No count of anything.
- The system recommends; a person confirms. No line says the system decides compliance.
- Every measured value on screen is from the recorded scan of the MDH carton
  (2.61 ± 0.13 mm, 102.3 ± 10.2 cm², 1.5 mm to 2.5 mm) or the Parle-G packet (56 g,
  Rs 10.00). Map shading marks only the two wards the demo recording hovers.

## Share copy (draft)
Introducing PCCS: photograph a label, get every finding with the rule behind it, and a
refusal where the photograph cannot establish the answer. An officer confirms before
anything is enforced.

## Audio direction
- Role: warm bed, sparse professional accents
- Music: `happy-beats-business-moves-vol-11-by-ende-dot-app.mp3` (114.84 BPM)
- Music treatment: starts at 0 under a 0.8 s fade-in at 0.55, ducks to 0.35 under the
  refusal scene so the hold feels deliberate, returns, fades out over the last 1.5 s
- Music cue guidance: bundled preset read (`brag-output/…music-cues.json`). Strong cues at
  1.60, 3.70, 5.80, 8.96, 12.65, 17.91, 22.65 s. Scene edges sit on 3.70, 8.96, 22.65;
  the refusal sentence lands on 17.91. Findings rows use the beat grid at 9.50, 10.54,
  11.60 (every other beat, held afterwards).
- Audio-reactive treatment: subtle; bass drives a 2–4 % breathe on the paper glow behind the
  hero elements and on the map's lit wards. No waveform, no equaliser.
- SFX posture: sparse. One soft impact on the hook line, one click on the tap, three low-risk
  card slides on the findings rows, one soft impact when the refusal chip lands, one bong on
  the wordmark.
- Restraint rule: no sound on the refusal sentence itself; it arrives in silence over the
  ducked bed.

## Storyboard

### Scene 1 — Hook — 0.00–3.70 s
Paper canvas with a faint queue ledger drifting upward behind. Display line "Officers cannot
inspect every package by hand." slams in on 1.60 and holds. Mono subline with the Rules' name.
Sequential/interaction: none
Audio intent: quiet start, one soft impact on the line
Audio-coupled idea: hook line lands on the 1.60 strong cue
Music: bed fades in
Transition mood: soft crossfade → Scene 2

### Scene 2 — Photograph the label — 3.70–8.96 s
Left: display line "A shopper or a vendor photographs a label." Right: a phone frame showing
the `/consumer` capture screen — label photo tile, "Barcode" line reading what the browser
read, the "Check this label" button. A cursor-less tap ripple on the button at 7.0 s and the
button state reads "Sending…".
Sequential/interaction: yes — simulated tap on "Check this label"
Audio intent: a single click on the tap
Audio-coupled idea: tap at 7.02 (beat)
Transition mood: soft crossfade → Scene 3

### Scene 3 — Every finding names its rule — 8.96–14.50 s
Display line "It reads the label and cites the rule behind every finding." Under it three
ledger rows arrive one by one (9.50, 10.54, 11.60) and hold: the net quantity row (PASS, tick,
Rule 6(1)(d), "56 g"), the MRP row (PASS, tick, "Rs 10.00"), and one INSUFFICIENT EVIDENCE row
(hollow ring) with "Could not be read from this photograph. That is not a finding that it is
absent." Rows are verbatim from the recorded Parle-G scan.
Sequential/interaction: yes — three rows, one per every-other beat, then a 2.9 s hold
Audio intent: three low-risk card slides
Audio-coupled idea: beat-grid rows
Transition mood: soft crossfade → Scene 4

### Scene 4 — The refusal — 14.50–20.50 s
The Table-I ledger row at full width. Label "Net quantity, letter height", chip REVIEW
REQUIRED (amber query), Measured 2.61 mm, Required 1.5 mm to 2.5 mm, Rule 7(2), Table-I. Two
mono lines name the uncertainties: "panel area 102.3 ± 10.2 cm² · across a Table-I band
edge" and "character height 2.61 ± 0.13 mm · across the 2.5 mm requirement". Then, on
17.91, the closing clause in display type, verbatim: "which side of the requirement this
package falls on is not established at the measurement's own precision." Held to the end of
the scene.
Sequential/interaction: yes — chip, pairs, two uncertainty lines, then the sentence
Audio intent: bed ducks; one soft impact on the chip; silence on the sentence
Audio-coupled idea: sentence beat-locked to 17.91
Transition mood: soft crossfade → Scene 5

### Scene 5 — An officer confirms — 20.50–22.65 s
Display line "An officer confirms before any enforcement act." beside the disposition panel:
the category select reading FOOD and the "Confirm and re-evaluate" button.
Sequential/interaction: none
Audio intent: bed returns
Transition mood: soft crossfade → Scene 6

### Scene 6 — The ward map — 22.65–25.00 s
The 145 GHMC ward boundaries draw in as hairlines on paper; Ward 121 Kukatpally and Ward 91
Khairatabad fill with the heat ramp and breathe with the bass. Wordmark "PCCS" with
"Packaged Commodity Compliance System" and the closing line "It recommends. An officer
confirms." Music fades.
Sequential/interaction: yes — outline, then the two wards, then the wordmark
Audio intent: one bong on the wordmark, bed out
Transition mood: hold to black-free end (paper stays)

**Music mood for this video:** warm, unhurried
**Audio summary:** a bed that fades in under the hook, ducks for the refusal sentence, and
leaves on the wordmark; six sounds in total.
