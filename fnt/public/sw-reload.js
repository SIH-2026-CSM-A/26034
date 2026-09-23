/*
 * Imported into the generated service worker (vite.config.ts, workbox.importScripts).
 *
 * The generated worker already skips waiting and claims clients, so a new build takes
 * control within seconds of a returning visitor's first load. But that first load was
 * served by the previous worker, from the previous build, and nothing in that old page
 * knows to reload. This runs in the new worker, so it does: on activation after an
 * update, it reloads the visible tab onto the new build.
 *
 * Only on an update, never on the first install, which serves the current build already.
 * Only the visible tab: a tab in the background may hold a half-filled form, and it will
 * pick up the new build on its own next load, as it did before this existed.
 */
let isUpdate = false

self.addEventListener('install', () => {
  isUpdate = Boolean(self.registration.active)
})

self.addEventListener('activate', (event) => {
  if (!isUpdate) return
  event.waitUntil(
    (async () => {
      // A client must be controlled by this worker before it can be navigated.
      await self.clients.claim()
      const tabs = await self.clients.matchAll({ type: 'window' })
      // Started, not awaited. The reload's own request is served by this worker, and a
      // worker serves nothing until its activate event settles: awaiting the navigation
      // here would deadlock, and the tab would hang instead of reloading.
      for (const tab of tabs) {
        if (tab.visibilityState === 'visible') tab.navigate(tab.url).catch(() => undefined)
      }
    })(),
  )
})
