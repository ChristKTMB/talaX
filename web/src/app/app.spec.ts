import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter, withComponentInputBinding } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';
import { I18n } from './core/i18n/i18n';
import { PageHead } from './core/i18n/page-head';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes, withComponentInputBinding())],
    });
    TestBed.inject(PageHead);
  });

  it('shows the header, the main area and the footer', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('app-header header')).not.toBeNull();
    expect(page.querySelector('main')).not.toBeNull();
    expect(page.querySelector('app-footer footer')).not.toBeNull();
  });

  it('switches the whole interface language from the footer, address included', async () => {
    const fixture = TestBed.createComponent(App);
    await TestBed.inject(Router).navigateByUrl('/privacy');
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(TestBed.inject(I18n).language()).toBe('en');
    const french = page.querySelector<HTMLButtonElement>('button[lang="fr"]');
    french?.click();
    await fixture.whenStable();
    expect(TestBed.inject(Location).path()).toBe('/fr/confidentialite');
    expect(french?.getAttribute('aria-pressed')).toBe('true');
    expect(page.querySelector('.header__source')?.textContent?.trim()).toBe('Code source');
    expect(page.querySelector('footer a')?.getAttribute('href')).toBe('/fr/conditions');
  });

  it('shows a "not found" page for any other address', async () => {
    const fixture = TestBed.createComponent(App);
    await TestBed.inject(Router).navigateByUrl('/fr/nowhere');
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('app-not-found h1')?.textContent).toBe('Page introuvable');
    expect(page.querySelector('app-not-found a')?.getAttribute('href')).toBe('/fr');
  });
});
