// Captures Caldova app frames at a controlled desktop viewport.
// The shared VS Code browser renders at ~578px wide, which forces the mobile layout.
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frames = path.join(here, 'frames')
const appUrl = process.env.CALDOVA_URL
  ?? 'https://caldova-app.whitemeadow-b4119f0c.westcentralus.azurecontainerapps.io/'

const QUESTION = 'How does disruption of the intestinal microbiome influence anxiety and depressive symptoms?'

const clickByText = (page, text) => page.evaluate((label) => {
  const node = Array.from(document.querySelectorAll('button')).find(
    (candidate) => candidate.textContent.trim() === label)
  if (!node) throw new Error(`button not found: ${label}`)
  node.click()
}, text)

const clickTab = (page, text) => page.evaluate((label) => {
  const node = Array.from(document.querySelectorAll('[role=tab]')).find(
    (candidate) => candidate.textContent.trim() === label)
  if (!node) throw new Error(`tab not found: ${label}`)
  node.click()
}, text)

const setQuestion = (page, text) => page.evaluate((value) => {
  const input = document.querySelector('.search-form input')
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
}, text)

// The band is the honesty check: it must never show a number the demo cannot back up.
const band = (page) => page.evaluate(
  () => document.querySelector('.status-band')?.textContent?.trim().replace(/\s+/g, ' ') ?? '')

// Frames whose status band is not live get a work-in-progress banner at build time.
const NOT_LIVE = /not ready|not reachable|unavailable|error/i
const workInProgress = []

const shot = async (page, name) => {
  await page.waitForTimeout(700)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: path.join(frames, name) })
  const status = await band(page)
  const wip = NOT_LIVE.test(status)
  if (wip) workInProgress.push(name)
  console.log(`captured ${name.padEnd(12)} ${wip ? '[WIP] ' : ''}${status.slice(0, 120)}`)
}

// The submit button relabels to "Searching" while a query is in flight, so every search
// waits for the idle label before clicking and again after, rather than a fixed delay.
const idle = (page, timeout) => page.waitForFunction(
  () => Array.from(document.querySelectorAll('button'))
    .some((candidate) => candidate.textContent.trim() === 'Search evidence'),
  null,
  { timeout },
).catch(() => {})

const search = async (page) => {
  await setQuestion(page, QUESTION)
  await idle(page, 120_000)
  await clickByText(page, 'Search evidence')
  await page.waitForTimeout(1500)
  await idle(page, 120_000)
  await page.waitForTimeout(1500)
}

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 })
const page = await context.newPage()

try {
  await page.goto(appUrl, { waitUntil: 'networkidle', timeout: 90_000 })
  await page.waitForTimeout(2500)

  // Beats 1-4 all run on hybrid, the app default, so the same result set carries the
  // whole opening and beat 4 explains what has been on screen rather than re-running.
  // Discarded run: the first search of a session pays cold ANN reads and would
  // otherwise put an unrepresentative number on the opening frames.
  await search(page)
  await search(page)
  await clickTab(page, 'SQL query')
  await shot(page, 'frame1.png')

  await clickTab(page, 'Evidence')
  await shot(page, 'frame2.png')

  await page.evaluate(() => {
    const first = Array.from(document.querySelectorAll('button'))
      .find((c) => c.textContent.trim().startsWith('02 PMC'))
    first?.click()
  })
  await shot(page, 'frame3.png')

  // Beat 4: cut back to the query so the filter predicate inside VECTOR_SEARCH is on
  // screen while it is described.
  await clickTab(page, 'SQL query')
  await shot(page, 'frame4.png')

  // Beats 7 and 10: the scaled targets. Each one re-runs the question so the frame shows
  // that target's own numbers rather than whatever the 4K target left on screen.
  await clickByText(page, '1M')
  await page.waitForTimeout(30_000)
  await search(page)
  await shot(page, 'frame5.png')

  await clickByText(page, 'Named Replica')
  await page.waitForTimeout(30_000)
  await search(page)
  await shot(page, 'frame6.png')

  // Beat 11: closing shot on a clean 4K session rather than a repeat of frame 4.
  await page.goto(appUrl, { waitUntil: 'networkidle', timeout: 90_000 })
  await page.waitForTimeout(3000)
  await setQuestion(page, QUESTION)
  await shot(page, 'frame7.png')

  fs.writeFileSync(path.join(frames, 'wip.json'), `${JSON.stringify(workInProgress, null, 2)}\n`)
  console.log(`work in progress: ${workInProgress.join(', ') || 'none'}`)
} finally {
  await browser.close()
}
