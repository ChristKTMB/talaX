import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import cameraOriginal from '../../../../../docs/api-examples/camera-original.fr.json';
import edited from '../../../../../docs/api-examples/edited.fr.json';
import gpsMasked from '../../../../../docs/api-examples/gps-masked.fr.json';
import platformCopy from '../../../../../docs/api-examples/platform-copy.fr.json';
import pngWithoutMetadata from '../../../../../docs/api-examples/png-without-metadata.fr.json';
import solarContradiction from '../../../../../docs/api-examples/solar-contradiction.fr.json';
import wrongExtension from '../../../../../docs/api-examples/wrong-extension.fr.json';
import { I18n } from '../../core/i18n/i18n';
import { AnalysisResult } from '../../core/models/analysis';
import { AnalysisSession } from '../../core/session/analysis-session';
import { Report } from './report';

const EXAMPLES = {
  cameraOriginal,
  edited,
  gpsMasked,
  platformCopy,
  pngWithoutMetadata,
  solarContradiction,
  wrongExtension,
} as unknown as Record<string, AnalysisResult>;

function render(result: AnalysisResult) {
  const session = {
    result: signal(result),
    file: signal(new File(['x'], 'plage.jpg')),
    imageUrl: signal('blob:photo'),
    reset: vi.fn(),
  };
  TestBed.configureTestingModule({
    imports: [Report],
    providers: [{ provide: AnalysisSession, useValue: session }],
  });
  TestBed.inject(I18n).language.set('fr');
  const fixture = TestBed.createComponent(Report);
  fixture.detectChanges();
  return { page: fixture.nativeElement as HTMLElement, session };
}

describe('Report', () => {
  beforeEach(() => {
    // jsdom cannot scroll.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined);
  });

  for (const [name, example] of Object.entries(EXAMPLES)) {
    it(`${name}: shows every check, each state with its explanation`, () => {
      const { page } = render(example);
      const rows = [...page.querySelectorAll('app-check-row')];
      expect(rows.length).toBe(example.results.length);
      example.results.forEach((check, index) => {
        const text = rows[index]?.textContent ?? '';
        expect(text).toContain(check.name);
        expect(text).toContain(check.label);
        expect(text).toContain(check.explanation);
      });
      expect(page.querySelector('h1')?.textContent).toContain(example.integrity.label);
      expect(page.textContent).toContain(example.integrity.explanation);
      expect(page.textContent).toContain(example.disclaimer);
    });
  }

  it('puts a banner at the top for a suspicious check only', () => {
    expect(render(EXAMPLES['solarContradiction']!).page.querySelectorAll('.alert').length).toBe(1);
    TestBed.resetTestingModule();
    // "To check" (an editor recorded) never earns a banner.
    expect(render(EXAMPLES['edited']!).page.querySelector('.alert')).toBeNull();
  });

  it('names the suspicious check in the banner and leads to it', () => {
    const { page } = render(EXAMPLES['solarContradiction']!);
    const banner = page.querySelector('.alert');
    expect(banner?.textContent).toContain('Cohérence solaire :');
    expect(banner?.textContent).toContain('à examiner avant toute conclusion');
    expect(page.querySelector('#check-solar.check--suspicious')).not.toBeNull();
  });

  it('shows the image and the preview side by side only when the file holds one', () => {
    const original = render(EXAMPLES['cameraOriginal']!).page;
    expect(original.querySelectorAll('app-visual figure').length).toBe(2);
    expect(original.textContent).toContain('Exploration visuelle, non concluante');
    TestBed.resetTestingModule();
    const copy = render(EXAMPLES['platformCopy']!).page;
    expect(copy.querySelectorAll('app-visual figure').length).toBe(1);
    expect(copy.textContent).toContain("Ce fichier ne contient pas d'aperçu intégré.");
  });

  it('shows text written in the metadata as text, never as markup', () => {
    const hostile = structuredClone(EXAMPLES['edited']!);
    const first = {
      ...hostile.results[0]!,
      explanation: '<img src=x onerror="alert(1)"><b>Photoshop</b>',
    };
    const forged = { ...hostile, results: [first, ...hostile.results.slice(1)] };
    const { page } = render(forged);
    expect(page.querySelector('app-check-row img')).toBeNull();
    expect(page.querySelector('app-check-row b')).toBeNull();
    expect(page.querySelector('app-check-row')?.textContent).toContain('<b>Photoshop</b>');
  });

  it('gives the technical details, the fingerprint when one matched', () => {
    const { page } = render(EXAMPLES['platformCopy']!);
    const details = page.querySelector('.details')?.textContent ?? '';
    expect(details).toContain(platformCopy.file.sha256);
    expect(details).toContain('2026-01-01 12:00 UTC');
    expect(details).toContain('whatsapp-gallery');
    expect(details).toContain('2 321 octets');
  });

  it('goes back to the form with "Analyse another file"', () => {
    const { page, session } = render(EXAMPLES['platformCopy']!);
    page.querySelector<HTMLButtonElement>('.actions button')?.click();
    expect(session.reset).toHaveBeenCalled();
  });
});
