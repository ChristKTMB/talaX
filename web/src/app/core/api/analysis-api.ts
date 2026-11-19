import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, from, map, of, shareReplay, switchMap, throwError } from 'rxjs';
import { Language } from '../i18n/i18n';
import { AnalysisResult, Answers, ApiError } from '../models/analysis';

/** Same limit as the API (MAX_UPLOAD_MB): larger files are refused before sending. */
export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

@Injectable({ providedIn: 'root' })
export class AnalysisApi {
  private readonly http = inject(HttpClient);

  /** Asked once: whether this server looks up the weather. Off when unknown. */
  readonly health = this.http.get<Health>('/api/health').pipe(
    catchError(() => of({ weather: false })),
    shareReplay(1),
  );

  /** Sends the file for one analysis. The server keeps nothing afterwards. */
  analyze(file: File, lang: Language, answers: Answers = {}): Observable<AnalysisResult> {
    // Errors follow Accept-Language, as the API refuses before reading `lang`.
    return this.http
      .post<AnalysisResult>('/api/analyze', form(file, lang, answers), {
        headers: { 'Accept-Language': lang },
      })
      .pipe(catchError((error: HttpErrorResponse) => throwError(() => toApiError(error))));
  }

  /** The self-contained HTML report, made by the server from the same file sent again. */
  report(file: File, lang: Language, answers: Answers = {}): Observable<SavedReport> {
    return this.http
      .post('/api/analyze', form(file, lang, answers), {
        params: { format: 'html' },
        headers: { 'Accept-Language': lang },
        responseType: 'blob',
        observe: 'response',
      })
      .pipe(
        map((response) => ({
          blob: response.body ?? new Blob(),
          name: fileName(response.headers.get('Content-Disposition')),
        })),
        catchError((error: HttpErrorResponse) =>
          from(readBlobError(error)).pipe(switchMap((apiError) => throwError(() => apiError))),
        ),
      );
  }
}

/** Whether the server offers the weather lookup (TALAX_WEATHER). */
export interface Health {
  readonly weather: boolean;
}

export interface SavedReport {
  readonly blob: Blob;
  readonly name: string;
}

function form(file: File, lang: Language, { sky, claim, weather, conditions }: Answers): FormData {
  const body = new FormData();
  body.append('file', file, file.name);
  body.append('lang', lang);
  if (sky) body.append('sky', sky);
  if (claim) {
    body.append('latitude', String(claim.latitude));
    body.append('longitude', String(claim.longitude));
    body.append('taken_at', claim.takenAt);
  }
  if (weather) body.append('weather', 'true');
  if (weather && conditions) body.append('conditions', conditions);
  return body;
}

/** The API names the report after the file's hash, never after the file. */
export function fileName(disposition: string | null): string {
  const name = /filename="?(talax-[0-9a-f]+\.html)"?/.exec(disposition ?? '')?.[1];
  return name ?? 'talax-report.html';
}

/** Error bodies arrive as a Blob when a file was asked for. */
async function readBlobError(response: HttpErrorResponse): Promise<ApiError> {
  if (!(response.error instanceof Blob)) return toApiError(response);
  try {
    const body: unknown = JSON.parse(await response.error.text());
    return toApiError(new HttpErrorResponse({ status: response.status, error: body }));
  } catch {
    return toApiError(new HttpErrorResponse({ status: response.status, error: null }));
  }
}

export function toApiError(response: HttpErrorResponse): ApiError {
  if (response.status === 0) return { code: 'network', message: null };
  const body: unknown = response.error;
  const error = isRecord(body) && isRecord(body['error']) ? body['error'] : null;
  const code = typeof error?.['code'] === 'string' ? error['code'] : 'internal';
  const message = typeof error?.['message'] === 'string' ? error['message'] : null;
  return { code, message };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
