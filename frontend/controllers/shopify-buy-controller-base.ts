import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import Client, { Address } from "shopify-buy";

export default class ShopifyBuyControllerBase extends Controller {
  // Values
  static values = {
    shopifyDomain: String,
    shopifyStorefrontAccessToken: String,
    shopifyCollectionId: String,
    userEmail: String,
    stripeShipping: Object,
  };
  public shopifyDomainValue: string | undefined;
  public shopifyStorefrontAccessTokenValue: string | undefined;
  public userEmailValue: string | undefined;
  public stripeShippingValue:
    | StripeShippingAddressElementChangeEvent["value"]
    | undefined;

  // Internal
  public client: Client.Client | undefined;

  async connect() {
    this.ensureCheckout(undefined);
  }

  get checkoutId() {
    return window.localStorage.getItem("checkoutId");
  }

  setCheckoutId(id: string | number) {
    window.localStorage.setItem("checkoutId", id.toString());
    return id;
  }

  ensureCheckout(checkoutId: number | undefined): Promise<Client.Cart> {
    return new Promise((resolve) => {
      if (!this.shopifyDomainValue || !this.shopifyStorefrontAccessTokenValue) {
        throw new Error(
          "Shopify could not initialise due to lack of shopifyDomainValue / shopifyStorefrontAccessTokenValue"
        );
      }

      this.client = Client.buildClient({
        domain: this.shopifyDomainValue,
        storefrontAccessToken: this.shopifyStorefrontAccessTokenValue,
      });

      if (this.checkoutId) {
        this.client.checkout.fetch(this.checkoutId).then((checkout) => {
          this.setCheckoutId(checkout.id);
          resolve(checkout);
        });
      } else {
        // @ts-ignore
        this.client.checkout
          .create({
            email: this.userEmailValue,
            lineItems: [],
            // shippingAddress: this.shippingAddress,
          })
          .then((checkout) => {
            // Do something with the checkout
            this.setCheckoutId(checkout.id);
            resolve(checkout);
          });
      }
    });
  }

  async redirectToCheckout() {
    // @ts-ignore
    const cart = await this.client?.checkout.fetch(this.checkoutId);
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
}
