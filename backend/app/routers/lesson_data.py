"""
课节数据查询路由 — Transcript / KnowledgePoint / Project

端点：
  GET /api/lessons/{id}/transcripts       — 转写文本列表
  GET /api/lessons/{id}/knowledge-points  — 知识点列表
  GET /api/lessons/{id}/projects          — 项目列表
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Lesson, Transcript, KnowledgePoint, Project
from ..services import course_service

router = APIRouter(prefix="/api/lessons", tags=["课节数据"])


# ===== Transcript 查询 =====
@router.get("/{lesson_id}/transcripts")
def list_transcripts(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """获取课节的所有转写文本（按时间排序）"""
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    segments = (
        db.query(Transcript)
        .filter(Transcript.lesson_id == lesson_id)
        .order_by(Transcript.start_time.asc())
        .all()
    )

    return [
        {
            "id": s.id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "text": s.text,
        }
        for s in segments
    ]


# ===== KnowledgePoint 查询 =====
@router.get("/{lesson_id}/knowledge-points")
def list_knowledge_points(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """获取课节的所有知识点（按重要程度降序）"""
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    points = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.lesson_id == lesson_id)
        .order_by(KnowledgePoint.importance.desc())
        .all()
    )

    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "timestamp": p.timestamp,
            "importance": p.importance,
            "category": p.category,
        }
        for p in points
    ]


# ===== Project 查询 =====
@router.get("/{lesson_id}/projects")
def list_projects(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """获取课节的所有项目"""
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    projects = (
        db.query(Project)
        .filter(Project.lesson_id == lesson_id)
        .all()
    )

    return [
        {
            "id": p.id,
            "name": p.name,
            "goal": p.goal,
            "input": p.input,
            "output": p.output,
            "technology_stack": p.technology_stack,
            "workflow": p.workflow,
        }
        for p in projects
    ]
