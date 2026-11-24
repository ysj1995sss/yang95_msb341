import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

// base "./" keeps every asset path relative, so the same build works on Vercel, Netlify and a
// GitHub Pages project page (https://user.github.io/repo/).
export default defineConfig({
  base: "./",
  // The service worker reads this list to keep every file, including the game screens that load on demand.
  build: {
    manifest: "asset-manifest.json",
    // The question banks are their own file, so a change to the app's code doesn't make people download them again.
    rollupOptions: { output: { manualChunks: (id: string) => (/src[\/]data[\/](trivia|choices|library)[\/]/.test(id) ? "questions" : undefined) } },
  },
  plugins: [react(), tailwindcss()],
  test: { environment: "node" },
});
