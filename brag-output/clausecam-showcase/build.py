"""Cut the ClauseCam showcase pitch from real screen recordings of the deployed app.

Every shot is footage: capture.webm (recorded by capture.cjs as demo-officer, read-only) and
demo/clausecam-walkthrough.webm. Nothing is redrawn. The one frame that is not footage is the
opening hook, which is type on the ink ground and shows no UI. Each line states only what its
shot shows, and an edit inside a take (the OCR wait) is named on screen.

Shape: hook, then problem, then the turn (applicability decides), then proof, then the close
on the wordmark. Hard cuts between shots, a slow push toward a focus point in each shot, and
fades only at the open and the close.

    python3 build.py <fonts dir>    # BricolageGrotesque-Bold.ttf, IBMPlexMono-Medium.ttf
"""

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAPTURE = HERE / "capture.webm"
WALK = REPO / "demo" / "clausecam-walkthrough.webm"
OUT = HERE.parent / "clausecam-showcase.mp4"
FONTS = Path(sys.argv[1])
DISPLAY = FONTS / "BricolageGrotesque-Bold.ttf"
MONO = FONTS / "IBMPlexMono-Medium.ttf"

W, H, FPS = 1280, 800, 30
INK, PAPER = "0x0E1620", "0xF3F4F1"
HOOK = ("Same rule.", "Different answer.")
HOOK_SECONDS = 3.0
OPEN_FADE, CLOSE_FADE = 0.4, 0.8


@dataclass(frozen=True)
class Shot:
    beat: str
    src: Path
    start: float
    dur: float
    line: str
    focus: tuple[float, float]  # where the push-in heads, as fractions of the frame
    push: float = 0.07  # zoom gained over the shot
    top: bool = (
        False  # set the line at the top where the shot's subject is at the bottom
    )
    note: str | None = None  # an edit inside the take, named on screen
    line_at: float = 0.06  # when the line enters
    hold: float = 0.0  # seconds the last frame is held (the close)


SHOTS = [
    # Problem
    Shot(
        "problem", CAPTURE, 3.6, 5.0, "One officer. One inspection queue.", (0.3, 0.25)
    ),
    Shot("problem", CAPTURE, 9.0, 5.0, "Every row, a pack to check.", (0.5, 0.5)),
    Shot("problem", WALK, 116.0, 5.0, "Dozens of clauses on every label.", (0.3, 0.5)),
    # The turn: applicability decides
    Shot("turn", CAPTURE, 18.6, 4.0, "First question: which rules apply?", (0.3, 0.45)),
    Shot(
        "turn",
        CAPTURE,
        22.6,
        4.0,
        "Category unknown. It won't guess.",
        (0.3, 0.52),
        push=0.12,
    ),
    Shot("turn", CAPTURE, 28.7, 6.5, "An officer confirms: food.", (0.2, 0.45)),
    Shot("turn", CAPTURE, 36.7, 4.5, "Same rule. Now: not applicable.", (0.3, 0.47)),
    Shot(
        "turn",
        CAPTURE,
        41.2,
        4.0,
        "It cites the law that governs.",
        (0.3, 0.52),
        push=0.12,
    ),
    # Proof
    Shot("proof", WALK, 31.0, 5.0, "A real pack. The live app.", (0.25, 0.35)),
    Shot(
        "proof",
        WALK,
        94.5,
        5.5,
        "Rule 7(2), Table-I. Measured: 2.61 mm.",
        (0.35, 0.2),
        note="57 s of OCR cut",
    ),
    Shot("proof", WALK, 166.5, 7.0, "Too close to call. It says so.", (0.3, 0.12)),
    Shot(
        "proof",
        WALK,
        239.5,
        5.5,
        "An officer decides. Not the machine.",
        (0.5, 0.6),
        top=True,
    ),
    Shot("proof", WALK, 253.5, 7.0, "Report out. SHA-256 on the chain.", (0.22, 0.62)),
    Shot("proof", WALK, 276.0, 5.0, "See where violations cluster.", (0.2, 0.4)),
    Shot("proof", WALK, 287.0, 5.0, "See which clauses break.", (0.82, 0.45)),
    # Close: the opening, ending on the wordmark
    Shot(
        "close",
        WALK,
        1.0,
        7.0,
        "Applicability first. Clause cited. Officer decides.",
        (0.5, 0.45),
        push=0.03,
        top=True,
        line_at=6.6,
        hold=4.0,
    ),
]


