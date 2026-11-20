import { j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { a as safeSelect, s as sanitizeColor, d as clampNumber } from './index-D4UN33jT.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

function GridBackground({ settings }) {
  const variant = safeSelect(settings.variant, ["grid", "dots"], "grid");
  const gridColor = sanitizeColor(settings.gridColor, "rgba(255,255,255,0.05)");
  const gridSize = clampNumber(settings.gridSize, 10, 200, 40);
  const dotSize = clampNumber(settings.dotSize, 0.5, 10, 1.5);
  if (variant === "dots") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: "absolute inset-0",
        style: {
          backgroundImage: `radial-gradient(circle, ${gridColor} ${dotSize}px, transparent ${dotSize}px)`,
          backgroundSize: `${gridSize}px ${gridSize}px`
        }
      }
    );
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: "absolute inset-0",
      style: {
        backgroundImage: `linear-gradient(${gridColor} 1px, transparent 1px), linear-gradient(to right, ${gridColor} 1px, transparent 1px)`,
        backgroundSize: `${gridSize}px ${gridSize}px`
      }
    }
  );
}

export { GridBackground as default };
