// import type { Map } from "mapbox-gl";
// import { MapConfigController } from "groundwork-django";
// import bbox from "@turf/bbox";

// export default class ZoomController extends MapConfigController {
//   static values = {
//     sourceIds: Array,
//     minZoom: { type: Number, default: 1 },
//     maxZoom: { type: Number, default: 20 },
//     padding: { type: Number, default: 30 },
//     delay: { type: Number, default: 500 },
//   };

//   private sourceIdsValue!: string[];
//   private maxZoomValue!: number;
//   private minZoomValue!: number;
//   private paddingValue!: number;
//   private delayValue!: number;

//   connectMap(map: Map) {
//     setTimeout(() => {
//       this.zoomToSourceFeatures();
//     }, this.delayValue);
//   }

//   zoomToSourceFeatures(
//     { params: { sourceIds } } = { params: { sourceIds: this.sourceIdsValue } }
//   ) {
//     const features = this.getSourceFeatures(sourceIds);
//     this.zoomToFeatures(features);
//   }

//   getSourceFeatures(sourceIds = this.sourceIdsValue) {
//     let features: mapboxgl.MapboxGeoJSONFeature[] = [];
//     for (const id of sourceIds) {
//       const source = this.map?.getSource?.(id);
//       if (source) {
//         // @ts-ignore
//         features = features.concat(source._data.features || []);
//       }
//     }
//     return features;
//   }

//   zoomToFeatures(features: mapboxgl.MapboxGeoJSONFeature[]) {
//     const addressBounds = bbox({
//       type: "FeatureCollection",
//       features: features,
//     });

//     const bounds = this.bboxToBounds(addressBounds as any);

//     const nextCamera = this.map?.cameraForBounds(bounds, {
//       padding: this.paddingValue,
//       maxZoom: this.maxZoomValue,
//     });

//     this.map?.flyTo({
//       ...nextCamera,
//       zoom: Math.min(
//         this.maxZoomValue,
//         Math.max(this.minZoomValue, (nextCamera?.zoom! || 0) - 1)
//       ),
//       // essential: true,
//     });
//   }

//   bboxToBounds = (
//     n: [number, number, number, number]
//   ): [[number, number], [number, number]] => {
//     return [
//       [Number(n[0]), Number(n[1])],
//       [Number(n[2]), Number(n[3])],
//     ];
//   };
// }
