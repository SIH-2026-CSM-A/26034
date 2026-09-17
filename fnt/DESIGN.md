# DESIGN.md — fnt

The design system for the PCCS frontend: the public consumer surface (`src/consumer/`),
the officer surface (`src/officer/`) and sign-in. This is the source of truth for palette,
type, elevation, motion, state rendering and verdict rendering. Where a component
disagrees with this file, the component is wrong.

Two readers. A member of the public — or a judge — opening `/consumer` on a phone, who
should feel they are holding a well-made consumer app. And a Legal Metrology officer
holding a phone at arm's length in daylight, standing in front of the person whose package
they just scanned. The register is a **precision instrument**: calm surfaces, exact type,
motion that behaves like a physical thing. Not a dashboard template, not a ledger.

**What outranks aesthetics, always:** the verdict and field-state rules below, the
forbidden vocabulary, and honesty about data — no number, count or percentage appears
that is not computed from a response, seeded records keep their badge, the ward
disclaimer stays on the map, and an empty list says it is empty rather than spinning.

---

## Tokens

All colour is a CSS variable in `src/index.css`, exposed to Tailwind in
`tailwind.config.js`. A raw hex in a component is a bug. The one sanctioned exception is
the choropleth data ramp in `HeatmapJurisdiction.tsx`, which is interpolated in JS.

### Grounds, back to front

| Token | Light | Dark | Used for |
|---|---|---|---|
| `paper` | `#F3F4F1` | `#0A0E13` | The page |
| `sunken` | `#E8EAE6` | `#06090D` | Input wells, tracks, the map's empty wards |
| `surface` | `#FFFFFF` | `#141A22` | Cards, sheets, chips |
| `focus-tint` | `#E4E8EC` | `#202A36` | The focused ledger row |

### Ink

| Token | Light | Dark | Used for |
|---|---|---|---|
| `ink` | `#0E1620` | `#E9EDF0` | Text, primary buttons |
| `mute` | `#4A5560` | `#9EAAB6` | Secondary text; NOT APPLICABLE and INSUFFICIENT EVIDENCE |
| `hairline` | `#D4D8D3` | `#2C3642` | Card edges, dividers |
| `accent` | `#23489B` | `#8FB0FF` | Focus ring, links, selection. Lapis. Never a state. |

### State colours — the most constrained colours in the system

| Token | Light | Dark | Means |
|---|---|---|---|
| `attest` / `attest-tint` | `#14603C` / `#E2F1E8` | `#62CE97` / `#102C1F` | PASS, and nothing else |
| `query` / `query-tint` | `#7D5004` / `#F7EDD6` | `#E4B450` / `#30250C` | REVIEW, REVIEW REQUIRED, the seeded-demo badge |
| `seal` / `seal-tint` | `#A32A1E` / `#FAE5E2` | `#FF8E7E` / `#3A1813` | FAIL, POTENTIAL VIOLATION |

**Seal means *this package fails a rule that applies to it, pending officer
confirmation*.** It is never used for absent data, a network error, a refused sign-in, a
rejected photograph, a destructive button or emphasis. System messages use
`src/ui/Notice.tsx`, which is ink on a dashed card.

### Measured contrast — do not trust a table, re-run it

`node scripts/contrast.mjs` reads the variables out of `index.css`, prints every
text-on-ground pair in both themes and exits 1 under 4.5:1. Lowest pairs as of this
revision: light `query on focus-tint` 5.64, dark `mute on focus-tint` 6.14. The old
palette's focus-tint defect (Query Ochre at 3.97:1 on the focused row) is gone because
the pair now clears AA outright — but unfilled chips still ground on `surface`
explicitly, so that stays true if the tint ever moves.

Text never sits on the hatch. INSUFFICIENT EVIDENCE plates its label on `surface` and
the hatch frames it.

### The gradient system

