import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import busy from '../../../../../../docs/api-examples/error-busy.fr.json';
import { I18n } from '../../../core/i18n/i18n';
import { ApiError } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { UploadCard } from './upload-card';

function render(error: ApiError | null, retryIn = 0) {
  const session = {
    file: signal(new File(['x'], 'plage.jpg')),
    error: signal(error),
    retryIn: signal(retryIn),
    canAnalyze: signal(retryIn === 0),
    select: vi.fn(),
    analyze: vi.fn(),
  };
  TestBed.configureTestingModule({
    imports: [UploadCard],
    providers: [provideRouter([]), { provide: AnalysisSession, useValue: session }],
  });
  TestBed.inject(I18n).language.set('fr');
  const fixture = TestBed.createComponent(UploadCard);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('UploadCard', () => {
  it('shows the message of the API, and keeps the photo selected', () => {
    const page = render(busy.error);
    const alert = page.querySelector('[role="alert"]');
    expect(alert?.textContent).toContain('Service occupé');
    expect(alert?.textContent).toContain(busy.error.message);
    expect(alert?.textContent).toContain('Votre photo reste sélectionnée : plage.jpg');
    expect(alert?.querySelector('button')?.textContent).toContain('Réessayer');
  });

  it('counts down before a new attempt after a 429', () => {
    const page = render({ code: 'rate_limited', message: 'Trop d’analyses.' }, 42);
    const retry = page.querySelector<HTMLButtonElement>('[role="alert"] button');
    expect(retry?.disabled).toBe(true);
    expect(retry?.textContent).toContain('Réessayer dans 42 s');
    expect(page.querySelector('[role="alert"]')?.textContent).toContain('Pause d');
  });

  it('offers another file, not a retry, when sending the same one cannot work', () => {
    const page = render({ code: 'file_too_large', message: null });
    const alert = page.querySelector('[role="alert"]');
    expect(alert?.textContent).toContain('Fichier trop lourd');
    expect(alert?.textContent).toContain('Le fichier dépasse 50 Mo');
    expect(alert?.querySelector('button')).toBeNull();
    expect(alert?.querySelector('label[for="photo"]')?.textContent).toContain(
      'Choisir un autre fichier',
    );
    expect(page.querySelector<HTMLButtonElement>('button.submit')?.disabled).toBe(true);
  });

  it('shows a fixed text when the server gave none', () => {
    const page = render({ code: 'network', message: null });
    expect(page.querySelector('[role="alert"]')?.textContent).toContain('Vérifiez votre connexion');
  });
});
