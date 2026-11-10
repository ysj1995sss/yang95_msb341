import { describe, expect, it } from "vitest";
import indexHtml from "../index.html?raw";
import manifestText from "../public/manifest.webmanifest?raw";
import serviceWorker from "../public/sw.js?raw";

// The installable-app files are plain files in public/, so they're checked as files: a broken
// manifest or a missing icon silently turns the "Install" option off.
const manifest = JSON.parse(manifestText) as {
  name: string; short_name: string; start_url: string; scope: string; display: string;
  background_color: string; theme_color: string;
  icons: { src: string; sizes: string; type: string; purpose?: string }[];
};
const iconFiles = Object.keys(import.meta.glob("../public/icons/*.png"));
const hasFile = (path: string) => iconFiles.includes(`../public/${path}`);

describe("installable app", () => {
  it("has a manifest that makes the site installable and relative to wherever it is hosted", () => {
    expect(manifest.name).toBe("Closer");
    expect(manifest.short_name).toBe("Closer");
    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("./");
    expect(manifest.scope).toBe("./");
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i);
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("lists 192 and 512 pixel icons, a maskable one, and every file exists", () => {
    const sizes = manifest.icons.map((i) => i.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");
    expect(manifest.icons.some((i) => i.purpose?.includes("maskable"))).toBe(true);
    for (const icon of manifest.icons) {
      expect(icon.src.startsWith("./")).toBe(true);
      expect(hasFile(icon.src.slice(2))).toBe(true);
    }
    expect(hasFile("icons/apple-touch-icon.png")).toBe(true);
  });

  it("links the manifest and phone home-screen icon from the page", () => {
    expect(indexHtml).toContain('rel="manifest" href="./manifest.webmanifest"');
    expect(indexHtml).toContain('rel="apple-touch-icon" href="./icons/apple-touch-icon.png"');
    expect(indexHtml).toContain('name="mobile-web-app-capable"');
  });

  it("ships an offline service worker that cleans up old caches and falls back to the cached page", () => {
    expect(serviceWorker).toContain("caches.open");
    expect(serviceWorker).toContain("caches.delete");
    expect(serviceWorker).toContain('addEventListener("fetch"');
    expect(serviceWorker).toContain("index.html");
  });

  it("also keeps the Google Fonts files, so the offline app looks the same", () => {
    expect(serviceWorker).toContain("fonts.googleapis.com");
    expect(serviceWorker).toContain("fonts.gstatic.com");
    expect(indexHtml).toContain("fonts.googleapis.com/css2");
  });
});