One, called `aurora` (`.aurora` in `index.css`): three very wide radial washes of
`accent`, `query` and `attest` at a few percent alpha, fixed behind the page. It is the
state palette diluted, so it cannot drift into a fourth colour story, and it follows the
theme for free. No purple, no mesh blob, no gradient text, no gradient on a button
beyond the 14% rim highlight on `.btn-primary`.

---

## Type

Three faces, all self-hosted from `public/fonts/` as OFL `.woff2`. No webfont CDN: the
demo has to render with the venue network dead.

- **Bricolage Grotesque** (variable, 200–800) — voice. Page titles, verdict words, the
  numeral on a metric tile. `font-display`. It has optical character at 40px+ and that is
  the only place it is used.
- **IBM Plex Sans** — language. Prose, labels, buttons.
- **IBM Plex Mono** — anything measured, cited or timestamped: measurements, thresholds,
  rule citations, ids, rule-set versions, timestamps. Tabular, so `2.1 mm` sits digit over
  digit above `≥ 2.5 mm`.

| Step | Size / weight | Role |
|---|---|---|
| `text-hero` | clamp 38–64 / 650 | Consumer landing headline. One per surface. |
| `text-display` | clamp 34–44 / 650 | Verdict banner, metric numerals |
| `text-title` | 28 / 600 | Screen title |
| `text-section` | 21 / 600 | Section heading |
| `text-body` | 17 / 400 | Body copy, field names |
| `text-secondary` | 15 / 400 | Reasons, meta, buttons |
| `text-label` | 13 / 500 | Column headers, chip text, citations |

17px base, in px, for a phone at arm's length. Sentence case throughout. No tracked-out
all-caps labels, no eyebrow above every heading, no italic or recoloured word inside a
headline. Verdicts and field states are the one exception and are set in capitals, because
they are quoted verbatim in the report.

## Space, radius, elevation

Tailwind's 4px scale. Rhythm: 16 inside a control group, 24 between cards, 40–56 between
page sections. Page gutter 16 at 390, max content width 1280 (officer) / 720 (consumer).

| Radius | Value | For |
|---|---|---|
| `rounded-ctl` | 12 | Buttons, inputs |
| `rounded-card` | 20 | Cards, banners |
| `rounded-sheet` | 28 | Bottom sheets, the mobile tab bar |
| `rounded-full` | — | Chips, tags, pills |

| Shadow | For |
|---|---|
| `shadow-e1` | A card at rest |
| `shadow-e2` | Hover, the verdict banner, a toggle knob |
| `shadow-e3` | Sheets, dialogs, the floating tab bar |
| `shadow-rim` | The 1px top light on any raised surface; bundled into `.card` and `.glass` |

Each level is a tight contact shadow plus a wide ambient one, tinted from `--c-shadow`.
**Glass** (`.glass`) is for chrome that content scrolls under — the top bar, the tab bar,
the verdict confirmation sheet, the map readout — and nowhere else. A glass card in the
page flow is decoration.

## Motion

Framer Motion, with tokens in `src/ui/motion.ts`: springs `snap` (presses, toggles, nav
pill), `glide` (cards, rows, shared elements) and `lift` (hover on the map and tiles),
plus the `stagger` / `rise` list variants. CSS transitions use `duration-fast|base|slow`
with `ease-out` / `ease-in-out`. Never the browser default `ease`, never a bounce on state.

- **Animation never delays a verdict and never hides a citation.** Entrances run on nodes
  that already hold their final text. No verdict, state, clause reference or count is
  typed on, revealed on scroll, or placed behind a hover.
- **Shared elements:** a queue row and the verdict screen's summary card share
  `layoutId={`scan-${id}`}`; the row hands its summary over in router state so the card is
  on screen on the first frame, before the detail fetch returns.
- **Lists** enter with `stagger` + `rise`, 35ms a row.
- **Press** is `scale(0.965)` in 80ms; release springs back. **Hover** lifts 1–2px to
  `shadow-e2`, only under `(hover: hover)`.
