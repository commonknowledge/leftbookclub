import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import Client, { Cart, Collection, Product } from "shopify-buy";

/**
 * Take customers to checkout from a product
 * TODO: add to cart via event (example at https://cloudsh.com/eleventy/posts/2019/stimulusjs_and_shopify_api.html)
 */
class ProductController extends Controller {
  // Targets
  static targets = [];

  // Values
  static values = {
    shopifyDomain: String,
    shopifyStorefrontAccessToken: String,
    shopifyCollectionId: String,
    userEmail: String,
    stripeShipping: Object,
    shopifyProductId: String,
  };
  private shopifyProductIdValue: string | undefined;
  private shopifyDomainValue: string | undefined;
  private shopifyStorefrontAccessTokenValue: string | undefined;
  private emailValue: string | undefined;
  private stripeShippingValue:
    | StripeShippingAddressElementChangeEvent["value"]
    | undefined;

  // Internal
  private client: Client.Client | undefined;
  private checkoutId: any | undefined;
  private product: Product | undefined;

  async connect() {
    this.ensureCheckout(undefined);
    this.renderProductData();
  }

  renderProductData() {
    if (!this.shopifyProductIdValue) return;
    this.client?.product.fetch(this.shopifyProductIdValue).then((product) => {
      this.product = product;
      if (this.titleTarget) {
        this.titleTarget.innerHTML = product.title;
      }
      if (this.imageTarget) {
        this.imageTarget.innerHTML = product.images[0].src;
      }
      if (this.priceTarget) {
        this.priceTarget.innerHTML = product.variants[0].price;
      }
    });
  }

  ensureCheckout(checkoutId: number | undefined): checkoutId is number {
    if (checkoutId) return true;

    if (!this.shopifyDomainValue || !this.shopifyStorefrontAccessTokenValue) {
      throw new Error(
        "Shopify could not initialise due to lack of shopifyDomainValue / shopifyStorefrontAccessTokenValue"
      );
    }

    this.client = Client.buildClient({
      domain: this.shopifyDomainValue,
      storefrontAccessToken: this.shopifyStorefrontAccessTokenValue,
    });

    this.client.checkout
      .create(
        this.emailValue,
        [],
        this.stripeShippingValue
          ? {
              address1: this.stripeShippingValue.address.line1,
              address2: this.stripeShippingValue.address.line2,
              city: this.stripeShippingValue.address.city,
              province: this.stripeShippingValue.address.state,
              zip: this.stripeShippingValue.address.postal_code,
              country: this.stripeShippingValue.address.country,
              company: "",
              firstName: this.stripeShippingValue.name,
              lastName: "",
              phone: "",
            }
          : undefined
      )
      .then((checkout) => {
        this.checkoutId = checkout.id;
      });

    return true;
  }

  async add(event: EventInit) {
    if (!this.ensureCheckout(this.checkoutId) || !this.product) return;
    const variantId = event.target.dataset.variantId;
    await this.client?.checkout.addLineItems(this.checkoutId, [
      {
        variantId: `gid://shopify/ProductVariant/${variantId}`,
        quantity: 1,
      },
    ]);

    // TODO: For now, clicking "buy" sends you straight to Shopify
    // but in future we'll implement a cart UI so that multiple books can be purchased
    this.redirectToCheckout();
  }

  async redirectToCheckout() {
    const cart = await this.client?.checkout.fetch(String(this.checkoutId));
    if (!cart?.webUrl) return;
    window.location.href = cart?.webUrl;
  }
}

export default ProductController;
