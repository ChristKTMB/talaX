import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { Icon } from '../icon/icon';

/** "Try again", disabled with a countdown during the pause that follows a 429. */
@Component({
  selector: 'app-retry-button',
  imports: [Icon],
  template: `
    <button
      [type]="submit() ? 'submit' : 'button'"
      class="retry"
      [disabled]="disabled()"
      (click)="retry.emit()"
    >
      <app-icon name="retry" [size]="16" [weight]="1.8" />
      @if (waitSeconds() > 0) {
        {{ i18n.t('error.retry_in', { seconds: waitSeconds() }) }}
      } @else {
        {{ i18n.t('error.retry') }}
      }
    </button>
  `,
  styles: `
    .retry {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
      padding: 0 18px;
      border: 1px solid var(--ink);
      border-radius: 4px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;

      &:disabled {
        cursor: not-allowed;
        opacity: 0.55;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RetryButton {
  protected readonly i18n = inject(I18n);
  readonly waitSeconds = input(0);
  readonly disabled = input(false);
  /** Inside the upload form, the button submits it. */
  readonly submit = input(false);
  readonly retry = output();
}
