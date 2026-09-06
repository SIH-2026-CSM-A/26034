# DESIGN.md — fnt

The design system for the PCCS frontend. Applies to the officer surface
(`src/officer/`) and the admin surface (`src/admin/`).

This is the source of truth for palette, type, state rendering and verdict rendering.
Where a component disagrees with this file, the component is wrong.

The reader this is designed for is a Legal Metrology officer — Controller, Deputy or
Inspector — holding a phone at arm's length in Indian daylight, on a cheap panel with
washed-out saturation, possibly offline, standing in front of the person whose package
they just scanned. Every decision below follows from that and not from taste.

---

## Palette

Light-first. There is no dark mode and no inversion: the screen is read under sun far
more often than in a dim room, and a dark ground under glare loses more than it gains.

| Role | Name | Hex | Used for |
|---|---|---|---|
| Ground | Field Paper | `#DCDFDB` | The page. Every screen sits on this. |
| Ink | Gazette Ink | `#101A24` | Body copy, rules, verdict bars, focus bar |
| Conformity asserted | Attest Green | `#14603C` | PASS, and nothing else |
| Human judgement required | Query Ochre | `#845605` | REVIEW REQUIRED, REVIEW |
| Fails an applicable rule | Seal Vermilion | `#A32A1E` | FAIL, POTENTIAL VIOLATION |
| No claim made | Slate Void | `#4A5560` | Secondary text, NOT APPLICABLE, INSUFFICIENT EVIDENCE |
| Hairline | — | `#A8AFAC` | Row rules, table rules, chip borders |
| Focus tint | — | `#C9CEC9` | The ground of a focused ledger row |

**Seal Vermilion is the most constrained colour in the system.** It means *this package
fails a rule that applies to it, pending officer confirmation*. It is never used for
absent data, never for emphasis, never for a destructive-action button, never for an
error toast. If something red-looking is needed that is not a rule failure, it does not
get Seal Vermilion — it gets Gazette Ink and a shape.

**Slate Void is the colour of silence.** Every state where the machine declines to make
a claim wears it: NOT APPLICABLE (the rule does not reach this package),
INSUFFICIENT EVIDENCE (we could not read it), and secondary text generally.

### Measured contrast — do not trust this table, re-run it

WCAG 2.1 relative-luminance ratios, computed rather than eyeballed:

| Colour | on Field Paper `#DCDFDB` | on focus tint `#C9CEC9` |
|---|---|---|
| Gazette Ink `#101A24` | 13.07 | 11.01 |
| Attest Green `#14603C` | 5.64 | 4.75 |
| Query Ochre `#845605` | **4.71** | **3.97** |
| Seal Vermilion `#A32A1E` | 5.37 | 4.53 |
| Slate Void `#4A5560` | 5.66 | 4.77 |
| Hairline `#A8AFAC` | 1.66 | 1.40 |

Every state colour clears 4.5:1 on Field Paper. Query Ochre clears it by the narrowest
margin in the set, which is why nothing may be layered under it.

Hairline sits at 1.66:1 on purpose. It is a rule, not text, and a rule that meets text
contrast is a rule that competes with the reading.

### The focus-tint finding, and the fix

**Query Ochre on the focus tint measures 3.97:1 — below AA.** A focused REVIEW REQUIRED
row would therefore drop out of compliance at exactly the moment the officer is reading
it hardest. This is a real defect in the naive implementation, found by measuring rather
than by assuming the Field Paper figures carried over.

**The fix is at the component, not the palette: an unfilled state chip carries an
explicit Field Paper ground.** It does not inherit the row background. A state colour
therefore never sits on the tint, in any row, in any focus condition, and the 4.71:1
figure holds everywhere.

