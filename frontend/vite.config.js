import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  base: "/static/",
  build: {
    manifest: true,
    rollupOptions: {
      input: "src/main.js",
    },
    outDir: "dist",
  },
  server: {
    port: 5173,
  },
});
