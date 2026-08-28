import { useEffect, useState } from "react";
import "./BackToTopButton.css";

/**
 * 页面右侧的通用返回顶部按钮。
 */
export default function BackToTopButton() {
  const [canScrollToTop, setCanScrollToTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => setCanScrollToTop(window.scrollY > 0);
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <button
      type="button"
      className="back-to-top"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      disabled={!canScrollToTop}
      aria-label={canScrollToTop ? "返回页面顶部" : "当前已在页面顶部"}
      title={canScrollToTop ? "返回顶部" : "当前已在顶部"}
    >
      <span className="back-to-top-icon" aria-hidden="true">↑</span>
      <span className="back-to-top-label">返回顶部</span>
    </button>
  );
}
