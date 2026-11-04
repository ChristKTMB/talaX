import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export type IconName =
  | 'upload'
  | 'trash'
  | 'terminal'
  | 'hourglass'
  | 'clock'
  | 'alert'
  | 'retry'
  | 'download'
  | 'day'
  | 'twilight'
  | 'night';

/** The line icons of the mockup, drawn on a 24 px grid, in the current text colour. */
@Component({
  selector: 'app-icon',
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      [attr.stroke-width]="weight()"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      @switch (name()) {
        @case ('upload') {
          <path d="M12 15V4M7.5 8.5 12 4l4.5 4.5" />
          <path d="M4 14v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5" />
        }
        @case ('trash') {
          <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" />
        }
        @case ('terminal') {
          <rect x="3" y="4" width="18" height="16" rx="1.5" />
          <path d="m7 10 3 2-3 2M12 15h5" />
        }
        @case ('hourglass') {
          <path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9" />
        }
        @case ('clock') {
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        }
        @case ('alert') {
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5v5.5M12 16.5h.01" />
        }
        @case ('retry') {
          <path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v4.5h-4.5" />
        }
        @case ('download') {
          <path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 20h14" />
        }
        @case ('day') {
          <circle cx="12" cy="12" r="4" />
          <path
            d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"
          />
        }
        @case ('twilight') {
          <path d="M6.5 17a5.5 5.5 0 0 1 11 0" />
          <path d="M2.5 17h19M12 7.5V10M5.6 10.6l1.6 1.6M18.4 10.6l-1.6 1.6M7 20.5h10" />
        }
        @case ('night') {
          <path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10Z" />
        }
      }
    </svg>
  `,
  host: { class: 'icon' },
  styles: `
    :host {
      display: inline-flex;
      flex: none;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Icon {
  readonly name = input.required<IconName>();
  readonly size = input(20);
  readonly weight = input(1.6);
}
