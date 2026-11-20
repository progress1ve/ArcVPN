import { r as reactExports, j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { d as clampNumber, s as sanitizeColor } from './index-D4UN33jT.js';
import { u as useAnimationPause } from './useAnimationLoop-BFrqRpQz.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

function Meteors({ settings }) {
  const count = clampNumber(settings.count, 1, 50, 20);
  const meteorColor = sanitizeColor(settings.meteorColor, "#ffffff");
  const paused = useAnimationPause();
  const meteors = reactExports.useMemo(
    () => Array.from({ length: count }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      delay: `${Math.random() * 5}s`,
      duration: `${2 + Math.random() * 6}s`,
      size: `${1 + Math.random()}px`
    })),
    [count]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0 overflow-hidden", children: meteors.map((meteor) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    "span",
    {
      className: "absolute top-0 rotate-[215deg] animate-meteor-effect rounded-[9999px]",
      style: {
        left: meteor.left,
        animationDelay: meteor.delay,
        animationDuration: meteor.duration,
        animationPlayState: paused ? "paused" : "running",
        width: meteor.size,
        height: meteor.size,
        boxShadow: `0 0 0 1px ${meteorColor}0d, 0 0 2px 1px ${meteorColor}20, 0 0 20px 2px ${meteorColor}40`,
        background: meteorColor
      },
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: "pointer-events-none absolute top-1/2 -z-10 h-px w-[50px] -translate-y-1/2",
          style: {
            background: `linear-gradient(to right, ${meteorColor}, transparent)`
          }
        }
      )
    },
    meteor.id
  )) });
}

export { Meteors as default };
