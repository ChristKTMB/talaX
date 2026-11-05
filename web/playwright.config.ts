import { defineConfig, devices } from '@playwright/test';

// End-to-end tests of the whole service as deployed: the Angular site and the
// API behind nginx, with its security policy (`docker compose up` first).
export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env['CI'] ? 1 : 0,
  reporter: process.env['CI'] ? 'github' : 'list',
  use: {
    baseURL: process.env['TALAX_URL'] ?? 'http://127.0.0.1:9188',
    locale: 'fr-FR',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
