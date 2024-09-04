import { Controller } from "@hotwired/stimulus";

class DonationController extends Controller {
  static targets = ["input"];
  inputTargets: any;

  setInputs(value: number) {
    // If the new value is one of the radios, select them
    // Else unselect all radios
    if (value) {
      this.inputTargets.forEach((input: { type: string; checked: boolean; value: string | number; }) => {
        if (input.type === "radio") {
          input.checked = parseFloat(input.value as string) === value;
        } else {
          input.value = String(value);
        }
      });
    } else {
      this.inputTargets.forEach((input: { type: string; checked: boolean; value: string; }) => {
        if (input.type === "radio") {
          input.checked = false;
        } else {
          input.value = "0";
        }
      });
    }
  }
  update(e: InputEvent) {
    let value = parseFloat((e.target as HTMLInputElement)?.value || "0") || 0;
    this.setInputs(value);
  }

  async submitWithoutDonation(e: InputEvent) {
    this.setInputs(0);
    (this.element as HTMLFormElement).submit();
  }
}

export default DonationController;
