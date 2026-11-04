import { TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';
import platformCopy from '../../../../../docs/api-examples/platform-copy.fr.json';
import { AnalysisApi, MAX_UPLOAD_BYTES } from '../api/analysis-api';
import { AnalysisResult, ApiError } from '../models/analysis';
import { AnalysisSession, RATE_LIMIT_PAUSE_SECONDS } from './analysis-session';

const photo = (size = 10) => new File([new Uint8Array(size)], 'photo.jpg', { type: 'image/jpeg' });

function setUp(answer: () => Observable<AnalysisResult>) {
  const analyze = vi.fn(answer);
  TestBed.configureTestingModule({ providers: [{ provide: AnalysisApi, useValue: { analyze } }] });
  return { session: TestBed.inject(AnalysisSession), analyze };
}

describe('AnalysisSession', () => {
  beforeEach(() => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:photo');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
  });
  afterEach(() => vi.useRealTimers());

  it('keeps the result of an analysis and shows the image from memory', async () => {
    const { session } = setUp(() => of(platformCopy as AnalysisResult));
    session.select(photo());
    expect(session.imageUrl()).toBe('blob:photo');
    await session.analyze();
    expect(session.phase()).toBe('done');
    expect(session.result()?.integrity.verdict).toBe('reprocessed');
  });

  it('refuses a file over 50 MB without sending it', async () => {
    const { session, analyze } = setUp(() => of(platformCopy as AnalysisResult));
    session.select(photo(MAX_UPLOAD_BYTES + 1));
    expect(session.error()?.code).toBe('file_too_large');
    await session.analyze();
    expect(analyze).not.toHaveBeenCalled();
  });

  it('keeps the file selected after a failure, so it can be sent again', async () => {
    const error: ApiError = { code: 'busy', message: 'Le service est occupé.' };
    const { session } = setUp(() => throwError(() => error));
    session.select(photo());
    await session.analyze();
    expect(session.phase()).toBe('idle');
    expect(session.error()).toEqual(error);
    expect(session.file()?.name).toBe('photo.jpg');
    expect(session.canAnalyze()).toBe(true);
  });

  it('waits a minute after a 429, even when another file is chosen', async () => {
    vi.useFakeTimers();
    const { session, analyze } = setUp(() =>
      throwError(() => ({ code: 'rate_limited', message: 'Trop d’analyses.' })),
    );
    session.select(photo());
    await session.analyze();
    expect(session.retryIn()).toBe(RATE_LIMIT_PAUSE_SECONDS);
    expect(session.canAnalyze()).toBe(false);

    session.select(photo());
    expect(session.error()?.code).toBe('rate_limited');
    await session.analyze();
    expect(analyze).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(RATE_LIMIT_PAUSE_SECONDS * 1000);
    expect(session.retryIn()).toBe(0);
    expect(session.canAnalyze()).toBe(true);
  });

  it('forgets the file and releases the image on reset', async () => {
    const { session } = setUp(() => of(platformCopy as AnalysisResult));
    session.select(photo());
    await session.analyze();
    session.reset();
    expect(session.file()).toBeNull();
    expect(session.result()).toBeNull();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:photo');
  });
});
