import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { State } from '../../../core/models/analysis';

/**
 * The label of a verdict state. Its colour never carries the meaning alone:
 * the word and a distinct shape are always there.
 */
@Component({
  selector: 'app-state-badge',
  template: `
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      @switch (state()) {
        @case ('consistent') {
          <rect x="2" y="2" width="10" height="10" fill="currentColor" />
        }
        @case ('to_check') {
          <rect
            x="2.75"
            y="2.75"
            width="8.5"
            height="8.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          />
          <rect x="2.75" y="2.75" width="4.25" height="8.5" fill="currentColor" />
        }
        @case ('suspicious') {
          <rect x="1.5" y="1.5" width="11" height="11" fill="currentColor" />
          <path
            d="M4.5 4.5l5 5M9.5 4.5l-5 5"
            class="cross"
            stroke-width="1.6"
            stroke-linecap="round"
          />
        }
        @case ('unverifiable') {
          <rect
            x="2.75"
            y="2.75"
            width="8.5"
            height="8.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-dasharray="2.2 1.6"
          />
        }
      }
    </svg>
    {{ label() }}
  `,
  host: { '[class]': '"badge badge--" + state()' },
  styleUrl: './state-badge.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StateBadge {
  readonly state = input.required<State>();
  readonly label = input.required<string>();
}
