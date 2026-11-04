import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  computed,
  inject,
  input,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { LEGAL_PAGES } from '../../../generated/legal';
import { I18n, Language } from '../../core/i18n/i18n';

export type LegalPageName = 'terms' | 'privacy';

export interface LegalDocument {
  readonly title: string;
  /** The "draft, not yet in force" notice, shown as a banner while it exists. */
  readonly draft: string;
  /** Titles of the numbered sections, in order. */
  readonly toc: readonly string[];
  readonly html: string;
}

export type LegalPages = Readonly<Record<LegalPageName, Readonly<Record<Language, LegalDocument>>>>;

/**
 * Terms of use and privacy policy, from docs/legal/ (the only source), turned
 * into HTML at build time by scripts/sync-docs.mjs. The HTML is ours, not the
 * API's: it is the only place where the front inserts markup.
 */
@Component({
  selector: 'app-legal-page',
  imports: [RouterLink],
  templateUrl: './legal-page.html',
  styleUrl: './legal-page.scss',
  host: { '(click)': 'follow($event)' },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LegalPage {
  protected readonly i18n = inject(I18n);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);

  /** From the route's data. */
  readonly page = input.required<LegalPageName>();
  protected readonly content = computed(() => LEGAL_PAGES[this.page()][this.i18n.language()]);
  protected readonly other = computed<LegalPageName>(() =>
    this.page() === 'terms' ? 'privacy' : 'terms',
  );

  protected show(index: number): void {
    const headings = this.document.querySelectorAll<HTMLElement>('.document__body h2');
    headings[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /** Links inside the document stay in the application instead of reloading it. */
  protected follow(event: MouseEvent): void {
    const link = (event.target as HTMLElement | null)?.closest('a');
    const href = link?.getAttribute('href');
    if (href?.startsWith('/') && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      void this.router.navigateByUrl(href);
    }
  }
}
