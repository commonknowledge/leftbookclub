import type { Map, Marker } from "mapbox-gl";
import { MapConfigController } from "groundwork-django";
import mapboxgl from "mapbox-gl";

export default class GeolocateController extends MapConfigController {
  marker: Marker | null = null;
  map!: Map;

  connectMap(map: Map) {
    this.map = map;

    map.addControl(
      new mapboxgl.GeolocateControl({
        fitBoundsOptions: { maxZoom: 11 },
        positionOptions: { enableHighAccuracy: false },
        trackUserLocation: false,
        showUserHeading: false,
      })
    );

    this.element.addEventListener("zoom-to-postcode", (event: Event) => {
      const customEvent = event as CustomEvent<{ lat: number; lon: number }>;
      const { lat, lon } = customEvent.detail;

      this.flyToPostcode(lat, lon);
      this.addMarker(lon, lat);
    });
  }

  flyToPostcode(lat: number, lon: number, zoomLevel = 14) {
    this.map.flyTo({
      center: [lon, lat],
      zoom: zoomLevel,
    });
  }

  addMarker(lon: number, lat: number) {
    if (this.marker) {
      this.marker.remove();
    }

    this.marker = new mapboxgl.Marker({ color: "#F8F400" })
      .setLngLat([lon, lat])
      .addTo(this.map);

    this.element.addEventListener("reset-zoom", () => {
      this.map.flyTo({
        center: [-2.5, 53.6],
        zoom: 5.5,
      });

      if (this.marker) {
        this.marker.remove();
        this.marker = null;
      }
    });
  }
}
