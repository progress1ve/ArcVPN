import { j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { s as sanitizeColor, a as safeSelect, b as safeBoolean, c as cn } from './index-D4UN33jT.js';
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
const SPEED_DURATIONS = {
  slow: "90s",
  normal: "60s",
  fast: "30s"
};
function AuroraBackground({ settings }) {
  const firstColor = sanitizeColor(settings.firstColor, "#3b82f6");
  const secondColor = sanitizeColor(settings.secondColor, "#a5b4fc");
  const thirdColor = sanitizeColor(settings.thirdColor, "#93c5fd");
  const speed = safeSelect(settings.speed, ["slow", "normal", "fast"], "normal");
  const showRadialGradient = safeBoolean(settings.showRadialGradient, true);
  const paused = useAnimationPause();
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0 overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: cn(
        "pointer-events-none absolute -inset-[10px] opacity-50",
        !isMobile && "animate-aurora",
        showRadialGradient && "[mask-image:radial-gradient(ellipse_at_100%_0%,black_10%,transparent_70%)]"
      ),
      style: {
        backgroundImage: `repeating-linear-gradient(100deg, #000 0%, #000 7%, transparent 10%, transparent 12%, #000 16%), repeating-linear-gradient(100deg, ${firstColor} 10%, ${secondColor} 15%, ${thirdColor} 20%, ${secondColor} 25%, ${firstColor} 30%)`,
        backgroundSize: isMobile ? "100%, 100%" : "300%, 200%",
        animationDuration: SPEED_DURATIONS[speed],
        animationPlayState: paused ? "paused" : "running"
      }
    }
  ) });
}

export { AuroraBackground as default };
