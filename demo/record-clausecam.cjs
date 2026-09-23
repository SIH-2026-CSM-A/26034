// Records the ClauseCam walkthrough against the deployed app, 1280x800, start to finish, with
// Playwright's own video recorder. Real browser, real network, real OCR, real writes. No
// stubbed responses, no synthetic clicks on anything not on screen. A step that fails is
// logged in the index and the recording carries on; nothing is edited out.
//
//   NODE_PATH=$(npm root -g) node demo/record-clausecam.cjs
//
// Signs in through the published Demo access panels (demo-officer, demo-vendor). The officer's
// determination is a write, so demo-officer's read_only must be lifted on the deployment for
// the pass and restored after it. Every write targets a scan this pass creates; seeded rows
// are never acted on.
'use strict'
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE = process.env.PCCS_URL || 'https://locally-progress-major-bare.trycloudflare.com'
const REPO = path.resolve(__dirname, '..')
const PHOTOS = {
  parle56: '/mnt/c/Users/drona/Downloads/parle-g-back.jpg',
  parle65: path.join(REPO, 'datasets/raw/food/food_parle_g_gluco_biscuits_65g/food_parle_g_gluco_biscuits_65g_001.jpg'),
  mdh: '/mnt/c/Users/drona/Downloads/mdh-kitchen-king-coin.jpg',
  // ffmpeg -loop 1 -i <parle65> -t 4 -r 15 -vf format=yuv420p demo/.raw/parle65.y4m
  // Native 500×500, unscaled: upscaled to 1280 the quality gate refuses it as too blurred.
  parle65y4m: path.join(__dirname, '.raw/parle65.y4m'),
}
// See record.cjs: flat, this mark measures 102.3 ± 10.2 cm², across the 100 cm² Table-I band
// edge, so Table-I is REVIEW_REQUIRED. Do not tighten it to force a PASS.
const MDH_MARK = { x: 86, y: 38, width: 776, height: 1207 }
const viewport = { width: 1280, height: 800 }
const OUT = __dirname
const tag = '1280x800'
const videoPath = path.join(OUT, 'clausecam-walkthrough.webm')
const indexPath = path.join(OUT, 'clausecam-walkthrough-index.md')
let token = null

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let t0 = Date.now()
const lines = []
function stamp() {
  const s = Math.round((Date.now() - t0) / 1000)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
function log(text) {
  const line = `- \`${stamp()}\` ${text}`
  lines.push(line)
  console.log(line)
  fs.writeFileSync(indexPath, header() + lines.join('\n') + '\n')
}
function header() {
  return `# ClauseCam walkthrough — ${tag}\n\nVideo: \`clausecam-walkthrough.webm\` · target ${BASE} · started ${new Date(t0).toISOString()}\n\nTimestamps are seconds from the start of the recording.\n\n`
}

async function api(p, opts = {}) {
  const r = await fetch(BASE + '/api' + p, opts)
  if (!r.ok) throw new Error(`${p} -> ${r.status} ${await r.text()}`)
  return r.json()
}
async function waitScanComplete(token, id, timeoutMs = 10 * 60 * 1000) {
  const start = Date.now()
  for (;;) {
    const d = await api(`/scans/${id}`, { headers: { authorization: `Bearer ${token}` } })
    if (d.status !== 'processing') return d
    if (Date.now() - start > timeoutMs) throw new Error('scan still processing after 10 min')
    await sleep(2000)
  }
}

async function smoothTo(page, locator) {
  await locator.first().evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  await sleep(900)
}
const fieldSummary = (d) =>
  d.findings.map((f) => `${f.field} ${f.rule_snapshot?.clause_ref ?? ''}=${f.state}`).join('; ')

async function step(name, fn) {
  log(`**${name}**`)
  try {
    await fn()
  } catch (e) {
    log(`FAILED — ${name}: ${String(e.message || e).split('\n')[0]}`)
  }
}


;(async () => {
  // The vendor surface is camera-only (getUserMedia). Headless Chromium has no camera, so
  // its fake capture device plays the vendor photograph: the same frame a phone held over
  // the packet would see. Stated in the index.
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-video-capture=${PHOTOS.parle65y4m}`],
  })
  const ctx = await browser.newContext({
    viewport,
    recordVideo: { dir: path.join(OUT, '.raw'), size: viewport },
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
    serviceWorkers: 'block',
    permissions: ['camera'],
  })
  const page = await ctx.newPage()
  t0 = Date.now()
  page.setDefaultTimeout(30000)
  const pageErrors = []
  page.on('pageerror', (e) => pageErrors.push(`${stamp()} ${e.message}`))
  page.on('response', (r) => {
    if (r.url().includes('/api/auth/token') && r.status() === 200) r.json().then((d) => (token = d.access_token)).catch(() => {})
  })

  await step('1 The opening on the root', async () => {
    await page.goto(BASE + '/')
    await sleep(3200)
  })
  await step('2 The four ways in', async () => {
    const links = await page.getByRole('navigation', { name: 'Ways in' }).getByRole('link').allInnerTexts()
    log(`ways in: ${links.map((l) => l.split('\n')[0]).join(' · ')}`)
    await sleep(5000)
  })
  await step('3 /login and its Demo access panel', async () => {
    await page.getByRole('link', { name: /^Officer/ }).click()
    await page.waitForURL(/\/login$/)
    const panel = page.locator('section', { has: page.getByRole('heading', { name: 'Demo access' }) })
    await smoothTo(page, panel)
    log(`panel: ${(await panel.innerText()).replace(/\s+/g, ' ')}`)
    await sleep(5000)
  })
  await step('4 One-click sign-in as demo-officer', async () => {
    await page.getByRole('button', { name: 'Sign in as this user' }).click()
    await page.waitForURL(/\/officer\/queue/)
  })
  await step('5 The queue', async () => {
    await page.getByText(/of \d+ inspections/).waitFor()
    log(`queue: ${await page.getByText(/of \d+ inspections/).innerText()}`)
    await sleep(6000)
  })
  async function fillMdhForm() {
    await page.setInputFiles('#scan-file', PHOTOS.mdh)
    await page.getByRole('heading', { name: 'Mark the principal display panel' }).waitFor()
    await page.getByText(/No panel marked/).waitFor()
    await sleep(1500)
    await page.selectOption('#calibration-method', 'reference_object')
    await sleep(700)
    await page.selectOption('#reference-type', 'coin_10')
    await sleep(700)
    await page.selectOption('#product-category', 'food')
    await sleep(1200)
  }
  async function submitAndWait(label) {
    const started = Date.now()
    await smoothTo(page, page.getByRole('button', { name: 'Submit scan for inspection' }))
    await page.getByRole('button', { name: 'Submit scan for inspection' }).click()
    await page.getByText('Inspection reference').waitFor({ timeout: 10 * 60 * 1000 })
    const id = (await page.getByText('Inspection reference').locator('..').innerText()).match(/[0-9a-f-]{36}/)?.[0]
    log(`${label}: evaluated in ${Math.round((Date.now() - started) / 1000)} s (scan ${id ? id.slice(0, 8) : '?'})`)
    await sleep(5000)
    const measurements = page.locator('[data-testid="measurements"]')
    await smoothTo(page, measurements)
    log(`measurements: ${(await measurements.innerText()).replace(/\s+/g, ' ')}`)
    if (id) {
      const d = await api(`/scans/${id}`, { headers: { authorization: `Bearer ${token}` } })
      const t1 = d.findings.find((f) => f.field === 'NET_QUANTITY' && /Table-I/.test(f.rule_snapshot?.clause_ref || ''))
      if (t1) log(`Table-I: ${t1.state} · observed ${t1.observed_value} · expected ${t1.expected_value} · ${t1.reason}`)
    }
    return id
  }

  await step('6 A scan, capture to verdict: the MDH carton with a ₹10 coin, Food, coin_10', async () => {
    await page.goto(BASE + '/officer/new')
    await page.waitForSelector('#scan-file')
    await sleep(2000)
    await fillMdhForm()
    const surface = page.getByRole('img', { name: /Drag over the principal display panel/ })
    await surface.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    await sleep(1500)
    const img = surface.locator('img')
    const g = await img.evaluate((el) => {
      const b = el.getBoundingClientRect()
      const scale = Math.min(b.width / el.naturalWidth, b.height / el.naturalHeight)
      const w = el.naturalWidth * scale
      const h = el.naturalHeight * scale
      return { left: b.left + (b.width - w) / 2, top: b.top + (b.height - h) / 2, scale, nw: el.naturalWidth, nh: el.naturalHeight, w, h }
    })
    const x0 = g.left + MDH_MARK.x * g.scale
    const y0 = g.top + MDH_MARK.y * g.scale
    const x1 = g.left + (MDH_MARK.x + MDH_MARK.width) * g.scale
    const y1 = g.top + (MDH_MARK.y + MDH_MARK.height) * g.scale
    log(`photograph ${g.nw}×${g.nh} drawn at ${Math.round(g.w)}×${Math.round(g.h)} px; dragging (${Math.round(x0)},${Math.round(y0)}) → (${Math.round(x1)},${Math.round(y1)})`)
    await page.mouse.move(x0, y0)
    await page.mouse.down()
    await page.mouse.move(x1, y1, { steps: 40 })
    await sleep(400)
    await page.mouse.up()
    await page.getByText(/Panel marked:/).waitFor()
    log(`caption: ${await page.getByText(/Panel marked:/).innerText()}`)
    await sleep(4000)
  })
  let scanId = null
  await step('6 Submit and wait out the real OCR and evaluation', async () => {
    scanId = await submitAndWait('marked')
    await sleep(8000)
  })
  await step('7 Applicability (category classification)', async () => {
    await page.getByRole('link', { name: /Open review ledger/ }).click()
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    const cat = page.locator('section[aria-label="Category classification"]')
    await cat.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    log(`applicability (category classification): ${(await cat.innerText()).replace(/\s+/g, ' ').slice(0, 300)}`)
    await sleep(7000)
  })
  await step('8 Each clause-cited finding', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'Findings' }))
    if (scanId) {
      const d = await api(`/scans/${scanId}`, { headers: { authorization: `Bearer ${token}` } })
      log(`verdict ${d.verdict}; findings: ${fieldSummary(d)}`)
    }
    await sleep(4000)
    await readThroughSection(page, page.locator('li', { hasText: 'principal display panel area' }), 4500)
  })
  await step('9 The band-edge REVIEW: Table-I, both uncertainties named', async () => {
    const row = page.locator('li', { hasText: 'principal display panel area' }).first()
    await smoothTo(page, row)
    const rowText = (await row.innerText()).replace(/\s+/g, ' ')
    log(`ledger row: ${rowText}`)
    if (!/REVIEW.?REQUIRED/i.test(rowText)) log('UNEXPECTED — the Table-I row is not REVIEW_REQUIRED')
    await sleep(20000)
    await readThroughSection(page, page.locator('footer'), 3500)
  })
  await step("10 The officer's actions: record a determination on this pass's own scan", async () => {
    await page.locator('footer button[aria-controls="determination-sheet"]').click()
    await page.getByRole('button', { name: 'Confirm', exact: true }).waitFor()
    await sleep(3000)
    await page.getByRole('button', { name: 'Confirm', exact: true }).click()
    await sleep(1500)
    await page.fill('#review-note', 'Table-I held for officer review: the panel area straddles the 100 cm² band edge at this precision. Re-measure on site.')
    await sleep(3000)
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/review') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Submit determination' }).click(),
    ])
    log(`POST /scans/${(scanId || '?').slice(0, 8)}/review -> ${resp.status()}`)
    await page.getByText('REVIEW RECORDED').waitFor()
    log(`determination: ${(await page.getByText('REVIEW RECORDED').locator('..').innerText()).replace(/\s+/g, ' ')}`)
    await sleep(7000)
  })
  await step('11 The report with its SHA-256', async () => {
    // Collapse the determination sheet so the fixed footer does not cover the report.
    await page.locator('footer button[aria-controls="determination-sheet"]').click()
    await sleep(1200)
    const section = page.locator('section[aria-labelledby="evidence-report"]')
    await section.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    await sleep(3000)
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/evidence/report') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Generate evidence report' }).click(),
    ])
    log(`POST /scans/${(scanId || '?').slice(0, 8)}/evidence/report -> ${resp.status()} ${resp.headers()['content-type']}`)
    const sha = page.getByTestId('report-sha256')
    await sha.waitFor()
    await section.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    log(`SHA-256 on screen: ${(await sha.innerText()).trim()}`)
    await sleep(14000)
  })
  await step('12 The ward map', async () => {
    await page.goto(BASE + '/officer/dashboard')
    const h = page.getByRole('heading', { name: 'Where scans were submitted' })
    await h.waitFor({ timeout: 60000 })
    await sleep(2500)
    await smoothTo(page, h)
    await sleep(4000)
    for (const ward of ['Ward 98 Ameerpet', 'Ward 91 Khairatabad']) {
      await page.locator(`path[aria-label^="${ward}"]`).hover()
      await sleep(700)
      const readout = page.locator('p[aria-live="polite"]', { hasText: /Ward/ }).first()
      if (await readout.count()) log(`readout: ${(await readout.innerText()).replace(/\s+/g, ' ')}`)
      await sleep(4000)
    }
  })
  await step('13 The clause breakdown', async () => {
    const h = page.getByRole('heading', { name: 'Rule clause breakdown' })
    await smoothTo(page, h)
    log(`clause breakdown: ${(await h.locator('..').locator('..').innerText()).replace(/\s+/g, ' ').slice(0, 300)}`)
    await sleep(8000)
  })
  await step('14 Officer sign-out', async () => {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
    await sleep(1500)
    await page.getByRole('button', { name: 'Sign out' }).click()
    await page.waitForURL(/\/login$/)
    await sleep(3500)
  })
  await step('15 /vendor/login and its Demo access panel', async () => {
    await page.goto(BASE + '/vendor/login')
    const panel = page.locator('section', { has: page.getByRole('heading', { name: 'Demo access' }) })
    await smoothTo(page, panel)
    log(`panel: ${(await panel.innerText()).replace(/\s+/g, ' ')}`)
    await sleep(5000)
    await page.getByRole('button', { name: 'Sign in as this user' }).click()
    await page.waitForURL((u) => /\/vendor\/?$/.test(u.pathname))
    await page.locator('video[aria-label="Live camera view"]').waitFor()
    await sleep(3000)
  })
  let vendorScanId = null
  await step('16 A vendor self-check', async () => {
    await page.locator('#vendor-shutter:not([disabled])').click()
    await page.getByRole('img', { name: 'The photograph you just took' }).waitFor()
    log('vendor capture: shutter on the live camera view (Chromium fake capture device playing the Parle-G 65 g photograph)')
    await sleep(3500)
    const started = Date.now()
    await page.getByRole('button', { name: 'Check this package' }).click()
    await page.waitForURL(/\/vendor\/scans\//)
    vendorScanId = page.url().split('/').pop()
    await page.getByText(/rule set/).waitFor({ timeout: 10 * 60 * 1000 })
    log(`OCR + evaluation took ${Math.round((Date.now() - started) / 1000)} s (scan ${vendorScanId.slice(0, 8)})`)
    await sleep(5000)
    const routed = page.getByText(/Routed to the/)
    if (await routed.count()) log(`routing: ${(await routed.innerText()).replace(/\s+/g, ' ')}`)
    await readThroughSection(page, page.getByRole('link', { name: 'Check another package' }), 3500)
    await sleep(3000)
  })
  let consumerScanId = null
  await step('17 The consumer surface: a Parle-G 56 g back panel, no sign-in', async () => {
    await page.goto(BASE + '/consumer')
    await page.waitForSelector('#consumer-photo')
    await sleep(2500)
    await page.setInputFiles('#consumer-photo', PHOTOS.parle56)
    await page.waitForFunction(() => {
      const t = document.body.innerText
      return t.includes('Barcode') && !t.includes('reading…')
    }, null, { timeout: 60000 })
    await sleep(3500)
    const started = Date.now()
    await page.getByRole('button', { name: 'Check this label' }).click()
    await page.waitForURL(/\/consumer\/scans\//)
    consumerScanId = page.url().split('/').pop()
    await page.getByText(/rule set/).waitFor({ timeout: 10 * 60 * 1000 })
    log(`OCR + evaluation took ${Math.round((Date.now() - started) / 1000)} s (scan ${consumerScanId.slice(0, 8)})`)
    await sleep(6000)
    const h = page.getByRole('heading', { name: 'What the rules ask for on a label' })
    await smoothTo(page, h)
    await sleep(6000)
    await readThroughSection(page, page.getByRole('heading', { name: 'What other shoppers reported' }), 3500)
    await sleep(5000)
  })
  await step('18 Sign-out (vendor)', async () => {
    await page.goto(BASE + '/vendor')
    await page.getByRole('button', { name: 'Sign out' }).click()
    await page.waitForURL(/\/vendor\/login/)
    await sleep(3500)
  })

  const runtimeMs = Date.now() - t0
  log(`end of recording — ${Math.round(runtimeMs / 1000)} s`)
  await ctx.close()
  fs.renameSync(await page.video().path(), videoPath)
  await browser.close()
  fs.appendFileSync(
    indexPath,
    `\nRuntime (recording start to close): **${(runtimeMs / 1000).toFixed(1)} s**\n` +
      `Scans created: officer ${scanId || '-'}, vendor ${vendorScanId || '-'}, consumer ${consumerScanId || '-'}\n` +
      (pageErrors.length ? `\nPage errors:\n${pageErrors.map((e) => `- ${e}`).join('\n')}\n` : '\nPage errors: none\n'),
  )
  console.log('video', videoPath)
})().catch((e) => {
  console.error(e)
  process.exit(1)
})

/** Scroll from the current position down to `until`, in readable steps. */
async function readThroughSection(page, until, stepMs = 2600) {
  const step = Math.round(viewport.height * 0.7)
  for (let i = 0; i < 12; i++) {
    const top = await until.first().evaluate((el) => el.getBoundingClientRect().top)
    if (top < viewport.height * 0.9) break
    await page.evaluate((s) => window.scrollBy({ top: s, behavior: 'smooth' }), step)
    await sleep(stepMs)
  }
}
