# ClauseCam showcase film

`../clausecam-showcase.mp4`: 91.9 s, 1280×800, H.264, no sound. It's a pitch cut, built
2026-09-23 against the deployed build.

**What's real.** Every shot is a screen recording of the deployed app, and nothing is redrawn.
The one frame that isn't footage is the three-second hook: type on the ink ground, with no UI.
Each line states only what its shot shows. The one edit inside a take, the 57 s OCR wait, is
tagged on screen.

**Style.** Hard cuts between shots, a slow push toward a focus point in every shot, and short
lines that slide in with each cut. The only fades are at the open and the close.

| Start | Beat | Line | Footage |
|---:|---|---|---|
| 0.0 | Hook | Same rule. Different answer. | type only |
| 3.0 | Problem | One officer. One inspection queue. | capture: the queue |
| 8.0 | Problem | Every row, a pack to check. | capture: the queue, scrolling |
| 13.0 | Problem | Dozens of clauses on every label. | walkthrough: the findings ledger |
| 18.0 | Turn | First question: which rules apply? | capture: Rule 6(1)(a), category unconfirmed |
| 22.0 | Turn | Category unknown. It won't guess. | capture: the same row's reason |
| 26.0 | Turn | An officer confirms: food. | capture: category classification |
| 32.5 | Turn | Same rule. Now: not applicable. | capture: Rule 6(1)(a) on the food scan |
| 37.0 | Turn | It cites the law that governs. | capture: its FSS Act reason |
| 41.0 | Proof | A real pack. The live app. | walkthrough: the MDH carton marked |
| 46.0 | Proof | Rule 7(2), Table-I. Measured: 2.61 mm. | walkthrough: measurements (tagged "57 s of OCR cut") |
| 51.5 | Proof | Too close to call. It says so. | walkthrough: the Table-I REVIEW reason |
| 58.5 | Proof | An officer decides. Not the machine. | walkthrough: the determination, REVIEW RECORDED |
| 64.0 | Proof | Report out. SHA-256 on the chain. | walkthrough: the evidence report |
| 71.0 | Proof | See where violations cluster. | walkthrough: the ward map |
| 76.0 | Proof | See which clauses break. | walkthrough: the clause breakdown |
| 81.0 | Close | Applicability first. Clause cited. Officer decides. | walkthrough: the opening, holding on the wordmark |

**Why this hook.** A line like "Same size. Different law." would describe the 8 g
shampoo/pan masala contrast. The app can't show that until #200 encodes Rule 26(a) and
G.S.R. 881(E). "Same rule. Different answer." is what the turn does show: Rule 6(1)(a) stays
undecided while the category is unknown, then reads NOT APPLICABLE for food. Change `HOOK`
once #200 ships.

The videos are not committed. `capture.webm` and the film stay local, and
`demo/clausecam-walkthrough.webm` is gitignored.

## Rebuilding

**1. Fonts.** ffmpeg's `drawtext` reads TrueType, not woff2. Convert once, from the repository
root. `fonttools` and `brotli` run in a throwaway environment, so no dependency is added to the
project. Bricolage Grotesque ships as a variable font, so pin its weight to 700:

```sh
mkdir -p ~/.cache/clausecam-fonts
uv run --no-project --with fonttools --with brotli python -c "
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
out = Path.home() / '.cache/clausecam-fonts'
bold = instancer.instantiateVariableFont(
    TTFont('fnt/public/fonts/BricolageGrotesque-Variable.woff2'), {'wght': 700})
bold.flavor = None; bold.save(out / 'BricolageGrotesque-Bold.ttf')
mono = TTFont('fnt/public/fonts/IBMPlexMono-Medium.woff2')
mono.flavor = None; mono.save(out / 'IBMPlexMono-Medium.ttf')
"
```

**2. Footage.**
- `demo/clausecam-walkthrough.webm` comes from `demo/record-clausecam.cjs`; its index is
  `demo/clausecam-walkthrough-index.md`.
- `capture.webm` comes from `capture.cjs`, which signs in as `demo-officer` and only reads:
  `NODE_PATH=$(npm root -g) node brag-output/clausecam-showcase/capture.cjs`. It writes
  `cuts.json` with the video-relative time of each shot.

The `start` times in `build.py`'s `SHOTS` were read from the 2026-09-23 recordings. A fresh
recording moves them, so re-read `cuts.json` and the walkthrough index first. The `focus`
points were chosen by looking at frames, so check them too.

**3. Build.**

```sh
python3 brag-output/clausecam-showcase/build.py ~/.cache/clausecam-fonts
```

This writes `brag-output/clausecam-showcase.mp4` and prints the beat list with start times.
