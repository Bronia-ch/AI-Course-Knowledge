import { useEffect } from "react";

/**
 * 通用弹窗组件
 *
 * @param {boolean} open - 是否打开
 * @param {function} onClose - 关闭回调
 * @param {string} title - 弹窗标题
 * @param {ReactNode} children - 内容
 */
export default function Modal({ open, onClose, title, children }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          padding: 24,
          minWidth: 360,
          maxWidth: "90vw",
          boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginBottom: 16, fontSize: "1.1rem" }}>{title}</h2>
        {children}
      </div>
    </div>
  );
}
