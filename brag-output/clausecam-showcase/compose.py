"""Generate the showcase's Hyperframes composition (composition/index.html) from one table.

Every screen is real footage of the deployed app, cut by prepare.sh. What this adds on top is
type and graphics only: titles, chips, highlight boxes and underlines drawn onto the footage at
the source-pixel positions of the UI they point at, a spotlight that dims the rest, and the
motion between shots. The one edit inside a take, the OCR wait, is named on screen.

Timing follows the voice: each line of voiceover.txt is its own clip, placed in VO below, and
the shots are cut to it. The chips in shot 1 and the wordmark land on strong beats of the bed.

    python3 brag-output/clausecam-showcase/compose.py
"""

import html
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "composition" / "index.html"
ASSETS = HERE / "composition" / "assets"

W, H = 1280, 800
DURATION = 88.5
INK, PAPER, AMBER = "#0E1620", "#F3F4F1", "#F5B301"

# (clip id, start, duration)
SHOTS = [
    ("sh01", 4.0, 8.3),
    ("sh02", 12.3, 3.5),
    ("sh03", 15.8, 4.4),
    ("sh04", 26.0, 4.6),
    ("sh05", 30.6, 1.6),
    ("sh06", 32.2, 6.2),
    ("sh07", 38.4, 3.8),
    ("sh08", 42.2, 5.0),
    ("sh09", 47.2, 5.8),
    ("sh10", 53.0, 5.4),
    ("sh11", 58.4, 7.6),
    ("sh12", 66.0, 4.5),
    ("sh13", 70.5, 3.7),
    ("sh14", 74.2, 7.0),
]
STILL = (81.2, DURATION - 81.2)  # the landing page's final frame, held under the close
CARDS = [("hook", 0.0, 4.0), ("question", 20.2, 5.8)]

# Voiceover line index -> start. Lines are voiceover.txt, one clip each.
VO = [
    0.8,
    4.3,
    12.5,
    16.0,
    20.5,
    23.8,
    26.3,
    30.8,
    34.0,
    38.8,
    42.5,
    47.5,
    53.4,
    58.8,
    78.7,
    80.9,
]

# Titles: (shot, text, at). A second title in the same shot replaces the first. Shots in
# TOP_TITLES carry theirs at the top, where the footage has its subject at the bottom.
TITLES = [
    ("sh01", "Every pack must declare", 4.4),
    ("sh02", "One inspector. A whole shelf.", 12.5),
    ("sh03", "Dozens of legal rules.", 16.0),
    ("sh04", "No category. No guess.", 26.3),
    ("sh05", "Confirmed: food.", 30.7),
    ("sh06", "Same rule. Not applicable.", 32.3),
    ("sh06", "It names the law.", 34.0),
    ("sh07", "A real scan. The live app.", 38.8),
    ("sh08", "The exact clause.", 42.6),
    ("sh09", "Too close to call? It says so.", 47.6),
    ("sh10", "An officer decides.", 53.4),
    ("sh11", "The report, fingerprinted.", 58.9),
    ("sh12", "See where violations cluster.", 66.2),
    ("sh13", "See which clauses break.", 70.6),
]
TOP_TITLES = {"sh10"}  # REVIEW RECORDED appears at the bottom of the frame

# Highlights in source pixels of the 1280x800 recording: (shot, kind, geometry, at, until).
# kind "box" draws a rectangle and dims the rest; "line" draws an underline.
HIGHLIGHTS = [
    ("sh03", "box", (300, 612, 325, 30), 16.5, None),  # "across 46 rules"
    ("sh04", "box", (560, 270, 206, 36), 26.5, None),  # INSUFFICIENT EVIDENCE
    (
        "sh04",
        "line",
        (42, 398, 720),
        27.4,
        None,
    ),  # "the product category has not been confirmed..."
    ("sh05", "box", (32, 274, 212, 32), 30.8, None),  # FOOD · OFFICER CONFIRMED
    ("sh06", "box", (620, 328, 144, 28), 32.4, 34.6),  # NOT APPLICABLE
    (
        "sh06",
        "line",
        (244, 452, 476),
        34.8,
        None,
    ),  # Food Safety and Standards Act, 2006
    ("sh06", "line", (688, 452, 746), 36.2, None),  # R6-1-A-
    ("sh06", "line", (42, 474, 150), 36.35, None),  # EXPL-III-FOOD
    (
        "sh08",
        "box",
        (314, 198, 652, 96),
        42.9,
        None,
    ),  # Rule 7(2), Table-I, measured, required
    ("sh09", "box", (34, 116, 734, 94), 48.3, None),  # the too-close-to-call reason
    ("sh10", "box", (44, 498, 238, 53), 53.5, 55.4),  # Confirm
    (
        "sh10",
        "box",
        (50, 722, 270, 55),
        56.2,
        None,
    ),  # REVIEW RECORDED · CONFIRM · Finalised
    ("sh11", "box", (46, 462, 592, 52), 59.6, None),  # the SHA-256
]

