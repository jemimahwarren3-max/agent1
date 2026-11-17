import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070b16",
          900: "#0c1324",
          800: "#121b33",
          700: "#1b2744",
        },
        accent: {
          500: "#3b82f6",
          400: "#60a5fa",
        },
      },
    },
  },
  plugins: [],
};

export default config;
