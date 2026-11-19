import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import weatherAsked from '../../../../../../docs/api-examples/weather-asked.fr.json';
import weatherToCheck from '../../../../../../docs/api-examples/weather-to-check.fr.json';
import { AnalysisApi } from '../../../core/api/analysis-api';
import { I18n } from '../../../core/i18n/i18n';
import { AnalysisResult, CheckResult } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { WeatherOffer } from './weather-offer';
import { WeatherQuestion } from './weather-question';

const weatherOf = (example: unknown) =>
  (example as AnalysisResult).results.find((check) => check.signal === 'weather')!;

function setUp(enabled: boolean) {
  const session = { canAnalyze: signal(true), lookUpWeather: vi.fn(() => Promise.resolve()) };
  TestBed.configureTestingModule({
    providers: [
      { provide: AnalysisSession, useValue: session },
      { provide: AnalysisApi, useValue: { health: of({ weather: enabled }) } },
    ],
  });
  TestBed.inject(I18n).language.set('fr');
  return session;
}

describe('WeatherOffer', () => {
  it('says what leaves, and to whom, before anything is sent', () => {
    const session = setUp(true);
    const fixture = TestBed.createComponent(WeatherOffer);
    fixture.componentRef.setInput('placeAndTime', true);
    fixture.detectChanges();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.textContent).toContain('arrondi à environ 11 km');
    expect(page.textContent).toContain('90 jours');
    expect(session.lookUpWeather).not.toHaveBeenCalled();
    page.querySelector('button')!.click();
    expect(session.lookUpWeather).toHaveBeenCalledWith();
  });

  it('asks for a place and a time first', () => {
    setUp(true);
    const fixture = TestBed.createComponent(WeatherOffer);
    fixture.detectChanges();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('button')).toBeNull();
    expect(page.textContent).toContain('saisissez ceux de la légende');
  });

  it('is not offered when the server does not enable it', () => {
    setUp(false);
    const fixture = TestBed.createComponent(WeatherOffer);
    fixture.componentRef.setInput('placeAndTime', true);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent?.trim()).toBe('');
  });
});

describe('WeatherQuestion', () => {
  function render(check: CheckResult) {
    const session = setUp(true);
    const fixture = TestBed.createComponent(WeatherQuestion);
    fixture.componentRef.setInput('check', check);
    fixture.detectChanges();
    return { page: fixture.nativeElement as HTMLElement, session };
  }

  it('asks what the photo shows, and credits Open-Meteo next to its data', () => {
    const { page, session } = render(weatherOf(weatherAsked));
    expect(page.querySelectorAll('.choices button').length).toBe(4);
    const credit = page.querySelector<HTMLAnchorElement>('a');
    expect(credit?.href).toBe('https://open-meteo.com/');
    expect(credit?.rel).toBe('noopener noreferrer');
    page.querySelector<HTMLButtonElement>('.choices button')!.click();
    expect(session.lookUpWeather).toHaveBeenCalledWith('rain');
  });

  it('shows the answer given, read from what the API used', () => {
    const { page } = render(weatherOf(weatherToCheck));
    expect(page.querySelector('.choices')).toBeNull();
    expect(page.textContent).toContain('Votre réponse : Pluie qui tombe.');
  });
});
