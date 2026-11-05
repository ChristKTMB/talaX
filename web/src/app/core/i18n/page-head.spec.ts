import { ApplicationRef, DOCUMENT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { routes } from '../../app.routes';
import { I18n } from './i18n';
import { PageHead } from './page-head';
import { pageAt } from './pages';

function start(browser: readonly string[] = ['en-US']) {
  Object.defineProperty(window.navigator, 'languages', { value: browser, configurable: true });
  TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
  const document = TestBed.inject(DOCUMENT);
  const head = TestBed.inject(PageHead);
  return { head, document, router: TestBed.inject(Router), i18n: TestBed.inject(I18n) };
}

/** Waits for navigations started by PageHead itself. */
const settled = () => TestBed.inject(ApplicationRef).whenStable();

const href = (document: Document, selector: string) =>
  document.head.querySelector(selector)?.getAttribute('href') ?? null;
const meta = (document: Document, selector: string) =>
  document.head.querySelector(selector)?.getAttribute('content') ?? null;

describe('pageAt', () => {
  it('knows each page in each language, and nothing else', () => {
    expect(pageAt('/')).toEqual({ page: 'home', language: 'en' });
    expect(pageAt('/fr')).toEqual({ page: 'home', language: 'fr' });
    expect(pageAt('/fr/conditions?x=1')).toEqual({ page: 'terms', language: 'fr' });
    expect(pageAt('/privacy#3')).toEqual({ page: 'privacy', language: 'en' });
    expect(pageAt('/fr/')).toBeNull();
    expect(pageAt('/fr/terms')).toBeNull();
  });
});

describe('PageHead', () => {
  it('takes the language from the address and writes the head of the page', async () => {
    const { document, router, i18n } = start();
    await router.navigateByUrl('/fr/confidentialite');
    TestBed.tick();
    expect(i18n.language()).toBe('fr');
    expect(document.title).toBe('Politique de confidentialité — Tala X');
    expect(meta(document, 'meta[name="description"]')).toContain('Rien n');
    expect(href(document, 'link[rel="canonical"]')).toBe('https://talax.online/fr/confidentialite');
    expect(href(document, 'link[hreflang="en"]')).toBe('https://talax.online/privacy');
    expect(href(document, 'link[hreflang="fr"]')).toBe('https://talax.online/fr/confidentialite');
    expect(href(document, 'link[hreflang="x-default"]')).toBe('https://talax.online/privacy');
    expect(meta(document, 'meta[property="og:locale"]')).toBe('fr_FR');

    await router.navigateByUrl('/');
    TestBed.tick();
    expect(i18n.language()).toBe('en');
    expect(document.title).toBe('Tala X — See beyond the pixel');
    expect(href(document, 'link[rel="canonical"]')).toBe('https://talax.online/');
  });

  it('switches to the same page in the other language', async () => {
    const { head, router } = start();
    await router.navigateByUrl('/terms');
    head.switchTo('fr');
    await settled();
    expect(router.url).toBe('/fr/conditions');
  });

  it('gives an unknown address no canonical link, and keeps its language', async () => {
    const { document, router, i18n } = start();
    await router.navigateByUrl('/fr/nowhere');
    TestBed.tick();
    expect(i18n.language()).toBe('fr');
    expect(document.title).toBe('Page introuvable — Tala X');
    expect(href(document, 'link[rel="canonical"]')).toBeNull();
    expect(href(document, 'link[hreflang="fr"]')).toBeNull();
  });

  it('sends a French-speaking visitor arriving on an English page to the French one', async () => {
    const { router } = start(['fr-CD', 'fr']);
    await router.navigateByUrl('/privacy');
    await settled();
    expect(router.url).toBe('/fr/confidentialite');
  });

  it('never sends anyone from a French page to an English one (crawlers run in English)', async () => {
    const { router, i18n } = start(['en-US']);
    await router.navigateByUrl('/fr');
    await settled();
    expect(router.url).toBe('/fr');
    expect(i18n.language()).toBe('fr');
  });
});
