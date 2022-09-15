import { MapConfigController } from "groundwork-django";

export default class MapHtmlBridgeController extends MapConfigController {
  static values = {
    zoom: { type: Number, default: 12 },
  };

  private zoomValue!: number;

  flyTo({ params: { lng, lat, zoom = this.zoomValue } }: any) {
    if (!!lng && !!lat) {
      this.map?.flyTo({
        center: [lng, lat],
        zoom: zoom,
      });
    }
  }
}
