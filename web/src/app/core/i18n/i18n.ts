import { DOCUMENT, Injectable, effect, inject, signal } from '@angular/core';
import en from './en.json';
import fr from './fr.json';
import { Language, PATHS, PageName, languageOfPath } from './pages';

export type { Language } from './pages';
export const LANGUAGES: readonly Language[] = ['fr', 'en'];

export type Catalog = Readonly<Record<string, string>>;
export const CATALOGS: Readonly<Record<Language, Catalog>> = { en, fr };

/** Same rule as the CLI and the API: French for `fr*`, English otherwise. */
export function languageFrom(preferred: readonly string[]): Language {
  return preferred[0]?.toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

/**
 * Interface texts. Verdicts and explanations come translated from the API;
 * this catalogue only holds the words of the page around them.
 */
@Injectable({ providedIn: 'root' })
export class I18n {
  private readonly document = inject(DOCUMENT);

  /**
   * The address says the language (`/fr/...`); the browser's language only
   * decides for an address that does not. The router keeps it in step
   * afterwards (`PageHead`).
   */
  readonly language = signal<Language>(
    languageOfPath(this.document.location?.pathname ?? '') ??
      languageFrom(this.document.defaultView?.navigator.languages ?? []),
  );

  private readonly syncDocument = effect(() => {
    this.document.documentElement.lang = this.language();
  });

  /** The address of `page` in the current language. */
  path(page: PageName): string {
    return PATHS[page][this.language()];
  }

  /** The text of `key` in the current language, with `{name}` placeholders filled. */
  t(key: string, values: Readonly<Record<string, string | number>> = {}): string {
    const text = CATALOGS[this.language()][key] ?? key;
    return text.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in values ? String(values[name]) : match,
    );
  }

  /** A whole number in the current language: "9 704", "9,704". */
  number(value: number): string {
    return new Intl.NumberFormat(this.language()).format(value);
  }

  /** A file size in the current language: "2,3 Mo", "2.3 MB". */
  size(bytes: number): string {
    const number = (value: number) =>
      new Intl.NumberFormat(this.language(), { maximumFractionDigits: 1 }).format(value);
    if (bytes < 1024) return this.t('size.bytes', { value: number(bytes) });
    if (bytes < 1024 * 1024) return this.t('size.kb', { value: number(bytes / 1024) });
    return this.t('size.mb', { value: number(bytes / (1024 * 1024)) });
  }
}
