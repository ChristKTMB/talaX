import { TestBed } from '@angular/core/testing';
import { I18n } from '../../../core/i18n/i18n';
import { LocationMap, TILE_URL } from './location-map';

async function render() {
  TestBed.configureTestingModule({ imports: [LocationMap] });
  TestBed.inject(I18n).language.set('fr');
  const fixture = TestBed.createComponent(LocationMap);
  fixture.componentRef.setInput('latitude', 48.8566);
  fixture.componentRef.setInput('longitude', 2.3522);
  await fixture.whenStable();
  return { fixture, page: fixture.nativeElement as HTMLElement };
}

const until = async (check: () => boolean) => {
  for (let i = 0; i < 50 && !check(); i++) await new Promise((done) => setTimeout(done, 20));
};

describe('LocationMap', () => {
  it('shows no map and asks for nothing until the user asks, saying what will leak', async () => {
    const { page } = await render();
    expect(page.querySelector('.leaflet-container')).toBeNull();
    expect(page.querySelector('img')).toBeNull();
    expect(page.querySelector('.offer button')?.textContent).toContain('Afficher sur la carte');
    expect(page.querySelector('.offer p')?.textContent).toContain(
      'OpenStreetMap ne voit ni votre adresse ni votre fichier',
    );
  });

  it('loads tiles through our server only, with the OpenStreetMap credit', async () => {
    const { fixture, page } = await render();
    page.querySelector<HTMLButtonElement>('.offer button')?.click();
    await fixture.whenStable();
    await until(() => page.querySelector('.leaflet-tile') !== null);

    const tiles = [...page.querySelectorAll<HTMLImageElement>('.leaflet-tile')];
    expect(tiles.length).toBeGreaterThan(0);
    for (const tile of tiles) {
      expect(new URL(tile.src).pathname).toMatch(/^\/api\/tiles\/15\/\d+\/\d+\.png$/);
    }
    expect(TILE_URL.startsWith('/')).toBe(true);
    expect(page.querySelector('.leaflet-control-attribution')?.textContent).toContain(
      '© OpenStreetMap contributors',
    );
    expect(page.querySelector('.map__foot')?.textContent).toContain('48.85660, 2.35220');
  });

  it('removes the map when hidden', async () => {
    const { fixture, page } = await render();
    page.querySelector<HTMLButtonElement>('.offer button')?.click();
    await fixture.whenStable();
    await until(() => page.querySelector('.leaflet-container') !== null);
    page.querySelector<HTMLButtonElement>('.map__foot button')?.click();
    await fixture.whenStable();
    expect(page.querySelector('.leaflet-container')).toBeNull();
    expect(page.querySelector('.offer')).not.toBeNull();
  });
});
