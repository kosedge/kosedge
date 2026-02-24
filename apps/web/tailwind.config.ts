import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ---- Brand ----
        "kos-green": "#22c55e",
        "kos-green-deep": "#15803d",
        "kos-gold": "#fbbf24",
        "kos-gold-metal": "#d4af37",

        // ---- Foundation ----
        "kos-black": "#0f0f0f",
        "kos-surface": "#111827",
        "kos-surface-2": "#1f2937",
        "kos-border": "#2a3647",
        "kos-text": "#ffffff",
        "kos-text-2": "#d1d5db",
        "kos-muted": "#9ca3af",

        // ---- Semantic ----
        "kos-success": "#34d399",
        "kos-danger": "#ef4444",
        "kos-warning": "#f59e0b",
        "kos-info": "#60a5fa",
      },
      fontFamily: {
        display: ['"Bebas Neue"', "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        accent: ["Oswald", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [typography],
};

export default config;