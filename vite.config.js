import { defineConfig } from "vite";
import purgecss from "@fullhuman/postcss-purgecss";
import tailwindcss from "tailwindcss";
import tailwindNesting from "tailwindcss/nesting";
import postcssImport from "postcss-import";
import autoprefixer from "autoprefixer";

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
                postcssImport,
                tailwindNesting,
                tailwindcss,
                autoprefixer,
                purgecss({
                  content: [
                    "./app/**/*.{py,html,js,ts}",
                    "./frontend/**/*.{html,js,ts}",
                    "./static/**/*.{html,js,ts}",
                  ],
                }),
              ],
            },
          }
        : {
            postcss: {
              plugins: [postcssImport, tailwindNesting, tailwindcss],
            },
          },
  };
});
