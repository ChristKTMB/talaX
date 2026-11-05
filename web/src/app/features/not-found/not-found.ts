import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n } from '../../core/i18n/i18n';

/** Any other address. nginx answers it with a 404 status, for search engines. */
@Component({
  selector: 'app-not-found',
  imports: [RouterLink],
  template: `
    <section class="not-found">
      <h1>{{ i18n.t('not_found.title') }}</h1>
      <p>{{ i18n.t('not_found.text') }}</p>
      <a [routerLink]="i18n.path('home')">{{ i18n.t('not_found.home') }}</a>
    </section>
  `,
  styles: `
    .not-found {
      max-width: var(--container);
      margin: 0 auto;
      padding: 72px 24px 96px;
    }
    h1 {
      margin: 0 0 12px;
      font-family: var(--font-mono);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotFound {
  protected readonly i18n = inject(I18n);
}
