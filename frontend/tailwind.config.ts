import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/remotion/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vice: {
          bg: "#07070d",
          panel: "#10101b",
          card: "#161626",
          border: "#26263f",
          pink: "#ff2e93",
          cyan: "#00f0ff",
          sunset: "#ff8a3d",
          gold: "#ffd43b",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-montserrat)", "Impact", "sans-serif"],
        condensed: ["var(--font-anton)", "Impact", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        "neon-pink": "0 0 28px rgba(255, 46, 147, 0.35)",
        "neon-cyan": "0 0 28px rgba(0, 240, 255, 0.32)",
      },
    },
  },
  plugins: [],
};

export default config;
