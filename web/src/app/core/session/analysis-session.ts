import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AnalysisApi, MAX_UPLOAD_BYTES } from '../api/analysis-api';
import { I18n } from '../i18n/i18n';
import { AnalysisResult, ApiError, Sky } from '../models/analysis';

/** After a 429, nginx refuses for about a minute: retrying sooner only fails again. */
export const RATE_LIMIT_PAUSE_SECONDS = 60;

export type Phase = 'idle' | 'analyzing' | 'done';

/**
 * The file being examined and its last analysis. Everything lives in memory
 * only: nothing is written to the device, and reloading the page forgets it.
 */
@Injectable({ providedIn: 'root' })
export class AnalysisSession {
  private readonly api = inject(AnalysisApi);
  private readonly i18n = inject(I18n);

  readonly file = signal<File | null>(null);
  /** The chosen image, shown from the browser's memory (the server never sends it back). */
  readonly imageUrl = signal<string | null>(null);
  readonly phase = signal<Phase>('idle');
  readonly result = signal<AnalysisResult | null>(null);
  readonly error = signal<ApiError | null>(null);
  /** Seconds before a new attempt is allowed, after a 429. */
  readonly retryIn = signal(0);
  readonly canAnalyze = computed(
    () => this.file() !== null && this.phase() !== 'analyzing' && this.retryIn() === 0,
  );

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

  async analyze(sky?: Sky): Promise<void> {
    const file = this.file();
    if (!file || !this.canAnalyze() || this.error()?.code === 'file_too_large') return;
    this.error.set(null);
    this.phase.set('analyzing');
    try {
      const result = await firstValueFrom(this.api.analyze(file, this.i18n.language(), sky));
      this.result.set(result);
      this.phase.set('done');
    } catch (error) {
      this.phase.set(this.result() ? 'done' : 'idle');
      this.fail(error as ApiError);
    }
  }

  /** Back to the empty form; the image is released from memory. */
  reset(): void {
    this.clearFile();
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
    if (this.retryIn() === 0) this.error.set(null);
  }
}
