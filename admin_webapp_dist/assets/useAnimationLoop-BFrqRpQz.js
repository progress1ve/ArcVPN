import { r as reactExports } from './vendor-react-CZvSMMDv.js';

const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
const TARGET_FPS = isMobile ? 30 : 60;
const FRAME_INTERVAL = 1e3 / TARGET_FPS;
function useAnimationLoop(callback, deps) {
  const callbackRef = reactExports.useRef(callback);
  callbackRef.current = callback;
  reactExports.useEffect(() => {
    let animId = 0;
    let lastTime = 0;
    let docHidden = document.hidden;
    let tgInactive = false;
    const isPaused = () => docHidden || tgInactive;
    const loop = (time) => {
      const delta = time - lastTime;
      if (delta >= FRAME_INTERVAL) {
        lastTime = time - delta % FRAME_INTERVAL;
        callbackRef.current(time, delta);
      }
      animId = requestAnimationFrame(loop);
    };
    const start = () => {
      if (animId) return;
      lastTime = performance.now();
      animId = requestAnimationFrame(loop);
    };
    const stop = () => {
      if (animId) {
        cancelAnimationFrame(animId);
        animId = 0;
      }
    };
    const onVisibilityChange = () => {
      docHidden = document.hidden;
      if (isPaused()) stop();
      else start();
    };
    const tg = window.Telegram?.WebApp;
    const onTgActivated = () => {
      tgInactive = false;
      if (!isPaused()) start();
    };
    const onTgDeactivated = () => {
      tgInactive = true;
      stop();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    if (tg) {
      tg.onEvent?.("activated", onTgActivated);
      tg.onEvent?.("deactivated", onTgDeactivated);
    }
    if (!isPaused()) start();
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      if (tg) {
        tg.offEvent?.("activated", onTgActivated);
        tg.offEvent?.("deactivated", onTgDeactivated);
      }
    };
  }, deps);
}
function useAnimationPause() {
  const [paused, setPaused] = reactExports.useState(
    () => typeof document !== "undefined" ? document.hidden : false
  );
  reactExports.useEffect(() => {
    let docHidden = document.hidden;
    let tgInactive = false;
    const update = () => setPaused(docHidden || tgInactive);
    const onVisibility = () => {
      docHidden = document.hidden;
      update();
    };
    const tg = window.Telegram?.WebApp;
    const onActivated = () => {
      tgInactive = false;
      update();
    };
    const onDeactivated = () => {
      tgInactive = true;
      update();
    };
    document.addEventListener("visibilitychange", onVisibility);
    if (tg) {
      tg.onEvent?.("activated", onActivated);
      tg.onEvent?.("deactivated", onDeactivated);
    }
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      if (tg) {
        tg.offEvent?.("activated", onActivated);
        tg.offEvent?.("deactivated", onDeactivated);
      }
    };
  }, []);
  return paused;
}
function getMobileDpr() {
  if (isMobile) return Math.min(devicePixelRatio, 1.5);
  return devicePixelRatio || 1;
}

export { useAnimationLoop as a, getMobileDpr as g, useAnimationPause as u };
