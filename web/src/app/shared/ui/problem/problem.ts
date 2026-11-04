import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { ApiError } from '../../../core/models/analysis';
import { Icon, IconName } from '../icon/icon';

/** Errors that sending the same file again cannot fix. */
export const FINAL_ERRORS: ReadonlySet<string> = new Set([
  'file_too_large',
  'analysis_failed',
  'invalid_request',
]);
const TITLED = new Set(['file_too_large', 'busy', 'rate_limited', 'analysis_failed', 'network']);
const ICONS: Readonly<Record<string, IconName>> = { rate_limited: 'hourglass', busy: 'clock' };

/**
 * An error of the service, in sand, never in red: red belongs to the
 * "suspicious" state. The text comes from the API or nginx when they gave one.
 * The action (retry, another file) is projected by the caller.
 */
@Component({
  selector: 'app-problem',
  imports: [Icon],
  template: `
    <div class="problem__body">
      <app-icon [name]="icon()" [size]="22" />
      <div class="problem__text">
        <p class="problem__title">{{ title() }}</p>
        <p>{{ text() }}</p>
        @if (fileName(); as name) {
          <p class="problem__kept">{{ i18n.t('error.kept', { name }) }}</p>
        }
      </div>
    </div>
    <ng-content />
  `,
  host: { role: 'alert' },
  styleUrl: './problem.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Problem {
  protected readonly i18n = inject(I18n);
  readonly error = input.required<ApiError>();
  /** The file still selected, named so the user knows nothing was lost. */
  readonly fileName = input<string | null>(null);

  private readonly kind = computed(() =>
    TITLED.has(this.error().code) ? this.error().code : 'other',
  );
  protected readonly icon = computed(() => ICONS[this.error().code] ?? 'alert');
  protected readonly title = computed(() => this.i18n.t(`error.title.${this.kind()}`));
  protected readonly text = computed(() => {
    const own = ['file_too_large', 'network'].includes(this.kind()) ? this.kind() : 'other';
    return this.error().message ?? this.i18n.t(`error.text.${own}`);
  });
}
