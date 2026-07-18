/**
 * 状态标签 — 根据 status 显示不同颜色
 *
 * pending:    灰色（无音频）
 * uploaded:   蓝色（已上传）
 * processing: 橙色（转录中）
 * completed:  绿色（转录完）
 * analyzing:  橙色（分析中）
 * analyzed:   紫色（分析完）
 */

const STATUS_MAP = {
  pending: { label: "待上传", color: "#999", bg: "#f0f0f0" },
  uploaded: { label: "已上传", color: "#007aff", bg: "#e8f2ff" },
  processing: { label: "转录中", color: "#ff9500", bg: "#fff3e0" },
  completed: { label: "转录完成", color: "#34c759", bg: "#e8f8ed" },
  analyzing: { label: "分析中", color: "#ff9500", bg: "#fff3e0" },
  analyzed: { label: "已完成", color: "#667eea", bg: "#f0edff" },
};

export default function StatusBadge({ status }) {
  const info = STATUS_MAP[status] || STATUS_MAP.pending;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "10px",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: info.color,
        background: info.bg,
      }}
    >
      {info.label}
    </span>
  );
}
