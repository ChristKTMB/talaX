import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n } from '../../../core/i18n/i18n';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { Icon, IconName } from '../../../shared/ui/icon/icon';

/** Errors that sending the same file again cannot fix. */
const FINAL_ERRORS = new Set(['file_too_large', 'analysis_failed', 'invalid_request']);
const KNOWN_TITLES = new Set([
  'file_too_large',
  'busy',
  'rate_limited',
  'analysis_failed',
  'network',
]);
const ICONS: Readonly<Record<string, IconName>> = { rate_limited: 'hourglass', busy: 'clock' };

@Component({
  selector: 'app-upload-card',
  imports: [RouterLink, Icon],
  templateUrl: './upload-card.html',
  styleUrl: './upload-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadCard {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  protected readonly dragging = signal(false);

  protected readonly problem = computed(() => {
    const error = this.session.error();
    if (!error) return null;
    const kind = KNOWN_TITLES.has(error.code) ? error.code : 'other';
    return {
      icon: ICONS[error.code] ?? 'alert',
      title: this.i18n.t(`error.title.${kind}`),
      text:
        error.message ??
        this.i18n.t(
          `error.text.${kind === 'file_too_large' || kind === 'network' ? kind : 'other'}`,
        ),
      final: FINAL_ERRORS.has(error.code),
    };
  });

  protected pick(input: HTMLInputElement): void {
    const file = input.files?.[0];
    if (file) this.session.select(file);
    // The same file can be chosen again after an error.
    input.value = '';
  }

  protected dragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(true);
  }

  protected drop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files[0];
    if (file) this.session.select(file);
  }

  protected submit(event: Event): void {
    event.preventDefault();
    void this.session.analyze();
  }
}