def text(tmp: Path, name: str, value: str) -> Path:
    path = tmp / f"{name}.txt"
    path.write_text(value, encoding="utf-8")
    return path


def kinetic(
    textfile: Path, size: int, x: str, y: str, at: float, box: bool = True
) -> str:
    """A line that slides up 36 px and fades in over 0.2 s, entering at ``at``."""
    rise = f"36*max(0\\,1-(t-{at})/0.2)"
    return (
        f"drawtext=fontfile={DISPLAY}:textfile={textfile}:expansion=none:fontsize={size}"
        f":fontcolor={PAPER}:x={x}:y={y}+{rise}"
        + (f":box=1:boxcolor={INK}@0.94:boxborderw=20" if box else "")
        + f":alpha='min(1\\,max(0\\,(t-{at})/0.16))':enable='gte(t\\,{at})'"
    )


def encode(args: list[str], out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            *args,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(out),
        ],
        check=True,
    )


def hook(tmp: Path) -> Path:
    first, second = (text(tmp, f"hook{i}", s) for i, s in enumerate(HOOK))
    vf = ",".join(
        [
            kinetic(first, 88, "(w-text_w)/2", "h/2-110", 0.15, box=False),
            kinetic(second, 88, "(w-text_w)/2", "h/2+10", 1.0, box=False),
            f"fade=t=in:st=0:d={OPEN_FADE}",
        ]
    )
    out = tmp / "part00.mp4"
    encode(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c={INK}:s={W}x{H}:r={FPS}:d={HOOK_SECONDS}",
            "-vf",
            vf,
        ],
        out,
    )
    return out


def shot_part(tmp: Path, i: int, s: Shot, last: bool) -> Path:
    frames = round((s.dur + s.hold) * FPS)
    fx, fy = s.focus
    vf = [f"fps={FPS}"]
    if s.hold:
        vf.append(f"tpad=stop_mode=clone:stop_duration={s.hold}")
    # Work at twice the size so the push-in moves in half-pixel steps rather than jumping.
    vf += [
        f"scale={W * 2}:{H * 2}:flags=lanczos",
        (
            f"zoompan=z='1+{s.push}*on/{frames}'"
            f":x='max(0\\,min(iw-iw/zoom\\,{fx}*iw-iw/zoom/2))'"
            f":y='max(0\\,min(ih-ih/zoom\\,{fy}*ih-ih/zoom/2))'"
            f":d=1:s={W}x{H}:fps={FPS}"
        ),
        "setsar=1",
    ]
    y = "64" if s.top else "h-150"
    vf.append(kinetic(text(tmp, f"line{i}", s.line), 50, "64", y, s.line_at))
    if s.note:
        vf.append(
            f"drawtext=fontfile={MONO}:textfile={text(tmp, f'note{i}', s.note)}:expansion=none"
            f":fontsize=20:fontcolor={INK}:box=1:boxcolor={PAPER}@0.94:boxborderw=10"
            f":x=w-text_w-40:y=96:enable='gte(t\\,{s.line_at})'"
        )
    if last:
        total = s.dur + s.hold
        vf.append(f"fade=t=out:st={total - CLOSE_FADE}:d={CLOSE_FADE}")
    out = tmp / f"part{i + 1:02d}.mp4"
    encode(
        ["-ss", str(s.start), "-t", str(s.dur), "-i", str(s.src), "-vf", ",".join(vf)],
        out,
    )
    return out


def main() -> None:
    with tempfile.TemporaryDirectory(dir=HERE) as tmpname:
        tmp = Path(tmpname)
        parts = [hook(tmp)]
        parts += [
            shot_part(tmp, i, s, i == len(SHOTS) - 1) for i, s in enumerate(SHOTS)
        ]
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
    t = HOOK_SECONDS
    print(f"{0:6.1f}  hook      {' '.join(HOOK)}")
    for s in SHOTS:
        print(f"{t:6.1f}  {s.beat:<8}  {s.line}")
        t += s.dur + s.hold
    print(f"{t:6.1f}  end\n{OUT}")


if __name__ == "__main__":
    main()
