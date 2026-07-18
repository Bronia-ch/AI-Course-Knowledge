"""
业务逻辑层 — Course / Chapter / Lesson CRUD

所有函数接受 db: Session 作为第一个参数（由 FastAPI Depends 注入），
保持纯函数风格，不持有状态。

查询模式：
  列表查询返回 List[Model]
  详情查询返回 Model | None
  树查询使用 selectinload 预加载嵌套关系，避免 N+1 问题
"""

from sqlalchemy.orm import Session, selectinload

from ..models.models import Course, Chapter, Lesson
from ..schemas.course import (
    CourseCreate,
    CourseUpdate,
    ChapterCreate,
    ChapterUpdate,
    LessonCreate,
    LessonUpdate,
)


# =============================================================================
# Course CRUD
# =============================================================================
def get_courses(db: Session) -> list[Course]:
    """获取所有课程，按创建时间倒序"""
    return db.query(Course).order_by(Course.created_at.desc()).all()


def get_course(db: Session, course_id: int) -> Course | None:
    """获取单个课程（不含嵌套关系）"""
    return db.query(Course).filter(Course.id == course_id).first()


def get_course_with_chapters(db: Session, course_id: int) -> Course | None:
    """获取课程详情（含章节列表，章节按 order_index 排序）"""
    return (
        db.query(Course)
        .filter(Course.id == course_id)
        .options(
            selectinload(Course.chapters).selectinload(Chapter.lessons)
        )
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
        .options(
            selectinload(Course.chapters)
            .selectinload(Chapter.lessons)
        )
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
        .options(selectinload(Chapter.lessons))
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
