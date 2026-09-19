import { expect, test } from '@playwright/test'

/** Mock management, and running a collection in a loop. */

test.describe('mocks', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/mocks')
    await expect(page.locator('.row').first()).toBeVisible()
  })

  test('seeded mocks are listed with their stats', async ({ page }) => {
    await expect(page.locator('.row')).not.toHaveCount(0)
    await expect(page.locator('.mocks__stats')).toContainText('enabled')
  })

  test('a mock can be created and then served', async ({ page, request }) => {
    const path = `/e2e/created-${Date.now()}`

    await page.getByRole('button', { name: 'New mock' }).click()
    await page.locator('.input--mono').first().fill(path)
    await page.getByRole('button', { name: 'Create mock' }).click()

    await expect(page.getByText(path)).toBeVisible()

    // The mock server should now answer on that path.
    const response = await request.get(`/mock${path}`)
    expect(response.status()).toBe(200)
    expect(await response.json()).toHaveProperty('message')
  })

  test('a duplicate path is rejected with a clear message', async ({ page }) => {
    const path = `/e2e/dupe-${Date.now()}`

    for (let attempt = 0; attempt < 2; attempt++) {
      await page.getByRole('button', { name: 'New mock' }).click()
      await page.locator('.input--mono').first().fill(path)
      await page.getByRole('button', { name: 'Create mock' }).click()
      await page.waitForTimeout(400)
    }

    await expect(page.locator('.toast--error')).toContainText('already exists')
  })

  test('search filters the list', async ({ page }) => {
    await page.getByPlaceholder('Search mocks…').fill('zzz-no-such-mock')
    await expect(page.locator('.empty-state__title')).toBeVisible()
  })

  test('a mock can be disabled and stops responding', async ({
    page,
    request,
  }) => {
    const path = `/e2e/toggle-${Date.now()}`

    await page.getByRole('button', { name: 'New mock' }).click()
    await page.locator('.input--mono').first().fill(path)
    await page.getByRole('button', { name: 'Create mock' }).click()
    await expect(page.getByText(path)).toBeVisible()

    expect((await request.get(`/mock${path}`)).status()).toBe(200)

    const row = page.locator('.row', { hasText: path })
    await row.locator('input[type="checkbox"]').click()
    await page.waitForTimeout(500)

    expect((await request.get(`/mock${path}`)).status()).toBe(404)
  })
})

test.describe('runner', () => {
  test('runs a collection and reports every assertion', async ({ page }) => {
    await page.goto('/runner')
    await expect(page.locator('.controls__run')).toBeEnabled()

    await page.locator('.controls__run').click()

    const summary = page.locator('.summary')
    await expect(summary).toBeVisible({ timeout: 20_000 })
    await expect(summary).toHaveClass(/summary--ok/)
    await expect(summary).toContainText('All checks passed')
  })

  test('looping multiplies the requests sent', async ({ page }) => {
    await page.goto('/runner')
    await expect(page.locator('.controls__run')).toBeEnabled()

    await page.locator('input[type="number"]').first().fill('3')
    await expect(page.locator('.controls__plan')).toContainText('9')

    await page.locator('.controls__run').click()

    await expect(page.locator('.summary')).toBeVisible({ timeout: 25_000 })
    // Three iterations, each its own expandable row.
    await expect(page.locator('.iteration')).toHaveCount(3)
    await expect(page.locator('.summary__stats')).toContainText('9')
  })

  test('an iteration expands to show each request', async ({ page }) => {
    await page.goto('/runner')
    await page.locator('.controls__run').click()
    await expect(page.locator('.summary')).toBeVisible({ timeout: 20_000 })

    await page.locator('.iteration__head').first().click()
    await expect(page.locator('.step')).toHaveCount(3)
    await expect(page.locator('.step').first()).toContainText('List users')
  })
})

test.describe('environments', () => {
  test('variables can be edited and saved', async ({ page }) => {
    await page.goto('/environments')
    await expect(page.locator('.env-item').first()).toBeVisible()

    await page.locator('.env-item').first().click()
    await expect(page.locator('.vars__row').first()).toBeVisible()

    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.locator('.toast--success')).toBeVisible()
  })
})

test.describe('history', () => {
  test('a sent request shows up with credentials masked', async ({ page }) => {
    const secret = `sk-e2e-${Date.now()}`

    // Send a request carrying a bearer token, so there is something to redact.
    await page.goto('/')
    await page.locator('.tree__request').first().click()

    await page.getByRole('tab', { name: 'Auth' }).click()
    await page.getByRole('button', { name: 'Bearer token' }).click()
    await page.locator('.auth__field input').first().fill(secret)

    await page.locator('.urlbar__send').click()
    await expect(page.locator('.status')).toBeVisible()

    await page.goto('/history')
    await expect(page.locator('.entry').first()).toBeVisible()
    await page.locator('.entry').first().click()
    await expect(page.locator('.detail__url')).not.toBeEmpty()

    // The Authorization header is stored, but its value must be masked.
    const headers = page.locator('.kvlist')
    await expect(headers).toContainText('Authorization')
    await expect(headers).not.toContainText(secret)

    // Belt and braces: the secret must not appear anywhere on the page.
    await expect(page.locator('body')).not.toContainText(secret)
  })
})
