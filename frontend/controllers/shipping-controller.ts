import { Controller } from "@hotwired/stimulus";

class ShippingController extends Controller {
  static targets = ["form", "frame"];

  readonly formTarget!: HTMLFormElement;
  readonly frameTarget!: HTMLFormElement;
  readonly priceValue!: string;
  readonly productValue!: string;
  readonly urlValue!: string;

  static values = {
    url: String,
    product: String,
    price: String,
  };

  formTargetConnected() {
    const dropdown = this.formTarget.querySelector("select");
    if (!dropdown) return;
    // e: HTMLElementEvent<HTMLSelectElement>
    dropdown.addEventListener("change", (e: any) =>
      this.updateFrame(e.target.value)
    );
  }

  updateFrame(country_code: string) {
    const newFrameURL = new URL(
      "/" +
        this.urlValue
          .replace("<price_id>", this.priceValue)
          .replace("<product_id>", this.productValue)
          .replace("<country_id>", country_code),
      window.location.toString()
    );
    this.frameTarget.src = newFrameURL;
  }
}

export default ShippingController;

interface HTMLElementEvent<T extends HTMLElement> extends Event {
  target: T;
  currentTarget: T;
}
