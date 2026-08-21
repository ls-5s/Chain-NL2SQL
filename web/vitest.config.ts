import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Vitest 2 resolves its own Vite 5 type while the app uses Vite 6.
  // The plugin API is compatible; keep the config type boundary explicit.
  plugins: [vue() as any],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/tests/**/*.spec.ts"],
  },
});
