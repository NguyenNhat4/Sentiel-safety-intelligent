import react from "@vitejs/plugin-react";
import {defineConfig} from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {target: "http://127.0.0.1:8000", ws: true},
      "/snapshots": {target: "http://127.0.0.1:8000"},
      "/vision-worker-cpu-api": {
        target: process.env.VISION_WORKER_CPU_DEV_URL ?? "http://127.0.0.1:8101",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vision-worker-cpu-api/, "")
      },
      "/vision-worker-gpu-api": {
        target: process.env.VISION_WORKER_GPU_DEV_URL ?? "http://127.0.0.1:8102",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vision-worker-gpu-api/, "")
      }
    }
  }
});
