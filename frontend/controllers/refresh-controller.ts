import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static values = {
    src: String,
    ms: { type: Number, default: 5000 },
  };

  private msValue?: number;
  private interval?: NodeJS.Timer;

  connect() {
    this.start();
  }

  disconnect() {
    this.stop();
  }

  toggle() {
    if (this.interval !== undefined) {
      this.stop();
    } else {
      this.start();
    }
  }

  start() {
    if (this.msValue) {
      this.interval = setInterval(() => {
        console.log(this.element, this.msValue);
        (this.element as any).reload?.();
      }, this.msValue);
    }
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval);
    }
  }
}