**Rejected alternative — lightening the focus tint. Do not re-propose this.** The
lightest tint on the `#C9CEC9`→`#DCDFDB` ramp that lifts Query Ochre to AA is `#D7DBD6`,
at 4.52:1. That tint measures **1.04:1 against Field Paper** — a focus signal at 1.04:1
is not a signal, it is a rounding error. Trading the visibility of the focus state for
2 percentage points of text contrast makes the screen worse for everyone in order to
make one number pass. The chip ground fixes both.

---

## Type

Two faces, both self-hosted from `public/fonts/` as OFL `.woff2`. No webfont CDN, no
`@fontsource` package: the officer surface has to render correctly with the venue
network dead, and a font that arrives over the wire is a font that does not arrive.

**IBM Plex Sans** — language. Prose, labels, field names, headings, buttons.

**IBM Plex Mono** — anything measured, cited or timestamped. Measurements, thresholds,
rule citations, confidence figures, inspection ids, rule-set versions, capture
timestamps.

The split is not decorative. Mono is tabular, and the ledger's whole argument is
*measured against required* — `2.1 mm` sitting directly above `≥ 2.5 mm` with the digits
in column. In a proportional face those two figures drift apart and the officer has to
read them instead of seeing them. Anything a report quotes verbatim is set in mono for
the same reason: it is a transcription, not prose.

Both faces are declared with a full system fallback stack, so a failed font load
degrades to a legible screen rather than a blank one.

### Scale

17px base. Not 16 — the base size is set for a phone held at arm's length in glare, and
the extra pixel is worth more here than the density it costs.

| Step | Size / weight | Role |
|---|---|---|
| Display | 44px / 600 | Verdict banner. One per screen. |
| Title | 27px / 600 | Screen title |
| Section | 21px / 500 | Section heading, queue column group |
| Body | 17px / 400 | Body copy, field names, ledger values |
| Secondary | 15px / 400 | Reasons, meta, masthead values |
| Label | 13px / 500 | Column headers, chip text, citations |

Six steps. Anything that does not fit one of them is being asked to do a job the
hierarchy already has a step for.

### Rules of setting

- **Sentence case throughout.** "Net quantity, letter height", not "Net Quantity, Letter
  Height" and not "NET QUANTITY".
- **No tracked-out all-caps labels.** Letter-spaced small caps are the house style of
  every dashboard template shipped since 2019 and they are harder to read at 13px in
  glare, which is the only size anyone would use them at.
- **No eyebrow above every heading.** A kicker above a title is a decoration that costs a
  line of vertical space on a 390px screen. If a section needs context, the heading
  carries it.
- **No single accented word in a headline.** Emphasis comes from the hierarchy, not from
  recolouring one word.
- **Verdicts are the one exception and are set in capitals** — `PASS`, `REVIEW`,
  `POTENTIAL VIOLATION`. They are quoted verbatim in the report, and the capitals are
  what the report contains. Field states are likewise capitalised where they name the
  state itself.

---

## The five field states

`FieldState` has five members and they are not five shades of one idea. Each renders on
**four independent channels, with colour last**: a glyph, a fill, a border treatment, and
a weight. Desaturate the screen and all five must remain separable.

| State | Glyph | Fill | Border | Weight | Colour |
|---|---|---|---|---|---|
| PASS | tick ✓ | filled | none | 500 | Attest Green |
| FAIL | cross ✕ | unfilled | 5px left edge | 600 | Seal Vermilion |
| REVIEW REQUIRED | question ? | unfilled | dashed outline | 500 | Query Ochre |
| NOT APPLICABLE | em dash — | unfilled | none | 400, lightest | Slate Void |
| INSUFFICIENT EVIDENCE | hollow ring ○ | 45° hatched ground | dotted | 500 | Slate Void |

Unfilled chips carry an explicit Field Paper ground — see the focus-tint finding above.

### FAIL and INSUFFICIENT EVIDENCE share no channel

This is the single most important separation in the product, and it is enforced
structurally rather than by good intentions:

