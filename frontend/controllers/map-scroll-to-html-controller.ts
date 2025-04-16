// import type { Map, MapLayerEventType } from "mapbox-gl";
// import { MapConfigController } from "groundwork-django";

// export default class MapScrollToHtmlController extends MapConfigController {
//   static targets = ["scroll"];
//   private readonly hasScrollTarget!: boolean;
//   private readonly scrollTarget?: HTMLElement;

//   static values = {
//     mapLayer: String,
//     scrollElementQuery: String,
//     mapEvent: { type: String, default: "click" },
//     mapLayerIdProperty: { type: String, default: "id" },
//     relatedIdPrefix: { type: String, default: "mapLayer-" },
//   };
//   private scrollElementQueryValue?: string;
//   private mapLayerValue!: string;
//   private mapEventValue!: keyof MapLayerEventType;
//   private mapLayerIdPropertyValue!: string;
//   private relatedIdPrefixValue!: string;

//   get scrollElement() {
//     return this.hasScrollTarget
//       ? this.scrollTarget!
//       : this.scrollElementQueryValue
//       ? document.querySelector(this.scrollElementQueryValue)
//       : this.element;
//   }

//   connectMap(map: Map) {
//     map?.on(this.mapEventValue, this.mapLayerValue, (e) => {
//       const id = `${this.relatedIdPrefixValue}${
//         (e.features?.[0]?.properties as any)[this.mapLayerIdPropertyValue]
//       }`;
//       const element = document.getElementById(id);
//       if (element) {
//         this.scrollTo(element);
//       }
//     });
//   }

//   scrollTo(element: HTMLElement) {
//     this.scrollElement?.scroll({
//       top: element.offsetTop + element.offsetHeight / 2,
//       left: 0,
//       behavior: "smooth",
//     });
//   }
// }
