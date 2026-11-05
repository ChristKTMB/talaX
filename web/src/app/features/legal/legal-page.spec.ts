import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { I18n } from '../../core/i18n/i18n';
import { LegalPage } from './legal-page';

async function open(url: string, language: 'en' | 'fr' = 'fr') {
  TestBed.configureTestingModule({
    providers: [
      provideRouter(
        [
          { path: 'terms', component: LegalPage, data: { page: 'terms' } },
          { path: 'privacy', component: LegalPage, data: { page: 'privacy' } },
        ],
        withComponentInputBinding(),
      ),
    ],
  });
  TestBed.inject(I18n).language.set(language);
  const harness = await RouterTestingHarness.create();
  await harness.navigateByUrl(url);
  return { harness, page: harness.routeNativeElement as HTMLElement };
}

describe('LegalPage', () => {
  it('shows the privacy policy from docs/legal, with its version and contents', async () => {
    const { page } = await open('/privacy');
    expect(page.querySelector('h1')?.textContent).toContain('Politique de confidentialité');
    // Approved: no draft banner (it only appears while docs/legal holds one).
    expect(page.querySelector('.draft')).toBeNull();
    expect(page.querySelector('.document__body')?.textContent).toContain('Version du 2026-11-05');
    expect(page.querySelectorAll('.toc li').length).toBeGreaterThan(5);
    expect(page.querySelector('.document__body')?.textContent).toContain("Rien n'est conservé");
    expect(page.querySelector('.document__body table')).not.toBeNull();
  });

  it('follows the language of the application', async () => {
    const { page } = await open('/terms', 'en');
    expect(page.querySelector('h1')?.textContent).toContain('Terms of use');
    TestBed.inject(I18n).language.set('fr');
    TestBed.tick();
    expect(page.querySelector('h1')?.textContent).toContain("Conditions d'utilisation");
  });

  it('lists every section of the document in the contents, in order', async () => {
    const { page } = await open('/terms');
    const contents = [...page.querySelectorAll('.toc li button')].map((b) => b.textContent?.trim());
    const headings = [...page.querySelectorAll('.document__body h2')].map((h) => h.textContent);
    expect(contents.length).toBe(9);
    expect(contents).toEqual(headings);
  });

  it('keeps links between the two documents inside the application', async () => {
    const { harness, page } = await open('/terms');
    const link = page.querySelector<HTMLAnchorElement>('.document__body a[href="/privacy"]');
    expect(link).not.toBeNull();
    link?.click();
    await harness.fixture.whenStable();
    expect(TestBed.inject(Location).path()).toBe('/privacy');
  });
});
