import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReverseSearch as Search } from '../../../core/models/analysis';

/**
 * For every file: where to look for earlier copies of the photo. The user
 * uploads it there; Tala X sends nothing, and no referrer goes with the link.
 */
@Component({
  selector: 'app-reverse-search',
  templateUrl: './reverse-search.html',
  styleUrl: './reverse-search.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReverseSearch {
  readonly search = input.required<Search>();
}
