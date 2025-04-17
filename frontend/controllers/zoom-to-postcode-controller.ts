import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["input", "error", "clear", "submit"];
  declare readonly inputTarget: HTMLInputElement;
  declare readonly errorTarget: HTMLElement;
  declare readonly clearTarget: HTMLElement;
  declare readonly submitTarget: HTMLElement;

  async searchPostcode(event: Event) {
    event.preventDefault();

    const postcode = this.inputTarget.value.trim().toUpperCase();
    this.errorTarget.textContent = "";
    this.toggleButtons(postcode.length > 0);

    if (!postcode) {
      this.errorTarget.textContent = "Please enter a postcode.";
      return;
    }

    try {
      const response = await fetch(
        `/geo/postcode/${encodeURIComponent(postcode)}/`
      );
      const data = await response.json();

      if (data && data.latitude && data.longitude) {
        this.element.dispatchEvent(
          new CustomEvent("zoom-to-postcode", {
            detail: { lat: data.latitude, lon: data.longitude },
            bubbles: true,
          })
        );

        this.sortReadingGroupsByDistance(data.latitude, data.longitude);
      } else {
        this.errorTarget.textContent =
          "Postcode not found. Please enter a valid UK postcode.";
      }
    } catch (err) {
      console.error(err);
      this.errorTarget.textContent = "Something went wrong. Try again.";
    }
  }

  clearSearch(event: Event) {
    event.preventDefault();
    this.inputTarget.value = "";
    this.errorTarget.textContent = "";
    this.toggleButtons(false);

    document.querySelectorAll("[data-reading-group-distance]").forEach((el) => {
      el.textContent = "";
    });

    const list = document.querySelector("ol");
    if (list) {
      const items = Array.from(
        list.querySelectorAll("[data-original-index]")
      ) as HTMLElement[];
      const sorted = items.sort((a, b) => {
        return (
          parseInt(a.dataset.originalIndex || "0") -
          parseInt(b.dataset.originalIndex || "0")
        );
      });

      sorted.forEach((el) => list.appendChild(el));
    }

    this.element.dispatchEvent(
      new CustomEvent("reset-zoom", {
        bubbles: true,
      })
    );
  }

  inputChanged() {
    this.toggleButtons(this.inputTarget.value.trim().length > 0);
  }

  toggleButtons(showClear: boolean) {
    this.clearTarget.classList.toggle("tw-hidden", !showClear);
    this.submitTarget.classList.toggle("tw-hidden", showClear);
  }
  sortReadingGroupsByDistance(lat: number, lon: number) {
    const items = Array.from(
      document.querySelectorAll('[data-list-filter-target="item"]')
    ) as HTMLElement[];

    const toMiles = (km: number) => km * 0.621371;
    const toRad = (deg: number) => deg * (Math.PI / 180);

    const distanceFromPostcode = (el: HTMLElement): number => {
      const lat2 = parseFloat(el.dataset.lat || "");
      const lon2 = parseFloat(el.dataset.lng || "");

      if (isNaN(lat2) || isNaN(lon2)) return Infinity;

      const R = 6371;
      const dLat = toRad(lat2 - lat);
      const dLon = toRad(lon2 - lon);
      const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      return R * c;
    };

    const sorted = items.sort((a, b) => {
      const aIsOnline = !a.dataset.lat || !a.dataset.lng;
      const bIsOnline = !b.dataset.lat || !b.dataset.lng;

      if (aIsOnline && !bIsOnline) return 1;
      if (!aIsOnline && bIsOnline) return -1;

      return distanceFromPostcode(a) - distanceFromPostcode(b);
    });

    const list = document.querySelector("ol");
    if (list) {
      sorted.forEach((el) => {
        list.appendChild(el);

        const km = distanceFromPostcode(el);
        const mi = toMiles(km);
        const label = el.querySelector("[data-reading-group-distance]");

        if (label) {
          if (isFinite(mi)) {
            label.textContent = `${mi.toFixed(1)} mi away`;
          } else {
            label.textContent = "";
          }
        }
      });
    }
  }
}
