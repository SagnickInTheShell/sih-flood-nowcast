export const theme = {
  navy: "#0B2545",
  navySoft: "#13355E",
  teal: "#00A8B5",
  gold: "#E8A33D",
  sky: "#EAF4FA",
  riskRed: "#C0392B",
  riskAmber: "#E8A33D",
  safeGreen: "#1F6B57",
  textDark: "#1F2937",
} as const;

export const stateColor: Record<string, [number, number, number]> = {
  clear: [31, 107, 87],
  at_risk: [232, 163, 61],
  flooded: [192, 57, 43],
};

export const stateLabel: Record<string, string> = {
  clear: "Clear",
  at_risk: "At risk",
  flooded: "Flooded",
};
