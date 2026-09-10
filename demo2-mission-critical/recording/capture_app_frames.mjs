// Captures Caldova app frames at a controlled desktop viewport.
// The shared VS Code browser renders at ~578px wide, which forces the mobile layout.
import { chromium } from 'playwright'
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

const shot = async (page, name) => {
  await page.waitForTimeout(700)
  await page.screenshot({ path: path.join(frames, name) })
  console.log(`captured ${name}`)
}

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 })
const page = await context.newPage()

try {
  await page.goto(appUrl, { waitUntil: 'networkidle', timeout: 90_000 })
  await page.waitForTimeout(2500)

  await setQuestion(page, QUESTION)
  await clickByText(page, 'Search evidence')
  await page.waitForTimeout(8000)

  await clickTab(page, 'SQL query')
  await shot(page, 'frame1.png')

  await clickTab(page, 'Evidence')
  await shot(page, 'frame2.png')

  // Frame 3 shows the search-mode control and an opened result.
  await page.evaluate(() => {
    const first = Array.from(document.querySelectorAll('button'))
      .find((c) => c.textContent.trim().startsWith('02 PMC'))
    first?.click()
    window.scrollTo(0, 0)
  })
  await shot(page, 'frame3.png')

  await clickByText(page, 'Research')
  await page.waitForTimeout(3500)
  await shot(page, 'frame4.png')

  await clickByText(page, 'Pilot')
  await page.waitForTimeout(3000)
  await setQuestion(page, QUESTION)
  await clickByText(page, 'Search evidence')
  await page.waitForTimeout(8000)

  await clickTab(page, 'SQL query')
  await shot(page, 'frame5.png')
  await clickTab(page, 'Evidence')
  await shot(page, 'frame6.png')
  await page.evaluate(() => window.scrollTo(0, 0))
  await shot(page, 'frame7.png')

  const band = await page.evaluate(() => document.querySelector('.status-band')?.textContent?.trim() ?? '')
  console.log('status band:', band.slice(0, 180))
} finally {
  await browser.close()
}
