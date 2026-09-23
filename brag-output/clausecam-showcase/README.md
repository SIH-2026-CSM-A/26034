# ClauseCam showcase film

`../clausecam-showcase.mp4`: 88.5 s, 1280×800, H.264 + AAC stereo. Built 2026-09-23 with the
brag pipeline (a Hyperframes composition, Kokoro voice, a music bed and sound design) against
the deployed build.

**What's real, and what isn't:**
- Every screen is a recording of the deployed app. Nothing in the UI is redrawn.
- On top of the footage there's only type and graphics: titles, chips, a spotlight, and
  highlight boxes and underlines drawn at the exact source-pixel positions of the UI they
  point to.
- The hook and the question are type on the ink ground.
- The one edit inside a take, the OCR wait, is tagged on screen ("57 s of OCR cut").
- The voice is synthetic, and the end card says so.

## Voiceover script

`voiceover.txt`, 161 words. Each line is its own clip, and the edit is cut to the voice.

> Same rule. Different answer.
> Every packed product sold in India must print certain facts on its label: who made it, how
> much is inside, and the price. One inspector can't check a whole shelf by hand. And every
> label is tested against dozens of legal rules.
> So ClauseCam starts with the question most tools skip. Which rules apply to this pack at all?
> Until an officer confirms what the product is, it won't guess. Confirmed as food, the same
> rule steps aside. For food, that duty sits under a different law, and ClauseCam names it.
> This is a real scan, on the live app. It measures the print on the pack against the exact
> clause. When the measurement is too close to call, it says so, instead of guessing. An
> officer makes the decision. Then the report goes out, with a digital fingerprint written
> into the scan's evidence trail.
> ClauseCam. The right rules. The exact clause. And a person who decides.

The hook stays "Same rule. Different answer." until #200 encodes Rule 26(a) and G.S.R. 881(E).
The 8 g shampoo/pan masala contrast can't be shown before then.

## Beats

| Time | Beat | On screen |
|---:|---|---|
| 0.0 | Hook | "Same rule. Different answer." builds; an amber bar draws |
| 4.0 | Problem | Queue; "Who made it", "How much is inside", "The price" pop in on the beat |
| 12.3 | Problem | Queue scrolling: "One inspector. A whole shelf." |
| 15.8 | Problem | "across 46 rules" boxed on a verdict page |
| 20.2 | Turn | Type card: "Which rules apply?" |
| 26.0 | Turn | Rule 6(1)(a) INSUFFICIENT EVIDENCE boxed; "category has not been confirmed" underlined |
| 30.6 | Turn | FOOD · OFFICER CONFIRMED boxed |
| 32.2 | Turn | The same row NOT APPLICABLE; "Food Safety and Standards Act, 2006" and "R6-1-A-EXPL-III-FOOD" underlined |
| 38.4 | Proof | The MDH carton marked on the live app ("LIVE · deployed app") |
| 42.2 | Proof | Rule 7(2), Table-I: 2.61 mm against 1.5 to 2.5 mm, boxed ("57 s of OCR cut") |
| 47.2 | Proof | The too-close-to-call reason, spotlit |
| 53.0 | Proof | Confirm, then REVIEW RECORDED · CONFIRM · Finalised, boxed |
| 58.4 | Proof | The report's SHA-256 boxed, "SHA-256 · written to the evidence chain" |
| 66.0 | Proof | Ward map, music up |
| 70.5 | Proof | Clause breakdown |
| 74.2 | Close | The opening; the wordmark lands on a strong beat (78.56 s) |
| 80.9 | Close | "The right rules." "The exact clause." "A person who decides." Credits, fade |

## Audio

- **Voice:** Kokoro `af_heart` through `hyperframes tts`, one clip per line, loudness-normalised to −16 LUFS.
- **Music:** "Happy Beats & Business Moves Vol. 12" by Sascha Ende (ende.app), **CC BY 4.0**.
  It's royalty-free and needs attribution, which is on the end card. The bed is ducked under
  the voice with a volume lane and comes up for the wordless map beat and the close.
- **Sound effects:** Kenney, CC0, bundled with the brag plugin. There are eight: an impact on
  the hook, drops on the chips, the SHA-256 and the question, a click on the submit, and a bell
  on the wordmark.
- The three chips and the wordmark are locked to strong beats of the bed. Everything else is
  paced to the voice.

## Rebuilding

```sh
# 1. A throwaway Python for Kokoro, outside the repo; no project dependency is added.
TMPDIR=~/.cache/tmp-uv uv venv --python 3.11 ~/.cache/hf-tts
TMPDIR=~/.cache/tmp-uv uv pip install --python ~/.cache/hf-tts/bin/python kokoro-onnx soundfile

# 2. Assets: cut the shots from the footage, synthesise the voice, copy fonts, music and effects.
HYPERFRAMES_PYTHON=~/.cache/hf-tts/bin/python \
BRAG_ASSETS=<brag plugin>/skills/brag/assets \
  bash brag-output/clausecam-showcase/prepare.sh

# 3. The composition, generated from one table of shots, voice cues, titles and highlights.
python3 brag-output/clausecam-showcase/compose.py

# 4. Check, render, then bake the settled hook frame as frame 0 so thumbnails show it.
cd brag-output/clausecam-showcase/composition
npx hyperframes@0.8.50 check
npx hyperframes@0.8.50 render --quality high --output ../../clausecam-showcase.mp4
```

For step 4's poster, follow the brag skill's delivery step: pull the frame at 3.2 s and
overlay it on frame 0.

**Footage.**
- `demo/clausecam-walkthrough.webm` comes from `demo/record-clausecam.cjs`.
- `capture.webm` comes from `capture.cjs`, which signs in as `demo-officer` and only reads. It
  writes `cuts.json` with the time of each shot.

`prepare.sh` holds the source offsets and `compose.py` holds the film times and highlight
positions. All of them were read from the 2026-09-23 recordings, so a fresh recording means
re-reading them.

`composition/assets/`, the rendered film and `poster.jpg` are not committed.
