import { DOCUMENT, Injectable, effect, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import en from './en.json';
import fr from './fr.json';

export type Language = 'en' | 'fr';
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
  private readonly title = inject(Title);

  readonly language = signal<Language>(
    languageFrom(this.document.defaultView?.navigator.languages ?? []),
  );

  private readonly syncDocument = effect(() => {
    this.document.documentElement.lang = this.language();
    this.title.setTitle(this.t('app.title'));
  });

  /** The text of `key` in the current language, with `{name}` placeholders filled. */
  t(key: string, values: Readonly<Record<string, string | number>> = {}): string {
    const text = CATALOGS[this.language()][key] ?? key;
    return text.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in values ? String(values[name]) : match,
    );
  }
}
