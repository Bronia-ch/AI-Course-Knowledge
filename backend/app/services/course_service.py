"""
业务逻辑层 — Course / Chapter / Lesson CRUD

所有函数接受 db: Session 作为第一个参数（由 FastAPI Depends 注入），
保持纯函数风格，不持有状态。

查询模式：
  列表查询返回 List[Model]
  详情查询返回 Model | None
  树查询使用 selectinload 预加载嵌套关系，避免 N+1 问题
"""

from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from ..models.models import Course, Chapter, Lesson, LessonProgress
from ..schemas.course import (
    CourseCreate,
    CourseUpdate,
    ChapterCreate,
    ChapterUpdate,
    LessonCreate,
    LessonUpdate,
)

LESSON_SUMMARY_RELATIONSHIPS = (
    Lesson.transcripts,
    Lesson.knowledge_points,
    Lesson.projects,
)


def _lesson_summary_options():
    """课节列表统计字段需要的关联加载配置。"""
    return tuple(
        selectinload(relationship)
        for relationship in LESSON_SUMMARY_RELATIONSHIPS
    )


def _chapter_lesson_summary_options():
    """章节详情中课节统计字段需要的关联加载配置。"""
    return tuple(
        selectinload(Chapter.lessons).selectinload(relationship)
        for relationship in LESSON_SUMMARY_RELATIONSHIPS
    )


def _course_tree_summary_options():
    """课程树中课节统计字段需要的关联加载配置。"""
    return tuple(
        selectinload(Course.chapters)
        .selectinload(Chapter.lessons)
        .selectinload(relationship)
        for relationship in LESSON_SUMMARY_RELATIONSHIPS
    )


# =============================================================================
# Course CRUD
# =============================================================================
def get_courses(db: Session) -> list[Course]:
    """获取所有课程，按创建时间倒序"""
    return db.query(Course).order_by(Course.created_at.desc()).all()


def _get_learning_status(
    total_lessons: int,
    started_lessons: int,
    completed_lessons: int,
) -> str:
    """根据课节汇总数据判定课程学习状态。"""
    if total_lessons > 0 and completed_lessons == total_lessons:
        return "completed"
    if started_lessons > 0:
        return "in_progress"
    return "not_started"


def get_courses_with_progress(db: Session) -> list[dict]:
    """获取课程列表及学习进度汇总，未开始课节按 0% 计算。"""
    progress_percent = func.coalesce(LessonProgress.progress_percent, 0.0)
    rows = (
        db.query(
            Course,
            func.count(Lesson.id).label("total_lessons"),
            func.sum(
                case((LessonProgress.id.is_not(None), 1), else_=0)
            ).label("started_lessons"),
            func.sum(
                case((LessonProgress.progress_percent >= 100, 1), else_=0)
            ).label("completed_lessons"),
            func.coalesce(func.avg(progress_percent), 0.0).label(
                "progress_percent"
            ),
            func.max(LessonProgress.updated_at).label("last_studied_at"),
        )
        .outerjoin(Chapter, Chapter.course_id == Course.id)
        .outerjoin(Lesson, Lesson.chapter_id == Chapter.id)
        .outerjoin(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
        .all()
    )

    # 一次性查询所有课程的学习记录，按更新时间倒序取每门课程第一条。
    recent_rows = (
        db.query(
            Course.id.label("course_id"),
            Lesson.id.label("lesson_id"),
            Lesson.title.label("lesson_title"),
            LessonProgress.current_time.label("current_time"),
            LessonProgress.updated_at.label("updated_at"),
        )
        .join(Chapter, Chapter.course_id == Course.id)
        .join(Lesson, Lesson.chapter_id == Chapter.id)
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .order_by(Course.id, LessonProgress.updated_at.desc())
        .all()
    )
    recent_by_course = {}
    for recent_row in recent_rows:
        recent_by_course.setdefault(recent_row.course_id, recent_row)

    result = []
    for row in rows:
        percent = min(max(float(row.progress_percent or 0), 0), 100)
        total_lessons = int(row.total_lessons or 0)
        started_lessons = int(row.started_lessons or 0)
        completed_lessons = int(row.completed_lessons or 0)
        learning_status = _get_learning_status(
            total_lessons,
            started_lessons,
            completed_lessons,
        )
        recent = recent_by_course.get(row.Course.id)
        result.append({
            "id": row.Course.id,
            "title": row.Course.title,
            "description": row.Course.description,
            "created_at": row.Course.created_at,
            "total_lessons": total_lessons,
            "started_lessons": started_lessons,
            "completed_lessons": completed_lessons,
            "progress_percent": round(percent, 1),
            "learning_status": learning_status,
            "last_studied_at": row.last_studied_at,
            "last_lesson_id": recent.lesson_id if recent else None,
            "last_lesson_title": recent.lesson_title if recent else None,
            "last_lesson_current_time": float(recent.current_time or 0)
            if recent
            else 0.0,
        })
    return result


def get_course(db: Session, course_id: int) -> Course | None:
    """获取单个课程（不含嵌套关系）"""
    return db.query(Course).filter(Course.id == course_id).first()


def get_course_with_chapters(db: Session, course_id: int) -> Course | None:
    """获取课程详情（含章节列表，章节按 order_index 排序）"""
    return (
        db.query(Course)
        .filter(Course.id == course_id)
        .options(selectinload(Course.chapters))
        .first()
    )


def get_course_tree(db: Session, course_id: int) -> Course | None:
    """
    获取课程完整树（课程 → 章节 → 课节）
    使用两层 selectinload 避免 N+1 查询：
    - 第一层：Course 预加载所有 Chapter
    - 第二层：每个 Chapter 预加载所有 Lesson
    """
    return (
        db.query(Course)
        .filter(Course.id == course_id)
        .options(*_course_tree_summary_options())
        .first()
    )


def create_course(db: Session, data: CourseCreate) -> Course:
    """创建新课程"""
    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: int, data: CourseUpdate) -> Course | None:
    """更新课程（只更新传入的字段）"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None
    # model_dump(exclude_unset=True) 只取客户端实际传入的字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, course_id: int) -> bool:
    """删除课程（级联删除关联章节和课节）"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return False
    db.delete(course)
    db.commit()
    return True


