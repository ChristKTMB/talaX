import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import type { Map as LeafletMap, Marker } from 'leaflet';
import { I18n } from '../../../core/i18n/i18n';
import { Icon } from '../../../shared/ui/icon/icon';
import { ATTRIBUTION, PIN, TILE_URL } from '../location-map/location-map';

export interface Place {
  readonly latitude: number;
  readonly longitude: number;
}

/**
 * A map to click on the place a caption claims. Like the map of the report, it
 * appears only after the user asks, saying the area will be requested from
 * OpenStreetMap through our server. The typed coordinates remain the way in
 * for keyboards and screen readers.
 */
@Component({
  selector: 'app-place-picker',
  imports: [Icon],
  templateUrl: './place-picker.html',
  styleUrl: './place-picker.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PlacePicker {
  protected readonly i18n = inject(I18n);
  readonly place = input<Place | null>(null);
  readonly picked = output<Place>();

  protected readonly shown = signal(false);
  protected readonly failed = signal(false);
  private readonly container = viewChild<ElementRef<HTMLElement>>('map');
  private map: LeafletMap | null = null;
  private marker: Marker | null = null;

  constructor() {
    afterRenderEffect(() => {
      const element = this.container()?.nativeElement;
      if (element && !this.map) void this.create(element);
    });
    // Typed coordinates move the pin too.
    afterRenderEffect(() => {
      const place = this.place();
      if (place && this.marker) this.marker.setLatLng([place.latitude, place.longitude]);
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
    const L = loaded.default ?? loaded;
    if (this.map || !element.isConnected) return;
    const place = this.place();
    const map = place
      ? L.map(element, { center: [place.latitude, place.longitude], zoom: 10, zoomControl: false })
      : L.map(element, { center: [10, 15], zoom: 2, zoomControl: false });
    map.attributionControl.setPrefix(false);
    L.control
      .zoom({ zoomInTitle: this.i18n.t('map.zoom_in'), zoomOutTitle: this.i18n.t('map.zoom_out') })
      .addTo(map);
    L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION })
      .on('tileerror', () => this.failed.set(true))
      .addTo(map);
    const icon = L.divIcon({
      html: PIN,
      className: 'pin',
      iconSize: [36, 48],
      iconAnchor: [18, 46],
    });
    if (place) {
      this.marker = L.marker([place.latitude, place.longitude], { icon, interactive: false });
      this.marker.addTo(map);
    }
    map.on('click', (event) => {
      const { lat, lng } = event.latlng.wrap();
      if (this.marker) this.marker.setLatLng([lat, lng]);
      else this.marker = L.marker([lat, lng], { icon, interactive: false }).addTo(map);
      this.picked.emit({ latitude: round(lat), longitude: round(lng) });
    });
    this.map = map;
  }

  private remove(): void {
    this.map?.remove();
    this.map = null;
    this.marker = null;
  }
}

/** Five decimals: about a metre, more than a click can mean. */
function round(degrees: number): number {
  return Math.round(degrees * 1e5) / 1e5;
}
