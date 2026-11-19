import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { AnalysisApi } from '../../../core/api/analysis-api';
import { I18n } from '../../../core/i18n/i18n';
import { AnalysisSession } from '../../../core/session/analysis-session';

/**
 * The weather lookup, offered only when the server enables it and never done
 * on its own: the place (rounded) and the date go to Open-Meteo, which may
 * keep them 90 days. The user is told before, and decides.
 */
@Component({
  selector: 'app-weather-offer',
  template: `
    @if (available()) {
      <section class="offer" aria-labelledby="weather-offer">
        <h2 id="weather-offer">{{ i18n.t('weather.title') }}</h2>
        <p>{{ i18n.t('weather.lead') }}</p>
        <p class="offer__warning">{{ i18n.t('weather.warning') }}</p>
        @if (placeAndTime()) {
          <button
            type="button"
            class="button"
            [disabled]="!session.canAnalyze()"
            (click)="session.lookUpWeather()"
          >
            {{ i18n.t('weather.ask') }}
          </button>
        } @else {
          <p class="offer__needed">{{ i18n.t('weather.needs_claim') }}</p>
        }
      </section>
    }
  `,
  styleUrl: './weather-offer.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WeatherOffer {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  private readonly health = toSignal(inject(AnalysisApi).health, { initialValue: null });
  /** The file or a claim gives a place and a time. */
  readonly placeAndTime = input(false);

  protected available(): boolean {
    return this.health()?.weather === true;
  }
}
