# fnt

**Owner:** @Abhiram-0910

Frontend. Empty on purpose — scaffolding the Vite project is a separate ticket, and
doing it here would put a package manager and a lockfile under someone who hasn't
picked them yet.

When it lands it follows the T3 frontend layout: `src/components`, `src/pages`,
`src/hooks`, `src/services`, `src/store`, `src/utils`, `src/styles`. It talks to the
backend only through `src/services` — no `fetch` inside a component.