- **Numbers** on metric tiles use `src/ui/CountUp.tsx`: the real value is rendered and
  read by assistive technology; the count is painted over it.
- **Skeletons** (`.skeleton`) take the exact box of what replaces them. A spinner is
  allowed only inside a button that is already the right size.
- **Focus rings never animate.** 2px `accent`, 3px offset, with a `paper` gap ring.
- `prefers-reduced-motion: reduce` collapses CSS to a ≤150ms opacity change and Framer
  follows through `<MotionConfig reducedMotion="user">`.

## Dark mode

Follows the system; the header switch overrides it and is remembered. The same tokens,
second values — no `dark:` classes in components. State colours lighten rather than
invert, and every pair is in the contrast script.

---

## The five field states

`FieldState` has five members and they are not five shades of one idea. Each renders on
**four independent channels, with colour last**: a glyph, a fill, a border treatment, and
a weight. Desaturate the screen and all five must remain separable.

| State | Glyph | Fill | Border | Weight | Colour |
|---|---|---|---|---|---|
| PASS | tick ✓ | filled | none | 500 | `attest` |
| FAIL | cross ✕ | unfilled | 5px left edge | 600 | `seal` |
| REVIEW REQUIRED | question ? | unfilled | dashed outline | 500 | `query` |
| NOT APPLICABLE | em dash — | unfilled | none | 400, lightest | `mute` |
| INSUFFICIENT EVIDENCE | hollow ring ○ | 45° hatched ground | dotted | 500 | `mute` |

Unfilled chips carry an explicit `surface` ground rather than inheriting the row's, so a state
colour only ever sits on a ground it was measured against.

### FAIL and INSUFFICIENT EVIDENCE share no channel

This is the single most important separation in the product, and it is enforced
structurally rather than by good intentions:

| Channel | FAIL | INSUFFICIENT EVIDENCE |
|---|---|---|
| Glyph | cross ✕ | hollow ring ○ |
| Fill | flat surface | 45° hatch |
| Border | 5px solid left edge | dotted, all round |
| Colour | `seal` | `mute` |

Four channels, four differences. There is no viewing condition — greyscale, glare,
colour-vision deficiency, a cracked panel — in which one degrades into the other.

**"We could not read it" and "it is not there" are different findings with different
legal consequences.** FAIL asserts something about the package and can support
enforcement. INSUFFICIENT EVIDENCE asserts something about our reading of the package and
cannot. Collapsing them is a wrongful-flag liability, not a style choice.

### The remedy is the tell, before the label is

**INSUFFICIENT EVIDENCE is never styled to read like a failure.** No seal, no seal-tint, no
warning triangle, no cross. It is a statement about the photograph. The same goes for a
photograph rejected for quality, and for a scan that did not finish.

- **INSUFFICIENT EVIDENCE rows always carry `Request recapture`.** Always. The remedy for
  an unreadable panel is a better photograph.
- **FAIL rows never carry it.** Re-photographing a package that genuinely falls short of
  a rule does not change what the package says. Offering recapture there would suggest
  the finding is a reading problem, which is the exact confusion the five-state enum
  exists to prevent.

An officer scanning the ledger sees which row is which from the action column before
they have read a single label. That is deliberate: the remedy is the fastest-read
channel on the row.

---

## The three verdicts

`PASS`, `REVIEW`, `POTENTIAL VIOLATION`. Every rendering of a verdict, at any size, is
**an icon, the word, and a colour together** — never one standing in for another, and
never an emoji. A fourth channel, rule weight, keeps them apart in greyscale:

| Verdict | Icon | Rule | Colour / tint | Weight on the page |
|---|---|---|---|---|
| PASS | tick in a circle | solid 2px | attest on attest-tint | ordinary |
| REVIEW | eye | dashed 2px | query on query-tint | ordinary |
| POTENTIAL VIOLATION | warning triangle | double 6px | seal on seal-tint | the heaviest object on the screen |

