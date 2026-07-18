import { useState } from "react";
import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge";

/**
 * 章节项 — 包含章节标题、排序按钮、课节列表
 */
export default function ChapterItem({
  chapter,
  lessons = [],
  onEdit,
  onDelete,
  onMoveUp,
  onMoveDown,
  onAddLesson,
  onEditLesson,
  onDeleteLesson,
}) {
  const [expanded, setExpanded] = useState(true);
  const nav = useNavigate();

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      {/* 章节头部 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: "#999", fontSize: "0.8rem" }}>
            {expanded ? "▾" : "▸"}
          </span>
          <strong>{chapter.title}</strong>
          <span style={{ fontSize: "0.75rem", color: "#aaa" }}>
            ({lessons.length} 课节)
          </span>
        </div>
        <div
          style={{ display: "flex", gap: 4 }}
          onClick={(e) => e.stopPropagation()}
        >
          {onMoveUp && (
            <button className="btn btn-secondary btn-sm" onClick={onMoveUp}>
              ↑
            </button>
          )}
          {onMoveDown && (
            <button className="btn btn-secondary btn-sm" onClick={onMoveDown}>
              ↓
            </button>
          )}
          <button className="btn btn-secondary btn-sm" onClick={onEdit}>
            编辑
          </button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}>
            删除
          </button>
        </div>
      </div>

      {/* 展开的课节列表 */}
      {expanded && (
        <div style={{ marginTop: 12, paddingLeft: 20, borderLeft: "2px solid #f0f0f0" }}>
          {lessons.map((lesson) => (
            <div
              key={lesson.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 0",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
                onClick={() => nav(`/lessons/${lesson.id}`)}
              >
                <span style={{ fontSize: "0.9rem" }}>{lesson.title}</span>
                <StatusBadge status={lesson.status} />
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onEditLesson?.(lesson)}
                >
                  编辑
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => onDeleteLesson?.(lesson)}
                >
                  删除
                </button>
              </div>
            </div>
          ))}

          {/* 添加课节按钮 */}
          <button
            className="btn btn-secondary btn-sm"
            style={{ marginTop: 8 }}
            onClick={() => onAddLesson?.()}
          >
            + 添加课节
          </button>
        </div>
      )}
    </div>
  );
}