| Channel | FAIL | INSUFFICIENT EVIDENCE |
|---|---|---|
| Glyph | cross ✕ | hollow ring ○ |
| Fill | flat Field Paper | 45° hatch |
| Border | 5px solid left edge | dotted, all round |
| Colour | Seal Vermilion | Slate Void |

Four channels, four differences. There is no viewing condition — greyscale, glare,
colour-vision deficiency, a cracked panel — in which one degrades into the other.

**"We could not read it" and "it is not there" are different findings with different
legal consequences.** FAIL asserts something about the package and can support
enforcement. INSUFFICIENT EVIDENCE asserts something about our reading of the package and
cannot. Collapsing them is a wrongful-flag liability, not a style choice.

### The remedy is the tell, before the label is

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

`PASS`, `REVIEW`, `POTENTIAL VIOLATION`. They render at banner scale, one per screen, and
are **distinguished by rule weight so a verdict can never be mistaken for a field state**:

| Verdict | Rule | Weight on the page |
|---|---|---|
| PASS | solid rule | ordinary |
| REVIEW | dashed rule | ordinary |
| POTENTIAL VIOLATION | double rule | the heaviest object on the screen |

Rule weight is the channel because field-state chips do not use rules at all. A banner
and a chip are different kinds of object before they are different colours.

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

## Interaction

- **Row focus is a 4px Gazette Ink left bar plus a shift to the focus tint. Never a
  shadow lift.** A ledger is a ruled document. A row that lifts off the page is a card
  pretending to be a row, and the ledger has no cards.
- **48px minimum touch target**, everywhere, including ledger rows and queue rows.
- **Keyboard focus is always visible.** `:focus-visible` rings render instantly and are
  never animated — a ring that fades in is a ring the officer's eye has already left.
- **No meaning carried by hover alone.** Hover is not available on the primary device.
  Anything hover reveals must also be present, or reachable by focus and by tap.
- **No state carried by a colour dot.** A dot is one channel, and one channel is never
  enough. See the five-state table.
- **`prefers-reduced-motion: reduce` is respected.** Spatial motion collapses to an
  opacity change of 150ms or less.
- **The machine's column and the officer's column never share a background.** What the
  system found and what the officer decides are different kinds of claim, and the screen
  says so before it says anything else.

## Layout

- **Phone 390 first, desktop 1280 second**, for the officer verdict surface. The
  inspector is standing up.
- **The review queue is desktop-only in intent** — it exists to clear forty inspections,
  which is a seated task.
- **The masthead is permanent furniture, not a toast.** Inspection id, rule-set version,
  capture timestamp and the offline marker are on screen at all times. An officer must
  never have to remember whether they saw an offline warning three minutes ago.
- **Ruled rows, no cards.** Hairline rules, no shadows, no rounded surfaces floating on
  the ground.
- Tailwind's 4px spacing scale.

---

## Implementation conventions

- **Tailwind only.** No CSS-in-JS, no `styled-components`, no CSS Modules. A shared class
  only when three or more components repeat it verbatim, and then as an `@apply` rule.
- **No component library.** No shadcn, no Radix, no MUI. Components are built per ticket.
- **No new dependencies.** Every addition is a package a teammate installs and CI builds.
- **Tokens, not raw values.** Colours come from `theme.colors` in `tailwind.config.js`
  and type from `theme.fontSize`. A raw hex in a component is a bug.
- **No `any`.** Strict mode is on. A shape that would need `any` belongs in
  `contracts/` on the backend and reaches the frontend through
  `src/services/generated/` — never hand-waved on this side.
- **Shared layout, independent trees.** `src/layout/AppShell.tsx` is the only piece
  shared between the two surfaces, and it is owned jointly. The officer verdict screens
  carry their own masthead — the inspection id, rule-set version and offline marker are
  verdict furniture, not generic chrome — and so do not mount `AppShell`. Restyling
  shared chrome to serve one surface would change the other surface's owner's screens,
  which is the coupling `/officer/*` and `/admin/*` are kept separate to prevent.
