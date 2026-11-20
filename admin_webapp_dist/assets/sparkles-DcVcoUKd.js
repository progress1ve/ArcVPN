import { r as reactExports, j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { d as clampNumber, s as sanitizeColor } from './index-D4UN33jT.js';
import { a as useAnimationLoop, g as getMobileDpr } from './useAnimationLoop-BFrqRpQz.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-motion-BnKR5j6s.js';
import './vendor-recharts-BDHDAAEe.js';

function hexToRgb(hex) {
  hex = hex.replace("#", "");
  if (hex.length === 3)
    hex = hex.split("").map((c) => c + c).join("");
  return {
    r: parseInt(hex.substring(0, 2), 16),
    g: parseInt(hex.substring(2, 4), 16),
    b: parseInt(hex.substring(4, 6), 16)
  };
}
function Sparkles({ settings }) {
  const canvasRef = reactExports.useRef(null);
  const stateRef = reactExports.useRef(null);
  const particleDensity = clampNumber(settings.particleDensity, 50, 5e3, 800);
  const minSize = clampNumber(settings.minSize, 0.1, 5, 0.4);
  const maxSize = clampNumber(settings.maxSize, 0.5, 10, 1.4);
  const speed = clampNumber(settings.speed, 0.1, 10, 2);
  const particleColor = sanitizeColor(settings.particleColor, "#FFFFFF");
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
    const area = w * h;
    const count = Math.floor(area / 1e6 * particleDensity);
    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      size: minSize + Math.random() * (maxSize - minSize),
      speedX: (Math.random() - 0.5) * speed * 0.2,
      speedY: (Math.random() - 0.5) * speed * 0.2,
      opacity: Math.random(),
      opacityDirection: Math.random() > 0.5 ? 1 : -1,
      opacitySpeed: 5e-3 + Math.random() * 0.01 * speed
    }));
    stateRef.current = { ctx, particles, rgb: hexToRgb(particleColor), w, h, dpr };
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
  }, [particleDensity, minSize, maxSize, speed, particleColor]);
  useAnimationLoop(() => {
    const state = stateRef.current;
    if (!state) return;
    const { ctx, particles, rgb, w, h } = state;
    ctx.clearRect(0, 0, w, h);
    for (const p of particles) {
      p.x += p.speedX;
      p.y += p.speedY;
      p.opacity += p.opacityDirection * p.opacitySpeed;
      if (p.opacity <= 0) {
        p.opacity = 0;
        p.opacityDirection = 1;
      } else if (p.opacity >= 1) {
        p.opacity = 1;
        p.opacityDirection = -1;
      }
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${p.opacity})`;
      ctx.fill();
    }
  }, [particleDensity, minSize, maxSize, speed, particleColor]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("canvas", { ref: canvasRef, className: "absolute inset-0 h-full w-full" });
}

export { Sparkles as default };
