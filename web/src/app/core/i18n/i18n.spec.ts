import { DOCUMENT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { CATALOGS, I18n, languageFrom } from './i18n';

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe('catalogues', () => {
  const { en, fr } = CATALOGS;

  it('have the same keys in both languages', () => {
    expect(Object.keys(fr).sort()).toEqual(Object.keys(en).sort());
  });

  it('have no empty text', () => {
    for (const catalog of [en, fr]) {
      for (const [key, text] of Object.entries(catalog)) {
        expect(text.trim(), key).not.toBe('');
      }
    }
  });

  it('have the same placeholders in both languages', () => {
    for (const key of Object.keys(en)) {
      expect(placeholders(fr[key] ?? ''), key).toEqual(placeholders(en[key] ?? ''));
    }
  });
});

describe('languageFrom', () => {
  it('follows the same rule as the API: fr* is French, anything else English', () => {
    expect(languageFrom(['fr-CD', 'en'])).toBe('fr');
    expect(languageFrom(['FR'])).toBe('fr');
    expect(languageFrom(['en-GB', 'fr'])).toBe('en');
    expect(languageFrom(['ln-CD'])).toBe('en');
    expect(languageFrom([])).toBe('en');
  });
});

describe('I18n', () => {
  it('translates, fills placeholders and keeps unknown ones visible', () => {
    const i18n = TestBed.inject(I18n);
    i18n.language.set('fr');
    expect(i18n.t('header.source')).toBe('Code source');
    i18n.language.set('en');
    expect(i18n.t('header.source')).toBe('Source code');
    expect(i18n.t('missing.key')).toBe('missing.key');
  });

  it('writes file sizes the way each language does', () => {
    const i18n = TestBed.inject(I18n);
    i18n.language.set('fr');
    expect(i18n.size(2_400_000)).toBe('2,3 Mo');
    expect(i18n.size(2321)).toBe('2,3 ko');
    i18n.language.set('en');
    expect(i18n.size(2_400_000)).toBe('2.3 MB');
    expect(i18n.size(512)).toBe('512 B');
  });

  it('sets the language of the page', () => {
    const i18n = TestBed.inject(I18n);
    i18n.language.set('fr');
    TestBed.tick();
    expect(TestBed.inject(DOCUMENT).documentElement.lang).toBe('fr');
  });

  it('gives the address of each page in the current language', () => {
    const i18n = TestBed.inject(I18n);
    i18n.language.set('fr');
    expect(i18n.path('home')).toBe('/fr');
    expect(i18n.path('privacy')).toBe('/fr/confidentialite');
    i18n.language.set('en');
    expect(i18n.path('home')).toBe('/');
    expect(i18n.path('terms')).toBe('/terms');
  });
});
