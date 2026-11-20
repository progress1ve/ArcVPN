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

function ShootingStarsBackground({ settings }) {
  const canvasRef = reactExports.useRef(null);
  const stateRef = reactExports.useRef(null);
  const starColor = sanitizeColor(settings.starColor, "#9E00FF");
  const trailColor = sanitizeColor(settings.trailColor, "#2EB9DF");
  const bgStarColor = sanitizeColor(settings.bgStarColor, "#ffffff");
  const starDensity = clampNumber(settings.starDensity, 1e-5, 1e-3, 15e-5);
  const minSpeed = clampNumber(settings.minSpeed, 1, 50, 10);
  const maxSpeed = clampNumber(settings.maxSpeed, 5, 100, 30);
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
    const count = Math.floor(w * h * starDensity);
    const bgStars = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      radius: Math.random() * 1.2 + 0.3,
      opacity: Math.random(),
      twinkleSpeed: Math.random() > 0.3 ? 0.5 + Math.random() * 0.5 : null
    }));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stateRef.current = {
      ctx,
      shootingStars: [],
      bgStars,
      lastShootingTime: 0,
      nextShootingDelay: 4200 + Math.random() * 4500,
      w,
      h,
      dpr
    };
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
  }, [starDensity]);
  useAnimationLoop(
    (time) => {
      const state = stateRef.current;
      if (!state) return;
      const { ctx, bgStars, w, h } = state;
      ctx.clearRect(0, 0, w, h);
      for (const s of bgStars) {
        let opacity = s.opacity;
        if (s.twinkleSpeed) {
          opacity = 0.5 + 0.5 * Math.sin(time / 1e3 * s.twinkleSpeed * Math.PI * 2);
        }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
        ctx.globalAlpha = opacity;
        ctx.fillStyle = bgStarColor;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (time - state.lastShootingTime > state.nextShootingDelay) {
        state.shootingStars.push({
          x: Math.random() * w,
          y: Math.random() * h * 0.5,
          angle: Math.PI / 4 + (Math.random() - 0.5) * 0.3,
          scale: 0.5 + Math.random() * 0.5,
          speed: minSpeed + Math.random() * (maxSpeed - minSpeed),
          distance: 0,
          opacity: 1
        });
        state.lastShootingTime = time;
        state.nextShootingDelay = 4200 + Math.random() * 4500;
      }
      state.shootingStars = state.shootingStars.filter((star) => {
        star.distance += star.speed;
        star.opacity = Math.max(0, 1 - star.distance / 500);
        if (star.opacity <= 0) return false;
        const x2 = star.x + Math.cos(star.angle) * star.distance;
        const y2 = star.y + Math.sin(star.angle) * star.distance;
        const tailX = star.x + Math.cos(star.angle) * Math.max(0, star.distance - 80);
        const tailY = star.y + Math.sin(star.angle) * Math.max(0, star.distance - 80);
        ctx.lineWidth = star.scale * 2;
        ctx.globalAlpha = star.opacity * 0.4;
        ctx.strokeStyle = trailColor;
        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        ctx.globalAlpha = star.opacity;
        ctx.fillStyle = starColor;
        ctx.beginPath();
        ctx.arc(x2, y2, star.scale * 1.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        return true;
      });
    },
    [starColor, trailColor, bgStarColor, starDensity, minSpeed, maxSpeed]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx("canvas", { ref: canvasRef, className: "absolute inset-0 h-full w-full" });
}

export { ShootingStarsBackground as default };
