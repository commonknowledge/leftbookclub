/// <reference types="vite/client" />

declare module "*.css";

export declare global {
  interface Window {
    POSTHOG_PUBLIC_TOKEN?: string;
    POSTHOG_URL?: string;
    DEBUG: boolean;
    SENTRY_PROJECT_ID?: string;
    SENTRY_ORG_SLUG?: string;
    SENTRY_DSN?: string;
    FLY_APP_NAME?: string;
    GIT_SHA?: string;
    STRIPE_LIVE_MODE: boolean;
    userData?: {
      is_authenticated: boolean;
      set?: {
        django_id: string;
        email?: string;
        name?: string;
        stripe_customer_id?: string;
        staff: boolean;
      };
      register: {
        shipping_city?: string;
        shipping_country?: string;
        subscription_billing_interval?: string;
        subscription_price?: string;
        primary_stripe_product_name?: string;
        primary_stripe_product_id?: string;
      };
    };
  }
}
