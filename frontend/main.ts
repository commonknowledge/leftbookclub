import "./scss/main.scss";
import "@hotwired/turbo";
import "bootstrap";
import * as Sentry from "@sentry/browser";
import { BrowserTracing } from "@sentry/tracing";

import { startApp } from "groundwork-ui";

const controllers = import.meta.glob("./controllers/*-controller.ts");

// @ts-ignore
if (typeof window !== undefined && !!window.SENTRY_DSN) {
  Sentry.init({
    // @ts-ignore
    dsn: window.SENTRY_DSN,

    // Alternatively, use `process.env.npm_package_version` for a dynamic release version
    // if your build tool supports it.
    // release: "my-project-name@2.3.12",
    integrations: [new BrowserTracing()],

    // Set tracesSampleRate to 1.0 to capture 100%
    // of transactions for performance monitoring.
    // We recommend adjusting this value in production
    tracesSampleRate: 0.25,
  });
}

startApp(controllers);
