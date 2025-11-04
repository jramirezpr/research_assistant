import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        personality: {
          helpful: "#14b8a6", // turquoise
          formal: "#800020", // burgundy
          casual: "#fb7185", // coral pink
        },
      },
    },
  },
  safelist: [
    "text-personality-helpful",
    "text-personality-formal",
    "text-personality-casual",
    "btn-helpful",
    "btn-formal",
    "btn-casual",
    "bg-personality-helpful",
    "bg-personality-formal",
    "bg-personality-casual",
  ],
  plugins: [],
};

export default config;
