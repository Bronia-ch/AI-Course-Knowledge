"""AI 学习助手相关 Schema。"""

from pydantic import BaseModel, Field


class LessonQuestionRequest(BaseModel):
    """当前课节问答请求。"""

    question: str = Field(min_length=1, max_length=1000)


class LessonQuestionResponse(BaseModel):
    """当前课节问答响应。"""

    lesson_id: int
    question: str
    answer: str
