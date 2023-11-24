import { defineConfig } from "vite";
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
      modulePreload: {
        polyfill: command === "build",
      },
      rollupOptions: {
        output: {
          dir: "vite/",
        },
        input: BUNDLE_ENTRYPOINTS,
      },
    },
    server: {
      port: 3001,
      strictPort: true,
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
