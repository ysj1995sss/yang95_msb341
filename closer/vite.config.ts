import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

// base "./" keeps every asset path relative, so the same build works on Vercel, Netlify and a
// GitHub Pages project page (https://user.github.io/repo/).
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  test: { environment: "node" },
});
