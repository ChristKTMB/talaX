import { ChangeDetectionStrategy, Component, DOCUMENT, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { I18n } from './core/i18n/i18n';
import { Footer } from './layout/footer/footer';
import { Header } from './layout/header/header';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Header, Footer],
  template: `
    <a class="skip" href="#main" (click)="skip($event)">{{ i18n.t('app.skip') }}</a>
    <app-header />
    <main id="main" tabindex="-1"><router-outlet /></main>
    <app-footer />
  `,
  styleUrl: './app.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly i18n = inject(I18n);
  private readonly document = inject(DOCUMENT);

  /** Goes to the main area without changing the address. */
  protected skip(event: Event): void {
    event.preventDefault();
    this.document.getElementById('main')?.focus();
  }
}
