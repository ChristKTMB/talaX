import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { CheckResult, Sky } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { Icon } from '../../../shared/ui/icon/icon';

const SKIES: readonly Sky[] = ['day', 'twilight', 'night'];

/** The engine computes, the human observes: the user says what the photo shows. */
export function asksForSky(check: CheckResult): boolean {
  return check.signal === 'solar' && check.message === 'solar.no_observation';
}

/**
 * Under the solar check: the question when the API waits for the user's
 * observation, or the answer given, which can be changed. Answering sends the
 * same file again with what the user saw.
 */
@Component({
  selector: 'app-sky-question',
  imports: [Icon],
  templateUrl: './sky-question.html',
  styleUrl: './sky-question.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SkyQuestion {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  readonly check = input.required<CheckResult>();

  protected readonly skies = SKIES;
  protected readonly changing = signal(false);
  /** The answer the API used, read from its evidence rather than kept aside. */
  protected readonly observed = computed(() => {
    const sky = this.check().evidence['observed_sky'];
    return SKIES.find((known) => known === sky) ?? null;
  });
  protected readonly asking = computed(() => asksForSky(this.check()) || this.changing());

  protected answer(sky: Sky): void {
    this.changing.set(false);
    void this.session.analyze(sky);
  }
}
