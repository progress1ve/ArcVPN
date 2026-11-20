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

function FirefliesBackground({ settings }) {
  const canvasRef = reactExports.useRef(null);
  const stateRef = reactExports.useRef(null);
  const color = sanitizeColor(settings.color, "#ffd166");
  const count = clampNumber(settings.count, 5, 200, 40);
  const speed = clampNumber(settings.speed, 0.1, 3, 1);
  const size = clampNumber(settings.size, 0.5, 6, 2);
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
    const fireflies = Array.from({ length: Math.floor(count) }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.6,
      vy: (Math.random() - 0.5) * 0.6,
      radius: 0.5 + Math.random() * 0.5,
      phase: Math.random() * Math.PI * 2,
      pulseSpeed: 0.5 + Math.random() * 1.5
    }));
    stateRef.current = { ctx, fireflies, w, h, dpr };
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
  }, [count]);
  useAnimationLoop(
    (time) => {
      const state = stateRef.current;
      if (!state) return;
      const { ctx, fireflies, w, h } = state;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = color;
      for (const f of fireflies) {
        f.x += f.vx * speed + Math.sin(time / 2e3 + f.phase) * 0.3 * speed;
        f.y += f.vy * speed + Math.cos(time / 2400 + f.phase) * 0.2 * speed;
        if (f.x < -20) f.x = w + 20;
        if (f.x > w + 20) f.x = -20;
        if (f.y < -20) f.y = h + 20;
        if (f.y > h + 20) f.y = -20;
        const pulse = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(time / 1e3 * f.pulseSpeed + f.phase));
        const radius = f.radius * size;
        ctx.globalAlpha = pulse * 0.25;
        ctx.beginPath();
        ctx.arc(f.x, f.y, radius * 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = pulse;
        ctx.beginPath();
        ctx.arc(f.x, f.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    },
    [color, count, speed, size]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx("canvas", { ref: canvasRef, className: "absolute inset-0 h-full w-full" });
}

export { FirefliesBackground as default };
