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
      manifest: true,
      emptyOutDir: true,
      polyfillModulePreload: false,
      rollupOptions: {
        output: {
          dir: "vite_dist",
        },
        input: BUNDLE_ENTRYPOINTS,
      },
    },
  };
});
