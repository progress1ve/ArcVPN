import { r as reactExports, j as jsxRuntimeExports } from './vendor-react-CZvSMMDv.js';
import { s as sanitizeColor, c as cn } from './index-D4UN33jT.js';
import { u as useAnimationPause } from './useAnimationLoop-BFrqRpQz.js';
import { m as motion, A as AnimatePresence } from './vendor-motion-BnKR5j6s.js';
import './vendor-i18n-j3Ir5l49.js';
import './vendor-query-Cwz0p0Au.js';
import './vendor-twemoji-38-gQyZv.js';
import './vendor-telegram-CFPGJijG.js';
import './vendor-utils-grxZi5Wh.js';
import './vendor-radix-_4PhBHDS.js';
import './vendor-recharts-BDHDAAEe.js';

const BEAMS = [
  { initialX: 10, translateX: 10, duration: 7, repeatDelay: 3, delay: 2 },
  { initialX: 600, translateX: 600, duration: 3, repeatDelay: 3, delay: 4 },
  { initialX: 100, translateX: 100, duration: 7, repeatDelay: 7, className: "h-6" },
  { initialX: 400, translateX: 400, duration: 5, repeatDelay: 14, delay: 4 },
  { initialX: 800, translateX: 800, duration: 11, repeatDelay: 2, className: "h-20" },
  { initialX: 1e3, translateX: 1e3, duration: 4, repeatDelay: 2, className: "h-12" },
  { initialX: 1200, translateX: 1200, duration: 6, repeatDelay: 4, delay: 2, className: "h-6" }
];
function Explosion({
  beamColor,
  explosionColor,
  ...props
}) {
  const spans = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    directionX: Math.floor(Math.random() * 80 - 40),
    directionY: Math.floor(Math.random() * -50 - 10)
  }));
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ...props, className: cn("absolute z-50 h-2 w-2", props.className), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 1.5, ease: "easeOut" },
        className: "absolute -inset-x-10 top-0 m-auto h-2 w-10 rounded-full blur-sm",
        style: {
          background: `linear-gradient(to right, transparent, ${explosionColor}, transparent)`
        }
      }
    ),
    spans.map((span) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.span,
      {
        initial: { x: 0, y: 0, opacity: 1 },
        animate: { x: span.directionX, y: span.directionY, opacity: 0 },
        transition: { duration: Math.random() * 1.5 + 0.5, ease: "easeOut" },
        className: "absolute h-1 w-1 rounded-full",
        style: {
          background: `linear-gradient(to bottom, ${beamColor}, ${explosionColor})`
        }
      },
      span.id
    ))
  ] });
}
function CollisionMechanism({
  containerRef,
  parentRef,
  beamOptions,
  beamColor,
  explosionColor
}) {
  const beamRef = reactExports.useRef(null);
  const [collision, setCollision] = reactExports.useState({ detected: false, coordinates: null });
  const [beamKey, setBeamKey] = reactExports.useState(0);
  const [cycleCollisionDetected, setCycleCollisionDetected] = reactExports.useState(false);
  const checkRef = reactExports.useRef({ cycleDetected: false });
  checkRef.current.cycleDetected = cycleCollisionDetected;
  const checkCollision = reactExports.useCallback(() => {
    if (checkRef.current.cycleDetected) return;
    if (!beamRef.current || !containerRef.current || !parentRef.current) return;
    const beamRect = beamRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();
    const parentRect = parentRef.current.getBoundingClientRect();
    if (beamRect.bottom >= containerRect.top) {
      const relativeX = beamRect.left - parentRect.left + beamRect.width / 2;
      const relativeY = beamRect.bottom - parentRect.top;
      setCollision({ detected: true, coordinates: { x: relativeX, y: relativeY } });
      setCycleCollisionDetected(true);
    }
  }, [containerRef, parentRef]);
  reactExports.useEffect(() => {
    let animId = 0;
    let lastCheck = 0;
    const CHECK_INTERVAL = 100;
    const loop = (time) => {
      if (time - lastCheck >= CHECK_INTERVAL) {
        lastCheck = time;
        checkCollision();
      }
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);
    return () => {
      if (animId) cancelAnimationFrame(animId);
    };
  }, [checkCollision]);
  reactExports.useEffect(() => {
    if (!collision.detected || !collision.coordinates) return;
    const timer = setTimeout(() => {
      setCollision({ detected: false, coordinates: null });
      setCycleCollisionDetected(false);
      setBeamKey((prev) => prev + 1);
    }, 2e3);
    return () => clearTimeout(timer);
  }, [collision.detected, collision.coordinates]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      motion.div,
      {
        ref: beamRef,
        animate: "animate",
        initial: {
          translateY: "-200px",
          translateX: `${beamOptions.initialX}px`,
          rotate: 0
        },
        variants: {
          animate: {
            translateY: "1800px",
            translateX: `${beamOptions.translateX}px`,
            rotate: 0
          }
        },
        transition: {
          duration: beamOptions.duration,
          repeat: Infinity,
          repeatType: "loop",
          ease: "linear",
          delay: beamOptions.delay ?? 0,
          repeatDelay: beamOptions.repeatDelay
        },
        className: cn(
          "absolute left-0 top-20 m-auto h-14 w-px rounded-full",
          beamOptions.className
        ),
        style: {
          background: `linear-gradient(to top, ${beamColor}, ${explosionColor}, transparent)`
        }
      },
      beamKey
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(AnimatePresence, { children: collision.detected && collision.coordinates && /* @__PURE__ */ jsxRuntimeExports.jsx(
      Explosion,
      {
        beamColor,
        explosionColor,
        style: {
          left: `${collision.coordinates.x}px`,
          top: `${collision.coordinates.y}px`,
          transform: "translate(-50%, -50%)"
        }
      },
      `${collision.coordinates.x}-${collision.coordinates.y}`
    ) })
  ] });
}
function BackgroundBeamsCollision({ settings }) {
  const containerRef = reactExports.useRef(null);
  const parentRef = reactExports.useRef(null);
  const paused = useAnimationPause();
  const beamColor = sanitizeColor(settings.beamColor, "#6366f1");
  const explosionColor = sanitizeColor(settings.explosionColor, "#a855f7");
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: parentRef, className: "absolute inset-0 overflow-hidden", children: [
    !paused && BEAMS.map((beam) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      CollisionMechanism,
      {
        beamOptions: beam,
        containerRef,
        parentRef,
        beamColor,
        explosionColor
      },
      `${beam.initialX}-beam`
    )),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        ref: containerRef,
        className: "pointer-events-none absolute inset-x-0 bottom-0 w-full",
        style: {
          boxShadow: "0 0 24px rgba(34, 42, 53, 0.06), 0 1px 1px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(34, 42, 53, 0.04), 0 0 4px rgba(34, 42, 53, 0.08), 0 16px 68px rgba(47, 48, 55, 0.05), 0 1px 0 rgba(255, 255, 255, 0.1) inset"
        }
      }
    )
  ] });
}

export { BackgroundBeamsCollision as default };
