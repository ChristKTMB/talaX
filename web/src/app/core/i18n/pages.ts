import pages from './pages.json';

// The addresses of the site, one per page and language, so that search engines
// find both languages (scripts/seo-pages.mjs reads the same file).

export type Language = 'en' | 'fr';
export type PageName = keyof typeof pages.paths;
/** Any address that is not one of the pages above. */
export type Page = PageName | 'not-found';

/** The site's own address: canonical links point there, never to www. */
export const SITE_URL: string = pages.site;
export const PATHS: Readonly<Record<PageName, Readonly<Record<Language, string>>>> = pages.paths;

/** The page and language of an address, or null if it is none of the site's pages. */
export function pageAt(url: string): { page: PageName; language: Language } | null {
  const path = url.split(/[?#]/)[0];
  for (const [page, paths] of Object.entries(PATHS) as [PageName, Record<Language, string>][]) {
    for (const [language, at] of Object.entries(paths) as [Language, string][]) {
      if (at === path) return { page, language };
    }
  }
  return null;
}

/** The language an unknown address belongs to, if it says one. */
export function languageOfPath(url: string): Language | null {
  const known = pageAt(url);
  if (known) return known.language;
  return /^\/fr(\/|$|[?#])/.test(url) ? 'fr' : null;
}
