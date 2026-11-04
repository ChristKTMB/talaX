import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import busy from '../../../../../docs/api-examples/error-busy.fr.json';
import tooLarge from '../../../../../docs/api-examples/error-file-too-large.en.json';
import platformCopy from '../../../../../docs/api-examples/platform-copy.fr.json';
import { AnalysisApi, toApiError } from './analysis-api';

describe('toApiError', () => {
  it('reads the error body of the API, as documented in docs/api-examples', () => {
    const response = new HttpErrorResponse({ status: 503, error: { error: busy.error } });
    expect(toApiError(response)).toEqual({ code: 'busy', message: busy.error.message });
    const large = new HttpErrorResponse({ status: 413, error: { error: tooLarge.error } });
    expect(toApiError(large).code).toBe('file_too_large');
  });

  it('calls a missing answer a network error, without text to show', () => {
    expect(toApiError(new HttpErrorResponse({ status: 0 }))).toEqual({
      code: 'network',
      message: null,
    });
  });

  it('never shows an unexpected body: an odd answer becomes an internal error', () => {
    const response = new HttpErrorResponse({ status: 502, error: '<html>Bad gateway</html>' });
    expect(toApiError(response)).toEqual({ code: 'internal', message: null });
  });
});

describe('AnalysisApi', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('sends the file, the language and the sky, with errors asked in the same language', async () => {
    const api = TestBed.inject(AnalysisApi);
    const http = TestBed.inject(HttpTestingController);
    const file = new File(['x'], 'photo.jpg', { type: 'image/jpeg' });
    const answer = firstValueFrom(api.analyze(file, 'fr', 'night'));

    const request = http.expectOne('/api/analyze');
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Accept-Language')).toBe('fr');
    const form = request.request.body as FormData;
    expect((form.get('file') as File).name).toBe('photo.jpg');
    expect(form.get('lang')).toBe('fr');
    expect(form.get('sky')).toBe('night');
    request.flush(platformCopy);

    expect((await answer).integrity.verdict).toBe('reprocessed');
    http.verify();
  });
});
