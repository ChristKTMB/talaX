import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n, LANGUAGES } from '../../core/i18n/i18n';
import { PageHead } from '../../core/i18n/page-head';
import { SOURCE_URL } from '../../core/links';

@Component({
  selector: 'app-footer',
  imports: [RouterLink],
  templateUrl: './footer.html',
  styleUrl: './footer.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Footer {
  protected readonly i18n = inject(I18n);
  protected readonly head = inject(PageHead);
  protected readonly languages = LANGUAGES;
  protected readonly sourceUrl = SOURCE_URL;
}
