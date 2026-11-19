import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { I18n } from '../../../core/i18n/i18n';
import { Claim } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { Place, PlacePicker } from './place-picker';

// "-4.3217, 15.3125" as map services copy it, or "-4,3217 ; 15,3125" in French.
const DOT_DECIMALS = /^\s*(-?\d{1,3}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/;
const COMMA_DECIMALS = /^\s*(-?\d{1,3}(?:,\d+)?)\s*[;\s]\s*(-?\d{1,3}(?:,\d+)?)\s*$/;

/** Latitude and longitude typed or pasted in, or null when they cannot be read. */
export function parsePlace(text: string): Place | null {
  const match = DOT_DECIMALS.exec(text) ?? COMMA_DECIMALS.exec(text);
  if (!match) return null;
  const latitude = Number(match[1]!.replace(',', '.'));
  const longitude = Number(match[2]!.replace(',', '.'));
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return null;
  return { latitude, longitude };
}

/** Coordinates keep the decimal point in both languages (project notes). */
export function formatPlace(place: Place): string {
  return `${place.latitude.toFixed(5)}, ${place.longitude.toFixed(5)}`;
}

/**
 * Manual mode: the place and time a caption claims. Tala X then computes the
 * sun there and then, and compares the claim with the file. Shown open when
 * the file lacks a position or a time; otherwise behind "Does the caption say
 * otherwise?", since a caption can lie about a camera original too.
 */
@Component({
  selector: 'app-claim-form',
  imports: [PlacePicker],
  templateUrl: './claim-form.html',
  styleUrl: './claim-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimForm {
  protected readonly i18n = inject(I18n);
  protected readonly session = inject(AnalysisSession);
  /** The file lacks what the solar check needs: the form comes first. */
  readonly needed = input(false);

  protected readonly editing = signal(false);
  protected readonly placeText = signal('');
  protected readonly date = signal('');
  protected readonly time = signal('');
  protected readonly tried = signal(false);

  protected readonly place = computed(() => parsePlace(this.placeText()));
  protected readonly placeError = computed(
    () => this.placeText().trim() !== '' && this.place() === null,
  );
  protected readonly claim = computed<Claim | null>(() => {
    const place = this.place();
    if (!place || !/^\d{4}-\d{2}-\d{2}$/.test(this.date()) || !/^\d{2}:\d{2}/.test(this.time())) {
      return null;
    }
    return { ...place, takenAt: `${this.date()}T${this.time().slice(0, 5)}` };
  });
  protected readonly open = computed(
    () => this.editing() || (this.needed() && this.session.claim() === null),
  );
  /** The claim the last analysis used, written out. */
  protected readonly current = computed(() => {
    const claim = this.session.claim();
    if (!claim) return null;
    const [date, time] = claim.takenAt.split('T');
    return { place: formatPlace(claim), date: this.readableDate(date!), time: time! };
  });

  protected start(): void {
    const claim = this.session.claim();
    if (claim) {
      this.placeText.set(formatPlace(claim));
      this.date.set(claim.takenAt.slice(0, 10));
      this.time.set(claim.takenAt.slice(11, 16));
    }
    this.tried.set(false);
    this.editing.set(true);
  }

  protected pick(place: Place): void {
    this.placeText.set(formatPlace(place));
  }

  protected submit(): void {
    this.tried.set(true);
    const claim = this.claim();
    if (!claim || !this.session.canAnalyze()) return;
    this.editing.set(false);
    void this.session.declare(claim);
  }

  protected withdraw(): void {
    this.editing.set(false);
    void this.session.declare(null);
  }

  protected value(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  private readableDate(iso: string): string {
    const locale = this.i18n.language() === 'fr' ? 'fr-FR' : 'en-GB';
    return new Intl.DateTimeFormat(locale, { dateStyle: 'long', timeZone: 'UTC' }).format(
      new Date(`${iso}T00:00:00Z`),
    );
  }
}