# =============================================================================
# Chapter CRUD
# =============================================================================
def get_chapters_by_course(db: Session, course_id: int) -> list[Chapter]:
    """获取某课程下的所有章节，按 order_index 升序排列"""
    return (
        db.query(Chapter)
        .filter(Chapter.course_id == course_id)
        .order_by(Chapter.order_index.asc())
        .all()
    )


def get_chapter(db: Session, chapter_id: int) -> Chapter | None:
    """获取单个章节（不含嵌套关系）"""
    return db.query(Chapter).filter(Chapter.id == chapter_id).first()


def get_chapter_with_lessons(db: Session, chapter_id: int) -> Chapter | None:
    """获取章节详情（含课节列表）"""
    return (
        db.query(Chapter)
        .filter(Chapter.id == chapter_id)
        .options(*_chapter_lesson_summary_options())
        .first()
    )


def create_chapter(db: Session, data: ChapterCreate) -> Chapter:
    """创建新章节"""
    chapter = Chapter(**data.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def update_chapter(db: Session, chapter_id: int, data: ChapterUpdate) -> Chapter | None:
    """更新章节标题和/或排序"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(chapter, key, value)
    db.commit()
    db.refresh(chapter)
    return chapter


def delete_chapter(db: Session, chapter_id: int) -> bool:
    """删除章节（级联删除关联课节）"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        return False
    db.delete(chapter)
    db.commit()
    return True


# =============================================================================
# Lesson CRUD
# =============================================================================
def get_lessons_by_chapter(db: Session, chapter_id: int) -> list[Lesson]:
    """获取某章节下的所有课节，按创建时间排序"""
    return (
        db.query(Lesson)
        .filter(Lesson.chapter_id == chapter_id)
        .options(*_lesson_summary_options())
        .order_by(Lesson.created_at.asc())
        .all()
    )


def get_lesson(db: Session, lesson_id: int) -> Lesson | None:
    """获取单个课节"""
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()


def create_lesson(db: Session, data: LessonCreate) -> Lesson:
    """创建新课节"""
    lesson = Lesson(**data.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def update_lesson(db: Session, lesson_id: int, data: LessonUpdate) -> Lesson | None:
    """更新课节（可用于更新 status 字段）"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lesson, key, value)
    db.commit()
    db.refresh(lesson)
    return lesson


def delete_lesson(db: Session, lesson_id: int) -> bool:
    """删除课节（同时清理关联的音频文件）"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        return False

    # 先清理磁盘上的音频文件
    from . import upload_service
    upload_service.delete_lesson_audio_folder(lesson_id)

    db.delete(lesson)
    db.commit()
    return True
