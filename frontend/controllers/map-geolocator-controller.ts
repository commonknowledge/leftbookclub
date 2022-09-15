import type { Map } from "mapbox-gl";
import { MapConfigController } from "groundwork-django";
import mapboxgl from "mapbox-gl";

export default class GeolocateController extends MapConfigController {
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
  }
}
