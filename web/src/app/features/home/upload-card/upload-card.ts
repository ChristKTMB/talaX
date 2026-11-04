import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { I18n } from '../../../core/i18n/i18n';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { Icon } from '../../../shared/ui/icon/icon';
import { FINAL_ERRORS, Problem } from '../../../shared/ui/problem/problem';
import { RetryButton } from '../../../shared/ui/retry-button/retry-button';

@Component({
  selector: 'app-upload-card',
  imports: [RouterLink, Icon, Problem, RetryButton],
  templateUrl: './upload-card.html',
  styleUrl: './upload-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadCard {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  protected readonly dragging = signal(false);

  /** Sending the same file again cannot fix these: another file is needed. */
  protected readonly final = computed(() => FINAL_ERRORS.has(this.session.error()?.code ?? ''));

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