`VerdictBanner` is the one-per-screen form, `VerdictTag` the list-row form. Both live in
`src/officer/components/VerdictBanner.tsx` and nothing else in `fnt/` may draw a verdict.
The word is never paraphrased: no "fail", no "cleared", nothing that reads as settled.

Every verdict banner carries **"Pending officer confirmation"** beneath it. The system
recommends; a human confirms. There is no verdict for a confirmed breach and there never
will be — the enum has three members for that reason.

### Forbidden vocabulary

Four phrasings never appear anywhere in `fnt/` — not in copy, not in comments, not in
fixtures, not in test names. They are deliberately described here rather than written
out, so that this file passes the same sweep it imposes:

1. The word "violation" followed by a word asserting it has been established.
2. The negated-compliance adjective, hyphenated, that asserts a package breaches the
   Rules as a settled fact.
3. The one-word adjective meaning contrary to law.
4. The one-word adjective assigning culpability to a person.

`POTENTIAL VIOLATION` is the sanctioned term and is safe: it is a recommendation, and
the qualifier is doing the legal work.

A case-insensitive `grep -rniE` over `fnt/` for the four phrasings, excluding
`node_modules` and `dist`, is part of the pre-push check. The pattern is not written
into any tracked file — a file carrying the pattern is a file that fails its own sweep,
and a sweep with a permanent exception is a sweep nobody trusts. Assemble it at the
command line from the four descriptions above.

The software recommends. It does not issue a legal determination, and its vocabulary
must not imply that it has. A human confirmation step sits between any output on these
screens and any action taken against a manufacturer, packer or importer.

---

## Greyscale is a shipping gate

**A screenshot desaturated to greyscale must let a reader tell all eight states apart —
the five field states and the three verdicts — from shape, fill, border and weight
alone.** Run it before any state-rendering component ships. If PASS and REVIEW REQUIRED
are the same object in greyscale, the component is not done.

This is not an accessibility nicety bolted on at the end. It is the test that proves the
four channels are actually independent, and it is the reason colour is specified last in
every table above.

---

---

## Interaction

- **48px minimum touch target**, everywhere.
- **No meaning carried by hover alone.** Hover is not available on the primary device.
  Anything hover reveals — the map readout included — is also reachable by tap and focus.
- **No state carried by a colour dot.** One channel is never enough.
- **The machine's column and the officer's column never share a ground.** What the system
  found sits on `surface`; what the officer decides sits on the ink confirmation sheet.
- **Every async screen has four honest states:** a skeleton while loading, a `Notice` on
  failure with a retry, a plain sentence when empty, and the data. Nothing polls forever
  without saying how long it has been.

## Layout

- **Phone 390 first, desktop 1280 second.** Both are first-class.
- On a phone the officer's primary navigation is a floating tab bar in thumb reach;
  pages that mount `OfficerHeader` leave `pb-28 md:pb-16` for it.
- The verdict screen keeps its own masthead: inspection id, rule-set version, capture
  time and the offline marker are permanent furniture, not a toast.
- The consumer surface carries no officer chrome at all.

## Implementation conventions

- **Tailwind only.** No CSS-in-JS. Shared looks are the component classes in `index.css`
  (`.card`, `.card-lift`, `.glass`, `.btn` + `.btn-primary|quiet|ghost`, `.input`,
  `.badge-seeded`, `.skeleton`, `.aurora`). Add one only when three components repeat it.
- **Primitives live in `src/ui/`** — `motion.ts`, `CountUp`, `ThemeToggle`, `Notice`,
  `Logo`. No component library.
- **Dependencies:** `framer-motion` is the one approved addition. Anything else, ask.
- **Tokens, not raw values. No `any`.** Types come from `src/services/generated/`.
- **No fixture imports** in anything that renders. No hardcoded ids.
- `src/layout/AppShell.tsx` belongs to the admin surface and is not restyled from here.
