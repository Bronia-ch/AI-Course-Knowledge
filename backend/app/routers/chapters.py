"""
Chapter 路由 — 章节 CRUD + 排序更新

端点：
  GET    /api/chapters?course_id=  — 某课程下章节列表
  GET    /api/chapters/{id}         — 章节详情（含课节）
  POST   /api/chapters              — 创建章节
  PUT    /api/chapters/{id}         — 更新章节（标题/排序）
  DELETE /api/chapters/{id}         — 删除章节（级联删除课节）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.course import ChapterCreate, ChapterUpdate, ChapterResponse, ChapterDetail
from ..services import course_service

router = APIRouter(prefix="/api/chapters", tags=["章节管理"])


@router.get("", response_model=list[ChapterResponse])
def list_chapters(
    course_id: int = Query(..., description="课程ID"),
    db: Session = Depends(get_db),
):
    """获取指定课程下的所有章节（按 order_index 升序）"""
    return course_service.get_chapters_by_course(db, course_id)


@router.get("/{chapter_id}", response_model=ChapterDetail)
def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    """获取章节详情（含课节列表）"""
    chapter = course_service.get_chapter_with_lessons(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.post("", response_model=ChapterResponse, status_code=201)
def create_chapter(data: ChapterCreate, db: Session = Depends(get_db)):
    """创建新章节"""
    return course_service.create_chapter(db, data)


@router.put("/{chapter_id}", response_model=ChapterResponse)
def update_chapter(chapter_id: int, data: ChapterUpdate, db: Session = Depends(get_db)):
    """
    更新章节（支持修改标题和排序）

    单独修改 order_index 即可实现拖拽排序。
    """
    chapter = course_service.update_chapter(db, chapter_id, data)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.delete("/{chapter_id}", status_code=204)
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)):
    """删除章节（级联删除所有课节）"""
    success = course_service.delete_chapter(db, chapter_id)
    if not success:
        raise HTTPException(status_code=404, detail="章节不存在")
