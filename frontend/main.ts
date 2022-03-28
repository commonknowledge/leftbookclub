import 'vite/modulepreload-polyfill'
import "./scss/main.scss";
import "@hotwired/turbo";

import { startApp } from "groundwork-ui";

const controllers = import.meta.glob("./controllers/*-controller.ts");

startApp(controllers);
