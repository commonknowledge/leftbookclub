import { Controller } from "@hotwired/stimulus";
import type { StripeShippingAddressElementChangeEvent } from "@stripe/stripe-js";
import { createStorefrontApiClient } from '@shopify/storefront-api-client';
import Mustache from "mustache";
import Wax from "@jvitela/mustache-wax";
Wax(Mustache, { currency, pluralize, length, shopifyId, stringify });
import { isAfter } from "date-fns";

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

  get cartId() {
    const cartId = window.localStorage.getItem(this.LOCALSTORAGE_CHECKOUT_ID);
    return cartId ? cartId.toString() : "";
  }

  set cartId(id: string | number) {
    window.localStorage.setItem(this.LOCALSTORAGE_CHECKOUT_ID, id.toString());
  }

  async getCart(): Promise<CartValue | null> {
        if (!this.shopifyDomainValue || !this.shopifyStorefrontAccessTokenValue) {
        throw new Error("Shopify could not initialise due to lack of shopifyDomainValue / shopifyStorefrontAccessTokenValue");
    }

    this.client = createStorefrontApiClient({
        storeDomain: "https://left-book-club-shop.myshopify.com/",
        apiVersion: "2024-10",
        publicAccessToken: this.shopifyStorefrontAccessTokenValue!,
    });


   
    if (!this.cartId) {
        return this.resetCart();
    }

    const query = `
    query {
      cart(id: "${this.cartId}") {
        id
        createdAt
        updatedAt
        lines(first: 10) {
          edges {
            node {
              id
              quantity
               merchandise {
                ... on ProductVariant {
                  id
                  title
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
              attributes {
                key
                value
              }
            }
          }
        }
        attributes {
          key
          value
        }
        cost {
          totalAmount {
            amount
            currencyCode
          }
          subtotalAmount {
            amount
            currencyCode
          }
          totalTaxAmount {
            amount
            currencyCode
          }
          totalDutyAmount {
            amount
            currencyCode
          }
        }
        buyerIdentity {
          email
          phone
          customer {
            id
          }
          countryCode
          deliveryAddressPreferences {
            ... on MailingAddress {
              address1
              address2
              city
              provinceCode
              countryCodeV2
              zip
            }
          }
          preferences {
            delivery {
              deliveryMethod
            }
          }
        }
      }
    }`;

    try {
      const apiUrl = `https://${this.shopifyDomainValue}/api/2024-10/graphql.json`;

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Shopify-Storefront-Access-Token': this.shopifyStorefrontAccessTokenValue!,
        },
        body: JSON.stringify({ data: { query } }),
      });
      const data = await response.json();
      const cart = data?.data?.cart;

        if (!cart) {
            console.warn('Cart not found. Resetting cart.');
            return this.resetCart();
        }

        return cart;

    } catch (error) {
        console.error('Failed to fetch cart:', error);
        return this.resetCart();
    }
}

async resetCart(): Promise<CartValue | null> {
  try {
    if (!this.shopifyDomainValue || !this.shopifyStorefrontAccessTokenValue) {
      throw new Error("Shopify initialization failed: Missing domain or access token");
    }

    const apiUrl = `https://${this.shopifyDomainValue}/api/2024-10/graphql.json`;

    const query = `
      mutation {
        cartCreate(input: {
          buyerIdentity: { email: "${this.userEmailValue}" },
          lines: []
        }) {
          cart {
            id
            checkoutUrl
            lines(first: 10) {
              edges {
                node {
                  id
                  quantity
                  merchandise {
                    ... on ProductVariant {
                      id
                      title
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
              totalAmount {
                amount
                currencyCode
              }
            }
          }
          userErrors {
            field
            message
          }
        }
      }
    `;

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Storefront-Access-Token': this.shopifyStorefrontAccessTokenValue!,
      },
      body: JSON.stringify({ query }),
    });

    const data = await response.json();
    const newCart = data?.data?.cartCreate?.cart;

    if (!newCart) {
      console.error('Failed to create a new cart:', data?.errors || data?.data?.cartCreate?.userErrors);
      return null;
    }

    this.cartId = newCart.id;
    this.cartValue = newCart;

    return newCart;

  } catch (error) {
    console.error('Error creating new cart:', error);
    return null;
  }
}

async add({ params: { variantId } }: any) {
  if (!this.cartId) return;

  this.mustacheViewValue = { ...this.mustacheViewValue, loading: true };

  const apiUrl = `https://${this.shopifyDomainValue}/api/2024-10/graphql.json`;

  const query = `
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
          totalAmount {
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
  console.log('Adding product with query:', query);

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Storefront-Access-Token': this.shopifyStorefrontAccessTokenValue!,
      },
      body: JSON.stringify({ query }),
    });

    const data = await response.json();
    const cart = data?.data?.cartLinesAdd?.cart;

    if (cart) {
      this.cartValue = cart;
      this.mustacheViewValue = {
        loading: false,
        hasLineItems: cart.lines.edges.length > 0,
        lineItems: cart.lines.edges.map((edge: any) => {
          const lineItem = edge.node;
          const productImages = lineItem.merchandise.product.images.edges;

          return {
            id: lineItem.id,
            quantity: lineItem.quantity,
            title: lineItem.merchandise.product.title,
            variantId: lineItem.merchandise.id,
            canDecreaseQuantity: lineItem.quantity > 1,
            imageUrl: productImages?.[0]?.node?.url,
            imageAlt: productImages?.[0]?.node?.altText
          };
        }),
        checkout: cart.checkoutUrl,
        totalCost: cart.cost.totalAmount.amount,
        currency: cart.cost.totalAmount.currencyCode
      };
    } else {
      console.error('Failed to add item to cart:', data?.data?.cartLinesAdd?.userErrors);
      this.mustacheViewValue = { ...this.mustacheViewValue, loading: false };
    }

  } catch (error) {
    console.error('Error adding item to cart:', error);
    this.mustacheViewValue = { ...this.mustacheViewValue, loading: false };
    await this.resetCart();
    await this.add({ params: { variantId } });
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
  if (typeof id === 'string') {
    return id.replace(new RegExp("gid://shopify/[a-zA-Z]+/"), "");
  }
  return id;
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