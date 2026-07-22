import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { courseAPI } from "../services/api";
import CourseCard from "../components/CourseCard";
import LearningStats from "../components/LearningStats";
import Modal from "../components/Modal";
import "./CourseListPage.css";

/**
 * 课程列表首页
 */
export default function CourseListPage() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 弹窗状态
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null); // 正在编辑的课程
  const [form, setForm] = useState({ title: "", description: "" });

  const loadCourses = async () => {
    try {
      setLoading(true);
      const data = await courseAPI.list();
      setCourses(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
  }, []);

  // 打开创建弹窗
  const openCreate = () => {
    setEditing(null);
    setForm({ title: "", description: "" });
    setShowForm(true);
  };

  // 打开编辑弹窗
  const openEdit = (course) => {
    setEditing(course);
    setForm({ title: course.title, description: course.description || "" });
    setShowForm(true);
  };

  // 提交表单（创建或更新）
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    try {
      if (editing) {
        await courseAPI.update(editing.id, form);
      } else {
        await courseAPI.create(form);
      }
      setShowForm(false);
      await loadCourses();
    } catch (err) {
      alert(err.message);
    }
  };

  // 删除课程
  const handleDelete = async (course) => {
    if (!window.confirm(`确定删除课程「${course.title}」？\n删除后不可恢复。`)) return;
    try {
      await courseAPI.delete(course.id);
      await loadCourses();
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>AI课程知识库</h1>
          <p style={{ color: "#888", fontSize: "0.9rem" }}>管理你的AI学习旅程</p>
        </div>
        <div className="course-list-actions">
          <Link className="btn btn-secondary" to="/portfolio-projects">
            我的作品
          </Link>
          <button className="btn btn-primary" onClick={openCreate}>
            + 创建课程
          </button>
        </div>
      </div>

      <LearningStats courses={courses} />

      {courses.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60, color: "#aaa" }}>
          <p style={{ fontSize: "2rem", marginBottom: 8 }}>📚</p>
          <p>还没有课程，点击上方按钮创建第一个课程</p>
        </div>
      ) : (
        <div className="grid-3">
          {courses.map((c) => (
            <CourseCard
              key={c.id}
              course={c}
              onEdit={() => openEdit(c)}
              onDelete={() => handleDelete(c)}
            />
          ))}
        </div>
      )}

      {/* 创建/编辑弹窗 */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editing ? "编辑课程" : "创建课程"}
      >
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>课程标题 *</label>
            <input
              className="form-input"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="例如：深度学习入门"
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>课程描述</label>
            <textarea
              className="form-input"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="简单描述课程内容..."
            />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowForm(false)}
            >
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              {editing ? "保存" : "创建"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
