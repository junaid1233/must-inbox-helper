import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// /api is proxied to the FastAPI backend so the browser talks to one origin in development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
  },
});
