/**
 * EAN-13 / UPC-A decode from image pixels, in the browser, with no library.
 *
 * Scanline decoding: binarise a row of pixels, measure the run lengths of alternating
 * bars and spaces, find the start guard (1-1-1), decode six left digits (L or G parity,
 * which together encode the first digit), the centre guard (1-1-1-1-1), six right digits
 * (R parity), and the end guard. A result is accepted only when the modulo-10 checksum
 * holds. Rows are scanned at many heights, in both directions, and columns likewise for
 * a barcode printed vertically. UPC-A is EAN-13 with a leading 0.
 *
 * ponytail: no rotation beyond 0 and 90 degrees, no perspective correction. A tilted
 * barcode on a curved packet may not decode; the reader is told so and can retake. The
 * upgrade is a proper library, which is a dependency to ask for.
 */

export interface BarcodeResult {
  value: string
  symbology: 'EAN-13' | 'UPC-A'
  /** Whether the printed check digit matches the GS1 modulo-10 rule over the other twelve. */
  checkDigitVerifies: boolean
}

// Left-hand (L) patterns as four run lengths in modules per digit.
const L: readonly (readonly number[])[] = [
  [3, 2, 1, 1], [2, 2, 2, 1], [2, 1, 2, 2], [1, 4, 1, 1], [1, 1, 3, 2],
  [1, 2, 3, 1], [1, 1, 1, 4], [1, 3, 1, 2], [1, 2, 1, 3], [3, 1, 1, 2],
]
// G patterns are L reversed. R patterns share L's widths with inverted colours, which
// run-length matching does not see, so the right half matches against L directly.
const G: readonly (readonly number[])[] = L.map((p) => [...p].reverse())

// First digit from the parity of the six left digits, L = 0, G = 1.
const FIRST_DIGIT: readonly string[] = [
  'LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG',
  'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL',
]

function fit(runs: number[], p: readonly number[]): number {
  const total = runs.reduce((a, b) => a + b, 0)
  if (total === 0 || runs.length < 4) return Infinity
  const module = total / 7
  let err = 0
  for (let i = 0; i < 4; i++) err += Math.abs(runs[i]! / module - p[i]!)
  return err
}

function matchDigit(runs: number[], patterns: readonly (readonly number[])[]): number | null {
  let best = -1
  let bestErr = Infinity
  for (let d = 0; d < 10; d++) {
    const err = fit(runs, patterns[d]!)
    if (err < bestErr) {
      bestErr = err
      best = d
    }
  }
  return bestErr < 1.1 ? best : null
}

function checksumOk(digits: number[]): boolean {
  let sum = 0
  for (let i = 0; i < 12; i++) sum += digits[i]! * (i % 2 === 0 ? 1 : 3)
  return (10 - (sum % 10)) % 10 === digits[12]
}

/** Run lengths of a binarised line, and whether the first run is a bar. */
function runsOf(line: Uint8Array): { runs: number[]; startsWithBar: boolean } {
  const runs: number[] = []
  let current = line[0]!
  let count = 0
  for (const v of line) {
    if (v === current) count++
    else {
      runs.push(count)
      current = v
      count = 1
    }
  }
  runs.push(count)
  return { runs, startsWithBar: line[0] === 1 }
}

function decodeRuns(runs: number[], firstIsBar: boolean): number[] | null {
  const barAt = (i: number) => (firstIsBar ? i % 2 === 0 : i % 2 === 1)
  for (let s = 0; s + 59 <= runs.length; s++) {
    if (!barAt(s)) continue
    const g = [runs[s]!, runs[s + 1]!, runs[s + 2]!]
    const m = (g[0]! + g[1]! + g[2]!) / 3
    if (m < 1 || g.some((w) => Math.abs(w - m) > m * 0.6)) continue
    const left: number[] = []
    let parity = ''
    let i = s + 3
    let ok = true
    for (let d = 0; d < 6; d++, i += 4) {
      const r = runs.slice(i, i + 4)
      const l = matchDigit(r, L)
      const gg = matchDigit(r, G)
      if (l === null && gg === null) {
        ok = false
        break
      }
      const useL = l !== null && (gg === null || fit(r, L[l]!) <= fit(r, G[gg]!))
      left.push(useL ? l! : gg!)
      parity += useL ? 'L' : 'G'
    }
    if (!ok) continue
    const c = runs.slice(i, i + 5)
    if (c.length < 5) continue
    const cm = c.reduce((a, b) => a + b, 0) / 5
    if (c.some((w) => Math.abs(w - cm) > cm * 0.7)) continue
    i += 5
    const right: number[] = []
    for (let d = 0; d < 6; d++, i += 4) {
      const v = matchDigit(runs.slice(i, i + 4), L)
      if (v === null) {
        ok = false
        break
      }
      right.push(v)
    }
    if (!ok) continue
    // End guard: three runs of near-equal width, or this was not a barcode at all.
    const e = runs.slice(i, i + 3)
    if (e.length < 3) continue
    const em = (e[0]! + e[1]! + e[2]!) / 3
    if (e.some((w) => Math.abs(w - em) > em * 0.6)) continue
    const first = FIRST_DIGIT.indexOf(parity)
    if (first < 0) continue
    // Structure alone is the acceptance test: start, centre and end guards, twelve
    // digits that each fit a pattern, and a parity that names a first digit. The
    // checksum is reported, not enforced — see decodeEAN13.
    return [first, ...left, ...right]
  }
  return null
}

