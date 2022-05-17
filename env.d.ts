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
      id?: string;
      email?: string;
      name?: string;
      stripe_customer_id?: string;
    };
  }
}
