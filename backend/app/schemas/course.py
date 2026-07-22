"""
API Schema 定义 — Course / Chapter / Lesson

所有 Response schema 设置 from_attributes=True，
使得 SQLAlchemy ORM 对象可直接通过 Pydantic 序列化。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Course Schemas
# =============================================================================
class CourseCreate(BaseModel):
    """创建课程请求"""
    title: str
    description: Optional[str] = None


class CourseUpdate(BaseModel):
    """更新课程请求（所有字段可选，只更新传入的字段）"""
    title: Optional[str] = None
    description: Optional[str] = None


class CourseResponse(BaseModel):
    """课程基础响应"""
    id: int
    title: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseDetail(CourseResponse):
    """课程详情（含章节列表）"""
    chapters: List["ChapterResponse"] = Field(default_factory=list)


class CourseTreeResponse(CourseResponse):
    """课程树（含章节→课节完整嵌套）"""
    chapters: List["ChapterTreeResponse"] = Field(default_factory=list)


# =============================================================================
# Chapter Schemas
# =============================================================================
class ChapterCreate(BaseModel):
    """创建章节请求"""
    course_id: int
    title: str
    order_index: int = 0


class ChapterUpdate(BaseModel):
    """更新章节请求（标题和排序均可独立修改）"""
    title: Optional[str] = None
    order_index: Optional[int] = None


class ChapterResponse(BaseModel):
    """章节基础响应"""
    id: int
    course_id: int
    title: str
    order_index: int

    model_config = {"from_attributes": True}


class ChapterDetail(ChapterResponse):
    """章节详情（含课节列表）"""
    lessons: List["LessonResponse"] = Field(default_factory=list)


class ChapterTreeResponse(ChapterResponse):
    """章节树节点（含课节列表）"""
    lessons: List["LessonResponse"] = Field(default_factory=list)


# =============================================================================
# Lesson Schemas
# =============================================================================
class LessonCreate(BaseModel):
    """创建课节请求"""
    chapter_id: int
    title: str
    description: Optional[str] = None
    audio_path: Optional[str] = None
    duration: int = 0


class LessonUpdate(BaseModel):
    """更新课节请求（所有字段可选）"""
    title: Optional[str] = None
    description: Optional[str] = None
    audio_path: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[str] = None


class LessonResponse(BaseModel):
    """课节响应"""
    id: int
    chapter_id: int
    title: str
    description: Optional[str]
    audio_path: Optional[str]
    duration: int
    status: str
    transcript_count: int = 0      # 转写片段数量
    knowledge_point_count: int = 0 # 知识点数量
    project_count: int = 0         # 项目数量
    created_at: datetime

    model_config = {"from_attributes": True}


# 解决前向引用：CourseDetail 引用 ChapterResponse，
# ChapterDetail 引用 LessonResponse（已在上面定义，无需特殊处理）
# CourseTreeResponse 引用 ChapterTreeResponse
