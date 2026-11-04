import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { I18n } from './core/i18n/i18n';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideRouter([])] });
  });

  it('shows the header, the main area and the footer', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('app-header header')).not.toBeNull();
    expect(page.querySelector('main')).not.toBeNull();
    expect(page.querySelector('app-footer footer')).not.toBeNull();
  });

  it('switches the whole interface language from the footer', async () => {
    TestBed.inject(I18n).language.set('en');
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    const french = page.querySelector<HTMLButtonElement>('button[lang="fr"]');
    french?.click();
    await fixture.whenStable();
    expect(french?.getAttribute('aria-pressed')).toBe('true');
    expect(page.querySelector('.header__source')?.textContent?.trim()).toBe('Code source');
  });
});
