import "./scss/main.scss";
import "@hotwired/turbo";
import "bootstrap";
import initialiseSentry from "./sentry";
import { startApp } from "groundwork-ui";
const controllers = import.meta.glob("./controllers/*-controller.ts");

initialiseSentry();
startApp(controllers);
