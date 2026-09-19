import { expect, test } from '@playwright/test'

/**
 * The core loop: open a saved request, send it, read the response, and see
 * assertions evaluated. If this suite passes, the product works.
 */

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.tree__request').first()).toBeVisible()
})

test('seeded collection appears in the sidebar', async ({ page }) => {
  await expect(page.getByText('Getting started')).toBeVisible()
  await expect(page.locator('.tree__request')).toHaveCount(3)
  await expect(page.locator('.tree__request').first()).toContainText('List users')
})

test('opening a request loads it into a tab', async ({ page }) => {
  await page.locator('.tree__request').first().click()

  await expect(page.locator('.tabbar__tab')).toContainText(['List users'])
  await expect(page.locator('.urlbar__url')).toHaveValue(
    '{{baseUrl}}/mock/api/users',
  )
})

test('sending a request returns a response and runs its assertions', async ({
  page,
}) => {
  await page.locator('.tree__request').first().click()
  await page.locator('.urlbar__send').click()

  const status = page.locator('.status')
  await expect(status).toBeVisible()
  await expect(status).toContainText('200')

  // The three seeded assertions should all pass.
  await expect(page.locator('.response__bar .badge').first()).toContainText(
    '3/3',
  )

  // The body renders as formatted JSON.
  await expect(page.locator('.cm-content')).toContainText('"users"')
  await expect(page.locator('.cm-content')).toContainText('Leang')
})

test('a failing assertion is reported, not hidden', async ({ page }) => {
  await page.locator('.tree__request').first().click()

  // Point an assertion at a value that cannot match.
  await page.getByRole('tab', { name: /Tests/ }).click()
  const target = page.locator('.assert__target').first()
  await target.fill('418')

  await page.locator('.urlbar__send').click()

  await expect(page.locator('.response__bar .badge').first()).toContainText(
    '2/3',
  )
  await expect(page.locator('.assert__row--fail').first()).toBeVisible()
})

test('a request to an unreachable host fails cleanly', async ({ page }) => {
  await page.locator('.urlbar__url').fill('http://127.0.0.1:9/nope')
  await page.locator('.urlbar__send').click()

  await expect(page.locator('.response__error')).toBeVisible()
  await expect(page.locator('.response__error-text')).not.toBeEmpty()
})

test('an undefined variable is flagged before sending', async ({ page }) => {
  await page.locator('.urlbar__url').fill('{{nonexistentVariable}}/x')
  await expect(page.locator('.warnbar')).toContainText('nonexistentVariable')
})

test('tabs can be opened and closed', async ({ page }) => {
  const before = await page.locator('.tabbar__tab').count()

  await page.getByRole('button', { name: 'New request' }).click()
  await expect(page.locator('.tabbar__tab')).toHaveCount(before + 1)

  await page.locator('.tabbar__close').last().click()
  await expect(page.locator('.tabbar__tab')).toHaveCount(before)
})

test('theme cycles through every variant and persists', async ({ page }) => {
  const root = page.locator('html')
  const button = page.locator('header.header button').last()

  const seen: string[] = []
  for (let step = 0; step < 3; step++) {
    seen.push((await root.getAttribute('data-theme')) ?? '')
    await button.click()
    await page.waitForTimeout(120)
  }

  // Three distinct themes, and cycling returns to where it started.
  expect(new Set(seen).size).toBe(3)
  expect(await root.getAttribute('data-theme')).toBe(seen[0])

  // Pick a non-default one and confirm it survives a reload.
  await button.click()
  const chosen = await root.getAttribute('data-theme')
  await page.reload()
  await expect(root).toHaveAttribute('data-theme', chosen!)
})
