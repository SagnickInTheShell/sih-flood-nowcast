import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0B2545",
        navySoft: "#13355E",
        teal: "#00A8B5",
        gold: "#E8A33D",
        sky: "#EAF4FA",
        riskRed: "#C0392B",
        riskAmber: "#E8A33D",
        safeGreen: "#1F6B57",
        textDark: "#1F2937",
      },
    },
  },
  plugins: [],
} satisfies Config;
