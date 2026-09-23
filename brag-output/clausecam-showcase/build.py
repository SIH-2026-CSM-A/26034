"""Cut the ClauseCam showcase from real screen recordings of the deployed app.

Every frame is footage: capture.webm (beats 1 and 2, recorded by capture.cjs as demo-officer,
read-only) and demo/clausecam-walkthrough.webm (beat 3 and the closing wordmark). Captions
state only what the footage on screen shows. The one edit inside a take, the OCR wait, is
said in its caption.

    python3 build.py <fonts dir>    # IBMPlexSans-SemiBold.ttf, IBMPlexSans-Medium.ttf
"""

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAPTURE = HERE / "capture.webm"
WALK = REPO / "demo" / "clausecam-walkthrough.webm"
OUT = HERE.parent / "clausecam-showcase.mp4"
FONTS = Path(sys.argv[1])
BIG = FONTS / "IBMPlexSans-SemiBold.ttf"
SMALL = FONTS / "IBMPlexSans-Medium.ttf"

# (source, start s, duration s, headline, subline). A headline ending in "^" is set at the top of
# the frame instead, where the footage has what it describes at the bottom.
SEGMENTS = [
    (
        CAPTURE,
        3.6,
        12.0,
        "A shelf of packed goods. One officer.",
        "Every row is a recommendation pending officer confirmation.",
    ),
    (
        CAPTURE,
        18.6,
        8.0,
        "Before it checks anything, ClauseCam works out which rules apply.",
        "Category not yet confirmed: Rule 6(1)(a) is left undecided, and it says why.",
    ),
    (CAPTURE, 28.7, 6.5, "An officer confirms the category: food.", None),
    (
        CAPTURE,
        36.7,
        8.5,
        "Then it names the rule.",
        "For food packs, Rule 6(1)(a) gives way to the FSS Act, 2006, per R6-1-A-EXPL-III-FOOD.",
    ),
    (
        WALK,
        30.0,
        8.0,
        "The proof: a real scan on the live app.",
        "An MDH Kitchen King carton, a ten-rupee coin for scale, the display panel marked.",
    ),
    (
        WALK,
        94.5,
        8.5,
        "Each finding cites its clause.",
        "Real OCR took 57 s; the wait is cut. Rule 7(2), Table-I: 2.61 mm measured, 1.5 to 2.5 mm required.",
    ),
    (
        WALK,
        166.5,
        10.0,
        "Too close to call at its own precision, so it says REVIEW.",
        "Both uncertainties are named. No verdict is claimed that the measurement cannot support.",
    ),
    (
        WALK,
        238.5,
        8.5,
        "The officer confirms.^",
        "The determination is recorded and the scan is finalised.",
    ),
    (
        WALK,
        253.5,
        10.0,
        "The report goes out.",
        "Its SHA-256 is appended to the scan's evidence chain as the export record.",
    ),
    (WALK, 1.0, 8.0, None, None),  # the opening, ending on the ClauseCam wordmark
]
END_HOLD = 3.0
FADE = 0.35


def caption_filters(headline, subline, dur, tmp: Path, i: int) -> list[str]:
    if not headline:
        return []
    filters = []
    top = headline.endswith("^")
    headline = headline.rstrip("^")
    lines = [(headline, BIG, 34, "90" if top else ("h-150" if subline else "h-120"))]
    if subline:
        lines.append((subline, SMALL, 22, "144" if top else "h-96"))
    for k, (text, font, size, y) in enumerate(lines):
        tf = tmp / f"cap{i}_{k}.txt"
        tf.write_text(text, encoding="utf-8")
        filters.append(
            f"drawtext=fontfile={font}:textfile={tf}:expansion=none:fontsize={size}"
            f":fontcolor=0xF3F4F1:x=(w-text_w)/2:y={y}"
            f":box=1:boxcolor=0x0E1620@0.88:boxborderw=14"
            f":enable='between(t,0.25,{dur - 0.2})'"
        )
    return filters


def main() -> None:
    with tempfile.TemporaryDirectory(dir=HERE) as tmpname:
        tmp = Path(tmpname)
        parts = []
        for i, (src, start, dur, headline, subline) in enumerate(SEGMENTS):
            last = i == len(SEGMENTS) - 1
            vf = ["fps=30", "scale=1280:800", "setsar=1"]
            vf += caption_filters(headline, subline, dur, tmp, i)
            if last:
                vf.append(f"tpad=stop_mode=clone:stop_duration={END_HOLD}")
            total = dur + (END_HOLD if last else 0)
            vf.append(f"fade=t=in:st=0:d={FADE}")
            if not last:  # the film ends on the wordmark, not on black
                vf.append(f"fade=t=out:st={total - FADE}:d={FADE}")
            part = tmp / f"part{i:02d}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    str(start),
                    "-t",
                    str(dur),
                    "-i",
                    str(src),
                    "-vf",
                    ",".join(vf),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    str(part),
                ],
                check=True,
            )
            parts.append(part)
        listing = tmp / "parts.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(OUT),
            ],
            check=True,
        )
    print(OUT)


if __name__ == "__main__":
    main()
