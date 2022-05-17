import "./scss/main.scss";
import "@hotwired/turbo";
import "bootstrap";
import initialiseSentry from "./sentry";
import initialisePosthog from "./posthog";
import { startApp } from "groundwork-ui";
const controllers = import.meta.glob("./controllers/*-controller.ts");

initialisePosthog();
initialiseSentry();
startApp(controllers);
