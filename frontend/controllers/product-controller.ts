import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import { createStorefrontApiClient } from "@shopify/storefront-api-client";
import Mustache from "mustache";
import Wax from "@jvitela/mustache-wax";
Wax(Mustache, { currency, pluralize, length, shopifyId, stringify });

interface CartValue {
  id: string;
  createdAt?: string;
  updatedAt?: string;
  lines: {
    edges: {
      node: {
        id: string;
        quantity: number;
        merchandise: {
          id: string;
          title: string;
          product: {
            id: string;
            title: string;
            images: {
              edges: {
                node: {
                  url: string;
                  altText: string | null;
                };
              }[];
            };
          };
        };
        attributes: {
          key: string;
          value: string;
        }[];
      };
    }[];
  };
  cost: {
    totalAmount: {
      amount: string;
      currencyCode: string;
    };
    subtotalAmount?: {
      amount: string;
      currencyCode: string;
    };
    totalTaxAmount?: {
      amount: string;
      currencyCode: string;
    };
  };
  checkoutUrl: string;
}

interface LineItem {
  id: string;
  quantity: number;
  title: string;
  price: string;
  compareAtPrice?: string;
  variantId: string;
  canDecreaseQuantity: boolean;
  imageUrl: string;
  imageAlt: string | null;
}

