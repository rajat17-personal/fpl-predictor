import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// api/main.py mounts StaticFiles(directory=config.ROOT / "web") at "/", so a file at
// web/data/meta.json is served at GET /data/meta.json — NOT /web/data/meta.json. Both
// prefixes below must target the same running uvicorn process (localhost:8000).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/data": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
