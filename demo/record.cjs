// Records the PCCS demo against the live tunnel with Playwright's own video recorder.
// Real browser, real network, real OCR. No stubbed responses, no synthetic clicks on
// anything that is not on screen. A step that fails is logged in the index and the
// recording carries on; nothing is edited out.
//
//   PCCS_OFFICER_PASSWORD=… PCCS_VENDOR_PASSWORD=… NODE_PATH=$(npm root -g) node demo/record.cjs phone     # 390x844
//   PCCS_OFFICER_PASSWORD=… PCCS_VENDOR_PASSWORD=… NODE_PATH=$(npm root -g) node demo/record.cjs desktop   # 1280x800
'use strict'
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE = process.env.PCCS_URL || 'https://locally-progress-major-bare.trycloudflare.com'
// Credentials come from the environment, never from this file.
const OFFICER = { username: process.env.PCCS_OFFICER_USER || 'inspector1', password: process.env.PCCS_OFFICER_PASSWORD }
const VENDOR = { username: process.env.PCCS_VENDOR_USER || 'balaji-kirana', password: process.env.PCCS_VENDOR_PASSWORD }
if (!OFFICER.password || !VENDOR.password) {
  console.error('set PCCS_OFFICER_PASSWORD and PCCS_VENDOR_PASSWORD')
  process.exit(2)
}
const REPO = path.resolve(__dirname, '..')
const PHOTOS = {
  // Consumer act, first product: a close capture of a Parle-G 56 g back panel. Its
  // INGREDIENTS line reads and carries INS codes, and 8901719100015 is this packet's barcode.
  parle56: '/mnt/c/Users/drona/Downloads/parle-g-back.jpg',
  // Vendor act: the 65 g corpus Parle-G.
  parle65: path.join(REPO, 'datasets/raw/food/food_parle_g_gluco_biscuits_65g/food_parle_g_gluco_biscuits_65g_001.jpg'),
  // Consumer act, second product, and the measurement act: the MDH carton with a ₹10 coin.
  mdh: '/mnt/c/Users/drona/Downloads/mdh-kitchen-king-coin.jpg',
}
const SAFE_ID = '8901719100015'
const UNSAFE_ID = '8901725113320'
// The officer's mark over the MDH carton face, in the photograph's own pixels: just inside
// the red carton edge (red spans x 73–872, y 24–1262). Flat (#172) it measures
// 102.3 ± 10.2 cm², an interval across the 100 cm² Table-I band edge, and the character
// height 2.61 ± 0.13 mm spans the 2.5 mm requirement, so Table-I is REVIEW_REQUIRED (#174).
// That refusal is the point of the closing act. Do not tighten the mark to force a PASS.
const MDH_MARK = { x: 86, y: 38, width: 776, height: 1207 }

const PASSES = {
  phone: { width: 390, height: 844 },
  desktop: { width: 1280, height: 800 },
}
const passName = process.argv[2]
const viewport = PASSES[passName]
if (!viewport) {
  console.error('usage: node record.cjs phone|desktop')
  process.exit(2)
}
const OUT = __dirname
const tag = `${viewport.width}x${viewport.height}`
const videoPath = path.join(OUT, `pccs-demo-${tag}.webm`)
const indexPath = path.join(OUT, `pccs-demo-${tag}-index.md`)

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
  return `# PCCS demo recording — ${tag}\n\nVideo: \`pccs-demo-${tag}.webm\` · target ${BASE} · started ${new Date(t0).toISOString()}\n\nTimestamps are seconds from the start of the recording.\n\n`
}

