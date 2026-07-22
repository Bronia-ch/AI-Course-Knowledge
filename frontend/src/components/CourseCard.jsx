import { useNavigate } from "react-router-dom";

function formatPlaybackTime(seconds) {
  const safeSeconds = Math.max(Math.floor(seconds || 0), 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

const learningStatusLabels = {
  not_started: "尚未开始",
  in_progress: "学习中",
  completed: "已完成",
};

/**
 * 课程卡片
 */
export default function CourseCard({ course, onEdit, onDelete }) {
  const nav = useNavigate();
  const progress = Math.min(Math.max(course.progress_percent || 0, 0), 100);
  const isCompleted = course.learning_status === "completed";

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

      <div className={`course-learning-status ${course.learning_status}`}>
        {learningStatusLabels[course.learning_status] || "尚未开始"}
      </div>

      <div className="course-progress-header">
        <span>学习进度</span>
        <strong>{progress.toFixed(1)}%</strong>
      </div>
      <div className="course-progress-track">
        <div
          className={`course-progress-fill${isCompleted ? " completed" : ""}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="course-progress-meta">
        <span>
          {course.total_lessons > 0
            ? `已完成 ${course.completed_lessons}/${course.total_lessons} 课节`
            : "暂无课节"}
        </span>
        {course.last_studied_at && (
          <span>
            最近学习 {new Date(course.last_studied_at).toLocaleDateString("zh-CN")}
          </span>
        )}
      </div>

      {course.last_lesson_id ? (
        <div className="recent-learning">
          <div className="recent-learning-position">
            <span>最近学到</span>
            <strong title={course.last_lesson_title}>
              「{course.last_lesson_title}」 {formatPlaybackTime(course.last_lesson_current_time)}
            </strong>
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              nav(`/lessons/${course.last_lesson_id}`);
            }}
          >
            继续学习
          </button>
        </div>
      ) : (
        <div className="recent-learning-empty">尚未开始学习</div>
      )}

      <div style={{ fontSize: "0.75rem", color: "#aaa", marginTop: 10 }}>
        {new Date(course.created_at).toLocaleDateString("zh-CN")}
        {` · 已开始 ${course.started_lessons}/${course.total_lessons} 课节`}
      </div>
    </div>
  );
}
