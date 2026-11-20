import { j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { s as sanitizeColor, d as clampNumber } from './index-D4UN33jT.js';
import { u as useAnimationPause } from './useAnimationLoop-BFrqRpQz.js';
import { m as motion } from './vendor-motion-BnKR5j6s.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-recharts-BDHDAAEe.js';

const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
function SpotlightBg({ settings }) {
  const spotlightColor = sanitizeColor(settings.spotlightColor, "#818cf8");
  const spotlightSize = clampNumber(settings.spotlightSize, 100, 1e3, 400);
  const paused = useAnimationPause();
  const blur1 = isMobile ? 0 : 60;
  const blur2 = isMobile ? 0 : 80;
  if (paused) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0 overflow-hidden" });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "absolute inset-0 overflow-hidden", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        className: "absolute",
        animate: {
          x: ["-20%", "120%", "-20%"],
          y: ["-10%", "80%", "-10%"]
        },
        transition: {
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut"
        },
        style: {
          width: spotlightSize,
          height: spotlightSize,
          background: `radial-gradient(circle, ${spotlightColor}40 0%, transparent 70%)`,
          borderRadius: "50%",
          filter: `blur(${blur1}px)`
        }
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        className: "absolute",
        animate: {
          x: ["120%", "-20%", "120%"],
          y: ["80%", "-10%", "80%"]
        },
        transition: {
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut"
        },
        style: {
          width: spotlightSize * 0.8,
          height: spotlightSize * 0.8,
          background: `radial-gradient(circle, ${spotlightColor}30 0%, transparent 70%)`,
          borderRadius: "50%",
          filter: `blur(${blur2}px)`
        }
      }
    )
  ] });
}

export { SpotlightBg as default };
