import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "../ArmorX.Windows/wwwroot",
    emptyOutDir: true,
    sourcemap: false,
  },
});
