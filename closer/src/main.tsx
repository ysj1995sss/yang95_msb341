import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { listenForInstall } from "./utils/install";

// The browser can offer "install" before any screen has loaded; keep it until a button wants it.
listenForInstall();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Lets the built site open offline once it has been visited. Skipped in `npm run dev`, where a
// cached copy would hide edits.
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => undefined);
  });
}
