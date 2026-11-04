import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { Icon } from '../../../shared/ui/icon/icon';

/** Shown while the server analyses. It gives no progress: the server reports none. */
@Component({
  selector: 'app-analyzing',
  imports: [Icon],
  templateUrl: './analyzing.html',
  styleUrl: './analyzing.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Analyzing {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  protected readonly cells = Array.from({ length: 25 }, (_, index) => index);
}
