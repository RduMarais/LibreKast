module.exports = {
  content: [
    "/Users/romain/Stratus/info/server/tests_beekast/LibreKast/pollsite/templates/base_layout.html",
    "/Users/romain/Stratus/info/server/tests_beekast/LibreKast/pollsite/templates/**/*.html",
    "/Users/romain/Stratus/info/server/tests_beekast/template_html_tailwinds/*.html",
    "/Users/romain/Stratus/info/server/tests_beekast/template_html_tailwinds/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        "pour1nf0-pink": {
          "50": "#fe609f",
          "100": "#f45695",
          "200": "#ea4c8b",
          "300": "#e04281",
          "400": "#d63877",
          "500": "#cc2e6d",
          "600": "#c22463",
          "700": "#b81a59",
          "800": "#ae104f",
          "900": "#a40645"
        },
        "pour1nf0-purple": {
          "50": "#b158d8",
          "100": "#a74ece",
          "200": "#9d44c4",
          "300": "#933aba",
          "400": "#8930b0",
          "500": "#7f26a6",
          "600": "#751c9c",
          "700": "#6b1292",
          "800": "#610888",
          "900": "#57007e"
        },
        "pour1nf0-blue": {
          "50": "#56b4ef",
          "100": "#4caae5",
          "200": "#42a0db",
          "300": "#3896d1",
          "400": "#2e8cc7",
          "500": "#2482bd",
          "600": "#1a78b3",
          "700": "#106ea9",
          "800": "#06649f",
          "900": "#005a95"
        },
        "pour1nf0-back": {
          "50": "#5d6c82",
          "100": "#536278",
          "200": "#49586e",
          "300": "#3f4e64",
          "400": "#35445a",
          "500": "#2b3a50",
          "600": "#213046",
          "700": "#17263c",
          "800": "#0d1c32",
          "900": "#031228"
        },
        "pour1nf0-dark": {
          "50": "#4e5e70",
          "100": "#445466",
          "200": "#3a4a5c",
          "300": "#304052",
          "400": "#263648",
          "500": "#1c2c3e",
          "600": "#122234",
          "700": "#08182a",
          "800": "#000e20",
          "900": "#000416"
        }
      },
      fontFamily: {
        sans: ['Graphik', 'sans-serif'],
        serif: ['Merriweather', 'serif'],
      },
      spacing: {
        '8xl': '96rem',
        '9xl': '128rem',
      },
      borderRadius: {
        '4xl': '2rem',
      }
    }
  },
  plugins: [],
  darkMode: 'class',
}
