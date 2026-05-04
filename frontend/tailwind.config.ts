import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:      "var(--bg)",
        surface: "var(--surface)",
        border:  "var(--border)",
        text:    "var(--text)",
        muted:   "var(--muted)",
      },
    },
  },
  plugins: [],
};

export default config;
