import { MapConfigController } from "groundwork-django";

export default class MapHtmlBridgeController extends MapConfigController {
  static values = {
    zoom: { type: Number, default: 12 },
  };

  private zoomValue!: number;

  flyTo(event: any) {
    const button = event.currentTarget;
    const lng = parseFloat(button.dataset.lng);
    const lat = parseFloat(button.dataset.lat);
    const zoom = button.dataset.zoom
      ? parseFloat(button.dataset.zoom)
      : this.zoomValue;

    if (!isNaN(lng) && !isNaN(lat)) {
      this.map?.flyTo({
        center: [lng, lat],
        zoom: zoom,
      });
    }
  }
}
