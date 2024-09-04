import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import Client, { Address, MoneyV2 } from "shopify-buy";
import Mustache from "mustache";
import Wax from "@jvitela/mustache-wax";
Wax(Mustache, { currency, pluralize, length, shopifyId, stringify });
import { isAfter } from "date-fns";

export default class ShopifyBuyControllerBase extends Controller {
  // Targets
  static targets = ["template", "variantSelector", "addToCartButton"];

  public templateTargets?: HTMLElement[];
  public variantSelectorTarget!: HTMLSelectElement;
  public addToCartButtonTarget!: HTMLButtonElement;

  // Values
  static values = {
    shopifyDomain: String,
    shopifyStorefrontAccessToken: String,
    shopifyCollectionId: String,
    userEmail: String,
    stripeShipping: Object,
    checkout: Object,
    templateTags: { default: ["((", "))"], type: Array },
    mustacheView: Object,
  };
  public cartTitleTemplateValue!: string;
  public checkoutValue: Client.Cart | undefined;
  public shopifyDomainValue: string | undefined;
  public shopifyStorefrontAccessTokenValue: string | undefined;
  public userEmailValue: string | undefined;
  public stripeShippingValue:
    | StripeShippingAddressElementChangeEvent["value"]
    | undefined;
  public templateTagsValue!: [string, string];
  public mustacheViewValue!: any;

  // Internal
  public client: Client.Client | undefined;

  async connect() {
    this.getCart();
  }

  updateAddToCartButton() {
    const selectedOption = this.variantSelectorTarget.options[this.variantSelectorTarget.selectedIndex];
    const selectedVariantId = selectedOption.value;
    const inventoryQuantity = selectedOption.getAttribute('data-inventory-quantity');
    const inventoryPolicy = selectedOption.getAttribute('data-inventory-policy');
    this.addToCartButtonTarget.setAttribute('data-product-variant-id-param', selectedVariantId);

    if (Number(inventoryQuantity) == 0 && inventoryPolicy == 'deny') {
        this.addToCartButtonTarget.setAttribute('disabled', 'true');
    } else {
        this.addToCartButtonTarget.removeAttribute('disabled');
    }
}
  private LOCALSTORAGE_CHECKOUT_ID = "checkoutId";

  get checkoutId(): string | number {
    const id = window.localStorage.getItem(this.LOCALSTORAGE_CHECKOUT_ID);
    return id ? id.toString() : ""; 
  }

  set checkoutId(id: string | number) {
    window.localStorage.setItem(this.LOCALSTORAGE_CHECKOUT_ID, id.toString());
  }

  async getCart(): Promise<Client.Cart> {
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
      this.checkoutValue = await this.client.checkout.fetch(this.checkoutId.toString());
    }

    let checkoutIsExpired = false;
    if (!!this.checkoutValue && this.checkoutValue?.completedAt) {
      checkoutIsExpired = isAfter(
        new Date(),
        new Date(this.checkoutValue?.completedAt)
      );
    }

    if (!this.checkoutId || checkoutIsExpired) {
      return this.resetCart();
    }

