import { Page, expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// A synthetic photo: a plain colour, a made-up camera, a date and a position in
// Paris. Never a photo of the corpus (real positions of real people).
const PHOTO = join(__dirname, 'fixtures', 'paris.jpg');
const example = (name: string) =>
  readFileSync(join(__dirname, '..', '..', 'docs', 'api-examples', `${name}.json`), 'utf8');
// A 1×1 PNG, served instead of OpenStreetMap tiles: tests never load OSM's servers.
const TILE = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

/** Records what must never happen: a policy violation, a script error, a request elsewhere. */
function watch(page: Page) {
  const problems: string[] = [];
  const site = new URL(test.info().project.use.baseURL ?? '').origin;
  void page.addInitScript(() =>
    document.addEventListener('securitypolicyviolation', (event) =>
      console.error(`CSP violation: ${event.violatedDirective} ${event.blockedURI}`),
    ),
  );
  page.on('console', (message) => {
    // Refusals the tests cause on purpose (4xx) are logged by the browser too.
    if (message.type() === 'error' && !/status of 4\d\d/.test(message.text())) {
      problems.push(message.text());
    }
  });
  page.on('pageerror', (error) => problems.push(error.message));
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (!['blob:', 'data:'].includes(url.protocol) && url.origin !== site) {
      problems.push(`request outside the site: ${request.url()}`);
    }
  });
  return problems;
}

async function analyse(page: Page) {
  await page.goto('/');
  await page.setInputFiles('#photo', PHOTO);
  await page.getByRole('button', { name: 'Analyser la photo' }).click();
  await expect(page.locator('app-report h1')).toBeVisible();
}

test('the home page loads under the security policy, from our own server only', async ({
  page,
}) => {
  const problems = watch(page);
  await page.goto('/');
  // A French browser arriving from elsewhere gets the French page.
  await expect(page).toHaveURL(/\/fr$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Regardez au-delà du pixel');
  await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
  await expect(page).toHaveTitle('Tala X — Regardez au-delà du pixel');
  const font = await page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].some((face) => face.status === 'loaded');
  });
  expect(font).toBe(true);
  expect(problems).toEqual([]);
});

test('a real analysis, the sky question, and the HTML report', async ({ page }) => {
  const problems = watch(page);
  await analyse(page);
  await expect(page.locator('.ask')).toContainText('Une question pour compléter');

  await page.locator('#sky-question').getByRole('button', { name: 'Nuit' }).click();
  await expect(page.locator('#check-solar app-state-badge')).toHaveText(/Suspect/);
  await expect(page.locator('.alert')).toContainText('Cohérence solaire');
  await expect(page.locator('app-sky-question')).toContainText('la photo montre la nuit');

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /Télécharger le rapport/ }).click();
  expect((await download).suggestedFilename()).toMatch(/^talax-[0-9a-f]+\.html$/);
  expect(problems).toEqual([]);
});

test('the map shows only after a click, with tiles from our relay', async ({ page }) => {
  const problems = watch(page);
  const tiles: string[] = [];
  await page.route('**/api/tiles/**', (route) => {
    tiles.push(new URL(route.request().url()).pathname);
    return route.fulfill({ contentType: 'image/png', body: TILE });
  });
  await page.route('**/api/analyze', (route) =>
    route.fulfill({ contentType: 'application/json', body: example('camera-original.fr') }),
  );
  await analyse(page);
  await expect(page.locator('#check-gps')).toContainText('OpenStreetMap ne voit ni votre adresse');
  expect(tiles).toEqual([]);

  await page.getByRole('button', { name: 'Afficher sur la carte' }).click();
  await expect(page.locator('.leaflet-tile-loaded').first()).toBeVisible();
  expect(tiles.every((path) => /^\/api\/tiles\/\d+\/\d+\/\d+\.png$/.test(path))).toBe(true);
  await expect(page.locator('.leaflet-control-attribution')).toHaveText(
    '© OpenStreetMap contributors',
  );
  expect(problems).toEqual([]);
});

test('changing the language asks for the report again in that language', async ({ page }) => {
  const asked: string[] = [];
  await page.route('**/api/analyze', (route) => {
    const lang = route.request().headers()['accept-language'] === 'en' ? 'en' : 'fr';
    asked.push(lang);
    return route.fulfill({
      contentType: 'application/json',
      body: example(`platform-copy.${lang}`),
    });
  });
  await analyse(page);
  await expect(page.locator('app-report h1')).toHaveText('Copie retraitée');
  await page.locator('footer').getByRole('button', { name: 'EN' }).click();
  await expect(page.locator('app-report h1')).toHaveText('Reprocessed copy');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page).toHaveURL(/:\d+\/$/);
  expect(asked).toEqual(['fr', 'en']);
});

test('the legal pages come from docs/legal, with their version', async ({ page }) => {
  const problems = watch(page);
  await page.goto('/fr/confidentialite');
  await expect(page.getByRole('heading', { level: 1 })).toContainText(
    'Politique de confidentialité',
  );
  await expect(page.locator('.document__body')).toContainText('Version du 2026-11-05');
  await expect(page.locator('.draft')).toHaveCount(0);
  await page.locator('footer').getByRole('link', { name: "Conditions d'utilisation" }).click();
  await expect(page).toHaveURL(/\/fr\/conditions$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText("Conditions d'utilisation");
  expect(problems).toEqual([]);
});

test('search engines get one page per language, and real 404s', async ({ page, request }) => {
  // What a crawler reads before running any script.
  const html = await (await request.get('/fr/conditions')).text();
  expect(html).toContain('<html lang="fr">');
  expect(html).toContain("<title>Conditions d'utilisation — Tala X</title>");
  expect(html).toContain('<link rel="canonical" href="https://talax.online/fr/conditions" />');
  expect(html).toContain(
    '<link rel="alternate" hreflang="en" href="https://talax.online/terms" />',
  );
  expect(await (await request.get('/robots.txt')).text()).toContain('Sitemap:');
  expect(await (await request.get('/sitemap.xml')).text()).toContain('/fr/confidentialite');

  const problems = watch(page);
  const response = await page.goto('/fr/nowhere');
  expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Page introuvable');
  await page.getByRole('link', { name: "Retour à l'accueil" }).click();
  await expect(page).toHaveURL(/\/fr$/);
  expect(problems).toEqual([]);
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test('nothing is wider than the screen, and the form comes first', async ({ page }) => {
    await page.route('**/api/analyze', (route) =>
      route.fulfill({ contentType: 'application/json', body: example('solar-contradiction.fr') }),
    );
    await page.goto('/');
    const card = await page.locator('app-upload-card').boundingBox();
    const features = await page.locator('.features').boundingBox();
    expect(card!.y).toBeLessThan(features!.y);
    const width = () => page.evaluate(() => document.documentElement.scrollWidth);
    expect(await width()).toBeLessThanOrEqual(390);
    await page.setInputFiles('#photo', PHOTO);
    await page.getByRole('button', { name: 'Analyser la photo' }).click();
    await expect(page.locator('.alert')).toBeVisible();
    expect(await width()).toBeLessThanOrEqual(390);
  });
});
