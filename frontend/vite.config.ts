import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Bind-mounted source in Docker: polling makes hot reload reliable.
    watch: { usePolling: true },
  },
});
