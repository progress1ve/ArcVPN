import { R as React, r as reactExports, j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { d as clampNumber, s as sanitizeColor, b as safeBoolean } from './index-D4UN33jT.js';
import { a as useAnimationLoop, g as getMobileDpr } from './useAnimationLoop-BFrqRpQz.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

const COLORS = [
  "#93c5fd",
  "#f9a8d4",
  "#86efac",
  "#fde047",
  "#fca5a5",
  "#d8b4fe",
  "#a5b4fc",
  "#c4b5fd"
];
function hexToRgb(hex) {
  let value = hex.replace("#", "");
  if (value.length === 3)
    value = value.split("").map((c) => c + c).join("");
  if (!/^[0-9a-fA-F]{6}$/.test(value)) return [129, 140, 248];
  const v = parseInt(value, 16);
  return [v >> 16 & 255, v >> 8 & 255, v & 255];
}
const SKEW_X_TAN = Math.tan(-48 * Math.PI / 180);
const SKEW_Y_TAN = Math.tan(14 * Math.PI / 180);
const GRID_SCALE = 0.675;
const backgroundBoxes = React.memo(function BackgroundBoxes({ settings }) {
  const canvasRef = reactExports.useRef(null);
  const stateRef = reactExports.useRef(null);
  const rows = clampNumber(settings.rows, 4, 30, 15);
  const cols = clampNumber(settings.cols, 4, 30, 15);
  const boxColor = sanitizeColor(settings.boxColor, "#818cf8");
  const lineColor = sanitizeColor(settings.lineColor, "#334155");
  const multicolor = settings.multicolor === void 0 ? boxColor === "#818cf8" : safeBoolean(settings.multicolor, true);
  const cells = reactExports.useMemo(() => {
    return Array.from({ length: rows * cols }, () => ({
      rgb: hexToRgb(multicolor ? COLORS[Math.floor(Math.random() * COLORS.length)] : boxColor),
      phase: Math.random() * 8,
      period: 3 + Math.random() * 4
    }));
  }, [rows, cols, boxColor, multicolor]);
  reactExports.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = getMobileDpr();
    const parent = canvas.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    stateRef.current = { ctx, w: canvas.width, h: canvas.height };
    const onResize = () => {
      const r = parent.getBoundingClientRect();
      canvas.width = r.width * dpr;
      canvas.height = r.height * dpr;
      if (stateRef.current) {
        stateRef.current.w = canvas.width;
        stateRef.current.h = canvas.height;
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  useAnimationLoop(
    (now) => {
      const state = stateRef.current;
      if (!state) return;
      const { ctx, w, h } = state;
      const t = now * 1e-3;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      const cx = w / 2;
      const cy = h / 2;
      ctx.translate(cx, cy);
      ctx.transform(1, 0, SKEW_X_TAN, 1, 0, 0);
      ctx.transform(1, SKEW_Y_TAN, 0, 1, 0, 0);
      ctx.scale(GRID_SCALE, GRID_SCALE);
      ctx.translate(-cx, -cy);
      const gw = w * 3;
      const gh = h * 3;
      const ox = -w;
      const oy = -h;
      const cellW = gw / cols;
      const cellH = gh / rows;
      for (let i = 0; i < cells.length; i++) {
        const cell = cells[i];
        const cycleT = (t + cell.phase) % cell.period / cell.period;
        const alpha = 0.15 * Math.sin(cycleT * Math.PI);
        if (alpha < 5e-3) continue;
        const col = i % cols;
        const row = (i - col) / cols;
        const [r, g, b] = cell.rgb;
        ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`;
        ctx.fillRect(ox + col * cellW, oy + row * cellH, cellW, cellH);
      }
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let r = 0; r <= rows; r++) {
        const y = oy + r * cellH;
        ctx.moveTo(ox, y);
        ctx.lineTo(ox + gw, y);
      }
      for (let c = 0; c <= cols; c++) {
        const x = ox + c * cellW;
        ctx.moveTo(x, oy);
        ctx.lineTo(x, oy + gh);
      }
      ctx.stroke();
      ctx.restore();
    },
    [cells, rows, cols, lineColor]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "canvas",
    {
      ref: canvasRef,
      style: {
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%"
      }
    }
  );
});

export { backgroundBoxes as default };
