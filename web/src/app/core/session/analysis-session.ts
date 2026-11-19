import { DOCUMENT, DestroyRef, Injectable, computed, effect, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AnalysisApi, MAX_UPLOAD_BYTES } from '../api/analysis-api';
import { I18n } from '../i18n/i18n';
import { AnalysisResult, Answers, ApiError, Claim, Conditions, Sky } from '../models/analysis';

/** After a 429, nginx refuses for about a minute: retrying sooner only fails again. */
export const RATE_LIMIT_PAUSE_SECONDS = 60;

export type Phase = 'idle' | 'analyzing' | 'done';
type Action = 'analyze' | 'download';

/**
 * The file being examined and its last analysis. Everything lives in memory
 * only: nothing is written to the device, and reloading the page forgets it.
 * Each request sends the file again; the server keeps nothing in between.
 */
@Injectable({ providedIn: 'root' })
export class AnalysisSession {
  private readonly api = inject(AnalysisApi);
  private readonly i18n = inject(I18n);
  private readonly document = inject(DOCUMENT);

  readonly file = signal<File | null>(null);
  /** The chosen image, shown from the browser's memory (the server never sends it back). */
  readonly imageUrl = signal<string | null>(null);
  readonly phase = signal<Phase>('idle');
  readonly result = signal<AnalysisResult | null>(null);
  /** What the user saw in the photo, sent with every later request for this file. */
  readonly sky = signal<Sky | null>(null);
  /** The place and time the caption claims, sent with every later request too. */
  readonly claim = signal<Claim | null>(null);
  /** The user agreed to send the place and date to Open-Meteo, for this file. */
  readonly weather = signal(false);
  /** The weather the user sees in the photo. */
  readonly conditions = signal<Conditions | null>(null);
  readonly downloading = signal(false);
  readonly error = signal<ApiError | null>(null);
  /** Seconds before a new attempt is allowed, after a 429. */
  readonly retryIn = signal(0);
  readonly busy = computed(() => this.phase() === 'analyzing' || this.downloading());
  readonly canAnalyze = computed(
    () => this.file() !== null && !this.busy() && this.retryIn() === 0,
  );

  private lastAction: Action = 'analyze';
  /** The language a report was last asked again in, so that it is asked only once. */
  private relanguaged: string | null = null;

  /**
   * Changing the language applies to the whole application, report included:
   * a displayed report is asked again in the new language (the file is sent
   * again), never left half in one language. Once per language: after a
   * failure, the user retries.
   */
  private readonly followLanguage = effect(() => {
    const language = this.i18n.language();
    const result = this.result();
    if (!result || result.lang === language || this.relanguaged === language) return;
    if (this.phase() !== 'done' || !this.canAnalyze()) return;
    this.relanguaged = language;
    void this.analyze();
  });
  private countdown: ReturnType<typeof setInterval> | undefined;

  constructor() {
    inject(DestroyRef).onDestroy(() => {
      clearInterval(this.countdown);
      this.clearFile();
    });
  }

  select(file: File): void {
    this.clearFile();
    this.file.set(file);
    this.imageUrl.set(URL.createObjectURL(file));
    if (file.size > MAX_UPLOAD_BYTES) {
      this.error.set({ code: 'file_too_large', message: null });
    }
  }

  /**
   * Checks the place and time a caption claims, or with null goes back to the
   * file's own. The sky already given stays: it describes the photo, whatever
   * the claim.
   */
  declare(claim: Claim | null): Promise<void> {
    this.claim.set(claim);
    return this.analyze();
  }

  /** Looks up the weather for this file, from now on, then with what the photo shows. */
  lookUpWeather(conditions: Conditions | null = null): Promise<void> {
    this.weather.set(true);
    if (conditions) this.conditions.set(conditions);
    return this.analyze();
  }

  /** Analyses the file; with `sky`, again, with what the user saw in the photo. */
  async analyze(sky?: Sky): Promise<void> {
    const file = this.file();
    if (!file || !this.canAnalyze() || this.error()?.code === 'file_too_large') return;
    if (sky) this.sky.set(sky);
    this.lastAction = 'analyze';
    this.error.set(null);
    this.phase.set('analyzing');
    try {
      const result = await firstValueFrom(
        this.api.analyze(file, this.i18n.language(), this.answers()),
      );
      this.result.set(result);
      this.phase.set('done');
    } catch (error) {
      this.phase.set(this.result() ? 'done' : 'idle');
      this.fail(error as ApiError);
    }
  }

  /** Saves the self-contained HTML report of the current analysis. */
  async download(): Promise<void> {
    const file = this.file();
    if (!file || !this.result() || !this.canAnalyze()) return;
    this.lastAction = 'download';
    this.error.set(null);
    this.downloading.set(true);
    try {
      const report = await firstValueFrom(
        this.api.report(file, this.i18n.language(), this.answers()),
      );
      this.save(report.blob, report.name);
    } catch (error) {
      this.fail(error as ApiError);
    } finally {
      this.downloading.set(false);
    }
  }

  /** Does again what failed last. */
  retry(): Promise<void> {
    return this.lastAction === 'download' ? this.download() : this.analyze();
  }

  /** Back to the empty form; the image is released from memory. */
  reset(): void {
    this.clearFile();
  }

  private answers(): Answers {
    return {
      sky: this.sky(),
      claim: this.claim(),
      weather: this.weather(),
      conditions: this.conditions(),
    };
  }

  private save(blob: Blob, name: string): void {
    const url = URL.createObjectURL(blob);
    const link = this.document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  private fail(error: ApiError): void {
    this.error.set(error);
    if (error.code === 'rate_limited') this.pause(RATE_LIMIT_PAUSE_SECONDS);
  }

  private pause(seconds: number): void {
    clearInterval(this.countdown);
    this.retryIn.set(seconds);
    this.countdown = setInterval(() => {
      this.retryIn.update((left) => Math.max(0, left - 1));
      if (this.retryIn() === 0) clearInterval(this.countdown);
    }, 1000);
  }

  /** Forgets the file and its analysis. A running pause after a 429 is kept. */
  private clearFile(): void {
    const url = this.imageUrl();
    if (url) URL.revokeObjectURL(url);
    this.file.set(null);
    this.imageUrl.set(null);
    this.phase.set('idle');
    this.result.set(null);
    this.sky.set(null);
    this.claim.set(null);
    this.weather.set(false);
    this.conditions.set(null);
    this.lastAction = 'analyze';
    this.relanguaged = null;
    if (this.retryIn() === 0) this.error.set(null);
  }
}
