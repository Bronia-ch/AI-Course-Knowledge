"""
学习进度 Schema
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class LessonProgressCreate(BaseModel):
    """保存/更新进度请求"""
    current_time: float = 0.0
    completed_knowledge_points: List[int] = []   # 已完成知识点 ID 列表
    progress_percent: float = 0.0                 # 进度百分比 0-100


class LessonProgressResponse(BaseModel):
    """进度响应"""
    lesson_id: int
    current_time: float
    completed_knowledge_points: List[int]
    progress_percent: float
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