    this.checkoutId = this.checkoutValue!.id;
    return this.checkoutValue!;
  }

  async resetCart() {
    // @ts-ignore
    this.checkoutValue = await this.client?.checkout.create({
      email: this.userEmailValue || undefined,
      lineItems: [],
      shippingAddress: this.shippingAddress,
    });

    this.checkoutId = this.checkoutValue!.id;
    return this.checkoutValue!;
  }

  async add({ params: { variantId } }: any) {
    if (!this.checkoutId) return;
    this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };
    const newLineItems = [
      {
        variantId: stringToVariantURI(variantId),
        quantity: 1,
      },
    ];

    // @ts-ignore
    try {
      this.checkoutValue = await this.client?.checkout.addLineItems(
        this.checkoutId,
        newLineItems
      );
    } catch (e) {
      const checkoutValue = await this.resetCart();
      this.checkoutValue = await this.client?.checkout.addLineItems(
        checkoutValue.id,
        newLineItems
      );
    }
  }

  async buyNow(e: any) {
    this.add(e);
    this.redirectToCheckout();
  }

  async remove({
    params: { lineItem },
  }: {
    params: { lineItem: Client.LineItem };
  }) {
    if (!this.checkoutId) return;
    this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };
    this.checkoutValue = await this.client?.checkout.removeLineItems(
      this.checkoutId,
      [lineItem.id.toString()]
    );
  }

  async decrement({
    params: { lineItem },
  }: {
    params: { lineItem: Client.LineItem };
  }) {
    if (!this.checkoutId) return;
    this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };

    const quantity = lineItem.quantity - 1;

    if (quantity === 0) {
      return this.remove({ params: { lineItem } });
    }

    this.checkoutValue = await this.client?.checkout.updateLineItems(
      this.checkoutId,
      [
        {
          // variantId: stringToVariantURI(variantId),
          id: lineItem.id,
          quantity: Math.max(1, quantity),
        },
      ]
    );
  }

  async increment({
    params: { lineItem },
  }: {
    params: { lineItem: Client.LineItem };
  }) {
    if (!this.checkoutId) return;
    this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };

    // If the item is not in the cart, add it
    // if (!this.checkoutValue?.lineItems.find((item) => item.id === item.id)) {
    //   this.add({ params: { lineItem } })
    // }

    this.checkoutValue = await this.client?.checkout.updateLineItems(
      this.checkoutId,
      [
        {
          // variantId: stringToVariantURI(variantId),
          id: lineItem.id,
          quantity: Math.max(1, lineItem.quantity + 1),
        },
      ]
    );
  }

  checkoutValueChanged() {
    this.mustacheViewValue = {
      loading: false,
      hasLineItems: this.checkoutValue?.lineItems?.length || 0 > 0,
      lineItems: this.checkoutValue?.lineItems?.map((lineItem) => {
        return {
          ...lineItem,
          lineItem,
          canDecreaseQuantity: lineItem.quantity > 1,
        };
      }),
      checkout: this.checkoutValue,
    };
  }

  mustacheViewValueChanged() {
    this.renderCart();
  }

  cartTargetConnected() {
    this.renderCart();
  }

  // openCart() {
  //   if (!this.cartTarget) return
  //   (new Offcanvas(this.cartTarget)).show()
  // }

  renderCart() {
    for (const template of this.templateTargets || []) {
      const els = Array.from(
        document.querySelectorAll(template.dataset?.target || "")
      );
      if (els.length) {
        for (const el of els) {
          el.innerHTML = Mustache.render(
            template.innerHTML,
            this.mustacheViewValue,
            {},
            this.templateTagsValue
          );
        }
      }
    }
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
      const [firstName, lastName, ...names] =
        this.stripeShippingValue?.name.split(" ") || ["", ""];
      return this.stripeShippingValue
        ? {
            address1: this.stripeShippingValue.address.line1,
            address2: this.stripeShippingValue.address.line1,
            city: this.stripeShippingValue.address.city,
            province: this.stripeShippingValue.address.state,
            zip: this.stripeShippingValue.address.postal_code,
            country: this.stripeShippingValue.address.country,
            company: "",
            firstName,
            lastName,
            phone: "",
          }
        : undefined;
    } catch (e) {
      return undefined;
    }
  }
}

function shopifyId(id: any) {
  return id.replace(new RegExp("gid://shopify/[a-zA-Z]+/"), "");
}

function stringToVariantURI(variantId: any) {
  if (variantId.toString().startsWith("gid://shopify/ProductVariant/")) {
    return variantId;
  }
  return `gid://shopify/ProductVariant/${variantId}`;
}

function stringify(x: any) {
  try {
    return JSON.stringify(x);
  } catch (e) {
    console.error(e);
    return x.toString();
  }
}

function pluralize(count: number, word: string, plural?: string) {
  return count === 1 ? word : plural || word + "s";
}

function currency(
  money: string | number | MoneyV2 | undefined,
  currencyCode = "GBP"
) {
  if (!money) return "";
  else if (typeof money === "string") {
    money = parseFloat(money).toFixed(2);
  } else if (typeof money === "number") {
    money = money.toFixed(2);
  } else {
    currencyCode = money.currencyCode;
    money = parseFloat(money.amount).toFixed(2);
  }
  return (currencyCode === "GBP" ? "£" : currencyCode + " ") + money;
}

function length(arr: any[]) {
  if (!arr) return 0;
  return arr.length || 0;
}