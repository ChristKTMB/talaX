import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { CheckResult } from '../../../core/models/analysis';
import { StateBadge } from '../../../shared/ui/state-badge/state-badge';

/**
 * One check of the report. The state is never shown without its explanation,
 * and every text comes from the API as plain text (metadata are hostile).
 */
@Component({
  selector: 'app-check-row',
  imports: [StateBadge],
  template: `
    <div class="check__head">
      <h3>{{ result().name }}</h3>
      <app-state-badge [state]="result().state" [label]="result().label" />
    </div>
    <div class="check__body">
      <p>{{ result().explanation }}</p>
      <ng-content />
    </div>
  `,
  host: {
    '[id]': '"check-" + result().signal',
    '[class.check--suspicious]': 'result().state === "suspicious"',
    tabindex: '-1',
  },
  styleUrl: './check-row.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckRow {
  readonly result = input.required<CheckResult>();
}
