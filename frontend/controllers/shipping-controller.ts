import { Controller } from "@hotwired/stimulus"

class ClipboardController extends Controller {
  static targets = ["form", "frame"]

  static values = {
    url: String,
    product: String,
    // country_id: String
  }

  formTargetConnected() {
    const dropdown = this.formTarget.querySelector("select")
    dropdown.addEventListener("change", e => this.updateFrame(e.target.value))
  }

  updateFrame(country_code: string) {
    const newFrameURL = new URL(
      '/' + this.urlValue.replace("<str:product_id>", this.productValue).replace("<str:country_id>", country_code),
      window.location.toString()
    )
    this.frameTarget.src = newFrameURL
  }
}

export default ClipboardController
