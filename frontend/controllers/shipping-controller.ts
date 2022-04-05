import { Controller } from "@hotwired/stimulus";

class ClipboardController extends Controller {
  static targets = ["form", "frame"];

  readonly formTarget!: HTMLFormElement;
  readonly frameTarget!: HTMLFormElement;
  readonly productValue!: string;
  readonly urlValue!: string;

  static values = {
    url: String,
    product: String,
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
          .replace("<str:product_id>", this.productValue)
          .replace("<str:country_id>", country_code),
      window.location.toString()
    );
    this.frameTarget.src = newFrameURL;
  }
}

export default ClipboardController;

interface HTMLElementEvent<T extends HTMLElement> extends Event {
  target: T;
  currentTarget: T;
}
