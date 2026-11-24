import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { listenForInstall } from "./utils/install";
import { watchNavigation } from "./utils/navigation";
import { startUpdateWatch } from "./utils/update";
import { watchVisit } from "./utils/visit";

// The browser can offer "install" before any screen has loaded; keep it until a button wants it.
listenForInstall();

// Opening the app again starts every set on a fresh shuffle; going back returns to where you were.
// Both are set up before the first screen draws.
watchVisit();
watchNavigation();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Lets the built site open offline once it has been visited. Skipped in `npm run dev`, where a
// cached copy would hide edits.
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  startUpdateWatch();
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => undefined);
  });
}
