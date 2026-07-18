import { useNavigate } from "react-router-dom";

/**
 * 课程卡片
 */
export default function CourseCard({ course, onEdit, onDelete }) {
  const nav = useNavigate();

  return (
    <div
      className="card"
      style={{ cursor: "pointer" }}
      onClick={() => nav(`/courses/${course.id}`)}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <h3 style={{ fontSize: "1.05rem", marginBottom: 8 }}>{course.title}</h3>
        <div style={{ display: "flex", gap: 4 }} onClick={(e) => e.stopPropagation()}>
          <button className="btn btn-secondary btn-sm" onClick={onEdit}>
            编辑
          </button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}>
            删除
          </button>
        </div>
      </div>
      {course.description && (
        <p
          style={{
            fontSize: "0.85rem",
            color: "#888",
            marginBottom: 8,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {course.description}
        </p>
      )}
      <div style={{ fontSize: "0.75rem", color: "#aaa" }}>
        {new Date(course.created_at).toLocaleDateString("zh-CN")}
        {course.chapters && ` · ${course.chapters.length} 个章节`}
      </div>
    </div>
  );
}
