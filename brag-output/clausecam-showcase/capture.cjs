// Captures the real screens for beats 1 and 2 of the ClauseCam showcase from the deployed
// app, as demo-officer (read-only: this script only reads). Logs video-relative times for
// the cuts in cuts.json. Beat 3 and the closing wordmark come from demo/clausecam-walkthrough.webm.
'use strict'
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const BASE = 'https://locally-progress-major-bare.trycloudflare.com'
const OUT = __dirname
const UNCONFIRMED = '7340fcfe-e108-4036-9505-cec22ef2aacb'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
;(async () => {
  const b = await chromium.launch({ headless: true })
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: path.join(OUT, '.raw'), size: { width: 1280, height: 800 } }, serviceWorkers: 'block' })
  const page = await ctx.newPage()
  const t0 = Date.now(); const cuts = {}
  const mark = (k) => { cuts[k] = (Date.now() - t0) / 1000; console.log(k, cuts[k].toFixed(1)) }
  await page.goto(BASE + '/login')
  await page.getByRole('button', { name: 'Sign in as this user' }).click()
  await page.waitForURL(/\/officer\/queue/)
  await page.getByText(/of \d+ inspections/).waitFor()
  await sleep(1500)
  mark('queue_start')
  await sleep(3000)
  for (let i = 0; i < 6; i++) { await page.evaluate(() => window.scrollBy({ top: 260, behavior: 'smooth' })); await sleep(1300) }
  mark('queue_end')
  const tok = await page.evaluate(() => sessionStorage.getItem('pccs.access_token'))
  const scans = await page.evaluate(async (t) => (await fetch('/api/scans?limit=100', { headers: { authorization: 'Bearer ' + t } })).json(), tok)
  const food = scans.find((s) => s.id.startsWith('cb194e5d')).id
  async function row(id, name) {
    await page.goto(BASE + `/officer/verdicts/${id}`)
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    const r = page.locator('li', { hasText: 'Rule 6(1)(a)' }).filter({ hasText: /sector rule|Food Safety/ }).first()
    await r.evaluate((el) => el.scrollIntoView({ block: 'center' }))
    await sleep(1500)
    mark(name + '_start'); await sleep(8000); mark(name + '_end')
  }
  await row(UNCONFIRMED, 'unconfirmed')
  await page.goto(BASE + `/officer/verdicts/${food}`)
  await page.getByRole('heading', { name: 'Findings' }).waitFor()
  await page.locator('section[aria-label="Category classification"]').evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await sleep(1500)
  mark('category_start'); await sleep(6500); mark('category_end')
  const r = page.locator('li', { hasText: 'Rule 6(1)(a)' }).filter({ hasText: /Food Safety/ }).first()
  await r.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  await sleep(1500)
  mark('food_start'); await sleep(8500); mark('food_end')
  await ctx.close()
  fs.renameSync(await page.video().path(), path.join(OUT, 'capture.webm'))
  fs.writeFileSync(path.join(OUT, 'cuts.json'), JSON.stringify(cuts, null, 2))
  await b.close()
})().catch((e) => { console.error(e); process.exit(1) })
