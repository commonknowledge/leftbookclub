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

initialisePosthog();
initialiseSentry();
startApp(controllers);

import { Application } from "@hotwired/stimulus";
import ReadMore from "stimulus-read-more";
const application = Application.start();
application.register("read-more", ReadMore);
application.debug = true;
