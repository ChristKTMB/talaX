import { Route, UrlMatcher, UrlSegment } from '@angular/router';
import { PATHS, PageName } from './core/i18n/pages';

const legal = () => import('./features/legal/legal-page').then((m) => m.LegalPage);

/**
 * One route per page, matching its address in every language: changing the
 * language keeps the page's component (a map shown, an answer being changed).
 */
function page(name: PageName, route: Omit<Route, 'matcher'>): Route {
  const paths: readonly string[] = Object.values(PATHS[name]);
  const matcher: UrlMatcher = (segments: UrlSegment[]) =>
    paths.includes('/' + segments.map((segment) => segment.path).join('/'))
      ? { consumed: segments }
      : null;
  return { ...route, matcher, data: { ...route.data, page: name } };
}

export const routes: Route[] = [
  page('home', { loadComponent: () => import('./features/home/home').then((m) => m.Home) }),
  page('terms', { loadComponent: legal }),
  page('privacy', { loadComponent: legal }),
  {
    path: '**',
    loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
  },
];
