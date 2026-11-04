import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n } from '../../core/i18n/i18n';
import { AnalysisSession } from '../../core/session/analysis-session';
import { Report } from '../report/report';
import { Analyzing } from './analyzing/analyzing';
import { StatesLegend } from './states-legend/states-legend';
import { UploadCard } from './upload-card/upload-card';

/** One address for the form, the wait and the report: a report has no address of its own. */
@Component({
  selector: 'app-home',
  imports: [UploadCard, Analyzing, StatesLegend, Report],
  templateUrl: './home.html',
  styleUrl: './home.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  protected readonly features = [1, 2, 3, 4];
}