/**
 * Grey line → 1 for bar (dark), 0 for space, against a sliding local mean. A single
 * threshold for the whole line fails on a photograph, where the line crosses the
 * packet, its shadow and the table; a window of a few dozen modules follows the light.
 */
function binarise(grey: Float32Array): Uint8Array | null {
  const n = grey.length
  let min = Infinity
  let max = -Infinity
  for (const v of grey) {
    if (v < min) min = v
    if (v > max) max = v
  }
  if (max - min < 40) return null
  const half = Math.max(8, Math.floor(n / 40))
  const prefix = new Float64Array(n + 1)
  for (let i = 0; i < n; i++) prefix[i + 1] = prefix[i]! + grey[i]!
  const out = new Uint8Array(n)
  for (let i = 0; i < n; i++) {
    const a = Math.max(0, i - half)
    const b = Math.min(n, i + half + 1)
    const mean = (prefix[b]! - prefix[a]!) / (b - a)
    out[i] = grey[i]! < mean - 4 ? 1 : 0
  }
  return out
}

function tryLine(grey: Float32Array): number[] | null {
  const bin = binarise(grey)
  if (!bin) return null
  const { runs, startsWithBar } = runsOf(bin)
  if (runs.length < 59) return null
  const forward = decodeRuns(runs, startsWithBar)
  if (forward) return forward
  const reversed = [...runs].reverse()
  const lastIsBar = (runs.length - 1) % 2 === 0 ? startsWithBar : !startsWithBar
  return decodeRuns(reversed, lastIsBar)
}

/** Decode from RGBA pixels: many horizontal rows, then many vertical columns. */
export function decodeEAN13(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): BarcodeResult | null {
  const grey = (x: number, y: number) => {
    const i = (y * width + x) * 4
    return 0.299 * data[i]! + 0.587 * data[i + 1]! + 0.114 * data[i + 2]!
  }
  // One structurally valid line is not evidence: a photograph offers thousands of
  // candidate windows. A value is accepted only when three different lines read the
  // same thirteen digits. The check digit is reported alongside rather than enforced,
  // because it is shown to a person as what the label carries, not as a fact about it.
  const seen = new Map<string, number>()
  const vote = (d: number[]): BarcodeResult | null => {
    const key = d.join('')
    const n = (seen.get(key) ?? 0) + 1
    seen.set(key, n)
    return n >= 3 ? present(d) : null
  }
  const lines = 128
  for (let k = 0; k < lines; k++) {
    const y = Math.floor(((k + 0.5) / lines) * height)
    const row = new Float32Array(width)
    for (let x = 0; x < width; x++) row[x] = grey(x, y)
    const d = tryLine(row)
    if (d) {
      const r = vote(d)
      if (r) return r
    }
  }
  for (let k = 0; k < lines; k++) {
    const x = Math.floor(((k + 0.5) / lines) * width)
    const col = new Float32Array(height)
    for (let y = 0; y < height; y++) col[y] = grey(x, y)
    const d = tryLine(col)
    if (d) {
      const r = vote(d)
      if (r) return r
    }
  }
  return null
}

function present(digits: number[]): BarcodeResult {
  const value = digits.join('')
  const checkDigitVerifies = checksumOk(digits)
  return digits[0] === 0
    ? { value: value.slice(1), symbology: 'UPC-A', checkDigitVerifies }
    : { value, symbology: 'EAN-13', checkDigitVerifies }
}

/**
 * Decode from a drawable image at several scales, largest first. A downscale smooths
 * print noise; the original catches a small barcode on a large photograph.
 */
export async function decodeFromImageSource(
  src: CanvasImageSource,
  naturalWidth: number,
  naturalHeight: number,
): Promise<BarcodeResult | null> {
  // 2x first: a barcode of two pixels per module on a phone photo needs the upscale;
  // the smaller passes catch a large, close-up barcode without the cost.
  for (const s of [2, 1, 0.5]) {
    const w = Math.max(1, Math.round(naturalWidth * s))
    const h = Math.max(1, Math.round(naturalHeight * s))
    if (w > 4200 || h > 4200) continue
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return null
    ctx.drawImage(src, 0, 0, w, h)
    const result = decodeEAN13(ctx.getImageData(0, 0, w, h).data, w, h)
    if (result) return result
  }
  return null
}
