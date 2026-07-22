"""AI 学习助手路由。"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Transcript
from ..schemas.assistant import LessonQuestionRequest, LessonQuestionResponse
from ..services import course_service
from ..services.assistant_service import answer_lesson_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lessons", tags=["AI学习助手"])


@router.post("/{lesson_id}/ask", response_model=LessonQuestionResponse)
def ask_lesson_question(
    lesson_id: int,
    data: LessonQuestionRequest,
    db: Session = Depends(get_db),
):
    """基于当前课节转写文本回答问题。"""
    lesson = course_service.get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课节不存在")

    segments = (
        db.query(Transcript)
        .filter(Transcript.lesson_id == lesson_id)
        .order_by(Transcript.start_time.asc())
        .all()
    )
    if not segments:
        raise HTTPException(status_code=400, detail="该课节没有转写内容")

    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        answer = answer_lesson_question(segments, question)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("课节问答失败: lesson_id=%d", lesson_id)
        raise HTTPException(status_code=502, detail="AI 回答失败，请稍后重试") from exc

    return {
        "lesson_id": lesson_id,
        "question": question,
        "answer": answer,
    }
