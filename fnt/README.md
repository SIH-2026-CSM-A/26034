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
  layout/AppShell.tsx     shared chrome, used by both surfaces
  officer/OfficerRoutes.tsx   independent route tree, mounted at /officer/*
  admin/AdminRoutes.tsx       independent route tree, mounted at /admin/*
  services/generated/     machine-written API client — see its README, never hand-edit
  App.tsx                 mounts the two route trees side by side
```

`/officer/*` and `/admin/*` are separate route trees on purpose — see `AGENTS.md` on
module ownership (different owners land on each surface) and `ARCHITECTURE.md`. Don't
merge them into one tree with role-based conditional rendering.

See `DESIGN.md` for palette, type scale, spacing, and the verdict-display rule.

This is a route shell (26034-FNT-001) — no screens, no API calls yet. See `TODO.md`
for what's next.
