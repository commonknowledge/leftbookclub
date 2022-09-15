import { Controller } from "@hotwired/stimulus";

export default class ScrollController extends Controller {
  static values = {
    event: { type: String, default: "mouseenter" }
  };

  eventValue!: string;

  connect() {
    this.element?.addEventListener?.(this.eventValue, this.scrollToTop)
  }

  scrollToTop(e: Event) {
    this.element?.scrollIntoView?.()
  }

  disconnect(): void {
    this.element?.removeEventListener?.(this.eventValue, this.scrollToTop)
  }
}
