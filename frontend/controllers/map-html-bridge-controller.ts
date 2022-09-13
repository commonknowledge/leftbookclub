import type { Map, MapLayerEventType } from "mapbox-gl";
import { MapConfigController, getReferencedData } from "groundwork-django";

export default class MapHtmlBridgeController extends MapConfigController {
  static targets = ["scroll"];
  private readonly hasScrollTarget!: boolean;
  private readonly scrollTarget?: HTMLElement;

  static values = {
    mapLayer: String,
    mapEvent: { type: String, default: "click" },
    mapLayerIdProperty: { type: String, default: "id" },
    htmlIdPrefix: { type: String, default: "mapLayer-" },
    flyToZoom: { type: Number, default: 12 },
  };
  private mapLayerValue!: string;
  private mapEventValue!: keyof MapLayerEventType;
  private mapLayerIdPropertyValue!: string;
  private htmlIdPrefixValue!: string;
  private flyToZoomValue!: number;

  get scrollElement() {
    return this.hasScrollTarget ? this.scrollTarget! : this.element;
  }

  connectMap(map: Map) {
    map?.on(this.mapEventValue, this.mapLayerValue, (e) => {
      const id = `${this.htmlIdPrefixValue}${
        (e.features?.[0]?.properties as any)[this.mapLayerIdPropertyValue]
      }`;
      const element = document.getElementById(id);
      if (element) {
        this.scrollTo(element);
      }
    });
  }

  scrollTo(element: HTMLElement) {
    this.scrollElement.scroll({
      top: element.offsetTop,
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
