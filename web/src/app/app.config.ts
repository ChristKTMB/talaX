import { provideHttpClient, withFetch } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';
import { PageHead } from './core/i18n/page-head';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // No withInMemoryScrolling: PageHead scrolls to the top on a new page,
    // not when only the language changes.
    provideRouter(routes, withComponentInputBinding()),
    provideAppInitializer(() => {
      inject(PageHead);
    }),
    provideHttpClient(withFetch()),
  ],
};
