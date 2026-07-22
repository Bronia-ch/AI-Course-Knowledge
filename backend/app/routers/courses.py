"""
Course 路由 — 课程 CRUD + 课程树查询

端点：
  GET    /api/courses          — 课程列表
  GET    /api/courses/{id}     — 课程详情（含章节）
  GET    /api/courses/{id}/tree — 课程完整树
  POST   /api/courses          — 创建课程
  PUT    /api/courses/{id}     — 更新课程
  DELETE /api/courses/{id}     — 删除课程（级联删除）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseDetail,
    CourseTreeResponse,
)
from ..schemas.progress import CourseProgressResponse
from ..services import course_service

router = APIRouter(prefix="/api/courses", tags=["课程管理"])


@router.get("", response_model=list[CourseProgressResponse])
def list_courses(db: Session = Depends(get_db)):
    """获取所有课程列表及学习进度汇总"""
    return course_service.get_courses_with_progress(db)


@router.get("/{course_id}", response_model=CourseDetail)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """获取课程详情（含章节列表，章节按 order_index 排序）"""
    course = course_service.get_course_with_chapters(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    # 章节按 order_index 排序
    course.chapters.sort(key=lambda c: c.order_index)
    return course


@router.get("/{course_id}/tree", response_model=CourseTreeResponse)
def get_course_tree(course_id: int, db: Session = Depends(get_db)):
    """获取课程完整嵌套树（课程 → 章节 → 课节）"""
    course = course_service.get_course_tree(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    # 章节排序
    course.chapters.sort(key=lambda c: c.order_index)
    return course


@router.post("", response_model=CourseResponse, status_code=201)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    """创建新课程"""
    return course_service.create_course(db, data)


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, data: CourseUpdate, db: Session = Depends(get_db)):
    """更新课程信息（只更新传入的字段）"""
    course = course_service.update_course(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """删除课程（级联删除所有章节和课节）"""
    success = course_service.delete_course(db, course_id)
    if not success:
        raise HTTPException(status_code=404, detail="课程不存在")
