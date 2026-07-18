"""
学习进度路由

端点：
  GET  /api/lessons/{lesson_id}/progress  — 查询进度
  POST /api/lessons/{lesson_id}/progress  — 保存/更新进度
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Lesson, LessonProgress
from ..schemas.progress import LessonProgressCreate, LessonProgressResponse

router = APIRouter(prefix="/api/lessons", tags=["学习进度"])


# ===== 辅助函数 =====
def _parse_completed(completed_knowledge_points: str | None) -> list[int]:
    """将 TEXT 字段的 JSON 字符串转为列表，兼容空值和非法 JSON"""
    if not completed_knowledge_points:
        return []
    try:
        parsed = json.loads(completed_knowledge_points)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _progress_to_dict(progress: LessonProgress) -> dict:
    """将 ORM 对象转为 API 响应字典"""
    return {
        "lesson_id": progress.lesson_id,
        "current_time": progress.current_time,
        "completed_knowledge_points": _parse_completed(
            progress.completed_knowledge_points
        ),
        "progress_percent": progress.progress_percent,
        "created_at": progress.created_at.isoformat()
        if progress.created_at
        else None,
        "updated_at": progress.updated_at.isoformat()
        if progress.updated_at
        else None,
    }


def _default_response(lesson_id: int) -> dict:
    """构建默认进度数据"""
    return {
        "lesson_id": lesson_id,
        "current_time": 0,
        "completed_knowledge_points": [],
        "progress_percent": 0,
    }


# ===== 查询进度 =====
@router.get("/{lesson_id}/progress")
def get_progress(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """
    查询学习进度

    如果 LessonProgress 不存在则返回默认值，
    不会自动创建数据库记录。
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.lesson_id == lesson_id)
        .first()
    )

    if not progress:
        return _default_response(lesson_id)

    return _progress_to_dict(progress)


# ===== 保存/更新进度 =====
@router.post("/{lesson_id}/progress")
def save_progress(
    lesson_id: int,
    data: LessonProgressCreate,
    db: Session = Depends(get_db),
):
    """
    保存或更新学习进度

    - 如果 LessonProgress 已存在 → 更新
    - 如果不存在 → 创建新记录
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.lesson_id == lesson_id)
        .first()
    )

    # 将 completed_knowledge_points 序列化为 JSON 字符串
    kp_json = json.dumps(data.completed_knowledge_points)

    if progress:
        # 更新已有记录
        progress.current_time = data.current_time
        progress.completed_knowledge_points = kp_json
        progress.progress_percent = data.progress_percent
    else:
        # 创建新记录
        progress = LessonProgress(
            lesson_id=lesson_id,
            current_time=data.current_time,
            completed_knowledge_points=kp_json,
            progress_percent=data.progress_percent,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return _progress_to_dict(progress)