interface MustacheViewValue {
  loading: boolean;
  hasLineItems: boolean;
  lineItems: LineItem[];
  totalQuantity: number;
  checkout: string;
  totalCost: string;
  currency: string;
}

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
  public cartValue: CartValue | undefined;
  public shopifyDomainValue: string | undefined;
  public shopifyStorefrontAccessTokenValue: string | undefined;
  public userEmailValue: string | undefined;
  public stripeShippingValue:
    | StripeShippingAddressElementChangeEvent["value"]
    | undefined;
  public templateTagsValue!: [string, string];
  public mustacheViewValue!: any;

  // Internal
  public client: ReturnType<typeof createStorefrontApiClient> | undefined;

  async connect() {
    await this.getCart();
  }
  async shopifyRequest(query: string, variables: object = {}): Promise<any> {
    if (!this.shopifyDomainValue || !this.shopifyStorefrontAccessTokenValue) {
      throw new Error("Shopify initialization failed: Missing domain or token");
    }

    const apiUrl = `https://${this.shopifyDomainValue}/api/2025-01/graphql.json`;
    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Shopify-Storefront-Access-Token":
            this.shopifyStorefrontAccessTokenValue!,
        },
        body: JSON.stringify({ query, variables }),
      });
      return await response.json();
    } catch (error) {
      console.error("Shopify API request failed:", error);
      return null;
    }
  }

  updateCartState(cart: any) {
    const lineItems = cart.lines.edges.map((edge: any) => ({
      id: edge.node.id,
      quantity: edge.node.quantity,
      title: edge.node.merchandise.product.title,
      price: edge.node.merchandise.priceV2.amount,
      compareAtPrice: edge.node.merchandise.compareAtPriceV2?.amount,
      variantId: edge.node.merchandise.id,
      canDecreaseQuantity: edge.node.quantity > 1,
      imageUrl:
        edge.node.merchandise.product.images.edges?.[0]?.node?.url || "",
      imageAlt:
        edge.node.merchandise.product.images.edges?.[0]?.node?.altText || "",
    }));

    this.mustacheViewValue = {
      loading: false,
      hasLineItems: lineItems.length > 0,
      lineItems,
      totalQuantity: lineItems.reduce(
        (sum: number, item: LineItem) => sum + item.quantity,
        0
      ),
      checkout: cart.checkoutUrl,
      totalCost: cart.cost.subtotalAmount.amount,
      currency: cart.cost.subtotalAmount.currencyCode,
    } as MustacheViewValue;
  }

  updateAddToCartButton() {
    const selectedOption =
      this.variantSelectorTarget.options[
        this.variantSelectorTarget.selectedIndex
      ];
    const selectedVariantId = selectedOption.value;
    const inventoryQuantity = selectedOption.getAttribute(
      "data-inventory-quantity"
    );
    const inventoryPolicy = selectedOption.getAttribute(
      "data-inventory-policy"
    );
    this.addToCartButtonTarget.setAttribute(
      "data-product-variant-id-param",
      selectedVariantId
    );

    if (Number(inventoryQuantity) == 0 && inventoryPolicy == "deny") {
      this.addToCartButtonTarget.setAttribute("disabled", "true");
    } else {
      this.addToCartButtonTarget.removeAttribute("disabled");
    }
  }
  private LOCALSTORAGE_CART_ID = "checkoutId";

  get cartId() {
    const cartId = window.localStorage.getItem(this.LOCALSTORAGE_CART_ID);
    return cartId ? cartId.toString() : "";
  }

  set cartId(id: string | number) {
    window.localStorage.setItem(this.LOCALSTORAGE_CART_ID, id.toString());
  }

  async getCart() {
    const query = `
    query {
      cart(id: "${this.cartId}") {
        id
        lines(first: 10) {
          edges {
            node {
              id
              quantity
              merchandise {
                ... on ProductVariant {
                  id
                  title
                  priceV2 {
                    amount
                    currencyCode
                  }
                  compareAtPriceV2 {
                    amount
                    currencyCode
                  }
                  product {
                    title
                    images(first: 1) {
                      edges {
                        node {
                          url
                          altText
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        cost {
          subtotalAmount {
            amount
            currencyCode
          }
        }
        checkoutUrl
      }
    }`;

    const data = await this.shopifyRequest(query);
    if (data?.data?.cart) this.updateCartState(data.data.cart);
    else return this.resetCart();
  }

  async resetCart() {
    const buyerIdentity: Record<string, string> = {};

    if (this.userEmailValue) {
      buyerIdentity.email = this.userEmailValue;
    }
    if (this.shippingAddress) {
      buyerIdentity.countryCode = this.shippingAddress.country;
    }
    const input = {
      lines: [],
      ...(Object.keys(buyerIdentity).length > 0 && { buyerIdentity }),
    };

    const mutation = `
        mutation cartCreate($input: CartInput!) {
          cartCreate(input: $input) {
            cart {
              id
              checkoutUrl
              cost {
                subtotalAmount {
                  amount
                  currencyCode
                }
              }
              buyerIdentity {
                email
                countryCode
              }
            }
            userErrors {
              field
              message
            }
          }
        }
      `;
    const data = await this.shopifyRequest(mutation, { input });
    const newCart = data?.data?.cartCreate?.cart;

    if (!newCart) {
      console.error(
        "Failed to create a new cart:",
        data?.errors || data?.data?.cartCreate?.userErrors
      );
      return null;
    }

    this.cartId = newCart.id;
    this.cartValue = newCart;
    return newCart;
  }

  async add({ params: { variantId } }: { params: { variantId: string } }) {
    if (!this.cartId) return;

    const mutation = `
      mutation {
        cartLinesAdd(cartId: "${this.cartId}", lines: [
          {
            merchandiseId: "gid://shopify/ProductVariant/${variantId}",
            quantity: 1
          }
        ]) {
          cart {
            id
            lines(first: 10) {
              edges {
                node {
                  id
                  quantity
                  merchandise {
                    ... on ProductVariant {
                      id
                      title
                        priceV2 {
                        amount
                        currencyCode
                      }
                      compareAtPriceV2 {
                        amount
                        currencyCode
                      }
                      product {
                        title
                        images(first: 1) {
                          edges {
                            node {
                              url
                              altText
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            cost {
              subtotalAmount {
                amount
                currencyCode
              }
            }
            checkoutUrl
          }
          userErrors {
            field
            message
          }
        }
      }`;

    const data = await this.shopifyRequest(mutation);
    if (data?.data?.cartLinesAdd?.cart)
      this.updateCartState(data.data.cartLinesAdd.cart);
  }

  async buyNow(e: any) {
    this.add(e);
    this.redirectToCheckout();
  }

  async remove(event: Event) {
    if (!this.cartId) return;

    const lineItemId = (event.currentTarget as HTMLElement).dataset
      .productLineItemId;

    if (!lineItemId) {
      console.error("Line item ID not found.");
      return;
    }

    const mutation = `
    mutation {
      cartLinesRemove(cartId: "${this.cartId}", lineIds: ["${lineItemId}"]) {
        cart {
          id
          lines(first: 10) {
            edges {
              node {
                id
                quantity
                merchandise {
                  ... on ProductVariant {
                    id
                    title
                      priceV2 {
                    amount
                    currencyCode
                  }
                  compareAtPriceV2 {
                    amount
                    currencyCode
                  }
                    product {
                      title
                      images(first: 1) {
                        edges {
                          node {
                            url
                            altText
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
          cost {
            subtotalAmount {
              amount
              currencyCode
            }
          }
          checkoutUrl
        }
        userErrors {
          field
          message
        }
      }
    }`;

    await this.shopifyRequest(mutation);
    await this.getCart();
  }

  async updateCartQuantity(lineItemId: string, newQuantity: number) {
    const mutation = `
      mutation {
        cartLinesUpdate(cartId: "${this.cartId}", lines: [
          {
            id: "${lineItemId}",
            quantity: ${newQuantity}
          }
        ]) {
          cart {
            id
            lines(first: 10) {
              edges {
                node {
                  id
                  quantity
                  merchandise {
                    ... on ProductVariant {
                      id
                      title
                      priceV2 { amount currencyCode }
                      compareAtPriceV2 { amount currencyCode }
                      product {
                        title
                        images(first: 1) { edges { node { url altText } } }
                      }
                    }
                  }
                }
              }
            }
            cost { subtotalAmount { amount currencyCode } }
            checkoutUrl
          }
          userErrors { field message }
        }
      }`;

    const data = await this.shopifyRequest(mutation);
    if (data?.data?.cartLinesUpdate?.cart)
      this.updateCartState(data.data.cartLinesUpdate.cart);
  }

  async decrement(event: Event) {
    const lineItemId = (event.currentTarget as HTMLElement).dataset
      .productLineItemId;
    const quantity = Number(
      (event.currentTarget as HTMLElement).dataset.productQuantity
    );
    if (!lineItemId || isNaN(quantity))
      return console.error("Invalid line item ID or quantity");
    await this.updateCartQuantity(lineItemId, Math.max(0, quantity - 1));
  }

  async increment(event: Event) {
    const lineItemId = (event.currentTarget as HTMLElement).dataset
      .productLineItemId;
    const quantity = Number(
      (event.currentTarget as HTMLElement).dataset.productQuantity
    );
    if (!lineItemId || isNaN(quantity))
      return console.error("Invalid line item ID or quantity");
    await this.updateCartQuantity(lineItemId, quantity + 1);
  }

  mustacheViewValueChanged() {
    this.renderCart();
  }

  cartTargetConnected() {
    this.renderCart();
  }

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

  async fetchCheckoutUrl(): Promise<string | null> {
    const query = `
      query {
        cart(id: "${this.cartId}") {
          id
          checkoutUrl
        }
      }`;

    const data = await this.shopifyRequest(query);
    return data?.data?.cart?.checkoutUrl || null;
  }

  async redirectToCheckout() {
    if (!this.cartId) {
      console.error("Cart ID is missing.");
      return;
    }

    this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };

    try {
      const checkoutUrl = await this.fetchCheckoutUrl();
      if (checkoutUrl) {
        const checkoutURL = new URL(checkoutUrl);
        checkoutURL.searchParams.append(
          "return_to",
          new URL("/", window.location.href).toString()
        );

        try {
          // @ts-ignore
          posthog.capture("buy book");
        } catch (e) {
          console.warn("Posthog tracking failed:", e);
        }

        window.location.href = checkoutURL.toString();
      } else {
        console.error("Failed to retrieve checkout URL.");
      }
    } catch (error) {
      console.error("Error fetching checkout URL:", error);
    } finally {
      this.mustacheViewValue = { ...this.mustacheViewValue, loading: false };
    }
  }

  get shippingAddress() {
    try {
      return this.stripeShippingValue
        ? {
            country: this.stripeShippingValue.address.country,
          }
        : undefined;
    } catch (e) {
      return undefined;
    }
  }
}

function shopifyId(id: any) {
  if (typeof id === "string") {
    return id.replace(new RegExp("gid://shopify/[a-zA-Z]+/"), "");
  }
  return id;
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

interface Money {
  amount: string;
  currencyCode: string;
}

function currency(
  money: string | number | Money | undefined,
  currencyCode = "GBP"
): string {
  if (!money) return "";

  if (typeof money === "string") {
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
