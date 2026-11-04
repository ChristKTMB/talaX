import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import type { Map as LeafletMap } from 'leaflet';
import { I18n } from '../../../core/i18n/i18n';
import { Icon } from '../../../shared/ui/icon/icon';

/** Tiles come through our server (api/tiles.py): OpenStreetMap never sees the user. */
export const TILE_URL = '/api/tiles/{z}/{x}/{y}.png';
const ZOOM = 15;
const ATTRIBUTION =
  '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
// The pin of the mockup: the logo's marked cell inside a drop.
const PIN = `<svg width="36" height="48" viewBox="0 0 36 48" aria-hidden="true">
  <path d="M18 46C18 46 33 28 33 17A15 15 0 0 0 3 17C3 28 18 46 18 46Z" fill="#1b1a17" />
  <rect x="13" y="12" width="10" height="10" fill="#faf8f2" />
</svg>`;

/**
 * The recorded position on a map, only after the user asks for it: showing
 * the map tells OpenStreetMap which area is looked at (project notes, section
 * 12, "leaks are announced"). Leaflet itself is loaded at that moment too.
 */
@Component({
  selector: 'app-location-map',
  imports: [Icon],
  templateUrl: './location-map.html',
  styleUrl: './location-map.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LocationMap {
  protected readonly i18n = inject(I18n);
  readonly latitude = input.required<number>();
  readonly longitude = input.required<number>();

  protected readonly shown = signal(false);
  protected readonly failed = signal(false);
  /** Coordinates keep the decimal point in both languages (project notes). */
  protected readonly position = computed(
    () => `${this.latitude().toFixed(5)}, ${this.longitude().toFixed(5)}`,
  );
  private readonly container = viewChild<ElementRef<HTMLElement>>('map');
  private map: LeafletMap | null = null;

  constructor() {
    afterRenderEffect(() => {
      const element = this.container()?.nativeElement;
      if (element && !this.map) void this.create(element);
    });
    inject(DestroyRef).onDestroy(() => this.remove());
  }

  protected hide(): void {
    this.remove();
    this.failed.set(false);
    this.shown.set(false);
  }

  private async create(element: HTMLElement): Promise<void> {
    const loaded = await import('leaflet');
    // Leaflet is CommonJS: the production build puts it under `default`.
    const L = loaded.default ?? loaded;
    if (this.map || !element.isConnected) return;
    const center: [number, number] = [this.latitude(), this.longitude()];
    const map = L.map(element, { center, zoom: ZOOM, zoomControl: false });
    map.attributionControl.setPrefix(false);
    L.control
      .zoom({ zoomInTitle: this.i18n.t('map.zoom_in'), zoomOutTitle: this.i18n.t('map.zoom_out') })
      .addTo(map);
    L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION })
      .on('tileerror', () => this.failed.set(true))
      .addTo(map);
    L.marker(center, {
      icon: L.divIcon({ html: PIN, className: 'pin', iconSize: [36, 48], iconAnchor: [18, 46] }),
      keyboard: false,
      interactive: false,
    }).addTo(map);
    this.map = map;
  }

  private remove(): void {
    this.map?.remove();
    this.map = null;
  }
}
