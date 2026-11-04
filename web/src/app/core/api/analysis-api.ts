import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { Language } from '../i18n/i18n';
import { AnalysisResult, ApiError, Sky } from '../models/analysis';

/** Same limit as the API (MAX_UPLOAD_MB): larger files are refused before sending. */
export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

@Injectable({ providedIn: 'root' })
export class AnalysisApi {
  private readonly http = inject(HttpClient);

  /** Sends the file for one analysis. The server keeps nothing afterwards. */
  analyze(file: File, lang: Language, sky?: Sky): Observable<AnalysisResult> {
    const form = new FormData();
    form.append('file', file, file.name);
    form.append('lang', lang);
    if (sky) form.append('sky', sky);
    // Errors follow Accept-Language, as the API refuses before reading `lang`.
    return this.http
      .post<AnalysisResult>('/api/analyze', form, { headers: { 'Accept-Language': lang } })
      .pipe(catchError((error: HttpErrorResponse) => throwError(() => toApiError(error))));
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
