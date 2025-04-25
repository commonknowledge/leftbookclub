import "./scss/main.scss";
import "./scss/tailwind.scss";
import "@hotwired/turbo";
import * as Turbo from "@hotwired/turbo";
import "bootstrap";
import initialiseSentry from "./sentry";
import initialisePosthog from "./posthog";
import { startApp } from "groundwork-django";
const controllers = import.meta.glob("./controllers/*-controller.ts");
Turbo.session.drive = false;

console.log("running");

initialisePosthog();
initialiseSentry();
const application = startApp(controllers);

import ReadMore from "stimulus-read-more";
application.register("read-more", ReadMore);
application.debug = true;
