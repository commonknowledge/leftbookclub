import { Controller } from "@hotwired/stimulus";

class CouponController extends Controller {
  static targets = ["code", "frame"];

  readonly frameTarget!: HTMLFormElement;
  readonly codeTarget!: HTMLInputElement;
  readonly urlValue!: string;

  static values = {
    url: String,
  };

  updateFrame() {
    const newFrameURL = new URL(
      "/" + this.urlValue.replace("<str:code>", this.codeTarget.value),
      window.location.toString()
    );
    this.frameTarget.src = newFrameURL;
  }
}

export default CouponController;

interface HTMLElementEvent<T extends HTMLElement> extends Event {
  target: T;
  currentTarget: T;
}
