import { r as reactExports, j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { s as sanitizeColor, d as clampNumber } from './index-D4UN33jT.js';
import { a as useAnimationLoop, g as getMobileDpr } from './useAnimationLoop-BFrqRpQz.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

function SnowfallBackground({ settings }) {
  const canvasRef = reactExports.useRef(null);
  const stateRef = reactExports.useRef(null);
  const color = sanitizeColor(settings.color, "#ffffff");
  const density = clampNumber(settings.density, 20, 400, 150);
  const speed = clampNumber(settings.speed, 0.1, 3, 1);
  const wind = clampNumber(settings.wind, -3, 3, 0.5);
  reactExports.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = getMobileDpr();
    const parent = canvas.parentElement;
    const w = parent?.offsetWidth ?? window.innerWidth;
    const h = parent?.offsetHeight ?? window.innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const flakes = Array.from({ length: Math.floor(density) }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      radius: 0.8 + Math.random() * 2.2,
      fallSpeed: 0.4 + Math.random() * 1.2,
      phase: Math.random() * Math.PI * 2,
      opacity: 0.3 + Math.random() * 0.7
    }));
    stateRef.current = { ctx, flakes, w, h, dpr };
    const onResize = () => {
      const nw = parent?.offsetWidth ?? window.innerWidth;
      const nh = parent?.offsetHeight ?? window.innerHeight;
      canvas.width = nw * dpr;
      canvas.height = nh * dpr;
      canvas.style.width = `${nw}px`;
      canvas.style.height = `${nh}px`;
      if (stateRef.current) {
        stateRef.current.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        stateRef.current.w = nw;
        stateRef.current.h = nh;
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [density]);
  useAnimationLoop(
    (time) => {
      const state = stateRef.current;
      if (!state) return;
      const { ctx, flakes, w, h } = state;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = color;
      for (const f of flakes) {
        f.y += f.fallSpeed * speed;
        f.x += wind * f.fallSpeed * 0.6 + Math.sin(time / 1800 + f.phase) * 0.4;
        if (f.y > h + 5) {
          f.y = -5;
          f.x = Math.random() * w;
        }
        if (f.x > w + 5) f.x = -5;
        if (f.x < -5) f.x = w + 5;
        ctx.globalAlpha = f.opacity;
        ctx.beginPath();
        ctx.arc(f.x, f.y, f.radius, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    },
    [color, density, speed, wind]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx("canvas", { ref: canvasRef, className: "absolute inset-0 h-full w-full" });
}

export { SnowfallBackground as default };
