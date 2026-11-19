import { ChangeDetectionStrategy, Component, DOCUMENT, inject, input, signal } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { SourceRequest as Request } from '../../../core/models/analysis';

type Copy = 'idle' | 'copied' | 'failed';

/**
 * For a copy or an undetermined file: the message that asks the source for the
 * original, ready to copy, with the risk it carries for the source.
 */
@Component({
  selector: 'app-source-request',
  templateUrl: './source-request.html',
  styleUrl: './source-request.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SourceRequest {
  protected readonly i18n = inject(I18n);
  private readonly document = inject(DOCUMENT);
  readonly request = input.required<Request>();

  protected readonly copy = signal<Copy>('idle');

  protected async copyMessage(): Promise<void> {
    try {
      await this.document.defaultView?.navigator.clipboard.writeText(this.request().message);
      this.copy.set('copied');
    } catch {
      // No clipboard (insecure page, refused permission): the text stays selectable.
      this.copy.set('failed');
    }
  }
}
