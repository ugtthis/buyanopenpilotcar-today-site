import { defineConfig } from "vite";
import solid from "vite-plugin-solid";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss(), solid()],
  server: {
    fs: {
      // Allow serving files from the repo root (needed to import pipeline/data/)
      allow: [".."],
    },
  },
});
