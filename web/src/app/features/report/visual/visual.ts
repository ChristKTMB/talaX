import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';

/**
 * The image and the preview hidden in the file, side by side. A visual
 * exploration only: no state is drawn from it (project notes, section 3.2).
 */
@Component({
  selector: 'app-visual',
  templateUrl: './visual.html',
  styleUrl: './visual.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Visual {
  protected readonly i18n = inject(I18n);
  /** The uploaded image, from the browser's memory. */
  readonly image = input<string | null>(null);
  /** The embedded preview sent back by the API, as a data: URI. */
  readonly thumbnail = input<string | null>(null);

  protected readonly size = signal<{ width: number; height: number } | null>(null);
  protected readonly unreadable = signal(false);

  protected loaded(image: HTMLImageElement): void {
    this.size.set({ width: image.naturalWidth, height: image.naturalHeight });
  }
}
