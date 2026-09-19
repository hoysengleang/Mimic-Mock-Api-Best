import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests.
 *
 * These drive the real UI against the real API — nothing is stubbed — because
 * the bugs worth catching here live in the seam between them. The API must
 * already be running; `webServer` only starts the Vite dev server.
 */
const UI_PORT = Number(process.env.E2E_UI_PORT ?? 5175)
const API_URL = process.env.E2E_API_URL ?? 'http://127.0.0.1:5000'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // the tests share one backend database
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  timeout: 45_000,
  // Generous, because the first navigation in a cold run waits for Vite to
  // compile the route on demand. A tighter budget flakes on the first test.
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],

  use: {
    baseURL: `http://127.0.0.1:${UI_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: {
    command: `yarn vite --port ${UI_PORT} --strictPort`,
    url: `http://127.0.0.1:${UI_PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { VITE_PROXY_TARGET: API_URL },
  },
})
