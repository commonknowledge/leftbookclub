const plugin = require("tailwindcss/plugin");
const {
  default: flattenColorPalette,
} = require("tailwindcss/lib/util/flattenColorPalette");
const {
  default: createUtilityPlugin,
} = require("tailwindcss/lib/util/createUtilityPlugin");

/** @type {import('tailwindcss').Config} */
module.exports = {
  prefix: "tw-",
  content: [
    "./app/**/*.{py,html,js,ts,tsx}",
    "./frontend/**/*.{html,js,ts,tsx}",
  ],
  theme: {
    /*
    // Match to bootstrap 5
    // https://getbootstrap.com/docs/5.0/layout/breakpoints/
    */
    screens: {
      sm: "576px",
      md: "768px",
      lg: "992px",
      xl: "1200px",
      xxl: "1400px",
    },
    extend: {
      spacing: {
        1: "5px",
        2: "10px",
        3: "15px",
        4: "20px",
        5: "40px",
        6: "80px",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      fontSize: {
        // // xl
        // font-family: Inter;
        // font-size: 64px;
        // font-style: normal;
        // font-weight: 700;
        // line-height: 110%;
        // letter-spacing: -3.2px;
        xl: [
          "64px",
          {
            lineHeight: "110%",
            letterSpacing: "-3.2px",
            fontWeight: "700",
          },
        ],

        // // lg
        // font-family: Inter;
        // font-size: 48px;
        // font-style: normal;
        // font-weight: 700;
        // line-height: 120%;
        // letter-spacing: -2.4px;
        lg: [
          "48px",
          {
            lineHeight: "120%",
            letterSpacing: "-2.4px",
            fontWeight: "700",
          },
        ],

        // // md
        // font-family: Inter;
        // font-size: 24px;
        // font-style: normal;
        // font-weight: 600;
        // line-height: 120%;
        // letter-spacing: -1.2px;
        md: [
          "24px",
          {
            lineHeight: "120%",
            letterSpacing: "-1.2px",
            fontWeight: "600",
          },
        ],

        // // body
        // font-family: Inter;
        // font-size: 18px;
        // font-style: normal;
        // font-weight: 400;
        // line-height: 140%;
        // letter-spacing: -0.9px;
        body: [
          "18px",
          {
            lineHeight: "140%",
            letterSpacing: "-0.9px",
            fontWeight: "400",
          },
        ],

        // // sm
        // font-family: Inter;
        // font-size: 14px;
        // font-style: normal;
        // font-weight: 600;
        // line-height: 120%;
        // text-transform: uppercase;
        sm: [
          "14px",
          {
            lineHeight: "120%",
            textTransform: "uppercase",
            fontWeight: "600",
          },
        ],

        // // caslon
        // font-family: Adobe Caslon Pro;
        // font-size: 14px;
        // font-style: normal;
        // font-weight: 400;
        // line-height: 100%
        // letter-spacing: 2.8px;
        // text-transform: uppercase;
        caslon: [
          "14px",
          {
            lineHeight: "100%",
            letterSpacing: "2.8px",
            textTransform: "uppercase",
            fontWeight: "400",
          },
        ],
      },
      colors: {
        background: "#F2F0F0",
        black: "#231F20",
        yellow: "#F8F400",
        teal: "#46A9C2",
        darkgreen: "#2D936C",
        lilacgrey: "#A5A1BB",
        coral: "#FE825E",
        purpleDark: "#5752ff",
        purple: "#9A93FF",
        purpleLight: "#dcdbff",
        magenta: "#FF55B4",
        pink: "#FFBBD2",
        lightgreen: "#8FBB99",
        brown: "#796E67",
      },
    },
  },
  plugins: [
    plugin(({ matchUtilities, theme }) => {
      matchUtilities(
        {
          "inline-shadow": (value) => ({
            boxShadow: `var(--tw-inline-shadow-width, ${theme(
              "spacing.1"
            )}) 0 0 ${value}, calc(-1 * var(--tw-inline-shadow-width, ${theme(
              "spacing.1"
            )})) 0 0 ${value}`,
          }),
        },
        {
          values: flattenColorPalette(theme("colors")),
          type: "color",
        }
      );
    }),
    createUtilityPlugin("spacing", [
      ["inline-shadow-width", ["--tw-inline-shadow-width"]],
    ]),
  ],
  corePlugins: {
    preflight: false,
  },
};
