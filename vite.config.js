import { defineConfig } from "vite";
import purgecss from "@fullhuman/postcss-purgecss";

const BUNDLE_ENTRYPOINTS = {
  main: "./frontend/main.ts",
};

export default defineConfig(({ command }) => {
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
          dir: "vite/",
        },
        input: BUNDLE_ENTRYPOINTS,
      },
    },
    css:
      command === "build"
        ? {
            postcss: {
              plugins: [
                purgecss({
                  content: [
                    "app/**/*.html",
                    "frontend/**/*.ts",
                    "static/**/*.js",
                  ],
                }),
              ],
            },
          }
        : undefined,
  };
});
