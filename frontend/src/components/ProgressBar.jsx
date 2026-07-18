/**
 * 进度条 — 显示 Lesson 处理进度
 *
 * pending → uploaded → processing → completed → analyzing → analyzed
 */
const STEPS = ["pending", "uploaded", "processing", "completed", "analyzing", "analyzed"];
const LABELS = ["待上传", "已上传", "转录中", "转录完成", "分析中", "已完成"];

export default function ProgressBar({ status }) {
  const currentIdx = STEPS.indexOf(status);
  const progress = currentIdx >= 0 ? currentIdx : 0;

  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
          fontSize: "0.75rem",
        }}
      >
        {LABELS.map((label, i) => (
          <span
            key={i}
            style={{
              color: i <= progress ? "#667eea" : "#ccc",
              fontWeight: i === progress ? 600 : 400,
            }}
          >
            {label}
          </span>
        ))}
      </div>
      <div
        style={{
          height: 6,
          background: "#eee",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(progress / (STEPS.length - 1)) * 100}%`,
            background: "linear-gradient(90deg, #667eea, #764ba2)",
            borderRadius: 3,
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}
