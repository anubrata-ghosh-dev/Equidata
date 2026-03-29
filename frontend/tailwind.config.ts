import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./services/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0B0B0F",
        panel: "#14141C",
        panelSoft: "#1B1B26",
        accent: "#5B7CFF",
        accentAlt: "#8B5CF6",
        textMain: "#F5F7FF",
        textMuted: "#9DA3B6",
        danger: "#F43F5E",
        success: "#22C55E"
      },
      boxShadow: {
        panel: "0 12px 36px rgba(0,0,0,0.35)",
        glow: "0 0 0 1px rgba(91,124,255,0.18), 0 8px 30px rgba(91,124,255,0.22)"
      },
      borderRadius: {
        xl2: "1rem",
        xl3: "1.25rem"
      }
    }
  },
  plugins: []
};

export default config;
