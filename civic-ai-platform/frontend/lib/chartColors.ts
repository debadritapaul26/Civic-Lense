export const CHART_COLORS = {
  teal: "#188b8c",
  tealDark: "#0f6f72",
  coral: "#ed6a5a",
  amber: "#d99a22",
  blue: "#4c78a8",
  violet: "#8064a2",
  grid: "#e5eaf0",
  mist: "#f6f8fb",
  ink: "#172033",
} as const;

export const CHART_SERIES_COLORS = [
  CHART_COLORS.teal,
  CHART_COLORS.coral,
  CHART_COLORS.blue,
  CHART_COLORS.amber,
  CHART_COLORS.violet,
] as const;
