# DESIGN.md — fnt

Design conventions for the PCCS frontend. Applies to both the officer surface
(`src/officer/`) and the admin surface (`src/admin/`). This is conventions, not a
component library — no screens exist yet (see TODO.md).

---

## Verdict display — read this before building any screen

Verdicts are `PASS`, `REVIEW`, `POTENTIAL VIOLATION` (see `AGENTS.md`). A field-level
state, `INSUFFICIENT_EVIDENCE`, is separate again — "we could not read it" is not
"it is not there," and the UI must never blur that distinction into a fourth shade of
the same three colours.

**Colour alone must never carry verdict meaning.** This tool is read by inspectors in
the field: fluorescent-lit counters, midday glare on a phone screen, cheap panels with
washed-out saturation, and a share of colour-vision-deficient users. Every one of those
conditions defeats colour-only signalling. So:

- Every verdict renders with **three things together**: an icon, a text label, and a
  colour. Never fewer than two. Colour is decoration on top of the other two, not a
  substitute for either.
- The three verdicts get visually distinct icons, not tinted copies of one shape:
  - `PASS` — a check mark.
  - `REVIEW` — a triangle with an exclamation mark.
  - `POTENTIAL VIOLATION` — a filled octagon with an exclamation mark (echoes a stop
    sign — deliberately the most alarming shape in the set).
  - `INSUFFICIENT_EVIDENCE` — a question mark in a circle, kept visually distinct from
    all three verdict icons so it can never be misread as a fourth verdict.
- The text label is never abbreviated to a single letter or dropped on narrow layouts.
  If space is tight, wrap the label — don't hide it and keep only the icon or colour.
- **Test**: a screenshot desaturated to greyscale must still let a reader tell every
  state apart at a glance, from shape and text alone. Run this check by eye before any
  verdict-rendering component ships. If you can't tell `REVIEW` from `POTENTIAL
  VIOLATION` in greyscale, the component isn't done.

### Verdict tokens

Defined in `tailwind.config.js` under `colors.verdict`. These are the only sanctioned
colours for verdict UI — don't reach for a raw Tailwind colour (`red-500`, etc.) on a
verdict badge, and don't add a new verdict colour without updating this table.

| State | Token | Hex | Icon |
|---|---|---|---|
| PASS | `verdict-pass` | `#0F7B3C` | check mark |
| REVIEW | `verdict-review` | `#B75B00` | triangle-exclamation |
| POTENTIAL VIOLATION | `verdict-violation` | `#B3261E` | filled octagon-exclamation |
| INSUFFICIENT_EVIDENCE | `verdict-insufficient` | `#5B5F66` | circled question mark |

All four pass WCAG AA contrast (4.5:1) against both `#FFFFFF` and the `bg-slate-50`
page background used by `AppShell`.

---

## Palette

Everything outside verdict colours comes from Tailwind's default `slate` scale plus
the `verdict` tokens above. No custom greys, no second grey scale — one is enough for
an internal tool.

- Page background: `slate-50`
- Surface / card background: `white`
- Borders: `slate-200`
- Primary text: `slate-900`
- Secondary text: `slate-500`

## Type scale

Default Tailwind type scale (`text-xs` through `text-3xl`), no custom font sizes.
System font stack (`system-ui, "Segoe UI", Roboto, sans-serif`) — no webfont, so there
is no font-load flash on a slow venue network.

- Page/section titles: `text-lg font-semibold`
- Body text: `text-sm`
- Secondary/meta text: `text-sm text-slate-500`

## Spacing

Tailwind's default spacing scale, used in multiples of 4px (`p-4`, `gap-2`, etc.). No
custom spacing tokens.

## Component conventions

- **Tailwind only.** No CSS-in-JS, no `styled-components`, no CSS Modules. Utility
  classes in JSX; a shared class only when three or more components repeat it
  verbatim, and then as a `@apply` rule, not a runtime style object.
- **No component library.** Buttons, inputs, cards, etc. are built as needed per
  ticket, styled directly with Tailwind. Don't reach for shadcn/Radix/MUI without a
  separate decision — this scaffold ticket doesn't add one.
- **Shared layout, independent trees.** `src/layout/AppShell.tsx` is the only piece
  shared between the officer and admin surfaces. It takes `children`, not an
  `<Outlet />`, so each surface mounts it explicitly from its own route tree — see
  `ARCHITECTURE.md` and `AGENTS.md` on why `/officer/*` and `/admin/*` stay
  structurally independent (different owners, no coupling).
- **No `any`.** TypeScript strict mode is on (`tsconfig.app.json`). A type that would
  need `any` to avoid modeling a shape belongs in `contracts/` on the backend side,
  surfaced through `src/services/generated` once that ticket lands — not hand-waved
  away on the frontend.