# Small labels. (shot, text, at, style). "note" names an edit inside a take.
TAGS = [
    ("sh07", "LIVE · deployed app", 38.6, "tag"),
    ("sh08", "57 s of OCR cut", 42.2, "note"),
    ("sh11", "SHA-256 · written to the evidence chain", 61.3, "callout"),
]

# Chips: (text, at, group). The first group lands on strong beats of the bed.
CHIPS = [
    ("Who made it", 8.74, "declare"),  # beat-locked: 8.74
    ("How much is inside", 9.83, "declare"),  # beat-grid: 9.83
    ("The price", 10.93, "declare"),  # beat-locked: 10.93
    ("The right rules.", 80.95, "close"),
    ("The exact clause.", 82.0, "close"),
    ("A person who decides.", 83.1, "close"),
]

SFX = [  # (file, at, volume)
    ("impactSoft_medium_001.ogg", 0.75, 0.5),
    ("drop_001.ogg", 8.74, 0.4),
    ("drop_001.ogg", 9.83, 0.4),
    ("drop_001.ogg", 10.93, 0.4),
    ("drop_002.ogg", 23.8, 0.45),
    ("click_003.ogg", 55.0, 0.5),  # the submit click in the footage
    ("drop_002.ogg", 59.6, 0.45),
    ("bong_001.ogg", 78.56, 0.4),  # beat-locked: the wordmark lands
]

# Music bed, ducked under the voice. (seconds, level)
MUSIC_LANE = [
    (0, 0),
    (0.5, 0.26),
    (3.6, 0.26),
    (4.2, 0.13),
    (65.2, 0.13),
    (66.0, 0.34),
    (73.8, 0.34),
    (74.6, 0.28),
    (78.4, 0.28),
    (78.8, 0.13),
    (84.5, 0.13),
    (85.3, 0.3),
    (87.6, 0.3),
    (88.5, 0),
]
CREDIT = (
    "Music: “Happy Beats & Business Moves Vol. 12” by Sascha Ende (ende.app), "
    "CC BY 4.0 · Voice: synthetic (Kokoro)"
)


def length(path: Path) -> float:
    """The media file's own length, so every audio slot matches its clip."""
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return round(float(out.stdout), 2)


def words(text: str) -> str:
    return " ".join(f'<span class="w">{html.escape(w)}</span>' for w in text.split())


def shot_html(sid: str, start: float, dur: float) -> str:
    svg = []
    for i, (s, kind, g, _, _) in enumerate(HIGHLIGHTS):
        if s != sid:
            continue
        if kind == "box":
            x, y, w, h = g
            spot = f"M0 0H{W}V{H}H0Z M{x} {y}h{w}v{h}h{-w}Z"
            svg.append(f'<path id="{sid}-spot{i}" class="spot" d="{spot}"/>')
            svg.append(
                f'<rect id="{sid}-hl{i}" class="hl" x="{x}" y="{y}" width="{w}" height="{h}" '
                'rx="8" pathLength="1"/>'
            )
        else:
            x1, y, x2 = g
            svg.append(
                f'<line id="{sid}-hl{i}" class="ul" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
                'pathLength="1"/>'
            )
    tags = [
        f'<div id="{sid}-tag{i}" class="{style}">{html.escape(text)}</div>'
        for i, (s, text, _, style) in enumerate(TAGS)
        if s == sid
    ]
    titles = [
        f'<div id="{sid}-title{i}" class="title{" top" if sid in TOP_TITLES else ""}">'
        '<div class="pill"></div>'
        f'<div class="words">{words(text)}</div></div>'
        for i, (s, text, _) in enumerate(TITLES)
        if s == sid
    ]
    return f"""
      <div id="{sid}" class="shot">
        <div id="{sid}-frame" class="frame"><div id="{sid}-inner" class="inner" data-layout-allow-overflow>
          <video id="{sid}-video" class="clip media" src="assets/clips/{sid}.mp4"
            data-start="{start}" data-duration="{dur}" data-track-index="0" muted playsinline></video>
          <svg class="overlay" viewBox="0 0 {W} {H}" preserveAspectRatio="none">{"".join(svg)}</svg>
        </div>{"".join(tags)}</div>
        {"".join(titles)}
      </div>"""


