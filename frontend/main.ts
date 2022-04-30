import "./scss/main.scss";
import "@hotwired/turbo";
import "bootstrap";
import "./scss/tailwind.scss";

import { startApp } from "groundwork-ui";

const controllers = import.meta.glob("./controllers/*-controller.ts");

startApp(controllers);
