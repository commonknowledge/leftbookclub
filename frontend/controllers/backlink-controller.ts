import { Controller } from "@hotwired/stimulus";

/**
 * Creates a clickable element that takes you back a page in the history
 * inspired by https://stackoverflow.com/a/46163215
 */
class BacklinkController extends Controller {
  async connect() {
    try {
      // Provide a standard href to facilitate standard browser features such as
      //  - Hover to see link
      //  - Right click and copy link
      //  - Right click and open in new tab
      // @ts-ignore
      this.element.href = document.referrer;
    } catch (e) {}
    // @ts-ignore
    this.element.onclick = function () {
      // We can't let the browser use the above href for navigation. If it does,
      // the browser will think that it is a regular link, and place the current
      // page on the browser history, so that if the user clicks "back" again,
      // it'll actually return to this page. We need to perform a native back to
      // integrate properly into the browser's history behavior
      history.back();
      // Keep it from adding the current page to the browser history
      return false;
    };
  }
}

export default BacklinkController;
