# ClauseCam showcase film

`../clausecam-showcase.mp4`: 90.8 s, 1280×800, H.264, built 2026-09-23 against the deployed
build at `dddd631`. Every frame is a screen recording of the deployed app. Nothing is redrawn,
and each caption states only what its footage shows. The one edit inside a take, the OCR wait,
is named in its caption.

| Time | Beat | Source |
|---|---|---|
| 0:00–0:12 | The problem: the review queue | `capture.webm` |
| 0:12–0:35 | The idea: Rule 6(1)(a) left undecided until the category is confirmed, then NOT APPLICABLE for food under the FSS Act, 2006 | `capture.webm` |
| 0:35–1:20 | The proof: a marked MDH scan, the Table-I finding and its clause, REVIEW at the band edge, the officer's CONFIRM, the report and its SHA-256 | `demo/clausecam-walkthrough.webm` |
| 1:20–1:31 | The opening, holding on the ClauseCam wordmark | `demo/clausecam-walkthrough.webm` |

The videos are not committed. `capture.webm` and the film stay local, and
`demo/clausecam-walkthrough.webm` is gitignored.

## Rebuilding

**1. Fonts.** The captions use IBM Plex Sans from `fnt/public/fonts`. ffmpeg's `drawtext` reads
TrueType, not woff2, so convert the two weights once. `fonttools` and `brotli` run in a throwaway
environment, so no dependency is added to the project:

```sh
mkdir -p ~/.cache/clausecam-fonts
uv run --no-project --with fonttools --with brotli python -c "
from pathlib import Path
from fontTools.ttLib import TTFont
out = Path.home() / '.cache/clausecam-fonts'
for n in ('IBMPlexSans-SemiBold', 'IBMPlexSans-Medium'):
    f = TTFont(f'fnt/public/fonts/{n}.woff2'); f.flavor = None; f.save(out / f'{n}.ttf')
"
```

Run it from the repository root. The output differs from an earlier conversion only in the
`head` table's modification timestamp; the glyphs and metrics are identical.

**2. Footage.**
- `demo/clausecam-walkthrough.webm` comes from `demo/record-clausecam.cjs`; its index is
  `demo/clausecam-walkthrough-index.md`.
- `capture.webm` comes from `capture.cjs`, which signs in as `demo-officer` and only reads:
  `NODE_PATH=$(npm root -g) node brag-output/clausecam-showcase/capture.cjs`. It writes
  `cuts.json` with the video-relative time of each shot.

The segment times in `build.py` were read from the 2026-09-23 recordings: `cuts.json` for
beats 1 and 2, and the walkthrough index for beat 3 and the ending. A fresh recording moves
them, so update `SEGMENTS` from the new `cuts.json` and index before building.

**3. Build.**

```sh
python3 brag-output/clausecam-showcase/build.py ~/.cache/clausecam-fonts
```

The output is written to `brag-output/clausecam-showcase.mp4`.
