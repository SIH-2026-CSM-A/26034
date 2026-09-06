# fnt

PCCS frontend. React 18 + TypeScript (strict) + Vite + Tailwind v3 + React Router v6,
PWA-installable via `vite-plugin-pwa`.

```
install: npm install
dev:     npm run dev
build:   npm run build
```

## Layout

```
src/
  layout/AppShell.tsx         shared chrome, used by the admin surface
  officer/OfficerRoutes.tsx   independent route tree, mounted at /officer/*
  officer/ReviewQueue.tsx     /officer/queue — dense queue, desktop
  officer/VerdictDetail.tsx   /officer/verdicts/:subjectRef — phone 390 first
  officer/components/         state chip, verdict banner, capture register
  admin/AdminRoutes.tsx       independent route tree, mounted at /admin/*
  fixtures/                   pre-integration data — see its README
  services/generated/         machine-written API client — never hand-edit
  App.tsx                     mounts the two route trees side by side
```

The officer verdict screens do not mount `AppShell`: the masthead they carry is verdict
furniture, not generic chrome, and `AppShell` is shared with the admin surface.

`/officer/*` and `/admin/*` are separate route trees on purpose — see `AGENTS.md` on
module ownership (different owners land on each surface) and `ARCHITECTURE.md`. Don't
merge them into one tree with role-based conditional rendering.

See `DESIGN.md` for palette, type scale, spacing, and the verdict-display rule.

Two officer screens are built (26034-FNT-002) against fixtures in `src/fixtures/`. No
API calls yet — they are wired to the real endpoint at `PIP-002`, at the two route
components and nowhere else.

Fonts are self-hosted from `public/fonts/` (SIL OFL). There is no webfont CDN: the
officer surface has to render with the venue network dead.
