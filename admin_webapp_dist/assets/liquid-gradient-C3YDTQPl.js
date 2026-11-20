import { j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { s as sanitizeColor, a as safeSelect, d as clampNumber, c as cn } from './index-D4UN33jT.js';
import { u as useAnimationPause } from './useAnimationLoop-BFrqRpQz.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
const BLOBS = [
  { anim: "animate-move-vertical", baseDuration: 30, top: "5%", left: "10%" },
  { anim: "animate-move-in-circle", baseDuration: 20, top: "35%", left: "50%" },
  { anim: "animate-move-horizontal", baseDuration: 40, top: "55%", left: "15%" },
  { anim: "animate-move-in-circle-slow", baseDuration: 40, top: "15%", left: "55%" }
];
const SPEED_MULTIPLIERS = {
  slow: 1.6,
  normal: 1,
  fast: 0.5
};
function LiquidGradientBackground({ settings }) {
  const paused = useAnimationPause();
  const colors = [
    sanitizeColor(settings.color1, "#6366f1"),
    sanitizeColor(settings.color2, "#ec4899"),
    sanitizeColor(settings.color3, "#22d3ee"),
    sanitizeColor(settings.color4, "#a855f7")
  ];
  const speed = safeSelect(settings.speed, ["slow", "normal", "fast"], "normal");
  const blurAmount = clampNumber(settings.blurAmount, 10, 120, 60);
  const multiplier = SPEED_MULTIPLIERS[speed];
  const effectiveBlur = isMobile ? Math.min(blurAmount, 30) : blurAmount;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0 overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0", style: { filter: `blur(${effectiveBlur}px)` }, children: BLOBS.map((blob, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: cn("absolute h-[55%] w-[55%] rounded-full", blob.anim),
      style: {
        top: blob.top,
        left: blob.left,
        opacity: 0.7,
        background: `radial-gradient(circle at center, ${colors[i]} 0%, transparent 65%)`,
        animationDuration: `${blob.baseDuration * multiplier}s`,
        animationPlayState: paused ? "paused" : "running"
      }
    },
    i
  )) }) });
}

export { LiquidGradientBackground as default };
