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
}
