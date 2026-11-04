import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  afterNextRender,
  computed,
  inject,
} from '@angular/core';
import { I18n } from '../../core/i18n/i18n';
import { CheckResult } from '../../core/models/analysis';
import { AnalysisSession } from '../../core/session/analysis-session';
import { Icon } from '../../shared/ui/icon/icon';
import { FINAL_ERRORS, Problem } from '../../shared/ui/problem/problem';
import { RetryButton } from '../../shared/ui/retry-button/retry-button';
import { StateBadge } from '../../shared/ui/state-badge/state-badge';
import { CheckRow } from './check-row/check-row';
import { LocationMap } from './location-map/location-map';
import { SkyQuestion, asksForSky } from './sky-question/sky-question';
import { Visual } from './visual/visual';

/** The report of the last analysis: verdict first, then every check with its explanation. */
@Component({
  selector: 'app-report',
  imports: [CheckRow, Icon, LocationMap, Problem, RetryButton, SkyQuestion, StateBadge, Visual],
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
  /** The API waits for what the user sees in the photo. */
  protected readonly asksForSky = computed(
    () => this.result()?.results.some((check) => asksForSky(check)) ?? false,
  );
  protected readonly finalError = computed(() =>
    FINAL_ERRORS.has(this.session.error()?.code ?? ''),
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
    // A new report is announced: screen readers read the verdict first.
    afterNextRender(() => {
      this.document.defaultView?.scrollTo({ top: 0 });
      this.document.getElementById('verdict')?.focus({ preventScroll: true });
    });
  }

  /** A map is offered only for a GPS position found consistent (docs/api.md). */
  protected mapPosition(check: CheckResult): { latitude: number; longitude: number } | null {
    const { latitude, longitude } = check.evidence;
    if (check.signal !== 'gps' || check.state !== 'consistent') return null;
    if (typeof latitude !== 'number' || typeof longitude !== 'number') return null;
    return { latitude, longitude };
  }

  /** Brings an element of the report into view and gives it the focus. */
  protected show(id: string): void {
    const target = this.document.getElementById(id);
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target?.focus({ preventScroll: true });
  }

  protected another(): void {
    this.session.reset();
    this.document.defaultView?.scrollTo({ top: 0 });
  }
}
