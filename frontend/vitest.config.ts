import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Separate from vite.config.ts on purpose — the dev-server proxy config and the
// test config must not be able to interfere with each other.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
