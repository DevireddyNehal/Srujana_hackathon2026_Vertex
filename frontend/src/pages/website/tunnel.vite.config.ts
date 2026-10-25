import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const tunnelHost = process.env.VERTEX_TUNNEL_HOST;

if (tunnelHost && !/^[a-z0-9][a-z0-9-]*\.trycloudflare\.com$/i.test(tunnelHost)) {
  throw new Error("VERTEX_TUNNEL_HOST must be a Cloudflare Quick Tunnel hostname.");
}

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
