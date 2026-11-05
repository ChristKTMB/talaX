import { DOCUMENT, Injectable, effect, inject, signal } from '@angular/core';
import { ViewportScroller } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { I18n, Language, languageFrom } from './i18n';
import { PATHS, Page, PageName, SITE_URL, languageOfPath, pageAt } from './pages';

const OG_LOCALES: Readonly<Record<Language, string>> = { en: 'en_US', fr: 'fr_FR' };

/**
 * Keeps the language in step with the address, and the head of the page
 * (title, description, links to the other language) in step with both.
 * scripts/seo-pages.mjs writes the same head into each page at build time,
 * for search engines and link previews that do not run JavaScript.
 */
@Injectable({ providedIn: 'root' })
export class PageHead {
  private readonly router = inject(Router);
  private readonly i18n = inject(I18n);
  private readonly document = inject(DOCUMENT);
  private readonly title = inject(Title);
  private readonly meta = inject(Meta);
  private readonly scroller = inject(ViewportScroller);

  /** The page shown, from the address. */
  readonly page = signal<Page>('home');
  private first = true;

  constructor() {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => this.arrived(event.urlAfterRedirects));
    effect(() => this.write(this.page(), this.i18n.language()));
  }

  /** The same page in the other language, or only the texts on an unknown address. */
  switchTo(language: Language): void {
    const page = this.page();
    if (page === 'not-found') this.i18n.language.set(language);
    else void this.router.navigateByUrl(PATHS[page][language]);
  }

  private arrived(url: string): void {
    const known = pageAt(url);
    if (this.first) {
      this.first = false;
      if (known && this.sendToFrench(known.page, known.language)) return;
    } else if ((known?.page ?? 'not-found') !== this.page()) {
      // Not when only the language changes: the reader stays where they were.
      this.scroller.scrollToPosition([0, 0]);
    }
    this.page.set(known?.page ?? 'not-found');
    const language = known?.language ?? languageOfPath(url);
    if (language) this.i18n.language.set(language);
  }

  /**
   * A French-speaking visitor who arrives on an English page from elsewhere
   * gets the French one. Never the other way round: crawlers run in English,
   * and must be able to read the French pages.
   */
  private sendToFrench(page: PageName, language: Language): boolean {
    const browser = languageFrom(this.document.defaultView?.navigator.languages ?? []);
    const origin = this.document.location?.origin ?? '';
    const fromSite = origin !== '' && this.document.referrer.startsWith(origin);
    if (language !== 'en' || browser !== 'fr' || fromSite) return false;
    void this.router.navigateByUrl(PATHS[page].fr, { replaceUrl: true });
    return true;
  }

  private write(page: Page, language: Language): void {
    const texts = page === 'not-found' ? 'home' : page;
    const title = this.i18n.t(`page.${page}.title`);
    const description = this.i18n.t(`page.${texts}.description`);
    this.title.setTitle(title);
    this.meta.updateTag({ name: 'description', content: description });
    this.meta.updateTag({ property: 'og:title', content: title });
    this.meta.updateTag({ property: 'og:description', content: description });
    this.meta.updateTag({ property: 'og:locale', content: OG_LOCALES[language] });

    const url = (at: Language) => (page === 'not-found' ? null : SITE_URL + PATHS[page][at]);
    this.link('canonical', null, url(language));
    this.link('alternate', 'en', url('en'));
    this.link('alternate', 'fr', url('fr'));
    this.link('alternate', 'x-default', url('en'));
    const og = url(language);
    if (og) this.meta.updateTag({ property: 'og:url', content: og });
    else this.meta.removeTag('property="og:url"');
  }

  private link(rel: string, hreflang: string | null, href: string | null): void {
    const selector = `link[rel="${rel}"]` + (hreflang ? `[hreflang="${hreflang}"]` : '');
    let element = this.document.head.querySelector<HTMLLinkElement>(selector);
    if (href === null) {
      element?.remove();
      return;
    }
    if (!element) {
      element = this.document.createElement('link');
      element.rel = rel;
      if (hreflang) element.hreflang = hreflang;
      this.document.head.appendChild(element);
    }
    element.setAttribute('href', href);
  }
}
