import type { Map, MapLayerEventType } from "mapbox-gl";
import { MapConfigController, getReferencedData } from "groundwork-django";
import mapboxgl from "mapbox-gl";

export default class MapHtmlBridgeController extends MapConfigController {
  static targets = ["scroll"];
  private readonly hasScrollTarget!: boolean;
  private readonly scrollTarget?: HTMLElement;

  static values = {
    mapLayer: String,
    htmlScrollQuery: String,
    mapEvent: { type: String, default: "click" },
    mapLayerIdProperty: { type: String, default: "id" },
    htmlIdPrefix: { type: String, default: "mapLayer-" },
    flyToZoom: { type: Number, default: 12 },
  };
  private htmlScrollQueryValue?: string;
  private mapLayerValue!: string;
  private mapEventValue!: keyof MapLayerEventType;
  private mapLayerIdPropertyValue!: string;
  private htmlIdPrefixValue!: string;
  private flyToZoomValue!: number;

  get scrollElement() {
    return this.hasScrollTarget
      ? this.scrollTarget!
      : this.htmlScrollQueryValue
        ? document.querySelector(this.htmlScrollQueryValue)
        : this.element;
  }

  connectMap(map: Map) {
    map?.addControl(
      new mapboxgl.GeolocateControl({
        fitBoundsOptions: {
          maxZoom: 11,
        },
        positionOptions: {
          enableHighAccuracy: false,
        },
        trackUserLocation: false,
        showUserHeading: false,
      })
    );

    map?.on(this.mapEventValue, this.mapLayerValue, (e) => {
      const id = `${this.htmlIdPrefixValue}${(e.features?.[0]?.properties as any)[this.mapLayerIdPropertyValue]
        }`;
      const element = document.getElementById(id);
      if (element) {
        this.scrollTo(element);
      }
    });
  }

  scrollTo(element: HTMLElement) {
    this.scrollElement?.scroll({
      top: element.offsetTop + element.offsetHeight / 2,
      left: 0,
      behavior: "smooth",
    });
  }

  flyTo({ params: { lng, lat, zoom = this.flyToZoomValue } }: any) {
    if (!!lng && !!lat) {
      this.map?.flyTo({
        center: [lng, lat],
        zoom: zoom,
      });
    }
  }
}
