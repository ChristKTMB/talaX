import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  afterNextRender,
  computed,
  inject,
} from '@angular/core';
import { I18n } from '../../core/i18n/i18n';
import { AnalysisSession } from '../../core/session/analysis-session';
import { StateBadge } from '../../shared/ui/state-badge/state-badge';
import { CheckRow } from './check-row/check-row';
import { Visual } from './visual/visual';

/** The report of the last analysis: verdict first, then every check with its explanation. */
@Component({
  selector: 'app-report',
  imports: [CheckRow, StateBadge, Visual],
  templateUrl: './report.html',
  styleUrl: './report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Report {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  private readonly document = inject(DOCUMENT);

  protected readonly result = computed(() => this.session.result());
  /** Only a contradiction earns a banner at the top; "to check" never does. */
  protected readonly suspicious = computed(
    () => this.result()?.results.filter((check) => check.state === 'suspicious') ?? [],
  );
  protected readonly format = computed(() => {
    const real = this.result()?.file.real_format;
    return real ? real.split('/').pop()?.toUpperCase() : null;
  });
  /** "2026-01-01 12:00 UTC": the time of the analysis, the same for every reader. */
  protected readonly analysedAt = computed(() => {
    const created = this.result()?.created_at;
    if (!created) return '';
    const iso = new Date(created).toISOString();
    return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
  });

  constructor() {
    afterNextRender(() => this.document.defaultView?.scrollTo({ top: 0 }));
  }

  protected show(signal: string): void {
    const row = this.document.getElementById(`check-${signal}`);
    row?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    row?.focus({ preventScroll: true });
  }

  protected another(): void {
    this.session.reset();
    this.document.defaultView?.scrollTo({ top: 0 });
  }
}
