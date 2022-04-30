module.exports = {
  prefix: "tw-",
  content: [
    "./app/**/*.{py,html,js,ts}",
    "./frontend/**/*.{html,js,ts}",
    "./static/**/*.{html,js,ts}",
  ],
  theme: {
    extend: {
      spacing: {
        1: "5px",
        2: "10px",
        3: "15px",
        4: "20px",
        5: "40px",
        6: "80px",
      },
      colors: {
        background: "#F2F0F0",
        black: "#231F20",
        yellow: "#F8F400",
        teal: "#46A9C2",
        darkgreen: "#2D936C",
        lilacgrey: "#A5A1BB",
        coral: "#FE825E",
        purple: "#9A93FF",
        magenta: "#FF55B4",
        pink: "#FFBBD2",
        lightgreen: "#8FBB99",
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false,
  },
};
