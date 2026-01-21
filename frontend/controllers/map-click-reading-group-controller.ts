import type { Map } from "mapbox-gl";
import { MapConfigController } from "groundwork-django";

export default class MapClickReadingGroupController extends MapConfigController {
  static values = {
    delay: { type: Number, default: 500 },
  };

  private delayValue!: number;

  connectMap(map: Map) {
    setTimeout(() => {
      this.setupClickHandler();
    }, this.delayValue);
  }

  setupClickHandler() {
    this.map?.on("click", (e) => {
      if (!this.map) {
        return;
      }
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["reading-group-icons"],
      });
      if (!features.length) {
        return;
      }
      const feature = features[0];
      const id = feature.properties?.id;
      if (!id) {
        return;
      }
      const $el = document.getElementById(`event-${id}`);
      if (!$el) {
        return;
      }
      $el.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
    this.map?.on("mousemove", (e) => {
      if (!this.map) {
        return;
      }
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["reading-group-icons"],
      });
      if (features?.length) {
        this.map.getCanvas().style.cursor = "pointer";
      } else {
        this.map.getCanvas().style.cursor = "";
      }
    });
  }
}
