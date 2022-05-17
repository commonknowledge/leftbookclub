import * as Sentry from "@sentry/browser";
import { BrowserTracing } from "@sentry/tracing";
import posthog from "posthog-js";
import type * as SentryTypes from "@sentry/types";

export default function initialiseSentry() {
  // @ts-ignore
  if (typeof window !== undefined && !!window.SENTRY_DSN) {
    const integrations: SentryTypes.Options["integrations"] = [
      new BrowserTracing(),
    ];

    // @ts-ignore
    if (!!window.SENTRY_ORG_SLUG && !!window.SENTRY_PROJECT_ID) {
      integrations.push(
        new posthog.SentryIntegration(
          posthog,
          // @ts-ignore
          window.SENTRY_ORG_SLUG,
          // @ts-ignore
          parseInt(window.SENTRY_PROJECT_ID)
        )
      );
    }

    Sentry.init({
      // @ts-ignore
      dsn: window.SENTRY_DSN,

      // @ts-ignore
      environment: window.FLY_APP_NAME,

      // @ts-ignore
      release: window.GIT_SHA,

      // Alternatively, use `process.env.npm_package_version` for a dynamic release version
      // if your build tool supports it.
      // release: "my-project-name@2.3.12",
      integrations,

      // Set tracesSampleRate to 1.0 to capture 100%
      // of transactions for performance monitoring.
      // We recommend adjusting this value in production
      // @ts-ignore
      tracesSampleRate: window.STRIPE_LIVE_MODE ? 0.3 : 1,
    });
  }
}
