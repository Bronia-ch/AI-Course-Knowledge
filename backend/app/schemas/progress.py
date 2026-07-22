"""
学习进度 Schema
"""

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class LessonProgressCreate(BaseModel):
    """保存/更新进度请求"""
    current_time: float = Field(default=0.0, ge=0)
    completed_knowledge_points: List[int] = Field(default_factory=list)
    progress_percent: float = Field(default=0.0, ge=0, le=100)


class LessonProgressResponse(BaseModel):
    """进度响应"""
    lesson_id: int
    current_time: float
    completed_knowledge_points: List[int]
    progress_percent: float
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CourseProgressResponse(BaseModel):
    """课程列表中的学习进度汇总"""
    id: int
    title: str
    description: str | None = None
    created_at: datetime
    total_lessons: int
    started_lessons: int
    completed_lessons: int
    progress_percent: float
    learning_status: Literal["not_started", "in_progress", "completed"]
    last_studied_at: datetime | None = None
    last_lesson_id: int | None = None
    last_lesson_title: str | None = None
    last_lesson_current_time: float = 0.0
