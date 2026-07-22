import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { courseAPI, chapterAPI, lessonAPI } from "../services/api";
import Breadcrumb from "../components/Breadcrumb";
import ChapterItem from "../components/ChapterItem";
import Modal from "../components/Modal";

/**
 * 课程详情页 — 章节和课节管理
 */
export default function CourseDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [course, setCourse] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [lessonsMap, setLessonsMap] = useState({}); // { chapterId: [lessons] }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 弹窗
  const [showCourseForm, setShowCourseForm] = useState(false);
  const [courseForm, setCourseForm] = useState({ title: "", description: "" });

  const [showChapterForm, setShowChapterForm] = useState(false);
  const [editingChapter, setEditingChapter] = useState(null);
  const [chapterForm, setChapterForm] = useState({ title: "", order_index: 0 });

  const [showLessonForm, setShowLessonForm] = useState(false);
  const [lessonChapterId, setLessonChapterId] = useState(null);
  const [editingLesson, setEditingLesson] = useState(null);
  const [lessonForm, setLessonForm] = useState({ title: "", description: "" });

  // 加载全部数据
  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const c = await courseAPI.getTree(Number(id));
      setCourse(c);
      setCourseForm({ title: c.title, description: c.description || "" });

      const chs = c.chapters || [];
      setChapters(chs);
      setLessonsMap(
        Object.fromEntries(
          chs.map((chapter) => [
            chapter.id,
            [...(chapter.lessons || [])].sort((first, second) =>
              first.created_at === second.created_at
                ? first.id - second.id
                : first.created_at.localeCompare(second.created_at),
            ),
          ]),
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ===== 课程操作 =====
  const handleUpdateCourse = async (e) => {
    e.preventDefault();
    try {
      await courseAPI.update(Number(id), courseForm);
      setShowCourseForm(false);
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeleteCourse = async () => {
    if (!window.confirm(`确定删除课程「${course?.title}」？`)) return;
    try {
      await courseAPI.delete(Number(id));
      nav("/");
    } catch (err) {
      alert(err.message);
    }
  };

  // ===== 章节操作 =====
  const openChapterCreate = () => {
    setEditingChapter(null);
    setChapterForm({ title: "", order_index: chapters.length });
    setShowChapterForm(true);
  };

  const openChapterEdit = (ch) => {
    setEditingChapter(ch);
    setChapterForm({ title: ch.title, order_index: ch.order_index });
    setShowChapterForm(true);
  };

  const handleChapterSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingChapter) {
        await chapterAPI.update(editingChapter.id, chapterForm);
      } else {
        await chapterAPI.create({ ...chapterForm, course_id: Number(id) });
      }
      setShowChapterForm(false);
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleChapterDelete = async (ch) => {
    if (!window.confirm(`确定删除章节「${ch.title}」？`)) return;
    try {
      await chapterAPI.delete(ch.id);
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleChapterMove = async (ch, direction) => {
    const idx = chapters.findIndex((c) => c.id === ch.id);
    if (idx < 0) return;
    const swapIdx = idx + direction;
    if (swapIdx < 0 || swapIdx >= chapters.length) return;

    const other = chapters[swapIdx];
    try {
      await chapterAPI.update(ch.id, { order_index: other.order_index });
      await chapterAPI.update(other.id, { order_index: ch.order_index });
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  // ===== 课节操作 =====
  const openLessonCreate = (chapterId) => {
    setLessonChapterId(chapterId);
    setEditingLesson(null);
    setLessonForm({ title: "", description: "" });
    setShowLessonForm(true);
  };

  const openLessonEdit = (lesson) => {
    setLessonChapterId(lesson.chapter_id);
    setEditingLesson(lesson);
    setLessonForm({ title: lesson.title, description: lesson.description || "" });
    setShowLessonForm(true);
  };

  const handleLessonSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingLesson) {
        await lessonAPI.update(editingLesson.id, lessonForm);
      } else {
        await lessonAPI.create({ ...lessonForm, chapter_id: lessonChapterId });
      }
      setShowLessonForm(false);
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleLessonDelete = async (lesson) => {
    if (!window.confirm(`确定删除课节「${lesson.title}」？`)) return;
    try {
      await lessonAPI.delete(lesson.id);
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!course) return <div className="error">课程不存在</div>;

  return (
    <div className="page">
      <Breadcrumb
        items={[
          { label: "课程列表", to: "/" },
          { label: course.title },
        ]}
      />

      {/* 课程头部 */}
      <div className="page-header">
        <div>
          <h1>{course.title}</h1>
          {course.description && (
            <p style={{ color: "#888", fontSize: "0.9rem", marginTop: 4 }}>
              {course.description}
            </p>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setShowCourseForm(true);
            }}
          >
            编辑课程
          </button>
          <button className="btn btn-danger" onClick={handleDeleteCourse}>
            删除课程
          </button>
        </div>
      </div>

      {/* 章节列表 */}
      <div className="page-header">
        <h2 style={{ fontSize: "1.1rem" }}>章节列表</h2>
        <button className="btn btn-primary btn-sm" onClick={openChapterCreate}>
          + 添加章节
        </button>
      </div>

      {chapters.length === 0 ? (
        <p style={{ color: "#aaa", textAlign: "center", padding: 24 }}>
          还没有章节，点击添加
        </p>
      ) : (
        chapters.map((ch, idx) => (
          <ChapterItem
            key={ch.id}
            chapter={ch}
            lessons={lessonsMap[ch.id] || []}
            onEdit={() => openChapterEdit(ch)}
            onDelete={() => handleChapterDelete(ch)}
            onMoveUp={idx > 0 ? () => handleChapterMove(ch, -1) : null}
            onMoveDown={
              idx < chapters.length - 1 ? () => handleChapterMove(ch, 1) : null
            }
            onAddLesson={() => openLessonCreate(ch.id)}
            onEditLesson={(l) => openLessonEdit(l)}
            onDeleteLesson={(l) => handleLessonDelete(l)}
          />
        ))
      )}

      {/* 编辑课程弹窗 */}
      <Modal
        open={showCourseForm}
        onClose={() => setShowCourseForm(false)}
        title="编辑课程"
      >
        <form onSubmit={handleUpdateCourse}>
          <div className="form-group">
            <label>课程标题 *</label>
            <input
              className="form-input"
              value={courseForm.title}
              onChange={(e) =>
                setCourseForm({ ...courseForm, title: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>课程描述</label>
            <textarea
              className="form-input"
              rows={3}
              value={courseForm.description}
              onChange={(e) =>
                setCourseForm({ ...courseForm, description: e.target.value })
              }
            />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowCourseForm(false)}
            >
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              保存
            </button>
          </div>
        </form>
      </Modal>

      {/* 章节弹窗 */}
      <Modal
        open={showChapterForm}
        onClose={() => setShowChapterForm(false)}
        title={editingChapter ? "编辑章节" : "添加章节"}
      >
        <form onSubmit={handleChapterSubmit}>
          <div className="form-group">
            <label>章节标题 *</label>
            <input
              className="form-input"
              value={chapterForm.title}
              onChange={(e) =>
                setChapterForm({ ...chapterForm, title: e.target.value })
              }
              autoFocus
            />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowChapterForm(false)}
            >
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              {editingChapter ? "保存" : "添加"}
            </button>
          </div>
        </form>
      </Modal>

      {/* 课节弹窗 */}
      <Modal
        open={showLessonForm}
        onClose={() => setShowLessonForm(false)}
        title={editingLesson ? "编辑课节" : "添加课节"}
      >
        <form onSubmit={handleLessonSubmit}>
          <div className="form-group">
            <label>课节标题 *</label>
            <input
              className="form-input"
              value={lessonForm.title}
              onChange={(e) =>
                setLessonForm({ ...lessonForm, title: e.target.value })
              }
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>课节描述</label>
            <textarea
              className="form-input"
              rows={2}
              value={lessonForm.description}
              onChange={(e) =>
                setLessonForm({ ...lessonForm, description: e.target.value })
              }
            />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowLessonForm(false)}
            >
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              {editingLesson ? "保存" : "添加"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
