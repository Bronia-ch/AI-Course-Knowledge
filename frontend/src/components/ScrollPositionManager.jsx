import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { useLocation } from "react-router-dom";

const STORAGE_PREFIX = "page-scroll-position:";
const RESTORE_RETRY_DELAY = 100;
const MAX_RESTORE_ATTEMPTS = 50;

function readScrollPosition(storageKey) {
  try {
    const value = window.sessionStorage.getItem(storageKey);
    const position = Number(value);
    return value !== null && Number.isFinite(position) && position >= 0
      ? position
      : 0;
  } catch {
    return 0;
  }
}

function saveScrollPosition(storageKey, position = window.scrollY) {
  try {
    window.sessionStorage.setItem(storageKey, String(position));
  } catch {
    // 浏览器禁用会话存储时，页面仍可正常使用，只是不记忆滚动位置。
  }
}

/**
 * 为所有路由页面保存并恢复滚动位置。
 */
export default function ScrollPositionManager() {
  const location = useLocation();
  const latestPositionRef = useRef(0);
  const storageKey = useMemo(
    () => `${STORAGE_PREFIX}${location.pathname}${location.search}`,
    [location.pathname, location.search],
  );

  useEffect(() => {
    if (!("scrollRestoration" in window.history)) return undefined;

    const previousMode = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";

    return () => {
      window.history.scrollRestoration = previousMode;
    };
  }, []);

  useEffect(() => {
    let saveFrameId = null;

    latestPositionRef.current = window.scrollY;

    const flushPosition = () => {
      saveFrameId = null;
      saveScrollPosition(storageKey, latestPositionRef.current);
    };

    const handleScroll = () => {
      latestPositionRef.current = window.scrollY;
      if (saveFrameId === null) {
        saveFrameId = window.requestAnimationFrame(flushPosition);
      }
    };

    const handlePageHide = () =>
      saveScrollPosition(storageKey, latestPositionRef.current);

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("pagehide", handlePageHide);

      if (saveFrameId !== null) {
        window.cancelAnimationFrame(saveFrameId);
        flushPosition();
      } else {
        saveScrollPosition(storageKey, latestPositionRef.current);
      }
    };
  }, [storageKey]);

  useLayoutEffect(() => {
    const targetPosition = readScrollPosition(storageKey);
    let attemptCount = 0;
    let restoreTimerId = null;
    let restoreFrameId = null;
    let cancelled = false;
    let resizeObserver = null;

    const stopRestore = () => {
      cancelled = true;
      if (restoreTimerId !== null) {
        window.clearTimeout(restoreTimerId);
      }
      if (restoreFrameId !== null) {
        window.cancelAnimationFrame(restoreFrameId);
      }
      resizeObserver?.disconnect();
    };

    const attemptRestore = () => {
      if (cancelled) return;

      attemptCount += 1;
      window.scrollTo({ top: targetPosition, left: 0, behavior: "auto" });

      const restored = Math.abs(window.scrollY - targetPosition) <= 1;
      if (!restored && attemptCount < MAX_RESTORE_ATTEMPTS) {
        restoreTimerId = window.setTimeout(
          attemptRestore,
          RESTORE_RETRY_DELAY,
        );
      }
    };

    const queueRestore = () => {
      if (
        cancelled ||
        restoreFrameId !== null ||
        attemptCount >= MAX_RESTORE_ATTEMPTS
      ) {
        return;
      }
      restoreFrameId = window.requestAnimationFrame(() => {
        restoreFrameId = null;
        attemptRestore();
      });
    };

    const cancelOnUserAction = () => stopRestore();
    window.addEventListener("wheel", cancelOnUserAction, { passive: true });
    window.addEventListener("touchstart", cancelOnUserAction, { passive: true });
    window.addEventListener("pointerdown", cancelOnUserAction, {
      passive: true,
    });

    if (typeof ResizeObserver !== "undefined" && targetPosition > 0) {
      resizeObserver = new ResizeObserver(queueRestore);
      resizeObserver.observe(document.documentElement);
    }

    queueRestore();

    return () => {
      stopRestore();
      window.removeEventListener("wheel", cancelOnUserAction);
      window.removeEventListener("touchstart", cancelOnUserAction);
      window.removeEventListener("pointerdown", cancelOnUserAction);
    };
  }, [storageKey]);

  return null;
}
