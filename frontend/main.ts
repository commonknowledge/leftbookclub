import "./scss/main.scss";
import Turbo from "@hotwired/turbo";
import "bootstrap";
import initialiseSentry from "./sentry";
import initialisePosthog from "./posthog";
import { startApp } from "groundwork-ui";
const controllers = import.meta.glob("./controllers/*-controller.ts");
Turbo.session.drive = false;
console.log(Turbo);

initialisePosthog();
initialiseSentry();
startApp(controllers);
