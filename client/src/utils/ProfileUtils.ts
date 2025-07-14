const colorPalette = [
  "#FF6B6B", // Red
  "#6BCB77", // Green
  "#4D96FF", // Blue
  "#FFD93D", // Yellow
  "#FF9F1C", // Orange
  "#9D4EDD", // Purple
  "#00B4D8", // Teal
  "#F15BB5"  // Pink
];

export function getUserColor(username:string):string {
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash; // Convert to 32bit integer
  }
  const index = Math.abs(hash) % colorPalette.length;
  return colorPalette[index];
}
