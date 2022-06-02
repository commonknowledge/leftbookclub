import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import Client, { Address, Cart, Collection, Product } from "shopify-buy";

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
  };
  private shopifyDomainValue: string | undefined;
  private shopifyStorefrontAccessTokenValue: string | undefined;
  private userEmailValue: string | undefined;
  private stripeShippingValue:
    | StripeShippingAddressElementChangeEvent["value"]
    | undefined;

  // Internal
  private client: Client.Client | undefined;
  private checkoutId: any | undefined;

  async connect() {
    this.ensureCheckout(undefined);
  }

  get shippingAddress(): Address | undefined {
    try {
      return this.stripeShippingValue
        ? {
            address1: this.stripeShippingValue.address.line1,
            address2: this.stripeShippingValue.address.line1,
            city: this.stripeShippingValue.address.city,
            province: this.stripeShippingValue.address.state,
            zip: this.stripeShippingValue.address.postal_code,
            country: this.stripeShippingValue.address.country,
            company: "",
            firstName: this.stripeShippingValue.name,
            lastName: this.stripeShippingValue.name,
            phone: "",
          }
        : undefined;
    } catch (e) {
      return undefined;
    }
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
      // @ts-ignore
      .create({
        email: this.userEmailValue,
        lineItems: [],
        // shippingAddress: this.shippingAddress,
      })
      .then((checkout) => {
        this.checkoutId = checkout.id;
      });

    return true;
  }

  async add(event: EventInit) {
    if (!this.ensureCheckout(this.checkoutId)) return;
    // @ts-ignore
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
    // @ts-ignore
    const cart = await this.client?.checkout.fetch(String(this.checkoutId));
    if (!cart?.webUrl) return;
    const checkoutURL = new URL(cart?.webUrl);

    checkoutURL.searchParams.append(
      "return_to",
      new URL("/", window.location.href).toString()
    );
    try {
      // @ts-ignore
      posthog.capture("buy book");
    } catch (e) {}
    window.location.href = checkoutURL.toString();
  }
}

export default ProductController;
