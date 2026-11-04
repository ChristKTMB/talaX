import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { I18n, LANGUAGES } from '../../core/i18n/i18n';
import { SOURCE_URL } from '../../core/links';

@Component({
  selector: 'app-footer',
  templateUrl: './footer.html',
  styleUrl: './footer.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Footer {
  protected readonly i18n = inject(I18n);
  protected readonly languages = LANGUAGES;
  protected readonly sourceUrl = SOURCE_URL;
}
