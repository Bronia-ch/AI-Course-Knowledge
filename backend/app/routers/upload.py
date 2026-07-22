"""
音频上传路由 — Lesson 音频文件管理

端点：
  POST   /api/lessons/{id}/upload-audio  — 上传音频
  GET    /api/lessons/{id}/audio          — 获取音频信息
  DELETE /api/lessons/{id}/audio          — 删除音频
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.upload import AudioInfoResponse
from ..schemas.course import LessonResponse
from ..services import course_service, upload_service

router = APIRouter(prefix="/api/lessons", tags=["音频上传"])
logger = logging.getLogger(__name__)


@router.post("/{lesson_id}/upload-audio", response_model=LessonResponse)
async def upload_audio(
    lesson_id: int,
    file: UploadFile = File(..., description="音频文件"),
    db: Session = Depends(get_db),
):
    """
    上传课节音频文件

    - 文件保存到 uploads/audio/{lesson_id}/ 目录
    - 自动更新 Lesson.audio_path 和 status="uploaded"
    - 如果已有音频文件，会先删除旧文件
    """
    # 确保 Lesson 存在
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    try:
        old_filename = os.path.basename(lesson.audio_path) if lesson.audio_path else None
        # 新文件完成大小和真实音频校验后，才允许替换数据库记录。
        stored_filename, _ = await upload_service.save_audio_file(lesson_id, file)
        try:
            lesson.audio_path = stored_filename
            lesson.status = "uploaded"
            db.commit()
            db.refresh(lesson)
        except Exception:
            db.rollback()
            upload_service.delete_audio_file(lesson_id, stored_filename)
            raise

        # 数据库已稳定指向新文件，旧文件删除失败只会留下可清理的孤立文件。
        if old_filename and old_filename != stored_filename:
            try:
                upload_service.delete_audio_file(lesson_id, old_filename)
            except OSError:
                logger.warning("旧音频清理失败: lesson_id=%d, file=%s", lesson_id, old_filename)
        return lesson

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("文件保存失败: lesson_id=%d", lesson_id)
        raise HTTPException(status_code=500, detail="文件保存失败，请稍后重试") from e


@router.get("/{lesson_id}/audio", response_model=AudioInfoResponse)
def get_audio_info(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """
    获取课节的音频文件信息

    返回文件名、大小、格式等元数据。
    """
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    info = upload_service.get_audio_info(lesson_id, lesson.audio_path)
    if info is None:
        raise HTTPException(status_code=404, detail="该课节未上传音频文件")

    return info


@router.delete("/{lesson_id}/audio", response_model=LessonResponse)
def delete_audio(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """
    删除课节的音频文件

    - 删除磁盘上的音频文件
    - 重置 Lesson.audio_path 和 status="pending"
    """
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    if not lesson.audio_path:
        raise HTTPException(status_code=404, detail="该课节未上传音频文件")

    # 删除文件
    filename = os.path.basename(lesson.audio_path)
    upload_service.delete_audio_file(lesson_id, filename)

    # 重置 Lesson 状态
    from ..schemas.course import LessonUpdate
    course_service.update_lesson(
        db, lesson_id,
        LessonUpdate(audio_path=None, status="pending")
    )

    db.refresh(lesson)
    return lesson
