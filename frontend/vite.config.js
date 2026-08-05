import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 10000,
    rollupOptions: {
      onwarn(warning, warn) {
        warn(warning);
      },
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (
              id.includes("react") ||
              id.includes("react-dom") ||
              id.includes("react-router-dom")
            ) {
              return "vendor-react";
            }
            if (id.includes("recharts")) {
              return "vendor-recharts";
            }
            if (id.includes("chart.js") || id.includes("react-chartjs-2")) {
              return "vendor-charts";
            }
            if (id.includes("lucide-react") || id.includes("react-icons")) {
              return "vendor-ui";
            }
            if (
              id.includes("radix-ui") ||
              id.includes("@radix-ui") ||
              id.includes("cmdk") ||
              id.includes("sonner") ||
              id.includes("next-themes")
            ) {
              return "vendor-radix";
            }
            if (
              id.includes("react-phone-number-input") ||
              id.includes("clsx") ||
              id.includes("tailwind-merge") ||
              id.includes("class-variance-authority")
            ) {
              return "vendor-misc";
            }
            // All other node_modules go into vendor
            return "vendor";
          }
        },
      },
    },
    // Enable minification for production
    minify: true, // Uses Rolldown's built-in minifier
    sourcemap: false,
  },
  // server: {
  //   host: true, // or use '0.0.0.0' to expose on all network interfaces
  //   port: 5173,
  // },
});
