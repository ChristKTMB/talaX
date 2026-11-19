import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { I18n } from '../../../core/i18n/i18n';
import { Claim } from '../../../core/models/analysis';
import { AnalysisSession } from '../../../core/session/analysis-session';
import { ClaimForm, parsePlace } from './claim-form';

function render(needed: boolean, claim: Claim | null = null) {
  const session = {
    claim: signal(claim),
    canAnalyze: signal(true),
    declare: vi.fn(() => Promise.resolve()),
  };
  TestBed.configureTestingModule({
    imports: [ClaimForm],
    providers: [{ provide: AnalysisSession, useValue: session }],
  });
  TestBed.inject(I18n).language.set('fr');
  const fixture = TestBed.createComponent(ClaimForm);
  fixture.componentRef.setInput('needed', needed);
  fixture.detectChanges();
  return { fixture, page: fixture.nativeElement as HTMLElement, session };
}

function type(page: HTMLElement, selector: string, value: string): void {
  const input = page.querySelector<HTMLInputElement>(selector)!;
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

describe('parsePlace', () => {
  it.each([
    ['-4.3217, 15.3125', { latitude: -4.3217, longitude: 15.3125 }],
    ['-4.3217 15.3125', { latitude: -4.3217, longitude: 15.3125 }],
    ['-4,3217 ; 15,3125', { latitude: -4.3217, longitude: 15.3125 }],
    ['-1.68,29.22', { latitude: -1.68, longitude: 29.22 }],
  ])('reads %s', (text, place) => {
    expect(parsePlace(text)).toEqual(place);
  });

  it.each(['Goma', '-4.32', '95, 15', '10, 200', ''])('refuses %s', (text) => {
    expect(parsePlace(text)).toBeNull();
  });
});

describe('ClaimForm', () => {
  it('is open when the file lacks a position or a time, and sends the claim', () => {
    const { fixture, page, session } = render(true);
    expect(page.querySelector('form')).not.toBeNull();
    // The map is offered, never loaded on its own.
    expect(page.querySelector('.picker__canvas')).toBeNull();
    expect(page.textContent).toContain('OpenStreetMap ne voit ni votre adresse');

    type(page, '#claim-place', '-4.3217, 15.3125');
    type(page, '#claim-date', '2026-06-14');
    type(page, '#claim-time', '10:00');
    fixture.detectChanges();
    page.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    expect(session.declare).toHaveBeenCalledWith({
      latitude: -4.3217,
      longitude: 15.3125,
      takenAt: '2026-06-14T10:00',
    });
  });

  it('sends nothing incomplete, and says what is missing', () => {
    const { fixture, page, session } = render(true);
    type(page, '#claim-place', 'Goma');
    fixture.detectChanges();
    expect(page.textContent).toContain('degrés décimaux');
    page.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    fixture.detectChanges();
    expect(session.declare).not.toHaveBeenCalled();
    expect(page.querySelector('[role=alert]')?.textContent).toContain('tous nécessaires');
  });

  it('stays folded on a complete file, a click away', () => {
    const { fixture, page } = render(false);
    expect(page.querySelector('form')).toBeNull();
    page.querySelector<HTMLButtonElement>('button')!.click();
    fixture.detectChanges();
    expect(page.querySelector('form')).not.toBeNull();
  });

  it('shows the claim checked, which can be changed or removed', () => {
    const claim = { latitude: -1.6792, longitude: 29.2228, takenAt: '2026-06-14T10:00' };
    const { fixture, page, session } = render(true, claim);
    expect(page.textContent).toContain('-1.67920, 29.22280, le 14 juin 2026 à 10:00');
    expect(page.querySelector('form')).toBeNull();

    const [change, remove] = [...page.querySelectorAll<HTMLButtonElement>('button')];
    change!.click();
    fixture.detectChanges();
    expect(page.querySelector<HTMLInputElement>('#claim-place')?.value).toBe('-1.67920, 29.22280');
    TestBed.resetTestingModule();

    const again = render(true, claim);
    [...again.page.querySelectorAll<HTMLButtonElement>('button')][1]!.click();
    expect(again.session.declare).toHaveBeenCalledWith(null);
    expect(session.declare).not.toHaveBeenCalled();
    expect(remove).toBeDefined();
  });
});
