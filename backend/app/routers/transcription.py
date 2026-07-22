"""
转录路由 — 触发语音转文字

端点：
  POST /api/lessons/{id}/transcribe  — 启动后台转录任务
"""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..schemas.course import LessonResponse
from ..services import course_service, upload_service
from ..services.transcription_service import run_transcription

router = APIRouter(prefix="/api/lessons", tags=["语音转文字"])


@router.post("/{lesson_id}/transcribe", response_model=LessonResponse)
def trigger_transcription(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    触发语音转文字（异步后台执行）

    前置条件：
      - Lesson 存在
      - audio_path 不为空
      - status 为 "uploaded"（防止重复触发）
      - 音频文件在磁盘上存在

    响应立即返回 Lesson (status="processing")，
    客户端可通过轮询 GET /api/lessons/{id} 检查状态：
      - "processing" → 转写进行中
      - "completed"  → 转写完成
      - "uploaded"   → 转写失败（可重试）
    """
    # ---- 验证 Lesson ----
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    if not lesson.audio_path:
        raise HTTPException(status_code=400, detail="该课节未上传音频文件")

    if lesson.status == "processing":
        raise HTTPException(status_code=400, detail="转录正在进行中，请等待完成")

    if lesson.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="转录已完成。如需重新转录，请先删除旧音频再上传新文件。"
        )

    if lesson.status not in ("uploaded",):
        raise HTTPException(
            status_code=400,
            detail=f"当前状态 '{lesson.status}' 不支持转录操作"
        )

    # ---- 验证音频文件存在 ----
    audio_dir = upload_service.get_audio_dir(lesson_id)
    audio_abs_path = audio_dir / lesson.audio_path
    if not audio_abs_path.exists():
        raise HTTPException(status_code=400, detail=f"音频文件不存在: {audio_abs_path}")

    # ---- 获取 Whisper 转录器（模型会在后台任务首次使用时加载）----
    whisper_model = getattr(request.app.state, "whisper_model", None)
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper 转录服务未初始化，请重启后端服务")

    # ---- 设置状态为 processing ----
    from ..schemas.course import LessonUpdate
    course_service.update_lesson(db, lesson_id, LessonUpdate(status="processing"))
    db.commit()
    db.refresh(lesson)

    # ---- 启动后台转录 ----
    background_tasks.add_task(
        run_transcription,
        SessionLocal,      # 会话工厂（后台线程新建 session）
        lesson_id,
        whisper_model,
    )

    return lesson
