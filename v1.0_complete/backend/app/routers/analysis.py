"""
分析路由 — 触发 DeepSeek 知识总结

端点：
  POST /api/lessons/{id}/analyze  — 启动后台知识分析
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..schemas.course import LessonResponse
from ..services import course_service
from ..services.analysis_service import run_analysis

router = APIRouter(prefix="/api/lessons", tags=["知识分析"])


@router.post("/{lesson_id}/analyze", response_model=LessonResponse)
def trigger_analysis(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    触发 DeepSeek 知识分析（异步后台执行）

    前置条件：
      - Lesson 存在
      - status 为 "completed"（转录已完成）
      - Transcript 表中有转写数据
      - DEEPSEEK_API_KEY 已配置

    响应立即返回 Lesson (status="analyzing")，
    客户端可通过轮询 GET /api/lessons/{id} 检查状态：
      - "analyzing" → 分析进行中
      - "analyzed"  → 分析完成，knowledge_points 和 projects 已填充
      - "completed" → 分析失败（可重试）
    """
    # ---- 验证 Lesson ----
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    if lesson.status not in ("completed", "analyzed"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"当前状态 '{lesson.status}' 不支持分析。"
                "请先完成转录（status='completed'）再触发分析"
            )
        )

    if lesson.transcript_count == 0:
        raise HTTPException(
            status_code=400,
            detail="该课节没有转写数据。请先完成语音转文字"
        )

    if lesson.status == "analyzing":
        raise HTTPException(status_code=400, detail="分析正在进行中，请等待完成")

    # ---- 设置状态为 analyzing ----
    from ..schemas.course import LessonUpdate
    course_service.update_lesson(db, lesson_id, LessonUpdate(status="analyzing"))
    db.commit()
    db.refresh(lesson)

    # ---- 启动后台分析 ----
    background_tasks.add_task(
        run_analysis,
        SessionLocal,     # 会话工厂（后台线程新建 session）
        lesson_id,
    )

    return lesson
