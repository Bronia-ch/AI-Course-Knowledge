"""
Lesson 路由 — 课节 CRUD + 状态更新

端点：
  GET    /api/lessons?chapter_id=  — 某章节下课节列表
  GET    /api/lessons/{id}          — 课节详情
  POST   /api/lessons               — 创建课节
  PUT    /api/lessons/{id}          — 更新课节（含 status）
  DELETE /api/lessons/{id}          — 删除课节
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.course import LessonCreate, LessonUpdate, LessonResponse
from ..services import course_service

router = APIRouter(prefix="/api/lessons", tags=["课节管理"])


@router.get("", response_model=list[LessonResponse])
def list_lessons(
    chapter_id: int = Query(..., description="章节ID"),
    db: Session = Depends(get_db),
):
    """获取指定章节下的所有课节"""
    return course_service.get_lessons_by_chapter(db, chapter_id)


@router.get("/{lesson_id}", response_model=LessonResponse)
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """获取课节详情"""
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")
    return lesson


@router.post("", response_model=LessonResponse, status_code=201)
def create_lesson(data: LessonCreate, db: Session = Depends(get_db)):
    """创建新课节"""
    return course_service.create_lesson(db, data)


@router.put("/{lesson_id}", response_model=LessonResponse)
def update_lesson(lesson_id: int, data: LessonUpdate, db: Session = Depends(get_db)):
    """
    更新课节（支持修改 status 字段）

    status 可选值: pending / processing / completed
    """
    lesson = course_service.update_lesson(db, lesson_id, data)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")
    return lesson


@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """删除课节"""
    success = course_service.delete_lesson(db, lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="课节不存在")
