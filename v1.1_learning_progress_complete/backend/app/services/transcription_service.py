"""
转录服务 — 音频转文字编排

编排流程：
  1. 从 app.state 获取 Whisper 模型单例
  2. 读取音频文件路径
  3. 调用 Whisper 转写
  4. 遍历 segments 写入 Transcript 表
  5. 更新 Lesson.status 和 duration

错误处理：
  转写失败时回退 Lesson.status → "uploaded"（可重试）
"""

import logging
import os

from sqlalchemy.orm import Session

from . import upload_service

logger = logging.getLogger(__name__)


def run_transcription(
    db_session_factory,
    lesson_id: int,
    whisper_transcriber,
) -> None:
    """
    后台运行语音转写

    此函数作为 FastAPI BackgroundTask 在后台线程中执行。

    Args:
        db_session_factory: SessionLocal（会话工厂，不能跨线程共享 session）
        lesson_id: 课节ID
        whisper_transcriber: WhisperTranscriber 实例（来自 app.state）

    流程：
        1. 从 DB 获取 Lesson
        2. 构建音频文件绝对路径
        3. 清除旧的 Transcript 记录
        4. 调用 Whisper 转写
        5. 逐段写入 Transcript 表
        6. 更新 Lesson.duration 和 status="completed"
        7. 若任何步骤失败，回退 status="uploaded"
    """
    db = db_session_factory()
    try:
        # ---- 1. 获取 Lesson ----
        from ..models.models import Lesson, Transcript
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson or not lesson.audio_path:
            logger.error("转录失败: lesson_id=%d 不存在或无音频文件", lesson_id)
            return

        # ---- 2. 构建音频绝对路径 ----
        audio_dir = upload_service.get_audio_dir(lesson_id)
        audio_abs_path = audio_dir / lesson.audio_path
        if not audio_abs_path.exists():
            logger.error("转录失败: 音频文件不存在 %s", audio_abs_path)
            _set_lesson_status(db, lesson_id, "uploaded")
            return

        # ---- 3. 清除旧转录数据 ----
        deleted = (
            db.query(Transcript)
            .filter(Transcript.lesson_id == lesson_id)
            .delete()
        )
        if deleted:
            logger.info("已清除 %d 条旧转录记录", deleted)
            db.commit()

        # ---- 4. 开始转写 ----
        _set_lesson_status(db, lesson_id, "processing")
        logger.info("开始转录: lesson_id=%d, audio=%s", lesson_id, audio_abs_path)

        segments, info = whisper_transcriber.transcribe(str(audio_abs_path))

        # ---- 5. 逐段写入 Transcript ----
        segment_count = 0
        for seg in segments:
            db.add(Transcript(
                lesson_id=lesson_id,
                start_time=round(seg.start, 2),
                end_time=round(seg.end, 2),
                text=seg.text.strip(),
            ))
            segment_count += 1

        # 一次性提交所有 segments
        db.commit()
        logger.info("已写入 %d 条转录记录", segment_count)

        # ---- 6. 更新 Lesson ----
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if lesson:
            lesson.duration = int(info.duration)
            lesson.status = "completed"
            db.commit()
            logger.info(
                "转录完成: lesson_id=%d, segments=%d, duration=%ds, language=%s",
                lesson_id, segment_count, int(info.duration), info.language,
            )

    except Exception as e:
        logger.exception("转录异常: lesson_id=%d, error=%s", lesson_id, e)
        try:
            _set_lesson_status(db, lesson_id, "uploaded")
        except Exception:
            logger.exception("回退 status 失败")
    finally:
        db.close()


def _set_lesson_status(db: Session, lesson_id: int, status: str) -> None:
    """更新 Lesson 状态"""
    from ..models.models import Lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        lesson.status = status
        db.commit()