def timeline_js() -> str:
    js = ["const tl = gsap.timeline({ paused: true });"]
    js.append(
        f'tl.fromTo("#ground", {{ backgroundPosition: "0px 0px" }}, '
        f'{{ backgroundPosition: "-240px -150px", duration: {DURATION}, ease: "none" }}, 0);'
    )
    spans = list(SHOTS) + [("still", *STILL)]
    for sid, start, dur in spans:
        end = start + dur
        js.append(f'tl.set("#{sid}", {{ opacity: 1 }}, {start});')
        # Enter with movement, push in while held, snap out.
        js.append(
            f'tl.fromTo("#{sid}-frame", {{ x: 90, rotation: 0.6, scale: 1.04 }}, '
            f'{{ x: 0, rotation: 0, scale: 1, duration: 0.55, ease: "expo.out" }}, {start});'
        )
        js.append(
            f'tl.fromTo("#{sid}-inner", {{ scale: 1 }}, '
            f'{{ scale: 1.05, duration: {dur}, ease: "none" }}, {start});'
        )
        if sid != "still":
            js.append(
                f'tl.to("#{sid}-frame", {{ x: -70, scale: 0.98, duration: 0.22, '
                f'ease: "power2.in" }}, {end - 0.22});'
            )
            js.append(f'tl.set("#{sid}", {{ opacity: 0 }}, {end});')
    for cid, start, dur in CARDS:
        js.append(f'tl.set("#{cid}", {{ opacity: 1 }}, {start});')
        js.append(f'tl.set("#{cid}", {{ opacity: 0 }}, {start + dur});')
    # Hook: two lines build, an underline draws, the card pushes away.
    js.append(
        'tl.fromTo("#hook .l1 .w", { yPercent: 120 }, { yPercent: 0, stagger: 0.08, '
        'duration: 0.6, ease: "expo.out" }, 0.8);'
    )
    js.append(
        'tl.fromTo("#hook .l2 .w", { yPercent: 120 }, { yPercent: 0, stagger: 0.08, '
        'duration: 0.6, ease: "expo.out" }, 1.6);'
    )
    js.append(
        'tl.fromTo("#hook .bar", { scaleX: 0 }, { scaleX: 1, duration: 0.7, '
        'ease: "expo.inOut" }, 2.3);'
    )
    js.append(
        'tl.to("#hook .stack", { scale: 1.08, opacity: 0, duration: 0.35, '
        'ease: "power2.in" }, 3.65);'
    )
    js.append(
        'tl.fromTo("#question .eyebrow .w", { yPercent: 120 }, { yPercent: 0, '
        'stagger: 0.06, duration: 0.5, ease: "expo.out" }, 20.6);'
    )
    js.append(
        'tl.fromTo("#question .l1 .w", { yPercent: 120 }, { yPercent: 0, stagger: 0.09, '
        'duration: 0.6, ease: "expo.out" }, 23.8);'
    )
    js.append(
        'tl.fromTo("#question .bar", { scaleX: 0 }, { scaleX: 1, duration: 0.6, '
        'ease: "expo.inOut" }, 24.4);'
    )
    js.append(
        'tl.to("#question .stack", { x: -80, opacity: 0, duration: 0.3, '
        'ease: "power2.in" }, 25.7);'
    )
    # Titles: a panel wipes open, words rise through it; a later title replaces an earlier one.
    per_shot: dict[str, list[tuple[int, float]]] = {}
    for i, (s, _, at) in enumerate(TITLES):
        per_shot.setdefault(s, []).append((i, at))
    for s, items in per_shot.items():
        for n, (i, at) in enumerate(items):
            t = f"#{s}-title{i}"
            js.append(f'tl.set("{t}", {{ opacity: 1 }}, {at});')
            js.append(
                f'tl.fromTo("{t} .pill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.4, '
                f'ease: "expo.out" }}, {at});'
            )
            js.append(
                f'tl.fromTo("{t} .w", {{ yPercent: 110, opacity: 0 }}, {{ yPercent: 0, '
                f'opacity: 1, stagger: 0.05, duration: 0.45, ease: "expo.out" }}, {at + 0.08});'
            )
            if n + 1 < len(items):
                js.append(
                    f'tl.to("{t}", {{ y: -24, opacity: 0, duration: 0.25 }}, '
                    f"{items[n + 1][1] - 0.2});"
                )
    for i, (s, kind, _, at, until) in enumerate(HIGHLIGHTS):
        hl = f"#{s}-hl{i}"
        js.append(
            f'tl.fromTo("{hl}", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, '
            f'duration: 0.55, ease: "power2.inOut" }}, {at});'
        )
        if kind == "box":
            js.append(f'tl.to("#{s}-spot{i}", {{ opacity: 1, duration: 0.4 }}, {at});')
        if until is not None:
            js.append(f'tl.to("{hl}", {{ opacity: 0, duration: 0.25 }}, {until});')
            if kind == "box":
                js.append(
                    f'tl.to("#{s}-spot{i}", {{ opacity: 0, duration: 0.25 }}, {until});'
                )
    for i, (s, _, at, _) in enumerate(TAGS):
        js.append(
            f'tl.fromTo("#{s}-tag{i}", {{ opacity: 0, y: -12 }}, {{ opacity: 1, y: 0, '
            f'duration: 0.35, ease: "back.out(2)" }}, {at});'
        )
    for i, (_, at, group) in enumerate(CHIPS):
        js.append(
            f'tl.fromTo("#chip{i}", {{ opacity: 0, scale: 0.6, y: 16 }}, {{ opacity: 1, '
            f'scale: 1, y: 0, duration: 0.4, ease: "back.out(2.2)" }}, {at});'
        )
        if group == "declare":
            js.append(f'tl.to("#chip{i}", {{ opacity: 0, duration: 0.2 }}, 12.1);')
    js.append('tl.to("#credit", { opacity: 1, duration: 0.5 }, 84.8);')
    js.append(
        f'tl.fromTo("#fade", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.8 }}, '
        f"{DURATION - 0.8});"
    )
    js.append('window.__timelines["clausecam-showcase"] = tl;')
    return "\n      ".join(js)


