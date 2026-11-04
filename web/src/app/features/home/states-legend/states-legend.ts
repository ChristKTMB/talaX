import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { STATES } from '../../../core/models/analysis';
import { StateBadge } from '../../../shared/ui/state-badge/state-badge';

@Component({
  selector: 'app-states-legend',
  imports: [StateBadge],
  template: `
    <section class="legend">
      <div class="legend__inner">
        <div class="legend__head">
          <h2>{{ i18n.t('legend.title') }}</h2>
          <p>{{ i18n.t('legend.intro') }}</p>
        </div>
        <ul class="legend__states">
          @for (state of states; track state) {
            <li>
              <app-state-badge [state]="state" [label]="i18n.t('state.' + state)" />
              <p>{{ i18n.t('state.' + state + '.meaning') }}</p>
            </li>
          }
        </ul>
      </div>
    </section>
  `,
  styleUrl: './states-legend.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatesLegend {
  protected readonly i18n = inject(I18n);
  protected readonly states = STATES;
}