async function api(p, opts = {}) {
  const r = await fetch(BASE + '/api' + p, opts)
  if (!r.ok) throw new Error(`${p} -> ${r.status} ${await r.text()}`)
  return r.json()
}
async function officerToken() {
  const d = await api('/auth/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(OFFICER).toString(),
  })
  return d.access_token
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
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({
    viewport,
    recordVideo: { dir: path.join(OUT, '.raw'), size: viewport },
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
  })
  const page = await ctx.newPage()
  t0 = Date.now()
  page.setDefaultTimeout(30000)
  const pageErrors = []
  page.on('pageerror', (e) => pageErrors.push(`${stamp()} ${e.message}`))

  // ───────────────────────── 1. CONSUMER ─────────────────────────
  // Two products, two consensus outcomes. The Parle-G packet first, dwelt on in full; then
  // the MDH carton, straight to its verdict and the UNSAFE consensus.
  const consumerScanIds = []
  async function choosePhoto(photo, label) {
    await page.setInputFiles('#consumer-photo', photo)
    await page.waitForFunction(() => {
      const t = document.body.innerText
      return t.includes('Barcode') && !t.includes('reading…')
    })
    const barcodeLine = await page.evaluate(() =>
      [...document.querySelectorAll('p')].map((p) => p.innerText).find((t) => t.startsWith('Barcode')),
    )
    log(`${label} — in-browser barcode read: ${(barcodeLine || '').replace(/\n/g, ' ')}`)
    await sleep(3000)
  }
  async function submitConsumer(label) {
    const started = Date.now()
    await page.getByRole('button', { name: 'Check this label' }).click()
    await page.waitForURL(/\/consumer\/scans\//)
    const id = page.url().split('/').pop()
    consumerScanIds.push(id)
    await page.getByText(/rule set/).waitFor({ timeout: 10 * 60 * 1000 })
    log(`${label} — OCR + evaluation took ${Math.round((Date.now() - started) / 1000)} s (scan ${id.slice(0, 8)})`)
    const verdict = await page.evaluate(() => document.querySelector('main')?.innerText.split('\n').slice(0, 3).join(' | '))
    log(`${label} — verdict banner: ${verdict}`)
    await sleep(6000)
  }
  async function lookUp(id, label) {
    await smoothTo(page, page.getByRole('heading', { name: 'What other shoppers reported' }))
    const preloaded = (await page.getByText(`Identifier ${id}`).count()) > 0
    if (preloaded) {
      log(`consensus for ${id} was already on screen, loaded from the barcode decoded in the browser`)
    } else {
      await page.fill('#product-identifier', id)
      await sleep(800)
      await page.getByRole('button', { name: 'Look up' }).click()
      await page.getByText(`Identifier ${id}`).waitFor()
    }
    const card = await page.getByText(`Identifier ${id}`).locator('..').locator('..').innerText()
    log(`${label}: ${card.replace(/\s+/g, ' ').slice(0, 200)}`)
  }

  await step('1 Consumer — open /consumer, no sign-in', async () => {
    await page.goto(BASE + '/consumer')
    await page.waitForSelector('#consumer-photo')
    await sleep(3500)
  })
  await step('1 Consumer — first product: a Parle-G 56 g back panel', async () => {
    await choosePhoto(PHOTOS.parle56, 'Parle-G')
  })
  await step('1 Consumer — submit and wait out the real OCR', async () => {
    await submitConsumer('Parle-G')
  })
  await step('1 Consumer — the findings, each naming its rule', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'What the rules ask for on a label' }))
    const rows = await page.locator('section', { has: page.getByRole('heading', { name: 'What the rules ask for on a label' }) }).innerText()
    log(`findings block: ${rows.replace(/\s+/g, ' ').slice(0, 600)}…`)
    await readThroughSection(page, page.getByRole('heading', { name: 'Ingredients as declared on the label' }))
  })
  await step('1 Consumer — ingredients verbatim', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'Ingredients as declared on the label' }))
    const ing = await page.locator('section', { has: page.getByRole('heading', { name: 'Ingredients as declared on the label' }) }).innerText()
    log(`ingredients block: ${ing.replace(/\s+/g, ' ')}`)
    await sleep(6000)
  })
  await step('1 Consumer — additive codes with their FSS citations', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'Additive codes in that declaration' }))
    const codes = await page.locator('section', { has: page.getByRole('heading', { name: 'Additive codes in that declaration' }) }).innerText()
    log(`additives block: ${codes.replace(/\s+/g, ' ')}`)
    await readThroughSection(page, page.getByRole('heading', { name: 'Barcode', exact: true }), 3000)
    await sleep(4000)
  })
  await step('1 Consumer — the barcode section', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'Barcode', exact: true }))
    const bc = await page.locator('section', { has: page.getByRole('heading', { name: 'Barcode', exact: true }) }).innerText()
    log(`barcode section: ${bc.replace(/\s+/g, ' ').slice(0, 200)}`)
    await sleep(4500)
  })
  await step(`1 Consumer — ${SAFE_ID}, this packet's own barcode: the published SAFE consensus`, async () => {
    await lookUp(SAFE_ID, 'SAFE consensus')
    await sleep(7000)
  })
  await step('1 Consumer — second product: the MDH Kitchen King carton', async () => {
    await smoothTo(page, page.getByRole('link', { name: 'Check another label' }))
    await sleep(1200)
    await page.getByRole('link', { name: 'Check another label' }).click()
    await page.waitForSelector('#consumer-photo')
    await sleep(2000)
    await choosePhoto(PHOTOS.mdh, 'MDH')
  })
  await step('1 Consumer — submit the carton and wait out the OCR', async () => {
    await submitConsumer('MDH')
  })
  await step(`1 Consumer — look up ${UNSAFE_ID}: the published UNSAFE consensus`, async () => {
    await lookUp(UNSAFE_ID, 'UNSAFE consensus')
    await sleep(7000)
  })

  // ───────────────────────── 2. VENDOR ─────────────────────────
  await step('2 Vendor — sign in as balaji-kirana', async () => {
    await page.goto(BASE + '/vendor/login')
    await page.waitForSelector('#vendor-username')
    await sleep(1500)
    await page.fill('#vendor-username', VENDOR.username)
    await page.fill('#vendor-password', VENDOR.password)
    await sleep(800)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL((u) => /\/vendor\/?$/.test(u.pathname))
    await page.waitForSelector('#vendor-photo')
    await sleep(3500)
  })
  let vendorScanId = null
  await step('2 Vendor — submit a package photograph and wait for the verdict', async () => {
    await page.setInputFiles('#vendor-photo', PHOTOS.parle65)
    await sleep(2500)
    const started = Date.now()
    await page.getByRole('button', { name: 'Check this package' }).click()
    await page.waitForURL(/\/vendor\/scans\//)
    vendorScanId = page.url().split('/').pop()
    await page.getByText(/rule set/).waitFor({ timeout: 10 * 60 * 1000 })
    log(`OCR + evaluation took ${Math.round((Date.now() - started) / 1000)} s (scan ${vendorScanId.slice(0, 8)})`)
    await sleep(5000)
  })
  await step('2 Vendor — the routing line: which officer tier the premises falls under', async () => {
    const routed = page.getByText(/Routed to the/)
    await routed.waitFor({ timeout: 20000 })
    await smoothTo(page, page.getByText('WHAT THIS IS'))
    log(`routing: ${(await routed.innerText()).replace(/\s+/g, ' ')}`)
    await sleep(7000)
    await readThroughSection(page, page.getByRole('link', { name: 'Check another package' }))
  })
  await step('2 Vendor — sign out', async () => {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
    await sleep(1200)
    await page.getByRole('button', { name: 'Sign out' }).click()
    await page.waitForURL(/\/vendor\/login/)
    await sleep(2500)
  })

  // ───────────────────────── 3. OFFICER ─────────────────────────
  await step('3 Officer — sign in as inspector1', async () => {
    await page.goto(BASE + '/login')
    await page.waitForSelector('#username')
    await sleep(1500)
    await page.fill('#username', OFFICER.username)
    await page.fill('#password', OFFICER.password)
    await sleep(800)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL(/\/officer\/queue/)
    await page.getByText(/of \d+ inspections/).waitFor()
    log(`queue: ${await page.getByText(/of \d+ inspections/).innerText()}`)
    await sleep(6000)
  })
  let token = await officerToken()
  await step("3 Officer — the vendor's scan is in this officer's queue (jurisdiction covers the premises)", async () => {
    const row = page.locator(`a[href="/officer/verdicts/${vendorScanId}"]`)
    if ((await row.count()) === 0) throw new Error(`vendor scan ${vendorScanId} is not in inspector1's queue`)
    await smoothTo(page, row)
    log(`top row: ${(await row.innerText()).replace(/\s+/g, ' ')}`)
    await sleep(4000)
    await row.click()
    await page.waitForURL(/\/officer\/verdicts\//)
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    await sleep(5000)
  })
  await step('3 Officer — dwell on the verdict: rule citations and refusals worded as facts about the photograph', async () => {
    await smoothTo(page, page.getByRole('heading', { name: 'Findings' }))
    const d = await api(`/scans/${vendorScanId}`, { headers: { authorization: `Bearer ${token}` } })
    log(`findings: ${fieldSummary(d)}`)
    await readThroughSection(page, page.locator('footer'), 3200)
  })
  let confirmedScanId = null
  await step('3 Officer — confirm the category as Food; the capture is re-evaluated as a new scan', async () => {
    await smoothTo(page, page.getByText('Confirmed Product Category'))
    await sleep(1500)
    await page.selectOption('#select-category', 'food')
    await sleep(1200)
    const before = page.url()
    await page.getByRole('button', { name: 'Confirm and re-evaluate' }).click()
    await page.waitForURL((u) => u.toString() !== before && /\/officer\/verdicts\//.test(u.pathname), { timeout: 60000 })
    confirmedScanId = page.url().split('/').pop()
    log(`new scan ${confirmedScanId.slice(0, 8)}; waiting for its evaluation`)
    const d = await waitScanComplete(token, confirmedScanId)
    await page.reload()
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    log(`confirmed category ${d.product_category}; verdict ${d.verdict}; ${fieldSummary(d)}`)
    await sleep(4000)
    await smoothTo(page, page.getByText('Confirmed Product Category'))
    await sleep(4000)
    await smoothTo(page, page.getByRole('heading', { name: 'Findings' }))
    await sleep(5000)
  })
  // The complaints page lists finalised scans from the newest 50 only, and every pass adds
  // four scans before that step, so the seeded confirmations have long since left the page.
  // The officer therefore confirms a machine POTENTIAL VIOLATION here, on camera, and the
  // complaint below is raised against that confirmation. No automated path finalises a scan.
  let confirmedViolation = null
  await step('3 Officer — a machine POTENTIAL VIOLATION awaiting the officer: record the determination', async () => {
    const recent = await api('/scans?limit=50', { headers: { authorization: `Bearer ${token}` } })
    for (const s of recent.filter((s) => !s.finalised && s.verdict === 'POTENTIAL_VIOLATION')) {
      const d = await api(`/scans/${s.id}`, { headers: { authorization: `Bearer ${token}` } })
      if (d.findings.some((f) => f.state === 'FAIL')) {
        confirmedViolation = d
        break
      }
    }
    if (!confirmedViolation) {
      // Nothing left for the officer to confirm in this window: fall back to one already
      // confirmed, still within the newest 50, so the complaint step has a scan the page lists.
      for (const s of recent.filter((s) => s.finalised && s.verdict === 'POTENTIAL_VIOLATION')) {
        const d = await api(`/scans/${s.id}`, { headers: { authorization: `Bearer ${token}` } })
        if (d.findings.some((f) => f.state === 'FAIL')) {
          confirmedViolation = d
          break
        }
      }
      if (!confirmedViolation) throw new Error('no POTENTIAL_VIOLATION scan with a FAIL finding in the newest 50')
      log(`no unconfirmed POTENTIAL VIOLATION in the newest 50; ${confirmedViolation.id.slice(0, 8)} was confirmed on an earlier pass`)
      return
    }
    await page.goto(BASE + `/officer/verdicts/${confirmedViolation.id}`)
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    log(`scan ${confirmedViolation.id.slice(0, 8)} · machine verdict ${confirmedViolation.verdict} · ${fieldSummary(confirmedViolation)}`)
    await sleep(4000)
    const fail = page.locator('li', { has: page.getByText('FAIL', { exact: true }) }).first()
    await smoothTo(page, fail)
    await sleep(4000)
    await page.locator('footer button[aria-controls="determination-sheet"]').click()
    await page.getByRole('button', { name: 'Confirm', exact: true }).waitFor()
    await sleep(2000)
    await page.getByRole('button', { name: 'Confirm', exact: true }).click()
    await sleep(1500)
    await page.fill('#review-note', 'Confirmed as recommended: the FAIL finding is the machine reading, taken on the evidence as photographed.')
    await sleep(2500)
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/review') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Submit determination' }).click(),
    ])
    log(`POST /scans/${confirmedViolation.id.slice(0, 8)}/review -> ${resp.status()}`)
    await page.getByText('REVIEW RECORDED').waitFor()
    log(`determination: ${(await page.getByText('REVIEW RECORDED').locator('..').innerText()).replace(/\s+/g, ' ')}`)
    confirmedViolation = await api(`/scans/${confirmedViolation.id}`, { headers: { authorization: `Bearer ${token}` } })
    log(`scan now finalised ${confirmedViolation.finalised}, verdict ${confirmedViolation.verdict}`)
    await sleep(6000)
  })
  await step('3 Officer — dashboard: the GHMC choropleth', async () => {
    await page.goto(BASE + '/officer/dashboard')
    await page.getByRole('heading', { name: 'Where scans were submitted' }).waitFor({ timeout: 60000 })
    await sleep(4000)
    await smoothTo(page, page.getByRole('heading', { name: 'Where scans were submitted' }))
    await sleep(3000)
  })
  await step('3 Officer — hover a ward', async () => {
    for (const ward of ['Ward 121 Kukatpally', 'Ward 91 Khairatabad']) {
      const p = page.locator(`path[aria-label^="${ward}"]`)
      await p.hover()
      await sleep(600)
      const readout = await page.locator('p[aria-live="polite"]', { hasText: /Ward/ }).first().innerText()
      log(`readout: ${readout.replace(/\s+/g, ' ')}`)
      await sleep(4500)
    }
    await page.locator('path[aria-label^="Ward 121 Kukatpally"]').click()
    await sleep(3500)
  })
  // Complaint: real values from the real verdict of an officer-confirmed scan.
  let complaintScan = null
  let finding = null
  await step('3 Officer — complaints ledger', async () => {
    // The scan the officer confirmed a moment ago; the complaints page lists it because it is
    // finalised and among the newest 50.
    if (confirmedViolation && confirmedViolation.finalised && confirmedViolation.verdict === 'POTENTIAL_VIOLATION') {
      complaintScan = confirmedViolation
      finding = confirmedViolation.findings.find((f) => f.state === 'FAIL')
    }
    await page.goto(BASE + '/officer/complaints')
    await page.getByRole('button', { name: 'Raise new complaint' }).waitFor()
    await page.getByText('Total escalations').waitFor()
    await sleep(5000)
  })
  let complaintId = null
  await step('3 Officer — raise a complaint from an officer-confirmed POTENTIAL VIOLATION', async () => {
    if (!complaintScan) throw new Error('the officer determination above did not finalise a POTENTIAL_VIOLATION scan')
    const maker = complaintScan.findings.find((f) => f.field === 'NAME_AND_ADDRESS' && f.observed_value)?.observed_value
    await page.getByRole('button', { name: 'Raise new complaint' }).click()
    await page.getByRole('heading', { name: 'Raise manufacturer complaint' }).waitFor()
    await sleep(1500)
    await page.selectOption('#select-scan', complaintScan.id)
    await sleep(700)
    await page.fill('#mfr-name', (maker || 'manufacturer as declared').split(',')[0].slice(0, 80))
    await page.fill('#rule-id', finding.rule_snapshot.rule_id)
    await page.selectOption('#field-select', finding.field)
    await page.fill('#measured-value', finding.observed_value || 'not declared')
    await page.fill('#required-value', finding.expected_value || 'declaration present')
    log(`scan ${complaintScan.id.slice(0, 8)} · ${finding.rule_snapshot.rule_id} · ${finding.field} · observed "${finding.observed_value}" · required "${finding.expected_value}"`)
    await sleep(3000)
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith('/api/complaints') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Submit formal complaint' }).click(),
    ])
    log(`POST /complaints -> ${resp.status()}`)
    if (resp.status() === 201) complaintId = (await resp.json()).id
    await sleep(1500)
    if (complaintId) {
      const thread = page.locator('article', { hasText: complaintId.slice(0, 8) }).first()
      await smoothTo(page, thread)
      log(`thread: ${(await thread.innerText()).replace(/\s+/g, ' ').slice(0, 200)}`)
    }
    await sleep(6000)
  })
  await step('3 Officer — transition it: record the acknowledgement', async () => {
    if (!complaintId) throw new Error('no complaint was raised')
    const thread = page.locator('article', { hasText: complaintId.slice(0, 8) }).first()
    await thread.getByRole('button', { name: 'Record acknowledgement' }).click()
    await page.getByRole('heading', { name: 'Record acknowledged' }).waitFor()
    await sleep(1500)
    await page.fill('#action-note', `Manufacturer notice served on ${new Date().toISOString().slice(0, 10)}; receipt acknowledged by the declared packer.`)
    await sleep(2000)
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/transitions') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Append acknowledged record' }).click(),
    ])
    log(`POST /complaints/${complaintId.slice(0, 8)}/transitions -> ${resp.status()}`)
    await sleep(1500)
    const after = page.locator('article', { hasText: complaintId.slice(0, 8) }).first()
    await smoothTo(page, after)
    log(`thread now: ${(await after.innerText()).replace(/\s+/g, ' ').slice(0, 200)}`)
    await sleep(6500)
  })

  // ───────────────────────── 4. THE MEASUREMENT ─────────────────────────
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
  await step('4 Measurement — /officer/new, the MDH carton with a ₹10 coin, Food, coin_10, NO panel mark', async () => {
    await page.goto(BASE + '/officer/new')
    await page.waitForSelector('#scan-file')
    await sleep(2500)
    await fillMdhForm()
    await smoothTo(page, page.getByRole('heading', { name: 'Mark the principal display panel' }))
    await sleep(3500)
  })
  let unmarkedId = null
  await step('4 Measurement — submit unmarked: Table-I cannot band without a panel area', async () => {
    unmarkedId = await submitAndWait('unmarked')
    await sleep(12000)
  })
  await step('4 Measurement — submit again, this time dragging the panel over the carton face', async () => {
    await page.getByRole('button', { name: 'Submit another scan' }).click()
    await page.waitForSelector('#scan-file')
    await sleep(1500)
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
    await sleep(5000)
  })
  let markedId = null
  await step('4 Measurement — submit marked: Table-I consults both intervals and declines to band', async () => {
    markedId = await submitAndWait('marked')
    await sleep(12000)
  })
  await step('4 Measurement — the marked scan on the review ledger: the Table-I REVIEW_REQUIRED row, both uncertainties named', async () => {
    await page.getByRole('link', { name: /Open review ledger/ }).click()
    await page.getByRole('heading', { name: 'Findings' }).waitFor()
    await sleep(2000)
    const row = page.locator('li', { hasText: 'principal display panel area' }).first()
    await smoothTo(page, row)
    const rowText = (await row.innerText()).replace(/\s+/g, ' ')
    log(`ledger row: ${rowText}`)
    if (!/REVIEW.?REQUIRED/i.test(rowText)) log(`UNEXPECTED — the Table-I ledger row is not REVIEW_REQUIRED`)
    // The longest hold in the recording: the reason names two uncertainties and refuses a verdict.
    await sleep(25000)
  })

  const runtimeMs = Date.now() - t0
  log(`end of recording — ${Math.round(runtimeMs / 1000)} s`)
  await ctx.close()
  const raw = await page.video().path()
  fs.renameSync(raw, videoPath)
  await browser.close()
  fs.appendFileSync(
    indexPath,
    `\nRuntime (recording start to close): **${(runtimeMs / 1000).toFixed(1)} s**\n` +
      `Scans created: consumer ${consumerScanIds.join(' + ') || '-'}, vendor ${vendorScanId || '-'}, category-confirmed ${confirmedScanId || '-'}, unmarked ${unmarkedId || '-'}, marked ${markedId || '-'}; complaint ${complaintId || '-'}\n` +
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