def main() -> None:
    hook = (
        '<div id="hook" class="card"><div class="stack">'
        f'<div class="big l1">{words("Same rule.")}</div>'
        f'<div class="big l2">{words("Different answer.")}</div>'
        '<div class="bar"></div></div></div>'
    )
    question = (
        '<div id="question" class="card"><div class="stack">'
        f'<div class="eyebrow">{words("First, the question most tools skip:")}</div>'
        f'<div class="big l1">{words("Which rules apply?")}</div>'
        '<div class="bar"></div></div></div>'
    )
    still = (
        '<div id="still" class="shot"><div id="still-frame" class="frame">'
        '<div id="still-inner" class="inner" data-layout-allow-overflow>'
        f'<img id="still-img" class="clip media" src="assets/clips/close-still.png" '
        f'data-start="{STILL[0]}" data-duration="{STILL[1]:.1f}" data-track-index="1" alt=""/>'
        "</div></div></div>"
    )
    chips = "".join(
        f'<div id="chip{i}" class="chip {g}">{html.escape(t)}</div>'
        for i, (t, _, g) in enumerate(CHIPS)
    )
    vo = "".join(
        f'<audio id="vo{i:02d}" src="assets/vo/vo{i:02d}.wav" data-start="{at}" '
        f'data-duration="{length(ASSETS / "vo" / f"vo{i:02d}.wav")}" '
        f'data-track-index="3" data-volume="1"></audio>'
        for i, at in enumerate(VO)
    )
    sfx = "".join(
        f'<audio id="sfx{i}" src="assets/sfx/{f}" data-start="{at}" '
        f'data-duration="{length(ASSETS / "sfx" / f)}" '
        f'data-track-index="{11 + i}" data-volume="{v}"></audio>'
        for i, (f, at, v) in enumerate(SFX)
    )
    lane = json.dumps(
        {
            "version": 1,
            "lanes": [
                {
                    "target": "volume",
                    "points": [{"t": t, "v": v} for t, v in MUSIC_LANE],
                }
            ],
        }
    )
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>ClauseCam showcase</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Bricolage Grotesque"; font-weight: 200 800; src: url("assets/fonts/BricolageGrotesque-Variable.woff2") format("woff2"); }}
      @font-face {{ font-family: "IBM Plex Sans"; font-weight: 600; src: url("assets/fonts/IBMPlexSans-SemiBold.woff2") format("woff2"); }}
      @font-face {{ font-family: "IBM Plex Mono"; font-weight: 500; src: url("assets/fonts/IBMPlexMono-Medium.woff2") format("woff2"); }}
      body {{ margin: 0; background: {INK}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: {INK}; }}
      #ground {{ position: absolute; inset: 0; background-color: {INK};
        background-image: radial-gradient(rgba(243,244,241,0.09) 1.2px, transparent 1.3px);
        background-size: 30px 30px; }}
      .shot, .card {{ position: absolute; inset: 0; }}
      .frame {{ position: absolute; left: 40px; top: 25px; width: 1200px; height: 750px;
        border-radius: 18px; overflow: hidden; box-shadow: 0 30px 80px rgba(0,0,0,0.55); }}
      .inner {{ position: absolute; inset: 0; }}
      .media {{ position: absolute; left: 0; top: 0; width: 1200px; height: 750px; object-fit: cover; }}
      .overlay {{ position: absolute; inset: 0; width: 1200px; height: 750px; }}
      .spot {{ fill: {INK}; fill-opacity: 0.42; fill-rule: evenodd; }}
      .hl {{ fill: none; stroke: {AMBER}; stroke-width: 5; stroke-dasharray: 1; }}
      .ul {{ stroke: {AMBER}; stroke-width: 5; stroke-linecap: round; stroke-dasharray: 1; }}
      .title {{ position: absolute; left: 72px; bottom: 58px; padding: 14px 24px 16px; }}
      .title.top {{ top: 52px; bottom: auto; }}
      .pill {{ position: absolute; inset: 0; background: {INK}; border-radius: 14px;
        transform-origin: left center; box-shadow: 0 12px 40px rgba(0,0,0,0.35); }}
      .words {{ position: relative; overflow: hidden; font: 800 44px/1.12 "Bricolage Grotesque", sans-serif;
        color: {PAPER}; letter-spacing: -0.01em; padding-bottom: 6px; }}
      .w {{ display: inline-block; }}
      .card {{ display: flex; align-items: center; justify-content: center; background: transparent; }}
      .stack {{ display: flex; flex-direction: column; align-items: center; }}
      .big {{ overflow: hidden; font: 800 96px/1.08 "Bricolage Grotesque", sans-serif; color: {PAPER};
        letter-spacing: -0.02em; }}
      .eyebrow {{ overflow: hidden; margin-bottom: 18px; font: 600 28px/1.3 "IBM Plex Sans", sans-serif;
        color: {PAPER}; }}
      .bar {{ width: 520px; height: 8px; margin-top: 26px; border-radius: 4px; background: {AMBER};
        transform-origin: left center; }}
      .tag, .note {{ position: absolute; right: 24px; top: 96px; padding: 8px 14px; border-radius: 8px;
        font: 500 19px/1.2 "IBM Plex Mono", monospace; }}
      .tag {{ background: {INK}; color: {PAPER}; }}
      .note {{ background: {PAPER}; color: {INK}; box-shadow: 0 6px 20px rgba(0,0,0,0.25); }}
      .callout {{ position: absolute; left: 44px; top: 505px; padding: 10px 16px; border-radius: 10px;
        background: {AMBER}; color: {INK}; font: 600 22px/1.2 "IBM Plex Sans", sans-serif; }}
      .chip {{ position: absolute; padding: 12px 22px; border-radius: 999px; background: {PAPER};
        color: {INK}; font: 600 28px/1.1 "IBM Plex Sans", sans-serif; box-shadow: 0 10px 30px rgba(0,0,0,0.35); }}
      #chip0 {{ left: 110px; top: 250px; }} #chip1 {{ left: 110px; top: 330px; }} #chip2 {{ left: 110px; top: 410px; }}
      #chip3 {{ left: 120px; top: 44px; }} #chip4 {{ left: 470px; top: 44px; }} #chip5 {{ left: 830px; top: 44px; }}
      #credit {{ position: absolute; left: 0; right: 0; bottom: 34px; text-align: center; padding: 8px;
        font: 500 15px/1.3 "IBM Plex Mono", monospace; color: {INK}; }}
      #fade {{ position: absolute; inset: 0; background: {INK}; opacity: 0; }}
      .shot, .card, .title, .spot, .tag, .note, .callout, .chip, #credit {{ opacity: 0; }}
      .hl, .ul {{ stroke-dashoffset: 1; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="clausecam-showcase" data-start="0"
      data-width="{W}" data-height="{H}" data-duration="{DURATION}">
      <div id="ground"></div>
      {hook}
      {question}
      {"".join(shot_html(*s) for s in SHOTS)}
      {still}
      {chips}
      <div id="credit">{html.escape(CREDIT)}</div>
      <div id="fade"></div>
      <audio id="music" src="assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"
        data-start="0" data-duration="{DURATION}" data-track-index="10" data-volume="1"
        data-automation='{lane}'></audio>
      {vo}
      {sfx}
    </div>
    <script>
      {timeline_js()}
    </script>
  </body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
