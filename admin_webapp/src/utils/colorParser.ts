const COLORS: Record<string, [number, number, number]> = {
  cyan: [34, 211, 238],
  teal: [32, 201, 151],
  green: [64, 192, 87],
  lime: [130, 201, 30],
  yellow: [250, 176, 5],
  orange: [253, 126, 20],
  red: [250, 82, 82],
  pink: [230, 73, 128],
  grape: [190, 75, 219],
  violet: [151, 117, 250],
  indigo: [92, 124, 250],
  blue: [34, 139, 230],
  gray: [134, 142, 150],
  dark: [55, 58, 64],
};

const DEFAULT_COLOR = COLORS.cyan;

const hexToRgb = (hex: string): [number, number, number] | null => {
  const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return match ? [parseInt(match[1], 16), parseInt(match[2], 16), parseInt(match[3], 16)] : null;
};

const getRgb = (color: string): [number, number, number] =>
  COLORS[color] ?? hexToRgb(color) ?? DEFAULT_COLOR;

export interface ColorGradientStyle {
  background: string;
  border: string;
  boxShadow?: string;
}

export const getColorGradient = (color: string, light?: boolean): ColorGradientStyle => {
  const [r, g, b] = getRgb(color);
  if (light) {
    return {
      background: `linear-gradient(135deg, rgba(${r},${g},${b},0.12) 0%, rgba(${r},${g},${b},0.05) 100%)`,
      border: `1px solid rgba(${r},${g},${b},0.2)`,
      boxShadow: `0 1px 3px rgba(${r},${g},${b},0.1)`,
    };
  }
  return {
    background: `linear-gradient(135deg, rgba(${r},${g},${b},0.15) 0%, rgba(${r},${g},${b},0.08) 100%)`,
    border: `1px solid rgba(${r},${g},${b},0.3)`,
  };
};

export const getColorGradientSolid = (color: string, light?: boolean): ColorGradientStyle => {
  const [r, g, b] = getRgb(color);
  if (light) {
    // Light theme: soft tinted background instead of dark solid
    const light1 = [245 + r * 0.02, 243 + g * 0.02, 240 + b * 0.02].map((v) =>
      Math.min(255, Math.floor(v)),
    );
    const light2 = [240 + r * 0.03, 237 + g * 0.03, 233 + b * 0.03].map((v) =>
      Math.min(255, Math.floor(v)),
    );
    return {
      background: `linear-gradient(135deg, rgb(${light1}) 0%, rgb(${light2}) 100%)`,
      border: `1px solid rgba(${r},${g},${b},0.25)`,
      boxShadow: `0 1px 4px rgba(${r},${g},${b},0.12)`,
    };
  }
  const dark1 = [22 + r * 0.08, 27 + g * 0.08, 35 + b * 0.08].map(Math.floor);
  const dark2 = [20 + r * 0.05, 24 + g * 0.05, 30 + b * 0.05].map(Math.floor);

  return {
    background: `linear-gradient(135deg, rgb(${dark1}) 0%, rgb(${dark2}) 100%)`,
    border: `1px solid rgba(${r},${g},${b},0.4)`,
    boxShadow: `inset 0 0 20px rgba(${r},${g},${b},0.15)`,
  };
};
