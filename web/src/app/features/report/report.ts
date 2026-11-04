import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n } from '../../core/i18n/i18n';
import { AnalysisSession } from '../../core/session/analysis-session';

/** The report of the last analysis. Lot 3 of the front fills it in. */
@Component({
  selector: 'app-report',
  template: `
    @if (session.result(); as result) {
      <article class="report">
        <h1>{{ result.integrity.label }}</h1>
        <p>{{ result.integrity.explanation }}</p>
        <button type="button" (click)="session.reset()">{{ i18n.t('report.another') }}</button>
      </article>
    }
  `,
  styles: `
    .report {
      max-width: var(--container);
      margin: 0 auto;
      padding: 56px 24px;
    }
    h1 {
      font-family: var(--font-mono);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Report {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
}
