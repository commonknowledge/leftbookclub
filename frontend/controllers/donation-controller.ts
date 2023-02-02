import { Controller } from "@hotwired/stimulus";

class DonationController extends Controller {
  static targets = ["input"];

  async update(e: InputEvent) {
    // If the new value is one of the radios, select them
    // Else unselect all radios

    const value = (e.target as HTMLInputElement)?.value;
    if (value) {
      this.inputTargets.forEach((input) => {
        if (input.type === "radio") {
          input.checked = parseFloat(input.value) === parseFloat(value);
        } else {
          input.value = value;
        }
      });
    } else {
      this.inputTargets.forEach((input) => {
        if (input.type === "radio") {
          input.checked = false;
        } else {
          input.value = "";
        }
      });
    }
  }
}

export default DonationController;
