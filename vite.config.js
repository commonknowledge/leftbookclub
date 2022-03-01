import { defineConfig } from "vite";

const BUNDLE_ENTRYPOINTS = {
  main: "./frontend/main.ts",
};

export default defineConfig(() => {
  return {
    base: "/static/",
    optimizeDeps: {
      entries: Object.values(BUNDLE_ENTRYPOINTS),
    },
    build: {
      mainifest: true,
      emptyOutDir: true,
      rollupOptions: {
        output: {
          dir: "dist/",
        },
        input: BUNDLE_ENTRYPOINTS,
      },
    },
  };
});
