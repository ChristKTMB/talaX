import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { CheckResult, Conditions } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';

const CONDITIONS: readonly Conditions[] = ['rain', 'snow', 'overcast', 'clear'];

/** Open-Meteo's licence (CC BY 4.0) asks for a link next to its data. */
export const WEATHER_CREDIT_URL = 'https://open-meteo.com/';

/** The model answered and waits for what the photo shows. */
export function asksForConditions(check: CheckResult): boolean {
  return check.signal === 'weather' && check.message === 'weather.no_observation';
}

/**
 * Under the weather check: what the photo shows (the engine reads the model,
 * the human observes), the answer given, and the credit Open-Meteo asks for.
 */
@Component({
  selector: 'app-weather-question',
  templateUrl: './weather-question.html',
  styleUrl: '../sky-question/sky-question.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WeatherQuestion {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  readonly check = input.required<CheckResult>();

  protected readonly conditions = CONDITIONS;
  protected readonly creditUrl = WEATHER_CREDIT_URL;
  protected readonly changing = signal(false);
  protected readonly observed = computed(() => {
    const seen = this.check().evidence['observed_conditions'];
    return CONDITIONS.find((known) => known === seen) ?? null;
  });
  /** The model answered: there is something to compare, and to credit. */
  protected readonly answered = computed(() => this.check().evidence['source'] === 'open-meteo');
  protected readonly asking = computed(
    () => asksForConditions(this.check()) || (this.answered() && this.changing()),
  );

  protected answer(conditions: Conditions): void {
    this.changing.set(false);
    void this.session.lookUpWeather(conditions);
  }
}
